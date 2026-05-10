import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401
from app.db.session import engine
from app.services.corpus_loader.precomputed import file_path

logger = logging.getLogger(__name__)


def _resolve_eda_dir() -> Path | None:
    here = Path(__file__).resolve()
    for parents_up in range(3, 8):
        try:
            base = here.parents[parents_up]
        except IndexError:
            continue
        candidate = base / "docs" / "eda"
        if candidate.exists():
            return candidate
    return None

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="UPV-EARTH API",
    version="0.1.0",
    description="Plataforma analítica de Planetary Boundaries para corpus UPV",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _warmup_similarity_index() -> None:
    """Si hay embeddings precalculados, levanta el índice ya en RAM.

    Evita que el primer usuario vea `vectores=0` o pague el coste de la
    primera petición. La carga desde `.npy` precalculado es del orden de
    decenas de milisegundos.
    """
    if not file_path("embeddings.npy") or not file_path("embeddings_meta.json"):
        logger.info("Warmup omitido: no hay embeddings precalculados.")
        return
    try:
        from app.services.similarity_search.service import get_index

        idx = get_index()
        logger.info(
            "Warmup OK: índice %s con %s vectores · dim %s · modelo %s",
            idx.source,
            len(idx.doc_ids),
            idx.embedding_dim,
            idx.model_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Warmup del índice falló: %s", exc)


_eda_dir = _resolve_eda_dir()
if _eda_dir:
    app.mount("/static/eda", StaticFiles(directory=str(_eda_dir)), name="eda-static")
    logger.info("Servidor estático de EDA montado en /static/eda → %s", _eda_dir)
else:
    logger.warning("No se encontró el directorio docs/eda; los assets estáticos no se montarán.")


app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "upv-earth-api", "status": "ok"}


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
