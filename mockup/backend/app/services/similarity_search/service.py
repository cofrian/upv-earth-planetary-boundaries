"""Búsqueda de papers similares por contenido sobre el corpus UPV.

Construye un índice en memoria (numpy) con los embeddings de
`title + clean_abstract_semantic` para todas las filas con
`abstract_char_len > 500`.

Usa el mismo modelo que el `embedding_service`: por defecto SPECTER2
(`allenai/specter2_base`) cuando está disponible, con fallback a un
modelo sentence-transformers configurable. La firma del modelo se
expone para que la UI lo pueda mostrar al usuario.

El índice se construye perezosamente la primera vez que se consulta y
se invalida si el corpus cambia.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass

import numpy as np

from app.services.corpus_loader.precomputed import file_path
from app.services.corpus_loader.service import get_corpus_layers
from app.services.embedding_service.service import embed_texts, get_active_model_info

logger = logging.getLogger(__name__)


@dataclass
class CorpusIndex:
    matrix: np.ndarray
    doc_ids: list[str]
    titles: list[str]
    years: list[int | None]
    journals: list[str]
    dois: list[str]
    abstracts: list[str]
    keywords: list[str]
    pb_codes: list[str]
    model_id: str
    embedding_dim: int
    source: str = "computed"


_lock = threading.Lock()
_index: CorpusIndex | None = None


def _load_precomputed() -> CorpusIndex | None:
    npy_path = file_path("embeddings.npy")
    meta_path = file_path("embeddings_meta.json")
    if not npy_path or not meta_path:
        return None
    try:
        matrix = np.load(npy_path).astype(np.float32, copy=False)
        with meta_path.open("r", encoding="utf-8") as fh:
            meta = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo cargar índice precomputado: %s", exc)
        return None

    if matrix.shape[0] != len(meta.get("doc_ids", [])):
        logger.warning("Tamaño inconsistente entre embeddings.npy y embeddings_meta.json")
        return None

    logger.info(
        "Índice de similitud cargado desde precompute: %s vectores · dim %s · modelo %s",
        matrix.shape[0],
        matrix.shape[1],
        meta.get("model_id"),
    )

    return CorpusIndex(
        matrix=matrix,
        doc_ids=list(map(str, meta.get("doc_ids", []))),
        titles=list(map(str, meta.get("titles", []))),
        years=list(meta.get("years", [None] * matrix.shape[0])),
        journals=list(map(str, meta.get("journals", []))),
        dois=list(map(str, meta.get("dois", []))),
        abstracts=list(map(str, meta.get("abstracts", []))),
        keywords=list(map(str, meta.get("keywords", []))),
        pb_codes=list(map(str, meta.get("pb_codes", []))),
        model_id=str(meta.get("model_id", "unknown")),
        embedding_dim=int(meta.get("embedding_dim", matrix.shape[1])),
        source="precomputed",
    )


def _build_index() -> CorpusIndex:
    precomputed = _load_precomputed()
    if precomputed is not None:
        return precomputed

    layer = get_corpus_layers()["for_embeddings"]
    if layer.empty:
        info = get_active_model_info()
        return CorpusIndex(
            matrix=np.zeros((0, info.dimension or 768), dtype=np.float32),
            doc_ids=[],
            titles=[],
            years=[],
            journals=[],
            dois=[],
            abstracts=[],
            keywords=[],
            pb_codes=[],
            model_id=info.model_id,
            embedding_dim=info.dimension or 0,
        )

    texts = layer["embedding_text"].astype(str).tolist()
    matrix = embed_texts(texts)
    matrix = matrix.astype(np.float32, copy=False)

    pb_codes_col = "pb_folder" if "pb_folder" in layer.columns else None

    def _safe_year(value: object) -> int | None:
        try:
            if value is None:
                return None
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        import math
        if math.isnan(number):
            return None
        if 1900 <= number <= 2100:
            return int(number)
        return None

    doc_ids = layer["doc_id"].astype(str).tolist()
    titles = layer["title"].astype(str).tolist()
    if "year_int" in layer.columns:
        years = [_safe_year(v) for v in layer["year_int"].tolist()]
    else:
        years = [None] * len(layer)
    journals = layer["journal"].astype(str).tolist()
    dois = layer["doi"].astype(str).tolist()
    abstracts = layer["abstract_norm"].astype(str).tolist()
    keywords = layer["keywords"].astype(str).tolist() if "keywords" in layer.columns else [""] * len(layer)
    pbs = layer[pb_codes_col].astype(str).tolist() if pb_codes_col else [""] * len(layer)

    info = get_active_model_info()
    dim = matrix.shape[1] if matrix.size else (info.dimension or 0)

    return CorpusIndex(
        matrix=matrix,
        doc_ids=doc_ids,
        titles=titles,
        years=years,
        journals=journals,
        dois=dois,
        abstracts=abstracts,
        keywords=keywords,
        pb_codes=pbs,
        model_id=info.model_id,
        embedding_dim=int(dim),
    )


def get_index() -> CorpusIndex:
    global _index
    with _lock:
        if _index is None:
            logger.info("Inicializando índice de similitud...")
            _index = _build_index()
            logger.info(
                "Índice listo (%s): %s vectores · dim %s",
                _index.source,
                len(_index.doc_ids),
                _index.embedding_dim,
            )
        return _index


def reset_index() -> None:
    global _index
    with _lock:
        _index = None


def index_status(build_if_missing: bool = False) -> dict:
    """Devuelve estado del índice. Por defecto NO lo construye.

    El AED del frontend debe ver el estado teórico (papers candidatos,
    modelo activo) sin pagar el coste de generar embeddings hasta que
    el usuario solicita una búsqueda real.
    """
    info = get_active_model_info()
    layer = get_corpus_layers()["for_embeddings"]
    candidates = int(len(layer))

    has_precomputed = file_path("embeddings.npy") is not None and file_path("embeddings_meta.json") is not None
    if build_if_missing or _index is not None:
        idx = get_index()
        vectors = len(idx.doc_ids)
        dim = idx.embedding_dim
        model_id = idx.model_id
        source = idx.source
    else:
        vectors = 0
        dim = info.dimension or 0
        model_id = info.model_id
        source = "precomputed" if has_precomputed else "computed"

    return {
        "model_id": model_id,
        "embedding_dim": int(dim or 0),
        "vectors": vectors,
        "candidates": candidates,
        "indexed_total": candidates,
        "is_built": _index is not None,
        "is_precomputed": has_precomputed,
        "source": source,
        "embedding_text_rule": "title + clean_abstract_semantic",
        "filter_rule": "abstract_char_len > 500",
        "is_specter": info.is_specter,
        "fallback_used": info.fallback_used,
    }


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return matrix / norms


def _abstract_preview(text: str, max_chars: int = 320) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def find_similar_for_text(text: str, top_k: int = 8, exclude_doc_ids: set[str] | None = None) -> list[dict]:
    """Devuelve los top_k papers más similares al texto dado."""
    idx = get_index()
    if idx.matrix.shape[0] == 0:
        return []

    query_vec = embed_texts([text])
    if query_vec.size == 0:
        return []

    query_vec = _normalize(query_vec.astype(np.float32))
    matrix = _normalize(idx.matrix)

    sims = (matrix @ query_vec.T).flatten()
    order = np.argsort(-sims)
    excluded = exclude_doc_ids or set()

    results: list[dict] = []
    for rank in order:
        if len(results) >= top_k:
            break
        doc_id = idx.doc_ids[rank]
        if doc_id in excluded:
            continue
        score = float(sims[rank])
        if not np.isfinite(score):
            continue
        results.append({
            "doc_id": doc_id,
            "title": idx.titles[rank],
            "year": idx.years[rank],
            "journal": idx.journals[rank] or None,
            "doi": idx.dois[rank] or None,
            "score": round(score, 4),
            "abstract_preview": _abstract_preview(idx.abstracts[rank]),
            "pb_code": idx.pb_codes[rank] or None,
            "keywords": [k.strip() for k in (idx.keywords[rank] or "").split(",") if k.strip()][:8],
        })
    return results


def find_similar_for_doc(doc_id: str, top_k: int = 8) -> list[dict]:
    idx = get_index()
    if idx.matrix.shape[0] == 0:
        return []
    if doc_id not in idx.doc_ids:
        return []

    pos = idx.doc_ids.index(doc_id)
    query_vec = idx.matrix[pos:pos + 1]

    matrix = _normalize(idx.matrix)
    qv = _normalize(query_vec.astype(np.float32))
    sims = (matrix @ qv.T).flatten()
    order = np.argsort(-sims)

    results: list[dict] = []
    for rank in order:
        if len(results) >= top_k + 1:
            break
        if idx.doc_ids[rank] == doc_id:
            continue
        score = float(sims[rank])
        if not np.isfinite(score):
            continue
        results.append({
            "doc_id": idx.doc_ids[rank],
            "title": idx.titles[rank],
            "year": idx.years[rank],
            "journal": idx.journals[rank] or None,
            "doi": idx.dois[rank] or None,
            "score": round(score, 4),
            "abstract_preview": _abstract_preview(idx.abstracts[rank]),
            "pb_code": idx.pb_codes[rank] or None,
            "keywords": [k.strip() for k in (idx.keywords[rank] or "").split(",") if k.strip()][:8],
        })
    return results[:top_k]
