from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import ADMINS
from database import cur, save

OPTIONS = {
    "🌅 Imagem inicial": "main_img",
    "👤 Dono | Suporte": "support_user",
    "📢 Canal de ref": "channel_user",
}


@Client.on_callback_query(filters.regex(r"^bot_config$") & filters.user(ADMINS))
async def option_edit(c: Client, m: CallbackQuery):
    global OPTIONS

    bts = []
    for k, v in OPTIONS.items():
        bts.append(InlineKeyboardButton(text=k, callback_data=f"edit {v}"))
    orgn = (lambda data, step: [data[x : x + step] for x in range(0, len(data), step)])(
        bts, 2
    )
    orgn.append([InlineKeyboardButton(text="« Voltar", callback_data="painel")])
    kb = InlineKeyboardMarkup(inline_keyboard=orgn)
    await m.edit_message_text(
        "<b>🛠 Outras configs\n</b>"
        "<i>- Esta opção contém outras configurações da store.</i>\n\n"
        "<b>Selecione abaixo o que você deseja alterar:</b>",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^edit (?P<item>\w+)"))
async def edit_config(c: Client, m: CallbackQuery):
    global OPTIONS
    msg_type = {
        "main_img": "<b>link da imagem inicial </b><i>EX: new_link</i>",
        "support_user": "<b>Novo Usuário para suporte no bot </b><i>EX: @username</i>",
        "channel_user": "<b>Novo canal de referencia </b><i>EX: @user_channel</i>",
    }

    item = m.matches[0]["item"]

    if item not in list(msg_type):
        return
    await m.message.delete()
    new_arg = await m.message.ask(
        f"<b>para editar o </b> {msg_type[item]} <b>favor mandar apenas o solicitado igualmente o EXEMPLO</b>",
        reply_markup=ForceReply(),
    )
    if new_arg == "/cancel":
        ...
    else:
        cur.execute(f"UPDATE bot_config SET {item}=?", [new_arg["text"]])
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton("« Voltar", callback_data="painel"),
                ],
            ]
        )
        await m.message.reply_text(
            "<b>✅ Item alterado com sucesso</b>", reply_markup=kb
        )
        save()
