import hashlib
import hmac
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

TOKEN = "123456:TEST-TOKEN"
ADMIN_TG = 1000
os.environ.update({
    "DATA_DIR": tempfile.mkdtemp(prefix="starter-test-"),
    "BOT_TOKEN": TOKEN,  # initData is checked against this token
    "RUN_BOT": "0",  # but the bot itself never talks to Telegram in tests
    "SECRET_KEY": "test-secret",
    "ADMIN_IDS": str(ADMIN_TG),
    "DEV_MODE": "0",
    "PUBLIC_URL": "https://example.test",
})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def init_data(tg_id: int, first_name: str = "Test", token: str = TOKEN, auth_date: int | None = None) -> str:
    """Builds initData exactly the way Telegram signs it."""
    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAH",
        "user": json.dumps({"id": tg_id, "first_name": first_name, "language_code": "en"}),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def as_user(tg_id: int, **kw) -> dict:
    return {"X-Init-Data": init_data(tg_id, **kw)}


def jpeg(color=(200, 80, 40), size=(800, 600)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()
