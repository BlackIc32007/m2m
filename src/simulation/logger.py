"""
EventLogger -- пишет историю работы модели в JSON Lines файлы.

Два отдельных лога:
  logs/events.jsonl    -- изменения состояния узлов и события (задача создана,
                           поставлена в очередь, начата, завершена, узел
                           отказал/восстановился и т.п.)
  logs/llm_calls.jsonl -- каждый вызов Ollama: что отправили, что получили,
                           название модели, время ответа

Формат -- по одной JSON-записи на строку, чтобы можно было легко дописывать
построчно и потом разбирать (pandas.read_json(path, lines=True) и т.п.).
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventLogger:
    def __init__(self, log_dir: str = "logs", reset: bool = False):
        """reset=True -- начать журналы заново (иначе записи дописываются
        к прошлым запускам)."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.log_dir / "events.jsonl"
        self.llm_path = self.log_dir / "llm_calls.jsonl"
        if reset:
            for path in (self.events_path, self.llm_path):
                path.unlink(missing_ok=True)

    def _append(self, path: Path, record: dict) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ #
    # События модели: изменения состояния узлов
    # ------------------------------------------------------------------ #
    def log_state_change(
        self,
        simulation_step: int,
        node_id: str,
        old_state: str,
        new_state: str,
        event: str,
        task_id: str | None = None,
    ) -> None:
        record = {
            "timestamp": _now_iso(),
            "simulation_step": simulation_step,
            "node_id": node_id,
            "old_state": old_state,
            "new_state": new_state,
            "event": event,
            "task_id": task_id,
        }
        self._append(self.events_path, record)

    def log_event(
        self,
        simulation_step: int,
        node_id: str,
        event: str,
        task_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Событие без смены состояния (например, задача поставлена в очередь).
        details -- доп. поля, например причина решения агента."""
        record = {
            "timestamp": _now_iso(),
            "simulation_step": simulation_step,
            "node_id": node_id,
            "old_state": None,
            "new_state": None,
            "event": event,
            "task_id": task_id,
        }
        if details:
            record["details"] = details
        self._append(self.events_path, record)

    # ------------------------------------------------------------------ #
    # Вызовы LLM
    # ------------------------------------------------------------------ #
    def log_llm_call(
        self,
        simulation_step: int,
        node_id: str,
        model_name: str,
        llm_input: dict,
        llm_output: dict,
        response_time_sec: float,
        error: str = "",
    ) -> None:
        record = {
            "timestamp": _now_iso(),
            "simulation_step": simulation_step,
            "node_id": node_id,
            "model_name": model_name,
            "llm_input": llm_input,
            "llm_output": llm_output,
            "response_time_sec": round(response_time_sec, 3),
            "error": error,
        }
        self._append(self.llm_path, record)
