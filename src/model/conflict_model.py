"""
conflict_model.py -- модели КОНФЛИКТА "локальная цель узла vs глобальная цель
системы" на настоящей Mesa (mesa >= 3.0).

Что здесь от Mesa:
  * ConflictModel  наследует mesa.Model  (self.random, self.steps, self.agents)
  * SourceAgent / HubAgent / ZoneAgent наследуют mesa.Agent
  * порядок активации -- через AgentSet:
        self.agents_by_type[ZoneAgent].do("arrive")
        self.agents_by_type[ZoneAgent].shuffle_do("pull")   # случайный порядок
  * метрики собираются mesa.DataCollector (model.datacollector)

Постановка:
  * один ограниченный ресурс (supply за шаг), несколько параллельных зон;
  * ЛОКАЛЬНАЯ цель зоны -- забрать максимум (запрос = min(queue, max_intake));
  * ГЛОБАЛЬНАЯ цель системы -- max  sum(priority_i * sqrt(allocated_i));
  * пока суммарный спрос > supply, цели не совпадают -- конфликт измерим.

Схемы:
  "distributor" -- A. HubAgent-арбитр делит лимит (policy: equal / proportional / priority)
  "shared_tank" -- B. общий резервуар: зоны САМИ тянут (pull) в случайном порядке
  "auction"     -- C. HubAgent-аукционист: доли пропорциональны ставкам
                   bid = запрос * приоритет * (1 + 0.25 * шагов_без_полного_удовлетворения)

Интерфейс для live_server.py: steps, nodes, completed_tasks, trigger_failure,
force_recover, add_node, conflict_metrics(); у узлов -- name, downstream(s), state_dict().
"""
import math

import mesa


# ---------------------------------------------------------------- #
# Чистые функции распределения
# ---------------------------------------------------------------- #
def weighted_waterfill(requests, weights, supply):
    """Делит supply пропорционально weights, никому не больше запроса;
    остаток перераспределяется между остальными."""
    n = len(requests)
    alloc = [0.0] * n
    active = [i for i in range(n) if requests[i] > 1e-9 and weights[i] > 1e-9]
    remaining = float(supply)
    while active and remaining > 1e-9:
        total_w = sum(weights[i] for i in active)
        capped = [i for i in active
                  if alloc[i] + remaining * weights[i] / total_w >= requests[i] - 1e-9]
        if not capped:
            for i in active:
                alloc[i] += remaining * weights[i] / total_w
            break
        for i in capped:
            remaining -= requests[i] - alloc[i]
            alloc[i] = requests[i]
        active = [i for i in active if i not in capped]
    return alloc


def priority_fill(requests, priorities, supply):
    alloc = [0.0] * len(requests)
    remaining = float(supply)
    for i in sorted(range(len(requests)), key=lambda k: -priorities[k]):
        give = min(requests[i], remaining)
        alloc[i] = give
        remaining -= give
    return alloc


# ---------------------------------------------------------------- #
# Агенты (mesa.Agent)
# ---------------------------------------------------------------- #
class ConflictAgent(mesa.Agent):
    """Базовый агент: имя, отказ, состояние для UI."""

    def __init__(self, model, name, kind):
        super().__init__(model)
        self.name = name
        self.kind = kind
        self.downstreams = []
        self.failed_until = 0
        self.state = "idle"
        self.mode = ""
        self.current_task = None
        self.queue = 0.0
        self.load = 0.0

    @property
    def downstream(self):  # совместимость с edges_for() для цепочек
        return self.downstreams[0] if self.downstreams else None

    @property
    def is_failed(self):
        return self.model.steps < self.failed_until

    def state_dict(self):
        return {
            "node": self.name,
            "state": "failed" if self.is_failed else self.state,
            "mode": self.mode,
            "current_task": self.current_task,
            "queue": round(self.queue, 2),
            "load": round(self.load, 2),
        }


