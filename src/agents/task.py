"""Простой класс задачи, которая двигается между узлами модели."""
from dataclasses import dataclass, field


@dataclass
class Task:
    task_id: str
    created_step: int
    history: list = field(default_factory=list)  # список узлов, через которые прошла задача

    def visit(self, node_id: str, step: int) -> None:
        """Отметить, что задача побывала на узле node_id на шаге step."""
        self.history.append({"node": node_id, "step": step})
