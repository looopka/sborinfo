from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def user_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📤 Загрузить файл"))
    builder.row(KeyboardButton(text="📋 Мои события"))
    return builder.as_markup(resize_keyboard=True)


def choose_event_keyboard(events: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for event in events:
        builder.row(
            InlineKeyboardButton(
                text=event["name"], callback_data=f"upload_event:{event['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def skip_comment_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_comment")
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def upload_actions_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура во время сбора файлов."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⏭ Пропустить комментарий"))
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)
