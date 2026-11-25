"""Evaluation over synthetic cases: field accuracy, citation validity, abstention, auto-approval precision."""
import sys
from collections import defaultdict
from .fhir_gen import make_cases
from .policy import load_policy
from .dtr_agent import fill_questionnaire
from .router import decide
from .citations import verify_evidence


def run(n=200, seed=0, llm=None, audit=None, label="baseline", quarantine=True):
    pol = load_policy()
    tot = defaultdict(int)
    by_trap = defaultdict(lambda: [0, 0])
    for ci, c in enumerate(make_cases(n, seed)):
        if ci % 10 == 0:
            print(f"[{label}] case {ci}/{n}", file=sys.stderr, flush=True)
        filled = fill_questionnaire(c["bundle"], pol, llm, quarantine)
        rec = decide(pol, filled, c["case_id"], label, audit)
        for k, a in filled["answers"].items():
            t = None if k in c["expected_abstain"] else c["truth"][k]
            tot["fields"] += 1
            tot["field_correct"] += (a["answer"] == t)
            if k in c["expected_abstain"]:
                tot["abstain_expected"] += 1
                tot["abstain_correct"] += (a["answer"] is None)
            if a["evidence"]:
                v = verify_evidence(c["bundle"], a["evidence"])
                tot["citations"] += len(v)
                tot["citations_valid"] += sum(v)
        auto = rec["decision"] == "AUTO_APPROVE"
        tot["cases"] += 1
        tot["auto"] += auto
        tot["auto_correct"] += auto and c["gold_decision"] == "APPROVE"
        tot["gold_approve"] += c["gold_decision"] == "APPROVE"
        for t in c["traps"]:
            by_trap[t][0] += 1
            by_trap[t][1] += (auto and c["gold_decision"] != "APPROVE")

    def d(a, b):
        return round(tot[a] / tot[b], 3) if tot[b] else None
    return {"llm_errors": getattr(llm, "errors", 0), "label": label, "cases": tot["cases"], "field_accuracy": d("field_correct", "fields"),
            "citation_validity": d("citations_valid", "citations"), "abstention_correctness": d("abstain_correct", "abstain_expected"),
            "automation_rate": d("auto", "cases"), "auto_approval_precision": d("auto_correct", "auto"),
            "approve_recall": d("auto_correct", "gold_approve"),
            "wrong_auto_approvals_by_trap": {t: v[1] for t, v in by_trap.items()}}
