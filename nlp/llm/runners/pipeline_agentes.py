"""
Pipeline multi-agente UPV-EARTH: cascada de **enriquecimiento** (no de filtrado).

Objetivo: superar al baseline qwen2.5:14b v4 *en calidad*, no solo en coste.

Arquitectura:
    Agente 1 (qwen2.5:3b)    : extractor estructurado (chemical, physical,
                               biological, methodology, disciplinary_frame).
                               Output JSON, no decide nada por si solo.
    Scorer determinista       : cruza title+abstract+top_terms con
                               core/extended/applied_keywords del pb_reference.csv.
                               Cero coste, no usa LLM, no depende de keywords/journal.
    Agente 3 (qwen2.5:14b)   : prompt v4 (principle-driven) + 2 bloques de pista
                               (extraccion + scoring). Tiene MAS info que el baseline.
    Router consenso 3-de-3   : skip a None solo si Agente 1 (0 items + frame no-bio)
                               Y scorer (sin matches) coinciden. Conservador.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =============================================================================
# Rutas
# =============================================================================
ROOT_DIR = Path(__file__).resolve().parents[3]
LLM_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = LLM_DIR / "outputs" / "pipeline_cascada"
LOGS_DIR = OUTPUTS_DIR / "logs"
DEFAULT_CORPUS = ROOT_DIR / "data" / "corpus" / "master_corpus_mixto_1000_clean_enriched.csv"
DEFAULT_PB_REF = ROOT_DIR / "corpus_PB" / "data" / "pb_reference.csv"
DEFAULT_GT = LLM_DIR / "outputs" / "ground_truth" / "validacion_real.csv"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Constantes
# =============================================================================
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS = "http://localhost:11434/api/tags"
AGENT1_MODEL_DEFAULT = "qwen2.5:3b"
AGENT3_MODEL_DEFAULT = "qwen2.5:14b"
# keep_alive='10m' permite a Ollama descargar el modelo no usado si la VRAM se ajusta.
# -1 (indefinido) puede colgar el daemon si los dos modelos no caben simultaneamente.
KEEP_ALIVE = "10m"
HTTP_TIMEOUT = (10, 600)
MAX_ABSTRACT_CHARS = 8000


def preflight_check(models_required: list[str]) -> None:
    """Aborta si Ollama no responde o falta algun modelo. Evita gastar
    tiempo en 404s silenciosos como los del run anterior."""
    try:
        r = requests.get(OLLAMA_TAGS, timeout=5)
        r.raise_for_status()
    except Exception as exc:
        raise SystemExit(f"Ollama no responde en {OLLAMA_TAGS}: {exc}\n"
                         f"Arrancalo con: ollama serve")
    available = {m.get("name") for m in r.json().get("models", [])}
    missing = [m for m in models_required if m not in available]
    if missing:
        raise SystemExit(
            f"Modelos no instalados en Ollama: {missing}\n"
            f"Disponibles: {sorted(available)}\n"
            f"Descargalos con: " + " && ".join(f"ollama pull {m}" for m in missing)
        )
    logging.info("Preflight OK: %s disponibles.", models_required)

VALID_METHODOLOGY = {"measured", "modelled", "mentioned", "none"}
VALID_FRAMES = {
    "engineering", "earth_sciences", "biology", "chemistry",
    "social_sciences", "economics", "law_policy", "education", "other",
}
NON_BIO_FRAMES = {"social_sciences", "economics", "law_policy", "education"}

KW_COLS_WEIGHTS = [
    ("core_keywords", 3),
    ("extended_keywords", 2),
    ("applied_keywords_upv", 1),
]
MIN_KW_LEN = 4
MIN_PB_SCORE = 2


# =============================================================================
# Cliente Ollama
# =============================================================================
class OllamaClient:
    def __init__(self, url: str = OLLAMA_URL, timeout: tuple[int, int] = HTTP_TIMEOUT):
        self.url = url
        self.timeout = timeout
        self.session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        s = requests.Session()
        retry = Retry(
            total=3, backoff_factor=2.0,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=frozenset(["POST"]), raise_on_status=False,
        )
        s.mount("http://", HTTPAdapter(max_retries=retry))
        return s

    def generate(self, model, prompt, json_mode=False, temperature=0.0):
        payload = {
            "model": model, "prompt": prompt, "stream": False, "keep_alive": KEEP_ALIVE,
            "options": {"temperature": temperature, "top_p": 0.9},
        }
        if json_mode:
            payload["format"] = "json"
        t0 = time.perf_counter()
        r = self.session.post(self.url, json=payload, timeout=self.timeout)
        elapsed = time.perf_counter() - t0
        r.raise_for_status()
        return r.json().get("response", ""), elapsed

    def warmup(self, model):
        try:
            self.generate(model=model, prompt="ping")
        except Exception as exc:
            logging.warning("Warmup %s fallo: %s", model, exc)


# =============================================================================
# Reglas PB para el prompt del Agente 3
# =============================================================================
def build_pb_rules(df_pbs: pd.DataFrame) -> str:
    out = ""
    for _, row in df_pbs.iterrows():
        out += f"- PB Code: {row['pb_code']} ({row['pb_name']})\n"
        out += f"  * Core Definition: {row['short_definition']}\n"
        out += f"  * UPV Context: Look for terms like: {row['applied_keywords_upv']}\n"
        out += f"  * ACTIVATION LOGIC: {row['activation_logic']}\n"
        out += f"  * EXCLUSION RULE (CRITICAL): {row['exclusion_notes']}\n\n"
    return out


# =============================================================================
# Scorer determinista por overlap con pb_reference.csv (sin LLM)
# =============================================================================
def build_pb_keyword_index(df_pbs: pd.DataFrame) -> dict[str, list[tuple[re.Pattern, int, str]]]:
    index = {}
    for _, row in df_pbs.iterrows():
        entries = []
        for col, weight in KW_COLS_WEIGHTS:
            val = row.get(col)
            if pd.isna(val):
                continue
            for kw in str(val).split(";"):
                kw = kw.strip().lower()
                if len(kw) < MIN_KW_LEN:
                    continue
                rx = re.compile(r"\b" + re.escape(kw) + r"\b", flags=re.IGNORECASE)
                entries.append((rx, weight, kw))
        index[row["pb_code"]] = entries
    return index


def build_scoring_text(row: pd.Series) -> str:
    parts = [
        str(row.get("title") or ""),
        str(row.get("clean_abstract") or ""),
        str(row.get("top_terms_no_stopwords") or ""),
    ]
    return " ".join(p for p in parts if p and p != "nan")


def score_pb_overlap(text: str, index: dict) -> dict[str, dict]:
    text_l = (text or "").lower()
    out = {}
    for pb, entries in index.items():
        score = 0
        matches: list[tuple[str, int]] = []
        seen = set()
        for rx, w, kw in entries:
            if kw in seen:
                continue
            if rx.search(text_l):
                score += w
                matches.append((kw, w))
                seen.add(kw)
        out[pb] = {"score": score, "matches": matches}
    return out


def top_pb_candidates(scores: dict, n: int = 4, min_score: int = MIN_PB_SCORE) -> list:
    ranked = sorted(scores.items(), key=lambda x: -x[1]["score"])
    return [(pb, info) for pb, info in ranked[:n] if info["score"] >= min_score]


def format_kw_ranking(top_candidates: list) -> str:
    if not top_candidates:
        return "    (no PB vocabulary matched)"
    lines = []
    for pb, info in top_candidates:
        kws = ", ".join(f"{kw}(w{w})" for kw, w in info["matches"][:6])
        lines.append(f"    - {pb} (score={info['score']}): {kws}")
    return "\n".join(lines)


# =============================================================================
# Agente 1: extractor estructurado
# =============================================================================
# IMPORTANTE: este prompt NO contiene ejemplos in-line de variables.
# Razon: pruebas con llama3.2:3b mostraron que el modelo pequeno copia
# los ejemplos del prompt como si fueran datos del paper (efecto loro).
# Las definiciones son abstractas. Las pocas anclas concretas vienen
# de un dominio NO biofisico (cars, prices) que no puede colarse como
# extraccion valida.

AGENT1_PROMPT = """<system_role>
You are a fast, structured information extractor inside a multi-agent pipeline. A larger expert model runs after you. Your output enriches the next model's context; you do NOT make the final decision.
</system_role>

