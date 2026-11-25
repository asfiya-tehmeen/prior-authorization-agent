"""LLM interface. GroqLLM (OpenAI-compatible, free tier) for real runs; MockLLM is a TEST DOUBLE only."""
import hashlib
import json
import os
import re
import time
from pathlib import Path
import httpx


def _load_env(path=".env"):
    """Minimal .env loader (no extra dependency); real env vars take precedence."""
    try:
        for line in open(path, encoding="utf-8"):
            k, _, v = line.strip().partition("=")
            if k and not k.startswith("#") and v.strip():
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    except FileNotFoundError:
        pass


class GroqLLM:
    def __init__(self, model="openai/gpt-oss-120b", base="https://api.groq.com/openai/v1"):
        _load_env()
        if not os.environ.get("GROQ_API_KEY"):
            raise SystemExit("GROQ_API_KEY is empty - fill it in .env")
        self.model, self.base, self.key = model, base, os.environ["GROQ_API_KEY"]
        self.tokens = 0
        self.cache = {}
        self.cache_path = Path("data/llm_cache.jsonl")
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                d = json.loads(line)
                self.cache[d["k"]] = d["v"]

    def complete(self, system: str, user: str) -> str:
        key = hashlib.sha256(f"{self.model}\n{system}\n{user}".encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
        for attempt in range(12):
            try:
                r = httpx.post(f"{self.base}/chat/completions", timeout=90,
                               headers={"Authorization": f"Bearer {self.key}"},
                               json={"model": self.model, "temperature": 0, "reasoning_effort": "low", "max_tokens": 600,
                                     "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
            except httpx.TransportError:
                time.sleep(min(5 * (attempt + 1), 30))
                continue
            if r.status_code == 429:
                time.sleep(min(float(r.headers.get("retry-after", 0) or 0) + 1, 90) or 2 ** attempt * 3)
                continue
            r.raise_for_status()
            j = r.json()
            self.tokens += j.get("usage", {}).get("total_tokens", 0)
            out = j["choices"][0]["message"]["content"] or ""
            self.cache[key] = out
            self.cache_path.parent.mkdir(exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"k": key, "v": out}) + "\n")
            return out
        self.errors = getattr(self, "errors", 0) + 1   # degrade to abstain; not cached, so a rerun retries it
        return '{"answer": null, "abstain": true, "evidence": []}'


class MockLLM:
    """Naive regex reader of the prompt's note text. For testing the harness only - NOT a model result."""
    tokens = 0

    def complete(self, system: str, user: str) -> str:
        qid = re.search(r"QUESTION_ID: (\w+)", user).group(1)
        notes = re.findall(r"\[(DocumentReference/[\w-]+)\] (.*)", user)
        for ref, txt in notes:
            if qid == "pt_weeks" and (m := re.search(r"completed (\d+) weeks of supervised physical therapy", txt)):
                return json.dumps({"answer": int(m.group(1)), "abstain": False, "evidence": [{"ref": ref, "quote": m.group(0)}]})
            if qid == "nsaid_trial" and (m := re.search(r"ibuprofen[^.]*", txt)):
                return json.dumps({"answer": True, "abstain": False, "evidence": [{"ref": ref, "quote": m.group(0)}]})
            if qid == "neuro_deficit" and (m := re.search(r"progressive left foot drop", txt)):
                return json.dumps({"answer": True, "abstain": False, "evidence": [{"ref": ref, "quote": m.group(0)}]})
        return json.dumps({"answer": None, "abstain": True, "evidence": []})
