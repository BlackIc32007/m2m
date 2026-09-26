"""
Насколько стабильно локальная LLM возвращает JSON (вопрос из отчёта по
первому заданию: "получается ли стабильно возвращать JSON").

Тот же промпт, что у NodeAdvisor (Mesa Node State -> Ollama -> Recommendation),
на сетке состояний узла: state in {idle, working, failed} x 9 уровней load.
Для каждой модели -- два способа вызова:
    format=json  -- Ollama ограничивает вывод грамматикой JSON (как в OllamaClient);
    free         -- без ограничения, JSON ищем в свободном тексте.

Что считаем:
    json_ok   -- ответ разбирается json.loads
    schema_ok -- есть ключ "recommendation" с одним из двух допустимых значений
    rule_ok   -- значение совпадает с правилом из промпта (load > 0.8 или failed ->
                 do_not_accept_new_tasks); это проверка смысла, а не формата
    время ответа (медиана, с)

Запуск:
    python experiments/json_stability.py                       # 3 модели, ~3 мин
    python experiments/json_stability.py --models qwen2.5:1.5b
Результат: experiments/results/json_stability.csv и _summary.md
"""
import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from src.llm.node_advisor import RECOMMENDATION_INSTRUCTION
from src.llm.ollama_client import OLLAMA_HOST

ALLOWED = {"accept_new_tasks", "do_not_accept_new_tasks"}
RESULTS = Path(__file__).resolve().parent / "results"


def states():
    for state in ("idle", "working", "failed"):
        for load in (0.0, 0.1, 0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 1.0):
            yield {"node": "Machine_A", "state": state, "current_task": None if state == "idle" else "Task_4",
                   "queue": round(load * 10), "load": load, "available": state != "failed",
                   "priority": "normal"}


def expected(s):
    return "do_not_accept_new_tasks" if s["load"] > 0.8 or s["state"] == "failed" else "accept_new_tasks"


def call(model, node_state, constrained):
    # тот же текст промпта, что в OllamaClient.structured_call
    prompt = (f"{RECOMMENDATION_INSTRUCTION}\n\n"
              f"Node state (JSON): {json.dumps(node_state, ensure_ascii=False)}\n\n"
              "Respond with a single JSON object only, no other text.")
    body = {"model": model, "prompt": prompt, "stream": False, "think": False,
            "options": {"temperature": 0, "num_predict": 120}}
    if constrained:
        body["format"] = "json"
    t0 = time.time()
    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=body, timeout=180)
    r.raise_for_status()
    return r.json().get("response", ""), time.time() - t0


def parse(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen2.5:1.5b", "qwen2.5:3b", "qwen3.5:9b"])
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    rows = []
    for model in args.models:
        for constrained in (True, False):
            for s in states():
                raw, dt = call(model, s, constrained)
                obj = parse(raw)
                rec = obj.get("recommendation") if isinstance(obj, dict) else None
                rows.append({
                    "model": model, "format": "json" if constrained else "free",
                    "state": s["state"], "load": s["load"],
                    "json_ok": obj is not None,
                    "schema_ok": rec in ALLOWED,
                    "rule_ok": rec == expected(s),
                    "time_s": round(dt, 3), "raw": raw.strip()[:200],
                })
            print(f"{model:14s} format={'json' if constrained else 'free':4s} готово", flush=True)

    with open(RESULTS / "json_stability.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    lines = ["# Стабильность JSON-ответа (NodeAdvisor)", "",
             "27 состояний узла (idle/working/failed × 9 уровней load), temperature 0.", "",
             "| модель | вызов | валидный JSON | верная схема | совпадает с правилом | медиана, с |",
             "|---|---|---|---|---|---|"]
    for model in args.models:
        for fmt in ("json", "free"):
            g = [r for r in rows if r["model"] == model and r["format"] == fmt]
            n = len(g)
            lines.append(f"| {model} | {fmt} | {sum(r['json_ok'] for r in g)}/{n} | "
                         f"{sum(r['schema_ok'] for r in g)}/{n} | {sum(r['rule_ok'] for r in g)}/{n} | "
                         f"{statistics.median(r['time_s'] for r in g):.2f} |")
    bad = [r for r in rows if not r["json_ok"]][:3]
    if bad:
        lines += ["", "Примеры невалидных ответов:", ""]
        lines += [f"- {r['model']} ({r['format']}): `{r['raw'][:120]}`" for r in bad]
    (RESULTS / "json_stability_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
