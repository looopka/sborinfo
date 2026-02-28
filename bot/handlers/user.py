import os
import logging
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import settings
from bot.database.queries import (
    get_user_active_events,
    get_event,
    create_upload,
    get_all_admins_and_superadmin,
)
from bot.keyboards.user_kb import user_menu, choose_event_keyboard, upload_actions_keyboard
from bot.services import yandex_disk, excel_report
from bot.states.states import UploadFile
from bot.utils.helpers import format_user_display, get_menu_for_role

logger = logging.getLogger(__name__)
router = Router()

SUPPORTED_FILE_TYPES = {"photo", "video", "document", "audio", "voice", "video_note"}


def get_file_info(message: Message) -> tuple[str, str, str]:
    """Возвращает (file_id, file_name, file_type)."""
    if message.photo:
        photo = message.photo[-1]
        return photo.file_id, f"photo_{photo.file_id[-8:]}.jpg", "photo"
    elif message.video:
        name = message.video.file_name or f"video_{message.video.file_id[-8:]}.mp4"
        return message.video.file_id, name, "video"
    elif message.document:
        return message.document.file_id, message.document.file_name or "document", "document"
    elif message.audio:
        name = message.audio.file_name or f"audio_{message.audio.file_id[-8:]}.mp3"
        return message.audio.file_id, name, "audio"
    elif message.voice:
        return message.voice.file_id, f"voice_{message.voice.file_id[-8:]}.ogg", "voice"
    elif message.video_note:
        return message.video_note.file_id, f"video_note_{message.video_note.file_id[-8:]}.mp4", "video_note"
    return "", "", ""


def _make_unique_name(counter: int, file_name: str) -> str:
    """Добавляет порядковый номер к имени файла для уникальности."""
    return f"{counter:03d}_{file_name}"


def _extract_files(messages: list[Message], start_counter: int = 0) -> tuple[list[dict], int]:
    """Извлекает файлы из списка сообщений, возвращает (files, new_counter)."""
    files = []
    counter = start_counter
    for msg in messages:
        file_id, file_name, file_type = get_file_info(msg)
        if not file_id:
            continue
        counter += 1
        unique_name = _make_unique_name(counter, file_name)
        files.append({"file_id": file_id, "file_name": unique_name, "file_type": file_type})
    return files, counter


# ─── Список событий пользователя ─────────────────────────────────────────────

@router.message(F.text == "📋 Мои события")
async def my_events(message: Message, db_user: dict):
    events = await get_user_active_events(message.from_user.id)
    if not events:
        await message.answer(
            "У вас нет активных событий.\n"
            "Попросите администратора прислать пригласительную ссылку."
        )
        return
    lines = [f"📋 <b>Ваши события:</b>\n"]
    for e in events:
        lines.append(f"• {e['name']}")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ─── Загрузка файла (шаг 1: выбор события или сразу) ─────────────────────────

@router.message(F.text == "📤 Загрузить файл")
async def upload_file_start(message: Message, db_user: dict, state: FSMContext):
    events = await get_user_active_events(message.from_user.id)
    if not events:
        await message.answer(
            "У вас нет активных событий для загрузки файлов.\n"
            "Получите пригласительную ссылку от администратора."
        )
        return

    if len(events) == 1:
        await state.update_data(
            event_id=events[0]["id"], event_name=events[0]["name"],
            files=[], file_counter=0,
        )
        await state.set_state(UploadFile.waiting_comment)
        await message.answer(
            f"📤 Загрузка в событие <b>{events[0]['name']}</b>\n\n"
            "Отправьте файлы (фото, видео, документы). "
            "Можно несколько за раз.\n"
            "Когда закончите — напишите комментарий или нажмите\n"
            "«⏭ Пропустить комментарий».",
            parse_mode="HTML",
            reply_markup=upload_actions_keyboard(),
        )
    else:
        await state.set_state(UploadFile.choose_event)
        await message.answer(
            "Выберите событие для загрузки:",
            reply_markup=choose_event_keyboard(events),
        )


