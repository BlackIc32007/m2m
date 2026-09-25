"""
Сравнение трёх вариантов поведения клапана на идентичных условиях
(одна и та же PipelineModel, меняется только класс Valve):
  A. ValveAgent       -- ACCEPT/MODIFY: при перегрузке дросселирует обработку
  B. ValveAgentRefuse -- REFUSE новых задач + выход по гистерезису; отказанные
                         задачи остаются у Pump (backpressure), не теряются
  C. ValveAgentModify -- MODIFY: не отказывает, но обрабатывает медленнее

Запуск:
    python experiments/compare_valves.py
    python experiments/compare_valves.py --steps 100
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.valve_agent import ValveAgent
from src.agents.valve_agent_fixed import ValveAgentRefuse, ValveAgentModify
from src.model.pipeline_model import PipelineModel


def run_and_report(label, valve_class, valve_kwargs, steps):
    # decision_mode="agent": клапаны принимают решения (в режиме "pipe" все три
    # варианта вели бы себя одинаково -- как обычная труба)
    model = PipelineModel(valve_class=valve_class, valve_kwargs=valve_kwargs,
                          decision_mode="agent", rng=42)
    for _ in range(steps):
        model.step()

    print(f"=== {label} (после {steps} шагов) ===")
    for node in model.nodes:
        print(" ", node.state_dict())
    print(f"  completed_tasks (дошло до Output): {model.completed_tasks}, "
          f"отброшено на входе: {model.input.dropped}")
    print()
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сравнение вариантов ValveAgent")
    parser.add_argument("--steps", type=int, default=60)
    args = parser.parse_args()

    run_and_report("A. ValveAgent (ACCEPT/MODIFY)", ValveAgent, {"safety_threshold": 0.5}, args.steps)
    run_and_report("B. REFUSE с выходом", ValveAgentRefuse, {"safety_threshold": 0.5}, args.steps)
    run_and_report("C. MODIFY (частичный пропуск)", ValveAgentModify,
                   {"safety_threshold": 0.5, "throttle_factor": 3}, args.steps)
