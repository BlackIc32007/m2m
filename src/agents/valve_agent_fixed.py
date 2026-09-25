"""
Два способа починить дедлок первой версии ValveAgent (подробности --
docs/valve_gas_liquid_domain.md; текущий valve_agent.py его уже не имеет).

Корень проблемы был в том, что self.state одновременно означает "чем занят узел"
(idle/working/failed -- использует NodeAgent.step() для обработки) И
"принимает ли узел новый поток" (restricted). Пока state == "restricted",
NodeAgent.step() не вызывается вовсе -> очередь не убывает -> load не падает
-> условие выхода из restricted никогда не выполняется.

Оба варианта ниже разделяют эти два смысла на два независимых сигнала:
  - "чем занят узел" остаётся в self.state (idle/working/failed), как и было
    в NodeAgent -- НЕ трогаем.
  - "принимает ли узел новую работу" -- отдельный флаг/механизм, не блокирующий
    обработку уже накопленной очереди.

Это и есть чистая реализация ACCEPT / REFUSE / MODIFY: узел может отдельно
решать "беру ли я новую задачу" и "как быстро я обрабатываю то, что уже
взял" -- вместо одного грубого флага "работаю / не работаю вообще".
"""
from src.agents.node_agent import NodeAgent


# ===================================================================== #
# Вариант A -- REFUSE с выходом.
# Клапан продолжает обрабатывать то, что уже в очереди (NodeAgent.step()
# вызывается всегда), но ОТКАЗЫВАЕТ принимать новые задачи, пока перегружен.
# Задачи, которым отказали, остаются на upstream-узле (Pump) -- это
# называется backpressure: перегрузка распространяется назад по цепочке,
# а не теряется и не блокирует уже принятую работу.
# ===================================================================== #
class ValveAgentRefuse(NodeAgent):
    def __init__(self, model, name, safety_threshold: float = 0.7,
                 recovery_threshold: float | None = None, **kwargs):
        super().__init__(model, name, **kwargs)
        self.safety_threshold = safety_threshold
        # Гистерезис: выходим из throttled заметно раньше порога входа,
        # чтобы не "дрожать" туда-сюда на границе (вошли при load>=0.7,
        # выходим только при load<0.42, а не сразу при 0.69).
        # Проверка `is None`, а не `or`: явный recovery_threshold=0.0 --
        # допустимое значение ("выходить только при пустой очереди").
        if recovery_threshold is None:
            recovery_threshold = safety_threshold * 0.6
        if recovery_threshold > safety_threshold:
            raise ValueError("recovery_threshold не может быть выше safety_threshold")
        self.recovery_threshold = recovery_threshold
        self.throttled = False  # НЕ путать с self.state -- это отдельный сигнал

    def _update_throttle(self) -> None:
        """Единственное место, где меняется флаг throttled (с гистерезисом).

        Вызывается и из step() -- чтобы флаг сбрасывался, даже если новых
        задач нет (например, upstream в отказе, а очередь уже опустела), --
        и из accept_task(), чтобы решение о входе опиралось на свежий load.
        """
        if not self.throttled and self.load >= self.safety_threshold:
            self.throttled = True
            if self.logger:
                self.logger.log_event(
                    simulation_step=self.model.steps, node_id=self.name,
                    event="self_throttle_refuse_new",
                )
        elif self.throttled and self.load < self.recovery_threshold:
            self.throttled = False
            if self.logger:
                self.logger.log_event(
                    simulation_step=self.model.steps, node_id=self.name,
                    event="unrestricted",
                )

    def accept_task(self, task) -> bool:
        # Решение ACCEPT/REFUSE принимается независимо от self.state.
        self._update_throttle()

        if self.throttled:
            if self.logger:
                self.logger.log_event(
                    simulation_step=self.model.steps, node_id=self.name,
                    event="task_refused_throttled", task_id=task.task_id,
                )
            return False  # REFUSE -- задача остаётся у отправителя (Pump)

        return super().accept_task(task)  # ACCEPT -- обычная логика NodeAgent

    def step(self) -> None:
        # Обработка уже принятой очереди НИКОГДА не блокируется throttled --
        # это и разрывает дедлок: queue продолжает убывать, значит load рано
        # или поздно упадёт ниже recovery_threshold.
        super().step()
        # Обновляем флаг после шага (очередь могла уменьшиться), даже если
        # accept_task в этом тике не вызывался.
        self._update_throttle()

    def state_dict(self) -> dict:
        d = super().state_dict()
        d["accepting_new"] = not self.throttled  # видимость ACCEPT/REFUSE в снимке состояния
        return d


# ===================================================================== #
# Вариант B -- MODIFY (частичный пропуск).
# Клапан не отказывается ни от чего, но при перегрузке обрабатывает МЕДЛЕННЕЕ
# (эффективный processing_time увеличивается). Задача всё равно рано или
# поздно проходит, просто дольше -- как частично прикрытый вентиль, а не
# полностью закрытый.
# ===================================================================== #
class ValveAgentModify(NodeAgent):
    def __init__(self, model, name, safety_threshold: float = 0.7,
                 throttle_factor: int = 3, **kwargs):
        super().__init__(model, name, **kwargs)
        self.safety_threshold = safety_threshold
        self.throttle_factor = throttle_factor  # во сколько раз медленнее при перегрузке
        self._base_processing_time = self.processing_time

    def step(self) -> None:
        # MODIFY: подстраиваем скорость обработки ПЕРЕД тем, как NodeAgent
        # решит, начинать ли новую задачу. Раз это происходит в step(), а не
        # в accept_task(), узел никогда не отказывает во входе -- он просто
        # медленнее его переваривает.
        if self.load >= self.safety_threshold:
            self.processing_time = self._base_processing_time * self.throttle_factor
        else:
            self.processing_time = self._base_processing_time
        super().step()

    def state_dict(self) -> dict:
        d = super().state_dict()
        d["effective_processing_time"] = self.processing_time  # видимость MODIFY
        return d
