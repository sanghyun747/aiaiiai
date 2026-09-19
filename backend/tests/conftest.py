import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "vendor" / "follower_diff"))

FIXTURES = BACKEND.parent / "fixtures"


@pytest.fixture
def follower_case():
    return json.loads((FIXTURES / "follower-case.json").read_text(encoding="utf-8"))


@pytest.fixture
def profile_dict():
    return json.loads((FIXTURES / "profile-sample.json").read_text(encoding="utf-8"))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_store():
    """Each API test starts from an empty in-memory store (no JOB_LIMIT bleed)."""
    from app.store import STORE
    STORE._runs.clear()
    STORE._idem.clear()
    STORE._public.clear()
    yield
    STORE._runs.clear()
    STORE._idem.clear()
    STORE._public.clear()
