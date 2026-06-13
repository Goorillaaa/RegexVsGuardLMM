# The Guardrail Comparison — Regex vs Guard LLM

Course project for *LLM Security & Privacy*. We compare two output-moderation defenses
on their ability to flag **unsafe model responses**, trading detection quality against
speed and cost.

> **Framing:** *the attack is an unsafe response presented to the filter.* Both defenses
> receive a model response and classify it as `safe` or `unsafe`. They are evaluated on a
> self-generated, out-of-distribution (OOD) test set of jailbroken responses.

## The two defenses

| | Defense A | Defense B |
|---|---|---|
| **Name** | Regex / blocklist filter | Guard LLM |
| **Model** | hand-curated regular expressions | Qwen2.5-0.5B fine-tuned (LoRA) |
| **Output** | binary verdict | verdict + continuous score |
| **Strength** | microsecond latency | catches obfuscated / paraphrased cases |
| **Cost** | ~0 | GPU at inference |

The point of the comparison is the **trade-off curve**: the regex is a step function that
collapses on obfuscation, while the Guard LLM degrades gracefully but costs latency.

## Repository structure

```
guardrail-comparison/
├── README.md
├── requirements.txt
├── common/
│   ├── interface.py        # shared classify() contract for both filters
│   ├── schema.py           # test-set schema + validation
│   └── utils.py            # seed, file hashing, latency benchmark
├── data/                   # CSV + canonical split (on Drive, git-ignored)
├── defense_regex/          # Defense A: blocklist + RegexDefense
├── defense_llm/            # Defense B: training script + checkpoint (Phase 2)
├── attacks/
│   └── test_set.jsonl      # generated OOD test set (Phase 3)
├── eval/
│   └── harness.py          # runs both filters on the test set (Phase 4)
├── report/                 # report + slides (Phase 5)
└── notebooks/
    ├── 00_setup.ipynb
    └── 01_eda_regex.ipynb
```

## Setup (Google Colab)

Colab Free **wipes the filesystem** every session, so code lives on GitHub and heavy files
live on Google Drive. Run this as the first cell each session:

```python
from google.colab import drive
drive.mount('/content/drive')

!git clone https://github.com/<YOUR_USER>/guardrail-comparison.git
%cd guardrail-comparison
!pip install -q -r requirements.txt
```

> Phases 0 and 1 need **no GPU** — set the Colab runtime to CPU to preserve your daily
> GPU quota for Phase 2 onward.

### Where things live

- **Code** → GitHub (cloned each session).
- **Source CSV, canonical train/test split, model checkpoints** → Google Drive (git-ignored).
- **Attack test set (`attacks/test_set.jsonl`)** → versioned in git (it is the key
  reproducibility artifact). Because it contains unsafe content, **keep this repo private.**

## The interface contract

Both defenses implement the same `Defense.classify(response_text)` method, returning the
same `ClassificationResult` (`verdict`, `score`, `latency_ms`, `matched_rule`). This lets
the two tracks be built in parallel and turns the Phase 4 harness into a simple loop:

```python
for f in [regex_defense, llm_defense]:
    result = f.classify(response_text)
```

## Roadmap

| Phase | What | GPU | Status |
|---|---|---|---|
| 0 | Setup: repo, contract, schema, data integrity check | no | — |
| 1 | EDA + Defense A (regex), canonical split, latency | no | — |
| 2 | Defense B: fine-tune Qwen2.5-0.5B, freeze checkpoint | light | — |
| 3 | Generate OOD attack test set (self-jailbreaking) | light | — |
| 4 | Comparative evaluation: detection, FP rate, latency | no | — |
| 5 | Report + slides | no | — |

## Team & roles

- **Track A** — *(name)*: Guard LLM (Phase 2) + evaluation harness (Phase 4).
- **Track B** — *(name)*: regex filter (Phase 1) + attack generation (Phase 3).

**Sync points:** end of Phase 1 (regex interface ready), end of Phase 2 (LLM interface
ready), start of Phase 4 (test set frozen). Track B can start preparing attack generation
as soon as the canonical split exists, without waiting for the regex to be finished.

## Reproducibility

- Global seed fixed via `common.utils.set_seed(42)`.
- Source CSV verified by row count + SHA-256 hash (`common.utils.file_hash`).
- **One** canonical train/test split, stratified by category, saved on Drive and reused by
  both the regex term-mining and the LLM training (no leakage).
- Frozen artifacts are tagged in git (e.g. `fase1-regex-frozen`); after a freeze the
  blocklist / checkpoint is never edited.
- Latency for both defenses is measured with the same `benchmark_latency` helper.

## Notebooks discipline

Notebooks are committed (they are code), but clear cell outputs before committing — or run
`pip install nbstripout && nbstripout --install` once so outputs are stripped automatically.
This avoids huge diffs and merge conflicts when two people work on the same notebooks.
