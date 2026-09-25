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

    def _decide(self) -> None:
        """Решение клапана вместо общего правила NodeAgent: REFUSE по
        собственному порогу с гистерезисом. В пассивном режиме -- без решений."""
        if not self.decides:
            self.throttled = False
            return
        self._update_throttle()
        self.accepting = not self.throttled  # NodeAgent.accept_task отказывает по этому флагу

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

    # accept_task/step -- из NodeAgent: он вызывает _decide() и отказывает,
    # пока accepting == False (задача остаётся у отправителя -- Pump).
    # Обработка уже принятой очереди НИКОГДА не блокируется throttled --
    # это и разрывает дедлок: queue продолжает убывать, значит load рано
    # или поздно упадёт ниже recovery_threshold.

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

    def _decide(self) -> None:
        # MODIFY: подстраиваем скорость обработки (NodeAgent.step вызывает
        # _decide до того, как решит, начинать ли новую задачу). Во входе
        # узел никогда не отказывает -- он просто медленнее его переваривает.
        # В пассивном режиме -- всегда базовая скорость.
        if self.decides and self.load >= self.safety_threshold:
            self.processing_time = self._base_processing_time * self.throttle_factor
        else:
            self.processing_time = self._base_processing_time

    def state_dict(self) -> dict:
        d = super().state_dict()
        d["effective_processing_time"] = self.processing_time  # видимость MODIFY
        return d
