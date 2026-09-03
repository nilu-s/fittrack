"""Contract checks for explicit, member-authorized shared workspaces."""
from __future__ import annotations

import unittest
import uuid

from fastapi import HTTPException
from pydantic import ValidationError

from app.main import app
from app.schemas import SpaceCreate, SpaceInviteCreate, SpaceProjectCreate, TodoCreate
from app.services.spaces import validate_assignee, validate_project


class _Session:
    def __init__(self): self.statements = []
    async def scalar(self, statement): self.statements.append(statement); return None


class SharedSpacesContractTests(unittest.IsolatedAsyncioTestCase):
    def test_public_contract_exposes_spaces_without_client_owned_identity(self):
        paths = app.openapi()["paths"]
        self.assertIn("/api/spaces", paths)
        self.assertIn("/api/spaces/{space_id}/invitations", paths)
        self.assertIn("/api/spaces/{space_id}/projects", paths)
        self.assertIn("/api/space-invitations/{invitation_id}/accept", paths)
        with self.assertRaises(ValidationError):
            SpaceCreate(name="Haushalt", owner_account_id=uuid.uuid4())
        with self.assertRaises(ValidationError):
            SpaceInviteCreate(email="a@example.test", invited_account_id=uuid.uuid4())

    def test_todo_contract_accepts_only_resource_references(self):
        todo = TodoCreate(title="Müll rausbringen", space_id=uuid.uuid4(), project_id=uuid.uuid4(), assignee_id=uuid.uuid4())
        self.assertIsNotNone(todo.space_id)
        with self.assertRaises(ValidationError):
            TodoCreate(title="Fremd", account_id=uuid.uuid4())

    async def test_project_and_assignee_are_rejected_without_a_matching_space(self):
        session = _Session()
        with self.assertRaises(HTTPException) as project_error:
            await validate_project(session, uuid.uuid4(), None)
        self.assertEqual(project_error.exception.status_code, 422)
        with self.assertRaises(HTTPException) as assignee_error:
            await validate_assignee(session, uuid.uuid4(), None)
        self.assertEqual(assignee_error.exception.status_code, 422)

    async def test_project_and_assignee_must_be_members_of_the_same_space(self):
        session = _Session()
        space_id = uuid.uuid4()
        with self.assertRaises(HTTPException) as project_error:
            await validate_project(session, uuid.uuid4(), space_id)
        with self.assertRaises(HTTPException) as assignee_error:
            await validate_assignee(session, uuid.uuid4(), space_id)
        self.assertEqual(project_error.exception.status_code, 422)
        self.assertEqual(assignee_error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
