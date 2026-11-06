"""One process runs both the bot (long polling) and the web part.

On shared hosting you usually cannot open a public port or receive webhooks
easily, so polling plus a local port behind the hosting's Apache/nginx is the
simplest setup that works everywhere.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import settings
from .db import init_db
from .media import check_sig

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("starter")
WEBAPP = Path(__file__).resolve().parent.parent / "webapp"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = bot = None
    if settings.bot_token and settings.run_bot:
        from .bot import create_bot
        bot, dp = create_bot()
        task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
        log.info("bot started, mini app: %s", settings.public_url)
    else:
        log.warning("bot is off (no BOT_TOKEN or RUN_BOT=0): running the web part only")
    yield
    if task:
        task.cancel()
    if bot:
        await bot.session.close()


app = FastAPI(title="tg-miniapp-starter", lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/media/{path:path}")
def media(path: str, s: str = ""):
    if ".." in path or not check_sig(path, s):
        raise HTTPException(404)
    file = settings.data_dir / "media" / path
    if not file.is_file():
        raise HTTPException(404)
    return FileResponse(file, headers={"Cache-Control": "private, max-age=86400"})


class FreshStatic(StaticFiles):
    """Telegram's in-app browser caches app.js and style.css aggressively, so after an
    update users keep seeing the old version. "no-cache" makes it ask the server every
    time; an unchanged file is answered with 304, so traffic barely grows."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/", FreshStatic(directory=WEBAPP, html=True), name="webapp")
