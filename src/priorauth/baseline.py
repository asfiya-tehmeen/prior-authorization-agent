"""Rule-based (FHIRPath-style) extractor over STRUCTURED resources only. Abstains on note-only evidence."""
import re
from datetime import date
from .fhir_gen import ORDER_DATE


def _by(bundle, rt): return [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == rt]


def _ev(res, quote): return {"ref": f"{res['resourceType']}/{res['id']}", "quote": quote}


def answer_all(bundle: dict, policy: dict) -> dict:
    out = {}
    # duration
    conds = [c for c in _by(bundle, "Condition") if any(x.get("code", "").startswith("M54") for x in c["code"]["coding"])]
    onsets = {c["onsetDateTime"]: c for c in conds}
    if len(onsets) == 1:
        o, c = next(iter(onsets.items()))
        out["duration_days"] = {"answer": (ORDER_DATE - date.fromisoformat(o)).days, "evidence": [_ev(c, o)]}
    else:
        out["duration_days"] = {"answer": None, "evidence": []}
    # PT
    pts = [p for p in _by(bundle, "Procedure") if "physical therapy" in p["code"].get("text", "").lower()]
    if pts:
        m = re.search(r"(\d+) weeks", pts[0]["note"][0]["text"])
        out["pt_weeks"] = {"answer": int(m.group(1)), "evidence": [_ev(pts[0], m.group(0))]} if m else {"answer": None, "evidence": []}
    else:
        out["pt_weeks"] = {"answer": 0, "evidence": []}   # absence of structured record -> 0 (wrong when note-only)
    # NSAID
    nsaid = [m for m in _by(bundle, "MedicationRequest") if m["medicationCodeableConcept"]["coding"][0]["code"] in {"5640", "7258"}]
    out["nsaid_trial"] = {"answer": bool(nsaid), "evidence": [_ev(nsaid[0], nsaid[0]["medicationCodeableConcept"]["coding"][0]["code"])] if nsaid else []}
    # cancer
    ca = [c for c in conds_all(bundle) if any(x.get("code", "").startswith("C") for x in c["code"]["coding"])]
    out["cancer_history"] = {"answer": bool(ca), "evidence": [_ev(ca[0], ca[0]["code"]["coding"][0]["code"])] if ca else []}
    # neuro
    ne = [o for o in _by(bundle, "Observation") if "foot drop" in o["code"].get("text", "").lower()]
    out["neuro_deficit"] = {"answer": bool(ne), "evidence": [_ev(ne[0], "Foot drop")] if ne else []}
    # prior MRI
    mri = [s for s in _by(bundle, "ImagingStudy") if "lumbar" in s.get("description", "").lower()
           and (ORDER_DATE - date.fromisoformat(s["started"])).days <= 365]
    out["prior_mri_12m"] = {"answer": bool(mri), "evidence": [_ev(mri[0], mri[0]["started"])] if mri else []}
    return out


def conds_all(bundle): return _by(bundle, "Condition")
