"""
Critic asimetrico retroactivo: revisa solo las filas del pipeline_cascada.csv
donde primary=None y hay senal (kw_top score >= MIN_KW_SCORE), e invoca un
prompt 'challenger' al 14B. El critic SOLO puede:
  - confirmar None (no cambiar nada), o
  - rescatar a una PB.
Nunca degrada PBx -> None. Asi reduce el riesgo asimetrico.

Justificacion (para el proyecto):
  Patron 'verifier' / 'self-critique' (Constitutional AI, debate, GPT-judge).
  Aqui es asimetrico porque la failure mode dominante del pipeline base es
  recall fail (15 PBx -> None) y precision fail en None (15 None -> PBx pero
  esos en su mayoria son ruido del GT, ver analisis).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT_DIR = Path(__file__).resolve().parents[3]
LLM_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = LLM_DIR / "outputs" / "pipeline_cascada" / "pipeline_cascada.csv"
DEFAULT_PB_REF = ROOT_DIR / "corpus_PB" / "data" / "pb_reference.csv"
DEFAULT_CORPUS = ROOT_DIR / "data" / "corpus" / "master_corpus_mixto_1000_clean_enriched.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_DEFAULT = "qwen2.5:14b"
KEEP_ALIVE = "10m"
HTTP_TIMEOUT = (10, 600)
MAX_ABSTRACT_CHARS = 8000
MIN_KW_SCORE = 3  # critic solo dispara si el scorer determinista dio >= esta puntuacion


CRITIC_PROMPT = """<system_role>
You are a senior reviewer auditing a previous classification decision. The previous judge classified the abstract below as "None" (no Planetary Boundary actively studied). A complementary keyword scorer disagrees and surfaces one or more candidate PBs that share vocabulary with the abstract. Your job is to re-read the abstract WITHOUT assuming the previous None verdict was correct, and pick exactly one of: keep "None", or override to one of the candidate PBs listed below.
</system_role>

<task>
Pick ONE option from this closed set:
  - "None"           -> no PB is actively measured / modelled / imposed; the previous None was correct.
  - "{candidates_pipe}" -> one of the candidate PBs is actively studied. Active study means the paper (a) measures or quantifies that variable, (b) models or simulates it, or (c) applies it as an experimental treatment / imposed scenario / forcing to observe downstream effects.

You may ONLY pick from {{None}} U {{{candidates_set}}}. Do NOT invent another PB.
</task>

<rules>
- Background mentions of climate / aerosols / nutrients in the introduction are NOT enough. Active study is required.
- Do NOT default to None just because the abstract is technical or dense. Specific measurements, model outputs, or imposed treatments all count as active study.
- A small extractor model reported these structured fields (UNRELIABLE — use only as a hint, never as ground truth):
    chemical_species:        {a1_chem}
    physical_metrics:        {a1_phys}
    biological_observations: {a1_bio}
    methodology:             {a1_meth}
    disciplinary_frame:      {a1_frame}
  In particular, when the small extractor reported `methodology=mentioned` it is wrong about half the time; do not anchor on it.
</rules>

<candidate_pbs>
{candidate_blocks}
</candidate_pbs>

<keyword_evidence>
{kw_matches_block}
</keyword_evidence>

<abstract>
{abstract}
</abstract>

