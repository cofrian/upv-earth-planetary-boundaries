import os
import math
import hashlib
import random
import re
import html
import subprocess
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # PyMuPDF
import pandas as pd

try:
    from nltk.corpus import stopwords as nltk_stopwords
    import nltk

    try:
        STOPWORDS = set(nltk_stopwords.words("english")) | set(nltk_stopwords.words("spanish"))
    except LookupError:
        nltk.download("stopwords", quiet=True)
        STOPWORDS = set(nltk_stopwords.words("english")) | set(nltk_stopwords.words("spanish"))
except Exception:
    STOPWORDS = {
        "the", "and", "for", "with", "this", "that", "from", "were", "are", "was", "have", "has", "had",
        "into", "their", "there", "than", "then", "when", "where", "which", "while", "within", "without",
        "using", "used", "use", "also", "can", "may", "might", "more", "most", "some", "such", "over",
        "between", "through", "about", "across", "during", "results", "result", "study", "paper", "article",
        "data", "method", "methods", "model", "models", "analysis", "based", "show", "shows", "shown",
        "high", "low", "new", "one", "two", "three", "four", "five", "first", "second", "third", "both",
        "these", "those", "each", "other", "than", "into", "onto", "per", "via", "its", "our", "your",
        "they", "them", "you", "we", "his", "her", "not", "but", "all", "any", "due", "doi", "http",
        "https", "www", "com", "org", "edu", "introduction", "abstract", "keywords", "index", "terms",
        "del", "las", "los", "una", "uno", "unos", "unas", "para", "por", "con", "sin", "sobre", "entre",
        "desde", "hasta", "como", "tambien", "también", "este", "esta", "estos", "estas", "ese", "esa",
        "esos", "esas", "fue", "fueron", "ser", "son", "han", "hace", "hacer", "hacia", "segun", "según",
        "datos", "estudio", "resultados", "metodo", "método", "metodos", "métodos", "analisis", "análisis",
        "introduccion", "introducción", "resumen", "palabras", "clave",
    }

SAMPLE_SIZE = 1000
DOWNLOAD_BLOCKS = 3
# Anchored to the repository root so the script runs from any working directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST_FILE = os.path.join(BASE_DIR, "muestras", "listado_pdfs.txt")
SAMPLE_MANIFEST = os.path.join(BASE_DIR, "muestras", "muestra_seleccionada_1000_balanced.csv")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "data", "pdfs")

# Distinct from the random-sample outputs in extract_corpus.py: writing to the
# same names would overwrite the versioned corpus in data/corpus/.
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "corpus", "corpus_1000_balanced_clean.csv")
TRACEABILITY_FILE = os.path.join(BASE_DIR, "data", "corpus", "corpus_1000_balanced_traceability.csv")

# The Drive remote is team-specific; override it without editing the source.
RCLONE_REMOTE = os.getenv("RCLONE_REMOTE", "gdrive:datos proyectoiii/PB/")
PREVIEW_PAGES = 2
KEEP_LOCAL_CACHE = False
USE_BATCH_DOWNLOAD = True
MIN_CLEAN_ABSTRACT_CHARS = 500
LANGUAGE_MIN_CONFIDENCE = 0.80
CPU_COUNT = os.cpu_count() or 1
MAX_WORKERS = 1 if CPU_COUNT <= 1 else min(4, CPU_COUNT)

DOMAIN_STOPWORDS = {"doi", "http", "https", "www", "com", "org", "edu", "introduction", "abstract", "keywords", "index", "terms"}
AUXILIARY_NOISE_STOPWORDS = {
    "be", "been", "being", "am", "is", "are", "was", "were",
    "do", "does", "did", "done",
    "will", "would", "should", "could", "might", "must", "shall", "can", "may",
    "get", "gets", "got", "getting",
    "make", "makes", "made", "making",
    "using", "used", "use",
    "however", "therefore", "thus", "although",
    "paper", "study", "studies", "article", "research",
    "keyword", "keywords", "author", "authors", "et", "al",
}
STOPWORDS = STOPWORDS | DOMAIN_STOPWORDS | AUXILIARY_NOISE_STOPWORDS


