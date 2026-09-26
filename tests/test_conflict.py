"""
Проверки модели конфликта (ConflictModel): распределение, коллизии,
конфликт целей, отказы, учёт воды и метрики.

    python -m unittest discover -s tests -v
"""
import itertools
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.model.conflict_model import ConflictModel, priority_fill, weighted_waterfill
from src.model.zone_policies import Decision

SCHEMES = [("distributor", "proportional"), ("distributor", "equal"), ("distributor", "priority"),
           ("shared_tank", "proportional"), ("auction", "proportional")]
EPS = 1e-9


def models(mode="passive", seeds=range(3)):
    for (scheme, policy), seed in itertools.product(SCHEMES, seeds):
        yield ConflictModel(scheme, policy=policy, seed=seed, decision_mode=mode)


class TestAllocationFunctions(unittest.TestCase):
    def test_waterfill_properties(self):
        rnd = random.Random(1)
        for _ in range(2000):
            n = rnd.randint(1, 5)
            req = [rnd.choice([0, rnd.uniform(0, 10)]) for _ in range(n)]
            w = [rnd.uniform(0.1, 3) for _ in range(n)]
            supply = rnd.uniform(0, 30)
            a = weighted_waterfill(req, w, supply)
            self.assertAlmostEqual(sum(a), min(supply, sum(req)), places=6)
            for ai, ri in zip(a, req):
                self.assertGreaterEqual(ai, -EPS)
                self.assertLessEqual(ai, ri + 1e-6)
            # незаполненные получают доли строго пропорционально весам
            free = [i for i in range(n) if a[i] < req[i] - 1e-6]
            for i, j in itertools.combinations(free, 2):
                self.assertAlmostEqual(a[i] / w[i], a[j] / w[j], places=5)

    def test_priority_fill_serves_higher_first(self):
        self.assertEqual(priority_fill([5, 5, 5], [1, 2, 1], 6), [1.0, 5.0, 0.0])

    def test_priority_fill_ties_are_not_fixed_by_index(self):
        """Коллизия зон с одинаковым приоритетом не должна всегда решаться в
        пользу зоны, стоящей раньше в списке."""
        wins = {0: 0, 2: 0}
        for seed in range(200):
            a = priority_fill([5, 5, 5], [1, 2, 1], 6, rng=random.Random(seed))
            wins[0 if a[0] > a[2] else 2] += 1
        self.assertGreater(min(wins.values()), 60, wins)


class TestCollisions(unittest.TestCase):
    """Коллизия: несколько зон одновременно претендуют на воду, которой не
    хватает. Проверяем, кто и сколько получает в каждой схеме."""

    def run_model(self, scheme, policy="proportional", steps=300, seed=0):
        m = ConflictModel(scheme, policy=policy, seed=seed)
        for _ in range(steps):
            m.step()
        return m

    def test_demand_exceeds_supply_every_step(self):
        m = ConflictModel("distributor", seed=0)
        for _ in range(50):
            m.step()
            self.assertGreater(sum(z.need for z in m.zones), m.hub.available)

    def test_equal_zones_with_equal_priority_get_similar_share_under_priority(self):
        """Zone1 и Zone3 (приоритет 1 у обеих) должны делить остаток поровну --
        при любом сиде, в обоих режимах и после переключения режима на ходу
        (в автономном режиме REFUSE сбивает зонам счётчики нехватки)."""
        for seed in range(8):
            for mode in ("passive", "autonomous", "switch"):
                m = ConflictModel("distributor", policy="priority", seed=seed,
                                  decision_mode="passive" if mode == "passive" else "autonomous")
                for t in range(300):
                    if mode == "switch" and t == 20:
                        m.set_decision_mode("passive")
                    m.step()
                z1, z3 = m.zones[0], m.zones[2]
                ratio = min(z1.total_served, z3.total_served) / max(z1.total_served, z3.total_served)
                self.assertGreater(ratio, 0.8, (seed, mode, z1.total_served, z3.total_served))

    def test_shared_tank_order_is_random(self):
        """В общем баке первым тянет случайная зона, а не всегда одна и та же."""
        m = ConflictModel("shared_tank", seed=0)
        first_full = set()
        for _ in range(100):
            m.step()
            full = [z.name for z in m.zones if z.mode == "FULL"]
            first_full.update(full)
        self.assertEqual(first_full, {"Zone1", "Zone2", "Zone3"})

    def test_higher_priority_wins_under_priority_and_auction(self):
        for scheme, policy in (("distributor", "priority"), ("auction", "proportional")):
            m = self.run_model(scheme, policy)
            z1, z2 = m.zones[0], m.zones[1]
            self.assertGreater(z2.total_yield / z2.priority, z1.total_yield / z1.priority, scheme)


