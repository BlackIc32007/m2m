"""
NodeAdvisor -- простейшая интеграция Mesa и Ollama.

Цепочка:
    Mesa Node State -> Python -> Ollama -> Recommendation

Рекомендация ТОЛЬКО логируется и возвращается вызывающему коду. Она НИКОГДА
не меняет состояние модели автоматически -- это осознанное ограничение
задания на первом этапе.
"""
from src.llm.ollama_client import OllamaClient, OllamaError

RECOMMENDATION_INSTRUCTION = (
    "You are monitoring a factory node. Given the node's current state, "
    'respond with JSON like {"recommendation": "accept_new_tasks"} or '
    '{"recommendation": "do_not_accept_new_tasks"}. '
    "Recommend do_not_accept_new_tasks if load is above 0.8 or the node is failed, "
    "otherwise recommend accept_new_tasks.\n\n"
    "Examples:\n"
    'Input: {"load": 0.0, "state": "idle"} -> '
    'Output: {"recommendation": "accept_new_tasks"}\n'
    'Input: {"load": 0.3, "state": "working"} -> '
    'Output: {"recommendation": "accept_new_tasks"}\n'
    'Input: {"load": 0.9, "state": "working"} -> '
    'Output: {"recommendation": "do_not_accept_new_tasks"}\n'
    'Input: {"load": 0.1, "state": "failed"} -> '
    'Output: {"recommendation": "do_not_accept_new_tasks"}'
)


class NodeAdvisor:
    def __init__(self, ollama_client: OllamaClient, logger, simulation_step_getter):
        """
        ollama_client         -- экземпляр OllamaClient
        logger                -- экземпляр EventLogger (пишет в logs/llm_calls.jsonl)
        simulation_step_getter -- функция без аргументов, возвращающая текущий model.steps
                                  (нужна, чтобы не тянуть в этот модуль всю Mesa-модель)
        """
        self.client = ollama_client
        self.logger = logger
        self.simulation_step_getter = simulation_step_getter

    def advise(self, node_state: dict) -> dict | None:
        """
        Запросить рекомендацию у LLM для данного состояния узла.
        Возвращает распарсенный dict с рекомендацией, либо None при ошибке
        (ошибка тоже логируется).
        """
        try:
            recommendation, elapsed = self.client.structured_call(
                node_state, RECOMMENDATION_INSTRUCTION
            )
            self.logger.log_llm_call(
                simulation_step=self.simulation_step_getter(),
                node_id=node_state.get("node", "unknown"),
                model_name=self.client.model,
                llm_input=node_state,
                llm_output=recommendation,
                response_time_sec=elapsed,
            )
            return recommendation
        except OllamaError as e:
            self.logger.log_llm_call(
                simulation_step=self.simulation_step_getter(),
                node_id=node_state.get("node", "unknown"),
                model_name=self.client.model,
                llm_input=node_state,
                llm_output={},
                response_time_sec=0.0,
                error=str(e),
            )
            return None
