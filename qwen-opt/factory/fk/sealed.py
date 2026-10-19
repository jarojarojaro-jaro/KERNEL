"""Sealed held-out prompt sets (sealed/), rotated once per RSI-F cycle, and the public spec_sweep set.

sealed/registry.json  {"active": id, "sets": [{"id", "file", "sha256", "cycle", "activated"}]}: every set ever used, in
                      order; the active one is what the verifier measures. A set is never reused after rotation.
sealed/pool.jsonl     unused prompts, each with "set": "sealed-vN"; `rotate()` activates the next whole set.
Both files are part of the harness hash (fk/hashing.py hashes sealed/), so a rotation is a harness change: it needs
`factory harness lock` and shows up in every later ledger row (sealed_sha256). The sha256 of each set file is pinned
in the registry; check_seal() refuses a set whose bytes changed.
Implementers do not read sealed/ (README); R36 checks diffs for 8-grams of every set, used, active or pooled.
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import os
import re

from . import paths
from .hashing import sha256_file

PUBLIC_ID = "spec6"
NEED = {"class": {"new-writing": 5, "copy-edit": 5}, "lang": {"pl": 4, "en": 6}}  # composition of every set (R24)
DRAW_N = 10  # prompts per verify, drawn from the active set (which may hold 10 x k)


class SealError(Exception):
    pass


def registry_path():
    return paths.SEALED_DIR / "registry.json"


def registry() -> dict:
    return json.loads(registry_path().read_text())


def active() -> dict:
    reg = registry()
    for s in reg["sets"]:
        if s["id"] == reg["active"]:
            return {**s, "path": paths.SEALED_DIR / s["file"]}
    raise SealError(f"registry: active set {reg['active']!r} not listed")


def prompt_set_id() -> str:
    return f"{active()['id']}+{PUBLIC_ID}"


def check_seal(path=None, pinned=None) -> str:
    if path is None or pinned is None:
        a = active()
        path, pinned = path or a["path"], pinned or a["sha256"]
    d = sha256_file(path, use_cache=False)
    if d != pinned:
        raise SealError(f"{path}: sha256 {d} != pinned {pinned} (sealed set changed without a harness change)")
    return d


def load_sealed(path=None, pinned=None) -> list[dict]:
    if path is None:
        a = active()
        path, pinned = a["path"], pinned or a["sha256"]
    check_seal(path, pinned)
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_pool() -> list[dict]:
    p = paths.SEALED_DIR / "pool.jsonl"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_all() -> list[dict]:
    """Every sealed prompt: used and active sets (sealed against tampering) plus the pool."""
    out = []
    for s in registry()["sets"]:
        out += load_sealed(paths.SEALED_DIR / s["file"], s["sha256"])
    return out + load_pool()


def composition_problems(entries: list[dict]) -> list[str]:
    """A set holds k x 10 prompts in the proportions of NEED (sealed-v1: 10; pooled sets: 40, drawn 10 per verify)."""
    out = []
    k = len(entries) / DRAW_N
    for key, need in NEED.items():
        have = {}
        for e in entries:
            have[e.get(key)] = have.get(e.get(key), 0) + 1
        want = {v: n * k for v, n in need.items()}
        if have != want:
            out.append(f"{key} counts {have} != {want}")
    if len({e["id"] for e in entries}) != len(entries):
        out.append("duplicate ids")
    return out


def draw(entries: list[dict], seed: int, n: int = DRAW_N) -> list[dict]:
    """n prompts of the active set for ONE verify (21i A12), stratified so every draw keeps the composition of NEED
    (5 new-writing / 5 copy-edit, 4 pl / 6 en): pick x = #(pl, new-writing), the other cells follow. Both ABBA arms
    get the same draw; the seed is chosen by the verifier and written into the ledger row."""
    import random
    if len(entries) <= n:
        return list(entries)
    rng = random.Random(seed)
    cells = {}
    for e in entries:
        cells.setdefault((e["lang"], e["class"]), []).append(e)
    pl, nw = NEED["lang"]["pl"], NEED["class"]["new-writing"]
    feas = [x for x in range(0, pl + 1)
            if all(len(cells.get(c, [])) >= m and m >= 0 for c, m in
                   ((("pl", "new-writing"), x), (("pl", "copy-edit"), pl - x), (("en", "new-writing"), nw - x),
                    (("en", "copy-edit"), n - pl - nw + x)))]
    if not feas:
        raise SealError("the active set cannot give a stratified draw")
    x = rng.choice(feas)
    out = []
    for c, m in ((("pl", "new-writing"), x), (("pl", "copy-edit"), pl - x), (("en", "new-writing"), nw - x),
                 (("en", "copy-edit"), n - pl - nw + x)):
        out += rng.sample(sorted(cells.get(c, []), key=lambda e: e["id"]), m)
    return sorted(out, key=lambda e: e["id"])


def rotate(cycle: int, dry_run: bool = False) -> dict:
    """Activate the next unused pool set for `cycle`. Writes sealed/prompts-<id>.jsonl (0444) and the registry.
    The caller must then lock the harness (it changed). dry_run: only say what would happen."""
    reg = registry()
    used = {s["id"] for s in reg["sets"]}
    pool = load_pool()
    ids = sorted({e["set"] for e in pool} - used, key=lambda x: [int(t) if t.isdigit() else t
                                                                    for t in re.split(r"(\d+)", x)])
    if not ids:
        raise SealError("pool exhausted: write a new set into sealed/pool.jsonl (harness change)")
    sid = ids[0]
    entries = [{k: v for k, v in e.items() if k != "set"} for e in pool if e["set"] == sid]
    probs = composition_problems(entries)
    if probs:
        raise SealError(f"{sid}: {probs}")
    fname = f"prompts-{sid}.jsonl"
    plan = {"from": reg["active"], "to": sid, "file": fname, "cycle": cycle, "n": len(entries)}
    if dry_run:
        return plan
    f = paths.SEALED_DIR / fname
    if f.exists():
        raise SealError(f"{f} exists")
    f.write_text("".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in entries), encoding="utf-8")
    os.chmod(f, 0o444)
    reg["sets"].append({"id": sid, "file": fname, "sha256": sha256_file(f, use_cache=False), "cycle": cycle,
                        "activated": dt.date.today().isoformat()})
    reg["active"] = sid
    # the pool keeps only unused sets: a burned set must not be rotated in again
    rest = [e for e in pool if e["set"] != sid]
    (paths.SEALED_DIR / "pool.jsonl").write_text(
        "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in rest), encoding="utf-8")
    tmp = registry_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=1) + "\n")
    os.replace(tmp, registry_path())
    return {**plan, "sha256": reg["sets"][-1]["sha256"]}


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