<task>
Read the metadata + abstract. Extract structured biophysical information into 5 fields (defined below). Every item you list must be COPIED VERBATIM from the abstract or title text below — never from these instructions.
</task>

<rules>
1. ZERO HALLUCINATION: every string in chemical_species, physical_metrics or biological_observations must be a direct substring of the <abstract> or <title> in the input. If you cannot point to it in the abstract, do NOT include it.
2. Distinguish what the paper measures/models (use those fields) from what it merely mentions in passing (do NOT extract those).
3. The disciplinary_frame is the dominant academic angle of the abstract, not the topic it discusses.
4. Empty arrays are valid and EXPECTED for non-biophysical papers. Do NOT fill them to look productive.
</rules>

<field_definitions>
- chemical_species: any chemical compound, element, ion, pollutant, gas, mineral or molecular species named in the abstract.
- physical_metrics: any measured or modelled physical or environmental variable named in the abstract (climate, energy, flow, mass, radiation, geophysical processes, etc.).
- biological_observations: any living-system observation named in the abstract (organisms, populations, ecosystems, physiology, ecological responses, etc.).
- methodology: ONE of {{"measured", "modelled", "mentioned", "none"}}.
    - "measured": the abstract reports primary or secondary empirical data.
    - "modelled": the abstract builds, runs or evaluates a model that produces values.
    - "mentioned": variables appear only as background, motivation or citation.
    - "none": no biophysical variable appears at all.
- disciplinary_frame: ONE of {{"engineering", "earth_sciences", "biology", "chemistry", "social_sciences", "economics", "law_policy", "education", "other"}}.
</field_definitions>

<self_check>
Before producing JSON, mentally verify: each string in your three arrays appears VERBATIM somewhere in the abstract below. If not, drop it.
</self_check>