@router.callback_query(UploadFile.choose_event, F.data.startswith("upload_event:"))
async def upload_choose_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    event = await get_event(event_id)
    if not event or not event["is_active"]:
        await callback.answer("Событие недоступно.", show_alert=True)
        return

    await state.update_data(
        event_id=event_id, event_name=event["name"],
        files=[], file_counter=0,
    )
    await state.set_state(UploadFile.waiting_comment)
    await callback.message.edit_text(
        f"📤 Загрузка в событие <b>{event['name']}</b>\n\n"
        "Отправьте файлы (фото, видео, документы). "
        "Можно несколько за раз.\n"
        "Когда закончите — напишите комментарий или нажмите\n"
        "«⏭ Пропустить комментарий».",
        parse_mode="HTML",
    )
    # Показываем reply-клавиатуру отдельным сообщением (inline нельзя совмещать)
    await callback.message.answer("⬇️", reply_markup=upload_actions_keyboard())
    await callback.answer()


# ─── Обработка входящего файла ───────────────────────────────────────────────

@router.message(F.photo | F.video | F.document | F.audio | F.voice | F.video_note)
async def handle_incoming_file(
    message: Message, db_user: dict, state: FSMContext, bot: Bot,
    album: list[Message] | None = None,
):
    messages = album or [message]
    current_state = await state.get_state()

    # Если уже в процессе загрузки — тихо добавляем файлы
    if current_state == UploadFile.waiting_comment.state:
        await _add_files_to_queue(messages, state)
        return

    # Иначе — нужно выбрать событие
    events = await get_user_active_events(message.from_user.id)
    if not events:
        await message.answer(
            "У вас нет активных событий. Получите пригласительную ссылку от администратора."
        )
        return

    new_files, counter = _extract_files(messages)

    if len(events) == 1:
        await state.update_data(
            event_id=events[0]["id"], event_name=events[0]["name"],
            files=new_files, file_counter=counter,
        )
        await state.set_state(UploadFile.waiting_comment)
        await message.answer(
            f"📎 Принято файлов: {len(new_files)}. Событие: <b>{events[0]['name']}</b>\n"
            "Можете отправить ещё файлы.\n"
            "Когда закончите — напишите комментарий или нажмите\n"
            "«⏭ Пропустить комментарий».",
            parse_mode="HTML",
            reply_markup=upload_actions_keyboard(),
        )
    else:
        await state.update_data(files=new_files, file_counter=counter)
        await state.set_state(UploadFile.choose_event)
        await message.answer(
            "Выберите событие для загрузки:",
            reply_markup=choose_event_keyboard(events),
        )


async def _add_files_to_queue(messages: list[Message], state: FSMContext):
    """Тихо добавляет файлы в очередь (без отправки сообщений)."""
    data = await state.get_data()
    file_counter = data.get("file_counter", 0)
    files = data.get("files", [])

    new_files, file_counter = _extract_files(messages, file_counter)
    files.extend(new_files)

    await state.update_data(files=files, file_counter=file_counter)


# ─── Обработка комментария / пропуска ────────────────────────────────────────

@router.message(UploadFile.waiting_comment, F.text)
async def handle_comment(message: Message, db_user: dict, state: FSMContext, bot: Bot):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_menu_for_role(db_user))
        return

    if message.text == "⏭ Пропустить комментарий":
        await _do_upload(message, db_user, state, bot, comment="")
        return

    comment = message.text.strip()
    await _do_upload(message, db_user, state, bot, comment=comment)


@router.callback_query(UploadFile.waiting_comment, F.data == "skip_comment")
async def handle_skip_comment(callback: CallbackQuery, db_user: dict, state: FSMContext, bot: Bot):
    """Обратная совместимость с инлайн-кнопкой (если осталась в чате)."""
    await _do_upload(callback.message, db_user, state, bot, comment="", original_user=callback.from_user)
    await callback.answer()


# ─── Основная логика загрузки файлов ─────────────────────────────────────────

