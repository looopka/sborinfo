import asyncio
import os
from functools import partial

import yadisk

from bot.config import settings


def _get_client() -> yadisk.YaDisk:
    return yadisk.YaDisk(token=settings.yandex_disk_token)


def _ensure_folder_sync(client: yadisk.YaDisk, path: str):
    """Создаёт папку и все родительские папки при необходимости."""
    parts = path.strip("/").split("/")
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else part
        if not client.exists(current):
            client.mkdir(current)


def _upload_file_sync(client: yadisk.YaDisk, local_path: str, remote_path: str):
    client.upload(local_path, remote_path, overwrite=True)


def _get_public_link_sync(client: yadisk.YaDisk, remote_path: str) -> str:
    try:
        meta = client.get_meta(remote_path)
        if not getattr(meta, "public_url", None):
            client.publish(remote_path)
            meta = client.get_meta(remote_path)
        return meta.public_url or ""
    except Exception:
        return ""


def _download_file_sync(client: yadisk.YaDisk, remote_path: str, local_path: str):
    client.download(remote_path, local_path)


def _exists_sync(client: yadisk.YaDisk, path: str) -> bool:
    return client.exists(path)


async def ensure_folder(path: str):
    loop = asyncio.get_event_loop()
    client = _get_client()
    await loop.run_in_executor(None, partial(_ensure_folder_sync, client, path))


async def upload_file(local_path: str, remote_path: str):
    loop = asyncio.get_event_loop()
    client = _get_client()
    await loop.run_in_executor(None, partial(_upload_file_sync, client, local_path, remote_path))


async def get_public_link(remote_path: str) -> str:
    loop = asyncio.get_event_loop()
    client = _get_client()
    return await loop.run_in_executor(None, partial(_get_public_link_sync, client, remote_path))


async def download_file(remote_path: str, local_path: str):
    loop = asyncio.get_event_loop()
    client = _get_client()
    await loop.run_in_executor(None, partial(_download_file_sync, client, remote_path, local_path))


async def exists(path: str) -> bool:
    loop = asyncio.get_event_loop()
    client = _get_client()
    return await loop.run_in_executor(None, partial(_exists_sync, client, path))


async def upload_event_file(
    event_name: str,
    username: str,
    date_str: str,
    local_path: str,
    file_name: str,
) -> tuple[str, str]:
    """
    Загружает файл на Яндекс Диск в структуру:
      {root}/{event_name}/{username}/{date}/
    Возвращает (remote_path, public_link).
    """
    from bot.utils.helpers import sanitize_folder_name

    safe_event = sanitize_folder_name(event_name)
    safe_user = sanitize_folder_name(username) if username else "unknown"
    root = settings.yandex_disk_root

    folder_path = f"{root}/{safe_event}/{safe_user}/{date_str}"
    await ensure_folder(folder_path)

    remote_path = f"{folder_path}/{file_name}"
    await upload_file(local_path, remote_path)

    link = await get_public_link(remote_path)
    return remote_path, link
