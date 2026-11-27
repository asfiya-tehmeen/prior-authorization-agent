import argparse
import json
from pathlib import Path
from .evaluate import run
from .fhir_gen import make_cases
from .policy import load_policy, to_questionnaire


def main():
    p = argparse.ArgumentParser("priorauth")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--n", type=int, default=200)
    g.add_argument("--out", default="data/cases.jsonl")
    sub.add_parser("questionnaire")
    e = sub.add_parser("eval")
    e.add_argument("--n", type=int, default=200)
    e.add_argument("--llm", choices=["none", "mock", "groq"], default="none")
    e.add_argument("--model", default="openai/gpt-oss-120b")
    e.add_argument("--no-quarantine", action="store_true", help="ablation: show injection notes to the LLM")
    e.add_argument("--hard", action="store_true", help="add harder traps (prior episode, hedges, negations, conflicts, stealth injection)")
    a = p.parse_args()
    if a.cmd == "generate":
        Path(a.out).parent.mkdir(exist_ok=True)
        Path(a.out).write_text("\n".join(json.dumps(c) for c in make_cases(a.n)), encoding="utf-8")
    elif a.cmd == "questionnaire":
        print(json.dumps(to_questionnaire(load_policy()), indent=2))
    else:
        llm = None
        if a.llm == "mock":
            from .llm import MockLLM
            llm = MockLLM()
        elif a.llm == "groq":
            from .llm import GroqLLM
            llm = GroqLLM(a.model)
        label = a.llm + (f":{a.model}" if a.llm == "groq" else "") + (":noquarantine" if a.no_quarantine else "") + (":hard" if a.hard else "")
        Path("results").mkdir(exist_ok=True)
        tag = a.llm + ("_noq" if a.no_quarantine else "") + ("_hard" if a.hard else "")
        audit = Path("results") / f"audit_{tag}.jsonl"
        audit.unlink(missing_ok=True)
        res = run(a.n, llm=llm, audit=audit, label=label, quarantine=not a.no_quarantine, hard=a.hard)
        Path(f"results/eval_{tag}.json").write_text(json.dumps(res, indent=2))
        print(json.dumps(res, indent=2))
