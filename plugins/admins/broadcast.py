import time
from typing import List

from pyrogram import Client, filters
from pyrogram.types import Message

from config import ADMINS
from database import cur


@Client.on_message(filters.command(["broadcast", "enviar"]) & filters.user(ADMINS))
async def broadcast(c: Client, m: Message):
    await m.reply_text(
        "📣 Você está no <b>modo broadcast</b>, no qual você pode enviar mensagens para todos os usuários do bot.\n"
        "Por favor, envie a(s) mensagem(s) que você deseja enviar abaixo. "
        "Envie <b>/enviar</b> novamente para enviar ou <b>/cancel</b> para cancelar."
    )
    last_msg = 0
    messages: List[Message] = []
    while True:
        msg = await c.wait_for_message(m.chat.id, filters.incoming, timeout=300)

        if msg.text:
            if msg.text.startswith("/send") or msg.text.startswith("/enviar"):
                break
            if msg.text.startswith("/cancel"):
                return await m.reply_text("✔️ Comando cancelado.")
        messages.append(msg)
        await msg.reply_text(
            "✔️ Mensagem adicionada. "
            "Envie mais mensagens ou digite <b>/enviar</b> para enviar ou <b>/cancel</b> para cancelar.",
            quote=True,
        )

    if not messages:
        await m.reply_text("❕ Não há nada para enviar. Comando cancelado.")
    else:
        sent = await m.reply_text("📣 Enviando mensagens...")
        all_users = cur.execute(
            "SELECT id FROM users WHERE is_blacklisted = 0"
        ).fetchall()
        users_count = len(all_users)
        count = 0
        for i, u in enumerate(all_users):
            for message in messages:
                try:
                    if message.poll or message.forward_from_chat:
                        await message.forward(u[0])
                    else:
                        await message.copy(u[0])
                except:
                    pass
                else:
                    count += 1
            if time.time() - last_msg > 3:
                last_msg = time.time()
                try:
                    await sent.edit_text(
                        f"📣 Enviando mensagens... {(i / users_count) * 100:.2f}% concluído."
                    )
                except:
                    pass

        await sent.edit_text(
            f"✅ {count} mensagens foram enviadas para {users_count} usuários."
        )
