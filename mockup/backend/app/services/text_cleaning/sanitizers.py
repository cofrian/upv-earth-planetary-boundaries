"""Saneadores de texto para corpus científicos.

Aporta dos funciones públicas:

- ``sanitize_semantic_text``: limpia un texto largo (abstract / título +
  abstract) eliminando ruido bibliográfico antes del embedding.
- ``sanitize_title``: limpia un título corto. Si detecta que está
  completamente contaminado con cabecera de journal, devuelve cadena vacía
  para que el caller decida si reinferirlo.

Las heurísticas son conservadoras: prefieren dejar texto crudo que
borrar contenido legítimo. Todo se basa en regex puramente locales
(sin red, sin LLM).
"""
from __future__ import annotations

import re
import unicodedata

# --- Patrones reutilizables -------------------------------------------------

_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_DOI_PREFIX_RE = re.compile(r"\bdoi\s*[:.]\s*\S+", re.IGNORECASE)
_DOI_BARE_RE = re.compile(r"\b10\.\d{4,9}/[^\s)]+", re.IGNORECASE)
_COPYRIGHT_RE = re.compile(
    r"©\s*(?:the\s+)?author\(?s?\)?\s*\d{0,4}\.?", re.IGNORECASE
)
_COPYRIGHT_PLAIN_RE = re.compile(r"©\s*\d{4}[^.]*\.?")
_AUTHORS_BARE_RE = re.compile(r"\bauthor\(?s?\)?\s+\d{4}\b\.?", re.IGNORECASE)
_CC_LICENSE_RE = re.compile(
    r"\bcc\b[^.]{0,80}?(?:license|licence)\.?|creative\s+commons[^.]{0,80}?(?:license|licence)?\.?|\bcc(?:\s|-)?(?:by|attribution)[^.]{0,80}?(?:license|licence)?\.?",
    re.IGNORECASE,
)
_CC_LEFTOVER_RE = re.compile(r"\bcc\s+(?=[A-Z])", re.IGNORECASE)
_LICENSE_TAIL_RE = re.compile(r"\battribution\s*\d*(?:\.\d+)?\s+licen[sc]e\.?", re.IGNORECASE)
_LICENSE_NUMERIC_RE = re.compile(r"\b\d+\.\d+\s+licen[sc]e\b\.?", re.IGNORECASE)
_VOLUME_PAGE_RE = re.compile(
    r"\b(?:vol\.?|volume)\s*\d+[\s,;]+(?:no\.?\s*\d+[\s,;]+)?(?:pp\.?\s*)?\d+\s*[-–]\s*\d+\b",
    re.IGNORECASE,
)
_JOURNAL_HEADER_RE = re.compile(
    # Patrón típico: "Geosci. Model Dev., 7, 2077-2090, 2014" (o con
    # cualquier ruido pegado tras el año)
    r"\b[A-Z][A-Za-z]{2,}\.?(?:\s+[A-Z][A-Za-z\.]{0,})?(?:\s+[A-Z][a-z]+\.?)?,\s*\d+,\s*\d+\s*[-–]\s*\d+,\s*\d{4}\S*",
)
_HAL_ID_RE = re.compile(r"\bhal[-\s]?id\s*:\s*\S+", re.IGNORECASE)
_ARTICLE_PREFIX_RE = re.compile(r"^\s*article(?=[A-Z])|^\s*article\s+", re.IGNORECASE)
_AUTHORS_INLINE_RE = re.compile(
    r"Author\(?s?\)?\s*:\s*[A-Z][^.]{0,200}?(?=(?:abstract|introduction|methods|results|$))",
    re.IGNORECASE,
)
_AUTHORS_TAIL_RE = re.compile(r"author\(?s?\)?\s*:.*$", re.IGNORECASE | re.DOTALL)
_NUMERIC_CITATION_RE = re.compile(r"\[\s*\d+(?:\s*[,\-]\s*\d+)*\s*\]")
_MULTI_WS_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"^[\s\-\.,;:]+|[\s\-\.,;:]+$")
_DANGLING_DOT_RE = re.compile(r"\s+\.")
_LEADING_NUMBER_RE = re.compile(r"^\s*\d{4}\b\.?\s*")

