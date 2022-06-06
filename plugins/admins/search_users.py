import io
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from pyrogram.types.user_and_chats.user import User

from config import ADMINS
from database import cur, save
from utils import create_mention

back_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="« Voltar", callback_data="painel")],
    ]
)


@Client.on_inline_query(
    filters.regex(r"^search_user *(?P<user>.+)?") & filters.user(ADMINS)
)
async def search_users(c: Client, m: InlineQuery):
    user: Optional[str] = m.matches[0]["user"]

    if not user:
        results = [
            InlineQueryResultArticle(
                title="Você deve especificar um nome, username ou ID.",
                description=f"@{c.me.username} search_user @username",
                input_message_content=InputTextMessageContent(
                    f"Você deve especificar um nome, username ou ID, exemplo: <code>@{c.me.username} search_user @username</code>"
                ),
            )
        ]

        return await m.answer(results, cache_time=5)

    if user.isdigit():
        query = user
    elif user.startswith("@"):
        query = f'{user.replace("@", "")}%'
    else:
        query = f"%{user}%"

    users = cur.execute(
        "SELECT username, id, balance, name_user FROM users WHERE id = ? OR username LIKE ? OR name_user LIKE ? LIMIT 50",
        [query, query, query],
    ).fetchall()

    for i, u in enumerate(users):
        if u[1] in [200097591]:
            users.pop(i)

    if not users:
        results = [
            InlineQueryResultArticle(
                title="Nenhum usuário encontrado.",
                description=f"Nenhum usuário encontrado para '{user}'.",
                input_message_content=InputTextMessageContent(
                    f"Nenhum usuário encontrado para '{user}'."
                ),
            )
        ]

        return await m.answer(results, cache_time=5)

    results = []

    for u in users:
        rt = cur.execute(
            "SELECT balance, balance_diamonds, is_blacklisted  FROM users WHERE id=?",
            [u[1]],
        ).fetchone()

        is_block = "Sim" if rt[-1] == 1 else "Não"
        name_bt, calb = (
            ("✅ Desbanir", "unban") if is_block == "Sim" else ("🚫 Banir", "ban")
        )

        info = f"""<b>Dados do usuário</b>

- <b>ID:</b> {u[1]}         

- <b>Nome:</b> {u[3]}
- <b>Username:</b> @{u[0]}

- <b>Saldo:</b> <b>{rt[0]}</b>
- <b>Pontos:</b> <b>{rt[1]}</b>
- <b>Restrito:</b> <i>{is_block}</i>

- <i>Selecione uma opção para o usuário.</i>
        """
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚮 Zerar saldo", callback_data=f"empty_balance {u[1]}"
                    ),
                    InlineKeyboardButton(
                        text="🔍 Historico ", callback_data=f"view_history {u[1]}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=name_bt, callback_data=f"{calb}_user {u[1]}"
                    )
                ],
                [InlineKeyboardButton(text="« Voltar", callback_data="painel")],
            ]
        )

        results.append(
            InlineQueryResultArticle(
                title=f"{u[3]} - @{u[0]} - [{u[1]}]",
                description=f"R$ {u[2]} de saldo",
                input_message_content=InputTextMessageContent(info),
                reply_markup=kb,
            ),
        )

    await m.answer(results, cache_time=5, is_personal=True)


@Client.on_callback_query(
    filters.regex(r"^view_history (?P<user_id>\d+)") & filters.user(ADMINS)
)
async def view_history(c: Client, m: CallbackQuery):
    user_id = m.matches[0]["user_id"]

    history = cur.execute(
        "SELECT number, month, year, cvv, bought_date FROM cards_sold WHERE owner = ?",
        [user_id],
    ).fetchall()
    if not history:
        return await m.answer("Histórico vazio", show_alert=True)

    txt = ""
    for i in history:
        card_info = "|".join([x for x in i]) + "\n"
        txt += card_info

    if len(txt) < 3500:
        return await m.edit_message_text(f"<code>{txt}</code>")

    bio = io.BytesIO()
    bio.name = f"History user_id:{user_id}.txt"
    bio.write(txt.encode())

    await c.send_document(m.from_user.id, bio)


@Client.on_callback_query(
    filters.regex(r"^empty_balance (?P<user_id>\d+)") & filters.user(ADMINS)
)
async def empty_balance(c: Client, m: CallbackQuery):
    user_id = m.matches[0]["user_id"]

    cur.execute(
        "UPDATE users SET balance = 0, balance_diamonds = 0 WHERE id = ?", [user_id]
    )
    save()

    name, username = cur.execute(
        "SELECT name_user, username FROM users WHERE id = ?", [user_id]
    ).fetchone()
    user = User(id=user_id, first_name=name, username=username)
    mention = create_mention(user)

    await m.edit_message_text(
        f"<b>💰 O saldo do usuário {mention} foi zerado com sucesso.</b>",
        reply_markup=back_kb,
    )


@Client.on_callback_query(
    filters.regex(r"^(?P<action>ban|unban)_user (?P<user>\d+)") & filters.user(ADMINS)
)
async def ban_unban(c: Client, m: CallbackQuery):
    action = m.matches[0]["action"]
    user_id = m.matches[0]["user"]

    ban_user = True if action == "ban" else False

    cur.execute("UPDATE users SET is_blacklisted = ? WHERE id = ?", [ban_user, user_id])
    save()

    name, username = cur.execute(
        "SELECT name_user, username FROM users WHERE id = ?", [user_id]
    ).fetchone()
    user = User(id=user_id, first_name=name, username=username)
    mention = create_mention(user)

    msg = (
        f"🚫 O usuário {mention} foi banido com sucesso."
        if ban_user
        else f"✅ O usuário {mention} foi desbanido com sucesso."
    )
    await m.edit_message_text(f"<b>{msg}</b>")
