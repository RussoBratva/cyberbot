from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMINS
from database import cur


@Client.on_callback_query(filters.regex(r"^report (?P<days>\d+)"))
@Client.on_message(filters.command(["report", "relatorio"]) & filters.user(ADMINS))
async def report(c: Client, m: Union[CallbackQuery, Message]):
    if isinstance(m, CallbackQuery):
        send = m.edit_message_text
        days = int(m.matches[0]["days"])
    else:
        send = m.reply_text
        days = 1

    # days = 0 == since 0h
    if days == 0:
        last_days = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        last_days = (datetime.now() - timedelta(days=days)).replace(microsecond=0)

    count_balances = cur.execute(
        "SELECT type, SUM(value), count() FROM sold_balance WHERE add_balance_date >= ? GROUP BY type",
        [last_days],
    ).fetchall()

    sold_cards = cur.execute(
        "SELECT SUM(value), SUM(quantity) FROM sold_balance WHERE add_balance_date >= ? AND type = ?",
        [last_days, "cards"],
    ).fetchone()

    list_bt = []
    for x in [1, 2, 3, 4, 5, 6, 7, 15, 30]:
        tx = "dia" if x == 1 else "dias"

        emj = "✅" if days == x else "☑"
        list_bt.append(
            InlineKeyboardButton(
                text=f"{emj} {x} {tx}",
                callback_data=f"report {x}",
            )
        )

    organ = (
        lambda data, step: [data[x : x + step] for x in range(0, len(data), step)]
    )(list_bt, 3)

    emj = "✅" if days == 0 else "☑"

    buttons_list = [
        [
            InlineKeyboardButton(
                text=f"{emj} Desde o início do dia",
                callback_data="report 0",
            )
        ]
    ] + organ

    kb = InlineKeyboardMarkup(inline_keyboard=buttons_list)
    balances = {x[0]: [x[1], x[2]] for x in count_balances}

    em = "das últimas" if days in [1, 2, 3] else "dos últimos"

    h_d = f"{days * 24} horas" if days in [1, 2, 3] else f"{days} dias"

    nm = "desde o <b>início do dia</b>" if days == 0 else f"{em} <b>{h_d}</b>"

    txt = f"""<b>📊 Relatório de vendas</b>

<b>💳 Cartões vendidos</b> ({nm})
 ├ Valor total das vendas: <b>R$ {round(sold_cards[0] or 0, 2)}</b>
 └ Número total de vendas: <b>{sold_cards[1] or 0}</b>

<b>💰 Adições por <i>Pix automático</i></b> ({nm})
 ├ Valor total de adições de saldo: <b>R$ {round(balances["auto"][0], 2) if balances.get("auto") else 0}</b>
 └ Número de adições de saldo: <b>{balances["auto"][1] if balances.get("auto") else 0}</b>

<b>🏷 Adições por <i>Pix manual</i></b> ({nm})
 ├ Valor total de adições de saldo: <b>R$ {round(balances["manual"][0], 2) if balances.get("manual") else 0}</b>
 └ Número de gifts resgatados: <b>{balances["manual"][1] if balances.get("manual") else 0}</b>
"""

    return await send(txt, reply_markup=kb)
