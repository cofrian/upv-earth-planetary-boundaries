"""Wrapper de embeddings con backbone SPECTER2 preferente.

El plan de entrega exige SPECTER2 (`allenai/specter2_base`) como modelo
de embeddings principal para representar `title + clean_abstract_semantic`.
Cuando el modelo no está disponible localmente y no se puede descargar,
hacemos fallback automático a un sentence-transformers genérico para
no bloquear la plataforma.

`get_active_model_info()` expone el modelo cargado para que la UI lo
informe al usuario con honestidad.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class ModelInfo:
    model_id: str
    family: str
    dimension: int | None
    is_specter: bool
    fallback_used: bool


_active_info: ModelInfo | None = None


def _looks_like_specter(model_id: str) -> bool:
    return "specter" in (model_id or "").lower()


def _candidates() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for candidate in (settings.embeddings_model_name, FALLBACK_MODEL):
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


@lru_cache(maxsize=1)
def _load_model() -> tuple[object, ModelInfo]:
    from sentence_transformers import SentenceTransformer

    candidates = _candidates()
    primary = candidates[0]

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            model = SentenceTransformer(candidate)
            dim = int(model.get_sentence_embedding_dimension() or 0)
            info = ModelInfo(
                model_id=candidate,
                family="SPECTER2" if _looks_like_specter(candidate) else "sentence-transformers",
                dimension=dim,
                is_specter=_looks_like_specter(candidate),
                fallback_used=candidate != primary,
            )
            logger.info("Embedding backbone activo: %s (dim=%s)", candidate, dim)
            return model, info
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("No se pudo cargar %s: %s", candidate, exc)
            continue

    raise RuntimeError(f"No se pudo cargar ningún modelo de embeddings. Último error: {last_error}")


def _ensure_loaded() -> tuple[object, ModelInfo]:
    global _active_info
    model, info = _load_model()
    _active_info = info
    return model, info


def get_active_model_info() -> ModelInfo:
    if _active_info is not None:
        return _active_info
    try:
        _, info = _ensure_loaded()
        return info
    except Exception as exc:  # noqa: BLE001
        logger.error("Embeddings no disponibles: %s", exc)
        return ModelInfo(
            model_id="unavailable",
            family="unavailable",
            dimension=None,
            is_specter=False,
            fallback_used=True,
        )


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    model, _ = _ensure_loaded()
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    return np.asarray(vectors)
