"""Deterministic citation verification: a cited quote must literally occur in the cited resource."""
import json, re


def resources(bundle: dict) -> dict:
    return {f"{e['resource']['resourceType']}/{e['resource']['id']}": e["resource"] for e in bundle["entry"]}


def _text(res: dict) -> str:
    return re.sub(r"\s+", " ", json.dumps(res, ensure_ascii=False)).lower()


def verify_evidence(bundle: dict, evidence: list) -> list:
    """Return list of booleans, one per evidence item."""
    idx = resources(bundle)
    out = []
    for ev in evidence or []:
        res = idx.get(ev.get("ref", ""))
        q = re.sub(r"\s+", " ", str(ev.get("quote", ""))).lower().strip()
        out.append(bool(res and len(q) >= 2 and q in _text(res)))
    return out
