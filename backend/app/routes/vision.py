"""Vision route — currently re-uses /api/photos/analyze.

This module exists so the vision endpoint can be extended independently
(e.g. for batch analysis, re-analysis, or different model routing).
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["vision"])

# The main analyze endpoint lives in photos.py.
# This router is a placeholder for future vision-specific endpoints.