import asyncio

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from config import ADMIN_CHAT
from database import cur, save
from utils import (
    MSG_TEO,
    create_mention,
    get_info_wallet,
    get_price,
    insert_buy_sold,
    insert_sold_balance,
    lock_user_buy,
    msg_buy_off_user,
    msg_buy_user,
    msg_group_adm,
)

from ..admins.panel_items.select_gate import gates

SELLERS, TESTED = 0, 0

gates_is_on = True if (len(gates) >= 1) else False
T = 0.1


async def chking(card):
    global gates, gates_is_on, T
    name_chk, _ = cur.execute(
        "SELECT gate_chk, gate_exchange FROM bot_config"
    ).fetchone()
    if name_chk == "pre-auth":
        T = 2
    else:
        T = 0.1

    return await gates[name_chk](card)


def rate_ccs():
    global SELLERS, TESTED
    rate = (SELLERS / TESTED) * 100
    return rate


# Listagem de tipos de compra.
@Client.on_callback_query(filters.regex(r"^buy_cc$"))
async def buy_cc_list(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("💳 Unitária", callback_data="buy_cc unit"),
                InlineKeyboardButton("🎲 Mix", callback_data="buy_cc mix"),
            ],
            [
                InlineKeyboardButton(
                    "🏦 Pesquisar banco",
                    switch_inline_query_current_chat="search_cc bank BANCO",
                ),
                InlineKeyboardButton(
                    "🔐 Bin unitária",
                    switch_inline_query_current_chat="search_cc bin 550209",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏳️ Pesquisar bandeira",
                    switch_inline_query_current_chat="search_cc vendor MASTERCARD",
                ),
            ],
            [
                InlineKeyboardButton("« Voltar", callback_data="start"),
            ],
        ]
    )

    await m.edit_message_text(
        f"""<b>💳 Comprar CC</b>
<i>- Escolha abaixo o produto que deseja comprar.</i>

{get_info_wallet(m.from_user.id)}""",
        reply_markup=kb,
    )


# Pesquisa de CCs via inline.
@Client.on_inline_query(filters.regex(r"^search_cc (?P<type>\w+) (?P<value>.+)"))
async def search_cc(c: Client, m: InlineQuery):
    """
    Pesquisa uma CC via inline por tipo e retorna os resultados via inline.

    O parâmetro `type` será o tipo de valor para pesquisar, ex.:
        bin (Por bin), bank (Por banco), vendor (Por bandeira), etc.
    O parâmetro `value` será o valor para pesquisa, ex.:
        550209 (Bin), Nubank (Banco), Mastercard (Bandeira), etc.
    """

    typ = m.matches[0]["type"]
    qry = m.matches[0]["value"]

    # Não aceitar outros valores para prevenir SQL Injection.
    if typ not in ("bin", "bank", "vendor"):
        return

    if typ != "bin":
        qry = f"%{qry}%"

    rt = cur.execute(
        f"SELECT number, month, year, {typ} FROM cards WHERE {typ} LIKE ? AND pending = 0 ORDER BY RANDOM() LIMIT 50",
        [qry.upper()],
    ).fetchall()

    results = []

    wallet_info = get_info_wallet(m.from_user.id)

    for number, month, year, value in rt:

        price = await get_price("bin", number[0:6])

        base = f"""Cartão: {number[0:6]}**********
Validade: {month}/{year}
Cvv: ***"""

        base_ml = f"""<b>Cartão:</b> <i>{number[0:6]}**********</i>
<b>Validade:</b> <i>{month}/{year}</i>
<b>Cvv:</b> <i>***</i>

<b>Valor:</b> <i>R$ {price}</i>"""

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Comprar",
                        callback_data=f"buy_cc bin '{number[0:6]}' {month}|{year}",
                    )
                ]
            ]
        )

        results.append(
            InlineQueryResultArticle(
                title=f"{typ} {value} - R$ {price}",
                description=base,
                input_message_content=InputTextMessageContent(
                    base_ml + "\n\n" + wallet_info
                ),
                reply_markup=kb,
            )
        )

    await m.answer(results, cache_time=5, is_personal=True)


