import base64
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Union

import httpx

from database import cur, save
from utils import hc


def names(nms):
    nms = nms.split()
    first_name, last_name = "", ""
    if len(nms) > 1 and len(nms) == 2:
        first_name, last_name = nms[0], nms[1]

    elif len(nms) > 1 and len(nms) == 3:
        first_name, last_name = nms[0], " ".join(nms[1:])

    elif len(nms) > 1 and len(nms) > 3:
        first_name, last_name = " ".join(nms[0:2]), " ".join(nms[2:])

    return first_name, last_name


def get_txid():
    lista = string.ascii_lowercase + string.digits
    txid = "".join(random.choices(lista, k=35))
    return txid


def two_case(num: Union[int, float]) -> str:
    return format(float(num), ".2f")


def expire_date_mp(time: int = "minutes") -> str:
    sum_time = timedelta(minutes=time)
    max_time = (datetime.now() + sum_time).astimezone().isoformat()
    expire = "{}.{}{}".format(
        max_time.split(".")[0], max_time.split(".")[1][0:3], max_time.split(".")[1][6:]
    )
    return expire


class MercadoPago:
    """Classe para pagamento do Mercado Pago."""

    def __init__(self, acess_token: str = "app_user"):
        self.acess_token = acess_token
        self.user_id = None
        self.payment_id = None
        self.user_name = None
        self.payment_status = None
        self.value = None
        self.c = "MercadoPago"

    async def create_payment(
        self,
        value,
        email,
        full_name,
        cpf: str,
        user_id: int = "telegran user_id",
        time: int = 30,
    ):
        expire = expire_date_mp(time)
        self.user_id = user_id
        # frist_name, last_name = names(full_name)
        payment = await hc.post(
            "https://api.mercadopago.com/v1/payments",
            headers={"Authorization": f"Bearer {self.acess_token}"},
            json={
                "transaction_amount": float(value),
                "description": "saldo",
                "payment_method_id": "pix",
                "payer": {
                    "email": email,
                    # "first_name": frist_name,
                    # "last_name": last_name,
                    "identification": {"type": "CPF", "number": cpf},
                    "address": {},
                },
                "date_of_expiration": expire,
            },
        )

        rjson: dict = payment.json()

        self.payment_id = rjson.get("id")

        self.user_name = full_name
        # pprint(rjson)
        rt = {
            "payment_id": rjson.get("id"),
            "copy_paste": rjson.get("point_of_interaction")
            .get("transaction_data")
            .get("qr_code"),
            "qr_code": rjson.get("point_of_interaction")
            .get("transaction_data")
            .get("qr_code_base64"),
            "status": rjson.get("status"),
        }
        return rt

    async def verify(self):
        rtr = await hc.get(
            f"https://api.mercadopago.com/v1/payments/{self.payment_id}",
            headers={"Authorization": f"Bearer {self.acess_token}"},
        )

        getpay = rtr.json()

        rt = {
            "status": getpay.get("status"),
            "payer": {"user_name": self.user_name, "user_id": self.user_id},
            "value": self.value,
        }

        if rt["status"] == "approved":
            self.payment_status = "PAGO"

        return self.payment_status


class GerencianetCredentials:
    """Class used only to generate access_token."""

    def __init__(self, client_id, client_secret, key, cert):
        self.payload = {"grant_type": "client_credentials"}

        self.client_id = client_id
        self.client_secret = client_secret

        self.cert = cert
        self.key_pix = key
        timeout = httpx.Timeout(40, pool=None)
        self.hc = httpx.AsyncClient(cert=self.cert, timeout=timeout)

    async def token(self):
        rt = await self.hc.post(
            "https://api-pix.gerencianet.com.br/oauth/token",
            auth=(self.client_id, self.client_secret),
            json=self.payload,
        )
        rjson: dict = rt.json()
        return rjson.get("access_token")


class Gerencianet:
    """Classe para pagamento do Gerencianet."""

    def __init__(self, credentials: GerencianetCredentials):
        self.header = {}
        self.credentials = credentials
        self.cert = credentials.cert
        self.payment_id = None
        self.status_payment = None
        self.key_pix = credentials.key_pix
        self.user_id = None
        self.hc = credentials.hc
        self.c = "GerenciaNet"

    async def create_payment(
        self,
        value: Union[int, float] = "digito",
        time: int = "segundos",
        cpf: str = "cpf sem pontuação",
        name: str = "nome completo",
        user_id: int = "user_id",
    ):
        token = await self.credentials.token()
        header = {
            "Authorization": f"Bearer {token}",
        }
        payload = {
            "calendario": {"expiracao": time},
            # "devedor": {"cpf": cpf, "nome": name},
            "valor": {"original": two_case(value)},
            "chave": self.key_pix,
            "solicitacaoPagador": "Informe o número ou identificador do pedido.",
        }
        self.header = header
        dados = await self.hc.post(
            "https://api-pix.gerencianet.com.br/v2/cob",
            headers=header,
            json=payload,
        )
        djson = dados.json()
        ID = djson["loc"]["id"]
        ########################  QRCODE AND COPY PAST PIX ########################################
        url = f"https://api-pix.gerencianet.com.br/v2/loc/{ID}/qrcode"
        rt = await self.hc.get(url, headers=header)

        self.payment_id = djson["txid"]
        self.user_id = user_id

        rjson = rt.json()

        return rjson

    async def verify(self):
        url = f"https://api-pix.gerencianet.com.br/v2/cob/{self.payment_id}"  # https://qrcodes-pix.gerencianet.com.br/v2/
        response = await self.hc.get(url, headers=self.header)

        rjson = response.json()

        if rjson["status"].upper() == "CONCLUIDA":
            self.status_payment = "PAGO"

        return self.status_payment


