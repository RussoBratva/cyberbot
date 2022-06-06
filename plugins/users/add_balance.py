import math
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_CHAT
from database import cur, save
from utils import create_mention, get_lara_info, get_support_user, insert_sold_balance


@Client.on_callback_query(filters.regex(r"^add_balance$"))
async def add_balance(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    "💠 Pix automático", callback_data="add_balance_auto"
                ),
                InlineKeyboardButton(
                    "💰 Pix manual", callback_data="add_balance_manual"
                ),
            ],
            [
                InlineKeyboardButton("« Voltar", callback_data="start"),
            ],
        ]
    )

    await m.edit_message_text(
        """<b>💰 Adicionar saldo</b>
<i>- Escolha abaixo como você deseja adicionar o saldo.</i>""",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^add_balance_manual$"))
async def add_balance_manual(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("« Voltar", callback_data="add_balance"),
            ],
        ]
    )

    pix_name, pix_key = get_lara_info()

    support_user = get_support_user()
    valor_min = 20
    details = (
        f"\n\n<i>⚠ Se você enviar um valor <b>MENOR</b> que <b>R$ {valor_min}</b>, você perderá o depósito.</i>"
        if valor_min
        else ""
    )
    await m.edit_message_text(
        f"""<b>💰 Pix manual</b>
<i>Para adicionar saldo a sua conta, envie um Pix para a seguinte chave:</i>

<b>Nome:</b> <code>{pix_name}</code>
<b>Chave Pix:</b> <code>{pix_key}</code>

<b>Após o pagamento, envie o comprovante para {support_user}.</b>
{details}""",
        reply_markup=kb,
    )


@Client.on_message(filters.regex(r"/resgatar (?P<gift>\w+)$"))
@Client.on_callback_query(filters.regex(r"^redeem (?P<gift>\w+)$"))
async def redeem_gift(c: Client, m: Union[CallbackQuery, Message]):
    user_id = m.from_user.id
    gift = m.matches[0]["gift"]

    if isinstance(m, Message):
        send = m.reply_text
    else:
        send = m.edit_message_text

    try:
        value = cur.execute(
            "SELECT value from gifts WHERE token = ?", [gift]
        ).fetchone()[0]
    except:
        return await send("Este gift card já foi resgatado ou não existe.")

    cur.execute("DELETE FROM gifts WHERE token = ?", [gift])

    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?", [value, user_id]
    ).fetchone()

    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    mention = create_mention(m.from_user)
    insert_sold_balance(value, user_id, "manual")
    base = f"""💰 {mention} resgatou um gift card de <b>R${value}</b>
- Novo saldo: <b>R${new_balance}</b>
- Gift card: <code>{gift}</code>"""

    who = m.from_user.first_name if isinstance(m, CallbackQuery) else "Você"

    await c.send_message(ADMIN_CHAT, base)
    await send(f"<b>✅ {who} resgatou R$ {value} com gift card.</b>")

    refer = cur.execute("SELECT refer FROM users WHERE id = ?", [user_id]).fetchone()[0]

    if refer:
        quantity = math.floor((value / 100) * 5)  # 5% normalizado para int.
        if quantity > 0:
            mention = create_mention(m.from_user, with_id=False)

            cur.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                [quantity, refer],
            ).fetchone()

            await c.send_message(
                int(refer),
                f"💰 Seu referenciado {mention} adicionou saldo no bot e você recebeu {quantity} de saldo.",
            )
    save()
