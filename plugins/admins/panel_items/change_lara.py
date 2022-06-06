from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import ADMINS
from database import cur, db
from utils import get_lara_info


def update_lara_info(name: str, pix_key: str):
    cur.execute(
        "UPDATE bot_config SET lara_name = ?, lara_key = ? WHERE ROWID = 0",
        (name, pix_key),
    )
    db.commit()


@Client.on_callback_query(filters.regex(r"^change_lara$") & filters.user(ADMINS))
async def change_lara(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    "🏦 Alterar dados", callback_data="change_lara_details"
                ),
            ],
            [InlineKeyboardButton("« Voltar", callback_data="painel")],
        ]
    )

    lara_name, lara_key = get_lara_info()

    await m.edit_message_text(
        "<b>🏦 Alterar lara</b>\n"
        '<i>- Esta opção permite alterar a lara atual do bot clicando no botão "Alterar dados" abaixo.</i>\n\n'
        "<b>Dados atuais:</b>\n"
        f"<b>Nome:</b> <code>{lara_name}</code>\n"
        f"<b>Chave Pix:</b> <code>{lara_key}</code>",
        reply_markup=kb,
    )


@Client.on_callback_query(
    filters.regex(r"^change_lara_details$") & filters.user(ADMINS)
)
async def change_lara_details(c: Client, m: CallbackQuery):
    await m.message.delete()

    name = await m.message.ask("Informe o nome da lara:", reply_markup=ForceReply())
    pix_key = await m.message.ask(
        "Informe a chave Pix da lara:", reply_markup=ForceReply()
    )

    update_lara_info(name.text, pix_key.text)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("✅ Ok", callback_data="painel")],
        ]
    )

    await m.message.reply_text(
        "✅ Dados da lara alterados com sucesso.", reply_markup=kb
    )
