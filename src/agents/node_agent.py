"""
NodeAgent -- узел производственной цепочки (Mesa Agent).

Состояние узла хранится как обычные атрибуты Python-объекта (это и есть
"хранение состояния агента" в Mesa -- никакой отдельной БД не требуется на
этом этапе):

    ID (mesa даёт unique_id автоматически)
    state          -- "idle" | "working" | "blocked" | "failed"
                       blocked -- задача обработана, но следующий узел её
                       пока не принимает (очередь полна / отказ); задача
                       остаётся здесь и передаётся повторно на каждом шаге
    current_task   -- задача, которая сейчас обрабатывается (или ждёт
                       передачи), либо None
    queue          -- список задач, ожидающих обработки (Task объекты)
    load           -- условная загрузка узла, 0..1 (для примера: len(queue)/queue_capacity)
    available      -- bool, может ли узел сейчас принять новую задачу
    priority       -- "normal" | "high" (на этом этапе не используется в логике,
                       зарезервировано под следующий этап)

Два режима работы (model.decision_mode, переключается на ходу):

    "passive"    -- пассивный: узел не принимает решений, только передаёт
                    поток -- принимает задачу, если в очереди есть место,
                    обрабатывает и передаёт дальше.
    "autonomous" -- автономный: узел сам решает, принимать ли новые задачи (ACCEPT/REFUSE),
               глядя только на свой локальный контекст:
                 REFUSE, если очередь >= stop_threshold или следующий узел
                        в отказе;
                 ACCEPT снова, когда очередь < resume_threshold и следующий
                        узел работает.
               Уже принятую очередь узел обрабатывает в любом случае.
               Каждое решение с причиной пишется в журнал (event=decision_*).
"""
from mesa import Agent


