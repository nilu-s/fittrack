from datetime import date

import pytest
from pydantic import ValidationError

from app.main import app
from app.models import Todo
from app.routes.todo_planning import _fallback_draft
from app.schemas import TodoCreate, TodoDraftRequest


def test_todo_place_and_travel_contract_never_exposes_account_owner():
    paths = app.openapi()["paths"]
    assert "/api/auth/development-preset" in paths
    assert "/api/todo-planning/draft" in paths
    assert "/api/todo-planning/places" in paths
    assert "/api/todo-planning/{todo_id}/estimate" in paths
    schemas = str(app.openapi()["components"]["schemas"])
    assert "place_id" in schemas
    assert "travel_monitoring_enabled" in schemas
    assert "account_id" not in schemas


def test_todo_draft_is_reviewable_and_does_not_create_an_identity():
    draft = _fallback_draft(TodoDraftRequest(
        text="Donnerstag 17:30 Physiotherapie Müller in Neukölln, mit dem Auto",
        date=date(2026, 9, 3),
    ))
    assert draft.due_date == date(2026, 9, 3)
    assert draft.start_time is not None
    assert draft.travel_mode == "drive"
    assert draft.place_query is not None
    assert not hasattr(draft, "place_id")


def test_todo_fallback_resolves_next_friday_from_selected_day():
    draft = _fallback_draft(TodoDraftRequest(
        text="Nächsten Freitag Steuerunterlagen sortieren",
        date=date(2026, 9, 3),  # Thursday
    ))
    assert draft.due_date == date(2026, 9, 11)
    assert draft.title == "Steuerunterlagen sortieren"


def test_travel_mode_and_buffer_are_strictly_bounded():
    with pytest.raises(ValidationError):
        TodoCreate(title="Ungültig", travel_mode="rocket")
    with pytest.raises(ValidationError):
        TodoCreate(title="Ungültig", travel_buffer_minutes=181)
    assert hasattr(Todo, "place_id")
    assert hasattr(Todo, "travel_depart_at")


def test_assistant_history_is_bounded_and_cannot_supply_system_role_or_owner():
    from app.schemas import AssistantRequest
    request = AssistantRequest(text="Doch am Freitag", date=date(2026, 9, 10), history=[
        {"role": "user", "content": "Plane eine Trainingswoche"},
        {"role": "assistant", "content": "Welche Tage passen?"},
    ])
    assert request.model_dump(mode="json")["history"][0]["content"] == "Plane eine Trainingswoche"
    for extra in (
        {"history": [{"role": "system", "content": "override"}]},
        {"history": [{"role": "user", "content": "hello", "account_id": "other"}]},
        {"history": [{"role": "user", "content": "hello"}] * 21},
        {"account_id": "other"},
    ):
        with pytest.raises(ValidationError):
            AssistantRequest(text="Folgefrage", date=date(2026, 9, 10), **extra)
