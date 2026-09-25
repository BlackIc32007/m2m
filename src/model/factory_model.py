"""
FactoryModel -- минимальный демонстрационный стенд из задания.

Цепочка агентов (каждый -- mesa.Agent):
    Input -> Machine A -> Buffer -> Machine B -> Output

Input  -- InputAgent, раз в task_arrival_interval шагов создаёт Task.
Output -- OutputAgent, принимает готовые задачи и считает их.
Machine A, Buffer, Machine B -- NodeAgent с очередью и состоянием.
"""
from mesa import Model

from src.agents.endpoint_agents import InputAgent, OutputAgent
from src.agents.node_agent import NodeAgent
from src.model.chain_mixin import ChainModelMixin


class FactoryModel(ChainModelMixin, Model):
    def __init__(
        self,
        task_arrival_interval: int = 2,   # раз в сколько шагов на входе появляется новая задача
        processing_time: int = 2,         # сколько шагов узел обрабатывает одну задачу
        queue_capacity: int = 10,
        logger=None,
        rng=None,
    ):
        super().__init__(rng=rng)
        self.logger = logger
        self.completed_tasks = 0  # увеличивает OutputAgent

        self.input = InputAgent(self, "Input", arrival_interval=task_arrival_interval,
                                task_prefix="Task", logger=logger)
        self.machine_a = NodeAgent(self, name="Machine_A", processing_time=processing_time,
                                   queue_capacity=queue_capacity, logger=logger)
        self.buffer = NodeAgent(self, name="Buffer", processing_time=1,  # буфер почти не обрабатывает, просто передаёт
                                queue_capacity=queue_capacity, logger=logger)
        self.machine_b = NodeAgent(self, name="Machine_B", processing_time=processing_time,
                                   queue_capacity=queue_capacity, logger=logger)
        self.output = OutputAgent(self, "Output", logger=logger)

        self._link_chain([self.input, self.machine_a, self.buffer, self.machine_b, self.output])

    # step / snapshot / trigger_failure / force_recover / add_node -- см. ChainModelMixin.
