"""
ValveAgent -- узел домена "газ/жидкость" с поддержкой паттерна
ACCEPT / REFUSE / MODIFY.

Логика решения агента:
- ACCEPT: Нагрузка нормальная. Пропускаем поток с базовой скоростью.
- MODIFY: Нагрузка выше safety_threshold. Клапан дросселирует (замедляет)
  обработку, чтобы дать системе разгрузиться, не останавливая поток полностью.
- REFUSE: Очередь переполнена. Приём новых задач невозможен.

В пассивном режиме (model.decision_mode == "passive") клапан не принимает
решений и только передаёт поток (ACCEPT с базовой скоростью).
"""
from src.agents.node_agent import NodeAgent


class ValveAgent(NodeAgent):
    def __init__(
        self,
        model,
        name: str,
        safety_threshold: float = 0.5,
        throttled_processing_time: int = 5,
        **kwargs
    ):
        super().__init__(model, name, **kwargs)
        self.safety_threshold = safety_threshold
        self.base_processing_time = self.processing_time
        self.throttled_processing_time = throttled_processing_time
        self.mode = "ACCEPT"  # Переключатель режимов: ACCEPT | MODIFY | REFUSE

    def _decide(self) -> None:
        """Решение клапана (вызывается NodeAgent.step и accept_task) --
        заменяет общее правило NodeAgent своим: ACCEPT/MODIFY."""
        self._evaluate_local_context()

    def _evaluate_local_context(self) -> None:
        """Локальный контекст узла определяет его режим работы."""
        # 1. Проверка на необходимость MODIFY (дросселирование)
        if self.decides and self.load >= self.safety_threshold:
            if self.mode != "MODIFY":
                self.mode = "MODIFY"
                self.processing_time = self.throttled_processing_time
                if self.logger:
                    self.logger.log_event(
                        simulation_step=self.model.steps,
                        node_id=self.name,
                        event="mode_changed_to_MODIFY",
                        task_id=self.current_task.task_id if self.current_task else None,
                    )
        else:
            if self.mode != "ACCEPT":
                self.mode = "ACCEPT"
                self.processing_time = self.base_processing_time
                if self.logger:
                    self.logger.log_event(
                        simulation_step=self.model.steps,
                        node_id=self.name,
                        event="mode_changed_to_ACCEPT",
                        task_id=self.current_task.task_id if self.current_task else None,
                    )

    def accept_task(self, task) -> bool:
        """Переопределение метода приёма задачи (ACCEPT / REFUSE)."""
        # Если очередь заполнена -- явный REFUSE
        if len(self.queue) >= self.queue_capacity:
            if self.logger:
                self.logger.log_event(
                    simulation_step=self.model.steps,
                    node_id=self.name,
                    event="REFUSE_task_queue_full",
                    task_id=task.task_id,
                )
            return False

        # ACCEPT -- делегируем в NodeAgent: он ставит задачу в очередь,
        # пишет task.visit(...) в историю и событие task_queued в лог.
        return super().accept_task(task)

    def state_dict(self) -> dict:
        d = super().state_dict()
        # режим ACCEPT/MODIFY -- только когда клапан сам принимает решения;
        # в пассивном режиме он просто передаёт поток, и "ACCEPT" вводил бы в заблуждение
        d["mode"] = self.mode if self.decides else None
        return d