def safe_filename(file_name):
    base_name = re.sub(r'[\\/:*?"<>|]+', "_", file_name).strip()
    return base_name or "documento.pdf"


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_identifier_text(text):
    text = strip_accents(normalize_text(text).lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(doi):
    if not doi:
        return None

    value = normalize_text(str(doi)).lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    value = value.strip().rstrip(".")
    return value or None


def build_doc_id(remote_path):
    return hashlib.md5(remote_path.encode("utf-8")).hexdigest()[:12]


def clean_abstract_text(text):
    if not text:
        return None
    return normalize_text(text)


def normalize_keywords_output(value):
    if not value:
        return None
    if isinstance(value, list):
        return "; ".join(value) if value else None
    return str(value)


def normalize_language_label(value):
    return value if value else None


def detect_language(text):
    if not text:
        return None, 0.0

    sample = normalize_text(text)[:6000]
    if len(sample) < 120:
        return None, 0.0

    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        detections = detect_langs(sample)
        if not detections:
            return None, 0.0

        best = detections[0]
        return best.lang, float(best.prob)
    except Exception:
        english_hits = sum(1 for token in re.findall(r"[a-zA-Z]{3,}", sample.lower()) if token in STOPWORDS)
        spanish_markers = sum(1 for token in re.findall(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{3,}", sample.lower()) if token in {"de", "la", "que", "y", "el", "en", "los", "las", "para", "con"})
        if english_hits >= spanish_markers:
            return "en", 0.55
        return "unknown", 0.0


def extract_authors(doc, preview_text):
    metadata_author = normalize_text(doc.metadata.get("author", "")) if doc.metadata else ""
    if metadata_author:
        return metadata_author

    page_lines = [normalize_text(line) for line in preview_text.splitlines() if normalize_text(line)]
    if len(page_lines) < 2:
        return None

    abstract_index = None
    for index, line in enumerate(page_lines):
        if re.search(r"(?i)\babstract\b", line):
            abstract_index = index
            break

    candidate_lines = page_lines[1:abstract_index] if abstract_index and abstract_index > 1 else page_lines[1:4]
    authors = []
    for line in candidate_lines:
        if re.search(r"(?i)copyright|received|accepted|doi|journal|volume|issn|abstract", line):
            continue
        if len(line) < 6:
            continue
        if re.search(r"\b(University|Institute|Department|School|Laboratory|Centre|Center|Faculty)\b", line, re.IGNORECASE):
            continue
        authors.append(line)

    if not authors:
        return None

    return normalize_text(" ".join(authors[:2]))


def extract_journal(doc, preview_text):
    if doc.metadata:
        metadata_subject = normalize_text(doc.metadata.get("subject", ""))
        metadata_title = normalize_text(doc.metadata.get("title", ""))
        if metadata_subject and len(metadata_subject) > 4:
            return metadata_subject
        if metadata_title and len(metadata_title) > 4:
            return metadata_title

    journal_patterns = [
        r"(?im)^\s*([A-Z][A-Za-z0-9&'\-\s]{4,80})\s+\d{4}.*$",
        r"(?im)^\s*([A-Z][A-Za-z0-9&'\-\s]{4,80})\s+(?:Vol\.?|Volume|No\.?|Issue)\b.*$",
    ]
    for pattern in journal_patterns:
        match = re.search(pattern, preview_text)
        if match:
            candidate = normalize_text(match.group(1))
            if len(candidate) > 4:
                return candidate

    return None


def extract_abstract_from_preview(preview_text):
    start_patterns = [
        r"(?i)\babstract\b\s*[:\n-]?",
        r"(?i)\ba\s*b\s*s\s*t\s*r\s*a\s*c\s*t\b\s*[:\n-]?",
        r"(?i)\bsummary\b\s*[:\n-]?",
        r"(?i)\bresumen\b\s*[:\n-]?",
        r"(?i)\bresumo\b\s*[:\n-]?",
    ]
    end_pattern = r"(?i)\b(introduction|1\.?\s*introduction|keywords?|index terms|materials? and methods?|methods?|background)\b"

    for pattern in start_patterns:
        start = re.search(pattern, preview_text)
        if not start:
            continue

        tail = preview_text[start.end():]
        end = re.search(end_pattern, tail)
        candidate = tail[:end.start()] if end else tail[:2500]
        candidate = normalize_text(candidate)

        if len(candidate) >= 120:
            return candidate

    intro = re.search(r"(?i)\b(1\.?\s*)?introduction\b", preview_text)
    head = preview_text[:intro.start()] if intro else preview_text[:3000]
    head = normalize_text(head)

    sentences = re.split(r"(?<=[.!?])\s+", head)
    joined = ""
    for sentence in sentences:
        s = sentence.strip()
        if len(s) < 40:
            continue
        joined = (joined + " " + s).strip()
        if len(joined) >= 220:
            break

    return joined if len(joined) >= 120 else None


def extract_keywords(raw_text):
    patterns = [
        r"(?im)^\s*(?:author\s+keywords?|keywords?|key\s+words|index\s+terms|indexing\s+terms|subject\s+terms|subject\s+headings?|descriptors?|descriptores?|palabras\s+clave|mots[-\s]?clés|schl[üu]sselwörter|termos\s+chave)\s*[:\-]?\s*(.{0,1000})",
        r"(?is)\b(?:author\s+keywords?|keywords?|key\s+words|index\s+terms|indexing\s+terms|subject\s+terms|subject\s+headings?|descriptors?|descriptores?|palabras\s+clave|mots[-\s]?clés|schl[üu]sselwörter|termos\s+chave)\b\s*[:\-]?\s*(.{0,1000})",
    ]

    stop_markers = re.compile(
        r"(?im)^(?:\s*)(abstract|introduction|materials? and methods?|methods?|background|results?|discussion|conclusions?|references?|acknowledg(e)?ments?|funding|competing interests?)\b"
    )

    for pattern in patterns:
        match = re.search(pattern, raw_text)
        if not match:
            continue

        chunk = match.group(1)
        stop = stop_markers.search(chunk)
        if stop:
            chunk = chunk[:stop.start()]

        blank_stop = re.search(r"\n\s*\n", chunk)
        if blank_stop:
            chunk = chunk[:blank_stop.start()]

        chunk = chunk.replace("\r", "")
        pieces = re.split(r"[\n,;|•·]+", chunk)
        cleaned = []
        for piece in pieces:
            token = normalize_text(piece)
            token = re.sub(r"^[\-–—:\.]|[\-–—:\.]$", "", token).strip()
            if len(token) < 3:
                continue
            if len(token) > 80:
                continue
            cleaned.append(token)

        unique = []
        seen = set()
        for item in cleaned:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        if unique:
            return "; ".join(unique[:15])

    return None


def extract_top_terms(full_text, top_n=12):
    if not full_text:
        return None

    text = full_text.lower()
    tokens = re.findall(r"[a-zA-ZÀ-ÿ]{4,}", text)
    filtered = []
    for token in tokens:
        normalized_token = strip_accents(token)
        if normalized_token in STOPWORDS:
            continue
        if normalized_token.isdigit():
            continue
        filtered.append(normalized_token)

    if not filtered:
        return None

    counts = Counter(filtered)
    return "; ".join(word for word, _ in counts.most_common(top_n))


OUTPUT_COLUMNS = [
    "doc_id",
    "title",
    "abstract",
    "clean_abstract",
    "year",
    "doi",
    "source",
    "authors",
    "keywords",
    "journal",
    "language",
    "top_terms_no_stopwords",
]


TRACEABILITY_COLUMNS = OUTPUT_COLUMNS + [
    "file_name",
    "pb_folder",
    "source_folder",
    "full_text",
    "language_confidence",
    "abstract_length",
    "clean_abstract_length",
    "dedupe_key",
    "filter_status",
    "filter_reason",
    "quality_flag",
]


def local_mirror_path(remote_path):
    return os.path.join(DOWNLOAD_DIR, remote_path)


def prune_empty_dirs(path):
    current = os.path.dirname(path)
    root = os.path.abspath(DOWNLOAD_DIR)

    while os.path.abspath(current).startswith(root) and current != DOWNLOAD_DIR:
        if os.path.isdir(current) and not os.listdir(current):
            os.rmdir(current)
            current = os.path.dirname(current)
            continue
        break


def load_pdf_inventory(list_file):
    if not os.path.exists(list_file):
        raise FileNotFoundError(
            f"No existe el listado de PDFs en {list_file}. Genera primero el inventario con rclone."
        )

    with open(list_file, "r", encoding="utf-8") as file_handle:
        # El listado puede contener entidades HTML (&lt; &gt;), las decodificamos.
        return [html.unescape(line.strip()) for line in file_handle if line.strip()]


def extract_path_parts(relative_path):
    parts = relative_path.split("/")
    pb_folder = parts[0] if parts else None
    source_folder = parts[1] if len(parts) > 1 else None
    return pb_folder, source_folder


def build_balanced_sample():
    """
    Crea una muestra estratificada equilibrada donde cada Planetary Boundary
    tiene la misma cantidad de papers.
    """
    all_paths = load_pdf_inventory(LIST_FILE)
    
    # Agrupar por Planetary Boundary
    pb_groups = defaultdict(list)
    for path in all_paths:
        pb_folder, _ = extract_path_parts(path)
        pb_groups[pb_folder].append(path)
    
    # Calcular cantidad de papers por PB
    num_pbs = len(pb_groups)
    papers_per_pb = SAMPLE_SIZE // num_pbs
    remainder = SAMPLE_SIZE % num_pbs
    
    print(f"\n=== MUESTREO ESTRATIFICADO EQUILIBRADO ===")
    print(f"Total de PDFs en inventario: {len(all_paths):,}")
    print(f"Cantidad de PB encontrados: {num_pbs}")
    print(f"Papers por PB: {papers_per_pb}")
    print(f"Remainder (papers adicionales): {remainder}")
    print(f"Tamaño total de muestra: {SAMPLE_SIZE}\n")
    
    selected = []
    pb_distribution = {}
    
    # Muestreo estratificado: mismo tamaño para cada PB
    for pb_index, (pb_folder, paths) in enumerate(sorted(pb_groups.items()), 1):
        # Algunos PB pueden tener papers adicionales si hay remainder
        size_for_pb = papers_per_pb + (1 if pb_index <= remainder else 0)
        
        # Hacer muestreo aleatorio dentro del grupo
        sampled = random.sample(paths, min(size_for_pb, len(paths)))
        selected.extend(sampled)
        
        pb_distribution[pb_folder] = len(sampled)
        print(f"  {pb_folder:<35} {len(sampled):>4} papers (disponibles: {len(paths):,})")
    
    print(f"\nTotal muestreado: {len(selected)} papers")
    
    # Crear estructura de datos para salida
    sample = []
    for remote_path in selected:
        pb_folder, source_folder = extract_path_parts(remote_path)
        sample.append(
            {
                "doc_id": build_doc_id(remote_path),
                "remote_path": remote_path,
                "file_name": os.path.basename(remote_path),
                "pb_folder": pb_folder,
                "source_folder": source_folder,
            }
        )
    
    # Guardar manifest
    os.makedirs(os.path.dirname(SAMPLE_MANIFEST), exist_ok=True)
    pd.DataFrame(sample).to_csv(SAMPLE_MANIFEST, index=False)
    
    print(f"\nManifesto guardado en: {SAMPLE_MANIFEST}")
    
    return sample


def build_random_sample():
    """Muestreo aleatorio sin estratificación (función original)"""
    all_paths = load_pdf_inventory(LIST_FILE)
    selected = random.sample(all_paths, min(SAMPLE_SIZE, len(all_paths)))

    sample = []
    for remote_path in selected:
        pb_folder, source_folder = extract_path_parts(remote_path)
        sample.append(
            {
                "doc_id": build_doc_id(remote_path),
                "remote_path": remote_path,
                "file_name": os.path.basename(remote_path),
                "pb_folder": pb_folder,
                "source_folder": source_folder,
            }
        )

    os.makedirs(os.path.dirname(SAMPLE_MANIFEST), exist_ok=True)
    pd.DataFrame(sample).to_csv(SAMPLE_MANIFEST, index=False)
    return sample


def split_sample_into_blocks(sample, num_blocks):
    if num_blocks <= 1 or len(sample) <= 1:
        return [sample]

    block_size = max(1, math.ceil(len(sample) / num_blocks))
    return [sample[i : i + block_size] for i in range(0, len(sample), block_size)]


def batch_download_sample(sample):
    list_path = os.path.join("muestras", "_sample_paths.tmp")
    with open(list_path, "w", encoding="utf-8") as handle:
        for item in sample:
            handle.write(f"{item['remote_path']}\n")

    try:
        result = subprocess.run(
            [
                "rclone",
                "copy",
                RCLONE_REMOTE,
                DOWNLOAD_DIR,
                "--files-from",
                list_path,
                "--ignore-existing",
                "--checkers",
                "8",
                "--transfers",
                "4",
                "--fast-list",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        # No abortar el flujo completo por errores parciales: luego hay fallback por archivo.
        if result.returncode != 0:
            stderr_text = (result.stderr or "").strip()
            short_error = "\n".join(stderr_text.splitlines()[:5])
            print("[Aviso] rclone batch devolvió errores parciales; se intentará fallback por archivo.")
            if short_error:
                print(f"[Detalle rclone] {short_error}")
    finally:
        if os.path.exists(list_path):
            os.remove(list_path)


def process_sample_block(sample_block, block_index, block_total):
    rows = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(process_pdf_item, item): item for item in sample_block}
        for index, future in enumerate(as_completed(future_map), 1):
            item = future_map[future]
            print(
                f"[Bloque {block_index}/{block_total} | {index}/{len(sample_block)}] Procesando mixto: {item['file_name'][:40]}..."
            )
            try:
                result = future.result()
            except Exception as error:
                print(f"    [Error] Fallo en {item['file_name']}: {error}")
                continue
            if result:
                rows.append(result)

    return rows


def append_rows_to_csv(rows, output_file, columns, write_header=False):
    if not rows:
        return

    pd.DataFrame(rows, columns=columns).to_csv(
        output_file,
        index=False,
        mode="w" if write_header else "a",
        header=write_header,
    )


def download_pdf(remote_path):
    try:
        file_path = local_mirror_path(remote_path)
        if os.path.exists(file_path):
            return file_path

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        remote_spec = f"{RCLONE_REMOTE}{remote_path}"
        subprocess.run(
            ["rclone", "copyto", remote_spec, file_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        return file_path
    except Exception as error:
        print(f"    [Error] No se pudo descargar {remote_path}: {error}")
        return None


def extract_mixed_content(pdf_path):
    data = {
        "file_name": os.path.basename(pdf_path),
        "doc_id": None,
        "title": None,
        "abstract": None,
        "clean_abstract": None,
        "full_text": None,
        "doi": None,
        "year": None,
        "authors": None,
        "journal": None,
        "keywords": None,
        "top_terms_no_stopwords": None,
        "language": None,
        "language_confidence": 0.0,
        "quality_flag": "low",
    }

    try:
        doc = fitz.open(pdf_path)
        page_texts = [doc[i].get_text() for i in range(len(doc))]
        preview_pages = min(PREVIEW_PAGES, len(page_texts))
        preview_text = "\n".join(page_texts[:preview_pages])
        data["full_text"] = " ".join(t.replace("\n", " ").replace("\r", " ") for t in page_texts).strip()
        data["keywords"] = extract_keywords(preview_text)
        data["top_terms_no_stopwords"] = extract_top_terms(data["full_text"])
        data["authors"] = extract_authors(doc, preview_text)
        data["journal"] = extract_journal(doc, preview_text)

        if len(doc) > 0:
            blocks = doc[0].get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] != 0:
                    continue
                block_text = "".join(
                    span["text"]
                    for line in block["lines"]
                    for span in line["spans"]
                )
                if len(block_text.strip()) > 15:
                    data["title"] = normalize_text(block_text)
                    break

        doi_match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", preview_text, re.IGNORECASE)
        if doi_match:
            data["doi"] = doi_match.group(1)

        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", preview_text)
        if year_match:
            data["year"] = year_match.group(1)

        data["abstract"] = extract_abstract_from_preview(preview_text)
        data["clean_abstract"] = clean_abstract_text(data["abstract"])
        if data["clean_abstract"]:
            data["quality_flag"] = "medium" if len(data["clean_abstract"]) > 150 else "low"
            language, confidence = detect_language(data["clean_abstract"])
            data["language"] = normalize_language_label(language)
            data["language_confidence"] = confidence

        if data["full_text"] and len(data["full_text"]) > 2000 and data["quality_flag"] == "low":
            data["quality_flag"] = "medium"

        doc.close()
    except Exception as error:
        print(f"Error procesando {pdf_path}: {error}")
        data["quality_flag"] = "error"

    return data


def process_pdf_item(pdf_item):
    local_path = local_mirror_path(pdf_item["remote_path"])
    if not os.path.exists(local_path):
        local_path = download_pdf(pdf_item["remote_path"])

    if not local_path:
        return None

    try:
        extracted = extract_mixed_content(local_path)
        return {
            "doc_id": pdf_item.get("doc_id"),
            "file_name": extracted["file_name"],
            "title": extracted["title"],
            "abstract": extracted["abstract"],
            "clean_abstract": extracted["clean_abstract"],
            "keywords": extracted["keywords"],
            "top_terms_no_stopwords": extracted["top_terms_no_stopwords"],
            "full_text": extracted["full_text"],
            "doi": extracted["doi"],
            "year": extracted["year"],
            "authors": extracted["authors"],
            "journal": extracted["journal"],
            "language": extracted["language"],
            "language_confidence": extracted["language_confidence"],
            "quality_flag": extracted["quality_flag"],
            "pb_folder": pdf_item.get("pb_folder"),
            "source_folder": pdf_item.get("source_folder"),
            "source": "rclone_drive",
        }
    finally:
        if (not KEEP_LOCAL_CACHE) and os.path.exists(local_path):
            os.remove(local_path)
            prune_empty_dirs(local_path)


def evaluate_record(row, seen_dois, seen_title_years):
    reasons = []
    abstract_text = clean_abstract_text(row.get("clean_abstract") or row.get("abstract"))
    row["clean_abstract"] = abstract_text
    row["abstract_length"] = len(abstract_text or "")
    row["clean_abstract_length"] = len(abstract_text or "")

    if not abstract_text:
        reasons.append("abstract_empty")
    elif len(abstract_text) < MIN_CLEAN_ABSTRACT_CHARS:
        reasons.append(f"abstract_too_short<{MIN_CLEAN_ABSTRACT_CHARS}")

    language = normalize_language_label(row.get("language"))
    if not language and abstract_text:
        language, confidence = detect_language(abstract_text)
        row["language"] = normalize_language_label(language)
        row["language_confidence"] = confidence
    else:
        confidence = float(row.get("language_confidence") or 0.0)

    if row.get("language") and row["language"] != "en":
        reasons.append(f"language_not_english:{row['language']}")
    elif not row.get("language"):
        reasons.append("language_unknown")
    elif confidence and confidence < LANGUAGE_MIN_CONFIDENCE:
        reasons.append(f"language_low_confidence:{confidence:.2f}")

    doi = normalize_doi(row.get("doi"))
    title_key = normalize_identifier_text(row.get("title") or "")
    year = str(row.get("year") or "").strip()
    dedupe_key = None

    if doi:
        dedupe_key = f"doi:{doi}"
        if dedupe_key in seen_dois:
            reasons.append("duplicate_doi")
    elif title_key and year:
        dedupe_key = f"titleyear:{title_key}|{year}"
        if dedupe_key in seen_title_years:
            reasons.append("duplicate_title_year")
    else:
        dedupe_key = f"doc:{row.get('doc_id') or row.get('file_name')}"

    row["dedupe_key"] = dedupe_key
    row["abstract"] = row.get("abstract") or abstract_text
    row["filter_reason"] = "|".join(reasons)
    row["filter_status"] = "kept" if not reasons else "dropped"
    return not reasons


def register_dedupe_key(row, seen_dois, seen_title_years):
    doi = normalize_doi(row.get("doi"))
    title_key = normalize_identifier_text(row.get("title") or "")
    year = str(row.get("year") or "").strip()

    if doi:
        seen_dois.add(f"doi:{doi}")
    elif title_key and year:
        seen_title_years.add(f"titleyear:{title_key}|{year}")


def make_output_row(row):
    return {column: row.get(column) for column in OUTPUT_COLUMNS}


def make_trace_row(row):
    trace_row = {column: row.get(column) for column in TRACEABILITY_COLUMNS}
    trace_row["filter_status"] = row.get("filter_status")
    trace_row["filter_reason"] = row.get("filter_reason")
    return trace_row


def main():
    start = time.time()
    # CAMBIO PRINCIPAL: Usar muestreo estratificado equilibrado en lugar de aleatorio
    sample = build_balanced_sample()
    sample_blocks = split_sample_into_blocks(sample, DOWNLOAD_BLOCKS)

    print(f"Muestra estratificada equilibrada: {len(sample)} PDFs")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    if os.path.exists(TRACEABILITY_FILE):
        os.remove(TRACEABILITY_FILE)

    total_kept = 0
    total_dropped = 0
    seen_dois = set()
    seen_title_years = set()

    for block_index, sample_block in enumerate(sample_blocks, 1):
        if not sample_block:
            continue

        if USE_BATCH_DOWNLOAD:
            print(f"Descargando bloque {block_index}/{len(sample_blocks)} con {len(sample_block)} PDFs...")
            batch_download_sample(sample_block)

        rows = process_sample_block(sample_block, block_index, len(sample_blocks))

        kept_rows = []
        trace_rows = []
        for row in rows:
            keep = evaluate_record(row, seen_dois, seen_title_years)
            trace_rows.append(make_trace_row(row))
            if keep:
                register_dedupe_key(row, seen_dois, seen_title_years)
                kept_rows.append(make_output_row(row))

        append_rows_to_csv(kept_rows, OUTPUT_FILE, OUTPUT_COLUMNS, write_header=(total_kept == 0))
        append_rows_to_csv(
            trace_rows,
            TRACEABILITY_FILE,
            TRACEABILITY_COLUMNS,
            write_header=(total_kept == 0 and total_dropped == 0),
        )
        total_kept += len(kept_rows)
        total_dropped += len(trace_rows) - len(kept_rows)

    elapsed = time.time() - start
    print(f"\nTiempo total (mixto balanceado): {elapsed:.2f} s")
    print(f"Tiempo medio por PDF: {elapsed / max(1, len(sample)):.2f} s")
    print(f"Registros conservados: {total_kept}")
    print(f"Registros descartados: {total_dropped}")
    print(f"Salida: {OUTPUT_FILE}")
    print(f"Trazabilidad: {TRACEABILITY_FILE}")
    print(f"Muestra guardada en: {SAMPLE_MANIFEST}")


if __name__ == "__main__":
    main()
