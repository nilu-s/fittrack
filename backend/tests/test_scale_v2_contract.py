from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import ScaleSyncV2Request
from app.services.scale_assignment import AssignmentRange, choose_assignment
from app.models import DayEntry, Goal, MealEntry, Todo
from app.main import app


def test_account_owned_models_expose_no_compatibility_owner_column():
    for model in (DayEntry, Goal, MealEntry, Todo):
        assert not hasattr(model, "user_id")


def test_openapi_exposes_only_scale_v2_and_no_browser_owner_inputs():
    document = app.openapi()
    assert "/api/scale-sync" not in document["paths"]
    assert "/api/scale-sync/v2" in document["paths"]
    serialized = str(document["components"]["schemas"])
    assert "user_id" not in serialized
    assert '"account_id"' not in serialized


def test_versioned_openapi_snapshot_matches_the_application_contract():
    snapshot_path = Path(__file__).parents[2] / "docs" / "contracts" / "openapi.json"
    assert json.loads(snapshot_path.read_text(encoding="utf-8")) == app.openapi()


def test_device_payload_cannot_carry_an_account_or_body_profile():
    payload = {
        "device_id": "esp32-renpho-aabb-bridge",
        "device_event_id": "event-115",
        "measured_at": "2026-08-31T07:15:02Z",
        "weight_kg": 115.2,
        "impedance_ohm": None,
        "protocol": "renpho-aabb",
        "protocol_version": 1,
        "account_id": "must-not-be-accepted",
        "height_cm": 180,
    }

    with pytest.raises(ValidationError):
        ScaleSyncV2Request.model_validate(payload)


def test_device_event_time_must_be_timezone_aware():
    with pytest.raises(ValidationError, match="timezone"):
        ScaleSyncV2Request.model_validate(
            {
                "device_id": "esp32-renpho-aabb-bridge",
                "device_event_id": "event-naive-time",
                "measured_at": "2026-08-31T07:15:02",
                "weight_kg": 115.2,
                "protocol": "renpho-aabb",
                "protocol_version": 1,
            }
        )


def test_non_overlapping_ranges_assign_only_one_account_or_discard():
    ranges = [
        AssignmentRange(account_id="friend", minimum_kg=45, maximum_kg=85),
        AssignmentRange(account_id="owner", minimum_kg=90, maximum_kg=145),
    ]

    assert choose_assignment(63.0, ranges).account_id == "friend"
    assert choose_assignment(115.0, ranges).account_id == "owner"
    assert choose_assignment(87.0, ranges) is None


def test_ranges_are_rejected_when_they_overlap():
    ranges = [
        AssignmentRange(account_id="friend", minimum_kg=45, maximum_kg=92),
        AssignmentRange(account_id="owner", minimum_kg=90, maximum_kg=145),
    ]

    with pytest.raises(ValueError, match="overlap"):
        choose_assignment(91.0, ranges)


def test_baseline_move_is_limited_to_two_kg_in_seven_days():
    from app.services.scale_assignment import advance_baseline

    moved = advance_baseline(
        baseline_kg=115.0,
        target_kg=108.0,
        previous_updated_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
        now=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )

    assert moved == 113.0
