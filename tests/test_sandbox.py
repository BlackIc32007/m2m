"""
Проверки песочницы: удаление и добавление узлов на ходу, изменение
параметров узлов (src/simulation/sandbox.py) и API веб-интерфейса.

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.model.conflict_model import ConflictModel, ZoneAgent
from src.model.factory_model import FactoryModel
from src.simulation import sandbox


class TestChainRemove(unittest.TestCase):
    def test_remove_rewires_and_keeps_tasks(self):
        m = FactoryModel(rng=1)
        for _ in range(12):
            m.step()
        held = len(m.buffer.queue) + (1 if m.buffer.current_task else 0)
        lost = m.remove_node("Buffer")
        self.assertEqual([d.name for d in m.machine_a.downstreams], ["Machine_B"])
        self.assertNotIn(m.buffer, m.agents)          # снят с регистрации в Mesa
        self.assertLessEqual(lost, held)
        done = m.completed_tasks
        for _ in range(30):
            m.step()
        self.assertGreater(m.completed_tasks, done)   # поток идёт дальше

    def test_endpoints_cannot_be_removed(self):
        m = FactoryModel(rng=1)
        for name in ("Input", "Output"):
            with self.assertRaises(ValueError):
                m.remove_node(name)


class TestConflictZones(unittest.TestCase):
    def test_added_zone_gets_water_and_removed_zone_stops(self):
        m = ConflictModel("distributor", policy="equal", supply=9, seed=0)
        m.step()
        m.add_zone("Zone4", priority=2, arrival_rate=3)
        for _ in range(20):
            m.step()
        z4 = next(z for z in m.zones if z.name == "Zone4")
        self.assertGreater(z4.total_served, 0)
        m.remove_node("Zone1")
        self.assertEqual(len(m.agents_by_type[ZoneAgent]), 3)
        for _ in range(5):
            m.step()
        self.assertEqual([z.name for z in m.zones], ["Zone2", "Zone3", "Zone4"])

    def test_cannot_remove_hub_or_last_zone(self):
        m = ConflictModel("auction", seed=0)
        with self.assertRaises(ValueError):
            m.remove_node("Auctioneer")
        m.remove_node("Zone1")
        m.remove_node("Zone2")
        with self.assertRaises(ValueError):
            m.remove_node("Zone3")
        with self.assertRaises(ValueError):
            m.add_zone("Zone3")                       # имя занято


class TestParams(unittest.TestCase):
    def test_validation_is_all_or_nothing(self):
        m = FactoryModel(rng=1)
        node = m.machine_a
        with self.assertRaises(ValueError):
            sandbox.apply_params(node, {"processing_time": 3, "queue_capacity": 1000})
        self.assertEqual(node.processing_time, 2)     # ничего не применилось
        with self.assertRaises(ValueError):
            sandbox.apply_params(node, {"resume_threshold": 0.9})   # выше stop_threshold
        with self.assertRaises(ValueError):
            sandbox.apply_params(node, {"unknown": 1})
        sandbox.apply_params(node, {"processing_time": "3"})
        self.assertEqual(node.processing_time, 3)

    def test_distributor_rule_switch_updates_model(self):
        m = ConflictModel("distributor", policy="proportional", seed=0)
        sandbox.apply_params(m.hub, {"mode": "equal"})
        self.assertEqual((m.hub.mode, m.policy), ("equal", "equal"))
        self.assertIn("equal", m.conflict_metrics()["title"])

    def test_zone_capacity_shrink_counts_lost_demand(self):
        m = ConflictModel("distributor", supply=3, seed=0)
        for _ in range(20):
            m.step()
        z = m.zones[0]
        before = z.queue
        sandbox.apply_params(z, {"capacity": 5})
        self.assertLessEqual(z.queue, 5)
        self.assertGreaterEqual(z.lost_demand, before - 5)


class TestApi(unittest.TestCase):
    def test_sandbox_endpoints(self):
        import live_server
        c = live_server.app.test_client()
        r = c.post("/api/reset", json={"model_name": "conflict_auction", "params": {"supply": 9}})
        self.assertEqual(r.json["model_params"]["supply"], 9.0)
        r = c.post("/api/step", json={"n": 5})
        self.assertEqual(len(r.json["history"]), 6)
        self.assertEqual(c.post("/api/node_params", json={"node": "Zone1", "params": {"priority": 99}}).status_code, 400)
        r = c.post("/api/add_node", json={"class_name": "ZoneAgent", "name": "Zone4", "params": {"priority": 2}})
        self.assertIn("Zone4", [n["node"] for n in r.json["nodes"]])
        self.assertEqual(c.post("/api/remove_node", json={"node": "Source"}).status_code, 400)
        self.assertEqual(c.post("/api/fail", json={"node": "Zone1", "duration": 0}).status_code, 400)
        self.assertEqual(c.post("/api/reset", json={"model_name": "factory",
                                                    "params": {"processing_time": "x"}}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
