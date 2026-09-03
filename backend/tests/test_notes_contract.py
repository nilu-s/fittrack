"""Public contract checks for private-first notes and calendar planning."""
from __future__ import annotations

import unittest
import uuid

from pydantic import ValidationError

from app.main import app
from app.schemas import NoteCreate, NoteMove, NotePlan


class NotesContractTests(unittest.TestCase):
    def test_note_routes_do_not_accept_client_owned_identity(self):
        paths = app.openapi()["paths"]
        self.assertIn("/api/notes", paths)
        self.assertIn("/api/notes/{note_id}/move", paths)
        self.assertIn("/api/notes/{note_id}/plan", paths)
        with self.assertRaises(ValidationError):
            NoteCreate(title="Privat", account_id=uuid.uuid4())

    def test_sharing_requires_an_explicit_boolean_and_planning_has_a_date(self):
        space_id = uuid.uuid4()
        self.assertFalse(NoteMove(space_id=space_id).confirm_share)
        self.assertTrue(NoteMove(space_id=space_id, confirm_share=True).confirm_share)
        with self.assertRaises(ValidationError):
            NotePlan()


if __name__ == "__main__":
    unittest.main()
