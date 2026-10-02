"""Durable per-attempt usage, including unknown outcomes and local reuse."""
import json
import time
from collections import defaultdict
from sqlalchemy import update, null
from api.models.database_models import Job, Book, CostLog
from api.config.settings import settings

# Standard rates checked on 2026-10-02. Unknown models never inherit another price.
# https://developers.openai.com/api/docs/models/gpt-5
# https://developers.openai.com/api/docs/models/gpt-6.1-sol
# https://developers.openai.com/api/docs/models/tts-1-hd
PRICES = {"openai:gpt-5": {"input": 1.25, "cached": .125, "output": 10},
          "openai:gpt-5-2025-08-07": {"input": 1.25, "cached": .125, "output": 10},
          "openai:gpt-6.1-sol": {"input": 2, "cached": .10, "cache_write": 2.50, "output": 10,
                                "long_context_threshold": 272000, "long_input_factor": 2,
                                "long_output_factor": 1.5},
          "openai:tts-1-hd": {"character": .000030},
          "openai:tts-1": {"character": .000015}}


def price_reply(provider, reply):
    prices = {**PRICES, **settings.production_prices}
    rate = prices.get(provider + ":" + reply.model)
    if not rate:
        return None
    if reply.characters:
        return reply.characters * rate["character"] if "character" in rate else None
    if reply.input_tokens is None or reply.output_tokens is None:
        return None
    if not all(k in rate for k in ("input", "cached", "output")):
        return None
    cached = min(reply.cached_input, reply.input_tokens)
    writes = min(reply.cache_write, reply.input_tokens - cached)
    if writes and "cache_write" not in rate:
        return None
    long = reply.input_tokens > rate.get("long_context_threshold", float("inf"))
    input_factor = rate.get("long_input_factor", 1) if long else 1
    output_factor = rate.get("long_output_factor", 1) if long else 1
    return (((reply.input_tokens - cached - writes) * rate["input"] + cached * rate["cached"]
             + writes * rate.get("cache_write", 0)) * input_factor
            + reply.output_tokens * rate["output"] * output_factor) / 1_000_000


class UsageRecorder:
    def __init__(self, db, job):
        self.db, self.job = db, job

    def run(self, phase, provider, function):
        row = CostLog(job_id=self.job.job_id, book_id=self.job.book_id, user_id=self.job.user_id,
            operation=phase, step_name=self.job.current_step, provider=provider.name,
            model=provider.model, cost_usd=null(),
            details=json.dumps({"status": "started", "usage_known": False}))
        self.db.add(row)
        self.db.commit()
        started = time.monotonic()
        try:
            reply = function()
        except Exception as exc:
            row.details = json.dumps({"status": "failed", "usage_known": False,
                                      "error_type": type(exc).__name__, "seconds": round(time.monotonic() - started, 3)})
            self.db.commit()
            raise
        cost = price_reply(provider.name, reply)
        known = reply.characters > 0 or (reply.input_tokens is not None and reply.output_tokens is not None)
        row.model = reply.model
        row.input_tokens = reply.input_tokens or 0
        row.output_tokens = reply.output_tokens or 0
        row.characters = reply.characters
        row.cost_usd = cost
        row.details = json.dumps({"status": "completed", "usage_known": known,
            "cached_input": reply.cached_input, "cache_write": reply.cache_write, "reasoning": reply.reasoning,
            "raw_usage": reply.raw_usage, "request_id": reply.request_id,
            "seconds": round(time.monotonic() - started, 3), "price_basis": "configured_standard_estimate"})
        is_audio = phase == "audio"
        values = {"input_tokens": Job.input_tokens + (reply.input_tokens or 0),
                  "output_tokens": Job.output_tokens + (reply.output_tokens or 0),
                  "total_tokens": Job.total_tokens + (reply.input_tokens or 0) + (reply.output_tokens or 0),
                  "total_characters": Job.total_characters + reply.characters,
                  "total_cost_usd": Job.total_cost_usd + (cost or 0)}
        values["tts_cost_usd" if is_audio else "llm_cost_usd"] = (
            Job.tts_cost_usd if is_audio else Job.llm_cost_usd) + (cost or 0)
        self.db.execute(update(Job).where(Job.job_id == self.job.job_id).values(**values))
        if self.job.book_id and cost is not None:
            field = Book.total_tts_cost_usd if is_audio else Book.total_llm_cost_usd
            self.db.execute(update(Book).where(Book.book_id == self.job.book_id).values(
                {field.key: field + cost, "total_cost_usd": Book.total_cost_usd + cost}))
        self.db.commit()
        return reply

    def cache_hit(self, phase):
        row = CostLog(job_id=self.job.job_id, book_id=self.job.book_id, user_id=self.job.user_id,
            operation=phase, provider="local_cache", model="checkpoint", cost_usd=0,
            details=json.dumps({"status": "reused", "usage_known": True}))
        self.db.add(row)
        self.db.commit()


def usage_report(db, job_id):
    rows = db.query(CostLog).filter(CostLog.job_id == job_id).order_by(CostLog.log_id).all()
    phases = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0, "cached_input": 0, "cache_write": 0,
        "reasoning": 0, "characters": 0, "known_cost_usd": 0., "unknown_calls": 0, "cache_hits": 0})
    calls = []
    for row in rows:
        details = json.loads(row.details or "{}")
        phase = phases[row.operation]
        reused = details.get("status") == "reused"
        phase["cache_hits" if reused else "calls"] += 1
        phase["input"] += row.input_tokens or 0
        phase["output"] += row.output_tokens or 0
        phase["characters"] += row.characters or 0
        phase["cached_input"] += details.get("cached_input", 0)
        phase["cache_write"] += details.get("cache_write", 0)
        phase["reasoning"] += details.get("reasoning", 0)
        phase["known_cost_usd"] += row.cost_usd or 0
        if not reused and (not details.get("usage_known") or row.cost_usd is None):
            phase["unknown_calls"] += 1
        calls.append({"id": row.log_id, "phase": row.operation, "provider": row.provider,
            "model": row.model, "input": row.input_tokens if details.get("usage_known") else None,
            "output": row.output_tokens if details.get("usage_known") else None,
            "characters": row.characters, "cost_usd": row.cost_usd, **details})
    totals = {key: sum(p[key] for p in phases.values()) for key in
              ("calls", "input", "output", "cached_input", "cache_write", "reasoning", "characters", "known_cost_usd", "unknown_calls", "cache_hits")}
    return {"totals": totals, "estimated_cost_usd": totals["known_cost_usd"] if not totals["unknown_calls"] else None,
            "phases": [{"phase": k, **v} for k, v in phases.items()], "calls": calls,
            "note": "USD-Kosten sind Schätzungen anhand konfigurierter Standardpreise. "
                "Cache und Reasoning sind Teilmengen von Input und Output. Unbekannte Aufrufe sind nicht kostenlos."}
