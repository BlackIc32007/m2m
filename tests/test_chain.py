"""
Проверки цепочек (FactoryModel, PipelineModel): сохранение задач, отказы,
решения узлов в автономном режиме, ветвление.

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.node_agent import NodeAgent
from src.agents.valve_agent_fixed import ValveAgentModify, ValveAgentRefuse
from src.model.factory_model import FactoryModel
from src.model.pipeline_model import PipelineModel


def in_system(m):
    return sum(len(n.queue) + (n.current_task is not None) for n in m.nodes)


class ConservationMixin:
    def assertConserved(self, m):
        self.assertEqual(m.input.generated, m.completed_tasks + in_system(m) + m.input.dropped)


class TestConservation(unittest.TestCase, ConservationMixin):
    def test_all_models_modes_and_valves(self):
        for mode in ("passive", "autonomous"):
            for m in (FactoryModel(task_arrival_interval=1, decision_mode=mode),
                      PipelineModel(decision_mode=mode),
                      PipelineModel(decision_mode=mode, valve_class=ValveAgentRefuse,
                                    valve_kwargs={"safety_threshold": 0.5}),
                      PipelineModel(decision_mode=mode, valve_class=ValveAgentModify,
                                    valve_kwargs={"safety_threshold": 0.5})):
                for t in range(150):
                    if t == 20:
                        m.trigger_failure(m.nodes[2].name, 10)
                    if t == 60:
                        m.trigger_failure("Output", 5)
                    m.step()
                    self.assertConserved(m)


class TestFailures(unittest.TestCase, ConservationMixin):
    def test_interrupted_task_is_resumed(self):
        m = FactoryModel(task_arrival_interval=1, processing_time=3)
        for _ in range(3):
            m.step()
        task = m.machine_a.current_task
        m.trigger_failure("Machine_A", 2)
        m.step()
        self.assertIs(m.machine_a.current_task, task)  # задача не потеряна во время отказа
        for _ in range(30):
            m.step()
        self.assertIn("Output", [v["node"] for v in task.history])  # и в итоге дошла до конца

    def test_output_failure_blocks_back_pressure(self):
        m = FactoryModel()
        m.trigger_failure("Output", 30)
        for _ in range(12):
            m.step()
        self.assertEqual(m.machine_b.state, "blocked")
        self.assertEqual(m.completed_tasks, 0)

    def test_force_recover_on_working_node_keeps_task(self):
        m = FactoryModel(task_arrival_interval=1, processing_time=3)
        for _ in range(3):
            m.step()
        task = m.machine_a.current_task
        m.force_recover("Machine_A")  # узел не в отказе -- ничего не должно измениться
        self.assertEqual(m.machine_a.state, "working")
        self.assertIs(m.machine_a.current_task, task)

    def test_unknown_node(self):
        with self.assertRaises(ValueError):
            FactoryModel().trigger_failure("Nope", 3)


class TestDecisions(unittest.TestCase):
    def test_passive_nodes_never_refuse(self):
        m = FactoryModel(task_arrival_interval=1)
        m.trigger_failure("Machine_B", 20)
        for _ in range(40):
            m.step()
            self.assertTrue(all(n.state_dict().get("decision") in (None,) for n in m.nodes))

    def test_autonomous_node_refuses_when_downstream_failed(self):
        m = FactoryModel(task_arrival_interval=1, decision_mode="autonomous")
        m.step()
        m.trigger_failure("Machine_B", 20)
        m.step()
        self.assertEqual(m.buffer.state_dict()["decision"], "REFUSE")
        for _ in range(30):
            m.step()
        self.assertEqual(m.buffer.state_dict()["decision"], "ACCEPT")

    def test_valve_is_plain_pipe_in_passive_mode(self):
        m = PipelineModel(decision_mode="passive")
        for _ in range(40):
            m.step()
        self.assertEqual(m.valve.processing_time, 3)
        self.assertIsNone(m.valve.state_dict().get("mode"))

    def test_valve_throttles_in_autonomous_mode(self):
        m = PipelineModel(decision_mode="autonomous")
        for _ in range(40):
            m.step()
        self.assertEqual(m.valve.state_dict()["mode"], "MODIFY")

    def test_switching_modes_live(self):
        m = PipelineModel(decision_mode="autonomous", valve_class=ValveAgentRefuse,
                          valve_kwargs={"safety_threshold": 0.5})
        for _ in range(100):
            m.step()
            if m.valve.throttled:
                break
        self.assertTrue(m.valve.throttled)
        m.set_decision_mode("passive")
        m.step()
        self.assertFalse(m.valve.throttled)  # в пассивном режиме клапан больше не отказывает


class TestBranchCollision(unittest.TestCase):
    """Единственная коллизия в цепочке: узел с несколькими приёмниками делит
    поток. Делёж -- по кругу, отказавшая ветка пробуется последней."""

    def test_round_robin_split(self):
        class Log:
            def __init__(self):
                self.queued = {}

            def log_event(self, node_id, event, **kw):
                if event == "task_queued":
                    self.queued[node_id] = self.queued.get(node_id, 0) + 1

            def log_state_change(self, **kw):
                pass

        log = Log()
        # насос не быстрее приёмников -- ни одна ветка не переполняется, и делёж
        # определяется только чередованием
        m = PipelineModel(flow_arrival_interval=3, valve_processing_time=1, logger=log)
        m.add_node(NodeAgent, "Bypass", insert_after="Pump", mode="branch",
                   extra_kwargs={"processing_time": 1})
        for _ in range(120):
            m.step()
        self.assertLessEqual(abs(log.queued["Valve"] - log.queued["Bypass"]), 1, log.queued)

    def test_failed_branch_is_bypassed(self):
        m = PipelineModel()
        bypass = m.add_node(NodeAgent, "Bypass", insert_after="Pump", mode="branch")
        m.trigger_failure("Valve", 1000)
        for _ in range(60):
            m.step()
        # поток ушёл в живую ветку: ~1 задача за 3 шага (обработка 2 шага + передача),
        # а через отказавший Valve до Tank не прошло ничего
        self.assertGreaterEqual(m.completed_tasks, 15)
        self.assertEqual(m.tank.state, "idle")
        self.assertIsNone(m.tank.current_task)


if __name__ == "__main__":
    unittest.main()
