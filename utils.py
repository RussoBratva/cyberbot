import html
from asyncio import Lock
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Iterable, Optional, Tuple, Union

import httpx
from async_lru import alru_cache
from pyrogram import Client
from pyrogram.types import CallbackQuery, User

from database import cur

timeout = httpx.Timeout(40, pool=None)

hc = httpx.AsyncClient(http2=True, timeout=timeout)


lock = Lock()


def is_bot_online() -> bool:
    """Retorna `True` se o bot está online ou `False` se ele está em manutenção."""

    q = cur.execute("SELECT is_on from bot_config")

    return bool(q.fetchone()[0])


def is_user_banned(user_id: int) -> bool:
    """Retorna `True` se o usuário está banido ou `False` caso contrário."""

    q = cur.execute("SELECT is_blacklisted from users WHERE id = ?", [user_id])
    res = q.fetchone()

    return bool(res[0] if res else res)


def get_lara_info() -> Tuple[str, str]:
    """Retorna uma tupla contendo o nome da lara e chave Pix."""

    q = cur.execute("SELECT lara_name, lara_key from bot_config")

    return q.fetchone()


def get_support_user() -> str:
    """Retorna uma string contendo o username do usuário de suporte."""

    q = cur.execute("SELECT support_user from bot_config")

    return q.fetchone()[0]


def get_news_user() -> str:
    """Retorna uma string contendo o username do canal de notícias."""

    q = cur.execute("SELECT channel_user from bot_config")

    return q.fetchone()[0]


def get_info_wallet(user_id: int) -> str:
    base = """<b>🏦 Carteira:</b>
<b> ├ ID:</b> <code>{}</code>
<b> ├💰 Saldo: R$ {}</b>
<b> └💎 Pontos: {}</b>"""
    rt = cur.execute(
        "SELECT id, balance, balance_diamonds FROM users WHERE id=?", [user_id]
    ).fetchone()
    return base.format(*rt)


def insert_buy_sold(lista: Iterable = "sequence"):
    list_itens = "number, month, year, cvv, level, added_date, vendor, bank, country, cpf, name, owner, plan, is_checked"
    cur.execute(
        f"INSERT INTO cards_sold({list_itens}) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        lista,
    )


def insert_sold_balance(
    value: int, owner: int, type_add_balance: str, quantity: int = 1
):
    cur.execute(
        """INSERT INTO sold_balance(type, value, owner, quantity) VALUES(?, ?, ?, ?)""",
        [type_add_balance, value, owner, quantity],
    )


async def msg_buy_off_user(
    user_id: int,
    card: str,
    vendor: str,
    country: str,
    bank: str,
    level_cc: str,
    price: int,
    received_points: float,
    dados: Optional[Tuple[str, str]] = None,
) -> str:
    cpf, name = dados if dados else await get_person()
    bdados = f"""\n<b>Nome</b> <code>{name}</code>\n<b>Cpf:</b> <code>{cpf}</code>\n"""

    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    produto = f"""<b>💳 Produto:</b>
<b>Card:</b> <code>{card}</code>
<b>Bandeira:</b> <code>{vendor}</code>
<b>País: </b><code>{country}</code>
<b>Banco: </b> <code>{bank}</code>"""

    base = f"""<b>☑️ Compra efetuada!</b>
<b>- {level_cc}</b>
<b>- Preço: R$ {price}</b>
<b>- Novo Saldo: R$ {new_balance}</b>
<b>- Pontos recebidos: {received_points}</b>


<b>NÃO GARANTIMOS A APROVAÇÃO</b>
<b>NÃO GARANTIMOS SALDO</b>

{produto}
{bdados}
Produto comprado com gate off, ou seja, sem troca."""
    return base


