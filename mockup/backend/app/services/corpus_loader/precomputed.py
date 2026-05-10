"""Localización canónica de los artefactos precalculados.

Estos artefactos se generan una sola vez con los scripts:
- `python -m scripts.precompute_eda`
- `python -m scripts.precompute_embeddings`

y se cargan al arranque del backend para evitar recalcular en cada request.
"""
from __future__ import annotations

import os
from pathlib import Path

PRECOMPUTED_SUBPATH = Path("seed") / "precomputed"


def _candidates() -> list[Path]:
    here = Path(__file__).resolve()
    fallbacks: list[Path] = [Path("/app/data") / PRECOMPUTED_SUBPATH]
    for parents_up in range(3, 8):
        try:
            base = here.parents[parents_up]
        except IndexError:
            continue
        fallbacks.append(base / "data" / PRECOMPUTED_SUBPATH)
        fallbacks.append(base / "mockup" / "data" / PRECOMPUTED_SUBPATH)
    override = os.getenv("PRECOMPUTED_DIR")
    if override:
        fallbacks.insert(0, Path(override))
    seen: set[str] = set()
    out: list[Path] = []
    for path in fallbacks:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def find_existing_dir() -> Path | None:
    for candidate in _candidates():
        if candidate.exists():
            return candidate
    return None


def writable_dir() -> Path:
    """Para los scripts: devuelve un directorio existente o el mejor candidato.

    Prefiere candidatos cuyo directorio padre ya exista, para no crear
    paths absolutos como `/app/...` cuando estamos ejecutando en local.
    """
    existing = find_existing_dir()
    if existing:
        return existing
    candidates = _candidates()
    for path in candidates:
        if path.parent.exists():
            path.mkdir(parents=True, exist_ok=True)
            return path
    target = candidates[-1]
    target.mkdir(parents=True, exist_ok=True)
    return target


def file_path(filename: str) -> Path | None:
    base = find_existing_dir()
    if base is None:
        return None
    candidate = base / filename
    return candidate if candidate.exists() else None


def writable_file(filename: str) -> Path:
    return writable_dir() / filename
