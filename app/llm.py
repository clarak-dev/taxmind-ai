"""Cliente de geração estruturada; credenciais permanecem no servidor."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import BaseModel

from app.ingestion import ROOT

DEFAULT_MODEL = "qwen/qwen3.8-27b"
ENV_KEYS = {"TAXMIND_LLM_PROVIDER", "TAXMIND_LLM_MODEL", "GROQ_API_KEY"}


class LLMError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    api_key: str = field(repr=False)


def read_settings(path: Path = ROOT / ".env") -> LLMSettings:
    values = {}
    try:
        lines = path.read_text("utf-8-sig").splitlines() if path.exists() else []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            key = key.strip()
            if key not in ENV_KEYS:
                continue
            if not separator or key in values:
                raise ValueError("Entrada inválida")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key] = value
    except (OSError, ValueError) as exc:
        raise LLMError("Configuração do LLM inválida. Confira o arquivo .env.", 503) from exc
    values.update({key: os.environ[key] for key in ENV_KEYS if key in os.environ})
    provider = values.get("TAXMIND_LLM_PROVIDER", "groq").strip()
    model = values.get("TAXMIND_LLM_MODEL", DEFAULT_MODEL).strip()
    key = values.get("GROQ_API_KEY", "").strip()
    if provider != "groq" or not model or len(model) > 150:
        raise LLMError("Provedor ou modelo do LLM inválido.", 503)
    if not key or any(character.isspace() for character in key) or not key.isascii():
        raise LLMError("LLM não configurado. Configure GROQ_API_KEY no servidor.", 503)
    return LLMSettings(provider=provider, model=model, api_key=key)


class StructuredLLM(Protocol):
    provider: str
    model: str

    def complete(self, system: str, payload: dict, schema: type[BaseModel]) -> BaseModel: ...


class GroqLLM:
    provider = "groq"

    def __init__(self, settings: LLMSettings, transport=None):
        self.model = settings.model
        self._api_key = settings.api_key
        self._transport = transport

    def complete(self, system: str, payload: dict, schema: type[BaseModel]) -> BaseModel:
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0,
            "max_completion_tokens": 1800,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": schema.__name__, "strict": True, "schema": schema.model_json_schema(),
            }},
        }
        try:
            with httpx.Client(timeout=httpx.Timeout(45, connect=10), transport=self._transport,
                              follow_redirects=False) as client:
                response = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"}, json=request,
                )
            if response.status_code == 429:
                raise LLMError("Limite do serviço de IA atingido. Tente novamente mais tarde.", 429)
            if response.status_code in {401, 403}:
                raise LLMError("A credencial do serviço de IA foi recusada. Confira a configuração.", 503)
            if response.status_code != 200:
                raise LLMError("O serviço de IA não conseguiu concluir a solicitação.")
            body = response.json()
            choice = body["choices"][0]
            if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
                raise LLMError("O serviço de IA não retornou uma resposta estruturada completa.")
            return schema.model_validate_json(choice["message"]["content"], strict=True)
        except httpx.TimeoutException as exc:
            raise LLMError("O serviço de IA excedeu o tempo de resposta.", 504) from exc
        except httpx.HTTPError as exc:
            raise LLMError("Não foi possível conectar ao serviço de IA.", 503) from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("O serviço de IA retornou uma resposta em formato inválido.") from exc
