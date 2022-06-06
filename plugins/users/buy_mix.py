from io import BytesIO

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import ADMIN_CHAT
from database import cur, save
from plugins.users.buy_cc import chking
from utils import (
    create_mention,
    get_info_wallet,
    get_price,
    insert_buy_sold,
    insert_sold_balance,
    lock_user_buy,
    msg_mix_buy_user,
    msg_mix_group_adm,
)


# Opção Compra de CCs tipo Mix.
@Client.on_callback_query(filters.regex(r"^buy_cc mix$"))
async def buy_mixes(c: Client, m: CallbackQuery):
    levels_list = cur.execute(
        "SELECT price_name, price FROM prices WHERE price_type LIKE ?", ["mix"]
    ).fetchall()
    levels_list.sort(key=lambda x: int(x[0]))

    levels = []
    for level, price in levels_list:
        levels.append(
            InlineKeyboardButton(
                text=f"Mix {level} | R$ {price}", callback_data=f"buy_cc mix {level}"
            )
        )

    organ = (
        lambda data, step: [data[x : x + step] for x in range(0, len(data), step)]
    )(levels, 2)
    organ.append([InlineKeyboardButton(text="« Voltar", callback_data="buy_cc")])
    kb = InlineKeyboardMarkup(inline_keyboard=organ)

    await m.edit_message_text(
        f"""<b>🎲 Comprar Mix</b>
<i>- Escolha abaixo a quantidade desejada.</i>

{get_info_wallet(m.from_user.id)}""",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^buy_cc mix (?P<quantity>\d+)"))
@lock_user_buy
async def buy_mix(c: Client, m: CallbackQuery):
    user_id = m.from_user.id
    balance: int = cur.execute("SELECT balance FROM users WHERE id = ?", [user_id]).fetchone()[0]  # fmt: skip

    type_cc = "mix"
    quantity = int(m.matches[0]["quantity"])

    do_check = quantity <= 10

    price = await get_price(type_cc, quantity)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="« Voltar", callback_data="buy_cc"),
            ],
        ]
    )

    if balance < price:
        return await m.answer(
            "Você não possui saldo suficiente para esse item. Por favor, faça uma transferência.",
            show_alert=True,
        )

    ccs_list = cur.execute(
        "SELECT number, month, year, cvv, level, added_date, vendor, bank, country, cpf, name FROM cards WHERE pending = ? ORDER BY RANDOM() LIMIT ?",
        [False, quantity * 20 if do_check else quantity],
    ).fetchall()

    if len(ccs_list) < quantity:
        return await m.answer(
            "❗️ Não há CCs disponiveis para o tamanho do mix requisitado.",
            show_alert=True,
        )

    sold_list = []

    await m.edit_message_text("⏰ Aguarde, estou processando o seu pedido...")

    for tp in ccs_list:
        (
            number,
            month,
            year,
            cvv,
            level,
            added_date,
            vendor,
            bank,
            country,
            cpf,
            name,
        ) = tp

        card = "|".join([number, month, year, cvv])
        is_pending = cur.execute(
            "SELECT pending FROM cards WHERE number = ?", [tp[0]]
        ).fetchone()
        # Se retornar None, a cc já foi vendida ou marcada die.
        # Se is_pending[0] for True, ela está sendo verificada por outro processo.
        if not is_pending or is_pending[0]:
            continue
        cur.execute("UPDATE cards SET pending = 1 WHERE number = ?", [number])
        if do_check:
            live_or_die = await chking(card)
        else:
            live_or_die = True, None

        if live_or_die[0]:  # caso venha cc live
            sold_list.append(tp)
            if len(sold_list) == quantity:
                break
            if do_check:
                await m.edit_message_text(
                    f"⏰ Aguarde, estou processando o seu pedido... ({len(sold_list)}/{quantity})"
                )

        elif live_or_die[0] is None:  # ccs type return None
            cur.execute("UPDATE cards SET pending = False WHERE number = ?", [tp[0]])

        else:  # para cc die
            cur.execute(
                "DELETE FROM cards WHERE number = ?",
                [tp[0]],
            )
            values = "number, month, year, cvv, level, added_date, vendor, bank, country, cpf, name, plan"
            list_dies = tp + (type_cc,)
            cur.execute(
                f"INSERT INTO cards_dies({values}) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                list_dies,
            )
    # Fim do for, finaliza a compra aqui.

    # Se o tamanho da lista de CCs checadas for inferior a quantidade:
    if len(sold_list) < quantity:
        return await m.edit_message_text(
            "Infelizmente não consegui completar sua requisição de mix.",
            reply_markup=kb,
        )

    # Se o tamaho da lista for igual ao requisitado (sucesso), continua a compra:
    diamonds = (price / 100) * 8

    base = await msg_mix_buy_user(
        user_id,
        quantity,
        price,
        diamonds,
    )

    to_message = []

    for new_cc in sold_list:
        (
            number,
            month,
            year,
            cvv,
            level,
            added_date,
            vendor,
            bank,
            country,
            cpf,
            name,
        ) = new_cc

        cur.execute(
            "DELETE FROM cards WHERE number = ?",
            [number],
        )

        list_dados = new_cc + (user_id, f"mix {quantity}", True)

        insert_buy_sold(list_dados)

        to_message.append("|".join([number, month, year, cvv, vendor, level, bank]))

    insert_sold_balance(price, user_id, "cards", quantity=quantity)

    await m.edit_message_text(base)

    file = BytesIO()
    file.name = f"mix_{m.from_user.id}.txt"
    file.write("\n".join(to_message).encode())

    await m.message.reply_document(file)

    cur.execute(
        "UPDATE users SET balance = round(balance - ?, 2), balance_diamonds = round(balance_diamonds + ?, 2) WHERE id = ?",
        [price, diamonds, user_id],
    )

    await m.message.reply_text(
        "✅ Compra realizada com sucesso. Clique no botão abaixo para voltar para o menu principal.",
        reply_markup=kb,
    )

    mention = create_mention(m.from_user)
    adm_msg = msg_mix_group_adm(
        mention,
        quantity,
        price,
        round(balance - price, 2),
    )
    await c.send_message(ADMIN_CHAT, adm_msg)
    await c.send_document(ADMIN_CHAT, file)

    save()
