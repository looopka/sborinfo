import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str
    superadmin_id: int
    yandex_disk_token: str
    yandex_disk_root: str
    db_path: str
    temp_dir: str


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN")
    superadmin_id = os.getenv("SUPERADMIN_ID")
    yandex_disk_token = os.getenv("YANDEX_DISK_TOKEN")

    if not bot_token:
        raise ValueError("BOT_TOKEN не задан в .env")
    if not superadmin_id:
        raise ValueError("SUPERADMIN_ID не задан в .env")
    if not yandex_disk_token:
        raise ValueError("YANDEX_DISK_TOKEN не задан в .env")

    return Settings(
        bot_token=bot_token,
        superadmin_id=int(superadmin_id),
        yandex_disk_token=yandex_disk_token,
        yandex_disk_root=os.getenv("YANDEX_DISK_ROOT", "SborInfo"),
        db_path=os.getenv("DB_PATH", "data/sborinfo.db"),
        temp_dir=os.getenv("TEMP_DIR", "temp"),
    )


settings = get_settings()
