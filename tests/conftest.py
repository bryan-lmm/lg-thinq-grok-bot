from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_model() -> dict:
    path = FIXTURE_DIR / "sample_tower_washer.json"
    return json.loads(path.read_text(encoding="utf-8"))
