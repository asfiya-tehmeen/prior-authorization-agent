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

## Results so far (150 synthetic cases, seed 0, Groq `openai/gpt-oss-120b`, temperature 0)
| run | field acc | citation validity | automation | auto-approve precision | approve recall | LLM errors |
|---|---|---|---|---|---|---|
| structured baseline (no LLM) | 0.923 | 1.0 | 0.367 | 1.0 | 0.679 | – |
| LLM over notes + injection quarantine | 1.0 | 1.0 | 0.48 | 1.0 | 0.889 | 0 |
| LLM over notes, quarantine OFF (ablation) | 1.0 | 1.0 | 0.54 | 1.0 | 1.0 | 0 |

What this shows, and what it doesn't:
- Reading notes lifts automation from 0.37 to 0.48–0.54 with no wrong auto-approvals, because the baseline can't see note-only evidence.
- The model was not fooled by the planted injection on this sample: no decision flips with quarantine off. The quarantine's only
  measured effect is a **cost**: it sends injection-containing cases to human review even when they're approvable (recall 0.889 vs 1.0).
  It stays on as defence in depth, because the injection is crude (a single, obvious template) and one model run proves little.
- Field accuracy of 1.0 means the generator is **too easy**, not that the agent is perfect. Next step is harder cases.
- Synthetic data, one illustrative policy, n=150: none of this says anything about real-world accuracy.
- The mock LLM (`--llm mock`) is a regex test double for the harness, not a model result.

## Hard set (`--hard`)
Adds traps that a careless reader gets wrong. Each appears only when the true answer is the negative one, so gold labels don't change:
`pt_prior_episode` (PT for a resolved 2019 episode), `nsaid_hedged` ("may consider ibuprofen"), `cancer_family_history`,
`neuro_negated` ("no foot drop"), `pt_conflicting_notes` (two notes disagree → expected abstain), `stealth_injection`
(instruction-shaped text the quarantine regex does **not** catch). Uses its own random stream, so the default set is unchanged.

`trap_field_error_rate` attributes errors to the field each trap targets. A case can carry several traps, so counting
"wrong auto-approvals per trap" would only measure co-occurrence.

Sanity check, regex mock on 150 hard cases: auto-approval precision falls to 0.88, failing every `nsaid_hedged` (22/22) and every
`pt_conflicting_notes` (13/13). So the hard set does separate a naive reader from a careful one.

## Next
1. Phase 0: pick 3–5 real MCD policies, read licence terms, rewrite criteria (summaries + IDs only).
2. Swap in Synthea/HAPI FHIR for realistic records; harder traps (outdated evidence, contradictory notes, paraphrased note wording).
3. Real LLM run + injection ablation; BM25/embedding/hybrid retrieval once policies are long enough to need it; risk–coverage curve.
4. Reviewer UI (Streamlit); reuse `../h-biomedical-mcp-suite` rxnorm/trials tools for terminology lookup.