async def _do_upload(
    message: Message,
    db_user: dict,
    state: FSMContext,
    bot: Bot,
    comment: str,
    original_user=None,
):
    data = await state.get_data()
    files = data.get("files", [])
    event_id = data.get("event_id")
    event_name = data.get("event_name")

    if not files or not event_id:
        await message.answer(
            "❌ Нет файлов для загрузки. Сначала отправьте файлы.",
            reply_markup=get_menu_for_role(db_user),
        )
        await state.clear()
        return

    await state.clear()

    user_id = original_user.id if original_user else message.from_user.id
    username = db_user.get("username") or str(user_id)
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    total = len(files)
    processing_msg = await message.answer(
        f"⏳ Загружаю {total} файл(ов) на Яндекс Диск...",
        reply_markup=get_menu_for_role(db_user),
    )

    uploaded = []
    errors = 0

    for i, f in enumerate(files):
        try:
            tg_file = await bot.get_file(f["file_id"])
            local_path = os.path.join(settings.temp_dir, f["file_name"])
            os.makedirs(settings.temp_dir, exist_ok=True)
            await bot.download_file(tg_file.file_path, local_path)

            remote_path, link = await yandex_disk.upload_event_file(
                event_name=event_name,
                username=username,
                date_str=date_str,
                local_path=local_path,
                file_name=f["file_name"],
            )

            if os.path.exists(local_path):
                os.remove(local_path)

            await create_upload(
                event_id=event_id,
                user_id=user_id,
                file_name=f["file_name"],
                file_type=f["file_type"],
                yandex_path=remote_path,
                yandex_link=link,
                comment=comment,
            )

            upload_data = {
                **db_user,
                "telegram_id": user_id,
                "file_name": f["file_name"],
                "yandex_link": link,
                "comment": comment,
                "uploaded_at": time_str,
            }
            await excel_report.update_event_report(
                event_name=event_name,
                upload_data=upload_data,
                temp_dir=settings.temp_dir,
            )

            uploaded.append({"file_name": f["file_name"], "link": link})

        except Exception as e:
            logger.error(f"Ошибка при загрузке файла {f['file_name']}: {e}", exc_info=True)
            errors += 1

    await processing_msg.delete()

    # Формируем итоговое сообщение
    if uploaded:
        if len(uploaded) == 1:
            u = uploaded[0]
            text = (
                f"✅ Файл <b>{u['file_name']}</b> успешно загружен!\n"
                f"📅 Событие: {event_name}"
            )
            if u["link"]:
                text += f"\n🔗 <a href='{u['link']}'>Открыть на Яндекс Диске</a>"
        else:
            text = (
                f"✅ Загружено файлов: <b>{len(uploaded)}</b> из {total}\n"
                f"📅 Событие: {event_name}"
            )
        if errors:
            text += f"\n⚠️ Не удалось загрузить: {errors}"
        await message.answer(text, parse_mode="HTML", reply_markup=get_menu_for_role(db_user))
    else:
        await message.answer(
            "❌ Не удалось загрузить файлы. Попробуйте снова.",
            reply_markup=get_menu_for_role(db_user),
        )

    # Уведомляем администраторов (одно уведомление на всю пачку)
    if uploaded:
        admins = await get_all_admins_and_superadmin()
        user_display = format_user_display(db_user)
        file_list = "\n".join(f"  • {u['file_name']}" for u in uploaded)
        notif_text = (
            f"📥 <b>Новые файлы загружены!</b>\n\n"
            f"👤 Пользователь: {user_display}\n"
            f"📅 Событие: <b>{event_name}</b>\n"
            f"📁 Файлы ({len(uploaded)}):\n{file_list}\n"
            f"💬 Комментарий: {comment or '—'}\n"
            f"🕐 Время: {time_str}"
        )
        for admin in admins:
            try:
                await bot.send_message(admin["telegram_id"], notif_text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Не удалось уведомить администратора {admin['telegram_id']}: {e}")
