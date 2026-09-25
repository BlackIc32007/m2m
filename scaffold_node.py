"""
scaffold_node.py -- генератор заготовки нового типа узла (NodeAgent
subclass) по образцу valve_agent.py, чтобы не переписывать одинаковый
boilerplate каждый раз, когда появляется новый тип узла/агента.

Использование:
    cd m2m_project/project
    python scaffold_node.py PumpAgent
    python scaffold_node.py CompressorAgent --param-name max_pressure --description "узел, сдерживающий давление в магистрали"

Создаст src/agents/pump_agent.py (или compressor_agent.py) с классом,
готовым к редактированию -- структура методов такая же, как в
src/agents/valve_agent.py: _decide / accept_task / state_dict.
"""
import argparse
import re
from pathlib import Path

TEMPLATE = '''"""
{class_name} -- {description}

TODO: опишите здесь локальную целевую функцию узла и в чём может быть
конфликт с глобальной целью системы (см. docs/valve_gas_liquid_domain.md
как пример такого описания для ValveAgent).
"""
from src.agents.node_agent import NodeAgent


class {class_name}(NodeAgent):
    def __init__(self, model, name, {param_name}: float = 0.5, **kwargs):
        super().__init__(model, name, **kwargs)
        self.{param_name} = {param_name}
        # TODO: добавьте сюда остальное внутреннее состояние узла,
        # если одного {param_name} недостаточно.

    def _decide(self) -> None:
        """TODO: локальная логика принятия решения узла.

        Вызывается NodeAgent в начале каждого шага и перед приёмом задачи.
        Обычно здесь сравнивают self.load (или другую метрику) с
        self.{param_name}: self.accepting = False -- REFUSE новых задач,
        смена self.processing_time -- MODIFY. В режиме "pipe"
        (self.decides == False) узел должен вести себя как труба.
        Если не переопределять -- работает общее правило NodeAgent.
        """
        super()._decide()

    def state_dict(self) -> dict:
        d = super().state_dict()
        d["{param_name}"] = self.{param_name}  # TODO: добавьте то, что хотите видеть в логах/UI
        return d
'''


def to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def main() -> None:
    parser = argparse.ArgumentParser(description="Сгенерировать заготовку нового NodeAgent")
    parser.add_argument("class_name", help="Имя класса, например PumpAgent")
    parser.add_argument("--param-name", default="threshold", help="Имя основного числового параметра узла (по умолчанию: threshold)")
    parser.add_argument("--description", default="узел со своей локальной целевой функцией.")
    parser.add_argument("--out-dir", default="src/agents")
    args = parser.parse_args()

    file_name = to_snake(args.class_name) + ".py"
    out_path = Path(args.out_dir) / file_name
    if out_path.exists():
        print(f"Уже существует: {out_path} -- ничего не создаю, чтобы не затереть правки.")
        return

    content = TEMPLATE.format(
        class_name=args.class_name,
        description=args.description,
        param_name=args.param_name,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"Создано: {out_path}")
    print(f"Не забудьте добавить импорт в модель: from src.agents.{to_snake(args.class_name)} import {args.class_name}")


if __name__ == "__main__":
    main()
