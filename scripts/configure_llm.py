"""Configura a chave local sem exibi-la no terminal ou gravá-la no histórico."""

import getpass
import sys

from app.ingestion import ROOT
from app.llm import DEFAULT_MODEL, LLMError, read_settings


def main():
    if not sys.stdin.isatty():
        print("Execute este comando em um terminal interativo para ocultar a chave.")
        return 1
    destination = ROOT / ".env"
    if destination.exists():
        print("O arquivo .env já existe. Edite-o localmente para preservar a configuração atual.")
        return 1
    try:
        key = getpass.getpass("Cole a chave da Groq (não será exibida): ").strip()
        if not key or not key.isascii() or any(character.isspace() for character in key):
            print("Chave vazia ou com caracteres inválidos. Nenhum arquivo foi criado.")
            return 1
        with destination.open("x", encoding="utf-8") as output:
            output.write(f"TAXMIND_LLM_PROVIDER=groq\nTAXMIND_LLM_MODEL={DEFAULT_MODEL}\nGROQ_API_KEY={key}\n")
        read_settings(destination)
    except (EOFError, KeyboardInterrupt):
        print("\nConfiguração cancelada.")
        return 1
    except (OSError, LLMError):
        print("Não foi possível concluir a configuração. Confira o arquivo .env localmente.")
        return 1
    print("Configuração salva em .env. A conexão ainda precisa ser testada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
