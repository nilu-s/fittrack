from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config import _DEVELOPMENT_JWT_SECRET, settings, validate_runtime_settings


class RuntimeSecurityTests(unittest.TestCase):
    def test_production_rejects_development_jwt_secret(self):
        with patch.object(settings, "ENVIRONMENT", "production"), patch.object(
            settings, "FITTRACK_JWT_SECRET", _DEVELOPMENT_JWT_SECRET
        ):
            with self.assertRaisesRegex(RuntimeError, "FITTRACK_JWT_SECRET"):
                validate_runtime_settings()

    def test_production_accepts_a_non_default_long_jwt_secret(self):
        with patch.object(settings, "ENVIRONMENT", "production"), patch.object(
            settings, "FITTRACK_JWT_SECRET", "x" * 32
        ):
            validate_runtime_settings()
