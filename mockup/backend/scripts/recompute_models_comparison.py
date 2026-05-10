"""Genera comparativas SPECTER2 vs SciBERT por paper.

Produce dos artefactos en `mockup/data/seed/precomputed/`:

- `models_comparison.csv`
  SPECTER2 vs SciBERT vs `pb_folder` (carpeta drive UPV) sobre los
  papers indexados. Pseudo-verdad: la organización del drive.

- `models_comparison_human.csv`
  SPECTER2 vs SciBERT vs etiquetas humanas multi-etiqueta de
  `nlp/llm/outputs/ground_truth/validacion_real.csv`. Verdad real
  hecha por revisión humana. Solo papers con `1stpb` etiquetado.

Ejecución:
    python -m scripts.recompute_models_comparison
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.corpus_loader.precomputed import file_path, writable_dir
from app.services.embedding_service.service import embed_texts
from app.services.pb_inference.service import load_pb_catalog


def _repo_file(*parts: str) -> Path | None:
    here = Path(__file__).resolve()
    for parents_up in range(3, 8):
        try:
            base = here.parents[parents_up]
        except IndexError:
            continue
        candidate = base.joinpath(*parts)
        if candidate.exists():
            return candidate
    return None


def _scibert_csv() -> Path | None:
    return _repo_file(
        "nlp",
        "bert_finetuning",
        "outputs",
        "backbone_allenai_scibert_scivocab_uncased",
        "predictions_all_docs.csv",
    )


def _human_validation_csv() -> Path | None:
    return _repo_file("nlp", "llm", "outputs", "ground_truth", "validacion_real.csv")


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1, norms)


def main() -> None:
    npy = file_path("embeddings.npy")
    meta_path = file_path("embeddings_meta.json")
    if not (npy and meta_path):
        raise SystemExit("Faltan embeddings precomputados (.npy/.json)")

    matrix = np.load(npy).astype(np.float32)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    doc_ids = meta["doc_ids"]
    print(f"Corpus indexado: {matrix.shape}")

    catalog = load_pb_catalog()
    pb_codes = [item["pb_code"] for item in catalog]
    pb_vecs = embed_texts([item["text"] for item in catalog]).astype(np.float32)
    print(f"Catálogo PB: {pb_vecs.shape}")

    sim = _normalize(matrix) @ _normalize(pb_vecs).T  # N × 9
    top_idx = sim.argmax(axis=1)
    sorted_idx = np.argsort(-sim, axis=1)
    top2_idx = sorted_idx[:, 1]

    specter = pd.DataFrame(
        {
            "doc_id": doc_ids,
            "specter_pred": [pb_codes[i] for i in top_idx],
            "specter_top2": [pb_codes[i] for i in top2_idx],
            "specter_score": [float(sim[r, top_idx[r]]) for r in range(len(doc_ids))],
        }
    )

    sci_path = _scibert_csv()
    if not sci_path:
        raise SystemExit("No se encontró el CSV de predicciones SciBERT.")
    sci = pd.read_csv(sci_path)[["doc_id", "pb_code_from_folder", "pred_top1", "pred_top2"]].rename(
        columns={
            "pred_top1": "scibert_pred",
            "pred_top2": "scibert_top2",
            "pb_code_from_folder": "gt_folder",
        }
    )

    merged = sci.merge(specter, on="doc_id", how="inner")
    merged["specter_ok"] = merged["specter_pred"] == merged["gt_folder"]
    merged["scibert_ok"] = merged["scibert_pred"] == merged["gt_folder"]

    out = writable_dir() / "models_comparison.csv"
    merged.to_csv(out, index=False)
    print(f"[carpeta drive ] Filas comparadas: {len(merged)}  →  {out}")
    print(
        f"  SPECTER top1 acc: {merged['specter_ok'].mean():.3f}  "
        f"SciBERT top1 acc: {merged['scibert_ok'].mean():.3f}"
    )

    # === Comparativa contra validación humana multi-etiqueta ===
    val_path = _human_validation_csv()
    if not val_path:
        print("[validación humana] CSV no encontrado, se omite.")
        return

    val = pd.read_csv(val_path, sep=";")
    val.columns = [c.strip() for c in val.columns]
    val["doc_id"] = val["doc_id"].astype(str)

    label_cols = [c for c in ["1stpb", "2ndpb", "3rdpb"] if c in val.columns]

    def _to_pb(value: object) -> str | None:
        if pd.isna(value):
            return None
        try:
            return f"PB{int(value)}"
        except (TypeError, ValueError):
            return None

    def _row_labels(row: pd.Series) -> list[str]:
        labels: list[str] = []
        for col in label_cols:
            pb = _to_pb(row[col])
            if pb and pb not in labels:
                labels.append(pb)
        return labels

    val["gold_labels"] = val.apply(_row_labels, axis=1)
    val_with_labels = val[val["gold_labels"].map(len) > 0][["doc_id", "gold_labels"]].copy()
    print(f"[validación humana] Total con 1stpb anotado: {len(val_with_labels)}")

    # 1) SPECTER cubre los del índice precomputed.
    specter_extended = specter.copy()
    indexed_ids = set(specter["doc_id"].astype(str))
    missing_for_specter = val_with_labels[~val_with_labels["doc_id"].isin(indexed_ids)]
    print(f"[validación humana] Sin embedding SPECTER precalculado: {len(missing_for_specter)}")

    # 2) Recuperar embeddings on-the-fly para los faltantes que sí están
    #    en el CSV enriquecido (aunque no pasaran el filtro de 500 chars).
    if len(missing_for_specter) > 0:
        from app.services.corpus_loader.service import load_bundle

        enriched = load_bundle().enriched
        if not enriched.empty:
            enriched["doc_id"] = enriched["doc_id"].astype(str)
            need_ids = set(missing_for_specter["doc_id"])
            recoverable = enriched[enriched["doc_id"].isin(need_ids)].copy()
            print(f"[validación humana] Recuperables del CSV enriquecido: {len(recoverable)}")
            if len(recoverable) > 0:
                # Embed con SPECTER on-the-fly. Texto = title + abstract.
                title_col = "title_clean" if "title_clean" in recoverable.columns else "title"
                abstract_col = (
                    "clean_abstract_semantic"
                    if "clean_abstract_semantic" in recoverable.columns
                    else "abstract_norm"
                )
                texts = (
                    recoverable[title_col].fillna("").astype(str)
                    + " "
                    + recoverable[abstract_col].fillna("").astype(str)
                ).tolist()
                extra_emb = embed_texts(texts).astype(np.float32)
                extra_sim = _normalize(extra_emb) @ _normalize(pb_vecs).T
                extra_top = extra_sim.argmax(axis=1)
                extra_top2 = np.argsort(-extra_sim, axis=1)[:, 1]
                extra_df = pd.DataFrame(
                    {
                        "doc_id": recoverable["doc_id"].tolist(),
                        "specter_pred": [pb_codes[i] for i in extra_top],
                        "specter_top2": [pb_codes[i] for i in extra_top2],
                        "specter_score": [
                            float(extra_sim[r, extra_top[r]]) for r in range(len(recoverable))
                        ],
                    }
                )
                specter_extended = pd.concat([specter_extended, extra_df], ignore_index=True)
                print(f"[validación humana] Embeddings añadidos al vuelo: {len(extra_df)}")

    # 3) Cruce final: union de papers donde haya AL MENOS una predicción.
    sci_for_human = sci[["doc_id", "scibert_pred", "scibert_top2"]]
    human = (
        val_with_labels.merge(specter_extended, on="doc_id", how="left")
        .merge(sci_for_human, on="doc_id", how="left")
    )
    n_total = len(human)
    n_specter = human["specter_pred"].notna().sum()
    n_scibert = human["scibert_pred"].notna().sum()
    n_both = ((human["specter_pred"].notna()) & (human["scibert_pred"].notna())).sum()
    print(
        f"[validación humana] Total: {n_total}  · "
        f"con SPECTER: {n_specter}  · con SciBERT: {n_scibert}  · ambos: {n_both}"
    )

    def _in_gold(pred: object, gold: list[str]) -> bool:
        if isinstance(pred, str) and pred in gold:
            return True
        return False

    def _any_in_gold(preds: list[object], gold: list[str]) -> bool:
        return any(isinstance(p, str) and p in gold for p in preds)

    human["specter_top1_in_gold"] = human.apply(
        lambda r: _in_gold(r["specter_pred"], r["gold_labels"]), axis=1
    )
    human["scibert_top1_in_gold"] = human.apply(
        lambda r: _in_gold(r["scibert_pred"], r["gold_labels"]), axis=1
    )
    human["specter_top12_in_gold"] = human.apply(
        lambda r: _any_in_gold([r["specter_pred"], r["specter_top2"]], r["gold_labels"]), axis=1
    )
    human["scibert_top12_in_gold"] = human.apply(
        lambda r: _any_in_gold([r["scibert_pred"], r["scibert_top2"]], r["gold_labels"]), axis=1
    )
    human["specter_evaluated"] = human["specter_pred"].notna()
    human["scibert_evaluated"] = human["scibert_pred"].notna()
    human["gold_count"] = human["gold_labels"].map(len)
    human["gold_labels_str"] = human["gold_labels"].map(lambda lst: ",".join(lst))

    out_human = writable_dir() / "models_comparison_human.csv"
    cols = [
        "doc_id",
        "gold_labels_str",
        "gold_count",
        "specter_pred",
        "specter_top2",
        "specter_score",
        "scibert_pred",
        "scibert_top2",
        "specter_top1_in_gold",
        "scibert_top1_in_gold",
        "specter_top12_in_gold",
        "scibert_top12_in_gold",
        "specter_evaluated",
        "scibert_evaluated",
    ]
    human[cols].to_csv(out_human, index=False)
    print(f"[validación humana] Volcado: {out_human}")

    sp_eval = human[human["specter_evaluated"]]
    sc_eval = human[human["scibert_evaluated"]]
    print(
        f"  SPECTER  top1∈gold: {sp_eval['specter_top1_in_gold'].mean():.3f}  "
        f"({sp_eval['specter_top1_in_gold'].sum()}/{len(sp_eval)})"
    )
    print(
        f"  SciBERT  top1∈gold: {sc_eval['scibert_top1_in_gold'].mean():.3f}  "
        f"({sc_eval['scibert_top1_in_gold'].sum()}/{len(sc_eval)})"
    )
    print(
        f"  SPECTER  top1+top2∈gold: {sp_eval['specter_top12_in_gold'].mean():.3f}  "
        f"  SciBERT  top1+top2∈gold: {sc_eval['scibert_top12_in_gold'].mean():.3f}"
    )


if __name__ == "__main__":
    main()