# Patrones extra detectados en el corpus mixto (PDFs reales): "Citation:",
# "Keywords:", "ISSN:", "TYPE …", "Vol. …", URL sin esquema (warwick.ac.uk/…),
# DOI pelado al inicio, "Article" pegado al primer token, etc.
_CITATION_PREFIX_RE = re.compile(
    r"^\s*citation\s*(?:for\s+published\s+version)?\s*[:\-].*$",
    re.IGNORECASE | re.DOTALL,
)
_KEYWORDS_PREFIX_RE = re.compile(r"^\s*(?:key\s*words?|keywords?)\s*[:\-].*$", re.IGNORECASE | re.DOTALL)
_TYPE_PREFIX_RE = re.compile(r"^\s*type\s+[A-Z][\w\s\-]*$", re.IGNORECASE)
_ISSN_RE = re.compile(r"\b(?:e-?)?ISSN\s*[:\-]?\s*[\dX\-]+", re.IGNORECASE)
_VOL_PLACEHOLDER_RE = re.compile(r"vol\.?\s*[:\-]?\s*\(?[\d\s]+\)?", re.IGNORECASE)
_VOLUME_ISSUE_RE = re.compile(
    r"\b(?:volume|vol\.?)\s*\d+\s*(?:[,;]?\s*(?:issue|no\.?)\s*\d+)?",
    re.IGNORECASE,
)
_BARE_DOI_PREFIX_RE = re.compile(r"^\s*10\.\d{4,9}/\S+\s*", re.IGNORECASE)
_URL_NOSCHEME_RE = re.compile(
    # Cualquier dominio acabado en TLD habitual seguido (opcional) de /path,
    # incluidos compuestos como ac.uk, co.uk, edu.au, etc.
    r"\b[\w\-]+(?:\.[\w\-]+){1,4}\.(?:com|org|edu|gov|net|io|info|uk|de|es|fr|it|nl|au|ca|jp|cn|in|br|mx|ar|cl|us)\b(?:/\S*)?",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\b[\w\.\-+]+@[\w\.\-]+\.[a-z]{2,}\b", re.IGNORECASE)
_AFFIL_TAIL_RE = re.compile(
    r"\b(?:university|institute|school|department|faculty|college|laboratory)[^.]{0,120}",
    re.IGNORECASE,
)
_PAGES_TAIL_RE = re.compile(r"\bpp?\.?\s*\d+\s*[-–]\s*\d+\b", re.IGNORECASE)
_ARTICLE_HEADING_RE = re.compile(
    r"^\s*(?:article|review|paper\s+in|paper\s+on)\s+",
    re.IGNORECASE,
)
_LEADING_VOLUME_LINE_RE = re.compile(
    r"^[^A-Za-z]*(?:volume\s+\d+|vol\.?\s*\d+|issue\s+\d+).{0,160}$",
    re.IGNORECASE,
)
_CC_LICENSE_TEXT_RE = re.compile(
    r"this\s+work\s+is\s+(?:distributed|licensed)[^.]{0,160}",
    re.IGNORECASE,
)
_PUBLISHED_BY_RE = re.compile(r"\bpublished\s+(?:by|here\s+under)[^.]{0,120}", re.IGNORECASE)
_INSTITUTION_PREFIX_RE = re.compile(
    r"^\s*[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,4}\s+University[\.,]\s.*$"
)


def _normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace(" ", " ")
    return text


def sanitize_semantic_text(text: str) -> str:
    """Limpia un texto antes del embedding.

    Elimina URLs, DOIs, copyright, license y citaciones numéricas.
    No corta contenido científico legítimo.
    """
    if not text:
        return ""
    out = _normalize_unicode(text)
    out = _JOURNAL_HEADER_RE.sub(" ", out)
    out = _URL_RE.sub(" ", out)
    out = _DOI_PREFIX_RE.sub(" ", out)
    out = _DOI_BARE_RE.sub(" ", out)
    out = _COPYRIGHT_RE.sub(" ", out)
    out = _COPYRIGHT_PLAIN_RE.sub(" ", out)
    out = _AUTHORS_BARE_RE.sub(" ", out)
    out = _CC_LICENSE_RE.sub(" ", out)
    out = _LICENSE_TAIL_RE.sub(" ", out)
    out = _LICENSE_NUMERIC_RE.sub(" ", out)
    out = _CC_LEFTOVER_RE.sub("", out)
    out = _HAL_ID_RE.sub(" ", out)
    out = _NUMERIC_CITATION_RE.sub(" ", out)
    out = _DANGLING_DOT_RE.sub(".", out)
    out = _MULTI_WS_RE.sub(" ", out).strip()
    return out


# --- Detección y limpieza de títulos ---------------------------------------

_DIRTY_TITLE_SIGNALS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\bdoi\s*:", re.IGNORECASE),
    re.compile(r"©|creative\s+commons|cc\s*by|attribution\s+\d", re.IGNORECASE),
    _JOURNAL_HEADER_RE,
    _HAL_ID_RE,
    re.compile(r"\b\d{4}\s*www\.", re.IGNORECASE),
    # Cabeceras / placeholders típicos de PDF que el extractor confunde con título.
    re.compile(r"^\s*citation\s*(?:for\s+published\s+version)?\s*[:\-]", re.IGNORECASE),
    re.compile(r"^\s*key\s*words?\s*[:\-]", re.IGNORECASE),
    re.compile(r"^\s*type\s+[A-Z]", re.IGNORECASE),
    re.compile(r"^\s*vol\.?\s*[:\-]?\s*\(?\s*\d", re.IGNORECASE),
    re.compile(r"\b(?:e-?)?issn\b\s*[:\-]?\s*\d", re.IGNORECASE),
    re.compile(r"\bcopyright\b", re.IGNORECASE),
    re.compile(r"^\s*paper\s+in\b", re.IGNORECASE),
    # URL sin esquema (warwick.ac.uk/lib-publications) o slug con barra,
    # cubriendo TLDs simples y compuestos (.ac.uk, .co.uk, etc.).
    re.compile(
        r"\b[\w\-]+(?:\.[\w\-]+){1,4}\.(?:com|org|edu|gov|net|io|info|uk|de|es|fr|it|nl|au|ca|jp|cn|in|br|mx|ar|cl|us)\b(?:/\S*)?",
        re.IGNORECASE,
    ),
    # DOI pelado al inicio (10.xxxx/...).
    re.compile(r"^\s*10\.\d{4,9}/\S", re.IGNORECASE),
    # Email embebido (afiliación de autor).
    re.compile(r"@[\w\.\-]+\.[a-z]{2,}", re.IGNORECASE),
    # "Vol.:(0123456789)" o similares de placeholder de Springer.
    re.compile(r"vol\.?\s*[:\-]?\s*\(\s*0123456789\s*\)", re.IGNORECASE),
    # "Volume 6 Issue 1" estilo cabecera revista.
    re.compile(r"\b(?:volume|vol\.?)\s+\d+\s+(?:issue|no\.?)\s+\d+", re.IGNORECASE),
)


