"""Deterministic rules (KernelGuard pattern): each rule is a small check with a fixture from a real past incident.

A rule module rNN_slug.py defines
  POLICY = RulePolicy(...)     id, stage, severity, verdict, source (incident + file:line), lesson (wiki note)
  check(ctx) -> list[str]      messages; [] = clean or not applicable (missing ctx keys)
and has rules/fixtures/rNN.json: {"cases": [{"name", "expect": "fire"|"clean", "source", "ctx": {...},
"ctx_files": {key: "fixtures/<file>"}}]}; a .jsonl file loads as a list of rows, anything else as text.

ctx keys (all optional; a rule ignores a ctx without its keys):
  card, profile, diff (unified diff text), files_after {path: text}, server_argv {arm: argv}
  snapshot, snapshot_after              fk.preflight.snapshot()
  greedy {"base"|"cand"|"cand_off": {mode: md5}}, greedy_compared [[modeX, modeY]], greedy_requests [{pid, prompt}]
  kld {"base": meta, "cand": meta}      meta: {ctx, chunks, ppl_base, reference}
  runs [run]                            run: arm, round, pos, pid, session, ok, lib_sha256, build_info, request,
                                        argv, log_tail, telemetry {max_junction_c, max_gtt_used, max_vram_used},
                                        values {metric: value}, n_tokens {prompt: n}
  workload {"prompts": [{id, class, lang, domain}]}, history [spec_sweep rows], text, commit_message, ledger_rows,
  harness_before, harness_after, stage_info
Stages: static, preflight, correctness, measurement, physics, text, merge, history.
"""
from __future__ import annotations

import importlib
import json
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
STAGES = ("static", "preflight", "correctness", "measurement", "physics", "text", "merge", "history")


@dataclass(frozen=True)
class RulePolicy:
    id: str
    name: str
    stage: tuple
    severity: str          # block | warn
    verdict: str           # REFUSE (do not run) | INVALID | NEEDS-HUMAN
    source: str            # incident and where its artifact lives
    lesson: str = ""       # wiki note
    failure_mode: str = ""  # "07#8" = report 07 §2.2.4 failure mode 8, or "lekcja"


@dataclass
class Finding:
    rule: str
    name: str
    severity: str
    verdict: str
    message: str

    def as_dict(self):
        return dict(self.__dict__)


@dataclass
class Rule:
    policy: RulePolicy
    check: object
    module: str
    fixtures: list = field(default_factory=list)


def load_rules() -> list[Rule]:
    out = []
    for m in sorted(pkgutil.iter_modules([str(HERE)]), key=lambda m: m.name):
        if not m.name.startswith("r") or not m.name[1:3].isdigit():
            continue
        mod = importlib.import_module(f"rules.{m.name}")
        out.append(Rule(mod.POLICY, mod.check, m.name))
    ids = [r.policy.id for r in out]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"duplicate rule ids: {ids}")
    return out


def run(stage: str, ctx: dict, rules: list[Rule] | None = None) -> list[Finding]:
    assert stage in STAGES, stage
    out = []
    for r in rules or load_rules():
        if stage not in r.policy.stage:
            continue
        for msg in r.check(ctx) or []:
            out.append(Finding(r.policy.id, r.policy.name, r.policy.severity, r.policy.verdict, msg))
    return out


def blocking(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "block"]


def load_fixture(rule_id: str) -> list[dict]:
    p = FIXTURES / f"{rule_id.lower()}.json"
    data = json.loads(p.read_text())
    cases = []
    for c in data["cases"]:
        ctx = dict(c.get("ctx", {}))
        for key, rel in (c.get("ctx_files") or {}).items():
            f = HERE / rel
            if f.suffix == ".jsonl":
                ctx[key] = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            elif key == "files_after":
                raise ValueError("use ctx_files_after for files_after")
            else:
                ctx[key] = f.read_text()
        for path, rel in (c.get("ctx_files_after") or {}).items():
            ctx.setdefault("files_after", {})[path] = (HERE / rel).read_text()
        cases.append({**c, "ctx": ctx})
    return cases
