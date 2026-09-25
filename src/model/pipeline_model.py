"""
PipelineModel -- домен "газ/жидкость" поверх той же архитектуры Mesa.

Цепочка агентов: Input -> Pump -> Valve -> Tank -> Output

Pump и Tank -- обычные NodeAgent (как Machine_A/Machine_B в первом домене).
Valve -- по умолчанию ValveAgent (ACCEPT/MODIFY: при перегрузке дросселирует
обработку); класс клапана можно подменить через valve_class, чтобы сравнить
варианты на одинаковых условиях (см. experiments/compare_valves.py).
"""
from mesa import Model

from src.agents.endpoint_agents import InputAgent, OutputAgent
from src.agents.node_agent import NodeAgent
from src.agents.valve_agent import ValveAgent
from src.model.chain_mixin import ChainModelMixin


class PipelineModel(ChainModelMixin, Model):
    def __init__(
        self,
        flow_arrival_interval: int = 1,   # как часто на входе появляется новая "порция" потока
        pump_processing_time: int = 1,    # насос быстрый -- будет создавать давление на клапан
        valve_processing_time: int = 3,   # клапан медленнее насоса -- станет узким местом
        tank_processing_time: int = 1,
        queue_capacity: int = 10,
        valve_safety_threshold: float = 0.5,
        valve_class=ValveAgent,
        valve_kwargs: dict | None = None,  # если задано -- вместо safety_threshold
        decision_mode: str = "passive",   # "passive" -- узлы только передают поток, "autonomous" -- решают сами
        logger=None,
        rng=None,
    ):
        super().__init__(rng=rng)
        self.logger = logger
        self.completed_tasks = 0  # здесь -- количество дошедших до Output "порций потока"

        if valve_kwargs is None:
            valve_kwargs = {"safety_threshold": valve_safety_threshold}

        self.input = InputAgent(self, "Input", arrival_interval=flow_arrival_interval,
                                task_prefix="Flow", logger=logger)
        self.pump = NodeAgent(self, name="Pump", processing_time=pump_processing_time,
                              queue_capacity=queue_capacity, logger=logger)
        self.valve = valve_class(self, name="Valve", processing_time=valve_processing_time,
                                 queue_capacity=queue_capacity, logger=logger, **valve_kwargs)
        self.tank = NodeAgent(self, name="Tank", processing_time=tank_processing_time,
                              queue_capacity=queue_capacity, logger=logger)
        self.output = OutputAgent(self, "Output", logger=logger)

        self._link_chain([self.input, self.pump, self.valve, self.tank, self.output])
        self.set_decision_mode(decision_mode)

    # step / snapshot / trigger_failure / force_recover / add_node -- см. ChainModelMixin.


if __name__ == "__main__":
    # быстрая ручная проверка без логгера и без Ollama: насос быстрее
    # клапана, поэтому на клапане растёт очередь и он переходит в MODIFY.
    model = PipelineModel()
    for i in range(20):
        model.step()
        print(f"--- шаг {i+1} ---")
        for node in model.nodes:
            print(" ", node.state_dict())
