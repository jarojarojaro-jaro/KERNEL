"""Sealed held-out prompt set (sealed/prompts.jsonl) and the public spec_sweep set.

The sealed set is read only by the verifier. Its sha256 is pinned here (SEALED_SHA256), so any edit to the prompts
is a harness change: it changes this file, the harness hash in every ledger row and needs `factory harness lock`.
Implementers do not read sealed/prompts.jsonl (the README says so; the leak rule R36 checks diffs for its n-grams).
"""
from __future__ import annotations

import ast
import json
import re

from . import paths
from .hashing import sha256_file

SEALED_ID = "sealed-v1"
SEALED_SHA256 = "1e6c3a4ba773a3f2a5c15d3cc5d6d8f425cbdbf65ac29bb2020fb89f39373cc5"
SEALED_FILE = paths.SEALED_DIR / "prompts.jsonl"
PUBLIC_ID = "spec6"


class SealError(Exception):
    pass


def check_seal(path=SEALED_FILE, pinned=SEALED_SHA256) -> str:
    d = sha256_file(path, use_cache=False)
    if d != pinned:
        raise SealError(f"{path}: sha256 {d} != pinned {pinned} (sealed set changed without a harness change)")
    return d


def load_sealed(path=SEALED_FILE, pinned=SEALED_SHA256) -> list[dict]:
    check_seal(path, pinned)
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_public(spec_sweep=paths.SPEC_SWEEP) -> list[dict]:
    """The 6 prompts of spec_sweep.py (parsed, not imported), as single-turn sealed-format entries."""
    tree = ast.parse(spec_sweep.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "PROMPTS" for t in node.targets):
            prompts = ast.literal_eval(node.value)
            return [{"id": k, "class": "new-writing", "lang": k.split("-")[0], "domain": k.split("-")[1],
                     "messages": [{"role": "user", "content": v}]} for k, v in prompts.items()]
    raise SealError(f"{spec_sweep}: PROMPTS not found")


def summary(entries: list[dict]) -> dict:
    """Counts only (what implementers may see)."""
    out = {"n": len(entries), "class": {}, "lang": {}, "domain": {}}
    for e in entries:
        for k in ("class", "lang", "domain"):
            out[k][e[k]] = out[k].get(e[k], 0) + 1
    return out


WORD = re.compile(r"\w+", re.U)


def ngrams(text: str, n: int = 8) -> set[tuple]:
    w = [x.lower() for x in WORD.findall(text)]
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def sealed_ngrams(entries: list[dict], n: int = 8) -> set[tuple]:
    out = set()
    for e in entries:
        for m in e["messages"]:
            if m["role"] == "user":
                out |= ngrams(m["content"], n)
    return out
