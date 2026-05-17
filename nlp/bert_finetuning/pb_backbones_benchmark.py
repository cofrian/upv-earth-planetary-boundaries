"""
Benchmark de Planetary Boundaries (PB) con backbones de embeddings.

Incluye:
- Tarea 7 Baseline 1: puntuacion lexico-keyword
- Tarea 7 Baseline 2: similitud semantica simple TF-IDF
- Tarea 8 Metodo principal: embeddings con BERT / RoBERTa / SciBERT

Salida:
- tabla comparativa de metricas
- predicciones por modelo para corpus y subset de validacion humana
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    f1_score,
    jaccard_score,
    label_ranking_average_precision_score,
)
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer


PB_NUMERIC_PATTERN = re.compile(r"(\d+)")


@dataclass
class EvalBundle:
    score_matrix: np.ndarray
    top1_sets: list[set[str]]
    top2_sets: list[set[str]]
    tuned_sets: list[set[str]]
    tuned_tau: float
    tuned_delta: float
    tuned_metrics: dict[str, float]
    top1_metrics: dict[str, float]
    top2_metrics: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark embeddings PB con BERT/RoBERTa/SciBERT + baselines."
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("data/corpus/master_corpus_mixto_1000_clean_enriched.csv"),
        help="CSV del corpus enriquecido.",
    )
    parser.add_argument(
        "--traceability",
        type=Path,
        default=Path("data/corpus/master_corpus_mixto_1000_traceability.csv"),
        help="CSV con trazabilidad y pb_folder.",
    )
    parser.add_argument(
        "--pb-reference",
        type=Path,
        default=Path("corpus_PB/data/pb_reference.csv"),
        help="CSV maestro PB.",
    )
    parser.add_argument(
        "--pb-docs",
        type=Path,
        default=Path("corpus_PB/data/pb_corpus_documents.csv"),
        help="CSV textual PB para similitud semantica.",
    )
    parser.add_argument(
        "--validation",
        type=Path,
        default=Path("nlp/llm/validacion_real.csv"),
        help="CSV de validacion humana multietiqueta.",
    )
    parser.add_argument(
        "--text-col",
        type=str,
        default="abstract_norm",
        help="Columna de texto para embeddings (recomendado: abstract_norm).",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="bert-base-uncased,roberta-base,allenai/scibert_scivocab_uncased",
        help="Lista de modelos HF separados por coma.",
    )
    parser.add_argument(
        "--tau-grid",
        type=str,
        default="0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.55,0.60,0.65,0.70,0.75",
        help="Valores de threshold absoluto separados por coma.",
    )
    parser.add_argument(
        "--delta-grid",
        type=str,
        default="0.00,0.01,0.02,0.04,0.06,0.08,0.10,0.12,0.15,0.20",
        help="Valores de delta respecto al score maximo separados por coma.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size para inferencia de embeddings.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=256,
        help="Longitud maxima de tokens por texto.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="cpu, cuda o auto.",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=0,
        help="Si >0, limita documentos para prueba rapida.",
    )
    parser.add_argument(
        "--clean-text",
        action="store_true",
        help="Aplica limpieza defensiva (URLs, HTML, DOIs, copyright, whitespace) al texto de entrada.",
    )
    parser.add_argument(
        "--min-text-len",
        type=int,
        default=200,
        help="Longitud minima de caracteres tras limpieza; abstracts mas cortos se descartan.",
    )
    parser.add_argument(
        "--fallback-top1",
        action="store_true",
        help="Si no pasa threshold, asigna top-1 como fallback.",
    )
    parser.add_argument(
        "--max-avg-pred-labels",
        type=float,
        default=3.5,
        help="Tope de cardinalidad media predicha en tuning de threshold (0 desactiva).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("nlp/bert_finetuning/outputs"),
        help="Directorio de salida.",
    )
    return parser.parse_args()


def parse_float_grid(grid: str) -> list[float]:
    values: list[float] = []
    for chunk in grid.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        values.append(float(chunk))
    if not values:
        raise ValueError("La grid no puede estar vacia.")
    return values


_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_HTML_RE = re.compile(r"<[^>]+>")
_HTMLENT_RE = re.compile(r"&[a-zA-Z#0-9]{2,8};")
_DOI_RE = re.compile(r"\b(?:doi[:\s]*|https?://(?:dx\.)?doi\.org/)\S+", re.IGNORECASE)
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_MULTISPACE_RE = re.compile(r"\s+")
_COPYRIGHT_RE = re.compile(r"©.*?(?:reserved|rights|elsevier|wiley|springer|mdpi|taylor)\.?",
                           re.IGNORECASE)


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_for_inference(value: object, min_len: int = 0) -> str:
    """Limpieza defensiva de abstracts antes de pasar a tokenizer.

    - Elimina URLs, emails, etiquetas HTML y entidades.
    - Quita DOIs y boilerplate de copyright editorial.
    - Normaliza espacios y caracteres de control.
    - Devuelve cadena vacia si tras limpiar queda <min_len caracteres.
    """
    if pd.isna(value):
        return ""
    txt = str(value)
    txt = _HTML_RE.sub(" ", txt)
    txt = _HTMLENT_RE.sub(" ", txt)
    txt = _URL_RE.sub(" ", txt)
    txt = _EMAIL_RE.sub(" ", txt)
    txt = _DOI_RE.sub(" ", txt)
    txt = _COPYRIGHT_RE.sub(" ", txt)
    txt = _CTRL_RE.sub(" ", txt)
    txt = _MULTISPACE_RE.sub(" ", txt).strip()
    if min_len > 0 and len(txt) < min_len:
        return ""
    return txt


def parse_pb_code(value: object) -> str | None:
    if pd.isna(value):
        return None
    txt = str(value).strip().upper()
    if txt.startswith("PB"):
        num = PB_NUMERIC_PATTERN.search(txt)
        if num:
            return f"PB{int(num.group(1))}"
        return txt
    match = PB_NUMERIC_PATTERN.search(txt)
    if match:
        return f"PB{int(match.group(1))}"
    return None


def model_slug(model_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", model_name).strip("_").lower()


def sorted_pb_codes(pb_codes: Iterable[str]) -> list[str]:
    def _key(pb: str) -> tuple[int, str]:
        match = PB_NUMERIC_PATTERN.search(pb)
        if match:
            return (int(match.group(1)), pb)
        return (999, pb)

    return sorted(pb_codes, key=_key)


def detect_device(raw: str) -> str:
    if raw != "auto":
        return raw
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_project_data(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    corpus = pd.read_csv(args.corpus)
    trace = pd.read_csv(args.traceability, usecols=["doc_id", "pb_folder", "filter_status", "filter_reason"])
    pb_docs = pd.read_csv(args.pb_docs)

    if args.text_col not in corpus.columns:
        available = ", ".join(corpus.columns)
        raise ValueError(f"No existe columna '{args.text_col}' en corpus. Disponibles: {available}")

    merged = corpus.merge(trace, on="doc_id", how="left")
    if getattr(args, "clean_text", False):
        min_len = max(0, int(getattr(args, "min_text_len", 0)))
        merged["text_input"] = merged[args.text_col].map(
            lambda v: clean_for_inference(v, min_len=min_len)
        )
        before = len(merged)
        merged = merged[merged["text_input"].str.len() > 0].copy()
        print(
            f"[INFO] Limpieza activa: descartados {before - len(merged)} abstracts "
            f"con <{min_len} chars tras limpiar."
        )
    else:
        merged["text_input"] = merged[args.text_col].map(normalize_text)
        merged = merged[merged["text_input"].str.len() > 0].copy()
    merged["pb_code_from_folder"] = merged["pb_folder"].map(parse_pb_code)
    merged["filter_status"] = merged["filter_status"].fillna("unknown")
    merged["filter_reason"] = merged["filter_reason"].fillna("")
    if args.max_docs > 0:
        merged = merged.head(args.max_docs).copy()

    needed_pb_cols = {"pb_code", "document_text", "concept_text", "applied_text"}
    missing_pb_cols = needed_pb_cols - set(pb_docs.columns)
    if missing_pb_cols:
        raise ValueError(
            f"Faltan columnas en pb_docs: {sorted(missing_pb_cols)}. Revisa {args.pb_docs}"
        )

    pb_docs = pb_docs.copy()
    pb_docs["pb_code"] = pb_docs["pb_code"].map(parse_pb_code)
    pb_docs["pb_text"] = pb_docs["document_text"].map(normalize_text)
    short_pb_text = pb_docs["pb_text"].str.len() < 20
    pb_docs.loc[short_pb_text, "pb_text"] = (
        pb_docs["concept_text"].map(normalize_text)
        + " "
        + pb_docs["applied_text"].map(normalize_text)
    ).str.strip()

    pb_docs = pb_docs[pb_docs["pb_code"].notna()].copy()
    pb_docs = pb_docs[pb_docs["pb_text"].str.len() > 0].copy()
    pb_docs = pb_docs.drop_duplicates(subset=["pb_code"]).copy()
    pb_docs = pb_docs.sort_values("pb_code").reset_index(drop=True)

    pb_reference = pd.read_csv(args.pb_reference)
    pb_reference["pb_code"] = pb_reference["pb_code"].map(parse_pb_code)
    pb_reference = pb_reference[pb_reference["pb_code"].notna()].copy()
    pb_reference = pb_reference.sort_values("pb_code").reset_index(drop=True)

    return merged, pb_docs, pb_reference


def load_validation(args: argparse.Namespace, pb_codes: list[str]) -> pd.DataFrame:
    validation = pd.read_csv(args.validation, sep=";")
    validation.columns = [c.strip() for c in validation.columns]
    label_cols = [c for c in ["1stpb", "2ndpb", "3rdpb", "4thpb", "5thpb", "6thpb"] if c in validation.columns]
    if not label_cols:
        raise ValueError("No se encontraron columnas 1stpb..6thpb en el CSV de validacion.")

    allowed = set(pb_codes)

    def _parse_row_labels(row: pd.Series) -> set[str]:
        found: set[str] = set()
        for col in label_cols:
            pb_code = parse_pb_code(row[col])
            if pb_code and pb_code in allowed:
                found.add(pb_code)
        return found

    validation["gold_labels"] = validation.apply(_parse_row_labels, axis=1)
    validation["doc_id"] = validation["doc_id"].astype(str)
    return validation


def labels_to_matrix(label_sets: list[set[str]], pb_codes: list[str]) -> np.ndarray:
    index = {pb: idx for idx, pb in enumerate(pb_codes)}
    y = np.zeros((len(label_sets), len(pb_codes)), dtype=np.int64)
    for i, labels in enumerate(label_sets):
        for label in labels:
            if label in index:
                y[i, index[label]] = 1
    return y


def multilabel_metrics(
    y_true_sets: list[set[str]],
    y_pred_sets: list[set[str]],
    pb_codes: list[str],
    score_matrix: np.ndarray | None = None,
) -> dict[str, float]:
    y_true = labels_to_matrix(y_true_sets, pb_codes)
    y_pred = labels_to_matrix(y_pred_sets, pb_codes)

    out: dict[str, float] = {
        "micro_f1": float(f1_score(y_true, y_pred, average="micro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "jaccard_samples": float(jaccard_score(y_true, y_pred, average="samples", zero_division=0)),
        "exact_match_ratio": float(np.mean(np.all(y_true == y_pred, axis=1))),
        "avg_true_labels": float(np.mean(np.sum(y_true, axis=1))),
        "avg_pred_labels": float(np.mean(np.sum(y_pred, axis=1))),
    }
    out["abs_cardinality_error"] = float(abs(out["avg_pred_labels"] - out["avg_true_labels"]))

    if score_matrix is not None:
        positive_mask = np.sum(y_true, axis=1) > 0
        if np.any(positive_mask):
            out["lrap"] = float(
                label_ranking_average_precision_score(
                    y_true[positive_mask], score_matrix[positive_mask]
                )
            )
        else:
            out["lrap"] = float("nan")
    else:
        out["lrap"] = float("nan")

    return out


def predict_top_k(score_matrix: np.ndarray, pb_codes: list[str], k: int) -> list[set[str]]:
    if score_matrix.size == 0:
        return []
    order = np.argsort(-score_matrix, axis=1)
    out: list[set[str]] = []
    for row_idx in range(score_matrix.shape[0]):
        keep = order[row_idx, :k]
        out.append({pb_codes[col_idx] for col_idx in keep})
    return out


def predict_threshold_delta(
    score_matrix: np.ndarray,
    pb_codes: list[str],
    tau_abs: float,
    delta: float,
    fallback_top1: bool,
) -> list[set[str]]:
    out: list[set[str]] = []
    for row in score_matrix:
        max_score = float(np.max(row))
        keep: set[str] = set()
        for idx, score in enumerate(row):
            if score >= tau_abs and score >= (max_score - delta):
                keep.add(pb_codes[idx])
        if not keep and fallback_top1:
            top_idx = int(np.argmax(row))
            keep = {pb_codes[top_idx]}
        out.append(keep)
    return out


def tune_thresholds(
    score_matrix: np.ndarray,
    y_true_sets: list[set[str]],
    pb_codes: list[str],
    tau_grid: list[float],
    delta_grid: list[float],
    fallback_top1: bool,
    max_avg_pred_labels: float,
) -> tuple[float, float, list[set[str]], dict[str, float]]:
    best_tuple: tuple[float, float, float] | None = None
    backup_tuple: tuple[float, float, float] | None = None
    best_tau = tau_grid[0]
    best_delta = delta_grid[0]
    best_sets: list[set[str]] = []
    best_metrics: dict[str, float] = {}
    backup_tau = tau_grid[0]
    backup_delta = delta_grid[0]
    backup_sets: list[set[str]] = []
    backup_metrics: dict[str, float] = {}

    for tau in tau_grid:
        for delta in delta_grid:
            pred = predict_threshold_delta(score_matrix, pb_codes, tau, delta, fallback_top1)
            metrics = multilabel_metrics(y_true_sets, pred, pb_codes, score_matrix)
            candidate = (
                metrics["micro_f1"],
                metrics["jaccard_samples"],
                -metrics["abs_cardinality_error"],
            )
            if backup_tuple is None or candidate > backup_tuple:
                backup_tuple = candidate
                backup_tau = tau
                backup_delta = delta
                backup_sets = pred
                backup_metrics = metrics

            if max_avg_pred_labels > 0 and metrics["avg_pred_labels"] > max_avg_pred_labels:
                continue

            if best_tuple is None or candidate > best_tuple:
                best_tuple = candidate
                best_tau = tau
                best_delta = delta
                best_sets = pred
                best_metrics = metrics

    if best_tuple is None:
        best_tau = backup_tau
        best_delta = backup_delta
        best_sets = backup_sets
        best_metrics = backup_metrics

    return best_tau, best_delta, best_sets, best_metrics


def evaluate_score_matrix(
    score_matrix_val: np.ndarray,
    y_true_sets: list[set[str]],
    pb_codes: list[str],
    tau_grid: list[float],
    delta_grid: list[float],
    fallback_top1: bool,
    max_avg_pred_labels: float,
) -> EvalBundle:
    top1_sets = predict_top_k(score_matrix_val, pb_codes, 1)
    top2_sets = predict_top_k(score_matrix_val, pb_codes, min(2, len(pb_codes)))

    top1_metrics = multilabel_metrics(y_true_sets, top1_sets, pb_codes, score_matrix_val)
    top2_metrics = multilabel_metrics(y_true_sets, top2_sets, pb_codes, score_matrix_val)

    tuned_tau, tuned_delta, tuned_sets, tuned_metrics = tune_thresholds(
        score_matrix_val,
        y_true_sets,
        pb_codes,
        tau_grid,
        delta_grid,
        fallback_top1,
        max_avg_pred_labels,
    )

    return EvalBundle(
        score_matrix=score_matrix_val,
        top1_sets=top1_sets,
        top2_sets=top2_sets,
        tuned_sets=tuned_sets,
        tuned_tau=tuned_tau,
        tuned_delta=tuned_delta,
        tuned_metrics=tuned_metrics,
        top1_metrics=top1_metrics,
        top2_metrics=top2_metrics,
    )


def encode_transformer_texts(
    texts: list[str],
    model_name: str,
    batch_size: int,
    max_length: int,
    device: str,
) -> np.ndarray:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.to(device)
    model.eval()

    vectors: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            enc = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            output = model(**enc)
            token_embeddings = output.last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1)
            masked_embeddings = token_embeddings * mask
            sum_embeddings = masked_embeddings.sum(dim=1)
            lengths = mask.sum(dim=1).clamp(min=1)
            sentence_embeddings = sum_embeddings / lengths
            sentence_embeddings = torch.nn.functional.normalize(
                sentence_embeddings, p=2, dim=1
            )
            vectors.append(sentence_embeddings.detach().cpu().numpy())

    return np.vstack(vectors)


def build_prediction_table(
    base_df: pd.DataFrame,
    score_matrix: np.ndarray,
    pb_codes: list[str],
    tau: float,
    delta: float,
    fallback_top1: bool,
) -> pd.DataFrame:
    rank = np.argsort(-score_matrix, axis=1)
    pred_top1 = [pb_codes[idx] for idx in rank[:, 0]]
    pred_top2 = [pb_codes[idx] for idx in rank[:, 1]]
    pred_multi = predict_threshold_delta(score_matrix, pb_codes, tau, delta, fallback_top1)

    out = base_df.copy()
    out["pred_top1"] = pred_top1
    out["pred_top2"] = pred_top2
    out["pred_multilabel"] = [",".join(sorted(s)) for s in pred_multi]
    out["pred_multilabel_count"] = [len(s) for s in pred_multi]
    for col_idx, pb in enumerate(pb_codes):
        out[f"score_{pb}"] = score_matrix[:, col_idx]
    return out


def parse_keywords(raw_keywords: object) -> list[str]:
    text = normalize_text(raw_keywords)
    if not text:
        return []
    chunks = [part.strip().lower() for part in text.split(";")]
    return [x for x in chunks if len(x) >= 3]


def lexical_score_matrix(
    texts: list[str],
    pb_reference: pd.DataFrame,
    pb_codes: list[str],
) -> np.ndarray:
    pb_reference = pb_reference.set_index("pb_code", drop=False)
    score = np.zeros((len(texts), len(pb_codes)), dtype=np.float32)
    lowered_texts = [text.lower() for text in texts]

    for pb_idx, pb_code in enumerate(pb_codes):
        if pb_code not in pb_reference.index:
            continue
        row = pb_reference.loc[pb_code]
        core = parse_keywords(row.get("core_keywords", ""))
        applied = parse_keywords(row.get("applied_keywords_upv", ""))

        for txt_idx, txt in enumerate(lowered_texts):
            core_hits = sum(1 for kw in core if kw in txt)
            applied_hits = sum(1 for kw in applied if kw in txt)
            score[txt_idx, pb_idx] = (2.0 * core_hits) + (1.0 * applied_hits)

    row_max = score.max(axis=1, keepdims=True)
    row_max[row_max == 0] = 1.0
    return score / row_max


def tfidf_score_matrix(texts: list[str], pb_texts: list[str]) -> np.ndarray:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        max_features=40000,
        min_df=2,
    )
    joined = texts + pb_texts
    matrix = vectorizer.fit_transform(joined)
    text_mat = matrix[: len(texts)]
    pb_mat = matrix[len(texts) :]
    return cosine_similarity(text_mat, pb_mat)


def export_model_outputs(
    out_root: Path,
    model_key: str,
    eval_bundle: EvalBundle,
    summary_rows: list[dict[str, object]],
    all_docs_df: pd.DataFrame,
    all_scores: np.ndarray,
    val_docs_df: pd.DataFrame,
    pb_codes: list[str],
    fallback_top1: bool,
) -> None:
    model_dir = out_root / model_key
    model_dir.mkdir(parents=True, exist_ok=True)

    def push_row(mode: str, metrics: dict[str, float]) -> None:
        row = {"model": model_key, "mode": mode}
        row.update(metrics)
        row["tau"] = eval_bundle.tuned_tau if mode == "threshold_delta" else np.nan
        row["delta"] = eval_bundle.tuned_delta if mode == "threshold_delta" else np.nan
        summary_rows.append(row)

    push_row("top1", eval_bundle.top1_metrics)
    push_row("top2", eval_bundle.top2_metrics)
    push_row("threshold_delta", eval_bundle.tuned_metrics)

    metrics_dump = {
        "top1": eval_bundle.top1_metrics,
        "top2": eval_bundle.top2_metrics,
        "threshold_delta": {
            "tau": eval_bundle.tuned_tau,
            "delta": eval_bundle.tuned_delta,
            **eval_bundle.tuned_metrics,
        },
    }
    (model_dir / "metrics.json").write_text(
        json.dumps(metrics_dump, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    pred_all = build_prediction_table(
        base_df=all_docs_df[["doc_id", "title", "pb_folder", "pb_code_from_folder", "filter_status", "filter_reason"]].copy(),
        score_matrix=all_scores,
        pb_codes=pb_codes,
        tau=eval_bundle.tuned_tau,
        delta=eval_bundle.tuned_delta,
        fallback_top1=fallback_top1,
    )
    pred_all.to_csv(model_dir / "predictions_all_docs.csv", index=False)

    pred_val = build_prediction_table(
        base_df=val_docs_df[["doc_id", "gold_labels"]].copy(),
        score_matrix=eval_bundle.score_matrix,
        pb_codes=pb_codes,
        tau=eval_bundle.tuned_tau,
        delta=eval_bundle.tuned_delta,
        fallback_top1=fallback_top1,
    )
    pred_val["gold_labels"] = pred_val["gold_labels"].map(lambda s: ",".join(sorted(s)))
    pred_val.to_csv(model_dir / "predictions_validation.csv", index=False)


def main() -> None:
    args = parse_args()
    device = detect_device(args.device)
    tau_grid = parse_float_grid(args.tau_grid)
    delta_grid = parse_float_grid(args.delta_grid)
    model_names = [m.strip() for m in args.models.split(",") if m.strip()]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Device: {device}")
    print(f"[INFO] Output dir: {args.out_dir}")

    corpus_df, pb_docs_df, pb_reference_df = load_project_data(args)
    pb_codes = sorted_pb_codes(pb_docs_df["pb_code"].tolist())
    pb_docs_df = pb_docs_df.set_index("pb_code").loc[pb_codes].reset_index()
    pb_texts = pb_docs_df["pb_text"].tolist()

    print(f"[INFO] Corpus docs usable: {len(corpus_df)}")
    print(f"[INFO] PB labels loaded: {pb_codes}")

    validation_df = load_validation(args, pb_codes)
    merged_val = validation_df.merge(
        corpus_df[["doc_id", "text_input"]],
        on="doc_id",
        how="inner",
    )
    missing_val = len(validation_df) - len(merged_val)
    print(
        "[INFO] Validacion humana total="
        f"{len(validation_df)} | usable_en_corpus={len(merged_val)} | missing={missing_val}"
    )

    if len(merged_val) == 0:
        raise RuntimeError("No hay documentos de validacion que coincidan con el corpus actual.")

    val_gold_sets = merged_val["gold_labels"].tolist()
    all_texts = corpus_df["text_input"].tolist()

    summary_rows: list[dict[str, object]] = []

    # Baseline 1: Lexico
    print("[INFO] Ejecutando baseline lexico...")
    lex_all_scores = lexical_score_matrix(all_texts, pb_reference_df, pb_codes)
    docid_to_pos = {doc_id: idx for idx, doc_id in enumerate(corpus_df["doc_id"].astype(str).tolist())}
    val_positions = [docid_to_pos[str(doc)] for doc in merged_val["doc_id"].tolist()]
    lex_val_scores = lex_all_scores[val_positions]

    lex_eval = evaluate_score_matrix(
        score_matrix_val=lex_val_scores,
        y_true_sets=val_gold_sets,
        pb_codes=pb_codes,
        tau_grid=tau_grid,
        delta_grid=delta_grid,
        fallback_top1=args.fallback_top1,
        max_avg_pred_labels=args.max_avg_pred_labels,
    )
    export_model_outputs(
        out_root=args.out_dir,
        model_key="baseline_lexical",
        eval_bundle=lex_eval,
        summary_rows=summary_rows,
        all_docs_df=corpus_df,
        all_scores=lex_all_scores,
        val_docs_df=merged_val,
        pb_codes=pb_codes,
        fallback_top1=args.fallback_top1,
    )

    # Baseline 2: TF-IDF semantico simple
    print("[INFO] Ejecutando baseline semantico TF-IDF...")
    tfidf_all_scores = tfidf_score_matrix(all_texts, pb_texts)
    tfidf_val_scores = tfidf_all_scores[val_positions]
    tfidf_eval = evaluate_score_matrix(
        score_matrix_val=tfidf_val_scores,
        y_true_sets=val_gold_sets,
        pb_codes=pb_codes,
        tau_grid=tau_grid,
        delta_grid=delta_grid,
        fallback_top1=args.fallback_top1,
        max_avg_pred_labels=args.max_avg_pred_labels,
    )
    export_model_outputs(
        out_root=args.out_dir,
        model_key="baseline_semantic_tfidf",
        eval_bundle=tfidf_eval,
        summary_rows=summary_rows,
        all_docs_df=corpus_df,
        all_scores=tfidf_all_scores,
        val_docs_df=merged_val,
        pb_codes=pb_codes,
        fallback_top1=args.fallback_top1,
    )

    # Modelos principales embeddings
    for model_name in model_names:
        slug = model_slug(model_name)
        print(f"[INFO] Ejecutando backbone: {model_name}")
        try:
            pb_emb = encode_transformer_texts(
                texts=pb_texts,
                model_name=model_name,
                batch_size=args.batch_size,
                max_length=args.max_length,
                device=device,
            )
            all_emb = encode_transformer_texts(
                texts=all_texts,
                model_name=model_name,
                batch_size=args.batch_size,
                max_length=args.max_length,
                device=device,
            )
        except Exception as exc:
            print(f"[WARN] Modelo omitido por error al cargar/codificar: {model_name} -> {exc}")
            continue

        all_scores = all_emb @ pb_emb.T
        val_scores = all_scores[val_positions]

        eval_bundle = evaluate_score_matrix(
            score_matrix_val=val_scores,
            y_true_sets=val_gold_sets,
            pb_codes=pb_codes,
            tau_grid=tau_grid,
            delta_grid=delta_grid,
            fallback_top1=args.fallback_top1,
            max_avg_pred_labels=args.max_avg_pred_labels,
        )
        export_model_outputs(
            out_root=args.out_dir,
            model_key=f"backbone_{slug}",
            eval_bundle=eval_bundle,
            summary_rows=summary_rows,
            all_docs_df=corpus_df,
            all_scores=all_scores,
            val_docs_df=merged_val,
            pb_codes=pb_codes,
            fallback_top1=args.fallback_top1,
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_path = args.out_dir / "backbone_comparison.csv"
    summary_df.to_csv(summary_path, index=False)

    print(f"[OK] Resumen guardado: {summary_path}")
    print("[OK] Modelos disponibles en resumen:")
    if not summary_df.empty:
        print(summary_df[["model", "mode", "micro_f1", "macro_f1", "jaccard_samples", "tau", "delta"]].to_string(index=False))
    else:
        print("No se generaron resultados (posibles errores de carga de modelos).")


if __name__ == "__main__":
    main()
