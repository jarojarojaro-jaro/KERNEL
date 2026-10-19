"""`factory rsi ...`: the RSI-F loop on top of factory v1 (report 21h §5; README §12).

  rsi gates [--card CARD] [--json]                 live hardware gates H0-H11 (nothing started)
  rsi hw status | ack --reason TEXT [--by NAME]    fault watermark / halt / quarantine; ack = a human read the faults
  rsi approve --verdict-seq N --by NAME --reason T human approval of a NEEDS-HUMAN verdict (ledger note)
  rsi playbook new FILE [--by NAME]                draft from a JSON file (source must be a real CONFIRMED verdict)
  rsi playbook check FILE --repo R --base B --cand C [--source-seq N]   no-diff review of any text, nothing written
  rsi playbook review ID --repo R --base B --cand C --reviewer NAME --verdict pass|revise|reject [--notes T]
  rsi playbook accept ID | reject ID --reason T | list | show ID
  rsi transfer brief --target T --arm A|B --agent NAME --card-id ID [--playbook ID] --repo R --base B --cand C
                     [--minutes M]                 generate + review + ledger-pin a brief for a fresh agent
  rsi transfer effort --target T --arm A|B --agent NAME --minutes M [--tokens N] [--tool-calls N]
  rsi transfer score --targets T1,T2 [--review-passed yes|no]
  rsi calib [--write]                              predicted vs measured, abs error, Brier, prior P(CONFIRMED)
  rsi sealed rotate --cycle N [--dry-run]          activate the next pool set (then: harness lock)
  rsi cycle PLAN --dry-run | --go [--open] [--stop-topka]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import calib, cycle, diffscan, hwgates, paths, sealed, transfer
from . import playbook as pbm
from .ledger import Ledger


def _diff(a) -> str:
    return diffscan.git_diff(a.repo, a.base, a.cand)


def main(argv, ledger=None) -> int:
    ap = argparse.ArgumentParser(prog="factory rsi", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="area", required=True)
    s = sub.add_parser("gates")
    s.add_argument("--card")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("hw")
    s.add_argument("action", choices=["status", "ack"])
    s.add_argument("--reason", default="")
    s.add_argument("--by", default=os.environ.get("USER", "?"))
    s = sub.add_parser("approve")
    s.add_argument("--verdict-seq", type=int, required=True)
    s.add_argument("--by", required=True)
    s.add_argument("--reason", required=True)
    s = sub.add_parser("playbook")
    s.add_argument("action", choices=["new", "check", "review", "accept", "reject", "list", "show"])
    s.add_argument("arg", nargs="?")
    for k in ("repo", "base", "cand", "reviewer", "notes", "reason"):
        s.add_argument(f"--{k}", default="")
    s.add_argument("--verdict", choices=["pass", "revise", "reject"])
    s.add_argument("--source-seq", type=int)
    s.add_argument("--by", default=os.environ.get("USER", "?"))
    s = sub.add_parser("transfer")
    s.add_argument("action", choices=["brief", "effort", "score"])
    for k in ("target", "arm", "agent", "card-id", "playbook", "repo", "base", "cand", "targets", "review-passed"):
        s.add_argument(f"--{k}", default=None)
    s.add_argument("--minutes", type=float, default=90)
    s.add_argument("--tokens", type=int)
    s.add_argument("--tool-calls", type=int)
    s = sub.add_parser("calib")
    s.add_argument("--write", action="store_true")
    s = sub.add_parser("sealed")
    s.add_argument("action", choices=["rotate"])
    s.add_argument("--cycle", type=int, required=True)
    s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("cycle")
    s.add_argument("plan")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--go", action="store_true")
    s.add_argument("--open", action="store_true")
    s.add_argument("--stop-topka", action="store_true")
    s.add_argument("--by", default=os.environ.get("USER", "?"))
    s = sub.add_parser("workspace")
    s.add_argument("--repo", required=True)
    s.add_argument("--commit", required=True)
    s.add_argument("--dest", required=True)
    s = sub.add_parser("aob")
    s.add_argument("action", choices=["list", "validate", "plan"])
    s.add_argument("tasks", nargs="*")
    a = ap.parse_args(argv)
    led = Ledger(ledger or paths.LEDGER)
    out = lambda x: print(json.dumps(x, indent=1, ensure_ascii=False, default=str))  # noqa: E731

    if a.area == "workspace":
        print(transfer.snapshot(a.repo, a.commit, a.dest))
        return 0
    if a.area == "aob":
        from . import aob
        ids = a.tasks or aob.list_tasks()
        if a.action == "list":
            out([{"id": t, **{k: aob.load_task(t).get(k) for k in ("kind", "split", "profile", "gpu_minutes",
                                                                    "status")}} for t in ids])
            return 0
        if a.action == "validate":
            bad = {t: aob.validate_task(aob.load_task(t)) for t in ids}
            out(bad)
            return 1 if any(bad.values()) else 0
        out(aob.run_plan(ids))
        return 0
    if a.area == "gates":
        ctx = {"env": dict(paths.HW_ENV)}
        if a.card:
            from . import card as card_mod
            c = card_mod.load(a.card)
            ctx.update(card=c, builds=sorted({(c.get("builds") or {}).get(x, {}).get("dir") for x in ("base", "cand")}
                                            - {None, ""}))
        facts = hwgates.collect(ctx)
        bad = hwgates.check(facts)
        if a.json:
            out({"fire": bad, "facts": {k: v for k, v in facts.items() if k not in ("texts", "quarantine")}})
        else:
            for gname in hwgates.GATES:
                print(f"{gname:4} {'FIRE ' + '; '.join(bad[gname]) if gname in bad else 'ok'}")
        return 1 if bad else 0
    if a.area == "hw":
        if a.action == "status":
            st = hwgates.load_state()
            out({"state": st, "quarantine": list(hwgates.quarantined().values()),
                 "gpu_min_24h": round(hwgates.gpu_seconds(86400) / 60, 1),
                 "gpu_h_30d": round(hwgates.gpu_seconds(30 * 86400) / 3600, 2),
                 "new_faults": hwgates.kernel_faults(st["watermark"]) if st.get("watermark") else "not initialized"})
            return 0
        r = hwgates.ack(a.reason, a.by)
        row = led.append({"kind": "note", "note": "hw-ack", "by": a.by, "reason": a.reason, **r})
        out({**r, "ledger_seq": row["seq"]})
        return 0
    if a.area == "approve":
        rows = led.rows()
        if a.verdict_seq >= len(rows) or rows[a.verdict_seq].get("verdict") != "NEEDS-HUMAN":
            sys.exit(f"seq {a.verdict_seq} is not a NEEDS-HUMAN verdict")
        row = led.append({"kind": "note", "note": "human-approval", "verdict_seq": a.verdict_seq, "by": a.by,
                          "reason": a.reason, "verdict_sha256": rows[a.verdict_seq]["sha256"]})
        print(f"approval of seq {a.verdict_seq} -> ledger seq {row['seq']}")
        return 0
    if a.area == "playbook":
        try:
            if a.action == "new":
                pb = pbm.create(json.loads(open(a.arg).read()), led, a.by)
                print(f"{pb['id']}: draft -> {pbm.path_of(pb['id'])}")
            elif a.action == "check":
                rows = led.rows()
                text = open(a.arg).read()
                if a.arg.endswith(".json"):
                    text = pbm.text_of(json.loads(text))
                src = rows[a.source_seq] if a.source_seq is not None else None
                rev = pbm.review(text, _diff(a), src)
                out(rev)
                return 0 if rev["pass"] else 1
            elif a.action == "review":
                pb = pbm.do_review(a.arg, led, _diff(a), a.reviewer, a.verdict, a.notes)
                out({"id": pb["id"], "status": pb["status"], "auto": pb["review"]["auto"]})
            elif a.action == "accept":
                pb = pbm.accept(a.arg, led, a.by)
                print(f"{pb['id']}: accepted ({pb['transfers'][-1]})")
            elif a.action == "reject":
                pbm.reject(a.arg, led, a.by, a.reason)
            elif a.action == "list":
                out(pbm.library(led))
            elif a.action == "show":
                print(pbm.render(pbm.load(a.arg)))
        except pbm.PlaybookError as e:
            print(f"refused: {e}")
            return 1
        return 0
    if a.area == "transfer":
        if a.action == "brief":
            try:
                r = transfer.issue(a.target, a.arm, a.agent, a.card_id, led, _diff(a), a.playbook, int(a.minutes),
                                   by=os.environ.get("USER", "?"))
            except pbm.PlaybookError as e:
                print(f"refused: {e}")
                return 1
            out(r)
            return 0
        if a.action == "effort":
            f = paths.RSI / "transfer-effort.jsonl"
            f.parent.mkdir(parents=True, exist_ok=True)
            with open(f, "a") as fh:
                fh.write(json.dumps({"target": a.target, "arm": a.arm, "agent": a.agent, "minutes": a.minutes,
                                     "tokens": a.tokens, "tool_calls": a.tool_calls, "ts": hwgates.utcnow()}) + "\n")
            return 0
        rp = None if a.review_passed is None else a.review_passed == "yes"
        st = hwgates.load_state()
        out(transfer.score(a.targets.split(","), led, faults=[st["halt"]] if st.get("halt") else [],
                           review_passed=rp))
        return 0
    if a.area == "calib":
        if a.write:
            out(calib.log(led))
        else:
            es = calib.entries(led.rows())
            out({"entries": es, "summary": calib.summary(es)})
        return 0
    if a.area == "sealed":
        r = sealed.rotate(a.cycle, dry_run=a.dry_run)
        out(r)
        if not a.dry_run:
            print("harness changed: run `factory harness lock --reason 'sealed rotation ...'`")
        return 0
    if a.area == "cycle":
        plan = cycle.load_plan(a.plan)
        try:
            if a.dry_run:
                cycle.dry_run(plan, led)
            elif a.open:
                cycle.open_cycle(plan, led, a.by)
            else:
                r = cycle.run(plan, led, a.by, stop_topka=a.stop_topka)
                return 0 if not r.get("stopped") else 1
        except cycle.CycleError as e:
            print(f"refused: {e}")
            return 1
        return 0
    return 2
