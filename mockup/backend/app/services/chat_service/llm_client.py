"""Cliente LLM compatible con OpenAI Chat Completions.

Diseñado para hablar con servidores locales (vLLM, llama-cpp-python en modo
`--server`, LM Studio, text-generation-webui, etc.) que exponen el endpoint
`/v1/chat/completions`. El cliente no añade dependencias nuevas: usa
`requests` (ya en `requirements.txt`).

Si `LLM_ENABLED=false`, las llamadas devuelven inmediatamente un resultado
con `enabled=False`, dejando que la plataforma siga funcionando sin LLM.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterator

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    enabled: bool
    text: str
    error: str | None = None
    model: str | None = None
    duration_sec: float | None = None


def is_enabled() -> bool:
    return bool(settings.llm_enabled)


def health_check() -> dict:
    """Pequeño ping al endpoint del LLM. No falla si no responde.

    Devuelve un dict listo para serializar al frontend con el estado del
    chatbot. Útil para que la UI muestre "Chatbot no disponible" sin
    intentar enviar mensajes inútilmente.
    """
    if not is_enabled():
        return {
            "enabled": False,
            "available": False,
            "model": settings.llm_model,
            "base_url": settings.llm_base_url,
            "reason": "LLM_ENABLED=false",
        }

    try:
        url = settings.llm_base_url.rstrip("/") + "/models"
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            timeout=5,
        )
        response.raise_for_status()
        return {
            "enabled": True,
            "available": True,
            "model": settings.llm_model,
            "base_url": settings.llm_base_url,
            "reason": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "available": False,
            "model": settings.llm_model,
            "base_url": settings.llm_base_url,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _payload(messages: list[ChatMessage], stream: bool, max_tokens: int | None) -> dict:
    return {
        "model": settings.llm_model,
        "messages": [m.to_dict() for m in messages],
        "temperature": float(settings.chat_temperature),
        "max_tokens": int(max_tokens or settings.llm_max_tokens),
        "stream": stream,
    }


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }


def chat_completion(messages: list[ChatMessage], max_tokens: int | None = None) -> LLMResponse:
    """Llamada bloqueante a `/v1/chat/completions`.

    Si el LLM está deshabilitado o falla la red, devuelve un `LLMResponse`
    con `enabled=False` o `error` rellenado para que la capa de servicio
    pueda decidir un fallback elegante.
    """
    if not is_enabled():
        return LLMResponse(enabled=False, text="", error=None, model=settings.llm_model)

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    import time

    started = time.perf_counter()
    try:
        response = requests.post(
            url,
            json=_payload(messages, stream=False, max_tokens=max_tokens),
            headers=_headers(),
            timeout=settings.llm_request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        text = ""
        if isinstance(data, dict):
            choices = data.get("choices") or []
            if choices:
                text = (choices[0].get("message") or {}).get("content", "") or ""
        duration = round(time.perf_counter() - started, 3)
        return LLMResponse(
            enabled=True,
            text=text.strip(),
            error=None,
            model=settings.llm_model,
            duration_sec=duration,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM chat_completion falló: %s", exc)
        return LLMResponse(
            enabled=True,
            text="",
            error=f"{type(exc).__name__}: {exc}",
            model=settings.llm_model,
            duration_sec=round(time.perf_counter() - started, 3),
        )


def chat_completion_stream(
    messages: list[ChatMessage],
    max_tokens: int | None = None,
) -> Iterator[str]:
    """Generador de tokens en streaming SSE compatible OpenAI.

    Cada item es el `delta.content` parcial. Si el LLM no está habilitado o
    no responde, el generador termina sin emitir tokens (el caller debe
    detectar el caso revisando primero `is_enabled()` o `health_check()`).
    """
    if not is_enabled():
        return

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    try:
        with requests.post(
            url,
            json=_payload(messages, stream=True, max_tokens=max_tokens),
            headers=_headers(),
            timeout=settings.llm_request_timeout,
            stream=True,
        ) as response:
            response.raise_for_status()
            # Forzamos UTF-8: si el servidor (p. ej. Ollama) no anuncia
            # `charset=utf-8` en el Content-Type, `requests` cae al
            # default Latin-1 (RFC 2616) y rompe los acentos.
            for raw_line in response.iter_lines(decode_unicode=False):
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:"):].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                token = delta.get("content")
                if token:
                    yield token
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM chat_completion_stream falló: %s", exc)
        return
