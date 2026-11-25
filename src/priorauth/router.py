"""Criteria evaluation + routing. Never auto-deny: only a fully-met policy with clean evidence is auto-approved."""
import json
import time
from pathlib import Path
from .policy import evaluate_criteria, approval, MET


def decide(policy: dict, filled: dict, case_id: str, model: str, audit: Path | None = None) -> dict:
    values = {k: v["answer"] for k, v in filled["answers"].items()}
    verdicts = evaluate_criteria(policy, values)
    overall = approval(verdicts)
    reasons = []
    if filled["log"]["quarantined_notes"]:
        reasons.append("note contained instruction-like text (quarantined)")
    if overall != MET:
        reasons.append(f"policy not clearly met ({overall})")
    decision = "AUTO_APPROVE" if overall == MET and not reasons else "HUMAN_REVIEW"
    rec = {"case_id": case_id, "decision": decision, "verdicts": verdicts, "reasons": reasons,
           "answers": filled["answers"], "model": model, "policy": policy["id"], "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if audit:
        with audit.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    return rec
