"""Contract checks for consent-based contacts without resource sharing."""
import uuid
import unittest
from pydantic import ValidationError
from app.main import app
from app.schemas import AccountAliasUpdate, ContactInviteCreate

class ContactContractTests(unittest.TestCase):
    def test_contact_endpoints_and_no_client_identity(self):
        paths = app.openapi()["paths"]
        self.assertIn("/api/contacts", paths)
        self.assertIn("/api/contacts/search", paths)
        self.assertIn("/api/contacts/invitations", paths)
        self.assertIn("/api/contact-invitations/{invitation_id}/accept", paths)
        self.assertIn("/api/auth/alias", paths)
        self.assertEqual(AccountAliasUpdate(alias="@Alex_7").alias, "alex_7")
        with self.assertRaises(ValidationError): ContactInviteCreate(alias="a@example.test", invited_account_id=uuid.uuid4())
        with self.assertRaises(ValidationError): ContactInviteCreate(alias="a@example.test")

if __name__ == "__main__": unittest.main()
