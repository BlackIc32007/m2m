"""
zone_policies -- подключаемые политики решения зоны ConflictModel в
автономном режиме. Зона вызывает model.zone_policy.decide(zone) и получает
Decision: ACCEPT / REFUSE / MODIFY + заявленный запрос + причину.

    RulePolicy      -- пороговые правила (эталон, работает без Ollama)
    TokenLLMPolicy  -- решение одним токеном локальной LLM (src/llm/token_decision)
                       по тексту из выбранных блоков контекста (src/llm/zone_context)
    RecorderPolicy  -- честный запрос (как пассивный режим), но сохраняет
                       контексты -- для экспериментов без обратной связи

Тернарное решение раскладывается на два бинарных вопроса:
    Q1 "уступить воду в этот шаг?"            ДА -> REFUSE
    Q2 (если Q1 = НЕТ) "запросить больше?"    ДА -> MODIFY, НЕТ -> ACCEPT

debias=True -- устранение смещения к букве: каждый вопрос задаётся дважды,
с буквами ДА/НЕТ = M/K и K/M, и P(ДА) усредняется (у qwen2.5:1.5b перестановка
букв сдвигает P(ДА) с ~0.08 до ~0.48 -- см. experiments/results/open_loop.csv).

Защитный слой: если mass < mass_floor или буквы не найдены -- решение по
RulePolicy, в записи fallback=True. confidence < contested_floor -- решение
помечается как спорное (contested).
"""
import threading
from dataclasses import dataclass, field

import requests

from src.llm import token_decision, zone_context


@dataclass
class Decision:
    decision: str            # ACCEPT | REFUSE | MODIFY
    demand: float            # заявленный запрос
    reason: str
    meta: dict = field(default_factory=dict)  # запись для журнала решений


class RulePolicy:
    name = "rule"

    def __init__(self, refuse_threshold=None, inflate_after=None, inflate_factor=None):
        # None -- взять параметр самой зоны (ZoneAgent.__init__)
        self.refuse_threshold = refuse_threshold
        self.inflate_after = inflate_after
        self.inflate_factor = inflate_factor

    def decide(self, zone) -> Decision:
        rt = zone.refuse_threshold if self.refuse_threshold is None else self.refuse_threshold
        ia = zone.inflate_after if self.inflate_after is None else self.inflate_after
        f = zone.inflate_factor if self.inflate_factor is None else self.inflate_factor
        if zone.queue < rt * zone.capacity:
            return Decision("REFUSE", 0.0, f"запас {zone.queue:.1f} < {rt:.0%} ёмкости -- "
                                           "не срочно, уступаю ресурс другим")
        if zone.unmet_streak >= ia:
            return Decision("MODIFY", zone.need * f, f"недополучаю {zone.unmet_streak} шаг(а) "
                                                     f"подряд -- завышаю запрос в {f:g} раза")
        return Decision("ACCEPT", zone.need, "запрашиваю реальную потребность")


class RecorderPolicy:
    """Ведёт себя как пассивный режим, но на каждом решении сохраняет
    состояние и тексты контекста для всех заданных наборов блоков."""
    name = "recorder"

    def __init__(self, block_sets: dict, lang="en", own_goal="selfish"):
        self.block_sets = block_sets
        self.lang = lang
        self.own_goal = own_goal
        self.samples = []

    def decide(self, zone) -> Decision:
        m = zone.model
        self.samples.append({
            "scheme": zone_context.scheme_key(m), "step": m.steps, "zone": zone.name,
            "priority": zone.priority, "need": zone.need, "queue": zone.queue,
            "unmet_streak": zone.unmet_streak,
            "contexts": {k: zone_context.describe(zone, b, self.lang, self.own_goal)
                         for k, b in self.block_sets.items()},
            "contexts_nogoal": {k: zone_context.describe(zone, b, self.lang, "none")
                                for k, b in self.block_sets.items()},
            "contexts_ru": {k: zone_context.describe(zone, b, "ru", self.own_goal)
                            for k, b in self.block_sets.items()},
        })
        return Decision("ACCEPT", zone.need, "запись контекста (честный запрос)")


