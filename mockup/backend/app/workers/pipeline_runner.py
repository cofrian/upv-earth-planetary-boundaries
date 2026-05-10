from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.job_repository import JobRepository
from app.services.abstract_extraction.service import detect_abstract
from app.services.embedding_service.service import embed_texts, get_active_model_info
from app.services.metadata_extraction.service import infer_year
from app.services.pb_inference.llm_service import run_llm_pb_assessment
from app.services.pb_inference.service import infer_pb_scores
from app.services.pdf_ingestion.service import extract_text_from_pdf
from app.services.similarity_search.service import find_similar_for_text
from app.services.summarization.service import summarize_abstract
from app.services.system_metrics import collect_system_metrics
from app.services.text_cleaning.service import clean_abstract, normalize_text


def run_pdf_pipeline(db: Session, job_id: uuid.UUID, pdf_path: str) -> None:
    jobs = JobRepository(db)
    job = jobs.get_job(job_id)
    if not job:
        return

    try:
        jobs.add_event(job.id, "runtime_metrics", {"stage": "start", **collect_system_metrics()})

        jobs.update_job(job, status="parsing", stage="parse_pdf", progress_pct=10)
        full_text = extract_text_from_pdf(pdf_path)
        jobs.add_event(job.id, "parse_pdf", {"chars": len(full_text), **collect_system_metrics()})

        jobs.update_job(job, status="parsing", stage="extract_abstract", progress_pct=25)
        abstract_raw = detect_abstract(full_text)
        jobs.add_event(job.id, "extract_abstract", {"chars": len(abstract_raw), **collect_system_metrics()})

        jobs.update_job(job, status="parsing", stage="clean_text", progress_pct=35)
        abstract_norm = normalize_text(abstract_raw)
        clean = clean_abstract(abstract_norm)
        abstract_char_len = len(abstract_norm)
        is_valid = abstract_char_len > 500
        jobs.add_event(job.id, "clean_text", {
            "abstract_norm_chars": abstract_char_len,
            "clean_chars": len(clean),
            "passes_threshold": is_valid,
            **collect_system_metrics(),
        })

        jobs.update_job(job, status="inferencing", stage="validate_abstract", progress_pct=42)
        jobs.add_event(job.id, "validate_abstract", {
            "abstract_detected": abstract_char_len > 0,
            "abstract_char_len": abstract_char_len,
            "threshold": 500,
            "passes_threshold": is_valid,
            "is_valid_for_embedding": is_valid,
        })

        jobs.update_job(job, status="inferencing", stage="generate_embedding", progress_pct=55)
        embedding_text = f"{job.filename_original or ''} {abstract_norm}".strip()
        try:
            vectors = embed_texts([embedding_text]) if embedding_text else None
            embedding_dim = int(vectors.shape[1]) if vectors is not None and vectors.size else 0
        except Exception as exc:  # noqa: BLE001
            embedding_dim = 0
            jobs.add_event(job.id, "embedding_warning", {"error": str(exc)})

        active = get_active_model_info()
        jobs.add_event(job.id, "generate_embedding", {
            "model_id": active.model_id,
            "embedding_dim": embedding_dim,
            "is_specter": active.is_specter,
            "fallback_used": active.fallback_used,
            "embedding_text_rule": "title + clean_abstract_semantic",
            "valid": is_valid,
        })

        jobs.update_job(job, status="inferencing", stage="similarity_search", progress_pct=65)
        similar_papers: list[dict] = []
        if is_valid:
            try:
                similar_papers = find_similar_for_text(embedding_text, top_k=8)
            except Exception as exc:  # noqa: BLE001
                jobs.add_event(job.id, "similarity_warning", {"error": str(exc)})
        jobs.add_event(job.id, "similarity_search", {
            "results": len(similar_papers),
            "skipped": not is_valid,
        })

        jobs.update_job(job, status="inferencing", stage="pb_scoring", progress_pct=78)
        pb = infer_pb_scores(clean)
        jobs.add_event(job.id, "pb_scoring", {"top_pb_code": pb.get("top_pb_code"), **collect_system_metrics()})

        jobs.update_job(job, status="inferencing", stage="llm_reasoning", progress_pct=85)
        llm_result = run_llm_pb_assessment(clean)
        jobs.add_event(
            job.id,
            "llm_reasoning",
            {
                "enabled": llm_result.get("enabled", False),
                "assigned_count": len(llm_result.get("assigned_pbs", [])),
                "assigned_pb_codes": llm_result.get("assigned_pb_codes", []),
                "duration_sec": llm_result.get("duration_sec", 0.0),
                "ollama_model": settings.ollama_model_name,
                **collect_system_metrics(),
            },
        )

        jobs.update_job(job, status="summarizing", stage="summarize", progress_pct=92)
        summary = summarize_abstract(clean)
        jobs.add_event(job.id, "summarize", {"summary_chars": len(summary), **collect_system_metrics()})

        paper = jobs.create_paper(
            doc_id=f"upload-{job.id}",
            title=job.filename_original,
            abstract_raw=abstract_raw,
            abstract_norm=abstract_norm,
            clean_abstract=clean,
            year=infer_year(full_text),
            doi=None,
            source="uploaded_pdf",
            authors=None,
            keywords=None,
            journal=None,
            language="en",
            pdf_path=pdf_path,
        )
        jobs.attach_paper_to_job(job, paper.id)

        jobs.create_pb_result(
            paper_id=paper.id,
            model_version=f"{active.model_id}@v1",
            top_pb_code=pb["top_pb_code"],
            top_pb_score=pb["top_pb_score"],
            secondary_pbs=pb["secondary_pbs"],
            score_map=pb["score_map"],
            threshold_used=0.3,
            explanation_text=(
                f"{pb['explanation_text']} "
                f"Resumen: {summary} "
                f"LLM reasoning: {llm_result.get('reasoning_process', '')} "
                f"LLM assigned_pb_codes: {llm_result.get('assigned_pb_codes', [])} "
                f"LLM assigned_pbs: {llm_result.get('assigned_pbs', [])}"
            ),
        )

        jobs.add_event(job.id, "similar_papers_snapshot", {"items": similar_papers})

        jobs.update_job(job, status="completed", stage="persist", progress_pct=100)
        jobs.add_event(job.id, "persist", {"status": "completed", **collect_system_metrics()})
    except Exception as exc:
        jobs.add_event(job.id, "pipeline_error", {"error": str(exc), **collect_system_metrics()})
        jobs.update_job(
            job,
            status="failed",
            stage="error",
            progress_pct=100,
            error_code="PIPELINE_ERROR",
            error_message=str(exc),
        )
