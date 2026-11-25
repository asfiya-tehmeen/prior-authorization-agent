# G. FHIR Prior-Authorization Agent — Ideation

**Status:** Ideation | **Data:** REAL policies + standards; patients SYNTHETIC (no public real patient data with free LLM use); optional real de-identified demo data | **Target roles:** AI engineer (payers, health-tech), forward-deployed AI engineer, healthcare integration engineer

**One-line pitch:** A standards-based prior-authorization system where a provider-side agent fills the payer's documentation questionnaire from the patient's FHIR record with citations, and a payer-side agent checks the request against real coverage-policy criteria, abstaining and escalating when evidence is weak.

---

## 1. Why this matters

- Payer job postings explicitly describe this work: RAG over payer policies, multi-agent orchestration, determination and clinical evidence agents (Optum), and claim-denial agents (classification, evidence retrieval, policy reasoning, appeals).
- US regulation is pushing prior authorization onto FHIR APIs: CMS's Interoperability and Prior Authorization Final Rule (CMS-0057-F, January 2024) requires payers to build FHIR-based prior-authorization APIs, with most deadlines in 2026–2027. Verify the exact dates before writing about them.
- HL7's Da Vinci project publishes free implementation guides for this workflow: **CRD** (is prior auth required?), **DTR** (fill the documentation questionnaire), **PAS** (submit and get a decision).
- In Saudi Arabia, NPHIES handles eligibility, prior authorization and claims; I believe it is built on FHIR (verify). That makes the project Gulf-relevant.
- Most portfolio "prior-auth bots" are a chatbot over a PDF. Building on the real standards is what makes this stand out.

## 2. How the idea was improved from v1

| v1 idea | Improved version | Why |
|---|---|---|
| Agent reads a policy and a patient, says approve/deny | Two-sided, standards-based flow: provider agent (CRD + DTR auto-fill) and payer agent (criteria check + PAS-style response) | Matches how the industry is actually wiring this; FDE-relevant |
| Multi-agent orchestration | Small number of well-scoped agents with deterministic checks between them | Easier to evaluate; avoids over-building |
| Free-text decision | Criterion-by-criterion verdicts (MET / NOT MET / INSUFFICIENT EVIDENCE) with FHIR resource citations | Auditable; measurable |
| Synthetic patients only | Real policies, real standards and profiles, real terminology; synthetic patients with planted edge cases; optional real de-identified demo records | Real wherever possible |
| Accuracy only | Also calibration, abstention, time-to-decision, and red-teaming (prompt injection in clinical notes, missing data, conflicting evidence) | Safety evaluation is what payers worry about |

## 3. Research questions

1. **Auto-fill:** How accurately can an agent answer a documentation questionnaire from a FHIR record, with citations that verify?
2. **Criterion reasoning:** How accurate are criterion-level verdicts against a gold set built from real policy criteria?
3. **Abstention:** Does the agent say INSUFFICIENT EVIDENCE when it should, instead of guessing? What is the trade-off between automation rate and error rate?
4. **Retrieval design:** Which policy-chunking and retrieval strategy gives the best criterion recall?
5. **Safety:** How often do adversarial inputs (injected instructions in notes, contradictory records) change a decision?

## 4. Data plan (real first)

| Need | Source | Real? | Notes / to verify |
|---|---|---|---|
| Coverage criteria | CMS Medicare Coverage Database (NCDs, LCDs, articles) | ✅ Real | Downloads/API require accepting AMA/ADA/AHA licence agreements because of CPT codes. Read the terms; keep raw policy files out of the public repo; cite sources. |
| Workflow standards | HL7 Da Vinci CRD, DTR, PAS implementation guides; FHIR R4 | ✅ Real | Free to read and implement. |
| Questionnaire format | FHIR `Questionnaire` / `QuestionnaireResponse` (+ CQL in DTR) | ✅ Real standard | You author questionnaires from real policy criteria. |
| Terminology | ICD-10-CM (public), RxNorm via NLM RxNav API (free), LOINC (free with registration) | ✅ Real | CPT is licensed; avoid redistributing CPT descriptions. |
| Patients | Synthea FHIR R4 (Apache-2.0 code, public-domain data) | ❌ Synthetic | Needed: no real patient records can be sent to free LLM APIs. Add planted edge cases (missing labs, conflicting dates, borderline values). |
| Optional real records | MIMIC-IV demo on FHIR (I believe about 100 patients, open access; verify the licence and whether API use is allowed) | ✅ Real (de-identified) | Use for a realism check only. The full MIMIC requires credentialing and PhysioNet's rules on sending data to online LLM services; check before using. |
| FHIR server | HAPI FHIR (open source) running locally in Docker | ✅ Real software | Free. |

Scope: 3–5 services with clear, well-documented criteria (for example a few imaging, therapy or durable-equipment policies). Fewer policies, measured well, beats many policies measured badly.

## 5. System design

```
           PROVIDER SIDE                                  PAYER SIDE
  ┌──────────────────────────────┐            ┌─────────────────────────────────┐
  │ Order placed (ServiceRequest) │──CRD-like─►│ Is prior auth required? (rules) │
  └──────────────────────────────┘            └─────────────────────────────────┘
                 │                                          │ returns Questionnaire
                 ▼                                          │
  ┌──────────────────────────────┐                          │
  │ DTR agent: answer each item   │◄─────────────────────────┘
  │ from FHIR record with         │
  │ resource-ID citations         │
  │ + deterministic verifier      │
  └──────────────────────────────┘
                 │ QuestionnaireResponse + evidence bundle
                 ▼                                           
  ┌──────────────────────────────┐──PAS-like─►┌─────────────────────────────────┐
  │ Submit request bundle         │            │ Criteria agent: per-criterion    │
  └──────────────────────────────┘            │ MET / NOT MET / INSUFFICIENT,    │
                                              │ cites policy section + evidence  │
                                              │ Policy RAG (hybrid retrieval)    │
                                              └─────────────────────────────────┘
                                                             │
                                          all criteria met + high confidence? 
                                            yes → auto-approve │ no → human reviewer queue
                                                             ▼
                                              Decision + rationale + audit log
```

