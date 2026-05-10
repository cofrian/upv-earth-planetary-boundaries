"""Orquestador del chatbot RAG UPV-EARTH.

Une retrievers + context_builder + llm_client. El servicio expone dos
modos:

- `answer`: bloqueante, devuelve el texto completo + metadatos.
- `answer_stream`: generador SSE-compatible para el endpoint de streaming.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.services.chat_service import context_builder, llm_client, prompt_templates

logger = logging.getLogger(__name__)


@dataclass
class ChatAnswer:
    enabled: bool
    available: bool
    text: str
    error: str | None
    model: str | None
    duration_sec: float | None
    context_summary: dict[str, Any]


def _summarize_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """Mini-resumen del pack para devolver al frontend (transparencia)."""
    summary: dict[str, Any] = {
        "has_paper": bool(pack.get("paper")),
        "has_pb_result": bool(pack.get("pb_result")),
        "similar_count": len(pack.get("similar_papers") or []),
        "pb_catalog_count": len(pack.get("pb_catalog") or []),
        "methodology_count": len(pack.get("methodology") or []),
        "has_analytics": bool(pack.get("analytics")),
    }
    paper = pack.get("paper")
    if paper:
        summary["paper_title"] = paper.get("title")
    return summary


def _build_messages(question: str, pack: dict[str, Any]) -> list[llm_client.ChatMessage]:
    context_block = context_builder.render_context_block(pack)
    return [
        llm_client.ChatMessage(role="system", content=prompt_templates.SYSTEM_PROMPT),
        llm_client.ChatMessage(
            role="user",
            content=prompt_templates.render_user_prompt(question, context_block),
        ),
    ]


def answer(
    db: Session,
    question: str,
    paper_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    include_analytics: bool = True,
) -> ChatAnswer:
    pack = context_builder.build_context_pack(
        db,
        question=question,
        paper_id=paper_id,
        job_id=job_id,
        include_analytics=include_analytics,
    )
    summary = _summarize_pack(pack)

    if not llm_client.is_enabled():
        return ChatAnswer(
            enabled=False,
            available=False,
            text=prompt_templates.fallback_no_llm_message(),
            error=None,
            model=None,
            duration_sec=None,
            context_summary=summary,
        )

    messages = _build_messages(question, pack)
    response = llm_client.chat_completion(messages)

    if response.error or not response.text:
        return ChatAnswer(
            enabled=True,
            available=False,
            text=response.text or prompt_templates.fallback_no_llm_message(),
            error=response.error,
            model=response.model,
            duration_sec=response.duration_sec,
            context_summary=summary,
        )

    return ChatAnswer(
        enabled=True,
        available=True,
        text=response.text,
        error=None,
        model=response.model,
        duration_sec=response.duration_sec,
        context_summary=summary,
    )


def answer_stream(
    db: Session,
    question: str,
    paper_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    include_analytics: bool = True,
) -> Iterator[dict[str, Any]]:
    """Generador de eventos para SSE.

    Cada evento es un dict con:
      - {"type": "meta", ...}   -> resumen del pack
      - {"type": "token", ...}  -> token parcial
      - {"type": "done", ...}   -> cierre con duration_sec
      - {"type": "error", ...}  -> error o LLM no disponible
    """
    pack = context_builder.build_context_pack(
        db,
        question=question,
        paper_id=paper_id,
        job_id=job_id,
        include_analytics=include_analytics,
    )
    summary = _summarize_pack(pack)
    yield {"type": "meta", "context": summary}

    if not llm_client.is_enabled():
        yield {
            "type": "error",
            "enabled": False,
            "message": prompt_templates.fallback_no_llm_message(),
        }
        return

    messages = _build_messages(question, pack)
    started = time.perf_counter()
    emitted_any = False
    try:
        for token in llm_client.chat_completion_stream(messages):
            emitted_any = True
            yield {"type": "token", "content": token}
    except Exception as exc:  # noqa: BLE001
        logger.warning("answer_stream falló: %s", exc)
        yield {
            "type": "error",
            "enabled": True,
            "message": f"{type(exc).__name__}: {exc}",
        }
        return

    if not emitted_any:
        # vLLM/llama-cpp no emitió nada (servidor caído o no contestó):
        # caemos al modo bloqueante para garantizar respuesta.
        response = llm_client.chat_completion(messages)
        if response.text:
            yield {"type": "token", "content": response.text}
        else:
            yield {
                "type": "error",
                "enabled": True,
                "message": response.error or prompt_templates.fallback_no_llm_message(),
            }
            return

    duration = round(time.perf_counter() - started, 3)
    yield {"type": "done", "duration_sec": duration}
