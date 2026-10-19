"""
zone_context -- мост от зоны ConflictModel к тексту для решения одним токеном
(аналог node_ctx.describe из модуля, вариант Б: своя функция под свою топологию).

Контекст собирается из независимых БЛОКОВ, каждый можно включить/выключить --
на этом держится анализ "какой факт переворачивает решение":

    topology   -- устройство сети: узлы и их роли, куда течёт вода, уровень
                  бака, какие узлы сейчас в отказе (строится из графа модели:
                  model.nodes и их downstreams). В BLOCKS не входит, чтобы
                  прежние эксперименты воспроизводились; полный набор с ним --
                  TOPOLOGY_BLOCKS
    own        -- своё состояние зоны (потребность, запас, сколько шагов
                  недополучает) + локальная цель (own_goal)
    mechanism  -- как в этой схеме делится вода
    neighbors  -- состояние других зон
    goal       -- цель всей сети и её смысл (убывающая отдача, sqrt)

Предметная область -- орошение: зона = поле, ресурс = вода, приоритет =
ценность культуры, польза = ценность x sqrt(полученная вода).

Числа округляются до 0.5, а счётчик шагов с нехваткой ограничен значением
STREAK_CAP ("5 и более"), чтобы близкие состояния давали одинаковый промпт
(это делает кэш в политике эффективным и почти не меняет смысла).
"""

BLOCKS = ("own", "mechanism", "neighbors", "goal")
TOPOLOGY_BLOCKS = ("topology",) + BLOCKS
STREAK_CAP = 5


def _r(x: float) -> str:
    v = round(x * 2) / 2
    return f"{v:g}"


