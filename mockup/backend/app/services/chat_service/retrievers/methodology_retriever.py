"""Snippets metodológicos del M2 para responder a preguntas de "por qué".

No es un RAG vectorial — son snippets curados, alineados con DESIGN.md y
los planes del M2. Es la fuente más estable, así que vive como datos
estáticos en el código. Si en el futuro queremos un RAG real sobre los
documentos del M2, basta sustituir este módulo por un retriever que lea
los .md / .pdf desde `docs/`.
"""
from __future__ import annotations

from typing import Any

_SNIPPETS: list[dict[str, str]] = [
    {
        "id": "title_plus_abstract",
        "topic": "representación del paper",
        "question": "¿Por qué se representa el paper como title + abstract limpio?",
        "answer": (
            "SPECTER2 fue entrenado con la concatenación de título y abstract, igual que SPECTER. "
            "Repetir esa fórmula garantiza que la representación del paper esté en el mismo "
            "espacio semántico para el que se optimizó el modelo y maximiza la utilidad del "
            "embedding para búsqueda de similitud entre artículos científicos."
        ),
    },
    {
        "id": "abstract_500_filter",
        "topic": "filtro de calidad",
        "question": "¿Por qué se filtran los abstracts con menos de 500 caracteres?",
        "answer": (
            "Un abstract por debajo de 500 caracteres normalmente es un fragmento (extracto, "
            "DOI suelto, copyright o frase introductoria) y no aporta señal suficiente para que "
            "SPECTER2 produzca un embedding estable. El umbral 500 ha sido el que mejor separa "
            "abstracts reales de ruido en el corpus UPV durante el AED, por eso es el criterio "
            "del corpus apto para embeddings."
        ),
    },
    {
        "id": "specter2_choice",
        "topic": "elección del modelo",
        "question": "¿Por qué SPECTER2 y no un modelo general?",
        "answer": (
            "SPECTER2 está específicamente entrenado en literatura científica (S2ORC + adapters "
            "por dominio). Frente a modelos genéricos tipo all-MiniLM, captura mejor las "
            "relaciones entre conceptos científicos, lo que se traduce en una recuperación de "
            "papers similares de mayor calidad temática para tareas como clasificación PB."
        ),
    },
    {
        "id": "faiss_rationale",
        "topic": "motor de similitud",
        "question": "¿Por qué FAISS / índice numpy en RAM?",
        "answer": (
            "El corpus UPV cabe en RAM como matriz `(N, dim)` float32 normalizada. Con N pequeño "
            "(≈ miles), un índice exacto en memoria con producto interno coseno es más simple, "
            "reproducible y rápido que montar un servicio vectorial externo. Si el corpus crece, "
            "el módulo `similarity_search` se puede cambiar a FAISS IVF/HNSW sin tocar el resto."
        ),
    },
    {
        "id": "m2_scope",
        "topic": "alcance del M2",
        "question": "¿Qué cubre el M2?",
        "answer": (
            "El M2 entrega: (1) corpus UPV limpio y trazable con motivos de descarte, "
            "(2) AED con KPIs, distribuciones por año/PB y calidad de abstracts, "
            "(3) embeddings SPECTER2 precalculados y búsqueda de papers similares, "
            "(4) inferencia de Planetary Boundaries con scoring por similitud al catálogo PB y "
            "explicación opcional con LLM, (5) interfaz web para subir un paper y verlo "
            "analizado en el flujo completo."
        ),
    },
    {
        "id": "llm_role",
        "topic": "papel del LLM",
        "question": "¿Qué hace el LLM dentro del sistema?",
        "answer": (
            "El LLM NO clasifica PBs ni decide qué papers son similares. Esa lógica está en los "
            "módulos `embedding_service`, `similarity_search` y `pb_inference` (basados en "
            "SPECTER2 y reglas de catálogo). El LLM se usa sólo para producir explicaciones "
            "legibles (`explanation_text` del resultado PB) y para conversar sobre resultados "
            "ya calculados en este chatbot."
        ),
    },
    {
        "id": "no_full_text_v1",
        "topic": "alcance V1",
        "question": "¿Por qué V1 no usa el texto completo del paper?",
        "answer": (
            "V1 trabaja con título + abstract limpio para mantener la representación coherente "
            "con el entrenamiento de SPECTER2 y para que los costes de cómputo y almacenamiento "
            "sean predecibles. Incorporar texto completo requiere chunking, deduplicación y un "
            "índice mucho mayor; queda como evolución posterior."
        ),
    },
]


def all_snippets() -> list[dict[str, str]]:
    return list(_SNIPPETS)


def fetch_relevant(question: str, max_items: int = 4) -> list[dict[str, Any]]:
    """Heurística simple por solapamiento de palabras clave.

    No es un retriever vectorial; el chatbot inyecta los snippets más
    relevantes al contexto y deja que el LLM los use como referencia
    cuando el usuario pregunta por la metodología. Si no hay coincidencia,
    devuelve los primeros snippets como pista mínima.
    """
    if not question:
        return _SNIPPETS[:max_items]

    q = question.lower()
    keywords_per_snippet = {
        "title_plus_abstract": ["title", "título", "abstract", "representación", "embedding"],
        "abstract_500_filter": ["500", "filtro", "longitud", "umbral", "calidad", "corto"],
        "specter2_choice": ["specter", "modelo", "minilm", "scibert"],
        "faiss_rationale": ["faiss", "índice", "indice", "similitud", "rapidez", "ram"],
        "m2_scope": ["m2", "entrega", "alcance", "milestone", "scope"],
        "llm_role": ["llm", "qwen", "ollama", "gpt", "modelo de lenguaje", "chat"],
        "no_full_text_v1": ["full text", "texto completo", "v1", "chunking"],
    }

    scored: list[tuple[int, dict[str, str]]] = []
    for snippet in _SNIPPETS:
        kws = keywords_per_snippet.get(snippet["id"], [])
        score = sum(1 for kw in kws if kw in q)
        if score:
            scored.append((score, snippet))

    if not scored:
        return _SNIPPETS[:max_items]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [snippet for _, snippet in scored[:max_items]]