class SourceAgent(ConflictAgent):
    def __init__(self, model, name, supply):
        super().__init__(model, name, "source")
        self.supply = supply
        self.produced = 0.0

    def produce(self):
        self.produced = 0.0 if self.is_failed else self.supply
        self.state = "working" if self.produced > 0 else "idle"
        self.mode = "SUPPLY"
        self.load = 1.0 if self.produced > 0 else 0.0
        self.queue = self.produced


class HubAgent(ConflictAgent):
    """Общий узел между источником и зонами: Distributor / Tank / Auctioneer."""

    def __init__(self, model, name, kind, mode, capacity=0.0):
        super().__init__(model, name, kind)
        self.mode = mode          # для distributor -- политика
        self.capacity = capacity  # для tank
        self.level = capacity / 2 if capacity else 0.0
        self.available = 0.0

    # --- фаза 1: сколько ресурса вообще есть в этот шаг ---
    def prepare(self):
        supply = self.model.source.produced
        if self.kind == "tank":
            if not self.is_failed:
                self.level = min(self.capacity, self.level + supply)
            self.available = 0.0 if self.is_failed else self.level
        else:
            self.available = 0.0 if self.is_failed else supply

    # --- фаза 2 (только A и C): центральное решение "кому сколько" ---
    def allocate(self):
        zones = self.model.zones
        reqs = [z.demand for z in zones]
        if self.kind == "distributor":
            prios = [z.priority for z in zones]
            if self.mode == "equal":
                alloc = weighted_waterfill(reqs, [1.0] * len(reqs), self.available)
            elif self.mode == "priority":
                alloc = priority_fill(reqs, prios, self.available)
            else:  # proportional
                alloc = weighted_waterfill(reqs, reqs, self.available)
        else:  # auctioneer
            for z in zones:
                z.bid = z.demand * z.priority * (1 + 0.25 * z.unmet_streak)
            alloc = weighted_waterfill(reqs, [z.bid for z in zones], self.available)
        for z, a in zip(zones, alloc):
            z.grant(a)

    def finish(self):
        """Обновить состояние для UI после раздачи."""
        zones = self.model.zones
        total_demand = sum(z.demand for z in zones)
        supply = self.model.source.produced
        if self.kind == "tank":
            self.queue = self.level
            self.load = self.level / self.capacity if self.capacity else 0.0
        else:
            self.queue = total_demand
            self.load = total_demand / supply if supply > 0 else 0.0
        self.state = "working" if self.available > 0 and not self.is_failed else "idle"

    def state_dict(self):
        d = super().state_dict()
        if self.kind == "tank":
            d["level"] = round(self.level, 2)
            d["capacity"] = self.capacity
        return d


class ZoneAgent(ConflictAgent):
    """Зона со своей ЛОКАЛЬНОЙ целью: забрать как можно больше ресурса."""

    def __init__(self, model, name, priority=1.0, arrival_rate=3.0,
                 capacity=20.0, max_intake=5.0):
        super().__init__(model, name, "zone")
        self.priority = priority
        self.arrival_rate = arrival_rate
        self.capacity = capacity
        self.max_intake = max_intake
        self.demand = 0.0
        self.allocated = 0.0
        self.bid = 0.0
        self.unmet_streak = 0
        self.total_yield = 0.0

    def arrive(self):
        add = max(0.0, self.arrival_rate + self.model.random.choice([-1, 0, 0, 1]))
        self.queue = min(self.capacity, self.queue + add)

    def declare(self):
        """Локальная цель: запросить максимум."""
        self.allocated = 0.0
        self.demand = 0.0 if self.is_failed else min(self.queue, self.max_intake)

    def grant(self, amount):
        self.allocated += amount

    def pull(self):
        """Схема B: зона сама тянет из общего резервуара (без координации)."""
        tank = self.model.hub
        if tank.is_failed:
            return
        take = min(self.demand - self.allocated, tank.level)
        if take > 0:
            tank.level -= take
            self.grant(take)

    def settle(self):
        served = min(self.allocated, self.queue)
        self.allocated = served
        self.queue -= served
        self.total_yield += self.priority * math.sqrt(served)
        if self.demand > 1e-9 and served < self.demand - 1e-9:
            self.unmet_streak += 1
        else:
            self.unmet_streak = 0
        self.load = self.queue / self.capacity
        if self.is_failed:
            self.mode = "FAILED"
        elif self.demand <= 1e-9:
            self.mode = "NO DEMAND"
        elif served >= self.demand - 1e-9:
            self.mode = "FULL"
        elif served > 1e-9:
            self.mode = "PARTIAL"
        else:
            self.mode = "STARVED"
        self.state = "working" if served > 1e-9 else "idle"

    def state_dict(self):
        d = super().state_dict()
        d.update({
            "priority": self.priority,
            "demand": round(self.demand, 2),
            "allocated": round(self.allocated, 2),
            "deficit": round(self.demand - self.allocated, 2),
            "total_yield": round(self.total_yield, 2),
        })
        if self.bid:
            d["bid"] = round(self.bid, 2)
        return d


