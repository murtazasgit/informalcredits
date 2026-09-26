"""
Case 3 — Counterfactual "Target Achievement".

Public API (handoff to backend/api/ /target-achievement):
    find_min_change(features: UserFeatures, target_score: int, compute_score_fn,
                    target_product_name: str | None = None) -> dict

compute_score_fn is the REAL rule engine's compute_score() from backend/scoring_engine/, passed in
by the caller. This module never imports the scoring engine and never re-implements its point
table — it only nudges features and asks compute_score_fn for the new score. So if a teammate
tweaks a threshold, this module still gives correct advice with zero changes.

How the greedy search works:
  1. For each actionable sub-factor ("lever"), walk its value in small steps in the helpful
     direction (e.g. savings_days 27 -> 30 -> 35 -> ...) and re-score after each step.
     Every step that raises the score becomes a candidate change.
  2. Each candidate gets an effort number = |change| / effort_scale (effort 1.0 is roughly
     "a solid 3-month push", see LEVERS). This makes days, % and ratios comparable.
  3. If any single candidate closes the whole gap: pick the one with the lowest effort.
     Otherwise: pick the best points-per-effort candidate, apply it, and repeat (up to
     max_plan_steps) to build a short step-by-step plan.

Not levers (on purpose): education, housing and past delinquencies can't be changed by a quick
behavioural nudge; bonus/penalty counts are left to the scoring engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Optional

from common.schemas import UserFeatures

MAX_SCORE = 1000
_EPS = 1e-9


@dataclass(frozen=True)
class Lever:
    field: str           # UserFeatures field that gets nudged
    sub_factor: str      # matching ScoreBreakdown key (used in the output contract)
    label: str           # human-readable name
    direction: int       # +1 = higher is better, -1 = lower is better
    step: float          # search granularity; values are snapped to multiples of this
    max_change: float    # don't search further than this from the current value
    effort_scale: float  # change that counts as effort 1.0 (~ a solid 3-month push)
    unit: str            # "%", " days", " months", or "ratio" (shown as %)
    is_int: bool
    tip: str


# Tune effort_scale to change which advice "feels" easiest. Smaller = harder per unit.
LEVERS: tuple[Lever, ...] = (
    Lever("savings_days", "savings", "Savings buffer", +1, 5, 365, 90, " days", True,
          "Move a fixed amount into savings on payday, before you start spending."),
    Lever("cashflow_volatility_pct", "cashflow_volatility", "Cash-flow volatility", -1, 0.5, 100, 10, "%", False,
          "Split big irregular expenses into monthly amounts and put fixed bills on auto-pay."),
    Lever("on_time_payment_pct", "on_time_payment", "On-time payment rate", +1, 0.5, 100, 10, "%", False,
          "Turn on auto-pay for rent, EMIs and utilities so no due date slips."),
    Lever("digital_bill_ontime_pct", "digital_footprint", "Digital bills paid on time", +1, 1, 100, 20, "%", False,
          "Pay mobile, internet and electricity bills through UPI autopay."),
    Lever("credit_utilization_pct", "credit_utilization", "Credit utilization", -1, 1, 100, 30, "%", False,
          "Pay down card balances before the statement date, or split spend across limits."),
    Lever("spend_to_income_ratio", "spend_to_income", "Spend-to-income ratio", -1, 0.01, 5, 0.20, "ratio", False,
          "Set a weekly cap on discretionary spending like dining out and shopping."),
    Lever("essential_spend_pct", "expense_diversity", "Share of spend on essentials", +1, 1, 100, 20, "%", False,
          "Trim non-essential purchases so rent, bills and groceries make up more of your spend."),
    Lever("debt_to_income_ratio", "debt_to_income", "Debt-to-income ratio", -1, 0.01, 5, 0.20, "ratio", False,
          "Prepay your smallest loan first to remove an EMI entirely."),
    Lever("months_employed", "employment_stability", "Months at current job", +1, 1, 24, 12, " months", True,
          "Staying with your current employer a little longer counts in your favour."),
)


@dataclass
class _Candidate:
    lever: Lever
    old_value: float
    new_value: float
    gain: int
    new_score: int

    @property
    def effort(self) -> float:
        return abs(self.new_value - self.old_value) / self.lever.effort_scale


# ---------------------------------------------------------------- compute_score_fn adapter
# The team READMEs disagree on compute_score's signature: scoring_engine/README says
# dict -> dict, testing/README and ml_engine/README use UserFeatures -> ScoreResult.
# This adapter accepts either, so find_min_change works whichever one ships.

def _dump(features: UserFeatures) -> dict:
    return features.model_dump() if hasattr(features, "model_dump") else features.dict()


def _copy_with(features: UserFeatures, **changes) -> UserFeatures:
    if hasattr(features, "model_copy"):
        return features.model_copy(update=changes)
    return features.copy(update=changes)


def _extract_total(result: Any) -> int:
    if hasattr(result, "total_score"):
        return int(result.total_score)
    if isinstance(result, dict):
        return int(result["total_score"])
    return int(result)


def _make_scorer(compute_score_fn: Callable) -> Callable[[UserFeatures], int]:
    mode: dict[str, Optional[str]] = {"input": None}

    def score(features: UserFeatures) -> int:
        if mode["input"] == "dict":
            return _extract_total(compute_score_fn(_dump(features)))
        if mode["input"] == "model":
            return _extract_total(compute_score_fn(features))
        try:
            total = _extract_total(compute_score_fn(features))
            mode["input"] = "model"
        except (TypeError, KeyError, AttributeError):
            total = _extract_total(compute_score_fn(_dump(features)))
            mode["input"] = "dict"
        return total

    return score


# ---------------------------------------------------------------- search

def _grid(current: float, lever: Lever):
    """Values beyond `current`, in the helpful direction, snapped to multiples of lever.step."""
    step = lever.step
    limit = current + lever.direction * lever.max_change
    if lever.direction > 0:
        k = math.floor(current / step + _EPS) + 1
        limit = min(limit, 100.0) if lever.unit == "%" else limit
        while (v := round(k * step, 6)) <= limit + _EPS:
            yield int(v) if lever.is_int else v
            k += 1
    else:
        k = math.ceil(current / step - _EPS) - 1
        limit = max(limit, 0.0)
        while k >= 0 and (v := round(k * step, 6)) >= limit - _EPS:
            yield int(v) if lever.is_int else v
            k -= 1


def _scan(features: UserFeatures, base_score: int, gap: int, score_fn) -> list[_Candidate]:
    """Every value where a single lever raises the score, stopping once that lever closes the gap."""
    candidates = []
    for lever in LEVERS:
        current = float(getattr(features, lever.field))
        best_gain = 0
        for value in _grid(current, lever):
            new_score = score_fn(_copy_with(features, **{lever.field: value}))
            gain = new_score - base_score
            if gain > best_gain:
                best_gain = gain
                candidates.append(_Candidate(lever, current, value, gain, new_score))
                if gain >= gap:
                    break  # anything further along this lever costs more for the same result
    return candidates


def _choose(candidates: list[_Candidate], gap: int) -> tuple[Optional[_Candidate], bool]:
    closers = [c for c in candidates if c.gain >= gap]
    if closers:
        return min(closers, key=lambda c: (c.effort, -c.gain)), True
    if not candidates:
        return None, False
    return max(candidates, key=lambda c: (c.gain / max(c.effort, _EPS), c.gain)), False


# ---------------------------------------------------------------- formatting

def _fmt(value: float, lever: Lever) -> str:
    if lever.unit == "ratio":
        return f"{value * 100:g}%"
    if lever.is_int:
        return f"{int(value)}{lever.unit}"
    return f"{round(value, 2):g}{lever.unit}"


def _change_dict(lever: Lever, old_value: float, new_value: float, gain: int) -> dict:
    return {
        "sub_factor": lever.sub_factor,
        "feature_field": lever.field,
        "label": lever.label,
        "current_value": _fmt(old_value, lever),
        "target_value": ("≥" if lever.direction > 0 else "≤") + _fmt(new_value, lever),
        "current_raw": old_value,
        "target_raw": new_value,
        "expected_point_gain": gain,
        "effort": round(abs(new_value - old_value) / lever.effort_scale, 2),
        "tip": lever.tip,
    }


def _sentence(step: dict, lever: Lever) -> str:
    verb = "increase" if lever.direction > 0 else "reduce"
    return (f"{verb} your {lever.label.lower()} from {step['current_value']} to "
            f"{step['target_value'][1:]} (+{step['expected_point_gain']} pts)")


# ---------------------------------------------------------------- public API

def find_min_change(
    features: UserFeatures,
    target_score: int,
    compute_score_fn: Callable,
    target_product_name: Optional[str] = None,
    max_plan_steps: int = 4,
) -> dict:
    """Find the smallest, most achievable change that lifts `features` to `target_score`."""
    if isinstance(features, dict):
        features = UserFeatures(**features)
    if isinstance(target_score, bool) or not isinstance(target_score, int):
        raise TypeError("target_score must be an int")
    if not 0 <= target_score <= MAX_SCORE:
        raise ValueError(f"target_score must be between 0 and {MAX_SCORE}, got {target_score}")

    score_fn = _make_scorer(compute_score_fn)
    current_score = score_fn(features)
    gap = target_score - current_score
    goal = f"unlock the {target_product_name}" if target_product_name else f"reach a score of {target_score}"

    result = {
        "user_id": features.user_id,
        "target_product": target_product_name,
        "current_score": current_score,
        "target_score": target_score,
        "score_gap": max(gap, 0),
        "suggested_change": None,
        "single_change_closes_gap": False,
        "plan": [],
        "projected_score": current_score,
        "gap_closed": gap <= 0,
        "message": "",
    }
    if gap <= 0:
        result["message"] = (f"You already qualify: your score of {current_score} meets the "
                             f"{target_score} needed to {goal}.")
        return result

    # Greedy loop: pick the best change, apply it, repeat until the gap is closed.
    working, score = features, current_score
    plan: dict[str, dict] = {}      # field -> merged step, insertion-ordered
    lever_by_field = {lv.field: lv for lv in LEVERS}
    first_step_closes = None
    for _ in range(max_plan_steps):
        remaining = target_score - score
        if remaining <= 0:
            break
        best, closes = _choose(_scan(working, score, remaining, score_fn), remaining)
        if best is None:
            break
        if first_step_closes is None:
            first_step_closes = closes
        lv = best.lever
        original = float(getattr(features, lv.field))
        prev_gain = plan[lv.field]["expected_point_gain"] if lv.field in plan else 0
        plan[lv.field] = _change_dict(lv, original, best.new_value, prev_gain + best.gain)
        working = _copy_with(working, **{lv.field: best.new_value})
        score = best.new_score

    steps = list(plan.values())
    result.update(
        suggested_change=steps[0] if steps else None,
        single_change_closes_gap=bool(first_step_closes),
        plan=steps,
        projected_score=score,
        gap_closed=score >= target_score,
    )

    if not steps:
        result["message"] = (f"Your score is {current_score}, {gap} points short of what's needed to {goal}, "
                             f"and none of the quick-win factors can raise it further right now. "
                             f"Longer-term factors (education, housing, clearing past delinquencies) are the path here.")
    elif first_step_closes:
        s = steps[0]
        result["message"] = (f"To {goal}, {_sentence(s, lever_by_field[s['feature_field']])}, "
                             f"taking you from {current_score} to {score}. Tip: {s['tip']}")
    else:
        parts = [_sentence(s, lever_by_field[s["feature_field"]]) for s in steps]
        ending = (f"Together these take you from {current_score} to {score}, enough to {goal}."
                  if score >= target_score else
                  f"Together these take you from {current_score} to {score}, still "
                  f"{target_score - score} short, so reaching this target needs longer-term improvements too.")
        result["message"] = (f"No single change closes your {gap}-point gap. Step by step: "
                             + "; then ".join(parts) + f". {ending} First tip: {steps[0]['tip']}")
    return result