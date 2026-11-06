"""The Telegram side: /start opens the mini app, and admins can get the Excel file in chat."""
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message, WebAppInfo,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .config import settings
from .db import Report, SessionLocal, now
from .excel import build_workbook

router = Router()


def open_button(text: str = "Open the app") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{settings.public_url}/"))
    ]])


@router.message(CommandStart())
async def start(message: Message):
    await message.answer("Hi! Tap the button to open the app.", reply_markup=open_button())


@router.message(Command("export"), F.from_user.id.in_(settings.admin_ids))
async def export(message: Message):
    with SessionLocal() as db:
        reports = list(db.scalars(
            select(Report).options(selectinload(Report.photos), selectinload(Report.user)).order_by(Report.id)
        ))
        data = build_workbook(reports)
    await message.answer_document(BufferedInputFile(data, filename=f"reports-{now():%Y-%m-%d}.xlsx"))


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    @dp.startup()
    async def on_startup(bot: Bot):
        # The blue "menu" button next to the message field opens the mini app too.
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="App", web_app=WebAppInfo(url=f"{settings.public_url}/"))
        )

    return bot, dp