# ---------------------------------------------------------------- #
# Модель (mesa.Model)
# ---------------------------------------------------------------- #
DEFAULT_ZONES = [
    dict(name="Zone1", priority=1.0, arrival_rate=3.0),
    dict(name="Zone2", priority=2.0, arrival_rate=3.0),
    dict(name="Zone3", priority=1.0, arrival_rate=4.0),
]

SCHEME_INFO = {
    "distributor": {
        "title": "A. Арбитр (Distributor)",
        "mechanism": "Центральный распределитель делит лимит между ветками.",
    },
    "shared_tank": {
        "title": "B. Общий резервуар (конкурентный pull)",
        "mechanism": "Координатора нет: зоны сами тянут из Tank в случайном порядке.",
    },
    "auction": {
        "title": "C. Аукцион",
        "mechanism": "Ставка = запрос x приоритет x (1 + 0.25 x шагов без полного удовлетворения); "
                     "ресурс делится пропорционально ставкам.",
    },
}


class ConflictModel(mesa.Model):
    def __init__(self, scheme="distributor", policy="proportional",
                 supply=6.0, tank_capacity=12.0, seed=42, zones=None):
        try:
            super().__init__(rng=seed)      # Mesa >= 3.4
        except TypeError:
            super().__init__(seed=seed)     # Mesa 3.0-3.3
        if scheme not in SCHEME_INFO:
            raise ValueError(f"unknown scheme '{scheme}'")
        self.scheme = scheme
        self.policy = policy
        self.supply = supply
        self.total_served = 0.0
        self.cum_yield = 0.0
        self.cum_optimal = 0.0
        self.cum_wasted = 0.0

        # агенты создаются с model=self -> Mesa сама регистрирует их в self.agents
        self.source = SourceAgent(self, "Source", supply)
        if scheme == "distributor":
            self.hub = HubAgent(self, "Distributor", "distributor", policy)
        elif scheme == "shared_tank":
            self.hub = HubAgent(self, "SharedTank", "tank", "SHARED", tank_capacity)
        else:
            self.hub = HubAgent(self, "Auctioneer", "auctioneer", "AUCTION")
        self.zones = [ZoneAgent(self, **z) for z in (zones or DEFAULT_ZONES)]

        self.source.downstreams = [self.hub]
        self.hub.downstreams = list(self.zones)
        self.nodes = [self.source, self.hub] + self.zones

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "total_demand": lambda m: sum(z.demand for z in m.zones),
                "total_allocated": lambda m: sum(z.allocated for z in m.zones),
                "deficit": lambda m: sum(z.demand - z.allocated for z in m.zones),
                "efficiency": lambda m: m.efficiency,
                "fairness": lambda m: m.fairness,
            },
        )

    # --- совместимость с live_server ----------------------------- #
    @property
    def completed_tasks(self):
        return int(self.total_served)

    def _find(self, name):
        for n in self.nodes:
            if n.name == name:
                return n
        raise KeyError(f"нет узла '{name}'")

    def trigger_failure(self, node_name, duration):
        # Mesa увеличивает model.steps ДО вызова step(), поэтому +1: ровно duration шагов отказа
        self._find(node_name).failed_until = self.steps + 1 + duration

    def force_recover(self, node_name):
        self._find(node_name).failed_until = 0

    def add_node(self, *args, **kwargs):
        raise ValueError("В конфликтных моделях добавление узлов пока не поддерживается "
                         "-- переключитесь на pipeline/factory.")

    # --- метрики ------------------------------------------------- #
    @property
    def efficiency(self):
        return self.cum_yield / self.cum_optimal if self.cum_optimal > 1e-9 else 1.0

    @property
    def fairness(self):
        """Индекс Джайна по доле удовлетворённого спроса."""
        ratios = [z.allocated / z.demand for z in self.zones if z.demand > 1e-9]
        sq = sum(x * x for x in ratios)
        return sum(ratios) ** 2 / (len(ratios) * sq) if ratios and sq > 0 else 1.0

    # --- один шаг: стадийная активация через AgentSet ------------- #
    def step(self):
        zone_set = self.agents_by_type[ZoneAgent]

        self.agents_by_type[SourceAgent].do("produce")   # 1. источник
        zone_set.do("arrive")                            # 2. приходит потребность
        zone_set.do("declare")                           # 3. локальная цель: запрос
        self.hub.prepare()                               # 4. сколько ресурса доступно

        # эталон глобального оптимума для sum(w*sqrt(x)):  x_i ~ w_i^2
        opt = weighted_waterfill([z.demand for z in self.zones],
                                 [z.priority ** 2 for z in self.zones], self.hub.available)
        self.cum_optimal += sum(z.priority * math.sqrt(x) for z, x in zip(self.zones, opt))

        if self.scheme == "shared_tank":
            zone_set.shuffle_do("pull")                  # 5B. никто не координирует
        else:
            self.hub.allocate()                          # 5A/C. центральное решение

        zone_set.do("settle")                            # 6. зоны забирают выданное
        self.hub.finish()

        allocated = sum(z.allocated for z in self.zones)
        self.total_served += allocated
        self.cum_yield += sum(z.priority * math.sqrt(z.allocated) for z in self.zones)
        if self.scheme != "shared_tank":
            self.cum_wasted += max(0.0, self.hub.available - allocated)
        self.datacollector.collect(self)                 # 7. метрики

    def conflict_metrics(self):
        zones = self.zones
        reqs = [z.demand for z in zones]
        alloc = [z.allocated for z in zones]
        info = SCHEME_INFO[self.scheme]
        title = info["title"] + (f" -- {self.policy}" if self.scheme == "distributor" else "")
        return {
            "title": title,
            "mechanism": info["mechanism"],
            "local_goal": "каждая зона: забрать максимум ресурса себе",
            "global_goal": "система: максимум sum(приоритет x sqrt(выделено))",
            "supply": round(self.source.produced, 2),
            "available": round(self.hub.available, 2),
            "total_demand": round(sum(reqs), 2),
            "total_allocated": round(sum(alloc), 2),
            "deficit": round(sum(reqs) - sum(alloc), 2),
            "cum_wasted": round(self.cum_wasted, 2),
            "cum_yield": round(self.cum_yield, 2),
            "cum_optimal": round(self.cum_optimal, 2),
            "efficiency": round(self.efficiency, 3),
            "fairness": round(self.fairness, 3),
            "tank_level": round(self.hub.level, 2) if self.scheme == "shared_tank" else None,
            "zones": [
                {"name": z.name, "priority": z.priority, "demand": round(z.demand, 2),
                 "allocated": round(z.allocated, 2),
                 "deficit": round(z.demand - z.allocated, 2),
                 "bid": round(z.bid, 2) if z.bid else None}
                for z in zones
            ],
        }