import os
import re
from asyncio.exceptions import TimeoutError
from datetime import datetime
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)

from config import ADMINS
from database import cur, save
from utils import search_bin


def is_valid(now: datetime, month: Union[str, int], year: Union[str, int]) -> bool:
    """Verifica se a CC está dentro da data de validade."""

    now_month = now.month
    now_year = now.year

    # Verifica se o ano for menor que o ano atual.
    if int(year) < now_year:
        return False

    # Se o ano for o mesmo que o atual, verifica se o mês é menor que o atual.
    if int(month) < now_month and now_year == int(year):
        return False

    return True


async def iter_add_cards(cards):
    total = 0
    success = 0
    dup = []
    now = datetime.now()
    for row in re.finditer(
        r"(?P<number>\d{15,16})\W+(?P<month>\d{1,2})\W+(?P<year>\d{2,4})\W+(?P<cvv>\d{3,4}).?(?P<cpf>\d{3}.?\d{3}.?\d{3}.?\d{2})?.?(?P<name>.+)?",
        cards,
    ):
        total += 1
        card_bin = row["number"][:6]
        info = await search_bin(card_bin)
        if info:
            year = "20" + row["year"] if len(row["year"]) == 2 else row["year"]
            card = f'{row["number"]}|{row["month"]}|{year}|{row["cvv"].zfill(3)}'

            if not is_valid(now, row["month"], year):
                dup.append(f"{card} --- Vencida")
                continue

            available = cur.execute(
                "SELECT added_date FROM cards WHERE number = ?", [row["number"]]
            ).fetchone()
            solds = cur.execute(
                "SELECT bought_date FROM cards_sold WHERE number = ?",
                [row["number"]],
            ).fetchone()
            dies = cur.execute(
                "SELECT die_date FROM cards_dies WHERE number = ?",
                [row["number"]],
            ).fetchone()

            if available is not None:
                dup.append(f"{card} --- Repetida (adicionada em {available[0]})")
                continue

            if solds is not None:
                dup.append(f"{card} --- Repetida (vendida em {solds[0]})")
                continue

            if dies is not None:
                dup.append(f"{card} --- Repetida (marcada como die em {dies[0]})")
                continue

            level = info["level"].upper()

            # Alterações opcionais:
            # level = "NUBANK" if info["bank"].upper() == "NUBANK" else level

            name = row["name"] if row["cpf"] else None

            cur.execute(
                "INSERT INTO cards(number, bin, month, year, cvv, vendor, level, bank, country, card_type, cpf, name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["number"],
                    card_bin,
                    row["month"],
                    year,
                    row["cvv"].zfill(3),
                    info["vendor"],
                    level,
                    info["bank"],
                    info["country"],
                    info["card_type"],
                    row["cpf"],
                    name,
                ),
            )

            success += 1

    f = open("para_trocas.txt", "w")
    f.write("\n".join(dup))
    f.close()

    save()
    return (
        total,
        success,
    )


@Client.on_message(filters.regex(r"/add( (?P<cards>.+))?", re.S) & filters.user(ADMINS))
async def on_add_m(c: Client, m: Message):
    cards = m.matches[0]["cards"]

    if cards:
        total, success = await iter_add_cards(cards)
        if not total:
            text = (
                "❌ Não encontrei CCs na sua mensagem. Envie elas como texto ou arquivo."
            )
        else:
            text = f"✅ {success} CCs adicionadas com sucesso. Repetidas/Inválidas: {(total - success)}"
        sent = await m.reply_text(text, quote=True)

        if open("para_trocas.txt").read() != "":
            await sent.reply_document(open("para_trocas.txt", "rb"), quote=True)
        os.remove("para_trocas.txt")

        return

    await m.reply_text(
        "💳 Modo de adição ativo. Envie as CCs como texto ou arquivo e elas serão adicionadas.",
        reply_markup=ForceReply(),
    )

    first = True
    while True:
        if not first:
            await m.reply_text(
                "✔️ Envie mais CCs ou digite /done para sair do modo de adição.",
                reply_markup=ForceReply(),
            )

        try:
            msg = await c.wait_for_message(m.chat.id, timeout=300)
        except TimeoutError:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton("« Voltar", callback_data="start")]
                ]
            )

            await m.reply_text(
                "❕ Não recebi uma resposta para o comando anterior e ele foi automaticamente cancelado.",
                reply_markup=kb,
            )
            return

        first = False

        if not msg.text and (
            not msg.document or msg.document.file_size > 100 * 1024 * 1024
        ):  # 100MB
            await msg.reply_text(
                "❕ Eu esperava um texto ou documento contendo as CCs.", quote=True
            )
            continue
        if msg.text and msg.text.startswith("/done"):
            break

        if msg.document:
            cache = await msg.download()
            with open(cache) as f:
                msg.text = f.read()
            os.remove(cache)

        total, success = await iter_add_cards(msg.text)

        if not total:
            text = (
                "❌ Não encontrei CCs na sua mensagem. Envie elas como texto ou arquivo."
            )
        else:
            text = f"✅ {success} CCs adicionadas com sucesso. Repetidas/Inválidas: {(total - success)}"
        sent = await msg.reply_text(text, quote=True)

        if open("para_trocas.txt").read() != "":
            await sent.reply_document(open("para_trocas.txt", "rb"), quote=True)
        os.remove("para_trocas.txt")

    await m.reply_text(
        "✔ Saiu do modo de adição de CCs.", reply_markup=ReplyKeyboardRemove()
    )