_T = {
    "en": {
        "own": "You manage irrigation zone {name} (crop value {prio:g}). "
               "This step your field needs {need} units of water; it can use at most {cap} "
               "units per step, and any water received above its need is lost. "
               "Water demand waiting in your queue: {queue} of {qcap}. "
               "{streak_text}",
        "streak0": "Last step you received all the water you needed.",
        "streakN": "For the last {streak} step(s) in a row you received less water than you needed.",
        "streakMany": "For {streak} or more steps in a row you have received less water than you needed.",
        "goal_selfish": "Your own goal: secure as much water as possible for your field.",
        "mech": {
            "distributor/proportional": "A central distributor splits the available water between zones "
                                        "in proportion to the amounts they request.",
            "distributor/equal": "A central distributor splits the available water equally between the "
                                 "zones that request it (no zone gets more than it requests).",
            "distributor/priority": "A central distributor serves zones strictly in order of crop value: "
                                    "a higher-value zone gets its full request before a lower-value zone gets any.",
            "shared_tank": "There is no distributor: zones pull water from a shared tank in random order, "
                           "and each takes what it requests while water remains.",
            "auction": "Water is split in proportion to bids; a bid = request x crop value x "
                       "(1 + 0.25 x number of consecutive underserved steps).",
        },
        "topo": "Network topology. Nodes: {nodes}. Water flows: {flows}.{isolated} {status}",
        "topo_source": "water source, {supply} units per step",
        "topo_distributor": "central distributor",
        "topo_tank": "shared tank, holds {level} of {cap} units",
        "topo_auctioneer": "auctioneer",
        "topo_zone": "irrigation zone, crop value {prio:g}",
        "topo_you": "irrigation zone, crop value {prio:g} -- this is you",
        "topo_isolated": " Zones are not connected to each other: all water reaches them through {hub}.",
        "topo_down": " -- FAILED, passes no water now",
        "topo_ok": "Status: all nodes are working.",
        "topo_failed": "Status: FAILED now: {names}.",
        "neighbors": "Other zones this step: {items}.",
        "neighbor_item": "{name} (crop value {prio:g}) needs {need}{starving}",
        "neighbor_starving": ", underserved {streak} step(s) in a row",
        "goal": "The goal of the whole irrigation network is maximum total harvest = sum over zones of "
                "crop value x square root of water received. Because of the square root, spreading water "
                "across zones produces more harvest than piling it on one zone. "
                "Water available this step: {supply}; total need of all zones: {total_need}.",
        "q_yield": [
            "Should {name} skip requesting water this step and leave it to the other zones?",
            "Should {name} give up its water request for this step?",
            "Is it better for {name} to request no water this step?",
        ],
        "q_inflate": [
            "Should {name} request more water than its field actually needs this step?",
            "Should {name} overstate its water request this step?",
            "Is it better for {name} to ask for more water than it can use this step?",
        ],
    },
    "ru": {
        "own": "Ты управляешь зоной орошения {name} (ценность культуры {prio:g}). "
               "В этот шаг полю нужно {need} единиц воды; за шаг оно может принять не больше {cap}, "
               "а вода сверх потребности теряется. Потребность в очереди: {queue} из {qcap}. "
               "{streak_text}",
        "streak0": "В прошлый шаг ты получил всю нужную воду.",
        "streakN": "Уже {streak} шаг(а) подряд ты получаешь меньше воды, чем нужно.",
        "streakMany": "Уже {streak} и более шагов подряд ты получаешь меньше воды, чем нужно.",
        "goal_selfish": "Твоя цель: получить как можно больше воды для своего поля.",
        "mech": {
            "distributor/proportional": "Центральный распределитель делит доступную воду между зонами "
                                        "пропорционально их запросам.",
            "distributor/equal": "Центральный распределитель делит доступную воду поровну между зонами, "
                                 "которые её запросили (никто не получает больше запроса).",
            "distributor/priority": "Центральный распределитель обслуживает зоны строго по ценности "
                                    "культуры: более ценная зона получает весь запрос раньше менее ценной.",
            "shared_tank": "Распределителя нет: зоны берут воду из общего бака в случайном порядке, "
                           "каждая забирает свой запрос, пока вода есть.",
            "auction": "Вода делится пропорционально ставкам; ставка = запрос x ценность культуры x "
                       "(1 + 0.25 x число шагов подряд с нехваткой).",
        },
        "topo": "Устройство сети. Узлы: {nodes}. Вода течёт: {flows}.{isolated} {status}",
        "topo_source": "источник воды, {supply} единиц за шаг",
        "topo_distributor": "центральный распределитель",
        "topo_tank": "общий бак, в нём {level} из {cap} единиц",
        "topo_auctioneer": "аукционист",
        "topo_zone": "зона орошения, ценность культуры {prio:g}",
        "topo_you": "зона орошения, ценность культуры {prio:g} -- это ты",
        "topo_isolated": " Зоны не связаны друг с другом: вся вода приходит к ним через {hub}.",
        "topo_down": " -- В ОТКАЗЕ, сейчас не пропускает воду",
        "topo_ok": "Состояние: все узлы работают.",
        "topo_failed": "Состояние: сейчас в отказе: {names}.",
        "neighbors": "Другие зоны в этот шаг: {items}.",
        "neighbor_item": "{name} (ценность {prio:g}) нужно {need}{starving}",
        "neighbor_starving": ", недополучает {streak} шаг(а) подряд",
        "goal": "Цель всей оросительной сети -- максимальный суммарный урожай = сумма по зонам "
                "(ценность культуры x квадратный корень из полученной воды). Из-за корня вода, "
                "распределённая между зонами, даёт больше урожая, чем сосредоточенная в одной. "
                "Воды в этот шаг: {supply}; суммарная потребность всех зон: {total_need}.",
        "q_yield": [
            "Должна ли {name} в этот шаг не запрашивать воду и оставить её другим зонам?",
            "Должна ли {name} отказаться от запроса воды в этот шаг?",
            "Лучше ли {name} в этот шаг не запрашивать воду?",
        ],
        "q_inflate": [
            "Должна ли {name} в этот шаг запросить больше воды, чем реально нужно её полю?",
            "Должна ли {name} в этот шаг завысить свой запрос воды?",
            "Лучше ли {name} в этот шаг попросить больше воды, чем она может использовать?",
        ],
    },
}


def _need(zone) -> float:
    return 0.0 if zone.is_failed else min(zone.queue, zone.max_intake)


