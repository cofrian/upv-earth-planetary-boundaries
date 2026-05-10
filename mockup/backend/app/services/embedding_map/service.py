"""Servicio del mapa 2D de embeddings (UMAP sobre SPECTER2).

Lee los artefactos precalculados:
- `embeddings_2d.npy`        -> matriz (N, 2)
- `embeddings_2d_meta.json`  -> doc_id, title, year, pb_code, params

Expone una vista lista para el frontend (puntos coloreables por PB) y un
helper para localizar un paper concreto en el mapa.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np

from app.services.corpus_loader.precomputed import file_path

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingMap:
    available: bool
    points: list[dict[str, Any]]
    pbs: list[str]
    bounds: dict[str, float]
    params: dict[str, Any]
    model_id: str | None
    doc_id_index: dict[str, int]


@lru_cache(maxsize=1)
def load_map() -> EmbeddingMap:
    coords_path = file_path("embeddings_2d.npy")
    meta_path = file_path("embeddings_2d_meta.json")
    if coords_path is None or meta_path is None:
        return EmbeddingMap(
            available=False,
            points=[],
            pbs=[],
            bounds={"xmin": 0.0, "xmax": 0.0, "ymin": 0.0, "ymax": 0.0},
            params={},
            model_id=None,
            doc_id_index={},
        )

    try:
        coords = np.load(coords_path)
        with meta_path.open("r", encoding="utf-8") as fh:
            meta = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo cargar el mapa 2D: %s", exc)
        return EmbeddingMap(
            available=False,
            points=[],
            pbs=[],
            bounds={"xmin": 0.0, "xmax": 0.0, "ymin": 0.0, "ymax": 0.0},
            params={},
            model_id=None,
            doc_id_index={},
        )

    n = coords.shape[0]
    doc_ids = list(meta.get("doc_ids", []))
    titles = list(meta.get("titles", []))
    years = list(meta.get("years", []))
    pb_codes = list(meta.get("pb_codes", []))

    points: list[dict[str, Any]] = []
    doc_id_index: dict[str, int] = {}
    for i in range(n):
        doc_id = doc_ids[i] if i < len(doc_ids) else ""
        title = titles[i] if i < len(titles) else ""
        year = years[i] if i < len(years) else None
        pb = pb_codes[i] if i < len(pb_codes) else ""
        x, y = float(coords[i, 0]), float(coords[i, 1])
        points.append(
            {
                "doc_id": doc_id,
                "title": title,
                "year": year,
                "pb_code": pb or "Sin PB",
                "x": x,
                "y": y,
            }
        )
        if doc_id:
            doc_id_index[doc_id] = i

    pbs = sorted({p["pb_code"] for p in points})
    if not points:
        bounds = {"xmin": 0.0, "xmax": 0.0, "ymin": 0.0, "ymax": 0.0}
    else:
        xs = coords[:, 0]
        ys = coords[:, 1]
        bounds = {
            "xmin": float(xs.min()),
            "xmax": float(xs.max()),
            "ymin": float(ys.min()),
            "ymax": float(ys.max()),
        }

    return EmbeddingMap(
        available=True,
        points=points,
        pbs=pbs,
        bounds=bounds,
        params=dict(meta.get("params", {})),
        model_id=meta.get("model_id"),
        doc_id_index=doc_id_index,
    )


def reset_cache() -> None:
    load_map.cache_clear()


def get_map_payload(sample: int | None = None) -> dict[str, Any]:
    m = load_map()
    points = m.points
    if sample and len(points) > sample:
        # Sub-muestreo determinista (paso fijo) para mantener la
        # distribución espacial del mapa cuando el frontend pide menos
        # puntos por rendimiento.
        step = max(1, len(points) // sample)
        points = points[::step][:sample]
    return {
        "available": m.available,
        "points": points,
        "pbs": m.pbs,
        "bounds": m.bounds,
        "params": m.params,
        "model_id": m.model_id,
        "total": len(m.points),
        "returned": len(points),
    }


def get_paper_position(doc_id: str) -> dict[str, Any] | None:
    m = load_map()
    idx = m.doc_id_index.get(doc_id)
    if idx is None:
        return None
    return m.points[idx]
