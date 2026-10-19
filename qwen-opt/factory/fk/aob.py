"""AMD-Opt Bench aob-v1 (report 21i §5): the RSI-F progress measure. CPU only: aob never launches GPU work;
GPU measurement happens only through `factory verify` (and its gates), run by the planner.

Task layout (Harbor-lite), aob/tasks/<id>/:
  task.toml        id, title, kind opt|fix|neg|port, split dev|test, profile, metric, base_commit, oracle_commit
                   ("none" allowed), gpu_minutes, correctness_class, oracle_effect_pct (number | "none"), guards,
                   ops, switch_hint, status ready|needs-fixture, source; neg adds gpu="none",
                   decision_threshold_pct, oracle_decision, measured_effect_pct
  instruction.md   symptom/goal only (no patch number, commit, oracle switch); local measurement via --dry-run
  environment/     build.sh (HIP recipe + one-commit snapshot note)
  tests/           HIDDEN: card.json (claim-card template), f2p.json (fix), cpu_tier.sh
  solution/        HIDDEN: oracle.ref (repo/base/oracle/patches/switches/numbers), null.patch (noise probe)
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import re
import subprocess
import tomllib
from pathlib import Path

from . import paths

TASKS = paths.AOB / "tasks"
KINDS = ("opt", "fix", "neg", "port")
SPLITS = ("dev", "test")
TASK_PROFILES = ("qwen-mtp", "qwen-plain", "lfm")
STATUSES = ("ready", "needs-fixture")
REQUIRED = ("id", "kind", "split", "profile", "metric", "base_commit", "oracle_commit", "gpu_minutes",
            "correctness_class", "oracle_effect_pct", "guards", "ops", "switch_hint", "status", "source")
PATCH_NO_RE = re.compile(r"(?<![0-9A-Za-z])00[0-9]{2}(?![0-9A-Za-z])")
DEFAULT_REPO = paths.HOME / "llama-master"


def _none(v):
    return None if v in (None, "none", "") else v


def _read_ref(p: Path) -> dict:
    ref = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                ref[k.strip()] = v.strip()
    for k in ("patches", "switches"):
        ref[k] = ref.get(k, "").split()
    return ref


def load_task(tid: str, root: Path | None = None) -> dict:
    d = Path(root or TASKS) / tid
    with open(d / "task.toml", "rb") as f:
        t = tomllib.load(f)
    t["dir"] = str(d)
    t["instruction"] = (d / "instruction.md").read_text() if (d / "instruction.md").exists() else ""
    t["oracle_ref"] = _read_ref(d / "solution" / "oracle.ref")
    return t


def list_tasks(root: Path | None = None) -> list[str]:
    r = Path(root or TASKS)
    return sorted(p.name for p in r.iterdir() if (p / "task.toml").exists()) if r.exists() else []


def validate_task(task: dict) -> list[str]:
    p = [f"missing {k}" for k in REQUIRED if k not in task]
    if task.get("kind") not in KINDS:
        p.append(f"kind: one of {KINDS}")
    if task.get("split") not in SPLITS:
        p.append(f"split: one of {SPLITS}")
    if task.get("profile") not in TASK_PROFILES:
        p.append(f"profile: one of {TASK_PROFILES}")
    if task.get("status") not in STATUSES:
        p.append(f"status: one of {STATUSES}")
    gm = task.get("gpu_minutes")
    if not isinstance(gm, (int, float)) or gm < 0:
        p.append("gpu_minutes: number >= 0")
    if task.get("kind") == "neg" and (gm != 0 or task.get("gpu") != "none"):
        p.append("neg task: gpu_minutes must be 0 and gpu = \"none\" (CPU only, H2/H3)")
    eff = _none(task.get("oracle_effect_pct"))
    if task.get("kind") in ("opt", "port") and _none(task.get("oracle_commit")) and not isinstance(eff, (int, float)):
        p.append("oracle_effect_pct: number for opt/port with an oracle")
    d = Path(task.get("dir", ""))
    blob = json.dumps({k: v for k, v in task.items() if k not in ("instruction", "oracle_ref")})
    for f in ("environment/build.sh", "tests/card.json", "tests/cpu_tier.sh"):
        if (d / f).exists():
            blob += (d / f).read_text()
    if re.search(r"GGML_HIP_PM4\s*[=:\"' ]+\s*\"?([1-9])", blob):
        p.append("GGML_HIP_PM4 != 0 is forbidden in every task (report 17, H2)")
    # leak checks on the implementer-visible text
    ins = task.get("instruction", "")
    ref = task.get("oracle_ref") or {}
    for c in {_none(task.get("oracle_commit")), _none(ref.get("oracle"))} - {None}:
        if c[:7].lower() in ins.lower():
            p.append(f"instruction leaks the oracle commit {c[:7]}")
    if PATCH_NO_RE.search(ins):
        p.append(f"instruction names a patch number ({PATCH_NO_RE.search(ins).group(0)})")
    for s in ref.get("switches", []):
        if s in ins:
            p.append(f"instruction names the oracle switch {s}")
    if "GGML_HIP_PM4" in ins:
        p.append("instruction mentions GGML_HIP_PM4")
    return p


def make_card(task: dict, workspace, base: str, cand: str, author: str, created: str | None = None) -> dict:
    """Claim card from the hidden tests/card.json; hypothesis/metric/switch/kill/ops come from the task."""
    if task["kind"] == "neg":
        raise ValueError(f"{task['id']}: neg task is CPU only, no claim card")
    from . import card as fkcard
    tpl = json.loads((Path(task["dir"]) / "tests" / "card.json").read_text())
    now = _dt.datetime.now(_dt.timezone.utc)
    slug = "aob-" + task["id"].replace("_", "-")
    c = fkcard.template(f"{now:%Y-%m-%d}-{slug}", author, created or now.strftime("%Y-%m-%dT%H:%M:%S%z"))
    c.update(tpl)
    c["repo"] = str(workspace)
    c["commits"] = {"base": base, "cand": cand}
    c["aob"] = {"task": task["id"], "split": task["split"], "kind": task["kind"]}
    return c


def reward(task: dict, row: dict) -> dict:
    """21i §5.2 item 3. row: factory verdict row ({verdict, median}) for opt/port; {f2p_pass, p2p_pass, f2p} for fix;
    {decision, pred_effect_pct} for neg."""
    k = task["kind"]
    if k in ("opt", "port"):
        if row.get("verdict") != "CONFIRMED" or not isinstance(row.get("median"), (int, float)):
            return {"reward": 0.0, "recovery": 0.0, "needs_human": False}
        r = 1 + row["median"] / 100
        rew = max(0.0, r - 1)
        oe = _none(task.get("oracle_effect_pct"))
        rec = (r - 1) / (oe / 100) if isinstance(oe, (int, float)) and oe > 0 else None
        return {"reward": rew, "recovery": rec, "needs_human": rec is not None and rec > 2}
    if k == "fix":
        ok = bool(row.get("f2p_pass")) and bool(row.get("p2p_pass"))
        return {"reward": 1.0 if ok else 0.0, "f2p": float(row.get("f2p") or 0.0)}
    if k == "neg":
        dec = 1.0 if row.get("decision") == task.get("oracle_decision") else 0.0
        pred, meas = row.get("pred_effect_pct"), task.get("measured_effect_pct")
        est = 1 - min(1.0, abs(math.log(pred / meas))) if isinstance(pred, (int, float)) and pred > 0 and meas else 0.0
        return {"reward": dec, "estimate": est}
    raise ValueError(f"kind {k!r}")


def run_plan(task_ids) -> list:
    """Commands the PLANNER runs after the agent phase. aob itself never launches GPU work."""
    out = []
    for tid in task_ids:
        t = load_task(tid)
        d = Path(t["dir"])
        if t["kind"] == "neg":
            out.append({"task": tid, "gpu": False, "cmd": ["score-answer", tid], "note": "CPU only, scored by reward()"})
            continue
        cid = f"claims/<date>-aob-{tid.replace('_', '-')}.json"
        out.append({"task": tid, "gpu": False, "cmd": ["bash", str(d / "tests" / "cpu_tier.sh")], "status": t["status"]})
        out.append({"task": tid, "gpu": False, "cmd": ["./factory", "card", "fill", cid]})
        out.append({"task": tid, "gpu": False, "cmd": ["./factory", "register", cid]})
        out.append({"task": tid, "gpu": True, "gpu_minutes": t["gpu_minutes"], "cmd": ["./factory", "verify", cid]})
    return out


def leak_texts(split: str = "test", repo=None) -> dict:
    """Oracle diff texts of the split, for the RSI-F leak reviewer (8-grams, threshold 0). Missing commits skipped."""
    repo = Path(repo or DEFAULT_REPO)
    out = {}
    for tid in list_tasks():
        t = load_task(tid)
        b, o = _none(t.get("base_commit")), _none(t.get("oracle_commit"))
        if t["split"] != split or not (b and o):
            continue
        try:
            r = subprocess.run(["git", "-C", str(repo), "diff", b, o], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0:
            out[tid] = r.stdout
    return out