async def msg_buy_user(
    user_id: int,
    card: str,
    vendor: str,
    country: str,
    bank: str,
    level_cc: str,
    price: int,
    received_points: float,
    dados: Optional[Tuple[str, str]] = None,
) -> str:
    cpf, name = dados if dados else await get_person()

    time = cur.execute("SELECT time_exchange FROM bot_config").fetchone()[0]
    bdados = f"\n<b>Nome:</b> <code>{name}</code>\n<b>CPF:</b> <code>{cpf}</code>\n"

    exchange_on = bool(cur.execute("SELECT exchange_is FROM bot_config").fetchone()[0])
    time_exchange = int(
        cur.execute("SELECT time_exchange FROM bot_config").fetchone()[0]
    )
    time_max = (datetime.now() + timedelta(minutes=time_exchange)).strftime(
        "%d/%m/%Y %H:%M:%S"
    )
    info = f"⏳ Tempo máximo de troca {time_max}." if exchange_on else ""
    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    produto = f"""<b>💳 Produto:</b>
<b>Card:</b> <code>{card}</code>
<b>Bandeira:</b> <code>{vendor}</code>
<b>País: </b><code>{country}</code>
<b>Banco: </b> <code>{bank}</code>"""

    troca = (
        f"\nVocê tem {time} minutos para trocar se alguma CC não estiver live."
        if exchange_on
        else ""
    )

    base = f"""<b>✅ Compra efetuada!</b>
<b>- {level_cc}</b>
<b>- Preço: R$ {price}</b>
<b>- Novo Saldo: R$ {new_balance}</b>
<b>- Pontos recebidos: {received_points}</b>


<b>GARANTIMOS SOMENTE LIVE!</b>
<b>NÃO GARANTIMOS A APROVAÇÃO</b>
<b>NÃO GARANTIMOS SALDO</b>

{produto}
{bdados}{troca}

<b>{info}</b>"""
    return base


async def msg_mix_buy_user(
    user_id,
    level_cc,
    price,
    received_points,
) -> str:
    time = cur.execute("SELECT time_exchange FROM bot_config").fetchone()[0]

    swap_is = cur.execute("SELECT exchange_is FROM bot_config").fetchone()[0]

    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    troca = (
        f"\nVocê tem {time * level_cc} minutos para trocar se alguma CC não estiver live."
        if swap_is == 1
        else ""
    )

    base = f"""<b>✅ Compra efetuada!</b>
<b>- Mix {level_cc}</b>
<b>- Preço: R$ {price}</b>
<b>- Novo Saldo: R$ {new_balance}</b>
<b>- Pontos recebidos: {received_points}</b>


<b>GARANTIMOS SOMENTE LIVE!</b>
<b>NÃO GARANTIMOS A APROVAÇÃO</b>
<b>NÃO GARANTIMOS SALDO</b>
{troca}

<b>Produto segue no arquivo abaixo:</b>"""
    return base


def msg_group_adm(
    mention, card, level, type_buy, price, gate, new_balance, vendor
) -> str:
    produto = f"""<b>💳 </b> {mention} <b>comprou {type_buy} {level}</b>
<b>- Preço: R$ {price}</b>
<b>- Novo saldo: R$ {new_balance}</b>

<b>- Produto:</b>
<code>{card}|{vendor}|{gate}</code>"""
    return produto


def msg_mix_group_adm(mention, quantity, price, new_balance) -> str:
    produto = f"""<b>🎲 </b> {mention} <b>comprou Mix {quantity}</b>
<b>- Preço: R$ {price}</b>
<b>- Novo saldo: R$ {new_balance}</b>

<b>Produto segue no arquivo abaixo:</b>"""
    return produto


async def get_price(price_type: str, price_name: str) -> int:
    """
    Retorna uma int contendo o preço do item.

    O parâmetro `price_type` será o tipo de valor para pesquisar, ex.:
        UNIT (Por level) ou BIN (Por bin).
    O parâmetro `price_name` será o valor para pesquisa, ex.:
        GOLD (Por level) ou 550209 (Por bin).

    Por padrão, caso a compra for de tipo `BIN`, a função tentará obter
    o preço especifico da bin, e caso falhe, procurará o nível em `UNIT`,
    e caso falhe novamente, procurará o valor de INDEFINIDO em UNIT,
    e caso falhe novamente fará um "fallback" para R$ 12.
    """

    if price_type == "bin":
        price = cur.execute(
            "SELECT price FROM prices WHERE price_type = ? AND price_name LIKE ?",
            [price_type, price_name],
        ).fetchone()

        if price:
            return price[0]

        # Caso não exista preço de bin, pesquisa o level:
        new_price_type = "unit"
        price_name = (await search_bin(price_name))["level"]
    else:
        new_price_type = price_type

    # Caso seja unit ou a bin acima não tinha preço:
    price = cur.execute(
        "SELECT price FROM prices WHERE price_type = ? AND price_name LIKE ?",
        [new_price_type, price_name],
    ).fetchone()

    if price:
        return price[0] + (5 if price_type == "bin" else 0)

    # Caso o level requisitado não exista na db:
    price = cur.execute(
        "SELECT price FROM prices WHERE price_type = ? AND price_name LIKE ?",
        [new_price_type, "INDEFINIDO"],
    ).fetchone()

    if price:
        return price[0] + (5 if price_type == "bin" else 0)

    return 12


