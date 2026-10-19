"""Claim card: JSON written by the implementer BEFORE any measurement and frozen by `factory register`.

Required fields (validate() lists every problem):
  id                 YYYY-MM-DD-slug, also the file name claims/<id>.json
  author, created
  hypothesis         one falsifiable sentence;  mechanism: why it should work (free text)
  profile            measurement profile (fk/profiles.py): qwen-mtp | qwen-plain | lfm
  metric             ms_step | ms_token | tok_step | tps | pp_tps | tg_tps   (end-to-end only, rule R07)
  expected           {"effect_pct": +0.4}  favorable % (positive = better), optional "delta_ms": -0.04
  kill               {"effect_pct_below": 0.1}  REFUTED when the whole 95 % CI lies below this favorable %
  correctness_class  BIT | NEAR-TIE | SAME-TOK | KLD
  switch             {"name": "GGML_HIP_X", "on": "1", "off": "0"}  (every change behind an env switch)
  probe              how G3 sees that the change ran: {"kind": "log", "env": {...}, "regex": "..."}
                     | {"kind": "timing"} (A arm = candidate with the switch off) | {"kind": "md5"} (off restores
                     base md5; not for BIT)
  prompt_set         {"id": "sealed-v1+spec6", "sealed_sha256": <pinned hash>}
  repo, commits      {"base": sha, "cand": sha}; touched_paths (= files of the diff)
  builds             {"base": {"dir": ..., "sha256": {file: sha}}, "cand": {...}}   (factory card fill)
  model_sha256       sha256 of the profile's GGUF                                      (factory card fill)
Optional: attacked {"kernels": [...], "share_ms": 0.61, "source": {"tool": "pm4trace", "env": {...}}} for the
Amdahl gate; ops ["MUL_MAT", "MUL_MAT|type_a=q4_K"] for test-backend-ops (-o OP [-p PARAMS]); reference "fork" | "upstream"; mde_pct; notes.
RSI-F (fk/rsi.py): expected.p_confirmed (0..1, the implementer's probability of CONFIRMED, scored with Brier);
rsi {"playbook": id | null, "arm": "A" | "B", "target": target id, "brief_sha256": sha of the brief the agent got}.
prompt_set must name the ACTIVE sealed set (sealed/registry.json; it rotates once per RSI cycle).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .hashing import sha256_json
from .profiles import PROFILES
from . import sealed
from .stats import E2E_METRICS

CLASSES = ("BIT", "NEAR-TIE", "SAME-TOK", "KLD")
PROBES = ("log", "timing", "md5")
SWITCH_RE = re.compile(r"^(GGML_HIP|GGML_CUDA|GGML_VK|LLAMA|GGML)_[A-Z0-9_]+$")
ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*$")
RSI_ARMS = ("A", "B")  # A = fresh implementer with a playbook, B = the same brief without it (fk/transfer.py)


def load(path) -> dict:
    return json.loads(Path(path).read_text())


def card_sha(card: dict) -> str:
    return sha256_json(card)


def template(cid: str, author: str, created: str) -> dict:
    return {
        "id": cid, "author": author, "created": created,
        "hypothesis": "", "mechanism": "",
        "profile": "qwen-mtp", "metric": "ms_step",
        "expected": {"effect_pct": None}, "kill": {"effect_pct_below": None},
        "correctness_class": "BIT",
        "switch": {"name": "GGML_HIP_", "on": "1", "off": "0"},
        "probe": {"kind": "timing"},
        "prompt_set": {"id": sealed.prompt_set_id(), "sealed_sha256": sealed.active()["sha256"]},
        "attacked": {"kernels": [], "share_ms": None, "source": None},
        "ops": [], "reference": "fork",
        "repo": "", "commits": {"base": "", "cand": ""}, "touched_paths": [],
        "builds": {"base": {"dir": "", "sha256": {}}, "cand": {"dir": "", "sha256": {}}},
        "model_sha256": "",
    }


def validate(card: dict, filled: bool = True) -> list[str]:
    p = []

    def need(k, typ=str):
        if k not in card or card[k] in (None, "", [], {}):
            p.append(f"missing {k}")
            return False
        if not isinstance(card[k], typ):
            p.append(f"{k}: expected {typ.__name__}")
            return False
        return True

    if need("id") and not ID_RE.match(card["id"]):
        p.append("id: expected YYYY-MM-DD-slug (lowercase)")
    need("author")
    need("created")
    if need("hypothesis") and len(card["hypothesis"]) < 15:
        p.append("hypothesis: too short to be falsifiable")
    if need("profile") and card["profile"] not in PROFILES:
        p.append(f"profile: one of {sorted(PROFILES)}")
    if need("metric") and card["metric"] not in E2E_METRICS:
        p.append(f"metric: {card['metric']!r} is not an end-to-end metric {sorted(E2E_METRICS)} (R07)")
    if need("expected", dict) and not isinstance(card["expected"].get("effect_pct"), (int, float)):
        p.append("expected.effect_pct: number (favorable %, positive = better)")
    if need("kill", dict) and not isinstance(card["kill"].get("effect_pct_below"), (int, float)):
        p.append("kill.effect_pct_below: number (REFUTED when the 95 % CI lies below it)")
    if need("correctness_class") and card["correctness_class"] not in CLASSES:
        p.append(f"correctness_class: one of {CLASSES}")
    if need("switch", dict):
        s = card["switch"]
        if not SWITCH_RE.match(str(s.get("name", ""))):
            p.append("switch.name: an env name like GGML_HIP_FOO")
        if s.get("on") is None or s.get("off") is None or str(s.get("on")) == str(s.get("off")):
            p.append("switch.on/off: two different values")
    if need("probe", dict):
        k = card["probe"].get("kind")
        if k not in PROBES and not (k == "null" and card.get("null_rebuild") is True):
            p.append(f"probe.kind: one of {PROBES} (\"null\" only on a null_rebuild card)")
        if card.get("null_rebuild") is True and k != "null":
            p.append("a null_rebuild card has probe {\"kind\": \"null\"} (A = base build, B = rebuilt candidate)")
        if k == "log" and not card["probe"].get("regex"):
            p.append("probe.regex: required for kind log")
        if k == "md5" and card.get("correctness_class") == "BIT":
            p.append("probe md5 cannot show anything for a BIT claim (on and off give the same md5); use log/timing")
    for gd in card.get("guards") or []:
        prof = gd.get("profile") if isinstance(gd, dict) else gd
        met = gd.get("metric", "pp_tps") if isinstance(gd, dict) else "pp_tps"
        if prof not in PROFILES or met not in ("pp_tps", "tg_tps"):
            p.append(f"guards: {gd!r}: profile from {sorted(PROFILES)}, metric pp_tps|tg_tps (llama-bench guards, 21i A6)")
    if need("prompt_set", dict):
        ps = card["prompt_set"]
        a = sealed.active()
        if ps.get("id") != sealed.prompt_set_id():
            p.append(f"prompt_set.id: must be {sealed.prompt_set_id()} (the verifier always runs the active sealed set)")
        if ps.get("sealed_sha256") != a["sha256"]:
            p.append(f"prompt_set.sealed_sha256: does not match the active sealed set {a['id']}")
    pc = (card.get("expected") or {}).get("p_confirmed")
    if pc is not None and not (isinstance(pc, (int, float)) and 0 <= pc <= 1):
        p.append("expected.p_confirmed: probability 0..1")
    r = card.get("rsi")
    if r is not None:
        if not isinstance(r, dict) or r.get("arm") not in RSI_ARMS or not r.get("target") or \
                not re.fullmatch(r"[0-9a-f]{64}", str(r.get("brief_sha256", ""))):
            p.append("rsi: {playbook, arm A|B, target, brief_sha256} (factory rsi transfer brief)")
        elif (r["arm"] == "A") != bool(r.get("playbook")):
            p.append("rsi: arm A carries a playbook id, arm B none")
    att = card.get("attacked") or {}
    if card.get("metric") in ("ms_step", "ms_token") and not isinstance(att.get("share_ms"), (int, float)):
        p.append("attacked.share_ms: required for ms metrics (Amdahl gate G5); profile the attacked kernels")
    if card.get("reference", "fork") not in ("fork", "upstream"):
        p.append("reference: fork | upstream")
    if filled:
        need("repo")
        c = card.get("commits") or {}
        if not (c.get("base") and c.get("cand")):
            p.append("commits.base/cand: required")
        need("touched_paths", list)
        b = card.get("builds") or {}
        for arm in ("base", "cand"):
            if not (b.get(arm, {}).get("dir") and b.get(arm, {}).get("sha256")):
                p.append(f"builds.{arm}: dir + sha256 (factory card fill)")
        if not re.fullmatch(r"[0-9a-f]{64}", str(card.get("model_sha256", ""))):
            p.append("model_sha256: sha256 of the GGUF (factory card fill)")
    return p
