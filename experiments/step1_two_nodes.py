"""
Шаг 1: минимальный пример на Mesa 3.x
Два узла: Machine_A -> Buffer
Machine_A берёт задачу из очереди, "работает" 1 шаг, потом передаёт задачу в Buffer.
"""

import mesa


class NodeAgent(mesa.Agent):
    """
    Один узел системы (машина, буфер и т.п.).
    Наследуемся от mesa.Agent — это даёт нам:
      - self.unique_id (уникальный номер, Mesa назначает сама)
      - self.model (ссылка на модель, в которой живёт агент)
      - автоматическую регистрацию в model.agents
    """

    def __init__(self, model, name, next_node=None):
        # ОБЯЗАТЕЛЬНО вызвать родительский __init__.
        # Именно здесь Mesa добавляет агента в model.agents.
        super().__init__(model)

        self.name = name
        self.next_node = next_node   # кому передавать задачу после обработки

        # состояние узла — как в задании
        self.state = "idle"          # idle / working / failed
        self.current_task = None
        self.queue = []
        self.load = 0.0
        self.available = True
        self.priority = "normal"

    def receive_task(self, task_id):
        """Положить задачу в очередь этого узла."""
        self.queue.append(task_id)

    def step(self):
        """Вызывается моделью на каждом шаге для каждого агента."""

        if self.state == "working":
            # считаем, что обработка занимает ровно 1 шаг
            finished = self.current_task
            print(f"[{self.name}] закончил обработку {finished}")
            self.current_task = None
            self.state = "idle"

            if self.next_node:
                self.next_node.receive_task(finished)

        elif self.state == "idle" and self.queue:
            self.current_task = self.queue.pop(0)
            self.state = "working"
            print(f"[{self.name}] взял в работу {self.current_task}")

    def __repr__(self):
        return f"<{self.name} state={self.state} queue={self.queue}>"


class FactoryModel(mesa.Model):
    def __init__(self):
        super().__init__()

        # создаём Buffer первым, чтобы передать ссылку на него в Machine_A
        self.machine_b = NodeAgent(self, "Machine_B")
        self.buffer = NodeAgent(self, "Buffer" , next_node=self.machine_b)
        self.machine_a = NodeAgent(self, "Machine_A", next_node=self.buffer)

        # "подкидываем" задачи в начале
        self.machine_a.receive_task("Task_1")
        self.machine_a.receive_task("Task_2")

    def step(self):
        # вызвать .step() у ВСЕХ агентов модели, в случайном порядке
        self.agents.shuffle_do("step")


if __name__ == "__main__":
    model = FactoryModel()

    for i in range(6):
        print(f"--- шаг {i} ---")
        model.step()
        print("состояние:", model.machine_a, model.buffer, model.machine_b)
