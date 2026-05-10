"""Generate report figures for the multi-agent pipeline.

Outputs PNG files into docs/report/figures/.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re
import seaborn as sns

OUT_DIR = Path(__file__).resolve().parent / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[2]


def fig1_architecture():
    """Block diagram of the cascade pipeline."""
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis("off")

    def block(x, y, w, h, label, color, sub=None):
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04",
                                       linewidth=1.5, edgecolor="black", facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.62, label, ha="center", va="center",
                fontsize=11, fontweight="bold")
        if sub:
            ax.text(x + w / 2, y + h * 0.25, sub, ha="center", va="center", fontsize=8.5)

    # Input
    block(0.2, 3.0, 1.8, 1.4, "Paper", "#e8f0fe", "title + abstract\n+ keywords")

    # Agent 1
    block(2.6, 5.0, 2.4, 1.4, "Agent 1", "#fde7d6",
          "qwen2.5:3B\nstructured extractor\nchemicals / metrics /\nbio / methodology")

    # Scorer
    block(2.6, 0.6, 2.4, 1.4, "Scorer", "#d6f0fd",
          "deterministic\nkeyword overlap\n(pb_reference.csv)")

    # Router
    block(5.7, 3.0, 1.6, 1.4, "Router", "#f0d6fd",
          "consensus\nskip vs judge")

    # fast skip
    block(5.7, 5.4, 1.6, 1.0, "fast_skip", "#cccccc",
          "→ None (no LLM)")

    # Agent 3
    block(8.0, 3.0, 2.4, 1.4, "Agent 3", "#d6fdd6",
          "qwen2.5:14B\nprinciple-driven\njudge")

    # Agent 4
    block(11.0, 3.0, 2.4, 1.4, "Agent 4 (critic)", "#fdf3d6",
          "qwen2.5:14B\nasymmetric verifier\n(fires only if A3=None\n + kw signal)")

    # Output
    block(11.0, 0.4, 2.4, 1.2, "final_primary_pb", "#e8e8ff",
          "PB1..PB9 or None")

    # Arrows
    arrow = dict(arrowstyle="->", lw=1.5)
    ax.annotate("", xy=(2.6, 5.4), xytext=(2.0, 4.2), arrowprops=arrow)
    ax.annotate("", xy=(2.6, 1.3), xytext=(2.0, 3.6), arrowprops=arrow)
    ax.annotate("", xy=(5.7, 3.7), xytext=(5.0, 5.7), arrowprops=arrow)
    ax.annotate("", xy=(5.7, 3.7), xytext=(5.0, 1.3), arrowprops=arrow)
    ax.annotate("", xy=(7.3, 5.9), xytext=(6.5, 4.4), arrowprops=arrow)  # router → fast_skip
    ax.annotate("", xy=(8.0, 3.7), xytext=(7.3, 3.7), arrowprops=arrow)  # router → agent3
    ax.annotate("", xy=(8.0, 3.5), xytext=(2.0, 3.0), arrowprops=dict(arrowstyle="->", lw=0.8, color="gray"))
    ax.annotate("", xy=(11.0, 3.7), xytext=(10.4, 3.7), arrowprops=arrow)  # agent3 → agent4
    ax.annotate("", xy=(12.2, 1.6), xytext=(12.2, 3.0), arrowprops=arrow)  # agent4 → final
    ax.annotate("", xy=(12.2, 1.6), xytext=(7.3, 5.7), arrowprops=dict(arrowstyle="->", lw=0.6, color="gray", linestyle="dashed"))

    # Labels
    ax.text(7.0, 6.6, "Cascade architecture", ha="center", fontsize=14, fontweight="bold")
    ax.text(7.0, 0.05, "Solid arrows: data flow.   Gray arrow: abstract passed directly to Agent 3.   Dashed: fast-skip bypass.",
            ha="center", fontsize=9, style="italic")

    plt.tight_layout()
    out = OUT_DIR / "fig1_architecture.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


def fig2_data_flow():
    """Sequence diagram showing per-paper data flow."""
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 10)
    ax.axis("off")

    actors = [
        ("Paper", 1.0),
        ("Agent 1\n(qwen 3B)", 3.5),
        ("Scorer\n(rules)", 5.8),
        ("Agent 3\n(qwen 14B)", 8.4),
        ("Agent 4\n(qwen 14B)", 11.2),
    ]
    for name, x in actors:
        ax.add_patch(mpatches.FancyBboxPatch((x - 0.7, 8.6), 1.4, 0.9,
                                             boxstyle="round,pad=0.04",
                                             facecolor="#f5f5f5", edgecolor="black"))
        ax.text(x, 9.05, name, ha="center", va="center", fontsize=10, fontweight="bold")
        ax.plot([x, x], [0.5, 8.6], color="lightgray", linewidth=1, linestyle=":")

    def msg(t, from_x, to_x, label, color="#1f77b4"):
        ax.annotate("", xy=(to_x, t), xytext=(from_x, t),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.4))
        mid = (from_x + to_x) / 2
        offset = 0.2 if to_x > from_x else -0.2
        ax.text(mid, t + 0.18, label, ha="center", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none"))

    msg(8.0, 1.0, 3.5, "title + abstract + kw")
    msg(7.4, 3.5, 1.0, "JSON: chemicals, metrics, bio, methodology, frame", color="#ff7f0e")
    msg(6.7, 1.0, 5.8, "title+abstract+top_terms")
    msg(6.1, 5.8, 1.0, "kw_top: PB ranking by overlap", color="#ff7f0e")
    msg(5.4, 1.0, 8.4, "abstract")
    msg(5.0, 3.5, 8.4, "Agent 1 fields", color="gray")
    msg(4.6, 5.8, 8.4, "kw_top", color="gray")
    msg(3.9, 8.4, 1.0, "primary_pb, secondary_pbs, reasoning", color="#ff7f0e")
    ax.text(7.0, 3.4, "if primary_pb == 'None' AND kw_top has score >= 2:",
            fontsize=9, style="italic", color="#7f0000")
    msg(2.9, 8.4, 11.2, "abstract + kw candidates", color="#7f0000")
    msg(2.3, 11.2, 8.4, "decision: KEEP or OVERRIDE", color="#7f0000")
    msg(1.6, 8.4, 1.0, "final_primary_pb", color="#ff7f0e")

    ax.text(6.5, 9.7, "Per-paper data flow (one paper)", ha="center", fontsize=13, fontweight="bold")
    plt.tight_layout()
    out = OUT_DIR / "fig2_data_flow.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


def fig3_compare_systems():
    """Bar chart: pipeline base vs +critic vs fewshot v4 vs zeroshot."""
    systems = ["zero-shot\n(qwen 14B)",
               "few-shot v4\n(qwen 14B, single)",
               "Pipeline\nbase (3 agents)",
               "Pipeline\n+ Agent 4 critic"]
    top1   = [0.633, 0.721, 0.640, 0.653]
    top1_pb = [0.525, 0.701, 0.606, 0.626]
    top1_none = [0.843, 0.760, 0.706, 0.706]

    x = np.arange(len(systems))
    w = 0.27
    fig, ax = plt.subplots(figsize=(11, 5.5))
    bars1 = ax.bar(x - w, top1, w, label="top-1 overall", color="#1f77b4")
    bars2 = ax.bar(x,     top1_pb, w, label="top-1 (excl. None)", color="#ff7f0e")
    bars3 = ax.bar(x + w, top1_none, w, label="top-1 (only None)", color="#2ca02c")
    for bars in (bars1, bars2, bars3):
        for b in bars:
            ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.005,
                    f"{b.get_height():.2f}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(systems)
    ax.set_ylabel("Top-1 accuracy")
    ax.set_ylim(0, 1.0)
    ax.set_title("Top-1 accuracy on the 150-paper validation set", fontsize=13, fontweight="bold")
    ax.legend(loc="lower right")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()
    out = OUT_DIR / "fig3_compare_systems.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


def fig4_confusion_matrix():
    """Confusion matrix: pipeline (with critic) primary vs gt."""
    res_path = ROOT / "nlp" / "llm" / "outputs" / "pipeline_cascada" / "pipeline_cascada_with_critic.csv"
    gt_path = ROOT / "nlp" / "llm" / "outputs" / "ground_truth" / "validacion_real.csv"
    res = pd.read_csv(res_path, keep_default_na=False)
    gt = pd.read_csv(gt_path, sep=";", encoding="utf-8")

    def to_pb(x):
        if pd.isna(x) or str(x).strip() in ("", "nan"):
            return "None"
        s = str(x).strip().replace(".0", "")
        return f"PB{s}" if s.isdigit() else s

    gt["doc_id"] = gt["doc_id"].astype(str)
    gt["gt_pb"] = gt["1stpb"].apply(to_pb)
    res["doc_id"] = res["doc_id"].astype(str)
    res["pred"] = res["final_primary_pb"].replace("", pd.NA).fillna(res["llm_primary_pb"]).replace("", "None")

    m = res.merge(gt[["doc_id", "gt_pb"]], on="doc_id").dropna(subset=["gt_pb"])
    labels = [f"PB{i}" for i in range(1, 10)] + ["None"]
    cm = pd.crosstab(m["gt_pb"], m["pred"]).reindex(index=labels, columns=labels, fill_value=0)

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax)
    ax.set_xlabel("Predicted (final_primary_pb)")
    ax.set_ylabel("Ground truth (1st PB)")
    ax.set_title(f"Confusion matrix — Pipeline + critic ({len(m)} papers)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    out = OUT_DIR / "fig4_confusion_matrix.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


def fig5_per_class_f1():
    """Per-class F1 bar chart."""
    res_path = ROOT / "nlp" / "llm" / "outputs" / "pipeline_cascada" / "pipeline_cascada_with_critic.csv"
    gt_path = ROOT / "nlp" / "llm" / "outputs" / "ground_truth" / "validacion_real.csv"
    res = pd.read_csv(res_path, keep_default_na=False)
    gt = pd.read_csv(gt_path, sep=";", encoding="utf-8")

    def to_pb(x):
        if pd.isna(x) or str(x).strip() in ("", "nan"):
            return "None"
        s = str(x).strip().replace(".0", "")
        return f"PB{s}" if s.isdigit() else s

    gt["doc_id"] = gt["doc_id"].astype(str)
    gt["gt_pb"] = gt["1stpb"].apply(to_pb)
    res["doc_id"] = res["doc_id"].astype(str)
    res["pred"] = res["final_primary_pb"].replace("", pd.NA).fillna(res["llm_primary_pb"]).replace("", "None")
    m = res.merge(gt[["doc_id", "gt_pb"]], on="doc_id").dropna(subset=["gt_pb"])

    labels = [f"PB{i}" for i in range(1, 10)] + ["None"]
    rows = []
    for lab in labels:
        tp = ((m["gt_pb"] == lab) & (m["pred"] == lab)).sum()
        fp = ((m["gt_pb"] != lab) & (m["pred"] == lab)).sum()
        fn = ((m["gt_pb"] == lab) & (m["pred"] != lab)).sum()
        support = (m["gt_pb"] == lab).sum()
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        rows.append((lab, support, prec, rec, f1))
    df = pd.DataFrame(rows, columns=["label", "support", "precision", "recall", "f1"])

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(df))
    w = 0.27
    ax.bar(x - w, df["precision"], w, label="precision", color="#1f77b4")
    ax.bar(x,     df["recall"],    w, label="recall",    color="#ff7f0e")
    ax.bar(x + w, df["f1"],        w, label="F1",        color="#2ca02c")
    for i, s in enumerate(df["support"]):
        ax.text(i, 1.02, f"n={s}", ha="center", fontsize=9, color="#444444")
    ax.set_xticks(x)
    ax.set_xticklabels(df["label"])
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score")
    ax.set_title("Per-class precision / recall / F1 — Pipeline + critic",
                 fontsize=13, fontweight="bold")
    ax.legend(loc="lower right")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()
    out = OUT_DIR / "fig5_per_class_f1.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


def fig6_pipeline_vs_v4_diff():
    """Pipeline vs few-shot v4: who wins what."""
    pipe_path = ROOT / "nlp" / "llm" / "outputs" / "pipeline_cascada" / "pipeline_cascada.csv"
    v4_path = ROOT / "nlp" / "llm" / "outputs" / "inferences" / "qwen2.5_14b_fewshot_v4_principle.csv"
    gt_path = ROOT / "nlp" / "llm" / "outputs" / "ground_truth" / "validacion_real.csv"

    def to_pb(x):
        if pd.isna(x) or str(x).strip() in ("", "nan"):
            return "None"
        s = str(x).strip().replace(".0", "")
        return f"PB{s}" if s.isdigit() else s

    gt = pd.read_csv(gt_path, sep=";", encoding="utf-8")
    gt["doc_id"] = gt["doc_id"].astype(str); gt["gt_pb"] = gt["1stpb"].apply(to_pb)
    pipe = pd.read_csv(pipe_path, keep_default_na=False)
    pipe["doc_id"] = pipe["doc_id"].astype(str); pipe["pipe"] = pipe["llm_primary_pb"].replace("", "None")
    v4 = pd.read_csv(v4_path, keep_default_na=False)
    v4["doc_id"] = v4["doc_id"].astype(str); v4["v4"] = v4["llm_primary_pb"].replace("", "None")
    m = gt[["doc_id","gt_pb"]].merge(pipe[["doc_id","pipe"]], on="doc_id").merge(v4[["doc_id","v4"]], on="doc_id")
    m["pipe_ok"] = m["pipe"] == m["gt_pb"]
    m["v4_ok"]   = m["v4"]   == m["gt_pb"]

    counts = {
        "Both correct": ((m["pipe_ok"]) & (m["v4_ok"])).sum(),
        "Only pipeline": ((m["pipe_ok"]) & (~m["v4_ok"])).sum(),
        "Only few-shot v4": ((~m["pipe_ok"]) & (m["v4_ok"])).sum(),
        "Both wrong": ((~m["pipe_ok"]) & (~m["v4_ok"])).sum(),
    }
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(counts.keys(), counts.values(),
                  color=["#2ca02c", "#1f77b4", "#ff7f0e", "#7f7f7f"])
    for b, v in zip(bars, counts.values()):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1, str(v),
                ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("Number of papers")
    ax.set_title(f"Per-paper agreement on top-1 ({len(m)} papers)",
                 fontsize=13, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()
    out = OUT_DIR / "fig6_pipeline_vs_v4.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


def fig7_critic_impact():
    """Critic decision distribution on its 6 invocations."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    cases = [
        ("5194c7c1714e\nfungi/climate",      "PB1",  "PB1",  True,  "rescued"),
        ("21ecc353ac74\nbiodiversity\nlitigation", "PB7", "PB7", True,  "rescued"),
        ("4b96859cedec\nsocial protest",     "None", "None", True,  "kept None"),
        ("fd7c9736c65e\nviral RNA",          "None", "None", True,  "kept None"),
        ("36709684add1\n(GT not in eval)",    "?",    "None", None,  "kept None"),
        ("bb87293d7644\nclimate governance", "PB1",  "None", False, "kept None\n(disagrees w/GT)"),
    ]
    xs = np.arange(len(cases))
    colors = ["#2ca02c" if c[3] is True else ("#7f7f7f" if c[3] is None else "#d62728") for c in cases]
    ax.bar(xs, [1] * len(cases), color=colors, edgecolor="black")
    for i, (lab, gt, dec, ok, note) in enumerate(cases):
        ax.text(i, 0.55, f"GT: {gt}\nA4: {dec}\n{note}", ha="center", va="center", fontsize=9.5)
        ax.text(i, -0.18, lab, ha="center", va="top", fontsize=9)
    ax.set_xlim(-0.6, len(cases) - 0.4)
    ax.set_ylim(-0.6, 1.15)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Agent 4 (critic): per-case decisions on 150-paper validation set",
                 fontsize=13, fontweight="bold")
    handles = [mpatches.Patch(color=c, label=l) for c, l in [
        ("#2ca02c", "matches GT (or correctly kept None)"),
        ("#d62728", "disagrees with GT (defensible after manual inspection)"),
        ("#7f7f7f", "outside GT eval set"),
    ]]
    ax.legend(handles=handles, loc="upper right", fontsize=9)
    plt.tight_layout()
    out = OUT_DIR / "fig7_critic_impact.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


def fig8_failure_taxonomy():
    """Stacked bar of failure modes."""
    cats = [
        ("Recall fail\n(GT=PBx → pred=None)", 15, "#d62728"),
        ("Wrong-PB selection\n(GT=PBx → pred=PBy)", 24, "#ff7f0e"),
        ("False positive\n(GT=None → pred=PBx)", 15, "#9467bd"),
    ]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar([c[0] for c in cats], [c[1] for c in cats],
                  color=[c[2] for c in cats], edgecolor="black")
    for b, c in zip(bars, cats):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.4, str(c[1]),
                ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("Number of errors")
    ax.set_title("Failure-mode taxonomy on the 150-paper validation set\n(54 total errors before critic)",
                 fontsize=13, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()
    out = OUT_DIR / "fig8_failure_taxonomy.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


if __name__ == "__main__":
    print("Generating diagrams...")
    fig1_architecture()
    fig2_data_flow()
    fig3_compare_systems()
    fig4_confusion_matrix()
    fig5_per_class_f1()
    fig6_pipeline_vs_v4_diff()
    fig7_critic_impact()
    fig8_failure_taxonomy()
    print("Done.")
