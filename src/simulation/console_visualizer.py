"""
Простая текстовая визуализация состояния модели -- без сторонних библиотек,
чтобы поведение модели было понятно без чтения кода (как и требует задание).

Формат близок к примеру из задания:

    [Machine_A] WORKING  queue=2  task=Task_4
      |
      v
    [Buffer]    IDLE     queue=0
      |
      v
    [Machine_B] FAILED   queue=4
"""

STATE_LABELS = {
    "idle": "IDLE",
    "working": "WORKING",
    "failed": "FAILED",
    "blocked": "BLOCKED",
}


def render(model, step_label: str = "") -> str:
    lines = []
    if step_label:
        lines.append(f"=== step {step_label} ===")

    for i, node in enumerate(model.nodes):
        s = node.state_dict()
        label = STATE_LABELS.get(s["state"], s["state"].upper())
        task_part = f" task={s['current_task']}" if s["current_task"] else ""
        lines.append(
            f"[{s['node']:10s}] {label:8s} queue={s['queue']:<3d} load={s['load']:.2f}{task_part}"
        )
        if i < len(model.nodes) - 1:
            lines.append("  |")
            lines.append("  v")

    lines.append(f"completed_tasks={model.completed_tasks}")
    return "\n".join(lines)


def print_state(model, step_label: str = "") -> None:
    print(render(model, step_label))
    print()
