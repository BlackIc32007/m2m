"""
InputAgent / OutputAgent -- концы цепочки как полноценные Mesa-агенты.

Раньше Input был методом модели (_maybe_spawn_task), а Output -- просто
счётчиком. Теперь каждый объект схемы из задания

    Input -> Machine A -> Buffer -> Machine B -> Output

-- отдельный mesa.Agent со своим состоянием, шагом и возможностью отказа.

Оба наследуют NodeAgent, чтобы переиспользовать состояние, журналирование,
fail()/recover_now() и state_dict(), но у них нет своей очереди
(queue_capacity=0).
"""
import itertools

from src.agents.node_agent import NodeAgent
from src.agents.task import Task


class InputAgent(NodeAgent):
    """Источник задач: раз в arrival_interval шагов создаёт Task и отдаёт
    её первому узлу цепочки. Если первый узел её не принял (очередь полна
    или отказ), задача считается не поступившей в систему (dropped).
    Пока Input в отказе, новые задачи не появляются."""

    is_endpoint = True

    def __init__(self, model, name: str = "Input", arrival_interval: int = 2,
                 task_prefix: str = "Task", downstream=None, logger=None):
        super().__init__(model, name, processing_time=0, queue_capacity=0,
                         downstream=downstream, logger=logger)
        self.arrival_interval = arrival_interval
        self.task_prefix = task_prefix
        self._task_counter = itertools.count(1)
        self.generated = 0
        self.dropped = 0
        self.state = self._resume_state()

    def _resume_state(self) -> str:
        return "working" if self.arrival_interval > 0 else "idle"

    def accept_task(self, task) -> bool:
        return False  # в источник задачи не приходят

    def step(self) -> None:
        if self.state == "failed":
            super().step()  # отсчёт отказа и восстановление -- как у любого узла
            return
        if self.arrival_interval <= 0 or self.model.steps % self.arrival_interval != 0:
            return

        task = Task(task_id=f"{self.task_prefix}_{next(self._task_counter)}",
                    created_step=self.model.steps)
        self.generated += 1
        if self.logger:
            self.logger.log_event(simulation_step=self.model.steps, node_id=self.name,
                                  event="task_created", task_id=task.task_id)
        if not (self.downstreams and self._forward_task(task)):
            self.dropped += 1
            if self.logger:
                self.logger.log_event(simulation_step=self.model.steps, node_id=self.name,
                                      event="task_dropped_queue_full", task_id=task.task_id)

    def state_dict(self) -> dict:
        d = super().state_dict()
        d["generated"] = self.generated
        d["dropped"] = self.dropped
        return d


class OutputAgent(NodeAgent):
    """Сток: принимает готовые задачи и считает их (model.completed_tasks).
    В отказе не принимает ничего -- последний узел цепочки блокируется,
    и затор распространяется назад."""

    is_endpoint = True

    def __init__(self, model, name: str = "Output", logger=None):
        super().__init__(model, name, processing_time=0, queue_capacity=0, logger=logger)
        self.received = 0
        self._total_lead_time = 0
        self.last_task = None

    def accept_task(self, task) -> bool:
        if self.state == "failed":
            return False
        task.visit(self.name, self.model.steps)
        self.received += 1
        self._total_lead_time += self.model.steps - task.created_step
        self.last_task = task.task_id
        self.model.completed_tasks += 1
        if self.logger:
            self.logger.log_event(simulation_step=self.model.steps, node_id=self.name,
                                  event="task_output", task_id=task.task_id)
        return True

    def step(self) -> None:
        if self.state == "failed":
            super().step()

    def state_dict(self) -> dict:
        d = super().state_dict()
        d["received"] = self.received
        d["last_task"] = self.last_task
        d["avg_lead_time"] = round(self._total_lead_time / self.received, 2) if self.received else None
        return d
