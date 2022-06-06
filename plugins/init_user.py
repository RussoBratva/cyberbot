from pyrogram import Client, filters
from pyrogram.types import Message

from database import cur, save


@Client.on_message(~filters.channel & ~filters.service, group=-4)
@Client.on_callback_query(group=-3)
async def init_user(c: Client, m: Message):
    user_id = m.from_user.id
    name = m.from_user.first_name
    username = m.from_user.username

    data = cur.execute(
        "SELECT name_user, username FROM users WHERE id = ?", [user_id]
    ).fetchone()

    if data is None:
        cur.execute(
            "INSERT INTO users(id, username, name_user) VALUES(?, ?, ?)",
            [user_id, username, name],
        )

        save()

    elif data != (name, username):
        cur.execute(
            "UPDATE users SET name_user = ?, username = ? WHERE id = ?",
            [name, username, user_id],
        )

        save()