# Opção Compra de CCs e Listagem de Level's.
@Client.on_callback_query(filters.regex(r"^buy_cc unit$"))
async def buy_ccs(c: Client, m: CallbackQuery):
    list_levels_cards = cur.execute("SELECT level FROM cards GROUP BY level").fetchall()
    levels_list = [x[0] for x in list_levels_cards]
    levels = []
    for level in levels_list:
        level_name = level
        n = level.split()
        if len(n) > 1:
            level_name = n[0][:4] + " " + n[1]

        price = await get_price("unit", level)
        levels.append(
            InlineKeyboardButton(
                text=f"{level_name} | R$ {price}",
                callback_data=f"buy_cc unit '{level}'",
            )
        )

    organ = (
        lambda data, step: [data[x : x + step] for x in range(0, len(data), step)]
    )(levels, 2)
    organ.append([InlineKeyboardButton(text="« Voltar", callback_data="buy_cc")])
    kb = InlineKeyboardMarkup(inline_keyboard=organ)
    await m.edit_message_text(
        f"""<b>💳 Comprar CC Unitária</b>
<i>- Selecione o nivel da CC desejada.</i>

<b>- ⚠  Obs: sempre que as CCS forem enviadas e testadas pelo chk serão enviadas com</b>

<i>- ✅ para gates on e cc testada
- ☑ para caso as gates estejam off</i>

{get_info_wallet(m.from_user.id)}""",
        reply_markup=kb,
    )


@Client.on_callback_query(
    filters.regex(r"^buy_cc (?P<type>[a-z]+) '(?P<level_cc>.+)' ?(?P<other_params>.+)?")
)
@lock_user_buy
async def buy_final(c: Client, m: CallbackQuery):
    user_id = m.from_user.id
    balance: int = cur.execute("SELECT balance FROM users WHERE id = ?", [user_id]).fetchone()[0]  # fmt: skip

    type_cc = m.matches[0]["type"]
    level_cc = m.matches[0]["level_cc"]

    price = await get_price(type_cc, level_cc)

    if balance < price:
        return await m.answer(
            "Você não possui saldo suficiente para esse item. Por favor, faça uma transferência.",
            show_alert=True,
        )

    search_for = "level" if type_cc == "unit" else "bin"

    ccs_list = cur.execute(
        f"SELECT number, month, year, cvv, level, added_date, vendor, bank, country, cpf, name FROM cards WHERE {search_for} = ? AND pending = ? ORDER BY RANDOM() LIMIT 20",
        [level_cc, False],
    ).fetchall()

    if not ccs_list:
        return await m.answer("Sem ccs disponiveis para este nivel", show_alert=True)

    if gates_is_on:
        live = 0
        await m.edit_message_text(
            "⏰ Aguarde, estou verificando por uma CC live no banco de dados..."
        )
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
            cur.execute("UPDATE cards SET pending = 1 WHERE number = ?", [tp[0]])
            live_or_die = await chking(card)
            await asyncio.sleep(T)

            list_dados = tp + (user_id, type_cc, True)

            if live_or_die[0]:  # caso venha cc live
                diamonds = (price / 100) * 8
                new_balance = round(balance - price, 2)

                cur.execute(
                    "UPDATE users SET balance = round(balance - ?, 2), balance_diamonds = round(balance_diamonds + ?, 2) WHERE id = ?",
                    [price, diamonds, user_id],
                )
                dados = (cpf, name) if cpf != None else None
                base = await msg_buy_user(
                    user_id,
                    card,
                    vendor,
                    country,
                    bank,
                    level_cc,
                    price,
                    diamonds,
                    dados,
                )

                cur.execute(
                    "DELETE FROM cards WHERE number = ?",
                    [tp[0]],
                )

                insert_buy_sold(list_dados)
                insert_sold_balance(price, user_id, "cards")

                await m.edit_message_text(base)

                mention = create_mention(m.from_user)
                # await m.message.reply_text(MSG_TEO)
                adm_msg = msg_group_adm(
                    mention,
                    card,
                    level_cc,
                    type_cc,
                    price,
                    live_or_die[1],
                    new_balance,
                    vendor,
                )
                await c.send_message(ADMIN_CHAT, adm_msg)

                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="« Voltar", callback_data="buy_cc"
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="Não passou?, troque aqui!",
                                callback_data="exchange",
                            )
                        ],
                    ]
                )
                try:
                    await m.message.reply_text(
                        "✅ Compra realizada com sucesso. Clique no botão abaixo para voltar para o menu principal.",
                        reply_markup=kb,
                    )
                except:
                    ...
                save()
                return

            elif live_or_die[0] is None:  # ccs type return None
                cur.execute(
                    "UPDATE cards SET pending = False WHERE number = ?", [tp[0]]
                )

            else:  # para ccs_die
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

        if (live == 0) and gates_is_on:
            txt = "❗️ Não consegui achar CCs lives deste nível na minha database. Tente novamente com outro nível ou bin."
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="« Voltar", callback_data="buy_cc"),
                    ],
                ]
            )
        else:
            txt = (
                "⚠️ Parece que todas as gates do bot esão offline, você deseja continuar ou tentar novamente?\n"
                "Ao continuar, sua compra será efetuada <b>sem verificar</b>, ou seja, ela <b>não possuirá troca</b>."
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔁 Tentar novamente",
                            callback_data=m.data,
                        ),
                        InlineKeyboardButton(
                            text="✅ Continuar",
                            callback_data=f"buy_off {type_cc} '{level_cc}'",
                        ),
                    ],
                    [
                        InlineKeyboardButton(text="« Cancelar", callback_data="start"),
                    ],
                ]
            )
        await m.edit_message_text(txt, reply_markup=kb)

    # operação de venda caso as gates estejam off
    else:
        txt = (
            "⚠️ Parece que todas as gates do bot esão offline, você deseja continuar?\n"
            "Ao continuar, sua compra será efetuada <b>sem verificar</b>, ou seja, ela <b>não possuirá troca</b>."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Continuar",
                        callback_data=f"buy_off {type_cc} '{level_cc}'",
                    ),
                    InlineKeyboardButton(text="« Cancelar", callback_data="start"),
                ],
            ]
        )
        await m.edit_message_text(txt, reply_markup=kb)

    save()


