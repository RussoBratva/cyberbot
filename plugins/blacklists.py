"""
Este plugin executa de um jeito similar ao `bot_status.py`, antes dos outros,
cancelando o processamento da mensagem pelo bot de usuários blacklistados.
"""


from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)

from config import ADMINS
from utils import get_support_user, is_user_banned


@Client.on_message(
    ~filters.user(ADMINS) & filters.regex(r"^/") & ~filters.channel, group=-2
)
async def is_blacklisted_msg(c: Client, m: Message):
    if is_user_banned(m.from_user.id):
        support_user = get_support_user()
        await m.reply_text(
            f"❌ Você foi banido de utilizar o bot. Caso ache que isso é um engano, contate {support_user}."
        )
        await m.stop_propagation()


@Client.on_callback_query(~filters.user(ADMINS), group=-2)
async def is_blacklisted_cq(c: Client, m: CallbackQuery):
    if is_user_banned(m.from_user.id):
        support_user = get_support_user()
        await m.answer(
            f"❌ Você foi banido de utilizar o bot. Caso ache que isso é um engano, contate {support_user}.",
            show_alert=True,
            cache_time=30,
        )
        await m.stop_propagation()


@Client.on_inline_query(~filters.user(ADMINS), group=-2)
async def is_blacklisted_inline(c: Client, m: InlineQuery):
    if is_user_banned(m.from_user.id):
        support_user = get_support_user()

        results = [
            InlineQueryResultArticle(
                title="❌ Você foi banido de utilizar o bot.",
                input_message_content=InputTextMessageContent(
                    f"❌ Você foi banido de utilizar o bot. Caso ache que isso é um engano, contate {support_user}."
                ),
            )
        ]

        await m.answer(results, cache_time=30, is_personal=True)
        await m.stop_propagation()
