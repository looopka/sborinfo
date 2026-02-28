from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.config import settings
from bot.database.queries import (
    get_invite_link_by_token,
    add_user_to_event,
    get_user_active_events,
)
from bot.utils.helpers import get_menu_for_role

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: dict):
    args = message.text.split(maxsplit=1)
    token = args[1].strip() if len(args) > 1 else None
    role = db_user.get("role", "user")

    # Обработка токена приглашения
    if token:
        link_data = await get_invite_link_by_token(token)
        if not link_data:
            await message.answer("❌ Ссылка недействительна или была отозвана.")
        elif not link_data["is_active"]:
            await message.answer("❌ Эта пригласительная ссылка деактивирована.")
        else:
            await add_user_to_event(message.from_user.id, link_data["event_id"])
            event_name = link_data["event_name"]
            await message.answer(
                f"✅ Вы подключены к событию <b>{event_name}</b>!\n\n"
                "Теперь вы можете загружать файлы в это событие.",
                parse_mode="HTML",
                reply_markup=get_menu_for_role(db_user),
            )
            return

    # Меню по роли
    role_labels = {"superadmin": "суперадмин", "admin": "администратор"}
    label = role_labels.get(role, "")
    greeting = f"👋 Привет, {label + ' ' if label else ''}<b>{message.from_user.first_name}</b>!\n\n"

    if role in ("superadmin", "admin"):
        await message.answer(
            greeting + "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_menu_for_role(db_user),
        )
    else:
        events = await get_user_active_events(message.from_user.id)
        if events:
            await message.answer(
                greeting + "Используйте меню для загрузки файлов.",
                parse_mode="HTML",
                reply_markup=get_menu_for_role(db_user),
            )
        else:
            await message.answer(
                greeting + "Для участия в событии вам нужна пригласительная ссылка от администратора.",
                parse_mode="HTML",
            )
