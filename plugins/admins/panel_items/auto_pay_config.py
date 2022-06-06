import asyncio
import os
import shlex

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import ADMINS
from database import cur, save
from payments import AUTO_PAYMENTS


def if_exists():
    cur.executescript(
        """
    INSERT OR IGNORE INTO tokens(type_token) VALUES('mercado pago');
    INSERT OR IGNORE INTO tokens(type_token) VALUES('gerencia net');
    INSERT OR IGNORE INTO tokens(type_token) VALUES('pagbank');
    INSERT OR IGNORE INTO tokens(type_token) VALUES('juno');
        """
    )
    save()


@Client.on_callback_query(filters.regex(r"^auto_pay$") & filters.user(ADMINS))
async def pix_auto_config(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Troca de tokens", callback_data="config charge_pix"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Selecionar pix para uso", callback_data="config select_pix"
                )
            ],
            [InlineKeyboardButton(text="« Voltar", callback_data="painel")],
        ]
    )

    await m.edit_message_text(
        "<b>Selecione uma opção para prosseguir</b>", reply_markup=kb
    )


@Client.on_callback_query(filters.regex(r"^config (?P<type>.+)") & filters.user(ADMINS))
async def change_options(c: Client, m: CallbackQuery):
    type_config = m.matches[0]["type"]
    opts = []
    for item in AUTO_PAYMENTS:
        opts.append(
            [
                InlineKeyboardButton(
                    text=f"∘ {item}", callback_data=f"{type_config} {item}"
                )
            ]
        )

    if type_config == "select_pix":
        txt = "<b>Seleciona qual pix auto ira operar no bot</b>"
        opts.append(
            [
                InlineKeyboardButton(
                    text="Desativar Pix Auto", callback_data="select_pix off"
                )
            ]
        )
    else:
        txt = "<b>Em qual ira trocar os tokens.</b>"
    opts.append([InlineKeyboardButton(text="« Voltar", callback_data="painel")])
    kb = InlineKeyboardMarkup(inline_keyboard=opts)

    await m.edit_message_text(text=txt, reply_markup=kb)


@Client.on_callback_query(
    filters.regex(r"^charge_pix (?P<name_pix>.+)") & filters.user(ADMINS)
)
async def charge_token_pix(c: Client, m: CallbackQuery):
    await m.message.delete()
    if_exists()
    name_pix = m.matches[0]["name_pix"]

    try:
        os.mkdir("payment_keys")
    except FileExistsError:
        pass

    if name_pix == "gerencia net":
        client_id = await m.message.ask(
            "<i>Envie seu token</i> <b>CLIENT_ID</b>", reply_markup=ForceReply()
        )
        client_secret = await m.message.ask(
            "<i>Envie seu token</i> <b>CLIENT_SECRET</b>", reply_markup=ForceReply()
        )

        pix_key = await m.message.ask(
            "<b>💠 Sua chave pix</b>", reply_markup=ForceReply()
        )

        document = await m.message.ask(
            "<b>Envie seu arquivo .pem ou .p12</b>",
            filters=filters.document,
            reply_markup=ForceReply(),
        )

        out_file_name = os.path.join("payment_keys", "gerencianet.pem")

        if document.document.file_name.lower().endswith(".pem"):
            await document.download(out_file_name)

        elif document.document.file_name.lower().endswith(".p12"):
            in_file_name = await document.download(
                os.path.join("payment_keys", "gerencianet.p12")
            )

            proc = await asyncio.create_subprocess_shell(
                shlex.join(
                    [
                        "openssl",
                        "pkcs12",
                        "-in", in_file_name,
                        "-out", out_file_name,
                        "-nodes",
                        "-passin", "pass:",
                    ]  # fmt: skip
                )
            )

            await proc.communicate()

            os.remove(in_file_name)

            if proc.returncode != 0:
                return await m.message.reply_text(
                    "Ops, ocorreu um erro e o arquivo .p12 não pôde ser convertido para .pem."
                )

        cur.execute(
            "UPDATE tokens SET client_id = ?, client_secret = ?, name_cert_pem = ? WHERE type_token = ?",
            [client_id.text, client_secret.text, out_file_name, name_pix],
        )
        cur.execute("UPDATE bot_config SET random_pix = ?", [pix_key.text])
        save()

    elif name_pix == "mercado pago":
        client_secret = await m.message.ask(
            "<i>Envie seu token</i> <b>APP_USER</b>", reply_markup=ForceReply()
        )
        cur.execute(
            "UPDATE tokens SET client_secret = ? WHERE type_token = ?",
            [client_secret.text, name_pix],
        )
        save()

    elif name_pix == "juno":
        client_id = await m.message.ask(
            "<i>Envie seu token</i> <b>Clint_id</b>", reply_markup=ForceReply()
        )
        client_secret = await m.message.ask(
            "<i>Envie seu token</i> <b>CLient_secret</b>", reply_markup=ForceReply()
        )

        priv_token = await m.message.ask(
            "<i>Envie seu token</i> <b>Private token</b>", reply_markup=ForceReply()
        )
        pix_key = await m.message.ask(
            "<b>💠 Sua chave pix</b>", reply_markup=ForceReply()
        )

        cur.execute(
            "UPDATE tokens SET client_id = ?, client_secret = ?, bearer_tk = ?, name_cert_key = ? WHERE type_token = ?",
            [
                client_id.text,
                client_secret.text,
                priv_token.text,
                pix_key.text,
                name_pix,
            ],
        )
        save()

    elif name_pix == "pagbank":
        client_id = await m.message.ask(
            "<i>Envie seu token</i> <b>CLIENT_ID</b>", reply_markup=ForceReply()
        )
        client_secret = await m.message.ask(
            "<i>Envie seu token</i> <b>CLIENT_SECRET</b>", reply_markup=ForceReply()
        )

        pix_key = await m.message.ask(
            "<b>💠 Sua chave pix</b>", reply_markup=ForceReply()
        )

        pem_document = await m.message.ask(
            "<b>Envie seu arquivo .pem</b>",
            filters=filters.document,
            reply_markup=ForceReply(),
        )

        pem_file_name = os.path.join("payment_keys", "pagbank.pem")
        await pem_document.download(pem_file_name)

        key_document = await m.message.ask(
            "<b>Envie seu arquivo .key</b>",
            filters=filters.document,
            reply_markup=ForceReply(),
        )

        key_file_name = os.path.join("payment_keys", "pagbank.key")
        await key_document.download(key_file_name)

        cur.execute(
            "UPDATE tokens SET client_id = ?, client_secret = ?, name_cert_pem = ?, name_cert_key = ? WHERE type_token = ?",
            [
                client_id.text,
                client_secret.text,
                pem_file_name,
                key_file_name,
                name_pix,
            ],
        )

        cur.execute("UPDATE bot_config SET random_pix_pb = ?", [pix_key.text])
        save()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="« Voltar", callback_data="painel")]
        ]
    )

    await m.message.reply_text(
        "<b>Tokens atualizados com sucesso.</b>", reply_markup=kb
    )


@Client.on_callback_query(
    filters.regex(r"^select_pix (?P<pix_name>.+)") & filters.user(ADMINS)
)
async def select_pix(c: Client, m: CallbackQuery):
    pix_name = m.matches[0]["pix_name"]

    if pix_name == "off":
        pix_name = None

    cur.execute("UPDATE bot_config SET pay_auto = ?", [pix_name])

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="« Voltar", callback_data="painel")],
        ]
    )

    await m.edit_message_text(
        f"Pix automático alterado com sucesso para {pix_name}.", reply_markup=kb
    )
    save()
