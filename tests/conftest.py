import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

TEST_DB = ROOT / "data" / "test_tap.db"
os.environ["TAP_DB_PATH"] = str(TEST_DB)

from backend.app.db import init_db
from backend.app.main import app


@pytest.fixture
def client():
    if TEST_DB.exists():
        TEST_DB.unlink()

    init_db()

    with TestClient(app) as test_client:
        yield test_client

    if TEST_DB.exists():
        TEST_DB.unlink()