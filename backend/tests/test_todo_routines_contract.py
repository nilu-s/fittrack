from datetime import date

import pytest
from pydantic import ValidationError

from app.main import app
from app.schemas import TodoRoutineCreate


def test_todo_routine_requires_distinct_valid_weekdays():
    routine = TodoRoutineCreate(title="Kreatin", weekdays=[6, 0, 2], priority=2)
    assert routine.weekdays == [0, 2, 6]
    with pytest.raises(ValidationError):
        TodoRoutineCreate(title="Doppelt", weekdays=[1, 1])
    with pytest.raises(ValidationError):
        TodoRoutineCreate(title="Ungültig", weekdays=[7])


def test_todo_routine_contract_has_no_client_owned_account_field():
    paths = app.openapi()["paths"]
    assert "/api/todo-routines" in paths
    assert "/api/todo-routines/{routine_id}" in paths
    schemas = str(app.openapi()["components"]["schemas"])
    assert "TodoRoutine" in schemas
    assert "account_id" not in schemas


def test_weekday_values_follow_python_calendar_convention():
    # Monday is 0, the convention exposed by the API and used by materialization.
    assert date(2026, 9, 7).weekday() == 0