@Client.on_callback_query(
    filters.regex(r"^buy_off (?P<type>[a-z]+) '(?P<level_cc>.+)' ?(?P<other_params>.+)?")  # fmt: skip
)
@lock_user_buy
async def buy_off(c: Client, m: CallbackQuery):
    user_id = m.from_user.id
    balance: int = cur.execute("SELECT balance FROM users WHERE id = ?", [user_id]).fetchone()[0]  # fmt: skip

    type_cc = m.matches[0]["type"]
    level_cc = m.matches[0]["level_cc"]

    price = await get_price(type_cc, level_cc)

    if balance < price:
        return await m.answer(
            "Você não possui saldo suficiente para esse item. Por favor, faça uma transferência.",
            show_alert=True,
        )

    search_for = "level" if type_cc == "unit" else "bin"

    selected_cc = cur.execute(
        f"SELECT number, month, year, cvv, level, added_date, vendor, bank, country, cpf, name FROM cards WHERE {search_for} = ? AND pending = ? ORDER BY RANDOM()",
        [level_cc, False],
    ).fetchone()

    if not selected_cc:
        return await m.answer("Sem ccs disponiveis para este nivel.", show_alert=True)

    diamonds = round(((price / 100) * 8), 2)
    new_balance = balance - price

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
    ) = selected_cc

    card = "|".join([number, month, year, cvv])

    list_card_sold = selected_cc + (user_id, type_cc, False)

    cur.execute(
        "DELETE FROM cards WHERE number = ?",
        [selected_cc[0]],
    )

    cur.execute(
        "UPDATE users SET balance = ?, balance_diamonds = round(balance_diamonds + ?, 2) WHERE id = ?",
        [new_balance, diamonds, user_id],
    )

    insert_buy_sold(list_card_sold)
    insert_sold_balance(price, user_id, "cards")

    dados = (cpf, name) if cpf is not None else None
    base = await msg_buy_off_user(
        user_id, card, vendor, country, bank, level_cc, price, diamonds, dados
    )
    await m.edit_message_text(base)
    mention = create_mention(m.from_user)
    adm_msg = msg_group_adm(
        mention, card, level_cc, type_cc, price, "None", new_balance, vendor
    )
    await c.send_message(ADMIN_CHAT, adm_msg)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="« Voltar", callback_data="buy_cc"),
            ],
        ]
    )
    try:
        await m.message.reply_text(
            "✅ Compra realizada com sucesso. Clique no botão abaixo para voltar para o menu principal.",
            reply_markup=kb,
        )
    except:
        ...
    save()
