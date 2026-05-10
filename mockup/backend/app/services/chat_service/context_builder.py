"""Construye el "context pack" que se inyecta al LLM en cada turno.

El context pack es un dict serializable con todo lo que el LLM puede usar
como verdad: AED, paper subido (si aplica), PBs relevantes, similares y
snippets metodológicos. Este módulo NO llama al LLM ni recalcula nada;
solo orquesta los retrievers.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.chat_service.retrievers import (
    analytics_retriever,
    methodology_retriever,
    paper_retriever,
    pb_retriever,
)


def _truncate(text: str, max_chars: int) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def build_context_pack(
    db: Session,
    question: str,
    paper_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    include_analytics: bool = True,
    similar_top_k: int = 5,
) -> dict[str, Any]:
    """Recolecta todo el contexto disponible para responder la pregunta."""
    pack: dict[str, Any] = {"question": question}

    if include_analytics:
        pack["analytics"] = analytics_retriever.fetch_corpus_snapshot(db)

    paper_ctx: dict[str, Any] | None = None
    if paper_id is not None:
        paper_ctx = paper_retriever.fetch_paper_context(db, paper_id, similar_top_k=similar_top_k)
    elif job_id is not None:
        paper_ctx = paper_retriever.fetch_paper_context_by_job(db, job_id, similar_top_k=similar_top_k)

    if paper_ctx:
        pack["paper"] = paper_ctx["paper"]
        pack["pb_result"] = paper_ctx["pb"]
        pack["similar_papers"] = paper_ctx["similar"]

    relevant_pb_codes: list[str] = []
    pb_block = pack.get("pb_result")
    if pb_block:
        if pb_block.get("top_pb_code"):
            relevant_pb_codes.append(pb_block["top_pb_code"])
        secondary = pb_block.get("secondary_pbs") or []
        if isinstance(secondary, list):
            for item in secondary:
                if isinstance(item, dict) and item.get("pb_code"):
                    relevant_pb_codes.append(item["pb_code"])

    if not relevant_pb_codes and include_analytics:
        for item in (pack.get("analytics") or {}).get("pb_distribution", [])[:3]:
            label = item.get("label") if isinstance(item, dict) else None
            if label:
                relevant_pb_codes.append(label)

    if relevant_pb_codes:
        pack["pb_catalog"] = pb_retriever.fetch_pb_context_for(relevant_pb_codes)

    pack["methodology"] = methodology_retriever.fetch_relevant(question)
    return pack


def render_context_block(pack: dict[str, Any], max_chars: int = 6000) -> str:
    """Serializa el pack a un bloque markdown-ish compacto para el prompt.

    Optimizado para que un LLM 7B-14B con ventana de 4-8k pueda leerlo sin
    perderse. Todo numérico va con su unidad y se evita JSON anidado para
    no malgastar tokens.
    """
    lines: list[str] = []

    analytics = pack.get("analytics")
    if analytics:
        kpis = analytics.get("kpis", {})
        lines.append("## CORPUS UPV (AED)")
        lines.append(
            "- Papers bruto: {raw} · con abstract: {abs} · válidos: {valid} · "
            "aptos para embeddings (>500 car.): {emb} · indexados: {idx}".format(
                raw=kpis.get("total_raw"),
                abs=kpis.get("with_abstract"),
                valid=kpis.get("valid"),
                emb=kpis.get("for_embeddings"),
                idx=kpis.get("indexed"),
            )
        )
        if kpis.get("avg_abstract_length") is not None:
            lines.append(
                "- Longitud media abstract: {avg} caracteres (mediana {med}).".format(
                    avg=kpis.get("avg_abstract_length"),
                    med=kpis.get("median_abstract_length"),
                )
            )
        if kpis.get("min_year") and kpis.get("max_year"):
            lines.append(f"- Rango temporal: {kpis['min_year']}–{kpis['max_year']}.")
        lines.append(f"- Filtro de calidad: {kpis.get('filter_rule')}.")
        lines.append(f"- Texto que se embebe: {kpis.get('embedding_text_rule')}.")

        idx = analytics.get("index", {})
        if idx:
            lines.append(
                "- Índice de similitud: modelo {model} ({dim} dim), {n} vectores · SPECTER2={specter} · "
                "fuente={source}.".format(
                    model=idx.get("model_id"),
                    dim=idx.get("embedding_dim"),
                    n=idx.get("vectors"),
                    specter=idx.get("is_specter"),
                    source=idx.get("source"),
                )
            )

        pb_dist = analytics.get("pb_distribution") or []
        if pb_dist:
            top = ", ".join(
                f"{item.get('label')}={item.get('value')}" for item in pb_dist[:8]
            )
            lines.append(f"- Distribución por PB (top 8): {top}.")

        years = analytics.get("year_distribution") or []
        if years:
            head = ", ".join(f"{item.get('label')}={item.get('value')}" for item in years[-8:])
            lines.append(f"- Últimos años con datos: {head}.")
        lines.append("")

    paper = pack.get("paper")
    if paper:
        lines.append("## PAPER ANALIZADO")
        lines.append(f"- Título: {paper.get('title') or 'Sin título'}")
        if paper.get("year"):
            lines.append(f"- Año: {paper['year']}")
        if paper.get("journal"):
            lines.append(f"- Journal: {paper['journal']}")
        if paper.get("doi"):
            lines.append(f"- DOI: {paper['doi']}")
        if paper.get("keywords"):
            lines.append(f"- Keywords del autor: {paper['keywords']}")
        lines.append(
            "- Longitud del abstract: {n} caracteres · válido para embeddings: {ok}".format(
                n=paper.get("abstract_char_len"), ok=paper.get("is_valid_for_embedding")
            )
        )
        if paper.get("abstract_preview"):
            lines.append(f"- Abstract: {paper['abstract_preview']}")
        lines.append("")

    pb = pack.get("pb_result")
    if pb:
        lines.append("## RESULTADO PB (calculado por embeddings + catálogo PB, no por el LLM)")
        if pb.get("top_pb_code"):
            score = pb.get("top_pb_score")
            score_txt = f"{score:.3f}" if isinstance(score, (int, float)) else str(score)
            lines.append(f"- PB principal: {pb['top_pb_code']} (score {score_txt})")
        secondary = pb.get("secondary_pbs") or []
        if isinstance(secondary, list) and secondary:
            entries = []
            for item in secondary[:5]:
                if isinstance(item, dict):
                    code = item.get("pb_code")
                    sc = item.get("score")
                    sc_txt = f"{sc:.3f}" if isinstance(sc, (int, float)) else str(sc)
                    entries.append(f"{code}={sc_txt}")
            if entries:
                lines.append("- PBs secundarios: " + ", ".join(entries))
        if pb.get("explanation"):
            lines.append(f"- Explicación previamente generada: {_truncate(pb['explanation'], 600)}")
        lines.append("")

    catalog = pack.get("pb_catalog") or []
    if catalog:
        lines.append("## FICHAS DE PLANETARY BOUNDARIES RELEVANTES")
        for entry in catalog:
            lines.append(
                f"- {entry.get('pb_code')} {entry.get('pb_name')}: "
                f"{_truncate(entry.get('short_definition', ''), 280)}"
            )
        lines.append("")

    similar = pack.get("similar_papers") or []
    if similar:
        lines.append("## PAPERS SIMILARES (por embeddings, calculado en similarity_search)")
        for idx_, item in enumerate(similar, start=1):
            score = item.get("score")
            score_txt = f"{score:.3f}" if isinstance(score, (int, float)) else str(score)
            year = item.get("year") or "s/f"
            pb_code = item.get("pb_code") or "PB?"
            lines.append(
                f"{idx_}. ({score_txt}) [{pb_code}] {item.get('title')} ({year})"
            )
            preview = item.get("abstract_preview")
            if preview:
                lines.append(f"   resumen: {_truncate(preview, 240)}")
        lines.append("")

    methodology = pack.get("methodology") or []
    if methodology:
        lines.append("## SNIPPETS METODOLÓGICOS")
        for snippet in methodology:
            lines.append(f"- ({snippet.get('topic')}) {snippet.get('answer')}")
        lines.append("")

    block = "\n".join(lines).strip()

    if len(block) > max_chars:
        # Si nos pasamos, devolvemos un JSON crudo recortado como fallback.
        block = block[:max_chars].rstrip() + "\n…(contexto truncado)"
    return block or "(sin contexto disponible)"


def serialize_pack(pack: dict[str, Any]) -> str:
    """Versión JSON compacta para debug del context pack (no para el LLM)."""
    return json.dumps(pack, ensure_ascii=False, default=str, indent=2)