def looks_like_dirty_title(title: str) -> bool:
    """Heurística para decidir si un título está contaminado.

    True cuando contiene marcadores claros de cabecera bibliográfica
    o queda demasiado corto / largo para ser plausible.
    """
    if not title:
        return True
    text = title.strip()
    if len(text) < 8 or len(text) > 320:
        return True
    for pattern in _DIRTY_TITLE_SIGNALS:
        if pattern.search(text):
            return True
    return False


def sanitize_title(title: str) -> str:
    """Intenta dejar un título legible eliminando cabecera bibliográfica.

    Si tras la limpieza el resultado queda vacío o demasiado corto,
    devuelve "" para que el caller pueda intentar reinferirlo.
    """
    if not title:
        return ""
    out = _normalize_unicode(title)
    # Si el "título" empieza por Citation:/Keywords:/Vol./TYPE (placeholders
    # de PDF) preferimos descartar el título completo: la línea siguiente
    # nunca es un título real.
    if (
        _CITATION_PREFIX_RE.match(out)
        or _KEYWORDS_PREFIX_RE.match(out)
        or _VOL_PLACEHOLDER_RE.match(out)
        or _TYPE_PREFIX_RE.match(out)
        or _LEADING_VOLUME_LINE_RE.match(out)
        or _BARE_DOI_PREFIX_RE.match(out)
        or _INSTITUTION_PREFIX_RE.match(out)
    ):
        return ""
    out = _JOURNAL_HEADER_RE.sub(" ", out)
    out = _URL_RE.sub(" ", out)
    out = _URL_NOSCHEME_RE.sub(" ", out)
    out = _EMAIL_RE.sub(" ", out)
    out = _DOI_PREFIX_RE.sub(" ", out)
    out = _DOI_BARE_RE.sub(" ", out)
    out = _BARE_DOI_PREFIX_RE.sub(" ", out)
    out = _COPYRIGHT_RE.sub(" ", out)
    out = _COPYRIGHT_PLAIN_RE.sub(" ", out)
    out = _AUTHORS_BARE_RE.sub(" ", out)
    out = _CC_LICENSE_RE.sub(" ", out)
    out = _CC_LICENSE_TEXT_RE.sub(" ", out)
    out = _PUBLISHED_BY_RE.sub(" ", out)
    out = _LICENSE_TAIL_RE.sub(" ", out)
    out = _LICENSE_NUMERIC_RE.sub(" ", out)
    out = _HAL_ID_RE.sub(" ", out)
    out = _ISSN_RE.sub(" ", out)
    out = _VOLUME_PAGE_RE.sub(" ", out)
    out = _VOLUME_ISSUE_RE.sub(" ", out)
    out = _PAGES_TAIL_RE.sub(" ", out)
    out = _AUTHORS_INLINE_RE.sub(" ", out)
    out = _AUTHORS_TAIL_RE.sub(" ", out)
    out = _ARTICLE_PREFIX_RE.sub("", out)
    out = _ARTICLE_HEADING_RE.sub("", out)
    out = _LEADING_NUMBER_RE.sub("", out)
    out = _DANGLING_DOT_RE.sub(".", out)
    out = _MULTI_WS_RE.sub(" ", out).strip()
    out = _TRAILING_PUNCT_RE.sub("", out)
    if len(out) < 12 or out.lower().startswith("author"):
        return ""
    return out


__all__ = [
    "sanitize_semantic_text",
    "sanitize_title",
    "looks_like_dirty_title",
]
