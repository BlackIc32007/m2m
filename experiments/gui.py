import mesa
from mesa.visualization import SolaraViz
from mesa.visualization.utils import update_counter
import solara

# ------------------------------------------------------------
# 1. Определение Агентов и Модели
#    (без CellAgent/grid -- нам не нужно физическое расположение
#    на карте 5x5, нас интересует только распределение ресурса.
#    Обычный mesa.Agent -- проще и ничего не теряем.)
# ------------------------------------------------------------

class ValveAgent(mesa.Agent):
    """Узел, у которого есть локальный спрос (demand) и полученная доля (allocated_flow)."""
    def __init__(self, model, node_id, demand=40):
        super().__init__(model)
        self.node_id = node_id
        self.demand = demand
        self.allocated_flow = 0

    def step(self):
        pass


class SystemModel(mesa.Model):
    def __init__(self, *, conflict_type=1, total_system_capacity=100, num_nodes=4, seed=None):
        super().__init__(seed=seed)
        self.conflict_type = int(conflict_type)
        self.total_system_capacity = int(total_system_capacity)
        self.num_nodes = int(num_nodes)

        self.valves = [ValveAgent(self, node_id=i, demand=40) for i in range(self.num_nodes)]

        self.total_demanded = 0
        self.total_allocated = 0
        self.system_status = "OK"

    def step(self):
        self.total_demanded = sum(v.demand for v in self.valves)

        if self.conflict_type == 0:
            self.system_status = "Норма (ресурсов хватает всем)"
            for v in self.valves:
                v.allocated_flow = v.demand

        elif self.conflict_type == 1:
            self.system_status = "Узел vs Система: суммарный спрос превышает лимит -- всем режут пропорционально"
            if self.total_demanded > self.total_system_capacity:
                factor = self.total_system_capacity / self.total_demanded if self.total_demanded > 0 else 1
                for v in self.valves:
                    v.allocated_flow = v.demand * factor
            else:
                for v in self.valves:
                    v.allocated_flow = v.demand

        elif self.conflict_type == 2:
            self.system_status = "Узел vs Узел: ресурс раздаётся по очереди -- первым достаётся всё, последним ничего"
            remaining = self.total_system_capacity
            for v in self.valves:
                allocated = min(v.demand, max(0, remaining))
                v.allocated_flow = allocated
                remaining -= allocated

        self.total_allocated = sum(v.allocated_flow for v in self.valves)
        self.agents.do("step")


# ------------------------------------------------------------
# 2. Визуализация: горизонтальные шкалы "спрос vs выделено"
#    вместо точек на пустой сетке -- сразу видно, кто сколько
#    просил и сколько реально получил.
# ------------------------------------------------------------

def _satisfaction_color(satisfaction: float) -> str:
    if satisfaction >= 0.99:
        return "#3ecf6e"   # зелёный -- получил всё, что просил
    if satisfaction > 0.5:
        return "#f5a623"   # оранжевый -- получил частично
    return "#e5484d"       # красный -- почти или совсем ничего не получил


@solara.component
def NodeBar(node):
    """Одна горизонтальная шкала узла: серая рамка = спрос, цветная заливка = сколько реально выделено."""
    satisfaction = node.allocated_flow / node.demand if node.demand > 0 else 1.0
    fill_pct = min(100, round(satisfaction * 100))
    color = _satisfaction_color(satisfaction)

    with solara.Column(style={"width": "100%", "margin-bottom": "14px"}):
        with solara.Row(justify="space-between", style={"width": "100%"}):
            solara.Text(f"Узел #{node.node_id}", style={"font-weight": "bold"})
            solara.Text(
                f"{node.allocated_flow:.0f} / {node.demand:.0f}  ({fill_pct}%)",
                style={"color": color, "font-weight": "bold"},
            )
        # серая рамка = 100% от demand, внутри -- цветная заливка = allocated_flow
        with solara.v.Html(
            tag="div",
            style_=(
                "width:100%; height:22px; border:2px solid #555; border-radius:4px; "
                "background:#1e1e1e; overflow:hidden;"
            ),
        ):
            solara.v.Html(
                tag="div",
                style_=(
                    f"width:{fill_pct}%; height:100%; background:{color}; "
                    "transition: width 0.3s ease;"
                ),
            )


@solara.component
def CapacityBar(model):
    """Общая шкала: сколько всего запрошено vs сколько реально влезло в лимит системы."""
    demand_pct = min(100, round((model.total_demanded / model.total_system_capacity) * 100)) \
        if model.total_system_capacity > 0 else 0
    used_pct = min(100, round((model.total_allocated / model.total_system_capacity) * 100)) \
        if model.total_system_capacity > 0 else 0
    overloaded = model.total_demanded > model.total_system_capacity

    with solara.Column(style={"width": "100%", "margin-bottom": "20px"}):
        solara.Text("Лимит системы", style={"font-weight": "bold", "font-size": "15px"})
        with solara.v.Html(
            tag="div",
            style_=(
                "width:100%; height:30px; border:2px solid #999; border-radius:4px; "
                "background:#1e1e1e; position:relative; overflow:hidden;"
            ),
        ):
            # синим -- сколько реально выделено (влезло в лимит)
            solara.v.Html(
                tag="div",
                style_=(
                    f"width:{used_pct}%; height:100%; background:#3b82f6; "
                    "transition: width 0.3s ease;"
                ),
            )
        solara.Text(
            f"Запрошено: {model.total_demanded:.0f}   Выделено: {model.total_allocated:.0f}   "
            f"Лимит: {model.total_system_capacity}",
        )
        if overloaded:
            solara.Text(
                f"⚠ Спрос превышает лимит на {model.total_demanded - model.total_system_capacity:.0f} "
                "-- это и есть конфликт локальных целей узлов с общим лимитом системы.",
                style={"color": "#f5a623"},
            )


@solara.component
def SystemMetrics(model):
    update_counter.get()  # подписка компонента на пересчёт при каждом шаге модели
    with solara.Card("Распределение ресурса: спрос каждого узла vs то, что он реально получил"):
        solara.Markdown(f"**Режим:** {model.system_status}")
        solara.Markdown(f"**Шаг:** {model.steps}")

        CapacityBar(model)

        solara.Text("Узлы", style={"font-weight": "bold", "font-size": "15px", "margin-bottom": "6px"})
        for v in model.valves:
            NodeBar(v)


# ------------------------------------------------------------
# 3. Параметры модели и сборка страницы
# ------------------------------------------------------------

model_params = {
    "conflict_type": {
        "type": "Select",
        "value": 1,
        "values": [0, 1, 2],
        "label": "Режим конфликта (0: Нет, 1: Узел/Система, 2: Узел/Узел)"
    },
    "total_system_capacity": {
        "type": "SliderInt",
        "value": 90,
        "min": 20,
        "max": 200,
        "step": 10,
        "label": "Общая пропускная способность системы"
    },
    "num_nodes": {
        "type": "SliderInt",
        "value": 4,
        "min": 1,
        "max": 4,
        "step": 1,
        "label": "Количество узлов"
    }
}

initial_model = SystemModel(conflict_type=1, total_system_capacity=90, num_nodes=4)

page = SolaraViz(
    initial_model,
    components=[SystemMetrics],
    model_params=model_params,
    name="Исследование Коллизий и Конфликтов Ресурсов"
)