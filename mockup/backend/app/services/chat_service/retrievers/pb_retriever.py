"""Recupera el catálogo de Planetary Boundaries (definiciones, reglas).

Lee el mismo CSV `pb_reference.csv` que ya consume `pb_inference`. El
chatbot lo usa para explicar PBs sin recalcular nada.
"""
from __future__ import annotations

import csv
import logging
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_catalog() -> list[dict[str, str]]:
    try:
        with open(settings.pb_reference_csv, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            return [dict(row) for row in reader]
    except FileNotFoundError:
        logger.warning("PB reference CSV no encontrado: %s", settings.pb_reference_csv)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo leer PB reference CSV: %s", exc)
        return []


def get_catalog() -> list[dict[str, Any]]:
    """Devuelve los PBs con sus definiciones cortas y keywords UPV."""
    rows = _load_catalog()
    return [
        {
            "pb_code": row.get("pb_code") or "PB-UNK",
            "pb_name": row.get("pb_name") or "",
            "short_definition": row.get("short_definition") or "",
            "applied_keywords_upv": row.get("applied_keywords_upv") or "",
        }
        for row in rows
    ]


def get_pb(pb_code: str) -> dict[str, Any] | None:
    code = (pb_code or "").strip().upper()
    if not code:
        return None
    for row in get_catalog():
        if str(row.get("pb_code", "")).strip().upper() == code:
            return row
    return None


def fetch_pb_context_for(pb_codes: list[str]) -> list[dict[str, Any]]:
    """Devuelve la ficha resumida de un subconjunto de PBs (los relevantes)."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for code in pb_codes:
        if not code:
            continue
        norm = str(code).strip().upper()
        if norm in seen:
            continue
        info = get_pb(norm)
        if info:
            out.append(info)
            seen.add(norm)
    return out
