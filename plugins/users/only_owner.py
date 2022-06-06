from pyrogram import Client
from pyrogram.types import CallbackQuery

from config import ADMINS


@Client.on_callback_query(group=-2)
async def bot_status_cq(c: Client, m: CallbackQuery):
    if m.inline_message_id and m.message and (m.from_user.id != m.message.from_user.id):
        await m.answer(
            "❗️ Esta mensagem não é para você.", cache_time=30, show_alert=True
        )

        await m.stop_propagation()