class TestConflict(unittest.TestCase):
    """Конфликт: локальная цель зон (запросить/урвать) против глобальной
    (максимум sum(p*sqrt(x))). Эффективность -- мера этого разрыва."""

    def test_efficiency_never_exceeds_optimum(self):
        for mode in ("passive", "autonomous"):
            for m in models(mode):
                for _ in range(120):
                    m.step()
                    self.assertLessEqual(m.cum_yield, m.cum_optimal + 1e-6)
                self.assertLessEqual(m.efficiency, 1.0 + 1e-9)

    def test_inflation_harms_only_where_mechanism_allows(self):
        def eff(scheme, policy, mode):
            vals = []
            for s in range(5):
                m = ConflictModel(scheme, policy=policy, seed=s, decision_mode=mode)
                for _ in range(150):
                    m.step()
                vals.append(m.efficiency)
            return sum(vals) / len(vals)
        # пропорциональный распределитель нейтрализует завышение запросов
        self.assertAlmostEqual(eff("distributor", "proportional", "passive"),
                               eff("distributor", "proportional", "autonomous"), delta=0.01)
        # схема по приоритету -- нет
        self.assertLess(eff("distributor", "priority", "autonomous"),
                        eff("distributor", "priority", "passive") - 0.03)


class TestWaterAccounting(unittest.TestCase):
    """Вода не появляется из ниоткуда и не исчезает бесследно."""

    def test_conservation(self):
        for mode in ("passive", "autonomous"):
            for m in models(mode):
                produced = 0.0
                level0 = m.hub.level if m.scheme == "shared_tank" else 0.0
                for step in range(150):
                    if step == 30:
                        m.trigger_failure(m.hub.name, 5)
                    if step == 60:
                        m.trigger_failure("Source", 3)
                    m.step()
                    produced += m.source.produced
                level = m.hub.level if m.scheme == "shared_tank" else 0.0
                self.assertAlmostEqual(produced + level0, m.total_served + m.cum_wasted + level, places=6,
                                       msg=f"{m.scheme}/{m.policy}/{mode}")

    def test_zone_queue_bounds_and_lost_demand(self):
        for m in models():
            arrived = 0.0
            q0 = sum(z.queue for z in m.zones)
            for _ in range(100):
                before = [z.queue for z in m.zones]
                m.step()
                for z in m.zones:
                    self.assertGreaterEqual(z.queue, -EPS)
                    self.assertLessEqual(z.queue, z.capacity + EPS)
            served = sum(z.total_served for z in m.zones)
            lost = sum(z.lost_demand for z in m.zones)
            arrived = sum(z.total_arrived for z in m.zones)
            self.assertAlmostEqual(q0 + arrived, served + lost + sum(z.queue for z in m.zones), places=6)


class TestFailures(unittest.TestCase):
    def test_failure_lasts_exactly_duration_steps(self):
        m = ConflictModel("distributor", seed=0)
        m.step()
        m.trigger_failure("Zone2", 3)
        seen = []
        for _ in range(5):
            m.step()
            seen.append(m.zones[1].mode)
        self.assertEqual(seen[:3], ["FAILED"] * 3)
        self.assertNotEqual(seen[3], "FAILED")

    def test_failed_zone_gets_nothing_and_force_recover(self):
        m = ConflictModel("auction", seed=0)
        m.trigger_failure("Zone1", float("inf"))
        for _ in range(10):
            m.step()
            self.assertEqual(m.zones[0].allocated, 0.0)
        m.force_recover("Zone1")
        m.step()
        self.assertGreater(m.zones[0].allocated, 0.0)

    def test_unknown_node_raises_value_error(self):
        m = ConflictModel("distributor", seed=0)
        with self.assertRaises(ValueError):
            m.trigger_failure("NoSuchZone", 3)
        with self.assertRaises(ValueError):
            m.force_recover("NoSuchZone")


class TestDecisions(unittest.TestCase):
    def test_refuse_frees_water_for_others(self):
        class RefuseZone1:
            def decide(self, z):
                if z.name == "Zone1":
                    return Decision("REFUSE", 0.0, "тест")
                return Decision("ACCEPT", z.need, "тест")
        m = ConflictModel("distributor", seed=0, decision_mode="autonomous", zone_policy=RefuseZone1())
        for _ in range(5):
            m.step()
            self.assertEqual(m.zones[0].allocated, 0.0)
            self.assertEqual(m.zones[0].mode, "YIELDED")

    def test_completed_is_rounded_not_truncated(self):
        m = ConflictModel("distributor", seed=0)
        m.total_served = 5.9
        self.assertEqual(m.completed_tasks, 6)


if __name__ == "__main__":
    unittest.main()
