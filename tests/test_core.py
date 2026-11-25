from priorauth.fhir_gen import make_cases
from priorauth.policy import load_policy, evaluate_criteria, approval, INSUFFICIENT
from priorauth.citations import verify_evidence
from priorauth.dtr_agent import fill_questionnaire
from priorauth.llm import MockLLM
from priorauth.evaluate import run


def test_three_valued_logic():
    pol = load_policy()
    v = evaluate_criteria(pol, {"duration_days": 60, "pt_weeks": None, "nsaid_trial": False, "cancer_history": False,
                                "neuro_deficit": False, "prior_mri_12m": False})
    assert v["C2"] == INSUFFICIENT and approval(v) == INSUFFICIENT


def test_citation_verifier_rejects_fabricated_quote():
    c = make_cases(1)[0]
    p = c["bundle"]["entry"][0]["resource"]
    good = {"ref": f"Patient/{p['id']}", "quote": p["gender"]}
    assert verify_evidence(c["bundle"], [good, {"ref": good["ref"], "quote": "made up text"},
                                         {"ref": "Patient/nope", "quote": "x"}]) == [True, False, False]


def test_injection_quarantined_and_citations_valid():
    r = run(300, llm=MockLLM(), label="mock")
    assert r["citation_validity"] == 1.0
    c = [c for c in make_cases(300) if "injection" in c["traps"]][0]
    f = fill_questionnaire(c["bundle"], load_policy(), MockLLM())
    assert f["log"]["quarantined_notes"]


def test_llm_improves_over_structured_only():
    a, b = run(300, label="none"), run(300, llm=MockLLM(), label="mock")
    assert b["field_accuracy"] > a["field_accuracy"]
