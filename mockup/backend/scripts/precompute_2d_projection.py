"""Proyección 2D UMAP del corpus para el mapa de embeddings.

Lee `embeddings.npy` + `embeddings_meta.json` (matriz N×768 SPECTER2)
y produce dos artefactos en `data/seed/precomputed/`:

- `embeddings_2d.npy`        -> matriz (N, 2) float32 con coordenadas UMAP
- `embeddings_2d_meta.json`  -> doc_id, title, year, pb_code, params, model_id

Por qué UMAP:
- Mantiene la estructura local (clusters por PB se separan visualmente).
- Soporta `transform()` para proyectar nuevos papers sin reentrenar todo
  el modelo, así futuras subidas pueden colocarse en el mismo mapa.
- Determinista con `random_state=42`.

Ejecución:
    python -m scripts.precompute_2d_projection
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.services.corpus_loader.precomputed import file_path, writable_dir


def main() -> None:
    emb_path = file_path("embeddings.npy")
    meta_path = file_path("embeddings_meta.json")
    if emb_path is None or meta_path is None:
        raise SystemExit("embeddings.npy / embeddings_meta.json no encontrados")

    matrix = np.load(emb_path).astype(np.float32, copy=False)
    with meta_path.open("r", encoding="utf-8") as fh:
        meta = json.load(fh)

    n, dim = matrix.shape
    print(f"Cargados {n} embeddings ({dim}-dim).")

    # Importamos aquí para evitar coste de import si no se ejecuta.
    import umap  # type: ignore

    n_neighbors = min(30, max(5, n // 1000))
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=0.1,
        metric="cosine",
        random_state=42,
        verbose=True,
    )
    print(f"Ajustando UMAP (n_neighbors={n_neighbors}, metric=cosine)...")
    coords = reducer.fit_transform(matrix).astype(np.float32, copy=False)
    print(f"UMAP listo. Forma: {coords.shape}")

    target_dir: Path = writable_dir()
    npy_path = target_dir / "embeddings_2d.npy"
    np.save(npy_path, coords)

    payload = {
        "model_id": meta.get("model_id"),
        "embedding_dim": int(matrix.shape[1]),
        "vectors": int(coords.shape[0]),
        "params": {
            "method": "umap",
            "n_neighbors": int(n_neighbors),
            "min_dist": 0.1,
            "metric": "cosine",
            "random_state": 42,
        },
        "doc_ids": list(meta.get("doc_ids", [])),
        "titles": list(meta.get("titles", [])),
        "years": list(meta.get("years", [])),
        "pb_codes": list(meta.get("pb_codes", [])),
    }
    meta_2d_path = target_dir / "embeddings_2d_meta.json"
    with meta_2d_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)

    size_mb = npy_path.stat().st_size / (1024 * 1024)
    print(f"OK -> {npy_path} ({size_mb:.1f} MB)")
    print(f"Meta -> {meta_2d_path}")


if __name__ == "__main__":
    main()
