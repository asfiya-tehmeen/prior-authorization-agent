"""Load a policy file; build a FHIR Questionnaire; evaluate criteria from answers (deterministic)."""
import json
from pathlib import Path

POLICY_DIR = Path(__file__).resolve().parents[2] / "policies"
MET, NOT_MET, INSUFFICIENT = "MET", "NOT_MET", "INSUFFICIENT_EVIDENCE"


def load_policy(pid: str = "lumbar-mri") -> dict:
    return json.loads((POLICY_DIR / f"{pid.replace('-', '_')}.json").read_text(encoding="utf-8"))


def to_questionnaire(policy: dict) -> dict:
    return {
        "resourceType": "Questionnaire", "id": policy["id"], "status": "draft", "title": policy["title"],
        "item": [{"linkId": i["linkId"], "text": i["text"], "type": i["type"]} for i in policy["items"]],
    }


def _cmp(val, op, ref):
    return {">=": val >= ref, "==": val == ref, "<=": val <= ref}[op]


def _eval(rule: dict, answers: dict) -> str:
    """Three-valued logic over item answers. answers[item] is a value or None (abstained)."""
    if "any" in rule:
        vs = [_eval(r, answers) for r in rule["any"]]
        return MET if MET in vs else (INSUFFICIENT if INSUFFICIENT in vs else NOT_MET)
    if "all" in rule:
        vs = [_eval(r, answers) for r in rule["all"]]
        return NOT_MET if NOT_MET in vs else (INSUFFICIENT if INSUFFICIENT in vs else MET)
    v = answers.get(rule["item"])
    if v is None:
        return INSUFFICIENT
    return MET if _cmp(v, rule["op"], rule["value"]) else NOT_MET


def evaluate_criteria(policy: dict, answers: dict) -> dict:
    return {c["id"]: _eval(c["rule"], answers) for c in policy["criteria"]}


def approval(verdicts: dict) -> str:
    """lumbar-mri logic: C4 AND (C3 OR (C1 AND C2)) in three-valued logic."""
    def AND(*x): return NOT_MET if NOT_MET in x else (INSUFFICIENT if INSUFFICIENT in x else MET)
    def OR(*x): return MET if MET in x else (INSUFFICIENT if INSUFFICIENT in x else NOT_MET)
    v = verdicts
    return AND(v["C4"], OR(v["C3"], AND(v["C1"], v["C2"])))
