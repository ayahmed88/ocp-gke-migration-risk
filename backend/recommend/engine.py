"""Deterministic, traceable recommendation engine (Phase 4C).

evaluate(features, prediction) -> ordered recommendations, each carrying:
  rule id · action key · priority · stage · the exact condition values that
  fired it · the historical-evidence line from the rulebook.
Rules whose fields are unavailable at this stage (e.g. execution signals in a
pre-execution form) are simply not evaluable — reported separately, never
silently guessed.
"""
from __future__ import annotations
from pathlib import Path
import yaml

RULES_PATH = Path(__file__).with_name("rules.yaml")
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def load_rules() -> list[dict]:
    return yaml.safe_load(RULES_PATH.read_text())


def _check(cond: dict, ctx: dict):
    """-> (fired: bool|None, detail: str). None = field unavailable."""
    if "any" in cond or "all" in cond:
        mode = "any" if "any" in cond else "all"
        results = [_check(c, ctx) for c in cond[mode]]
        if any(r[0] is None for r in results) and not (
                mode == "any" and any(r[0] is True for r in results)):
            return None, ""
        fired = (any if mode == "any" else all)(bool(r[0]) for r in results)
        detail = " | ".join(d for f, d in results if f) if mode == "any" \
            else " & ".join(d for _, d in results)
        return fired, detail
    field, op, val = cond["field"], cond["op"], cond["value"]
    if field not in ctx:
        return None, ""
    actual = ctx[field]
    try:
        if op == "==":
            fired = str(actual) == str(val) if isinstance(val, str) else float(actual) == float(val)
        elif op == ">=":
            fired = float(actual) >= float(val)
        elif op == "in":
            fired = str(actual) in [str(v) for v in val]
        else:
            raise ValueError(f"unknown op {op}")
    except (TypeError, ValueError):
        return False, f"{field} = {actual!r} (uninterpretable)"
    return fired, f"{field} = {actual}"


def evaluate(features: dict, prediction: str | None = None) -> dict:
    ctx = dict(features)
    if prediction is not None:
        ctx["__prediction__"] = prediction
    fired, not_evaluable = [], []
    for rule in load_rules():
        if rule["trigger"] == "fallback":
            fallback = rule
            continue
        ok, detail = _check(rule["trigger"], ctx)
        if ok is None:
            not_evaluable.append({"rule_id": rule["id"], "action": rule["action"],
                                  "stage": rule["stage"]})
        elif ok:
            fired.append({"rule_id": rule["id"], "action": rule["action"],
                          "priority": rule["priority"], "stage": rule["stage"],
                          "triggered_by": detail, "evidence": rule["evidence"]})
    if not fired:
        fired.append({"rule_id": fallback["id"], "action": fallback["action"],
                      "priority": fallback["priority"], "stage": fallback["stage"],
                      "triggered_by": "no other rule fired",
                      "evidence": fallback["evidence"]})
    fired.sort(key=lambda r: _PRIORITY_ORDER[r["priority"]])
    return {"recommendations": fired,
            "not_evaluable_at_this_stage": not_evaluable,
            "governance": "Layer separation: ML prediction → explanation → "
                          "rule-based recommendation → human expert decision. "
                          "The system supports the decision; it never replaces expert sign-off."}
