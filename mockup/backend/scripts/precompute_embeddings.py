"""Precalcula los embeddings SPECTER2 del corpus UPV.

Genera dos artefactos en `data/seed/precomputed/`:
- `embeddings.npy`         -> matriz (N, dim) en float32, ya normalizada
- `embeddings_meta.json`   -> metadatos por fila para construir el índice

El backend cargará estos archivos al arranque y montará el índice de
similitud sin necesidad de volver a generar embeddings.

Ejecución:
    python -m scripts.precompute_embeddings
"""
from __future__ import annotations

import json
import math

import numpy as np

from app.services.corpus_loader.precomputed import writable_dir
from app.services.corpus_loader.service import get_corpus_layers
from app.services.embedding_service.service import embed_texts, get_active_model_info


def _coerce_year(value: object) -> int | None:
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    if 1900 <= number <= 2100:
        return int(number)
    return None


def main() -> None:
    layer = get_corpus_layers()["for_embeddings"]
    if layer.empty:
        print("No hay papers candidatos para embeddings.")
        return

    texts = layer["embedding_text"].astype(str).tolist()
    print(f"Calculando embeddings para {len(texts)} papers...")
    matrix = embed_texts(texts).astype(np.float32, copy=False)

    info = get_active_model_info()
    target_dir = writable_dir()

    np_path = target_dir / "embeddings.npy"
    np.save(np_path, matrix)

    pb_codes_col = "pb_folder" if "pb_folder" in layer.columns else None
    keywords_col = "keywords" if "keywords" in layer.columns else None
    title_col = "title_clean" if "title_clean" in layer.columns else "title"
    abstract_col = "clean_abstract_semantic" if "clean_abstract_semantic" in layer.columns else "abstract_norm"

    meta = {
        "model_id": info.model_id,
        "family": info.family,
        "embedding_dim": int(matrix.shape[1]),
        "vectors": int(matrix.shape[0]),
        "is_specter": info.is_specter,
        "fallback_used": info.fallback_used,
        "embedding_text_rule": "title + clean_abstract_semantic",
        "filter_rule": "abstract_char_len > 500",
        "doc_ids": layer["doc_id"].astype(str).tolist(),
        "titles": layer[title_col].astype(str).tolist(),
        "years": [_coerce_year(v) for v in layer.get("year_int", [])] if "year_int" in layer.columns else [None] * len(layer),
        "journals": layer["journal"].astype(str).tolist(),
        "dois": layer["doi"].astype(str).tolist(),
        "abstracts": layer[abstract_col].astype(str).tolist(),
        "keywords": layer[keywords_col].astype(str).tolist() if keywords_col else [""] * len(layer),
        "pb_codes": layer[pb_codes_col].astype(str).tolist() if pb_codes_col else [""] * len(layer),
    }

    meta_path = target_dir / "embeddings_meta.json"
    with meta_path.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)

    size_mb = np_path.stat().st_size / (1024 * 1024)
    print(f"Embeddings: {matrix.shape} ({size_mb:.1f} MB) -> {np_path}")
    print(f"Metadatos:  {meta_path}")
    print(f"Modelo:     {info.model_id} (specter={info.is_specter}, fallback={info.fallback_used})")


if __name__ == "__main__":
    main()