class TokenLLMPolicy:
    name = "llm"
    _cache = {}                      # общий на все экземпляры и потоки: промпт -> ответ
    _cache_lock = threading.Lock()

    def __init__(self, blocks=("own",), model=token_decision.MODEL, lang="en",
                 own_goal="selfish", sample=False, soft=False, question_variant=0,
                 swap_letters=False, debias=False, mass_floor=0.9, contested_floor=0.6,
                 inflate_factor=2.0, rng=None):
        """sample -- решать случайно с вероятностью P(ДА) (против стадности
        при temperature=0); soft -- MODIFY плавный: запрос = need x
        (1 + (factor-1) x P(ДА на Q2)), Q2 задаётся всегда."""
        self.blocks = tuple(blocks)
        self.model = model
        self.lang = lang
        self.own_goal = own_goal
        self.sample = sample
        self.soft = soft
        self.question_variant = question_variant
        self.letters = ("K", "M") if swap_letters else ("M", "K")
        self.debias = debias
        self.mass_floor = mass_floor
        self.contested_floor = contested_floor
        self.inflate_factor = inflate_factor
        self.rng = rng
        self.records = []
        self.fallback = RulePolicy()
        self.calls = 0
        self.cache_hits = 0

    def _ask_raw(self, context, q, letters):
        key = (self.model, self.lang, letters, context, q)
        with self._cache_lock:
            hit = self._cache.get(key)
        if hit is not None:
            self.cache_hits += 1
            return hit
        try:
            r = token_decision.ask(context, q, model=self.model, lang=self.lang,
                                   yes_letter=letters[0], no_letter=letters[1])
        except requests.RequestException as e:
            # Ollama недоступна -- не кэшируем, decide() откатится на правило
            return {"yes": None, "mass": 0.0, "p_yes": 0.0, "raw": f"ошибка Ollama: {e.__class__.__name__}"}
        r = {k: r[k] for k in ("yes", "mass", "p_yes", "raw")}
        self.calls += 1
        with self._cache_lock:
            self._cache[key] = r
        return r

    def _ask(self, context, q) -> dict:
        """-> {yes, p (нормированная P(ДА)), confidence, mass, raw}."""
        rs = [self._ask_raw(context, q, self.letters)]
        if self.debias:
            rs.append(self._ask_raw(context, q, self.letters[::-1]))
        if any(r["yes"] is None for r in rs):
            return {"yes": None, "p": None, "confidence": None, "mass": 0.0,
                    "raw": " | ".join(r["raw"] for r in rs)}
        p = sum(r["p_yes"] / r["mass"] for r in rs) / len(rs)
        return {"yes": p >= 0.5, "p": p, "confidence": max(p, 1 - p),
                "mass": min(r["mass"] for r in rs), "raw": " | ".join(r["raw"] for r in rs)}

    def _yes(self, r) -> bool:
        if self.sample:
            return self.rng.random() < r["p"]
        return r["yes"]

    def _bad(self, r) -> bool:
        return r["yes"] is None or r["mass"] < self.mass_floor

    def decide(self, zone) -> Decision:
        if self.rng is None:
            self.rng = zone.model.random  # сид модели -> воспроизводимая случайность
        ctx = zone_context.describe(zone, self.blocks, self.lang, self.own_goal)
        rec = {"step": zone.model.steps, "zone": zone.name, "scheme": zone_context.scheme_key(zone.model),
               "need": zone.need, "queue": zone.queue, "unmet_streak": zone.unmet_streak,
               "blocks": "+".join(self.blocks), "fallback": False}

        r1 = self._ask(ctx, zone_context.question("yield", zone.name, self.lang, self.question_variant))
        rec.update(q1_p_yes=r1["p"], q1_conf=r1["confidence"], q1_mass=r1["mass"])
        if self._bad(r1):
            return self._fallback(zone, rec, r1)
        if self._yes(r1):
            rec.update(decision="REFUSE", confidence=r1["confidence"])
            return self._done(rec, Decision("REFUSE", 0.0, f"LLM: уступить? ДА ({self._how(r1)})"))

        r2 = self._ask(ctx, zone_context.question("inflate", zone.name, self.lang, self.question_variant))
        rec.update(q2_p_yes=r2["p"], q2_conf=r2["confidence"], q2_mass=r2["mass"])
        if self._bad(r2):
            return self._fallback(zone, rec, r2)
        p2 = r2["p"]
        if self.soft:
            demand = zone.need * (1 + (self.inflate_factor - 1) * p2)
            dec = "MODIFY" if demand > zone.need * 1.05 else "ACCEPT"
            rec.update(decision=dec, confidence=r2["confidence"])
            return self._done(rec, Decision(dec, demand, f"LLM: запрос x{demand / zone.need:.2f} "
                                                         f"(P(завысить)={p2:.2f})"))
        if self._yes(r2):
            rec.update(decision="MODIFY", confidence=r2["confidence"])
            return self._done(rec, Decision("MODIFY", zone.need * self.inflate_factor,
                                            f"LLM: уступить? НЕТ ({self._how(r1)}); "
                                            f"завысить? ДА ({self._how(r2)})"))
        rec.update(decision="ACCEPT", confidence=r2["confidence"])
        return self._done(rec, Decision("ACCEPT", zone.need,
                                        f"LLM: уступить? НЕТ ({self._how(r1)}); "
                                        f"завысить? НЕТ ({self._how(r2)})"))

    def _how(self, r) -> str:
        """Как получен ответ: при случайном выборе важна P(ДА), иначе -- уверенность."""
        if self.sample:
            return f"P(ДА)={r['p']:.2f}, случайный выбор"
        return f"уверенность {r['confidence']:.2f}"

    def _done(self, rec, d: Decision) -> Decision:
        rec["contested"] = rec["confidence"] < self.contested_floor
        self.records.append(rec)
        d.meta = rec
        return d

    def _fallback(self, zone, rec, r) -> Decision:
        d = self.fallback.decide(zone)
        rec.update(decision=d.decision, confidence=None, contested=False, fallback=True,
                   raw=r["raw"])
        self.records.append(rec)
        why = "Ollama недоступна" if r["raw"].startswith("ошибка Ollama") else "плохой ответ LLM"
        d.reason = f"откат на правило ({why}): " + d.reason
        d.meta = rec
        return d