<output_format>
Return ONLY a JSON object. No markdown.
{{
  "decision": "None" or one of {candidates_set},
  "confidence": "High" / "Medium" / "Low",
  "reasoning": "1-2 sentences. Cite the abstract's terms; explain why this PB is actively studied (or why None is correct)."
}}
</output_format>"""


@dataclass
class CriticResult:
    raw: str
    decision: str
    confidence: str
    reasoning: str
    elapsed_s: float
    error: str | None = None


def build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=2.0,
                  status_forcelist=(500, 502, 503, 504),
                  allowed_methods=frozenset(["POST"]), raise_on_status=False)
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def kw_top_parsed(s: str) -> tuple[str, int, list[tuple[str, int]]]:
    """'PB1(6); PB9(3)' -> ('PB1', 6, [('PB1',6),('PB9',3)])."""
    if not isinstance(s, str) or not s.strip():
        return ("None", 0, [])
    pairs: list[tuple[str, int]] = []
    for chunk in s.split(";"):
        m = re.match(r"\s*(PB\d)\((\d+)\)", chunk)
        if m:
            pairs.append((m.group(1), int(m.group(2))))
    if not pairs:
        return ("None", 0, [])
    return (pairs[0][0], pairs[0][1], pairs)


def get_kw_matches_for_pb(scoring_text: str, pb_row: pd.Series) -> str:
    """Lista de keywords del pb_reference que aparecen en el texto."""
    matches: list[str] = []
    for col in ("core_keywords", "extended_keywords", "applied_keywords_upv"):
        val = pb_row.get(col)
        if pd.isna(val):
            continue
        for kw in str(val).split(";"):
            kw = kw.strip().lower()
            if len(kw) >= 4 and re.search(r"\b" + re.escape(kw) + r"\b", scoring_text.lower()):
                if kw not in matches:
                    matches.append(kw)
    return ", ".join(matches[:8]) if matches else "(none)"


def build_pb_block(pb_row: pd.Series) -> str:
    pb_code = pb_row.name if pb_row.name else pb_row.get('pb_code', '')
    return (
        f"  pb_code: {pb_code}\n"
        f"  pb_name: {pb_row['pb_name']}\n"
        f"  Core Definition: {pb_row['short_definition']}\n"
        f"  Activation Logic: {pb_row['activation_logic']}\n"
        f"  Exclusion Rule:   {pb_row['exclusion_notes']}"
    )


def call_critic(session: requests.Session, model: str, prompt: str) -> CriticResult:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.0, "top_p": 0.9},
    }
    t0 = time.perf_counter()
    try:
        r = session.post(OLLAMA_URL, json=payload, timeout=HTTP_TIMEOUT)
        elapsed = time.perf_counter() - t0
        r.raise_for_status()
        raw = r.json().get("response", "")
    except Exception as exc:
        return CriticResult("", "", "", "", time.perf_counter() - t0, str(exc))
    try:
        s, e = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[s:e + 1])
        return CriticResult(
            raw=raw,
            decision=str(data.get("decision", "")).strip().upper(),
            confidence=str(data.get("confidence", "")).strip(),
            reasoning=str(data.get("reasoning", "")).strip(),
            elapsed_s=elapsed,
        )
    except Exception as exc:
        return CriticResult(raw, "", "", "", elapsed, f"parse: {exc}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output", type=Path, default=DEFAULT_INPUT.with_name("pipeline_cascada_with_critic.csv"))
    p.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    p.add_argument("--pb-reference", type=Path, default=DEFAULT_PB_REF)
    p.add_argument("--model", default=MODEL_DEFAULT)
    p.add_argument("--min-kw-score", type=int, default=MIN_KW_SCORE)
    p.add_argument("--limit", type=int, default=None,
                   help="Procesar como mucho N candidatos (util para pruebas).")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)], force=True)

    df = pd.read_csv(args.input, keep_default_na=False)
    df["doc_id"] = df["doc_id"].astype(str)
    df["pred"] = df["llm_primary_pb"].replace("", "None")
    df["agent1_n_items"] = pd.to_numeric(df["agent1_n_items"], errors="coerce").fillna(0).astype(int)

    df[["kw_top1", "kw_top1_score"]] = df["kw_top_pbs"].apply(
        lambda s: pd.Series([kw_top_parsed(s)[0], kw_top_parsed(s)[1]])
    )

    # Elegibles: pred=None Y kw_top1 score >= umbral
    eligible_mask = df["pred"].eq("None") & (df["kw_top1_score"] >= args.min_kw_score)
    eligible = df[eligible_mask].copy()
    if args.limit:
        eligible = eligible.head(args.limit)
    logging.info("Filas en input: %d  -- Elegibles para critic: %d", len(df), len(eligible))

    pbs = pd.read_csv(args.pb_reference).set_index("pb_code")
    corpus = pd.read_csv(args.corpus)[["doc_id", "title", "clean_abstract", "top_terms_no_stopwords"]]
    corpus["doc_id"] = corpus["doc_id"].astype(str)
    corpus_idx = corpus.set_index("doc_id")

    session = build_session()
    overrides: dict[str, dict] = {}
    n_override = 0
    for i, (_, row) in enumerate(eligible.iterrows(), start=1):
        doc_id = row["doc_id"]
        # Todas las PBs candidatas con score >= MIN_KW_SCORE (no solo kw_top1).
        candidates = [
            (pb, sc) for (pb, sc) in kw_top_parsed(row["kw_top_pbs"])[2]
            if sc >= args.min_kw_score and pb in pbs.index
        ]
        if not candidates or doc_id not in corpus_idx.index:
            logging.warning("[%d/%d] %s saltado (faltan datos)", i, len(eligible), doc_id)
            continue
        cand_codes = [c[0] for c in candidates]
        cr = corpus_idx.loc[doc_id]
        scoring_text = " ".join(str(cr.get(c) or "") for c in
                                ["title", "clean_abstract", "top_terms_no_stopwords"])
        candidate_blocks = "\n\n".join(
            build_pb_block(pbs.loc[pb]) + f"\n  Scorer score: {sc}"
            for pb, sc in candidates
        )
        kw_matches_block = "\n".join(
            f"  {pb}: {get_kw_matches_for_pb(scoring_text, pbs.loc[pb])}"
            for pb, _ in candidates
        )
        prompt = CRITIC_PROMPT.format(
            candidates_pipe=" or ".join(f'"{c}"' for c in cand_codes),
            candidates_set="{" + ", ".join(f'"{c}"' for c in cand_codes) + "}",
            candidate_blocks=candidate_blocks,
            kw_matches_block=kw_matches_block,
            a1_chem=row["agent1_chemical"] or "[]",
            a1_phys=row["agent1_physical"] or "[]",
            a1_bio=row["agent1_biological"] or "[]",
            a1_meth=row["agent1_methodology"] or "?",
            a1_frame=row["agent1_frame"] or "?",
            abstract=str(cr["clean_abstract"])[:MAX_ABSTRACT_CHARS],
        )
        res = call_critic(session, args.model, prompt)
        if res.error:
            logging.warning("[%d/%d] %s critic FALLO: %s", i, len(eligible), doc_id, res.error)
            continue
        # Normaliza: el critic devuelve "None" o "PBx".
        decision_raw = res.decision.strip().strip('"').upper()
        if decision_raw in ("NONE", "KEEP_NONE"):
            chosen = "None"
        elif decision_raw in cand_codes:
            chosen = decision_raw
        elif decision_raw.startswith("OVERRIDE_TO_") and decision_raw[len("OVERRIDE_TO_"):] in cand_codes:
            chosen = decision_raw[len("OVERRIDE_TO_"):]
        else:
            # Decision invalida: no overrideamos.
            chosen = "None"
        flipped = chosen != "None"
        if flipped:
            n_override += 1
        logging.info("[%d/%d] %s candidates=%s pred=None -> %s (%s, %.1fs)",
                     i, len(eligible), doc_id, ",".join(cand_codes), chosen, res.confidence, res.elapsed_s)
        overrides[doc_id] = {
            "critic_decision": chosen if chosen != "None" else "KEEP_NONE",
            "critic_confidence": res.confidence,
            "critic_reasoning": res.reasoning,
            "critic_target_pb": chosen if chosen != "None" else "",
            "critic_candidates": ",".join(cand_codes),
            "critic_time_s": round(res.elapsed_s, 3),
        }

    # Escribe CSV con columnas critic_* anadidas y final_primary_pb (override si aplica).
    df["critic_decision"]   = df["doc_id"].map(lambda d: overrides.get(d, {}).get("critic_decision", ""))
    df["critic_confidence"] = df["doc_id"].map(lambda d: overrides.get(d, {}).get("critic_confidence", ""))
    df["critic_reasoning"]  = df["doc_id"].map(lambda d: overrides.get(d, {}).get("critic_reasoning", ""))
    df["critic_target_pb"]  = df["doc_id"].map(lambda d: overrides.get(d, {}).get("critic_target_pb", ""))
    df["critic_candidates"] = df["doc_id"].map(lambda d: overrides.get(d, {}).get("critic_candidates", ""))
    df["critic_time_s"]     = df["doc_id"].map(lambda d: overrides.get(d, {}).get("critic_time_s", ""))
    df["final_primary_pb"] = df.apply(
        lambda r: r["critic_target_pb"] if r["critic_target_pb"] else r["pred"],
        axis=1,
    )

    df.drop(columns=["pred"], inplace=True)
    df.to_csv(args.output, index=False)
    logging.info("Overrides aplicados: %d / %d candidatos", n_override, len(eligible))
    logging.info("CSV escrito: %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
