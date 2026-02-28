from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def superadmin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👥 Управление администраторами"))
    builder.row(KeyboardButton(text="📅 Мои события"), KeyboardButton(text="➕ Создать событие"))
    builder.row(KeyboardButton(text="🔗 Пригласительные ссылки"))
    builder.row(KeyboardButton(text="📤 Загрузить файл"))
    return builder.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📅 Мои события"))
    builder.row(KeyboardButton(text="➕ Создать событие"))
    builder.row(KeyboardButton(text="🔗 Пригласительные ссылки"))
    builder.row(KeyboardButton(text="📤 Загрузить файл"))
    return builder.as_markup(resize_keyboard=True)


def manage_admins_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="➕ Добавить администратора"))
    builder.row(KeyboardButton(text="➖ Убрать администратора"))
    builder.row(KeyboardButton(text="📋 Список администраторов"))
    builder.row(KeyboardButton(text="🔙 Назад"))
    return builder.as_markup(resize_keyboard=True)


def events_list_keyboard(events: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for event in events:
        status = "✅" if event["is_active"] else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {event['name']}",
                callback_data=f"event:{event['id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="➕ Создать событие", callback_data="create_event"))
    return builder.as_markup()


def event_actions_keyboard(event_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="❌ Деактивировать", callback_data=f"event_deactivate:{event_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Активировать", callback_data=f"event_activate:{event_id}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🔗 Создать ссылку", callback_data=f"create_link:{event_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Загрузки", callback_data=f"event_uploads:{event_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить событие", callback_data=f"event_delete:{event_id}"
        )
    )
    builder.row(InlineKeyboardButton(text="🔙 К списку событий", callback_data="events_list"))
    return builder.as_markup()


def invite_links_keyboard(links: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for link in links:
        status = "✅" if link["is_active"] else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {link['event_name']}",
                callback_data=f"link:{link['id']}",
            )
        )
    return builder.as_markup()


def link_actions_keyboard(link_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="❌ Деактивировать", callback_data=f"link_deactivate:{link_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Активировать", callback_data=f"link_activate:{link_id}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить ссылку", callback_data=f"link_delete:{link_id}"
        )
    )
    builder.row(InlineKeyboardButton(text="🔙 К списку ссылок", callback_data="links_list"))
    return builder.as_markup()


def choose_event_for_link(events: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for event in events:
        builder.row(
            InlineKeyboardButton(
                text=event["name"], callback_data=f"create_link:{event['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def admins_list_keyboard(admins: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for admin in admins:
        name = admin.get("username") or admin.get("first_name") or str(admin["telegram_id"])
        builder.row(
            InlineKeyboardButton(
                text=f"@{name}" if admin.get("username") else name,
                callback_data=f"remove_admin:{admin['telegram_id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)
