import os
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Tiny .env reader, so the app needs no extra dependency on shared hosting."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _ids(raw: str) -> set[int]:
    return {int(x) for x in raw.replace(" ", "").split(",") if x}


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    # 0 runs only the web part (tests, or a second copy while the main one polls Telegram)
    run_bot: bool = field(default_factory=lambda: os.getenv("RUN_BOT", "1") == "1")
    public_url: str = field(default_factory=lambda: os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/"))
    admin_ids: set[int] = field(default_factory=lambda: _ids(os.getenv("ADMIN_IDS", "")))
    # Everything that grows (database, photos) lives here - keep it outside the web root.
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "./data")).resolve())
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    # Local time used for date stamps on photos and in Excel (default: UTC+5).
    utc_offset_hours: int = field(default_factory=lambda: int(os.getenv("UTC_OFFSET_HOURS", "5")))
    max_photos: int = field(default_factory=lambda: int(os.getenv("MAX_PHOTOS", "5")))
    # Lets you open the mini app in a normal browser as ?dev=<telegram_id>. Never enable in production.
    dev_mode: bool = field(default_factory=lambda: os.getenv("DEV_MODE", "0") == "1")
    # Signs photo links; falls back to the bot token.
    secret: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "media").mkdir(exist_ok=True)
        if not self.database_url:
            self.database_url = f"sqlite:///{self.data_dir / 'app.db'}"
        if not self.secret:
            self.secret = self.bot_token or "dev-secret"

    @property
    def tz(self) -> timezone:
        return timezone(timedelta(hours=self.utc_offset_hours))


settings = Settings()
