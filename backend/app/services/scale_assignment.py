"""Pure rules for assigning a shared scale event without exposing accounts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class AssignmentRange:
    account_id: str
    minimum_kg: float
    maximum_kg: float

    def matches(self, weight_kg: float) -> bool:
        return self.minimum_kg <= weight_kg <= self.maximum_kg


def _validate_ranges(ranges: list[AssignmentRange]) -> None:
    ordered = sorted(ranges, key=lambda item: item.minimum_kg)
    for left, right in zip(ordered, ordered[1:]):
        if left.maximum_kg >= right.minimum_kg:
            raise ValueError("assignment ranges overlap")


def choose_assignment(weight_kg: float, ranges: list[AssignmentRange]) -> AssignmentRange | None:
    """Return the sole matching account range, or None for a discarded event."""
    _validate_ranges(ranges)
    matches = [item for item in ranges if item.matches(weight_kg)]
    return matches[0] if len(matches) == 1 else None


def advance_baseline(
    *,
    baseline_kg: float,
    target_kg: float,
    previous_updated_at: datetime,
    now: datetime,
) -> float:
    """Move a range baseline toward a rolling-median target by <=2 kg/week."""
    elapsed_days = max((now.date() - previous_updated_at.date()).days, 0)
    maximum_change = Decimal("2") * Decimal(elapsed_days) / Decimal("7")
    delta = Decimal(str(target_kg)) - Decimal(str(baseline_kg))
    if abs(delta) > maximum_change:
        delta = maximum_change.copy_sign(delta)
    return float((Decimal(str(baseline_kg)) + delta).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
