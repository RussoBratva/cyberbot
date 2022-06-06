import asyncio
import shlex
import time

import amanobot.aio
from amanobot.aio.loop import MessageLoop

TOKEN = "2010832443:AAFsjsbJIJtDazA89wnz98jrvP90UCTfMQg"
CHECK_ID = -1001189118018

bot = amanobot.aio.Bot(TOKEN)


# Um dict contendo o nome da screen (str) e o tempo da última resposta (float)
checked_bots = {}


async def main():
    global checked_bots

    while True:
        await bot.sendMessage(CHECK_ID, "!ping")
        await asyncio.sleep(30)
        for checked_bot, checked_time in checked_bots.items():
            # Se a última resposta foi 30s atrás, provavelmente o bot ficou off
            if checked_time + 35 < time.time():
                print(f"{checked_bot} off, reiniciando...")
                # Deixando um tempo no futuro para caso o bot demore reiniciar
                checked_bots[checked_bot] = time.time() + 15
                loop.create_task(restart_bot(checked_bot))


async def restart_bot(bot_screen_name):
    # Enviando ctrl-c e esperando 2s para fechar a db
    proc = await asyncio.create_subprocess_shell(
        shlex.join(["screen", "-S", bot_screen_name, "-X", "stuff", "^C"])
    )
    await proc.communicate()
    await asyncio.sleep(3)

    # Enviando ctrl-\ para caso o bot não tenha sido interrompido
    proc = await asyncio.create_subprocess_shell(
        shlex.join(["screen", "-S", bot_screen_name, "-X", "stuff", "^\\"])
    )
    await proc.communicate()
    await asyncio.sleep(1)

    # Enviando o comando para iniciar o bot novamente
    proc = await asyncio.create_subprocess_shell(
        shlex.join(["screen", "-S", bot_screen_name, "-X", "stuff", "python bot.py^M"])
    )
    await proc.communicate()


async def handle(msg):
    global checked_bots

    flavor = amanobot.flavor(msg)

    summary = amanobot.glance(msg, flavor=flavor)
    if summary[1] != "channel" or not msg["text"].startswith("Pong!"):
        return

    # Retorna beta-bot da mensagem: Pong! 11086.beta-bot
    screen_name = msg["text"].split(" ")[1].split(".")[1]

    checked_bots[screen_name] = time.time()


loop = asyncio.get_event_loop()

loop.create_task(MessageLoop(bot, handle).run_forever())
loop.run_until_complete(main())
