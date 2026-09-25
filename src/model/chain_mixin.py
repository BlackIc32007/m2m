"""
ChainModelMixin -- общий для PipelineModel и FactoryModel код цепочки:
связывание агентов, шаг модели через Mesa AgentSet, отказ/восстановление
и добавление узла "на лету" (live_server.py).

Модель-наследник создаёт агентов (InputAgent, NodeAgent..., OutputAgent)
и вызывает self._link_chain([...]); должен быть атрибут self.logger.

add_node поддерживает два режима:
  mode="insert" (по умолчанию) -- узел встраивается в цепочку ПОСЛЕ anchor:
        anchor -> new -> (бывшие приёмники anchor)
  mode="branch" -- узел добавляется как ДОПОЛНИТЕЛЬНЫЙ приёмник anchor,
        не разрывая существующую связь. Поток anchor делится между старыми
        приёмниками и новой веткой по кругу (см. NodeAgent._forward_task).
        Новая ветка ведёт прямо в Output.
"""
from mesa.agentset import AgentSet


class ChainModelMixin:
    def _link_chain(self, nodes: list) -> None:
        """nodes -- агенты в порядке цепочки: [Input, ..., Output]."""
        for src, dst in zip(nodes, nodes[1:]):
            src.downstream = dst
        self.nodes = list(nodes)
        self.input = nodes[0]
        self.output = nodes[-1]

    def step(self) -> None:
        # Все агенты шагают через Mesa AgentSet в порядке цепочки
        # (Input -> ... -> Output): задача за один шаг модели проходит не
        # больше одного шага обработки каждого узла -- предсказуемо.
        # Порядок берём из self.nodes, а не из self.agents, потому что
        # add_node вставляет узлы в середину цепочки.
        AgentSet(self.nodes, random=self.random).do("step")

    def snapshot(self) -> dict:
        return {node.name: node.state_dict() for node in self.nodes}

    def trigger_failure(self, node_name: str, duration_steps) -> None:
        # duration_steps можно передать float('inf') -- тогда узел не
        # восстановится сам, только через force_recover.
        self._find_node(node_name).fail(duration_steps)

    def force_recover(self, node_name: str) -> None:
        self._find_node(node_name).recover_now()

    def _find_node(self, node_name: str):
        for node in self.nodes:
            if node.name == node_name:
                return node
        raise ValueError(f"Unknown node: {node_name}")

    def add_node(self, node_class, name: str, insert_after: str | None = None,
                 extra_kwargs: dict | None = None, mode: str = "insert"):
        extra_kwargs = extra_kwargs or {}
        if mode not in ("insert", "branch"):
            raise ValueError(f"unknown mode '{mode}', expected 'insert' or 'branch'")
        if any(n.name == name for n in self.nodes):
            raise ValueError(f"node with name '{name}' already exists")

        # по умолчанию -- после последнего рабочего узла, перед Output
        anchor = self._find_node(insert_after) if insert_after else self.nodes[-2]
        if anchor is self.output:
            raise ValueError(f"после {self.output.name} узлы добавлять нельзя -- это конец цепочки")
        anchor_index = self.nodes.index(anchor)

        new_node = node_class(self, name=name, logger=self.logger, **extra_kwargs)
        if mode == "insert":
            new_node.downstreams = list(anchor.downstreams)
            anchor.downstreams = [new_node]
        else:  # branch
            new_node.downstreams = [self.output]
            anchor.downstreams.append(new_node)

        # порядок в self.nodes = порядок вызова step(): новый узел сразу
        # после anchor, чтобы задача не "перепрыгивала" через него.
        self.nodes.insert(anchor_index + 1, new_node)
        return new_node
