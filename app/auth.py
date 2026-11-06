"""Telegram Mini App authentication.

The mini app sends `Telegram.WebApp.initData` in the `X-Init-Data` header.
Telegram signs it with your bot token, so the server can trust the user id
without any login form. See https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import User, get_db

MAX_AGE = 24 * 3600


def verify_init_data(init_data: str, bot_token: str, max_age: int = MAX_AGE) -> dict | None:
    """Returns the Telegram user from initData, or None if it is forged or stale."""
    if not init_data or not bot_token:
        return None
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", None)
    if not received:
        return None
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    if max_age and time.time() - int(pairs.get("auth_date", "0") or 0) > max_age:
        return None
    try:
        user = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError:
        return None
    return user if isinstance(user, dict) and user.get("id") else None


def is_admin(user: User) -> bool:
    return user.tg_id in settings.admin_ids


def current_user(
    x_init_data: str | None = Header(default=None),
    x_dev_tg_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    tg_user = verify_init_data(x_init_data or "", settings.bot_token)
    if not tg_user and settings.dev_mode and x_dev_tg_id and x_dev_tg_id.isdigit():
        tg_user = {"id": int(x_dev_tg_id), "first_name": f"Dev {x_dev_tg_id}"}
    if not tg_user:
        raise HTTPException(401, "Open the app from Telegram")
    user = db.scalar(select(User).where(User.tg_id == tg_user["id"]))
    name = " ".join(x for x in (tg_user.get("first_name"), tg_user.get("last_name")) if x) or str(tg_user["id"])
    if not user:
        # Anyone who opens the bot gets an account. Add your own approval step here if you need one.
        user = User(tg_id=tg_user["id"], full_name=name)
        db.add(user)
    user.username = tg_user.get("username")
    user.lang = tg_user.get("language_code")
    db.commit()
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(403, "Admins only")
    return user
