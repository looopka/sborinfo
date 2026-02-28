import re
import uuid

# ─── Иерархия ролей ──────────────────────────────────────────────────────────
# superadmin > admin > user

ROLE_LEVELS = {"user": 0, "admin": 1, "superadmin": 2}


def has_role(db_user: dict, min_role: str) -> bool:
    """Проверяет, что у пользователя роль >= min_role."""
    user_level = ROLE_LEVELS.get(db_user.get("role", ""), -1)
    required_level = ROLE_LEVELS.get(min_role, 999)
    return user_level >= required_level


def get_menu_for_role(db_user: dict):
    """Возвращает клавиатуру главного меню в зависимости от роли."""
    from bot.keyboards.admin_kb import superadmin_menu, admin_menu
    from bot.keyboards.user_kb import user_menu

    role = db_user.get("role", "user")
    if role == "superadmin":
        return superadmin_menu()
    elif role == "admin":
        return admin_menu()
    return user_menu()


def generate_token() -> str:
    return str(uuid.uuid4()).replace("-", "")[:16]


def sanitize_folder_name(name: str) -> str:
    """Очищает строку для использования как имя папки на Яндекс Диске."""
    name = name.strip()
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name[:50]


def format_user_display(user: dict) -> str:
    """Форматирует отображение пользователя."""
    parts = []
    if user.get("first_name"):
        parts.append(user["first_name"])
    if user.get("last_name"):
        parts.append(user["last_name"])
    full_name = " ".join(parts) if parts else "Без имени"

    if user.get("username"):
        return f"{full_name} (@{user['username']})"
    uid = user.get("telegram_id") or user.get("user_id") or "?"
    return f"{full_name} (ID: {uid})"