async def get_person():
    rt = await hc.get(
        "http://140.82.31.167:5000/@metaofc/dados",
    )
    rjson = rt.json()

    return (rjson["cpf"], rjson["name"])


def create_mention(user: User, with_id: bool = True) -> str:
    name = f"@{user.username}" if user.username else html.escape(user.first_name)

    mention = f"<a href='tg://user?id={user.id}'>{name}</a>"

    if with_id:
        mention += f" (<code>{user.id}</code>)"

    return mention


@alru_cache(maxsize=1024, cache_exceptions=False)
async def search_bin(card_bin: Union[str, int]) -> dict:
    """Pesquisa informações sobre a bin e as retorna em um dict."""

    try:
        r = await hc.get(
            f"http://127.0.0.1/search/bin={card_bin}",
        )

        rj = r.json()

        info = {
            "card_bin": card_bin,
            "country": rj.get("pais") or "INDEFINIDO",
            "vendor": rj.get("bandeira") or "INDEFINIDO",
            "card_type": rj.get("type") or "INDEFINIDO",
            "level": rj.get("nivel") or "INDEFINIDO",
            "bank": rj.get("banco") or "INDEFINIDO",
        }
        return info
    except:
        info = {
            "card_bin": card_bin,
            "country": "INDEFINIDO",
            "vendor": "INDEFINIDO",
            "card_type": "INDEFINIDO",
            "level": "INDEFINIDO",
            "bank": "INDEFINIDO",
        }
        return info


def to_hex(dec: float):
    digits = "0123456789ABCDEF"
    x = dec % 16
    rest = dec // 16
    if rest == 0:
        return digits[x]
    return to_hex(rest) + digits[x]


def get_crc16(payload: str):
    crc = 0xFFFF
    for i in range(len(payload)):
        crc ^= ord(payload[i]) << 8
        for j in range(8):
            if (crc & 0x8000) > 0:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
    return to_hex(crc & 0xFFFF).upper()


def create_copy_paste_pix(location: str) -> str:
    # Copy paste sem CRC16
    copy_paste = f"00020126830014br.gov.bcb.pix2561{location}520489995303986540105802BR5921Pagseguro Internet SA6009SAO PAULO62070503***6304"

    return copy_paste + get_crc16(copy_paste)


def lock_user_buy(f: Callable):
    @wraps(f)
    async def lock_user(c: Client, m: CallbackQuery, *args, **kwargs):
        q = cur.execute(
            "SELECT is_action_pending FROM users WHERE id = ?", [m.from_user.id]
        ).fetchone()
        cur.execute(
            "UPDATE users SET is_action_pending = ? WHERE id = ?",
            [True, m.from_user.id],
        )
        if q[0]:
            return await m.answer(
                "Você só pode fazer uma compra/troca por vez. Por favor aguarde seu pedido anterior ser concluído.",
                show_alert=True,
            )
        try:
            return await f(c, m, *args, **kwargs)
        finally:
            cur.execute(
                "UPDATE users SET is_action_pending = ? WHERE id = ?",
                [False, m.from_user.id],
            )

    return lock_user


MSG_TEO = """<b>⏰ Condições de Troca:</b>\n
<i>O tempo de troca é em até 5 minutos, feito pelo próprio bot, no botao </i><b>"TROCA"</b><i>na tela principal.
O bot não permitirá troca caso passe 1 segundo deste tempo, por favor não insista com o vendedor.
 Caso haja a necessidade de troca, o próprio bot testará outra cc e lhe enviará live. Boas compras.</i>"""
