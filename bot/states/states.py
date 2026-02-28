from aiogram.fsm.state import State, StatesGroup


class CreateEvent(StatesGroup):
    name = State()
    description = State()


class CreateInviteLink(StatesGroup):
    choose_event = State()


class ManageAdmin(StatesGroup):
    waiting_user_id = State()


class RemoveAdmin(StatesGroup):
    choose_admin = State()


class UploadFile(StatesGroup):
    choose_event = State()
    waiting_comment = State()