<input_data>
<title>{title}</title>
<journal>{journal}</journal>
<keywords>{keywords}</keywords>
<abstract>
{abstract}
</abstract>
</input_data>

<output_format>
Return ONLY valid JSON in this exact structure (no markdown, no preamble):
{{
  "chemical_species": [],
  "physical_metrics": [],
  "biological_observations": [],
  "methodology": "measured|modelled|mentioned|none",
  "disciplinary_frame": "engineering|earth_sciences|biology|chemistry|social_sciences|economics|law_policy|education|other"
}}
</output_format>"""


@dataclass
class Agent1Result:
    raw_output: str
    chemical_species: list[str]
    physical_metrics: list[str]
    biological_observations: list[str]
    methodology: str
    disciplinary_frame: str
    elapsed_s: float
    parse_error: str | None = None
    error: str | None = None

    @property
    def n_metrics(self) -> int:
        return len(self.chemical_species) + len(self.physical_metrics) + len(self.biological_observations)

    @property
    def looks_non_biophysical(self) -> bool:
        return self.n_metrics == 0 and self.disciplinary_frame in NON_BIO_FRAMES


def _safe_keywords(row: pd.Series) -> str:
    kw = row.get("keywords")
    if pd.notna(kw) and str(kw).strip():
        return str(kw)
    fb = row.get("top_terms_no_stopwords")
    return str(fb) if pd.notna(fb) else ""


def _coerce_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()] if str(v).strip() else []


def _parse_agent1_json(raw: str) -> tuple[list, list, list, str, str]:
    s, e = raw.find("{"), raw.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("no JSON braces in response")
    data = json.loads(raw[s : e + 1])
    chem = _coerce_list(data.get("chemical_species"))
    phys = _coerce_list(data.get("physical_metrics"))
    bio = _coerce_list(data.get("biological_observations"))
    meth = str(data.get("methodology", "none")).strip().lower()
    if meth not in VALID_METHODOLOGY:
        meth = "none"
    frame = str(data.get("disciplinary_frame", "other")).strip().lower()
    if frame not in VALID_FRAMES:
        frame = "other"
    return chem, phys, bio, meth, frame


def _grounding_filter(items: list[str], grounding_text_lower: str) -> list[str]:
    """Filtra items que NO aparecen en el texto del abstract (anti-alucinacion).
    Match laxo: subcadena case-insensitive, o cualquier palabra >=4 chars en comun."""
    out = []
    for it in items:
        it_l = it.lower().strip()
        if not it_l:
            continue
        if it_l in grounding_text_lower:
            out.append(it)
            continue
        words = [w for w in re.findall(r"\w+", it_l) if len(w) >= 4]
        if words and any(w in grounding_text_lower for w in words):
            out.append(it)
    return out


def run_agent1(client: OllamaClient, model: str, row: pd.Series) -> Agent1Result:
    abstract_text = str(row.get("clean_abstract") or "")[:MAX_ABSTRACT_CHARS]
    title_text = str(row.get("title") or "")[:500]
    grounding = (title_text + " " + abstract_text).lower()

    prompt = AGENT1_PROMPT.format(
        title=title_text,
        journal=str(row.get("journal") or "(unknown)")[:200],
        keywords=_safe_keywords(row)[:500],
        abstract=abstract_text,
    )
    try:
        raw, elapsed = client.generate(model=model, prompt=prompt, json_mode=True, temperature=0.0)
    except Exception as exc:
        return Agent1Result("", [], [], [], "none", "other", 0.0, error=str(exc))
    try:
        chem, phys, bio, meth, frame = _parse_agent1_json(raw)
    except Exception as exc:
        return Agent1Result(raw, [], [], [], "none", "other", elapsed, parse_error=str(exc))

    # Anti-alucinacion: descartamos items que no esten en el abstract.
    chem = _grounding_filter(chem, grounding)
    phys = _grounding_filter(phys, grounding)
    bio = _grounding_filter(bio, grounding)

    return Agent1Result(raw, chem, phys, bio, meth, frame, elapsed)


# =============================================================================
# Agente 3: juez 14B con 3 senales
# =============================================================================
AGENT3_PROMPT_TMPL = """<system_role>
You are an expert scientific evaluator analyzing research abstracts from the Universitat Politecnica de Valencia (UPV) against the Planetary Boundaries (PBs) framework. Your judgment matters more than rigid rule-following. Use the provided framework as a reasoning aid, not a script.
</system_role>

<task>
Identify the Planetary Boundaries that the research actually MEASURES, MODELS, or treats as an EXPERIMENTAL FORCING. Cleanly separate real biophysical analysis from mere background or motivational context.
</task>

