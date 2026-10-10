"""share: placeholder router, already registered in app/main.py. Add the endpoints here (see the work package brief)."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/brief/shares", tags=["share"])
