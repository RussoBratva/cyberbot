import os
import subprocess
from getpass import getpass
from glob import glob

import colorama

token = getpass("Insira o seu token do GitHub: ")

print()

bots = glob("clientes/*/*")

bots.sort()

curdir = os.getcwd()

for bot in bots:
    nb = "/".join(
        colorama.Fore.YELLOW + i + colorama.Fore.RESET for i in bot.split("/")
    )

    print(f"Atualizando source de {nb}:")

    os.chdir(curdir + "/" + bot)

    print(" Fazendo backup da source atual...")
    ret = subprocess.run(["git", "stash"], capture_output=True)
    if ret.returncode != 0:
        pad = "\n   ".join(ret.stderr.decode().splitlines())
        pad += "\n   ".join(ret.stdout.decode().splitlines())
        print(
            f"{colorama.Fore.RED}  Ocorreu um erro ao executar o comando de backup e a pasta foi ignorada{colorama.Fore.RESET}:\n   {pad}\n"
        )
        continue

    print(" Atualizando a source...")

    ret2 = subprocess.run(
        ["git", "pull", f"https://git:{token}@github.com/alissonlauffer/cyberspacebot"],
        capture_output=True,
    )
    if ret2.returncode != 0:
        pad = "\n   ".join(ret2.stderr.decode().splitlines())
        print(
            f"{colorama.Fore.RED}  Ocorreu um erro ao fazer pull da source (token de acesso incorreto?){colorama.Fore.RESET}:\n   {pad}\n"
        )

    print(" Restaurando o backup sobre a nova source...")

    ret3 = subprocess.run(["git", "stash", "pop"], capture_output=True)
    if ret3.returncode != 0 and "No stash entries found." not in ret3.stderr.decode():
        pad = "\n   ".join(ret3.stderr.decode().splitlines())
        print(
            f"{colorama.Fore.RED}  Ocorreu um erro ao restaurar o backup (provavelmente um conflito?){colorama.Fore.RESET}:\n   {pad}\nLevando para o shell na pasta para resolução manual:"
        )
        os.system("bash")

    print(f" {colorama.Fore.GREEN}Source atualizada com sucesso.{colorama.Fore.RESET}")

    print()