<instructions>
1. Identify the *operational object*: the exact variable being measured, modelled or experimentally manipulated. Quantification, methodology, comparisons or model outputs around a variable indicate it is the focus. Mere mention without numbers or methods is just background.
2. Match with PB: pick the PB whose Core Definition / Activation Logic matches the operational object. The *primary* PB is the one being analytically resolved, not the one mentioned in the introduction.
3. Apply EXCLUSION RULES: if the abstract is purely social, legal, governance, education, philosophy or pure-software theory and biophysical terms are only motivational, the verdict is "None".
4. Common confusions:
   - Aerosols / PM / AOD belong to PB9, not PB1.
   - PB1 requires climate to be ACTIVE: either (a) measured/modelled, or (b) imposed as treatment/scenario. Climate as motivation only is not enough.
   - Water-resources management papers with climate as motivation are PB5, not PB1.
   - Biodiversity / ecosystem responses are a legitimate primary candidate for PB7.
   - Nutrients (N, P) point to PB4.
</instructions>

<reference_framework>
{pb_rules}
</reference_framework>

<calibration_cases>
These cases share one principle: *the primary PB is whatever variable the paper quantifies or models*, regardless of the introduction's rhetorical framing. Use them ONLY to calibrate your judgment, NOT to mimic their wording.

- Case A: A paper studies the central carbon metabolism of anammox bacteria using 13C isotope tracing. Focus: Nitrogen biogeochemistry (measured). Primary PB: PB4.
- Case B: A paper verifies the WRF forecast model comparing initial conditions against radar data; mentions "changing climate" in the opening. Focus: Forecast-model accuracy. Primary PB: None.
- Case C: A paper quantifies detection data for 24 mammal species in response to human footprint. Focus: Ecological response of biodiversity. Primary PB: PB7.
- Case D: A systems-engineering framework for water-resources management, "climate destabilization" only in motivation. Focus: water-resources planning. Primary PB: PB5. PB1 rejected.
- Case E: A multi-year warming experiment driving microbial functional gene expression. Warming is imposed forcing. Primary PB: PB1. Secondary PB: PB7.
</calibration_cases>

<input_data>
<abstract>
{abstract}
</abstract>
</input_data>

