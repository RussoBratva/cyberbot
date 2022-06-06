from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from database import cur, save
from utils import get_info_wallet


@Client.on_callback_query(filters.regex(r"^my_account$"))
async def my_account(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    "💳 Histórico de compras", callback_data="buy_history"
                ),
            ],
            [
                InlineKeyboardButton("💎 Trocar Pontos", callback_data="swap"),
            ],
            [
                InlineKeyboardButton("💠 Alterar dados Pix", callback_data="swap_info"),
            ],
            [
                InlineKeyboardButton("« Voltar", callback_data="start"),
            ],
        ]
    )
    link = f"https://t.me/{c.me.username}?start={m.from_user.id}"
    await m.edit_message_text(
        f"""<b>👤 Minha conta</b>
<i>- Aqui você pode visualizar detalhes da sua conta ou realizar alterações.</i>

{get_info_wallet(m.from_user.id)}


<b>🔗 Link de referência</b>
<i>- Convidando novos usuários pelo link abaixo, você recebe um bônus a cada vez que seus referenciados adicionarem saldo no bot.</i>

<b>Seu link de referência</b>: <code>{link}</code>""",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^buy_history$"))
async def buy_history(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("« Voltar", callback_data="my_account"),
            ],
        ]
    )
    history = cur.execute(
        "SELECT number, month, year, cvv FROM cards_sold WHERE owner = ? ORDER BY bought_date DESC LIMIT 50",
        [m.from_user.id],
    ).fetchall()

    if not history:
        cards_txt = "<b>Você ainda não comprou nenhuma CC.</b>"
    else:
        cards = []
        for card in history:
            cards.append("|".join([i for i in card]))
        cards_txt = "\n".join([f"<code>{cds}</code>" for cds in cards])

    await m.edit_message_text(
        f"""<b>💳 Histórico de compras</b>
<i>- Consulte seu histórico de 50 ultimas compras.</i>

{cards_txt}""",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^swap$"))
async def swap_points(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("« Voltar", callback_data="my_account"),
            ],
        ]
    )

    user_id = m.from_user.id
    balance, diamonds = cur.execute(
        "SELECT balance, balance_diamonds FROM users WHERE id=?", [user_id]
    ).fetchone()

    if diamonds >= 100:
        add_balance = round((diamonds / 2), 2)
        new_balance = round((balance + add_balance), 2)

        txt = f"💎 Seus <b>{diamonds}</b> pontos foram convertidos em R$ <b>{add_balance}</b> de saldo."

        cur.execute(
            "UPDATE users SET balance = ?, balance_diamonds=?  WHERE id = ?",
            [new_balance, 0, user_id],
        )
        return await m.edit_message_text(txt, reply_markup=kb)

    await m.answer(
        "Você não tem pontos suficientes para realizar a troca. O mínimo é 100 pontos.",
        show_alert=True,
    )


@Client.on_callback_query(filters.regex(r"^swap_info$"))
async def swap_info(c: Client, m: CallbackQuery):
    await m.message.delete()

    cpf = await m.message.ask(
        "<b>👤 CPF da lara (válido) da lara que irá pagar</b>",
        reply_markup=ForceReply(),
        timeout=120,
    )
    name = await m.message.ask(
        "<b>👤 Nome completo do pagador</b>", reply_markup=ForceReply(), timeout=120
    )
    email = await m.message.ask(
        "<b>📧 E-mail</b>", reply_markup=ForceReply(), timeout=120
    )
    cpf, name, email = cpf.text, name.text, email.text
    cur.execute(
        "UPDATE users SET cpf = ?, name = ?, email = ?  WHERE id = ?",
        [cpf, name, email, m.from_user.id],
    )
    save()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("« Voltar", callback_data="start"),
            ]
        ]
    )
    await m.message.reply_text(
        "<b> Seus dados foram alterados com sucesso.</b>", reply_markup=kb
    )
