"""
Este plugin executa antes dos outros e em caso do bot estar em manutenção,
exibe uma mensagem de aviso e cancelando o processamento da mensagem pelo bot.
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
from utils import get_news_user, is_bot_online


@Client.on_message(
    ~filters.user(ADMINS) & filters.regex(r"^/") & filters.private, group=-1
)
async def bot_status_msg(c: Client, m: Message):
    if not is_bot_online():
        news_user = get_news_user()
        await m.reply_text(
            f"⚠ O bot está em manutenção, tente novamente mais tarde. Para ficar sabendo as novidades do bot, siga {news_user}."
        )
        await m.stop_propagation()


@Client.on_callback_query(~filters.user(ADMINS), group=-1)
async def bot_status_cq(c: Client, m: CallbackQuery):
    if not is_bot_online():
        news_user = get_news_user()
        await m.answer(
            f"⚠ O bot está em manutenção, tente novamente mais tarde. Para ficar sabendo as novidades do bot, siga {news_user}.",
            show_alert=True,
            cache_time=5,
        )
        await m.stop_propagation()


@Client.on_inline_query(~filters.user(ADMINS), group=-1)
async def bot_status_inline(c: Client, m: InlineQuery):
    if not is_bot_online():
        news_user = get_news_user()
        results = [
            InlineQueryResultArticle(
                title="⚠ O bot está em manutenção.",
                description="Tente novamente mais tarde.",
                input_message_content=InputTextMessageContent(
                    f"⚠ O bot está em manutenção, tente novamente mais tarde. Para ficar sabendo as novidades do bot, siga {news_user}."
                ),
            )
        ]

        await m.answer(results, cache_time=5)
        await m.stop_propagation()