def scheme_key(model) -> str:
    return f"distributor/{model.policy}" if model.scheme == "distributor" else model.scheme


def _role(node, zone, t) -> str:
    return _base_role(node, zone, t) + (t["topo_down"] if node.is_failed else "")


def _base_role(node, zone, t) -> str:
    kind = node.kind
    if kind == "zone":
        return t["topo_you" if node is zone else "topo_zone"].format(prio=node.priority)
    if kind == "source":
        return t["topo_source"].format(supply=_r(node.supply))
    if kind == "tank":
        return t["topo_tank"].format(level=_r(node.level), cap=_r(node.capacity))
    return t[f"topo_{kind}"]


def topology(zone, lang: str = "en") -> str:
    """Устройство сети из графа модели: узлы с ролями, рёбра, отказы."""
    t = _T[lang]
    m = zone.model
    nodes = "; ".join(f"{n.name} ({_role(n, zone, t)})" for n in m.nodes)
    flows = "; ".join(f"{n.name} -> {', '.join(d.name for d in n.downstreams)}"
                      for n in m.nodes if n.downstreams)
    # зоны изолированы, если у всех один и тот же поставщик и нет рёбер зона -> зона
    feeders = {n.name for n in m.nodes for d in n.downstreams if d.kind == "zone"}
    isolated = (t["topo_isolated"].format(hub=next(iter(feeders)))
                if len(feeders) == 1 and not any(z.downstreams for z in m.zones) else "")
    failed = [n.name for n in m.nodes if n.is_failed]
    status = t["topo_failed"].format(names=", ".join(failed)) if failed else t["topo_ok"]
    return t["topo"].format(nodes=nodes, flows=flows, isolated=isolated, status=status)


def describe(zone, blocks=BLOCKS, lang: str = "en", own_goal: str = "selfish") -> str:
    """Текст контекста зоны из выбранных блоков. own_goal: "selfish" --
    с явной локальной целью (максимум воды себе), "none" -- без неё
    (проверка якорения на первой заявленной цели)."""
    t = _T[lang]
    m = zone.model
    parts = []
    if "topology" in blocks:
        parts.append(topology(zone, lang))
    if "own" in blocks:
        s = zone.unmet_streak
        streak_text = (t["streak0"] if s == 0 else t["streakN"].format(streak=s) if s < STREAK_CAP
                       else t["streakMany"].format(streak=STREAK_CAP))
        own = t["own"].format(name=zone.name, prio=zone.priority, need=_r(_need(zone)),
                              cap=_r(zone.max_intake), queue=_r(zone.queue), qcap=_r(zone.capacity),
                              streak_text=streak_text)
        if own_goal == "selfish":
            own += " " + t["goal_selfish"]
        parts.append(own)
    if "mechanism" in blocks:
        parts.append(t["mech"][scheme_key(m)])
    if "neighbors" in blocks:
        items = []
        for z in m.zones:
            if z is zone:
                continue
            ns = z.unmet_streak if z.unmet_streak < STREAK_CAP else f"{STREAK_CAP}+"
            starving = t["neighbor_starving"].format(streak=ns) if z.unmet_streak else ""
            items.append(t["neighbor_item"].format(name=z.name, prio=z.priority,
                                                   need=_r(_need(z)), starving=starving))
        parts.append(t["neighbors"].format(items="; ".join(items)))
    if "goal" in blocks:
        # source.produced уже посчитан в этот шаг (hub.available -- ещё нет:
        # зоны объявляют запрос до hub.prepare)
        # при отказе хаба до зон не доходит ничего, хотя источник воду выдал
        supply = 0.0 if m.hub.is_failed else m.source.produced
        parts.append(t["goal"].format(supply=_r(supply),
                                      total_need=_r(sum(_need(z) for z in m.zones))))
    return " ".join(parts)


def question(kind: str, zone_name: str, lang: str = "en", variant: int = 0) -> str:
    """kind: "yield" (ДА = REFUSE) или "inflate" (ДА = MODIFY)."""
    return _T[lang][f"q_{kind}"][variant].format(name=zone_name)