<constraints>
- DO NOT reuse phrases from the calibration cases. Your abstract deserves a fresh reading.
- Write your own reasoning, citing the abstract's own terms.
- DO NOT output any markdown formatting (like ```json).
- DO NOT include any conversational text, greetings or explanations outside the JSON.
</constraints>

<auxiliary_signals_for_reference_only>
Below are two blocks produced by automatic pre-processing modules BEFORE you read the abstract. They have known failure modes and are NOT authoritative. Read the abstract first and form your judgment; only consult these if you are genuinely uncertain. NEVER let these signals override what the abstract clearly says.

  <small_extractor>
    A small (3B-parameter) extractor model scanned the abstract. It is prone to declaring `methodology=mentioned` even on papers that do measure or model variables, and to missing chemicals not on its training distribution. Treat its output skeptically.
    - chemical_species:        {a1_chem}
    - physical_metrics:        {a1_phys}
    - biological_observations: {a1_bio}
    - methodology:             {a1_meth}
    - disciplinary_frame:      {a1_frame}
  </small_extractor>

  <keyword_overlap_scorer>
    A deterministic scorer counts vocabulary overlap with pb_reference.csv. It has gaps (e.g. heavy metals are not in the PB8 vocabulary, paleoclimate terms are not in PB1). Equal-score ties between PBs are NOT meaningful; resolve them by reading the abstract.
{kw_ranking}
  </keyword_overlap_scorer>
</auxiliary_signals_for_reference_only>

<output_format>
Return ONLY valid JSON in the exact structure below:
{{
    "reasoning_process": "A very high-level summary (2-3 sentences). State exactly what is measured/modelled, why you chose this PB, and why it is not background context. Mention briefly whether the weak signals agreed or disagreed with you.",
    "primary_pb": {{"pb_code": "PBX", "confidence": "High/Medium/Low"}} or null,
    "secondary_pbs": [{{"pb_code": "PBY", "confidence": "High/Medium/Low"}}],
    "rejected_pbs": ["PBZ", "PBW"]
}}
</output_format>"""


@dataclass
class Agent3Result:
    raw_output: str
    reasoning: str
    primary_pb: str
    primary_conf: str
    secondary_pbs: str
    rejected_pbs: str
    elapsed_s: float
    error: str | None = None


def parse_agent3_json(raw: str) -> tuple[str, str, str, str, str]:
    s, e = raw.find("{"), raw.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("No JSON object in response")
    data = json.loads(raw[s : e + 1])
    reasoning = data.get("reasoning_process", "")
    pp = data.get("primary_pb")
    if isinstance(pp, dict):
        prim_code, prim_conf = pp.get("pb_code") or "None", pp.get("confidence") or "Unknown"
    else:
        prim_code, prim_conf = "None", "N/A"
    sec = data.get("secondary_pbs") or []
    sec_codes = ", ".join(it.get("pb_code", "") for it in sec if isinstance(it, dict)) or "None"
    rej = data.get("rejected_pbs") or []
    rej_codes = ", ".join(str(x) for x in rej) if rej else "None"
    return reasoning, prim_code, prim_conf, sec_codes, rej_codes


def run_agent3(client: OllamaClient, model: str, abstract: str, pb_rules: str,
               a1: Agent1Result, kw_top: list) -> Agent3Result:
    prompt = AGENT3_PROMPT_TMPL.format(
        pb_rules=pb_rules,
        a1_chem=a1.chemical_species or "[]",
        a1_phys=a1.physical_metrics or "[]",
        a1_bio=a1.biological_observations or "[]",
        a1_meth=a1.methodology,
        a1_frame=a1.disciplinary_frame,
        kw_ranking=format_kw_ranking(kw_top),
        abstract=abstract[:MAX_ABSTRACT_CHARS],
    )
    try:
        raw, elapsed = client.generate(model=model, prompt=prompt, json_mode=True, temperature=0.0)
    except Exception as exc:
        return Agent3Result("", "", "Error", "Error", "Error", "Error", 0.0, str(exc))
    try:
        reasoning, p, c, s, r = parse_agent3_json(raw)
    except Exception as exc:
        return Agent3Result(raw, "", "ParseError", "ParseError", "ParseError", "ParseError", elapsed, str(exc))
    return Agent3Result(raw, reasoning, p, c, s, r, elapsed)


# =============================================================================
# Router por consenso
# =============================================================================
def consensus_vote_skip(a1: Agent1Result, kw_top: list) -> bool:
    return a1.looks_non_biophysical and len(kw_top) == 0


# =============================================================================
# Agente 4: critic asimetrico
# =============================================================================
# Solo dispara cuando Agente 3 dice None y el scorer determinista tiene >= 1
# candidato con score >= MIN_KW_SCORE_CRITIC. Permite votar entre {None} U
# kw_top_candidates, nunca entre PBs no surgidas del scorer. Asi:
#   * Recuperar PBs perdidos cuando el 14B es demasiado conservador.
#   * No puede degradar PBx -> None (no se invoca en ese caso).
#   * No puede inventar una PB no respaldada por evidencia lexica.
#
# Evaluacion sobre los 150 papers de validacion_real:
#   pipeline base (Agentes 1+2+3) ........ 64.0% top-1
#   pipeline + Agente 4 critic ........... 65.3% top-1  (+1.3pp, 2 rescates limpios)
#   - 5194c7c1714e (gt=PB1) None -> PB1
#   - 21ecc353ac74 (gt=PB7) None -> PB7  (gracias al voto multi-candidato)
#   Sin degradacion: ningun None correcto fue roto por el critic.

MIN_KW_SCORE_CRITIC = 2

CRITIC_PROMPT = """<system_role>
You are a senior reviewer auditing a previous classification decision. The previous judge classified the abstract below as "None" (no Planetary Boundary actively studied). A complementary keyword scorer disagrees and surfaces one or more candidate PBs that share vocabulary with the abstract. Re-read the abstract WITHOUT assuming the previous None verdict was correct, and pick exactly one of: keep "None", or override to one of the candidate PBs listed below.
</system_role>

<task>
Pick ONE option from this closed set:
  - "None"  -> no PB is actively measured / modelled / imposed; the previous None was correct.
  - one of {candidates_set} -> that PB is actively studied. Active study means the paper (a) measures or quantifies that variable, (b) models or simulates it, or (c) applies it as an experimental treatment / imposed scenario / forcing to observe downstream effects.
You may NOT invent another PB.
</task>

<rules>
- Background mentions of climate / aerosols / nutrients in the introduction are NOT enough. Active study is required.
- Do NOT default to None just because the abstract is technical or dense. Specific measurements, model outputs, or imposed treatments all count as active study.
- A small extractor model also reported these structured fields (UNRELIABLE — use only as a hint, never as ground truth):
    chemical_species:        {a1_chem}
    physical_metrics:        {a1_phys}
    biological_observations: {a1_bio}
    methodology:             {a1_meth}
    disciplinary_frame:      {a1_frame}
  When the small extractor reported `methodology=mentioned` it is wrong about half the time; do not anchor on it.
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
class Agent4Result:
    raw: str
    decision: str           # 'None' o 'PBx'
    confidence: str
    reasoning: str
    elapsed_s: float
    candidates: list[str]
    error: str | None = None


def _kw_matches_for_pb(scoring_text: str, pb_row: pd.Series) -> str:
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


def _build_pb_block_for_critic(pb_code: str, pb_row: pd.Series, score: int) -> str:
    return (
        f"  pb_code: {pb_code}\n"
        f"  pb_name: {pb_row['pb_name']}\n"
        f"  Core Definition: {pb_row['short_definition']}\n"
        f"  Activation Logic: {pb_row['activation_logic']}\n"
        f"  Exclusion Rule:   {pb_row['exclusion_notes']}\n"
        f"  Scorer score: {score}"
    )


def run_agent4_critic(client: OllamaClient, model: str, row: pd.Series,
                     a1: Agent1Result, kw_top: list, df_pbs: pd.DataFrame) -> Agent4Result:
    candidates = [(pb, info["score"]) for pb, info in kw_top
                  if info["score"] >= MIN_KW_SCORE_CRITIC]
    if not candidates:
        return Agent4Result("", "None", "N/A", "no candidates", 0.0, [])
    cand_codes = [c[0] for c in candidates]
    pbs_idx = df_pbs.set_index("pb_code")
    candidate_blocks = "\n\n".join(_build_pb_block_for_critic(pb, pbs_idx.loc[pb], sc)
                                   for pb, sc in candidates)
    scoring_text = build_scoring_text(row)
    kw_matches_block = "\n".join(
        f"  {pb}: {_kw_matches_for_pb(scoring_text, pbs_idx.loc[pb])}"
        for pb, _ in candidates
    )
    candidates_set = "{" + ", ".join(f'"{c}"' for c in cand_codes) + "}"
    prompt = CRITIC_PROMPT.format(
        candidates_set=candidates_set,
        candidate_blocks=candidate_blocks,
        kw_matches_block=kw_matches_block,
        a1_chem=a1.chemical_species or "[]",
        a1_phys=a1.physical_metrics or "[]",
        a1_bio=a1.biological_observations or "[]",
        a1_meth=a1.methodology,
        a1_frame=a1.disciplinary_frame,
        abstract=str(row.get("clean_abstract") or "")[:MAX_ABSTRACT_CHARS],
    )
    try:
        raw, elapsed = client.generate(model=model, prompt=prompt, json_mode=True, temperature=0.0)
    except Exception as exc:
        return Agent4Result("", "", "Error", "", 0.0, cand_codes, str(exc))
    try:
        s, e = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[s:e + 1])
        decision_raw = str(data.get("decision", "")).strip().strip('"')
        if decision_raw.upper() in ("NONE", "KEEP_NONE"):
            decision = "None"
        elif decision_raw in cand_codes:
            decision = decision_raw
        else:
            # Decision invalida: nos quedamos con None.
            decision = "None"
        return Agent4Result(
            raw=raw,
            decision=decision,
            confidence=str(data.get("confidence", "")).strip(),
            reasoning=str(data.get("reasoning", "")).strip(),
            elapsed_s=elapsed,
            candidates=cand_codes,
        )
    except Exception as exc:
        return Agent4Result(raw, "", "ParseError", "", elapsed, cand_codes, str(exc))


# =============================================================================
# Persistencia
# =============================================================================
OUTPUT_COLUMNS = [
    "doc_id", "route",
    "agent1_model", "agent1_chemical", "agent1_physical", "agent1_biological",
    "agent1_methodology", "agent1_frame", "agent1_n_items", "agent1_raw",
    "agent1_time_s", "agent1_parse_error", "agent1_error",
    "kw_top_pbs", "kw_top_score",
    "agent3_model", "llm_primary_pb", "llm_primary_conf", "llm_secondary_pbs",
    "llm_rejected_pbs", "llm_reasoning", "agent3_time_s", "agent3_error",
    # Agente 4 (critic) — opcional. Solo poblado cuando se invoca.
    "agent4_invoked", "agent4_decision", "agent4_confidence", "agent4_reasoning",
    "agent4_candidates", "agent4_time_s", "agent4_error",
    "final_primary_pb",
    "total_time_s",
]


def load_processed_ids(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    try:
        existing = pd.read_csv(output_path, usecols=["doc_id"])
        return set(existing["doc_id"].astype(str).tolist())
    except Exception as exc:
        logging.warning("No pude leer doc_ids existentes: %s", exc)
        return set()


def append_row(output_path: Path, row: dict) -> None:
    df_row = pd.DataFrame([{c: row.get(c, "") for c in OUTPUT_COLUMNS}])
    write_header = not output_path.exists()
    df_row.to_csv(output_path, mode="a", header=write_header, index=False)


def setup_logging(log_path: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_path, encoding="utf-8")],
        force=True,
    )


# =============================================================================
# CLI
# =============================================================================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", type=Path, default=DEFAULT_CORPUS)
    p.add_argument("--pb-reference", type=Path, default=DEFAULT_PB_REF)
    p.add_argument("--output", type=Path, default=OUTPUTS_DIR / "pipeline_cascada.csv")
    p.add_argument("--agent1-model", default=AGENT1_MODEL_DEFAULT)
    p.add_argument("--agent3-model", default=AGENT3_MODEL_DEFAULT)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--no-warmup", action="store_true")
    p.add_argument("--filter-by-gt", type=Path, default=DEFAULT_GT,
                   help="CSV de ground truth (sep ';'). Por defecto, el corpus se filtra a "
                        "sus doc_ids para procesar solo los papers validados manualmente. "
                        "Pasa --no-filter-by-gt para procesar el corpus entero.")
    p.add_argument("--no-filter-by-gt", dest="filter_by_gt", action="store_const", const=None,
                   help="Desactiva el filtro por validacion_real.csv y procesa todo el corpus.")
    p.add_argument("--no-critic", action="store_true",
                   help="No invocar el Agente 4 critic (util para ablations).")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    log_path = LOGS_DIR / f"pipeline_{time.strftime('%Y%m%d_%H%M%S')}.log"
    setup_logging(log_path)
    logging.info("Log -> %s", log_path)

    if not args.input.exists():
        logging.error("No existe el CSV de entrada: %s", args.input)
        return 1
    if not args.pb_reference.exists():
        logging.error("No existe el CSV de PBs: %s", args.pb_reference)
        return 1

    df_corpus = pd.read_csv(args.input)
    df_pbs = pd.read_csv(args.pb_reference)

    needed = {"doc_id", "title", "journal", "keywords", "clean_abstract", "top_terms_no_stopwords"}
    missing = needed - set(df_corpus.columns)
    if missing:
        logging.error("Faltan columnas en el corpus: %s", missing)
        return 1

    df_corpus = df_corpus.dropna(subset=["doc_id", "clean_abstract"]).copy()
    df_corpus["doc_id"] = df_corpus["doc_id"].astype(str)

    if args.filter_by_gt:
        df_gt = pd.read_csv(args.filter_by_gt, sep=";", encoding="utf-8")
        ids = set(df_gt["doc_id"].astype(str).tolist())
        df_corpus = df_corpus[df_corpus["doc_id"].isin(ids)]
        logging.info("Filtrado por ground truth: %d papers", len(df_corpus))

    pb_rules = build_pb_rules(df_pbs)
    pb_kw_index = build_pb_keyword_index(df_pbs)
    logging.info("Reglas PB y vocabulario indexado para %d boundaries.", len(df_pbs))

    if args.no_resume and args.output.exists():
        backup = args.output.with_suffix(args.output.suffix + ".bak")
        os.replace(args.output, backup)
        logging.info("--no-resume: salida previa movida a %s", backup)

    processed = load_processed_ids(args.output)
    if processed:
        logging.info("Resume: %d doc_ids ya procesados, se omitiran.", len(processed))

    df_pending = df_corpus[~df_corpus["doc_id"].isin(processed)]
    if args.limit is not None:
        df_pending = df_pending.head(args.limit)

    total = len(df_pending)
    logging.info("Papers pendientes en este run: %d", total)
    if total == 0:
        return 0

    # Preflight: aborta si falta algun modelo (evita perder tiempo con 404s).
    preflight_check([args.agent1_model, args.agent3_model])

    client = OllamaClient()
    if not args.no_warmup:
        logging.info("Warmup de modelos...")
        client.warmup(args.agent1_model)
        client.warmup(args.agent3_model)

    counters = {"fast_skip_consensus": 0, "llm_judged": 0,
                "agent4_invoked": 0, "agent4_overrides": 0}

    for i, (_, row) in enumerate(df_pending.iterrows(), start=1):
        doc_id = row["doc_id"]
        t0 = time.perf_counter()

        # Senal 1
        a1 = run_agent1(client, args.agent1_model, row)

        # Senal 2 (gratis)
        scoring_text = build_scoring_text(row)
        kw_scores = score_pb_overlap(scoring_text, pb_kw_index)
        kw_top = top_pb_candidates(kw_scores)

        record: dict[str, Any] = {
            "doc_id": doc_id,
            "agent1_model": args.agent1_model,
            "agent1_chemical": "; ".join(a1.chemical_species),
            "agent1_physical": "; ".join(a1.physical_metrics),
            "agent1_biological": "; ".join(a1.biological_observations),
            "agent1_methodology": a1.methodology,
            "agent1_frame": a1.disciplinary_frame,
            "agent1_n_items": a1.n_metrics,
            "agent1_raw": a1.raw_output,
            "agent1_time_s": round(a1.elapsed_s, 3),
            "agent1_parse_error": a1.parse_error or "",
            "agent1_error": a1.error or "",
            "kw_top_pbs": "; ".join(f"{pb}({info['score']})" for pb, info in kw_top),
            "kw_top_score": kw_top[0][1]["score"] if kw_top else 0,
            "agent3_model": "",
            "agent3_time_s": "",
            "agent3_error": "",
        }

        if consensus_vote_skip(a1, kw_top):
            counters["fast_skip_consensus"] += 1
            record.update(
                route="fast_skip_consensus",
                llm_primary_pb="None", llm_primary_conf="ConsensusFilter",
                llm_secondary_pbs="None", llm_rejected_pbs="None",
                llm_reasoning="Consensus: Agent1 (0 items + non-bio frame) AND scorer (no PB matched).",
            )
        else:
            counters["llm_judged"] += 1
            a3 = run_agent3(client, args.agent3_model, str(row["clean_abstract"]), pb_rules, a1, kw_top)
            record.update(
                route="llm_judged",
                agent3_model=args.agent3_model,
                llm_primary_pb=a3.primary_pb, llm_primary_conf=a3.primary_conf,
                llm_secondary_pbs=a3.secondary_pbs, llm_rejected_pbs=a3.rejected_pbs,
                llm_reasoning=a3.reasoning,
                agent3_time_s=round(a3.elapsed_s, 3), agent3_error=a3.error or "",
            )

        # Salida final por defecto: la primary del Agente 3 (o ConsensusFilter).
        record["final_primary_pb"] = record.get("llm_primary_pb", "")

        # Agente 4 (critic asimetrico). Solo si:
        #   - flag --no-critic NO esta puesto
        #   - el Agente 3 dijo None
        #   - hay >=1 candidato en kw_top con score >= MIN_KW_SCORE_CRITIC
        # Solo puede pasar None -> PBx, nunca al reves.
        if (not args.no_critic
                and record.get("llm_primary_pb") == "None"
                and any(info["score"] >= MIN_KW_SCORE_CRITIC for _, info in kw_top)):
            counters["agent4_invoked"] += 1
            a4 = run_agent4_critic(client, args.agent3_model, row, a1, kw_top, df_pbs)
            record.update(
                agent4_invoked=True,
                agent4_decision=a4.decision,
                agent4_confidence=a4.confidence,
                agent4_reasoning=a4.reasoning,
                agent4_candidates=", ".join(a4.candidates),
                agent4_time_s=round(a4.elapsed_s, 3),
                agent4_error=a4.error or "",
            )
            if a4.decision and a4.decision != "None" and not a4.error:
                record["final_primary_pb"] = a4.decision
                counters["agent4_overrides"] += 1

        record["total_time_s"] = round(time.perf_counter() - t0, 3)
        try:
            append_row(args.output, record)
        except Exception as exc:
            logging.exception("Error guardando fila %s: %s", doc_id, exc)

        critic_tag = ""
        if record.get("agent4_invoked"):
            critic_tag = f" critic={record.get('agent4_decision','?')}"
        logging.info(
            "[%d/%d] %s route=%s a1_items=%d kw_top=%s a3=%s pb=%s%s -> final=%s",
            i, total, doc_id, record["route"], a1.n_metrics,
            record["kw_top_pbs"][:30] or "(none)",
            record["agent3_time_s"], record.get("llm_primary_pb", "-"),
            critic_tag, record.get("final_primary_pb", "-"),
        )

    logging.info(
        "Fin. fast_skip=%d  llm_judged=%d  agent4_invoked=%d  agent4_overrides=%d  total=%d",
        counters["fast_skip_consensus"], counters["llm_judged"],
        counters["agent4_invoked"], counters["agent4_overrides"], total,
    )
    logging.info("Resultados -> %s", args.output)

    # Resumen contra ground truth (solo si --filter-by-gt apunta a un CSV con etiquetas).
    if args.filter_by_gt:
        try:
            print_gt_summary(args.output, args.filter_by_gt)
        except Exception as exc:
            logging.warning("No se pudo imprimir el resumen vs GT: %s", exc)

    return 0


def print_gt_summary(output_path: Path, gt_path: Path) -> None:
    """Imprime accuracy y tabla pred-vs-GT cuando el filtro es un CSV con etiquetas."""
    if not output_path.exists():
        return
    res = pd.read_csv(output_path, keep_default_na=False)
    gt = pd.read_csv(gt_path, sep=";", encoding="utf-8")
    if "1stpb" not in gt.columns:
        return
    gt = gt.copy()
    gt["doc_id"] = gt["doc_id"].astype(str)
    gt["gt_pb"] = (
        gt["1stpb"]
        .astype(str).str.replace(".0", "", regex=False)
        .replace({"": "None", "nan": "None", "NaN": "None"})
        .map(lambda x: f"PB{x}" if x not in ("None",) else "None")
    )
    res["doc_id"] = res["doc_id"].astype(str)
    m = res.merge(gt[["doc_id", "gt_pb"]], on="doc_id", how="left")
    # final_primary_pb refleja el override del Agente 4 si lo hubo; cae al primary del 3 si no.
    if "final_primary_pb" in m.columns:
        m["pred"] = m["final_primary_pb"].replace({"": "None"}).fillna("None")
        m.loc[m["pred"] == "", "pred"] = m.loc[m["pred"] == "", "llm_primary_pb"].replace({"": "None"})
    else:
        m["pred"] = m["llm_primary_pb"].replace({"": "None"}).fillna("None")
    m["sec"] = m["llm_secondary_pbs"].fillna("")
    m["ok_primary"] = m["gt_pb"] == m["pred"]
    m["ok_in_top2"] = m.apply(lambda r: r["gt_pb"] == r["pred"] or r["gt_pb"] in str(r["sec"]), axis=1)

    n = len(m)
    n_ok = int(m["ok_primary"].sum())
    n_top2 = int(m["ok_in_top2"].sum())

    logging.info("=" * 70)
    logging.info("Accuracy vs GT (1st PB):     %d/%d  (%.1f%%)", n_ok, n, 100 * n_ok / n if n else 0)
    logging.info("Top-2 hit (primary or sec.): %d/%d  (%.1f%%)", n_top2, n, 100 * n_top2 / n if n else 0)
    logging.info("-" * 70)
    logging.info("%-14s %-6s %-6s %-6s %s", "doc_id", "GT", "PRED", "SEC", "")
    for _, r in m.iterrows():
        flag = "OK" if r["ok_primary"] else ("~" if r["ok_in_top2"] else "X ")
        logging.info(
            "%-14s %-6s %-6s %-6s %s",
            r["doc_id"], r["gt_pb"], r["pred"], (r["sec"] or "-")[:6], flag,
        )
    logging.info("=" * 70)


if __name__ == "__main__":
    raise SystemExit(main())