class PagBankCredentials:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        key_pix: str,
        path_pem: str,
        path_key: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.key_pix = key_pix
        self.path_pem = path_pem
        self.path_key = path_key
        self.hc = None
        self.headers = None

    async def gerar_tk(self):
        timeout = httpx.Timeout(40, pool=None)
        self.hc = httpx.AsyncClient(
            cert=(self.path_pem, self.path_key), timeout=timeout
        )
        ac_token = cur.execute(
            "SELECT bearer_tk FROM tokens WHERE type_token = ?", ["pagbank"]
        ).fetchone()[0]

        if ac_token and ac_token != "None":
            return ac_token

        url = "https://secure.api.pagseguro.com/pix/oauth2"

        payload = {
            "grant_type": "client_credentials",
            "scope": "pix.write pix.read payloadlocation.write payloadlocation.read cob.write cob.read",
        }

        gerar = await self.hc.post(
            url, auth=(self.client_id, self.client_secret), json=payload
        )
        rt = gerar.json()["access_token"]
        cur.execute(
            "UPDATE tokens SET bearer_tk = ? WHERE type_token = ?", [rt, "pagbank"]
        )
        save()
        return rt


class PagBank:
    def __init__(self, credentials: PagBankCredentials):
        self.user_id = None
        self.status_payment = None
        self.headers = None
        self.key_pix = credentials.key_pix
        self.txid = get_txid()
        self.hc = credentials.hc
        self.credentials = credentials
        self.c = "PagBank"

    async def create_payment(self, value, cpf, name, user_id, time):
        self.user_id = user_id
        self.txid = get_txid()
        token = await self.credentials.gerar_tk()

        url = f"https://secure.api.pagseguro.com/instant-payments/cob/{self.txid}"

        self.headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "calendario": {"expiracao": time},
            # "devedor": {"cpf": cpf, "nome": name},
            "valor": {"original": two_case(value)},
            "chave": self.key_pix,
            "solicitacaoPagador": "Compra de saldo",
        }

        rt = await self.hc.put(url, headers=self.headers, json=payload)
        return rt.json()

    async def verify(self):
        rt = await self.hc.get(
            f"https://secure.api.pagseguro.com/instant-payments/cob/{self.txid}?revisao=0",
            headers=self.headers,
        )

        rjson = rt.json()

        if rjson["status"] == "CONCLUIDA":
            self.status_payment = "PAGO"
            await self.hc.aclose()
        return self.status_payment


class JunoCredentials:
    def __init__(self, client_id, client_secret, key_pix, priv_token):
        self.auth = base64.b64encode((f"{client_id}:{client_secret}").encode()).decode()
        self.priv_token = priv_token
        self.key_pix = key_pix

    async def Acess_token(self):
        auth_tk = await hc.post(
            url="https://api.juno.com.br/authorization-server/oauth/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {self.auth}",
            },
            data={"grant_type": "client_credentials"},
        )
        return auth_tk.json()["access_token"]


class Juno:
    def __init__(self, objeto: JunoCredentials):
        self.payment_id = None
        self.status_payment = None
        self.user_id = None
        self.key_pix = objeto.key_pix
        self.auth = objeto.auth
        self.priv_token = objeto.priv_token
        self.objs = objeto
        self.txid = get_txid()
        self.headers = None
        self.c = "Juno"

    async def create_payment(
        self,
        value: Union[int, float] = "digito",
        time: int = 300,
        cpf: str = "cpf sem pontuação",
        name: str = "nome completo",
        user_id: int = "user_id",
    ):

        self.user_id = user_id
        self.txid = get_txid()
        dados_cob = {
            "calendario": {"expiracao": time},
            # "devedor": {"cpf": cpf, "nome": name},
            "valor": {"original": two_case(value)},
            "chave": self.key_pix,
            "solicitacaoPagador": "Serviço realizado.",
        }

        access_token = await self.objs.Acess_token()

        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Api-Version": "2",
            "X-Resource-Token": self.priv_token,
            "X-Idempotency-Key": str(uuid.uuid4()).upper(),
        }

        cob_imediata = await hc.put(
            url=f"https://api.juno.com.br/pix-api/v2/cob/{self.txid}",
            headers=self.headers,
            json=dados_cob,
        )
        qr_code = await hc.get(
            f"https://api.juno.com.br/pix-api/qrcode/v2/{self.txid}",
            headers=self.headers,
        )
        return base64.b64decode(qr_code.json()["qrcodeBase64"]).decode()

    async def verify(self):
        rt = await hc.get(
            f"https://api.juno.com.br/pix-api/v2/cob/{self.txid}", headers=self.headers
        )
        self.status_payment = "PAGO" if rt.json()["status"] == "CONCLUIDA" else None
        return self.status_payment


AUTO_PAYMENTS = {
    "mercado pago": MercadoPago,
    "gerencia net": Gerencianet,
    "pagbank": PagBank,
    "juno": Juno,
}
