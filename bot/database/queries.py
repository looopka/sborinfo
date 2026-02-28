from typing import Optional
import aiosqlite
from bot.database.db import get_db


# ─── Users ───────────────────────────────────────────────────────────────────

async def upsert_user(telegram_id: int, username: str, first_name: str, last_name: str) -> dict:
    async with get_db() as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name
        """, (telegram_id, username, first_name, last_name))
        await db.commit()
        row = await db.execute_fetchall(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return dict(row[0]) if row else {}


async def get_user(telegram_id: int) -> Optional[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def set_user_role(telegram_id: int, role: str):
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?", (role, telegram_id)
        )
        await db.commit()


async def get_all_admins() -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM users WHERE role = 'admin' ORDER BY created_at"
        )
        return [dict(r) for r in rows]


async def get_all_admins_and_superadmin() -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM users WHERE role IN ('admin', 'superadmin') ORDER BY created_at"
        )
        return [dict(r) for r in rows]


async def get_user_by_username(username: str) -> Optional[dict]:
    username = username.lstrip("@")
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ─── Events ──────────────────────────────────────────────────────────────────

async def create_event(name: str, description: str, created_by: int) -> int:
    async with get_db() as db:
        async with db.execute(
            "INSERT INTO events (name, description, created_by) VALUES (?, ?, ?)",
            (name, description, created_by),
        ) as cursor:
            event_id = cursor.lastrowid
        await db.commit()
        return event_id


async def get_event(event_id: int) -> Optional[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_events() -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM events ORDER BY created_at DESC"
        )
        return [dict(r) for r in rows]


async def get_active_events() -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM events WHERE is_active = 1 ORDER BY created_at DESC"
        )
        return [dict(r) for r in rows]


async def delete_event(event_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM uploads WHERE event_id = ?", (event_id,))
        await db.execute("DELETE FROM invite_links WHERE event_id = ?", (event_id,))
        await db.execute("DELETE FROM user_events WHERE event_id = ?", (event_id,))
        await db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        await db.commit()


async def set_event_active(event_id: int, is_active: bool):
    async with get_db() as db:
        await db.execute(
            "UPDATE events SET is_active = ? WHERE id = ?", (int(is_active), event_id)
        )
        await db.commit()


# ─── Invite Links ─────────────────────────────────────────────────────────────

async def create_invite_link(event_id: int, token: str, created_by: int) -> int:
    async with get_db() as db:
        async with db.execute(
            "INSERT INTO invite_links (event_id, token, created_by) VALUES (?, ?, ?)",
            (event_id, token, created_by),
        ) as cursor:
            link_id = cursor.lastrowid
        await db.commit()
        return link_id


async def get_invite_link_by_token(token: str) -> Optional[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT il.*, e.name as event_name FROM invite_links il "
            "JOIN events e ON il.event_id = e.id "
            "WHERE il.token = ?",
            (token,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_invite_links_by_admin(admin_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT il.*, e.name as event_name FROM invite_links il "
            "JOIN events e ON il.event_id = e.id "
            "WHERE il.created_by = ? ORDER BY il.created_at DESC",
            (admin_id,),
        )
        return [dict(r) for r in rows]


async def delete_invite_link(link_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM invite_links WHERE id = ?", (link_id,))
        await db.commit()


async def set_invite_link_active(link_id: int, is_active: bool):
    async with get_db() as db:
        await db.execute(
            "UPDATE invite_links SET is_active = ? WHERE id = ?",
            (int(is_active), link_id),
        )
        await db.commit()


# ─── User Events ──────────────────────────────────────────────────────────────

async def add_user_to_event(user_id: int, event_id: int):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_events (user_id, event_id) VALUES (?, ?)",
            (user_id, event_id),
        )
        await db.commit()


async def get_user_events(user_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT e.* FROM events e "
            "JOIN user_events ue ON e.id = ue.event_id "
            "WHERE ue.user_id = ? ORDER BY ue.joined_at DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]


async def get_user_active_events(user_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT e.* FROM events e "
            "JOIN user_events ue ON e.id = ue.event_id "
            "WHERE ue.user_id = ? AND e.is_active = 1 ORDER BY ue.joined_at DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]


# ─── Uploads ─────────────────────────────────────────────────────────────────

async def create_upload(
    event_id: int,
    user_id: int,
    file_name: str,
    file_type: str,
    yandex_path: str,
    yandex_link: str,
    comment: str,
) -> int:
    async with get_db() as db:
        async with db.execute(
            """INSERT INTO uploads
               (event_id, user_id, file_name, file_type, yandex_path, yandex_link, comment)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, user_id, file_name, file_type, yandex_path, yandex_link, comment),
        ) as cursor:
            upload_id = cursor.lastrowid
        await db.commit()
        return upload_id


async def get_uploads_by_event(event_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT u.*, us.username, us.first_name, us.last_name
               FROM uploads u
               JOIN users us ON u.user_id = us.telegram_id
               WHERE u.event_id = ?
               ORDER BY u.uploaded_at""",
            (event_id,),
        )
        return [dict(r) for r in rows]
