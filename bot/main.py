import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database.db import create_tables
from bot.middlewares.role_middleware import RoleMiddleware
from bot.middlewares.album_middleware import AlbumMiddleware
from bot.handlers import common, superadmin, admin, user

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    os.makedirs("data", exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)
    await create_tables()
    logger.info("База данных инициализирована.")

    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: @{bot_info.username}")


async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware (порядок: album собирает альбомы → role добавляет db_user)
    dp.message.middleware(AlbumMiddleware())
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    # Роутеры (порядок важен: более специфичные сначала)
    dp.include_router(common.router)
    dp.include_router(superadmin.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await on_startup(bot)

    logger.info("Запуск polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