Key engineering choices:
- **Deterministic citation checks:** every answer cites a FHIR resource ID and value; code verifies the value exists and matches.
- **Never auto-deny:** the agent can auto-approve only when all criteria are clearly met; anything else goes to a human. (This mirrors common industry practice and avoids an obvious harm. Verify the framing before stating it as an industry norm.)
- **Audit log:** every decision stored with inputs, retrieved policy text IDs, model version and timestamps.
- **Untrusted text:** clinical note content is treated as data, never as instructions.

## 6. Evaluation plan

| Task | Ground truth | Metrics | Baselines |
|---|---|---|---|
| Questionnaire auto-fill | Answers derived programmatically from the synthetic record (you know what you generated) + planted traps | Field accuracy, citation validity rate, abstention correctness | Rule/FHIRPath extraction |
| Criterion verdicts | Gold set written from policy criteria (your labels; second reviewer if possible) | Per-criterion accuracy, macro F1, confusion on INSUFFICIENT | Rules-only engine |
| End-to-end decision | Gold decision per case | Auto-approval precision, automation rate, human-queue rate | Rules-only |
| Calibration | Correct/incorrect | Risk–coverage curve, ECE | — |
| Retrieval | Criteria needed per case | Recall@k of the right policy section | BM25 vs embeddings vs hybrid |
| Red team | Planted attacks | Attack success rate, decision flips | — |
| Cost/latency | Logs | Tokens, seconds per case | — |

Because the patients are generated, auto-fill ground truth comes from the generator itself, so labels are cheap and exact. Criterion verdicts still need careful human labelling; keep that set small (100–200 cases) and document the rules.

## 7. Free stack and budget

- Python, FastAPI, Pydantic, HAPI FHIR (Docker), `fhir.resources`, DuckDB, LangGraph (you know it), rank-bm25 + a local embedding model, pytest, Streamlit or Next.js for the reviewer UI.
- Synthea needs Java (free).
- LLM: Groq/Gemini free tiers or local; per case cost is several calls, so cap evaluation at a few hundred cases and cache.

## 8. Step-by-step plan

### Phase 0 — Decide (½ day)
- [ ] Pick 3–5 policies; read and accept the MCD licence terms; note what you may publish.
- [ ] Read the CRD, DTR and PAS guides at overview level; decide how closely to follow them (recommend: "inspired by", with real FHIR resources).

### Phase 1 — Data and infrastructure (2 days)
- [ ] Run HAPI FHIR locally; load Synthea patients.
- [ ] Generate patients targeted at the chosen services, plus planted edge cases.
- [ ] Turn each policy's criteria into a FHIR Questionnaire and a machine-readable criteria file.
- [ ] Optional: load the MIMIC-IV FHIR demo for a realism check (after verifying terms).

### Phase 2 — Baselines (1 day)
- [ ] FHIRPath/rule-based auto-fill.
- [ ] Rules-only criteria engine.

### Phase 3 — Agents (3–4 days)
- [ ] DTR agent with citation verifier.
- [ ] Policy RAG (BM25, embeddings, hybrid).
- [ ] Criteria agent with three-way verdicts.
- [ ] Routing: auto-approve vs human queue; audit log.
- [ ] Reviewer UI.

### Phase 4 — Evaluation (2–3 days)
- [ ] All metrics in section 6; retrieval ablation; threshold sweep.
- [ ] Red-team set: injected instructions, conflicting records, missing data, outdated evidence.

### Phase 5 — Write-up and ship (1–2 days)
- [ ] `REPORT.md` with failures; architecture diagram; Loom demo; deploy the API + UI.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| CPT licence limits publishing policy text | Publish criteria summaries and IDs, not raw text; link to CMS |
| Synthetic patients too clean | Planted edge cases; optional MIMIC demo realism check |
| Standards are large | Implement a documented subset; say "inspired by Da Vinci" |
| Gold labels are your judgement | Document labelling rules; second reviewer for a sample |
| Scope creep | Ship one policy end to end before adding more |

## 10. Do not claim

- Clinical validity or real-world approval accuracy.
- Compliance with CMS-0057-F or Da Vinci certification.
- That it is safe to deploy for real decisions.

## 11. Stretch ideas

- NPHIES-style variant: map the flow to Saudi NPHIES message types (after checking public NPHIES documentation).
- Appeal-letter generator for NOT MET decisions, with citations.
- CQL execution for deterministic criteria (as DTR intends).
- Reuse project H's MCP tools for terminology lookup.

## 12. Open questions to decide together

1. Which 3–5 services/policies?
2. Strict Da Vinci alignment or "inspired by"?
3. Payer-side only first, or both sides from the start?
4. LangGraph or plain Python state machine?

## 13. Resume/DM hook (fill in only after measuring)

> Built a FHIR-based prior-authorization agent (Da Vinci CRD/DTR/PAS-inspired) over [N] real CMS coverage policies: questionnaire auto-fill accuracy [x]% with 100% verified citations, auto-approval precision [x]% at [y]% automation, and [x]% of red-team attacks blocked.
