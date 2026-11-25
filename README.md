# priorauth — FHIR prior-authorization agent (Da Vinci CRD/DTR/PAS-inspired)

See `ideation.md` for the plan. Not clinically validated; not CMS-0057-F compliant; not for real decisions.

## What exists (Phase 0–3 skeleton, one policy end to end)
- `policies/lumbar_mri.json` — **illustrative** criteria + questionnaire items (paraphrased, NOT from a real LCD yet; Phase 0 task: replace with criteria summarised from a real MCD policy).
- `fhir_gen.py` — synthetic FHIR R4 bundles with exact ground truth and planted traps (note-only evidence, conflicting onset dates, old-MRI distractor, prompt injection).
- `baseline.py` — rule/FHIRPath-style extractor over structured resources (abstains/zeroes on note-only evidence).
- `dtr_agent.py` — structured-first, LLM-over-notes fallback; every LLM answer needs a citation that `citations.py` verifies (quote must occur in the cited resource); injection-like notes are quarantined.
- `policy.py` / `router.py` — three-valued criterion verdicts (MET / NOT_MET / INSUFFICIENT_EVIDENCE); **never auto-deny** — only fully-met + clean evidence is auto-approved, else HUMAN_REVIEW; JSONL audit log.
- `evaluate.py` — field accuracy, citation validity, abstention correctness, automation rate, auto-approval precision.

## Run
```
python -m venv .venv && .venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\priorauth eval --n 300 --llm none          # structured baseline
.venv\Scripts\priorauth eval --n 300 --llm mock          # harness test only
$env:GROQ_API_KEY="..."; .venv\Scripts\priorauth eval --n 300 --llm groq --model openai/gpt-oss-120b
```

## Results so far (300 synthetic cases)
| run | field acc | citation validity | automation | auto-approve precision |
|---|---|---|---|---|
| structured baseline | 0.925 | 1.0 | 0.397 | 1.0 |
| mock LLM (regex test double) | 1.0 | 1.0 | 0.53 | 1.0 |

The mock row only shows the harness works — it is **not** a model result. The generator is clean and the traps are few, so these
numbers say nothing about real-world accuracy. Real numbers need a Groq/Gemini run (not done yet).

## Next
1. Phase 0: pick 3–5 real MCD policies, read licence terms, rewrite criteria (summaries + IDs only).
2. Swap in Synthea/HAPI FHIR for realistic records; harder traps (outdated evidence, contradictory notes, paraphrased note wording).
3. Real LLM run + injection ablation; BM25/embedding/hybrid retrieval once policies are long enough to need it; risk–coverage curve.
4. Reviewer UI (Streamlit); reuse `../h-biomedical-mcp-suite` rxnorm/trials tools for terminology lookup.
