import html
import traceback

from meval import meval
from pyrogram import Client, filters
from pyrogram.types import Message

from config import SUDOERS


@Client.on_message(filters.command("eval", "!") & filters.user(SUDOERS))
async def evals(c: Client, m: Message):
    text = m.text.split(maxsplit=1)[1]
    try:
        res = await meval(text, globals(), **locals())
    except:  # skipcq
        ev = traceback.format_exc()
        await m.reply_text(f"<code>{html.escape(ev)}</code>")
    else:
        try:
            await m.reply_text(f"<code>{html.escape(str(res))}</code>")
        except Exception as e:  # skipcq
            await m.reply_text(str(e))
