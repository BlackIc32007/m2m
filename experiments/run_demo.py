"""
Демонстрационный сценарий из задания:

    Machine A -> Buffer -> Machine B
    Поступают Task 1, Task 2, Task 3
    Machine A начинает обработку
    Во время работы: Machine B = FAILED
    Показать: изменение состояния, накопление очереди, восстановление,
              продолжение работы

Запуск:
    python -m experiments.run_demo                  # без Ollama
    python -m experiments.run_demo --with-ollama     # + запросить рекомендацию у LLM
    python -m experiments.run_demo --model qwen2.5:3b --with-ollama
"""
import argparse
import sys
from pathlib import Path

# Позволяет запускать скрипт как `python experiments/run_demo.py` из корня проекта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.model.factory_model import FactoryModel
from src.simulation.logger import EventLogger
from src.simulation.console_visualizer import print_state
from src.llm.ollama_client import OllamaClient
from src.llm.node_advisor import NodeAdvisor


def main():
    parser = argparse.ArgumentParser(description="Демо-сценарий Mesa: отказ и восстановление узла")
    parser.add_argument("--steps", type=int, default=20, help="Сколько шагов прогнать модель")
    parser.add_argument("--fail-at", type=int, default=4, help="На каком шаге отказывает Machine_B")
    parser.add_argument("--fail-duration", type=int, default=5, help="На сколько шагов отказывает Machine_B")
    parser.add_argument("--with-ollama", action="store_true", help="Запрашивать рекомендацию у Ollama на каждом шаге")
    parser.add_argument("--model", default="qwen2.5:3b", help="Название модели Ollama")
    parser.add_argument("--quiet", action="store_true", help="Не печатать визуализацию на каждом шаге")
    args = parser.parse_args()

    logger = EventLogger(log_dir="logs")
    model = FactoryModel(
        task_arrival_interval=2,
        processing_time=2,
        queue_capacity=10,
        logger=logger,
        rng=42,
    )

    advisor = None
    if args.with_ollama:
        client = OllamaClient(model=args.model)
        advisor = NodeAdvisor(client, logger, simulation_step_getter=lambda: model.steps)

    print(f"Запуск демо-сценария: {args.steps} шагов, отказ Machine_B на шаге {args.fail_at}"
          f" длительностью {args.fail_duration} шагов.\n")

    for step in range(1, args.steps + 1):
        model.step()

        if step == args.fail_at:
            model.trigger_failure("Machine_B", args.fail_duration)
            print(f">>> Событие: Machine_B отказал на шаге {step}\n")

        if not args.quiet:
            print_state(model, step_label=str(step))

        if advisor is not None:
            for node in model.nodes:
                if node.is_endpoint:
                    continue  # Input/Output -- служебные, рекомендации им не нужны
                if node.state != "idle" or node.queue:
                    rec = advisor.advise(node.state_dict())
                    if rec is not None:
                        print(f"    [Ollama] {node.name}: {rec}")

    print(f"\nГотово. Завершено задач: {model.completed_tasks}")
    print(f"Логи: logs/events.jsonl" + (", logs/llm_calls.jsonl" if args.with_ollama else ""))


if __name__ == "__main__":
    main()