class NodeAgent(Agent):
    # True у служебных InputAgent/OutputAgent (концы цепочки): их нельзя
    # добавить через UI и им не нужны рекомендации LLM
    is_endpoint = False

    def __init__(
        self,
        model,
        name: str,
        processing_time: int = 2,
        queue_capacity: int = 10,
        downstream=None,
        logger=None,
        stop_threshold: float = 0.8,
        resume_threshold: float = 0.5,
    ):
        super().__init__(model)
        if resume_threshold > stop_threshold:
            raise ValueError("resume_threshold не может быть выше stop_threshold")
        self.name = name
        self.processing_time = processing_time
        self.queue_capacity = queue_capacity
        # Список приёмников. Для линейной цепочки в нём 0 или 1 элемент; при
        # ветвлении -- несколько (см. _forward_task). Атрибут .downstream
        # остаётся как совместимое свойство (первый приёмник либо None).
        self.downstreams = [downstream] if downstream is not None else []
        self._rr_index = 0  # для чередования веток при ветвлении
        self.logger = logger

        # -------- состояние узла --------
        self.state = "idle"          # idle | working | blocked | failed
        self.current_task = None     # Task | None
        self.queue = []              # list[Task]
        self._remaining_processing = 0  # сколько шагов осталось до завершения текущей задачи
        self.available = True
        self.priority = "normal"

        # -------- для сценария отказа/восстановления --------
        self._failed_steps_left = 0

        # -------- решение агента (используется только в автономном режиме) --------
        self.stop_threshold = stop_threshold
        self.resume_threshold = resume_threshold
        self.accepting = True           # решение: принимаю ли новые задачи
        self.last_decision_reason = None

    # ------------------------------------------------------------------ #
    # Публичное состояние в виде dict -- удобно для логов, визуализации и
    # передачи в Ollama.
    # ------------------------------------------------------------------ #
    @property
    def downstream(self):
        return self.downstreams[0] if self.downstreams else None

    @downstream.setter
    def downstream(self, node) -> None:
        self.downstreams = [node] if node is not None else []

    @property
    def load(self) -> float:
        if self.queue_capacity == 0:
            return 0.0
        return round(len(self.queue) / self.queue_capacity, 2)

    def state_dict(self) -> dict:
        return {
            "node": self.name,
            "state": self.state,
            "current_task": self.current_task.task_id if self.current_task else None,
            "queue": len(self.queue),
            "load": self.load,
            "available": self.available,
            "priority": self.priority,
        } | ({} if self.is_endpoint else {
            "decision": ("ACCEPT" if self.accepting else "REFUSE") if self.decides else None,
            "decision_reason": self.last_decision_reason if self.decides else None,
        })

    # ------------------------------------------------------------------ #
    # Решение агента: ACCEPT / REFUSE (только в автономном режиме).
    # ------------------------------------------------------------------ #
    @property
    def decides(self) -> bool:
        """True -- узел сам принимает решения; False -- пассивный режим."""
        return not self.is_endpoint and getattr(self.model, "decision_mode", "passive") == "autonomous"

    def _decide(self) -> None:
        if not self.decides:
            return
        downstream_down = bool(self.downstreams) and not any(d.available for d in self.downstreams)
        if self.accepting:
            if self.load >= self.stop_threshold:
                reason = f"очередь {self.load:.0%} >= порога {self.stop_threshold:.0%}"
            elif downstream_down:
                reason = "следующий узел в отказе -- нет смысла копить задачи"
            else:
                return
            self.accepting = False
            self._log_decision("REFUSE", reason)
        elif self.load < self.resume_threshold and not downstream_down:
            self.accepting = True
            self._log_decision("ACCEPT", f"очередь {self.load:.0%} < {self.resume_threshold:.0%}, "
                                         "следующий узел работает")

    def _log_decision(self, decision: str, reason: str) -> None:
        self.last_decision_reason = f"{decision}: {reason}"
        if self.logger:
            self.logger.log_event(simulation_step=self.model.steps, node_id=self.name,
                                  event=f"decision_{decision}", details={"reason": reason,
                                                                        "load": self.load})

    # ------------------------------------------------------------------ #
    # Изменение состояния -- централизованно, чтобы каждое изменение сразу
    # попадало в лог (журналирование событий).
    # ------------------------------------------------------------------ #
    def _set_state(self, new_state: str, event: str, task_id: str | None = None) -> None:
        old_state = self.state
        self.state = new_state
        self.available = new_state != "failed"
        if self.logger:
            self.logger.log_state_change(
                simulation_step=self.model.steps,
                node_id=self.name,
                old_state=old_state,
                new_state=new_state,
                event=event,
                task_id=task_id,
            )

    # ------------------------------------------------------------------ #
    # Приём задачи в очередь (вызывается либо моделью для входного узла,
    # либо соседним узлом при передаче задачи вниз по цепочке).
    # ------------------------------------------------------------------ #
    def accept_task(self, task) -> bool:
        self._decide()
        if self.decides and not self.accepting:
            return False  # REFUSE -- решение агента; задача остаётся у отправителя
        if len(self.queue) >= self.queue_capacity:
            return False  # очередь переполнена, задача не принята
        self.queue.append(task)
        task.visit(self.name, self.model.steps)
        if self.logger:
            self.logger.log_event(
                simulation_step=self.model.steps,
                node_id=self.name,
                event="task_queued",
                task_id=task.task_id,
            )
        return True

    # ------------------------------------------------------------------ #
    # Отказ / восстановление узла -- вызывается моделью по сценарию.
    # Задача, которая была в работе в момент отказа, НЕ теряется: она
    # остаётся в current_task, и после восстановления узел продолжает её
    # с того же места (_remaining_processing не сбрасывается).
    # ------------------------------------------------------------------ #
    def fail(self, duration_steps: int) -> None:
        self._failed_steps_left = duration_steps
        if self.state != "failed":
            self._set_state("failed", event="node_failed",
                            task_id=self.current_task.task_id if self.current_task else None)

    def _resume_state(self) -> str:
        """В какое состояние вернуться после отказа."""
        if self.current_task is None:
            return "idle"
        return "blocked" if self._remaining_processing <= 0 else "working"

    def recover_now(self) -> None:
        self._failed_steps_left = 0
        if self.state != "failed":
            return  # восстанавливать нечего; иначе затёрли бы working/blocked
        self._set_state(self._resume_state(), event="node_recovered",
                        task_id=self.current_task.task_id if self.current_task else None)

    # ------------------------------------------------------------------ #
    # Основной шаг агента -- вызывается планировщиком модели каждый tick.
    # ------------------------------------------------------------------ #
    def step(self) -> None:
        self._decide()  # пересмотреть решение, даже если новых задач не приходит

        # 1. Если узел в отказе -- просто ждём восстановления (задачи копятся в очереди).
        if self.state == "failed":
            self._failed_steps_left -= 1
            if self._failed_steps_left <= 0:
                self.recover_now()
            return

        # 2. Задача уже обработана, но следующий узел её не взял -- пробуем снова.
        if self.state == "blocked":
            self._try_hand_off()
            return

        # 3. Если узел сейчас обрабатывает задачу -- продолжаем обработку.
        if self.state == "working":
            self._remaining_processing -= 1
            if self._remaining_processing <= 0:
                self._finish_current_task()
            return

        # 4. Узел свободен (idle) -- взять следующую задачу из очереди, если она есть.
        if self.queue:
            self._start_next_task()

    def _start_next_task(self) -> None:
        task = self.queue.pop(0)
        self.current_task = task
        self._remaining_processing = self.processing_time
        self._set_state("working", event="task_started", task_id=task.task_id)

    def _finish_current_task(self) -> None:
        if self.logger:
            self.logger.log_event(
                simulation_step=self.model.steps,
                node_id=self.name,
                event="task_finished",
                task_id=self.current_task.task_id,
            )
        self._try_hand_off()

    def _try_hand_off(self) -> None:
        """Передать обработанную задачу дальше. Пока приёмник её не взял,
        задача остаётся у этого узла (state=blocked), а не теряется --
        так перегрузка/отказ распространяется назад по цепочке."""
        task = self.current_task
        if not self.downstreams:
            # узел без приёмника (цепочка без OutputAgent) -- сам конец цепочки
            self.model.completed_tasks += 1
        elif not self._forward_task(task):
            if self.state != "blocked":
                self._set_state("blocked", event="task_blocked_downstream_busy",
                                task_id=task.task_id)
            return
        self.current_task = None
        self._set_state("idle", event="task_handed_off", task_id=task.task_id)

    def _forward_task(self, task) -> bool:
        """Отдать задачу одному из приёмников; True, если кто-то принял.

        Если веток несколько, они перебираются по кругу (round-robin),
        причём неисправные узлы пробуются в последнюю очередь.
        """
        n = len(self.downstreams)
        start = self._rr_index % n
        candidates = [self.downstreams[(start + i) % n] for i in range(n)]
        candidates.sort(key=lambda t: not t.available)  # стабильная: живые первыми

        for target in candidates:
            if target.accept_task(task):
                self._rr_index = (self.downstreams.index(target) + 1) % n
                return True
        return False
