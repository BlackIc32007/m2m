"""
OllamaClient -- минимальная обёртка для вызова локальной LLM через Ollama.

На этом этапе Ollama НЕ управляет моделью Mesa -- она только получает
состояние узла и возвращает структурированный ответ, который логируется и
показывается пользователю (см. src/llm/node_advisor.py).

Требует запущенной Ollama (`ollama serve`) и загруженной модели
(`ollama pull <model>`).
"""
import json
import os
import time

import requests



def _ollama_host() -> str:
    """Адрес Ollama из переменной OLLAMA_HOST (её же читает сам ollama CLI).
    Ollama допускает значение без схемы ("0.0.0.0:11434") -- дописываем http://."""
    host = os.environ.get("OLLAMA_HOST", "").strip() or "localhost:11434"
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host.replace("://0.0.0.0", "://localhost").rstrip("/")


OLLAMA_HOST = _ollama_host()
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(self, model: str = "qwen2.5:3b", timeout: float = 60.0):
        self.model = model
        self.timeout = timeout

    def call(self, prompt: str) -> tuple[dict, float]:
        """
        Отправить промпт в Ollama, вернуть (распарсенный JSON-ответ, время ответа в секундах).
        Бросает OllamaError, если Ollama недоступна, вернула HTTP-ошибку, или
        ответ не удалось распарсить как JSON.
        """
        t0 = time.time()
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={"model": self.model, "prompt": prompt, "stream": False, "format": "json",
                      "think": False},  # qwen3.5 иначе сначала "думает"
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as e:
            raise OllamaError(f"Не удалось подключиться к Ollama: {e}") from e

        elapsed = time.time() - t0

        if resp.status_code != 200:
            raise OllamaError(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        raw_response = data.get("response", "")

        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise OllamaError(
                f"Ответ Ollama не является валидным JSON: {raw_response!r}"
            ) from e

        return parsed, elapsed

    def structured_call(self, node_state: dict, instruction: str) -> tuple[dict, float]:
        """
        Удобный метод для сценария из задания:
            {"node": "Machine_A", "state": "busy", "queue": 5} -> {"status": "overloaded"}
        instruction описывает, что именно должна вернуть модель.
        """
        prompt = (
            f"{instruction}\n\n"
            f"Node state (JSON): {json.dumps(node_state, ensure_ascii=False)}\n\n"
            "Respond with a single JSON object only, no other text."
        )
        return self.call(prompt)


if __name__ == "__main__":
    # Быстрая ручная проверка: python -m src.llm.ollama_client
    client = OllamaClient(model="qwen2.5:3b")
    example_state = {"node": "Machine_A", "state": "busy", "queue": 5}
    try:
        result, elapsed = client.structured_call(
            example_state,
            instruction='Return JSON like {"status": "overloaded"} describing whether this node is overloaded.',
        )
        print(f"Response ({elapsed:.2f}s): {result}")
    except OllamaError as e:
        print(f"Ollama call failed: {e}")
