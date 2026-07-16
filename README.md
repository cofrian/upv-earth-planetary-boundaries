# UPV-EARTH — Mapping University Research onto the Planetary Boundaries

Classifying 31,634 scientific abstracts from the Universitat Politècnica de València
against the nine **Planetary Boundaries**, using lexical baselines, scientific
transformer embeddings, a locally-hosted LLM, and an auditable agent cascade — with a
web platform that makes every result reviewable.

> **Degree Final Work — BSc Data Science, ETSINF, Universitat Politècnica de València (2025–2026).**
> Full report: [`docs/report/UPV-EARTH_report.pdf`](docs/report/UPV-EARTH_report.pdf)

---

## Table of contents

- [Why this project exists](#why-this-project-exists)
- [Headline results](#headline-results)
- [Quickstart](#quickstart)
- [Repository layout](#repository-layout)
- [Methodology](#methodology)
  - [1. Corpus construction](#1-corpus-construction)
  - [2. Exploratory analysis](#2-exploratory-analysis-what-does-the-upv-actually-publish)
  - [3. The PB ontology](#3-the-pb-ontology-what-counts-as-evidence)
  - [4. Baselines and transformers](#4-baselines-and-transformers)
  - [5. LLM classification](#5-llm-classification-zero-shot--v4)
  - [6. The agent cascade](#6-the-agent-cascade)
  - [7. The platform](#7-the-platform)
- [Economics of inference](#economics-of-inference)
- [Reproducing the results](#reproducing-the-results)
- [Limitations](#limitations)
- [Authors](#authors)

---

## Why this project exists

The **Planetary Boundaries** framework defines nine Earth-system processes that regulate
the stability of the planet and delimit a "safe operating space" for humanity. It matters
because it moves the conversation from vague environmental concern to *biophysical limits*.
As of the 2023 assessment, **six of the nine boundaries have been transgressed**, and Novel
Entities was already assessed as outside the safe zone.

Universities increasingly need to justify their environmental contribution — but
institutional sustainability claims require evidence. Knowing that the UPV "publishes on
sustainability" is not enough; the useful question is **which Earth-system processes its
research actually studies**.

That question is deceptively hard, and this is the central methodological problem of the project:

> A paper can be *about* sustainability without studying a planetary boundary, and a paper
> can advance a boundary without ever using SDG language. Words like *climate*, *water*,
> *biodiversity* or *pollution* routinely appear as background, motivation or application
> context — not as the thing the paper measures.

So keyword matching over-fires, and a naive LLM is worse: it happily labels anything that
*sounds* sustainable. The whole pipeline is built around the tension between two errors:

| Error | Meaning | Cost |
|---|---|---|
| **Positivity bias** | Assigning a PB to generic sustainability papers | Inflates the university's apparent environmental contribution |
| **False negatives** | Missing genuine PB evidence expressed indirectly | Understates real research strengths |

The nine boundaries, as operationalised here:

| | Boundary | | Boundary |
|---|---|---|---|
| **PB1** | Climate Change | **PB6** | Land-System Change |
| **PB2** | Ocean Acidification | **PB7** | Biosphere Integrity |
| **PB3** | Stratospheric Ozone Depletion | **PB8** | Novel Entities |
| **PB4** | Biogeochemical Flows | **PB9** | Atmospheric Aerosol Loading |
| **PB5** | Freshwater Use | | |

---

## Headline results

**Validation set:** 98 expert-annotated papers carrying 130 PB labels (98 primary + 32 secondary).

### Lexical and embedding baselines

Multi-label validation at each model's optimal threshold:

| Model | Predicted | Correct | Precision | Recall | F1 | Top-3 coverage |
|---|---|---|---|---|---|---|
| **TF-IDF** | 91 | 67 | 0.74 | 0.51 | **0.61** | **80.0%** |
| Keyword (lexical) | 60 | 48 | **0.80** | 0.37 | 0.51 | 60.0% |
| SPECTER | 119 | 63 | 0.53 | 0.49 | 0.51 | 70.8% |
| BERT-base | 163 | 67 | 0.41 | 0.52 | 0.46 | 74.6% |
| SciBERT | 218 | 80 | 0.37 | **0.62** | 0.46 | 79.2% |
| RoBERTa-base | 98 | 14 | 0.14 | 0.11 | 0.12 | 46.2% |

**The counter-intuitive result: TF-IDF beats every transformer.** Two reasons, and both are
about the task rather than the models. First, scientific abstracts state PB terminology
explicitly (*nitrogen*, *aragonite saturation*, *aerosol optical depth*). Second, the PB
reference documents are themselves keyword and phrase lists — so TF-IDF compares two
representations *of the same nature*.

The transformers were used **without task-specific fine-tuning**: mean-pooling
`last_hidden_state` turns them into generic feature extractors with no supervised
projection into PB label space. SciBERT illustrates the failure mode — it has the best
recall (0.62) but emits 218 labels against 130 real ones (~1.7× the target cardinality),
collapsing precision to 0.37. RoBERTa's embedding space collapses outright, with high
cosine similarity between unrelated classes.

### LLM classification

Local model selection (zero-shot protocol, earlier benchmark — not directly comparable to v1–v4):

| Model | Flexible agreement | Rigorousness | Positivity bias | Mean time |
|---|---|---|---|---|
| Llama 3.1 8B | 60.27% | **0.00%** | 10.96% | 3.08 s/doc |
| **Qwen 2.5 14B** | 52.05% | 38.36% | **0.00%** | 6.12 s/doc |
| Gemma 4 26B | 47.95% | **39.73%** | **0.00%** | 22.90 s/doc |

Llama was fastest with the highest agreement, but **0.00% rigorousness** — it never properly
rejected irrelevant documents, which is disqualifying for institutional mapping. Gemma
reasoned well but at 22.9 s/doc was too slow to iterate over a corpus. **Qwen 2.5 14B** was
the defensible compromise: fast enough, able to abstain, and reliable at structured JSON.

Prompt evolution (150 evaluated rows):

| Version | Key change | Top-1 | Positivity bias |
|---|---|---|---|
| Zero-shot | PB rules + exclusions + JSON | 63.3% | 15.7% |
| v1 contrastive | Rigid Q/A examples | 58.5% | 16.0% |
| v2 CoT | Mandatory deductive checklist | 63.9% | 46.0% |
| v3 focus filter | Context vs. real focus | 64.6% | 22.0% |
| **v4 principle** | **Operational object + calibration cases** | **72.1%** | 24.0% |

The evolution is the interesting part, not the final number:

- **v1 made things worse.** Adding examples *hurt* — the model reused prompt phrasing and PB7 collapsed as a class.
- **v2 bought recall with bias.** Top-1 rose, but it assigned a PB to nearly half of all human-`None` documents. Unusable for institutional mapping.
- **v3 fixed the bias, lost the recall.**
- **v4 broke the trade-off.** Its rule: identify the **operational object** — the variable the abstract actually *measures, models or experimentally manipulates* — and pick the primary PB from that, not from the narrative framing of the introduction.

That v4 improved accuracy *without* returning to v2's permissiveness is the evidence that
the operational-object principle changed the model's **reasoning**, rather than just making
it more willing to assign labels. A paired comparison against v3 over 147 evaluable rows
confirms this is not an aggregate artefact: **v4 corrected 15 documents that v3 got wrong,
while v3 won only 4** (both correct in 91, both wrong in 37).

### Final systems

| System | Top-1 | PB-only | None-only | Pos. bias | Verdict |
|---|---|---|---|---|---|
| **Qwen v4 (single model)** | **72.1%** | 70.1% | **76.0%** | **24.0%** | Best compact classifier |
| Agent cascade | 71.3% | **71.7%** | 70.6% | 29.4% | Less accurate, more traceable |

**The honest conclusion: the agent cascade does not beat v4.** It trades ~1 point of Top-1
for intermediate traces you can audit. v4 remains the best single-model solution; the
cascade is preferable only when human review and auditability outrank raw accuracy.

**The headline finding of the whole LLM stage:** the largest quality gain came from
*defining the scientific decision criterion correctly* — not from model size.

---

## Quickstart

The full platform (FastAPI + Next.js + Nginx) runs in containers, so it needs no Python or
Node on the host — only Docker. Works identically on Windows, macOS and Linux.

```bash
docker compose up -d --build
```

Then open **<http://localhost:8080>**.

| Service | Image | Role |
|---|---|---|
| `backend` | `python:3.11-slim` | FastAPI API + PDF→PB pipeline (SQLite, no GPU) |
| `frontend` | `node:20-alpine` | Next.js UI |
| `nginx` | `nginx:1.27-alpine` | Reverse proxy, publishes port `8080` |

The database is SQLite and the SPECTER2 embeddings are **precomputed and committed**, so the
dashboard, paper explorer and similarity search work immediately after startup. **No GPU required.**

<details>
<summary><b>Optional: the RAG chatbot (needs ~9 GB)</b></summary>

The chatbot is served by Ollama and is **off by default**; the rest of the platform works
without it (the UI shows "Chatbot unavailable").

```bash
docker compose --profile llm up -d          # start the Ollama container
docker compose exec ollama ollama pull qwen2.5:14b   # one-time model download
```

Use a different model with `OLLAMA_MODEL=llama3.1:8b docker compose --profile llm up -d`.
</details>

<details>
<summary><b>Optional: native install without Docker</b></summary>

| OS | Setup | Launch |
|---|---|---|
| Linux / macOS | `./setup.sh` | `./launch.sh` |
| Windows | `.\setup.ps1` | `.\launch.ps1` |

`setup` is idempotent: it detects the OS and package manager, installs Python 3.11, Node 20+
and Ollama, creates `.venv/`, installs backend and frontend dependencies, and pulls the model.
`launch` starts Ollama (`11434`), the backend (`8000`) and the frontend (`3000`), waits for
health checks, and supports `stop` / `status` / `restart`. Then open <http://localhost:3000>.

Windows requires `winget` and, once:
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
</details>

<details>
<summary><b>Troubleshooting</b></summary>

| Symptom | Cause | Fix |
|---|---|---|
| `permission denied ... docker.sock` | User not in `docker` group | `sudo usermod -aG docker "$USER"`, then re-login |
| Port 8080 busy | Another service | Change the mapping in `docker-compose.yml` (`"8081:80"`) |
| First `up` is slow | Pulling base images | Normal once; later runs use the cache |
| Chatbot "unavailable" | Missing `llm` profile or model | Start with `--profile llm` and `ollama pull` |
| Ports 3000/8000 busy (native) | Stale processes | `./launch.sh stop`, or `BACKEND_PORT=8080 FRONTEND_PORT=3001 ./launch.sh` |
</details>

---

## Repository layout

```
.
├── data/corpus/           Versioned corpus (see "Reproducing" for scope)
├── pipeline/              Corpus extraction + EDA (runnable from any cwd)
│   ├── extract_corpus.py         PDF → cleaned abstracts, dedup, traceability
│   ├── extract_corpus_balanced.py  Balanced-sampling variant
│   └── analyze_corpus_eda.py     EDA: enrichment, figures, tables
├── corpus_PB/             PB ontology: reference matrix + activation/exclusion rules
│   ├── data/pb_reference.csv     The 9 boundaries, keywords, activation logic
│   └── docs/                     Methodology + human-readable PB reference (ES/EN)
├── nlp/
│   ├── bert_finetuning/   Lexical, TF-IDF and transformer baselines + metrics
│   └── llm/               Prompts, runners (zero-shot → v4), agent cascade, analysis
├── mockup/                The web platform
│   ├── backend/           FastAPI, /api/v1, 16 service modules
│   ├── frontend/          Next.js + React + TypeScript + Tailwind + Recharts
│   ├── data/seed/         SQLite seed + precomputed SPECTER2 embeddings
│   ├── AGENTS.md          Engineering contract (see "The platform")
│   └── DESIGN.md          Interface contract
├── notebooks/             Exploratory notebooks
├── scripts/               EDA figure generation, service helpers
├── docs/                  Report, EDA outputs, architecture, guides
└── launch-video/          Remotion promo video (not part of the pipeline)
```

---

## Methodology

The pipeline is deliberately ordered so that **each stage answers a limitation of the
previous one**. It should not be read as a set of independent exercises.

| Stage | Answers | Why it comes here |
|---|---|---|
| Corpus construction | What can be analysed? | Defines the empirical base and its limits |
| EDA | What does the UPV publish? | Prevents interpreting models without knowing the corpus |
| PB ontology | What counts as PB evidence? | Prevents generic sustainability labelling |
| Baselines + transformers | Is semantic proximity enough? | Tests transparent alternatives first |
| LLM classifier | Can explicit reasoning + abstention do better? | Shows why reasoning helps but isn't sufficient alone |
| Agent cascade | Can we see *why* a PB fired? | Adds auditability to the LLM decision |
| Platform | Can this be used institutionally? | Turns a pipeline into a product |
| Economic analysis | Can it be operated for real? | Evaluates feasibility beyond model quality |

This ordering follows a principle worth stating explicitly: **the task was defined before the
technique**. The project did not start from *"which LLM should we use?"* but from *"what
evidence is needed to decide whether a paper addresses a Planetary Boundary?"*

### 1. Corpus construction

Consolidated from the shared UPV-EARTH drive: bibliographic records, PDF-derived
extractions and intermediate CSV exports.

| Stage | Records | What happened |
|---|---:|---|
| Raw consolidated | 44,970 | Initial universe |
| After duplicate control | 44,593 | DOI-based dedup + title-year matching for records without DOI |
| After structural filters | 31,634 | Minimum abstract length, language, completeness |
| Usable for inference | 31,560 | Final inference-oriented cleaning |

The filter was **intentionally conservative** — the goal was not to maximise rows but to
retain documents with enough textual evidence to support a defensible PB call. Note *where*
the loss happens: the big drop is from **text quality, not deduplication**. That is
methodologically preferable. A three-line abstract may well contain climate vocabulary
while lacking the research object, variable or mechanism needed to assign a boundary
responsibly. The final cleaning removed only 75 further documents (~0.24%), confirming
most unusable cases were already caught upstream.

Metadata was judged by the same standard: DOI is useful but incomplete, keywords too
sparse to carry semantics, and journal/author fields contain extraction artefacts. So the
**cleaned abstract is the evidence unit**; year, title and DOI are the reliable metadata;
everything else is contextual.

### 2. Exploratory analysis: what does the UPV actually publish?

Run *before* any modelling, for a specific reason: a boundary can grow in absolute terms
simply because the university publishes more. Absolute volume is therefore reported
alongside a **normalised** yearly profile, which separates genuine thematic change from
corpus growth.

**The UPV is a climate–atmosphere–territory university.** Its profile is not flat:

- **PB1 (Climate Change)** dominates — energy systems, emissions, thermal behaviour, transport, materials, environmental modelling.
- **PB9 (Aerosols)** adds a strong air-quality and atmospheric-measurement component.
- **PB6 (Land-System Change)** captures remote sensing, land cover, urban systems, soil, spatial planning.
- Water arrives through **two distinct channels** — PB2 (marine, carbonate, seawater) and PB5 (basins, rivers, irrigation). Both contain "water" vocabulary but refer to different mechanisms.
- **PB3** and **PB4** are smaller but coherent specialised niches.

Two findings deserve strategic reading rather than a ranking reading:

- **PB5 (Freshwater Use) is only moderate** — surprising for a Mediterranean university with historical irrigation and water-management links. This is either a real institutional gap *or* an absorption effect into PB1, PB4 and PB6.
- **PB8 (Novel Entities) is weak** despite the global relevance of plastics, synthetic chemicals and nanomaterials — making it a strategic area for monitoring.

**Term evolution** reveals three waves: a *pandemic* wave (lockdown, covid, sars-cov → mobility,
air quality, aerosols), a *circular-transition* wave (circularity, batteries, nature-based), and
a *machine-learning* wave (few-shot, pre-trained) — the last being the very methodology this
project uses.

**An internal validity check:** PB co-occurrences are scientifically plausible — ozone↔aerosols,
biogeochemical flows↔freshwater, land-system change↔biosphere integrity. The assignment
recovers real Earth-system couplings rather than merely reproducing frequent words.

### 3. The PB ontology: what counts as evidence

To stop the system labelling anything green, each boundary has explicit **activation** and
**exclusion** rules ([`corpus_PB/data/pb_reference.csv`](corpus_PB/data/pb_reference.csv)).
The exclusion rules carry most of the weight:

| PB | Activated when… | Excluded when… |
|---|---|---|
| **PB1** Climate | Technologies explicitly linked to GHG emissions, radiative forcing, climate scenarios/impacts | Generic energy-efficiency studies with no warming metric or climate mechanism |
| **PB2** Ocean Acidification | Marine acidity, carbonate chemistry, ocean pH, aragonite saturation | General coastal/marine/fisheries research with no pH or carbonate effect |
| **PB3** Stratospheric Ozone | Stratospheric ozone chemistry, ODS | Tropospheric ozone, urban air quality, ground-level pollution |

The nine boundaries are also grouped into three interpretive families — atmosphere–climate
(PB1, PB2, PB3, PB9), land–water–biosphere (PB5, PB6, PB7) and chemical/biogeochemical
pressure (PB4, PB8). This is a **reading aid only**; it never replaces the boundary-specific rules.

### 4. Baselines and transformers

Scored identically across all six models so results are directly comparable
(see [Headline results](#headline-results)).

- **Keyword matching** — `Score = 2 × core_hits + 1 × applied_hits`, row-normalised. The conservative lower bound: highest precision (0.80), but recall of only 0.37.
- **TF-IDF** — abstracts and PB reference docs as TF-IDF bags of words, 1–2 n-grams, ≤40,000 features; cosine similarity per PB. **The overall winner.**
- **Transformers** — BERT-base, RoBERTa-base, SciBERT (1.14M Semantic Scholar papers) and SPECTER (triplet loss over the citation graph), all mean-pooled and **not fine-tuned**.

Fine-tuning SPECTER with contrastive learning on the annotated examples would likely improve
ranking substantially — that remains future work, gated on having enough annotations.

### 5. LLM classification: zero-shot → v4

The transformers show how far semantic similarity goes; PB classification also needs a
**scientific judgement about the operational object**. The LLM does not replace the
ontology — it *applies* it, through explicit reasoning, exclusion rules and abstention.

The final v4 prompt is built from these blocks:

| Block | Function |
|---|---|
| System role | Strict but flexible scientific evaluator of the PB framework |
| Operational object | Restricts classification to PBs actively measured, modelled or manipulated |
| Exclusion rules | Blocks PB activation from generic climate/sustainability/water/biodiversity mentions |
| Common confusions | Enforces aerosols→PB9, nutrients→PB4, *measured* biodiversity→PB7 |
| Calibration cases | Calibrate decision boundaries **without being copyable examples** (the v1 lesson) |
| JSON output | Standardises `primary_pb`, `secondary_pbs`, `rejected_pbs`, `reasoning` |

**Error diagnosis.** The confusion matrix is treated as part of model quality, not as an
afterthought — because *where* a model fails determines whether you can trust it:

| Error family | ~Cases | Interpretation |
|---|---:|---|
| PBx → None | 14 | v4 stays conservative; misses PB1/PB7 when the signal is indirect |
| None → PBx | 12 | Partly positivity bias — but some may be **debatable ground truth** |
| PB1 → PB9 | 3 | Often *defensible*: climate-framed papers whose measured object is aerosols/PM/AOD |
| PB7 → None | 3 | PB7 is hard when biodiversity is conceptual rather than measured |

**The errors are not random** — they concentrate in scientifically plausible difficulty zones
(abstention, the PB1/PB9 frontier, PB7 recognition). That is the strongest signal that v4
learned a meaningful part of the PB decision structure. The `None` row holds 0.76 accuracy,
and boundaries with crisp technical vocabulary (PB4, PB8, PB9) show high diagonals.

Note that PB1→PB9 is not simply a bug: under the operational-object criterion, a paper
*motivated* by climate change but *measuring* particulate matter or aerosol optical depth
makes PB9 defensible. The confusion identifies a real scientific boundary between
**motivation and measured variable**.

### 6. The agent cascade

Built for **traceability, not accuracy** — separating literal extraction, lexical evidence,
scientific judgement and asymmetric review:

| Block | Function | Failure control |
|---|---|---|
| **Extractor** | Pulls species, metrics, observations, disciplinary frame | Accepts only strings **literally present** in the abstract |
| **Scorer** | Deterministic PB ranking from vocabulary | Provides evidence; **never decides** |
| **Router** | Skips the judge when extractor and scorer agree on irrelevance | Fast-skip only under strong consensus toward `None` |
| **Judge** | Qwen 14B with v4 logic + auxiliary signals | Signals explicitly marked fallible, to reduce anchoring |
| **Critic** | Reviews `None` cases with lexical candidates | **Can only flip None → PBx**, never downgrade |

The critic's asymmetry is the key design decision: letting a second pass downgrade any PB
to `None` would risk losing relevant papers, so restricting it to `None → PBx` makes it a
*controlled recovery mechanism* rather than a second source of false negatives.

### 7. The platform

A three-tier prototype that turns the pipeline into something a university user can review:

```
Frontend                    Backend                Local LLMs
Next.js + React    ──REST/SSE──▶  FastAPI    ──HTTP──▶  Ollama Qwen 14B
TypeScript + Tailwind         16 service modules        vLLM Qwen3-8B
Recharts                      /api/v1

Persistence              Precomputed artefacts      Storage
SQLite / PostgreSQL      EDA JSON                   PDF uploads
papers, jobs, PB results SPECTER2 embeddings        job files
                         2D projection              indexed corpus
        Nginx reverse proxy (upload limits + TLS) ──▶ UPV browser (VPN)
```

Five functional blocks: a **dashboard** (corpus KPIs and layers — deliberately distinguishing
the raw collection from the indexed SPECTER2 subset), an **EDA module**, a **paper explorer**,
an **upload page** running live inference on a new PDF, and a **strict RAG assistant**.

Two deliberate choices are worth calling out:

**The RAG assistant explains; it never classifies.** It is constrained to already-computed
results and corpus evidence, so the LLM cannot silently replace the deterministic classifier.

**A result is never shown as a single opaque label.** The user can inspect the cleaned
abstract, the PB profile, the similarity context, the pipeline stage the paper entered, and
the contextual explanation. Institutional sustainability claims should be traceable, not
just visually attractive.

**On AI-assisted development.** The platform was built through *controlled* AI-assisted
development, not an open-ended "build me a dashboard" request. Two Markdown contracts
constrained generation: [`mockup/DESIGN.md`](mockup/DESIGN.md) fixed the interface language
(dark scientific system, emerald accent, hierarchy, card layout, table style, loading states);
[`mockup/AGENTS.md`](mockup/AGENTS.md) fixed the engineering logic (backend modules, `/api/v1`
routing, async PDF flow, SPECTER2 embeddings, persistence, strict RAG behaviour). AI
accelerated implementation and refactoring; the team retained responsibility for
requirements, screen meaning, visible pipeline stages and safe LLM use.

---

## Economics of inference

The project does not train a foundation model — **the economically relevant operation is
inference**, repeated over a large corpus every time the prompt changes. The analysis
separates three layers: reference infrastructure (documented but not charged, since the
workstation already existed), marginal inference cost, and deployment cost (a dashboard and
database do **not** need a permanent GPU).

**Local inference, full corpus (31,634 papers) with `qwen2.5:14b`:**

| Metric | Value |
|---|---|
| Time per document | 6.12 s |
| Energy per document | 0.236 Wh |
| Total active inference | ~54 hours |
| Total GPU energy | 7.5 kWh |
| **Marginal electricity cost** @ 0.15 €/kWh | **≈ €1.12** |

That figure is the *additional* cost of running the classification on hardware that already
exists — not the cost of owning the workstation.

**Commercial APIs, same corpus:** ≈ **€20.78** (Gemini Flash-Lite), ≈ **€62.33** (GPT mini),
≈ **€80.24** (Claude Haiku, standard mode). Batch modes are cheaper but are not equivalent to
interactive use, since the user gets no immediate answer.

**The recommendation flips depending on the scenario** — which is the actual point:

| Scenario | Preferred | Reason |
|---|---|---|
| Repeated experimentation / prompt iteration | **Local workstation** | Very low marginal cost per run |
| Full-corpus reclassification | **Local workstation** | ~54 h and ~€1.12 of measured GPU electricity |
| Cloud app, low/moderate traffic | **Commercial API** | Avoids operating a GPU service |
| Cloud inference, one paper per request | **API, not a GPU** | Per-minute GPU billing beats the API only in batches |
| Privacy-sensitive or batched institutional processing | **Local / dedicated GPU** | Model control and data locality outweigh per-call cost |

---

## Reproducing the results

### What is in this repository

> **Scope note — read this before running the pipeline.**
> `data/corpus/` contains the **1,000-document mixed sample** from the earlier project phase
> (1,000 sampled → **700 retained** after cleaning, plus the full 1,000-row traceability
> table). The **31,634-document institutional corpus** described in the report is *not*
> redistributed here: it derives from a private UPV Drive and third-party publisher PDFs.
> The committed sample is enough to run and verify the EDA and the baselines end-to-end;
> reproducing the full-corpus figures requires access to the original drive.

Also committed and immediately usable: the **PB ontology** (`corpus_PB/`), all
**baseline metrics and predictions** (`nlp/bert_finetuning/outputs*/`), **LLM inference
outputs** (`nlp/llm/outputs/`), and **precomputed SPECTER2 embeddings** for the platform.

### Run the EDA

Scripts are anchored to the repository root, so they run from **any** working directory:

```bash
pip install -e .                       # or: uv sync
python pipeline/analyze_corpus_eda.py  # → docs/eda/ + enriched corpus CSV
```

Override any path if needed:

```bash
python pipeline/analyze_corpus_eda.py \
  --input data/corpus/corpus_1000_clean.csv \
  --trace data/corpus/corpus_1000_traceability.csv \
  --out-dir docs/eda
```

### Rebuild the corpus from source PDFs

Requires [`rclone`](https://rclone.org/) configured against the source drive:

```bash
rclone lsf upv_drive: --recursive --files-only --include "*.pdf" > muestras/listado_pdfs.txt
RCLONE_REMOTE="your_remote:path/" python pipeline/extract_corpus.py
```

This downloads in blocks, extracts text with PyMuPDF, cleans and deduplicates, writes a
traceability table, and runs the EDA. It is resumable — `rclone --ignore-existing` skips
already-downloaded PDFs, so an interrupted run can simply be relaunched.

### Reproduce the LLM experiments

Needs Ollama with `qwen2.5:14b` (~9 GB, GPU strongly recommended):

```bash
ollama pull qwen2.5:14b
python nlp/llm/runners/qwen_zeroshot.py     # zero-shot baseline
python nlp/llm/runners/qwen_fewshot_v2.py   # prompt iterations
python nlp/llm/runners/pipeline_agentes.py  # agent cascade
```

Prompts live in `nlp/llm/prompts/`; analysis notebooks in `nlp/llm/analysis/`.

---

## Limitations

These are part of the result, not a disclaimer. **UPV-EARTH is a structured and traceable
approximation to the environmental profile of UPV research — not an absolute measurement
of impact.**

- **Abstract-level evidence.** Some papers address a boundary in the full text but express it only indirectly in the abstract; others use sustainability language without enough biophysical evidence to activate one.
- **Heterogeneous data quality.** The corpus mixes bibliographic records and PDF extractions, so journal, author and keyword fields are unevenly reliable — hence the priority given to cleaned abstracts.
- **Small ground truth.** 98 annotated papers is small against 31,634, and some PB assignments are inherently ambiguous — Freshwater Use, Biogeochemical Flows, Biosphere Integrity and Climate Change genuinely overlap in real papers. **Errors may reflect interpretive difficulty as much as model limitation.**
- **Single annotator.** Expanding the validated set with multiple annotators is the highest-value next step.

**Appropriate use:** institutional screening, exploration, reporting and strategic review.
**Not appropriate:** mechanical certification of a single paper's environmental impact
without human review.

### Future work

1. Expand the annotated set with multiple annotators to reduce ground-truth ambiguity.
2. Fine-tune SPECTER or a scientific transformer on the PB task once annotations suffice.
3. Add authentication, persistent vector search and batch processing for larger uploads.
4. Extend beyond research articles — teaching guides, project reports, inter-university comparison.

---

## Documentation

| Document | Contents |
|---|---|
| [Full report (PDF)](docs/report/UPV-EARTH_report.pdf) | The complete study: methodology, results, appendices |
| [PB methodology](corpus_PB/docs/corpus_pb_methodology.pdf) | How the PB corpus and ontology were built |
| [PB reference (ES](corpus_PB/docs/pb_reference_readable_es.pdf) / [EN)](corpus_PB/docs/pb_reference_readable_en.pdf) | Human-readable boundary definitions |
| [Corpus extraction flow](docs/flujo_extraccion_1000.md) | The 1,000-document pipeline in detail |
| [Embedding inputs](docs/bert_embeddings_inputs.md) | Which columns to use for embeddings, and which not to |
| [Stratified sampling](docs/MUESTREO_ESTRATIFICADO.md) | Sampling strategy for the annotated subset |
| [`mockup/AGENTS.md`](mockup/AGENTS.md) · [`mockup/DESIGN.md`](mockup/DESIGN.md) | The engineering and design contracts |

---

## Authors

Degree Final Work, BSc Data Science — Escola Tècnica Superior d'Enginyeria Informàtica,
Universitat Politècnica de València, 2025–2026.

Fernando Martínez Gómez · Luis Trigueros Espada · **Sergio Ortiz Montesinos** ·
Sergio Domínguez Miró · Maria Montolio Maximiano · Alba Sanahuja Batalla

This is a six-author team project. Machine-readable metadata for all authors is in
[`CITATION.cff`](CITATION.cff) — GitHub renders it as a "Cite this repository" button.

### Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) enforces the properties this
repository claims, rather than just linting:

- The EDA runs **from an unrelated working directory**, proving the scripts are anchored to the repo root and not to the caller's cwd.
- Its outputs and the enriched corpus are checked to exist and be non-empty.
- Corpus integrity: 700 cleaned documents, 1,000 traceability rows, unique `doc_id`.
- No developer-specific absolute paths (`/home/<user>/…`) in runnable code.
- `docker-compose.yml` validates.

### Acknowledgements and references

The Planetary Boundaries framework: Rockström et al. (2009); Steffen et al. (2015);
Richardson et al. (2023). Models: BERT (Devlin et al., 2019), RoBERTa (Liu et al., 2019),
SciBERT (Beltagy et al., 2019), SPECTER (Cohan et al., 2020). Full bibliography in the report.
