from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database.queries import (
    create_event,
    get_all_events,
    get_active_events,
    get_event,
    set_event_active,
    delete_event,
    create_invite_link,
    get_invite_links_by_admin,
    set_invite_link_active,
    delete_invite_link,
    get_uploads_by_event,
)
from bot.keyboards.admin_kb import (
    admin_menu,
    superadmin_menu,
    events_list_keyboard,
    event_actions_keyboard,
    invite_links_keyboard,
    link_actions_keyboard,
    choose_event_for_link,
    cancel_keyboard,
)
from bot.states.states import CreateEvent
from bot.utils.helpers import format_user_display, generate_token, has_role, get_menu_for_role

router = Router()


def is_admin_or_superadmin(db_user: dict) -> bool:
    return has_role(db_user, "admin")


# ─── Создать событие (FSM) ────────────────────────────────────────────────────

@router.message(F.text == "➕ Создать событие")
async def create_event_start(message: Message, db_user: dict, state: FSMContext):
    if not is_admin_or_superadmin(db_user):
        return
    await state.set_state(CreateEvent.name)
    await message.answer(
        "📅 <b>Создание нового события</b>\n\nВведите название события:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(CreateEvent.name)
async def create_event_name(message: Message, db_user: dict, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_menu_for_role(db_user))
        return

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Название слишком короткое. Введите не менее 2 символов.")
        return

    await state.update_data(name=name)
    await state.set_state(CreateEvent.description)
    await message.answer(
        f"Название: <b>{name}</b>\n\nТеперь введите описание события (или пропустите):",
        parse_mode="HTML",
    )


@router.message(CreateEvent.description)
async def create_event_description(message: Message, db_user: dict, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_menu_for_role(db_user))
        return

    data = await state.get_data()
    name = data["name"]
    description = message.text.strip() if message.text.strip() != "—" else ""

    event_id = await create_event(name, description, message.from_user.id)
    await state.clear()

    await message.answer(
        f"✅ Событие <b>{name}</b> создано (ID: {event_id})!\n\n"
        "Теперь создайте пригласительную ссылку для участников.",
        parse_mode="HTML",
        reply_markup=get_menu_for_role(db_user),
    )


# ─── Список событий ───────────────────────────────────────────────────────────

@router.message(F.text.in_({"📅 Мои события", "📅 События"}))
async def list_events(message: Message, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    events = await get_all_events()
    if not events:
        await message.answer(
            "Событий пока нет. Нажмите «➕ Создать событие».",
            reply_markup=get_menu_for_role(db_user),
        )
        return
    await message.answer(
        "📅 <b>Все события:</b>",
        parse_mode="HTML",
        reply_markup=events_list_keyboard(events),
    )


@router.callback_query(F.data == "events_list")
async def cb_events_list(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    events = await get_all_events()
    await callback.message.edit_text(
        "📅 <b>Все события:</b>",
        parse_mode="HTML",
        reply_markup=events_list_keyboard(events),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event:"))
async def cb_event_detail(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    event_id = int(callback.data.split(":")[1])
    event = await get_event(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return

    status = "✅ Активно" if event["is_active"] else "❌ Неактивно"
    desc = event["description"] or "—"
    text = (
        f"📅 <b>{event['name']}</b>\n"
        f"Статус: {status}\n"
        f"Описание: {desc}\n"
        f"ID: {event['id']}"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=event_actions_keyboard(event_id, bool(event["is_active"])),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event_deactivate:"))
async def cb_event_deactivate(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    event_id = int(callback.data.split(":")[1])
    await set_event_active(event_id, False)
    event = await get_event(event_id)
    await callback.message.edit_reply_markup(
        reply_markup=event_actions_keyboard(event_id, False)
    )
    await callback.answer("Событие деактивировано.")


@router.callback_query(F.data.startswith("event_activate:"))
async def cb_event_activate(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    event_id = int(callback.data.split(":")[1])
    await set_event_active(event_id, True)
    await callback.message.edit_reply_markup(
        reply_markup=event_actions_keyboard(event_id, True)
    )
    await callback.answer("Событие активировано.")


@router.callback_query(F.data.startswith("event_delete:"))
async def cb_event_delete_ask(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    event_id = int(callback.data.split(":")[1])
    event = await get_event(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, удалить", callback_data=f"event_delete_confirm:{event_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data=f"event:{event_id}")],
    ])
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить событие <b>{event['name']}</b>?\n\n"
        "Будут удалены все связанные ссылки, привязки пользователей и загрузки.",
        parse_mode="HTML",
        reply_markup=confirm_kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event_delete_confirm:"))
async def cb_event_delete_confirm(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    event_id = int(callback.data.split(":")[1])
    event = await get_event(event_id)
    name = event["name"] if event else "?"
    await delete_event(event_id)
    events = await get_all_events()
    if events:
        await callback.message.edit_text(
            f"🗑 Событие <b>{name}</b> удалено.\n\n📅 <b>Все события:</b>",
            parse_mode="HTML",
            reply_markup=events_list_keyboard(events),
        )
    else:
        await callback.message.edit_text(
            f"🗑 Событие <b>{name}</b> удалено.\n\nСобытий больше нет.",
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "create_event")
async def cb_create_event(callback: CallbackQuery, db_user: dict, state: FSMContext):
    if not is_admin_or_superadmin(db_user):
        return
    await state.set_state(CreateEvent.name)
    await callback.message.answer(
        "📅 <b>Создание нового события</b>\n\nВведите название события:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


# ─── Просмотр загрузок события ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("event_uploads:"))
async def cb_event_uploads(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    event_id = int(callback.data.split(":")[1])
    event = await get_event(event_id)
    uploads = await get_uploads_by_event(event_id)

    if not uploads:
        await callback.answer("Загрузок пока нет.", show_alert=True)
        return

    lines = [f"📊 <b>Загрузки события «{event['name']}»:</b>\n"]
    for i, u in enumerate(uploads, 1):
        user_str = format_user_display(u) if u.get("username") or u.get("first_name") else f"ID {u['user_id']}"
        lines.append(
            f"{i}. {user_str}\n"
            f"   📁 {u['file_name']}\n"
            f"   💬 {u['comment'] or '—'}\n"
            f"   🕐 {u['uploaded_at']}"
        )

    text = "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (список обрезан)"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


# ─── Пригласительные ссылки ───────────────────────────────────────────────────

@router.message(F.text == "🔗 Пригласительные ссылки")
async def list_links(message: Message, db_user: dict, bot: Bot):
    if not is_admin_or_superadmin(db_user):
        return
    links = await get_invite_links_by_admin(message.from_user.id)
    if not links:
        await message.answer(
            "У вас нет пригласительных ссылок.\n\n"
            "Создайте ссылку через меню «📅 Мои события» → выберите событие → «🔗 Создать ссылку».",
            reply_markup=get_menu_for_role(db_user),
        )
        return
    await message.answer(
        "🔗 <b>Ваши пригласительные ссылки:</b>",
        parse_mode="HTML",
        reply_markup=invite_links_keyboard(links),
    )


@router.callback_query(F.data == "links_list")
async def cb_links_list(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    links = await get_invite_links_by_admin(callback.from_user.id)
    if not links:
        await callback.message.edit_text("У вас нет пригласительных ссылок.")
        await callback.answer()
        return
    await callback.message.edit_text(
        "🔗 <b>Ваши пригласительные ссылки:</b>",
        parse_mode="HTML",
        reply_markup=invite_links_keyboard(links),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("create_link:"))
async def cb_create_link(callback: CallbackQuery, db_user: dict, bot: Bot):
    if not is_admin_or_superadmin(db_user):
        return
    event_id = int(callback.data.split(":")[1])
    event = await get_event(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return

    token = generate_token()
    await create_invite_link(event_id, token, callback.from_user.id)

    bot_info = await bot.get_me()
    link_url = f"https://t.me/{bot_info.username}?start={token}"

    await callback.message.answer(
        f"✅ Создана пригласительная ссылка для события <b>{event['name']}</b>:\n\n"
        f"<a href='{link_url}'>{link_url}</a>\n\n"
        "Нажмите на ссылку чтобы перейти или скопируйте и отправьте участникам.",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("link:"))
async def cb_link_detail(callback: CallbackQuery, db_user: dict, bot: Bot):
    if not is_admin_or_superadmin(db_user):
        return
    link_id = int(callback.data.split(":")[1])
    links = await get_invite_links_by_admin(callback.from_user.id)
    link = next((l for l in links if l["id"] == link_id), None)
    if not link:
        await callback.answer("Ссылка не найдена.", show_alert=True)
        return

    bot_info = await bot.get_me()
    link_url = f"https://t.me/{bot_info.username}?start={link['token']}"
    status = "✅ Активна" if link["is_active"] else "❌ Неактивна"

    await callback.message.edit_text(
        f"🔗 <b>Ссылка для события «{link['event_name']}»</b>\n"
        f"Статус: {status}\n\n"
        f"<a href='{link_url}'>{link_url}</a>\n\n",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=link_actions_keyboard(link_id, bool(link["is_active"])),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("link_delete:"))
async def cb_link_delete_ask(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    link_id = int(callback.data.split(":")[1])
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, удалить", callback_data=f"link_delete_confirm:{link_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data="links_list")],
    ])
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить эту ссылку?",
        reply_markup=confirm_kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("link_delete_confirm:"))
async def cb_link_delete_confirm(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    link_id = int(callback.data.split(":")[1])
    await delete_invite_link(link_id)
    links = await get_invite_links_by_admin(callback.from_user.id)
    if links:
        await callback.message.edit_text(
            "🗑 Ссылка удалена.\n\n🔗 <b>Ваши пригласительные ссылки:</b>",
            parse_mode="HTML",
            reply_markup=invite_links_keyboard(links),
        )
    else:
        await callback.message.edit_text("🗑 Ссылка удалена. Ссылок больше нет.")
    await callback.answer()


@router.callback_query(F.data.startswith("link_deactivate:"))
async def cb_link_deactivate(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    link_id = int(callback.data.split(":")[1])
    await set_invite_link_active(link_id, False)
    await callback.message.edit_reply_markup(
        reply_markup=link_actions_keyboard(link_id, False)
    )
    await callback.answer("Ссылка деактивирована.")


@router.callback_query(F.data.startswith("link_activate:"))
async def cb_link_activate(callback: CallbackQuery, db_user: dict):
    if not is_admin_or_superadmin(db_user):
        return
    link_id = int(callback.data.split(":")[1])
    await set_invite_link_active(link_id, True)
    await callback.message.edit_reply_markup(
        reply_markup=link_actions_keyboard(link_id, True)
    )
    await callback.answer("Ссылка активирована.")


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено.")
    await callback.answer()
