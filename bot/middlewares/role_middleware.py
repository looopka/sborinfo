from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

from bot.config import settings
from bot.database.queries import upsert_user, get_user, set_user_role


class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None

        if isinstance(event, (Message, CallbackQuery)):
            tg_user = event.from_user
        elif isinstance(event, Update):
            if event.message:
                tg_user = event.message.from_user
            elif event.callback_query:
                tg_user = event.callback_query.from_user
            else:
                tg_user = None
        else:
            tg_user = getattr(event, "from_user", None)

        if tg_user:
            db_user = await upsert_user(
                telegram_id=tg_user.id,
                username=tg_user.username or "",
                first_name=tg_user.first_name or "",
                last_name=tg_user.last_name or "",
            )
            # Если это суперадмин — принудительно ставим роль
            if tg_user.id == settings.superadmin_id and db_user.get("role") != "superadmin":
                await set_user_role(tg_user.id, "superadmin")
                db_user["role"] = "superadmin"

            data["db_user"] = db_user

        return await handler(event, data)
