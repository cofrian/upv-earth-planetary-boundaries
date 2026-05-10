"""Comparativa real entre SPECTER2 y SciBERT (clasificación PB).

Lee dos artefactos:

- `mockup/data/seed/precomputed/models_comparison.csv`
  Tabla generada off-line con la predicción top-1/top-2 de cada modelo
  para los 677 papers indexados, junto con la verdad de carpeta
  (`pb_folder`).
- `nlp/bert_finetuning/outputs/backbone_comparison.csv`
  Métricas oficiales del benchmark de backbones (BERT base, RoBERTa,
  SciBERT, baselines).

A partir de la primera tabla calcula métricas globales y por PB.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.corpus_loader.precomputed import file_path


def _benchmark_csv() -> Path | None:
    here = Path(__file__).resolve()
    for parents_up in range(3, 8):
        try:
            base = here.parents[parents_up]
        except IndexError:
            continue
        candidate = base / "nlp" / "bert_finetuning" / "outputs" / "backbone_comparison.csv"
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=1)
def _load_comparison() -> pd.DataFrame | None:
    target = file_path("models_comparison.csv")
    if not target:
        return None
    df = pd.read_csv(target)
    return df


@lru_cache(maxsize=1)
def _load_human() -> pd.DataFrame | None:
    target = file_path("models_comparison_human.csv")
    if not target:
        return None
    df = pd.read_csv(target)
    return df


@lru_cache(maxsize=1)
def _load_backbones() -> pd.DataFrame | None:
    target = _benchmark_csv()
    if not target:
        return None
    return pd.read_csv(target)


def reset_cache() -> None:
    _load_comparison.cache_clear()
    _load_human.cache_clear()
    _load_backbones.cache_clear()


def models_benchmark() -> dict[str, Any]:
    df = _load_comparison()
    if df is None or df.empty:
        return {
            "available": False,
            "n_papers": 0,
            "models": [],
            "per_pb": [],
            "agreement": {},
            "discordance_examples": [],
            "backbones_table": [],
        }

    n = len(df)
    df = df.copy()
    df["specter_ok"] = df["specter_pred"] == df["gt_folder"]
    df["scibert_ok"] = df["scibert_pred"] == df["gt_folder"]
    df["specter_top12_ok"] = df.apply(
        lambda r: r["gt_folder"] in [r["specter_pred"], r["specter_top2"]], axis=1
    )
    df["scibert_top12_ok"] = df.apply(
        lambda r: r["gt_folder"] in [r["scibert_pred"], r["scibert_top2"]], axis=1
    )

    def _model_summary(label: str, top1_col: str, top12_col: str) -> dict[str, Any]:
        return {
            "model": label,
            "top1_correct": int(df[top1_col].sum()),
            "top1_accuracy": round(float(df[top1_col].mean()), 4),
            "top2_correct": int(df[top12_col].sum()),
            "top2_accuracy": round(float(df[top12_col].mean()), 4),
        }

    per_pb: list[dict[str, Any]] = []
    for pb, sub in df.groupby("gt_folder", sort=True):
        per_pb.append({
            "pb_code": str(pb),
            "n": int(len(sub)),
            "specter_top1": round(float(sub["specter_ok"].mean()), 4),
            "scibert_top1": round(float(sub["scibert_ok"].mean()), 4),
            "specter_top2": round(float(sub["specter_top12_ok"].mean()), 4),
            "scibert_top2": round(float(sub["scibert_top12_ok"].mean()), 4),
        })

    agreement = {
        "both_correct": int(((df["specter_ok"]) & (df["scibert_ok"])).sum()),
        "only_specter": int(((df["specter_ok"]) & (~df["scibert_ok"])).sum()),
        "only_scibert": int(((~df["specter_ok"]) & (df["scibert_ok"])).sum()),
        "both_wrong": int(((~df["specter_ok"]) & (~df["scibert_ok"])).sum()),
    }

    # Ejemplos donde solo SPECTER acierta (top, ordenados por score)
    only_specter_df = df[(df["specter_ok"]) & (~df["scibert_ok"])].sort_values(
        "specter_score", ascending=False
    ).head(8)
    only_scibert_df = df[(~df["specter_ok"]) & (df["scibert_ok"])].sort_values(
        "specter_score", ascending=True
    ).head(8)

    def _examples(sub: pd.DataFrame) -> list[dict[str, Any]]:
        return [
            {
                "doc_id": str(row["doc_id"]),
                "gt": str(row["gt_folder"]),
                "specter_pred": str(row["specter_pred"]),
                "scibert_pred": str(row["scibert_pred"]),
                "specter_score": round(float(row["specter_score"]), 4),
            }
            for _, row in sub.iterrows()
        ]

    backbones = _load_backbones()
    backbones_table: list[dict[str, Any]] = []
    if backbones is not None and not backbones.empty:
        for _, row in backbones.iterrows():
            backbones_table.append({
                "model": str(row.get("model", "")),
                "mode": str(row.get("mode", "")),
                "micro_f1": round(float(row.get("micro_f1", 0) or 0), 4),
                "macro_f1": round(float(row.get("macro_f1", 0) or 0), 4),
                "lrap": round(float(row.get("lrap", 0) or 0), 4),
            })

    # === Validación humana multi-etiqueta ===
    human_block: dict[str, Any] = {"available": False}
    human = _load_human()
    if human is not None and not human.empty:
        # Filtros de evaluación: cada modelo solo cuenta donde tiene predicción.
        if "specter_evaluated" not in human.columns:
            human["specter_evaluated"] = human["specter_pred"].notna()
        if "scibert_evaluated" not in human.columns:
            human["scibert_evaluated"] = human["scibert_pred"].notna()

        sp_eval = human[human["specter_evaluated"]]
        sc_eval = human[human["scibert_evaluated"]]
        both_eval = human[(human["specter_evaluated"]) & (human["scibert_evaluated"])]

        nh_total = len(human)
        avg_gold = float(human["gold_count"].mean())

        examples = (
            both_eval.sort_values("specter_score", ascending=False)
            .head(10)[
                [
                    "doc_id",
                    "gold_labels_str",
                    "specter_pred",
                    "scibert_pred",
                    "specter_score",
                    "specter_top1_in_gold",
                    "scibert_top1_in_gold",
                ]
            ]
        )

        def _model_block(label: str, sub: pd.DataFrame, top1_col: str, top12_col: str) -> dict[str, Any]:
            return {
                "model": label,
                "n_evaluated": int(len(sub)),
                "top1_in_gold_correct": int(sub[top1_col].sum()),
                "top1_in_gold_accuracy": round(float(sub[top1_col].mean()) if len(sub) else 0.0, 4),
                "top12_in_gold_correct": int(sub[top12_col].sum()),
                "top12_in_gold_accuracy": round(float(sub[top12_col].mean()) if len(sub) else 0.0, 4),
            }

        human_block = {
            "available": True,
            "n_papers_total": int(nh_total),
            "n_specter_evaluated": int(len(sp_eval)),
            "n_scibert_evaluated": int(len(sc_eval)),
            "n_both_evaluated": int(len(both_eval)),
            "n_uncovered": int(nh_total - len(sp_eval) - (len(sc_eval) - len(both_eval))),
            "avg_gold_labels_per_paper": round(avg_gold, 2),
            "models": [
                _model_block("SPECTER2", sp_eval, "specter_top1_in_gold", "specter_top12_in_gold"),
                _model_block("SciBERT", sc_eval, "scibert_top1_in_gold", "scibert_top12_in_gold"),
            ],
            "agreement": {
                "n_paired": int(len(both_eval)),
                "both_top1_correct": int(
                    ((both_eval["specter_top1_in_gold"]) & (both_eval["scibert_top1_in_gold"])).sum()
                ),
                "only_specter_top1": int(
                    ((both_eval["specter_top1_in_gold"]) & (~both_eval["scibert_top1_in_gold"])).sum()
                ),
                "only_scibert_top1": int(
                    ((~both_eval["specter_top1_in_gold"]) & (both_eval["scibert_top1_in_gold"])).sum()
                ),
                "both_top1_wrong": int(
                    ((~both_eval["specter_top1_in_gold"]) & (~both_eval["scibert_top1_in_gold"])).sum()
                ),
            },
            "examples": [
                {
                    "doc_id": str(row["doc_id"]),
                    "gold": str(row["gold_labels_str"]),
                    "specter_pred": str(row["specter_pred"]),
                    "scibert_pred": str(row["scibert_pred"]),
                    "specter_score": round(float(row["specter_score"]), 4),
                    "specter_ok": bool(row["specter_top1_in_gold"]),
                    "scibert_ok": bool(row["scibert_top1_in_gold"]),
                }
                for _, row in examples.iterrows()
            ],
        }

    return {
        "available": True,
        "n_papers": n,
        "ground_truth": "pb_folder (organización del drive UPV)",
        "models": [
            _model_summary("SPECTER2", "specter_ok", "specter_top12_ok"),
            _model_summary("SciBERT", "scibert_ok", "scibert_top12_ok"),
        ],
        "per_pb": per_pb,
        "agreement": agreement,
        "discordance_examples": {
            "only_specter": _examples(only_specter_df),
            "only_scibert": _examples(only_scibert_df),
        },
        "backbones_table": backbones_table,
        "human_validation": human_block,
    }
