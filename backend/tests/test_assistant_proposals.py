"""Proposal validation is a boundary; no provider or account data needed."""
import pytest
from pydantic import ValidationError
from app.schemas import AssistantResponse
from app.services.assistant import proposal_contract, validate_proposals


def action(kind, data, **extra):
    return {"key": "first", "kind": kind, "label": "Vorschlag", "data": data, **extra}


def reply(*actions):
    return validate_proposals(AssistantResponse(message="Bitte prüfen", actions=list(actions)))


def test_simple_todo_is_a_draft_with_manual_validation():
    result = reply(action("todo", {"title": "Paket", "due_date": "2026-09-11", "priority": 2}))
    assert result.actions[0].data["due_date"] == "2026-09-11"
    with pytest.raises(ValidationError):
        reply(action("todo", {"title": "Paket", "priority": 9}))


@pytest.mark.parametrize("kind,data", [
    ("note", {"title": "Idee", "body": "Wochenende"}),
    ("shopping", {"title": "Milch", "quantity": 1.5, "unit": "l"}),
    ("routine", {"title": "Pflanzen", "weekdays": [1], "due_time": "19:30"}),
    ("food", {"name": "Hafer", "kcal": 300}),
    ("recipe", {"name": "Brei", "servings": 1.5}),
    ("meal_plan", {"name": "Woche", "items": []}),
])
def test_supported_inputs_use_domain_schemas(kind, data):
    assert reply(action(kind, data)).actions[0].kind == kind


@pytest.mark.parametrize("data", [
    {"title": "Paket", "account_id": "foreign"},
    {"title": "Paket", "user_id": "foreign"},
    {"title": "Paket", "source": "google_calendar"},
    {"title": "Paket", "deleted": True},
    {"title": "Paket", "place_id": "invented-place"},
    {"title": "Paket", "travel_monitoring_enabled": True},
])
def test_no_identity_or_implicit_monitoring(data):
    with pytest.raises(ValueError):
        reply(action("todo", data))


def test_update_needs_explicit_target_and_duplicate_keys_rejected():
    with pytest.raises(ValueError):
        reply(action("todo", {"title": "Neu"}, operation="update"))
    with pytest.raises(ValueError):
        reply(action("todo", {"title": "A"}), action("note", {"title": "B"}))
    assert reply(action("todo", {"title": "Neu"}, operation="update", target_id="explicit-id")).actions[0].target_id == "explicit-id"


def test_contract_has_all_planned_kinds_and_no_account_records():
    contract = proposal_contract()
    assert set(contract) == {"todo", "note", "shopping", "routine", "food", "recipe", "meal", "meal_plan", "training_unit", "exercise", "rotation"}
    assert all(set(operations) == {"create", "update"} for operations in contract.values())
