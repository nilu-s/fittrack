"""Validate assistant proposals against the same public inputs as manual editors.

This service prepares drafts only. Resource authorization remains mandatory at
execution, using the authenticated account and existing domain services.
"""
from __future__ import annotations

from pydantic import BaseModel
from app import schemas

INPUTS: dict[str, tuple[type[BaseModel], type[BaseModel]]] = {
    "todo": (schemas.TodoCreate, schemas.TodoUpdate),
    "note": (schemas.NoteCreate, schemas.NoteUpdate),
    "shopping": (schemas.ShoppingItemCreate, schemas.ShoppingItemUpdate),
    "routine": (schemas.TodoRoutineCreate, schemas.TodoRoutineUpdate),
    "food": (schemas.FoodCreate, schemas.FoodUpdate),
    "recipe": (schemas.RecipeCreate, schemas.RecipeUpdate),
    "meal": (schemas.MealEntryCreate, schemas.MealEntryUpdate),
    "meal_plan": (schemas.MealPlanCreate, schemas.MealPlanUpdate),
    "training_unit": (schemas.TrainingUnitCreate, schemas.TrainingUnitUpdate),
    "exercise": (schemas.ExerciseCreate, schemas.ExerciseUpdate),
    "rotation": (schemas.TrainingRotationCreate, schemas.TrainingRotationUpdate),
}


def proposal_contract() -> dict:
    """Static field schemas only: never account records, credentials or location."""
    return {kind: {operation: model.model_json_schema() for operation, model in zip(("create", "update"), models)}
            for kind, models in INPUTS.items()}


def validate_proposals(reply: schemas.AssistantResponse) -> schemas.AssistantResponse:
    seen: set[str] = set()
    for action in reply.actions:
        if action.key in seen:
            raise ValueError("Duplicate proposal key")
        seen.add(action.key)
        if action.operation == "update" and not action.target_id:
            raise ValueError("An update requires an explicit target")
        if action.operation == "create" and action.target_id:
            raise ValueError("A create must not specify a target")
        forbidden = {"source", "external_id", "deleted", "place_id", "place_name", "place_address"}
        if forbidden.intersection(action.data):
            raise ValueError("Provenance, deletion and confirmed places are not assistant fields")
        model = INPUTS[action.kind][action.operation == "update"]
        unknown = set(action.data) - set(model.model_fields)
        if unknown:
            raise ValueError("Unknown proposal fields")
        # Assistant drafts do not implicitly activate monitoring or a meal plan.
        if action.data.get("travel_monitoring_enabled") or (action.kind == "meal_plan" and action.data.get("is_active")):
            raise ValueError("Activation requires a separate explicit action")
        validated = model.model_validate(action.data)
        action.data = validated.model_dump(mode="json", exclude_unset=True)
    return reply
