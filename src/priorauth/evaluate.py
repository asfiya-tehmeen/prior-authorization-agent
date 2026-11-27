"""Evaluation over synthetic cases: field accuracy, citation validity, abstention, auto-approval precision."""
import sys
from collections import defaultdict
from .fhir_gen import make_cases
from .policy import load_policy
from .dtr_agent import fill_questionnaire
from .router import decide
from .citations import verify_evidence

# the questionnaire field each trap targets (None = case-level trap, e.g. injection)
TRAP_FIELD = {"conflicting_onset": "duration_days", "pt_note_only": "pt_weeks", "pt_planned_distractor": "pt_weeks",
              "pt_prior_episode": "pt_weeks", "pt_conflicting_notes": "pt_weeks", "nsaid_note_only": "nsaid_trial",
              "nsaid_negated_distractor": "nsaid_trial", "nsaid_hedged": "nsaid_trial", "cancer_family_history": "cancer_history",
              "neuro_note_only": "neuro_deficit", "neuro_negated": "neuro_deficit", "old_mri_distractor": "prior_mri_12m"}


def run(n=200, seed=0, llm=None, audit=None, label="baseline", quarantine=True, hard=False):
    pol = load_policy()
    tot = defaultdict(int)
    by_trap = defaultdict(lambda: [0, 0, 0])  # [cases with trap, targeted field wrong, wrong auto-approval]
    wrong_auto = []
    for ci, c in enumerate(make_cases(n, seed, hard)):
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
        bad_auto = auto and c["gold_decision"] != "APPROVE"
        gold = {k: (None if k in c["expected_abstain"] else v) for k, v in c["truth"].items()}
        wrong_fields = [k for k, a in filled["answers"].items() if a["answer"] != gold[k]]
        if bad_auto:
            wrong_auto.append({"case": c["case_id"], "wrong_fields": wrong_fields, "traps": c["traps"]})
        for t in c["traps"]:
            by_trap[t][0] += 1
            by_trap[t][1] += TRAP_FIELD.get(t) in wrong_fields
            by_trap[t][2] += bad_auto

    def d(a, b):
        return round(tot[a] / tot[b], 3) if tot[b] else None
    return {"llm_errors": getattr(llm, "errors", 0), "label": label, "cases": tot["cases"], "field_accuracy": d("field_correct", "fields"),
            "citation_validity": d("citations_valid", "citations"), "abstention_correctness": d("abstain_correct", "abstain_expected"),
            "automation_rate": d("auto", "cases"), "auto_approval_precision": d("auto_correct", "auto"),
            "approve_recall": d("auto_correct", "gold_approve"),
            "trap_field_error_rate": {t: f"{v[1]}/{v[0]}" for t, v in sorted(by_trap.items()) if TRAP_FIELD.get(t)},
            "case_level_traps_wrong_auto": {t: f"{v[2]}/{v[0]}" for t, v in sorted(by_trap.items()) if not TRAP_FIELD.get(t)},
            "wrong_auto_approvals": wrong_auto}
