import asyncio
from typing import Any, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message


class AlbumMiddleware(BaseMiddleware):
    """Собирает сообщения из одного альбома (media_group) в список."""

    def __init__(self, latency: float = 0.5):
        self.latency = latency
        self.album_data: dict[str, list[Message]] = {}

    async def __call__(
        self,
        handler: Callable,
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.media_group_id:
            return await handler(event, data)

        media_group_id = event.media_group_id

        try:
            self.album_data[media_group_id].append(event)
            return  # Не первое сообщение в альбоме — пропускаем
        except KeyError:
            self.album_data[media_group_id] = [event]
            await asyncio.sleep(self.latency)

        data["album"] = self.album_data.pop(media_group_id, [event])
        return await handler(event, data)
