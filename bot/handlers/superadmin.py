from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import settings
from bot.database.queries import (
    get_all_admins,
    get_user,
    get_user_by_username,
    set_user_role,
)
from bot.keyboards.admin_kb import (
    superadmin_menu,
    manage_admins_menu,
    admins_list_keyboard,
    cancel_keyboard,
)
from bot.states.states import ManageAdmin, RemoveAdmin
from bot.utils.helpers import format_user_display, has_role

router = Router()


def is_superadmin(db_user: dict) -> bool:
    return has_role(db_user, "superadmin")


# ─── Вход в управление администраторами ──────────────────────────────────────

@router.message(F.text == "👥 Управление администраторами")
async def manage_admins(message: Message, db_user: dict):
    if not is_superadmin(db_user):
        return
    await message.answer(
        "👥 <b>Управление администраторами</b>",
        parse_mode="HTML",
        reply_markup=manage_admins_menu(),
    )


# ─── Список администраторов ───────────────────────────────────────────────────

@router.message(F.text == "📋 Список администраторов")
async def list_admins(message: Message, db_user: dict):
    if not is_superadmin(db_user):
        return
    admins = await get_all_admins()
    if not admins:
        await message.answer("Администраторов пока нет.", reply_markup=manage_admins_menu())
        return

    lines = []
    for i, admin in enumerate(admins, 1):
        lines.append(f"{i}. {format_user_display(admin)}")
    text = "📋 <b>Список администраторов:</b>\n\n" + "\n".join(lines)
    await message.answer(text, parse_mode="HTML", reply_markup=manage_admins_menu())


# ─── Добавить администратора ──────────────────────────────────────────────────

@router.message(F.text == "➕ Добавить администратора")
async def add_admin_start(message: Message, db_user: dict, state: FSMContext):
    if not is_superadmin(db_user):
        return
    await state.set_state(ManageAdmin.waiting_user_id)
    await message.answer(
        "Введите <b>Telegram ID</b> или <b>@username</b> пользователя, "
        "которого хотите назначить администратором:\n\n"
        "Пример: <code>123456789</code> или <code>@username</code>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(ManageAdmin.waiting_user_id)
async def add_admin_process(message: Message, db_user: dict, state: FSMContext):
    if not is_superadmin(db_user):
        await state.clear()
        return

    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=manage_admins_menu())
        return

    text = message.text.strip()
    target_user = None

    if text.startswith("@"):
        target_user = await get_user_by_username(text)
    elif text.isdigit():
        target_user = await get_user(int(text))

    if not target_user:
        await message.answer(
            "❌ Пользователь не найден. Убедитесь, что он уже запускал бота.\n"
            "Введите другой ID/username или нажмите «Отмена»."
        )
        return

    if target_user["telegram_id"] == settings.superadmin_id:
        await message.answer("❌ Нельзя изменить роль суперадмина.")
        return

    if target_user["role"] == "admin":
        await message.answer(
            f"ℹ️ {format_user_display(target_user)} уже является администратором.",
            reply_markup=manage_admins_menu(),
        )
        await state.clear()
        return

    await set_user_role(target_user["telegram_id"], "admin")
    await state.clear()
    await message.answer(
        f"✅ <b>{format_user_display(target_user)}</b> назначен администратором.",
        parse_mode="HTML",
        reply_markup=manage_admins_menu(),
    )


# ─── Убрать администратора ────────────────────────────────────────────────────

@router.message(F.text == "➖ Убрать администратора")
async def remove_admin_start(message: Message, db_user: dict, state: FSMContext):
    if not is_superadmin(db_user):
        return
    admins = await get_all_admins()
    if not admins:
        await message.answer("Нет администраторов для удаления.", reply_markup=manage_admins_menu())
        return
    await state.set_state(RemoveAdmin.choose_admin)
    await message.answer(
        "Выберите администратора для удаления:",
        reply_markup=admins_list_keyboard(admins),
    )


@router.callback_query(RemoveAdmin.choose_admin, F.data.startswith("remove_admin:"))
async def remove_admin_confirm(callback: CallbackQuery, db_user: dict, state: FSMContext):
    if not is_superadmin(db_user):
        await state.clear()
        return
    admin_id = int(callback.data.split(":")[1])
    target_user = await get_user(admin_id)
    if not target_user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        await state.clear()
        return

    await set_user_role(admin_id, "user")
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>{format_user_display(target_user)}</b> больше не администратор.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(RemoveAdmin.choose_admin, F.data == "cancel")
async def remove_admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено.")
    await callback.answer()


# ─── Назад ────────────────────────────────────────────────────────────────────

@router.message(F.text == "🔙 Назад")
async def go_back(message: Message, db_user: dict):
    if not is_superadmin(db_user):
        return
    await message.answer("Главное меню", reply_markup=superadmin_menu())
