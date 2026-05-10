from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.schemas.chat import ChatHealth, ChatRequest, ChatResponse
from app.services.chat_service import llm_client, service as chat_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=ChatHealth)
def chat_health() -> ChatHealth:
    return ChatHealth(**llm_client.health_check())


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    answer = chat_service.answer(
        db,
        question=req.question,
        paper_id=req.paper_id,
        job_id=req.job_id,
        include_analytics=req.include_analytics,
    )
    return ChatResponse(
        enabled=answer.enabled,
        available=answer.available,
        text=answer.text,
        error=answer.error,
        model=answer.model,
        duration_sec=answer.duration_sec,
        context=answer.context_summary,
    )


@router.post("/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Streaming SSE de la respuesta.

    No usa `Depends(get_db)` porque el generador puede sobrevivir al
    request handler si el cliente desconecta — abrimos una sesión propia
    y la cerramos en el `finally`.
    """

    def event_stream():
        db = SessionLocal()
        try:
            for event in chat_service.answer_stream(
                db,
                question=req.question,
                paper_id=req.paper_id,
                job_id=req.job_id,
                include_analytics=req.include_analytics,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.warning("chat_stream interrumpido: %s", exc)
            payload = {
                "type": "error",
                "enabled": True,
                "message": f"{type(exc).__name__}: {exc}",
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            db.close()
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
