"""Regenerate the checked-in API contract with deterministic branding."""
import json
import os
os.environ["APP_NAME"] = "Cronicl"
os.environ["APP_IGNORE_DOTENV"] = "1"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app
Path(__file__).resolve().parents[2].joinpath("docs/contracts/openapi.json").write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n")
