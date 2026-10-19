#!/usr/bin/env python3
"""Factory v1: claim cards, hash-chained ledger, isolated verifier. User guide (PL): README.md.

  factory.py card new ID --author NAME            template claims/ID.json
  factory.py card fill CARD --base-build D --cand-build D --repo R --base SHA --cand SHA
                                                   sha256 of builds and model, touched_paths from the diff
  factory.py card check CARD                      schema + static gate (no GPU)
  factory.py register CARD                        freeze the card (ledger row) BEFORE any measurement
  factory.py verify CARD [--dry-run | --fake]     gates G0-G5 -> verdict row (only writer of the ledger)
  factory.py ledger verify | show [--claim ID]    chain check / rows
  factory.py report [--out FILE] [--drafts]       markdown for the wiki (+ wiki-drafts/ notes)
  factory.py rules list | test | backtest JSONL | text FILE.md
  factory.py sealed check | summary               seal of the held-out set (counts only)
  factory.py harness status | lock --reason TEXT  pin the harness hash (planner only)
  factory.py merge-check COMMIT [--repo R]        exit 0 only with a CONFIRMED verdict and no UNMEASURED
  factory.py rsi ...                              RSI-F loop (report 21h): `factory rsi -h`, fk/rsicli.py
  factory.py preserve RUNDIR | check ID | restore ID DEST   sha256-addressed compressed evidence (fk/evidence.py)
Common: --ledger PATH (default ledger.jsonl; --fake uses ledger.fake.jsonl).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rules  # noqa: E402
from fk import card as card_mod  # noqa: E402
from fk import diffscan, hashing, paths, profiles, report, sealed  # noqa: E402
from fk.ledger import Ledger  # noqa: E402


def ledger_of(a, fake=False) -> Ledger:
    return Ledger(a.ledger or (paths.LEDGER_FAKE if fake else paths.LEDGER))


def cmd_card(a):
    if a.action == "new":
        p = paths.CLAIMS / f"{a.id}.json"
        if p.exists():
            sys.exit(f"{p} exists")
        c = card_mod.template(a.id, a.author, time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        p.write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
        print(p)
        return 0
    p = Path(a.card)
    c = card_mod.load(p)
    if a.action == "fill":
        c["builds"] = {arm: {"dir": str(Path(d).resolve()), "sha256": hashing.hash_build(d)}
                       for arm, d in (("base", a.base_build), ("cand", a.cand_build))}
        prof = profiles.PROFILES[c["profile"]]
        c["model_sha256"] = hashing.sha256_file(a.model or prof["gguf"])
        if a.repo:
            c["repo"] = str(Path(a.repo).resolve())
            c["commits"] = {"base": a.base, "cand": a.cand}
            c["touched_paths"] = diffscan.touched(diffscan.parse_unified(diffscan.git_diff(a.repo, a.base, a.cand)))
        p.write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
        print(f"filled {p}: {len(c['builds']['cand']['sha256'])} files per build, touched {c.get('touched_paths')}")
        return 0
    if a.action == "check":
        probs = card_mod.validate(c)
        ctx = {"card": c, "profile": profiles.PROFILES.get(c.get("profile"), {})}
        if c.get("repo") and (c.get("commits") or {}).get("cand"):
            try:
                ctx["diff"] = diffscan.git_diff(c["repo"], c["commits"]["base"], c["commits"]["cand"])
            except RuntimeError as e:
                probs.append(str(e))
        found = rules.run("static", ctx)
        for x in probs:
            print(f"problem: {x}")
        for f in found:
            print(f"{f.rule} [{f.severity}/{f.verdict}] {f.message}")
        print(f"card sha256 {card_mod.card_sha(c)}: " + ("OK" if not probs and not rules.blocking(found) else "NOT OK"))
        return 0 if not probs and not rules.blocking(found) else 1


def cmd_register(a):
    c = card_mod.load(a.card)
    probs = card_mod.validate(c)
    if probs:
        print("\n".join(f"problem: {x}" for x in probs))
        return 1
    led = ledger_of(a)
    sha = card_mod.card_sha(c)
    if led.registration(c["id"], sha):
        print(f"already registered: {c['id']} {sha[:12]}")
        return 0
    if any(r.get("kind") == "register" and r.get("claim_id") == c["id"] for r in led.rows()):
        print(f"note: {c['id']} was registered with other content before; the new version gets its own row")
    r = led.append({"kind": "register", "claim_id": c["id"], "claim_sha256": sha, "card": c, "author": c.get("author")})
    print(f"registered {c['id']} sha256 {sha[:12]} -> {led.path} seq {r['seq']}")
    return 0


def cmd_verify(a):
    from fk.verify import Verification
    mode = "dry" if a.dry_run else "fake" if a.fake else "real"
    if mode == "real" and not (paths.PORT_MIN <= a.port <= paths.PORT_MAX):
        sys.exit(f"port {a.port} outside {paths.PORT_MIN}-{paths.PORT_MAX}")
    fake = None
    if mode == "fake":
        fake = {"effect_pct": a.fake_effect, "noise_pct": a.fake_noise, "md5_diff": a.fake_md5_diff}
    v = Verification(a.card, mode=mode, ledger_path=a.ledger, rounds=a.rounds, port=a.port, pause_s=a.pause,
                     ci=a.ci, fake=fake, model_path=a.model)
    res = v.run()
    if mode == "dry":
        print(f"# {len(res['plan'])} GPU blocks planned, <= {paths.BLOCK_TIMEOUT_S} s each, {a.pause:g} s pauses")
        return 0 if not res["reasons"] else 1
    print(json.dumps({k: res.get(k) for k in ("verdict", "stat_verdict", "median", "ci95", "mde_pct", "seq",
                                              "written")}, ensure_ascii=False))
    return 0 if res.get("verdict") == "CONFIRMED" else 1


def cmd_ledger(a):
    led = ledger_of(a)
    if a.action == "verify":
        p = led.verify()
        print("\n".join(p) if p else f"{led.path}: chain OK ({len(led.rows())} rows)")
        return 1 if p else 0
    for r in led.rows():
        if a.claim and r.get("claim_id") != a.claim:
            continue
        print(json.dumps({k: r.get(k) for k in ("seq", "ts", "kind", "claim_id", "verdict", "median", "ci95",
                                                "sha256")}, ensure_ascii=False))
    return 0


def cmd_report(a):
    led = ledger_of(a)
    rows = led.rows()
    md = report.render(rows, led.verify())
    if a.out:
        Path(a.out).write_text(md)
        print(f"wrote {a.out}")
    else:
        print(md)
    if a.drafts:
        paths.WIKI_DRAFTS.mkdir(exist_ok=True)
        for r in rows:
            if r.get("kind") == "verdict" and r.get("mode") == "real":
                name, note = report.wiki_draft(r)
                (paths.WIKI_DRAFTS / name).write_text(note)
                print(f"draft {paths.WIKI_DRAFTS / name}")
    return 0


def cmd_rules(a):
    rs = rules.load_rules()
    if a.action == "list":
        for r in rs:
            p = r.policy
            print(f"{p.id} {p.name:26} {','.join(p.stage):22} {p.severity:5} {p.verdict:11} {p.failure_mode:6} "
                  f"{p.lesson}")
        return 0
    if a.action == "test":
        bad = 0
        for r in rs:
            for c in rules.load_fixture(r.policy.id):
                got = r.check(c["ctx"])
                ok = bool(got) == (c["expect"] == "fire")
                bad += not ok
                print(f"{'ok ' if ok else 'BAD'} {r.policy.id} {c['expect']:5} {c.get('kind', ''):13} {c['name']}")
        print(f"{bad} mismatches")
        return 1 if bad else 0
    if a.action == "backtest":
        rows = [json.loads(l) for l in Path(a.file).read_text().splitlines() if l.strip()]
        from rules.r21_anomaly_breaker import history_flags
        flags = history_flags(rows)
        for i, v, m in flags:
            print(f"R21 row {i} {rows[i].get('label', '')[:50]!r} T={rows[i].get('temp')}: {v:.1f} t/s vs median {m:.1f}")
        f20 = [f for f in rules.run("history", {"history": rows}) if f.rule == "R20"]
        for f in f20:
            print(f"R20 {f.message}")
        print(f"{len(rows)} rows: R21 {len(flags)} flags, R20 {len(f20)} labels")
        return 0
    if a.action == "text":
        found = rules.run("text", {"text": Path(a.file).read_text()})
        for f in found:
            print(f"{f.rule} {f.message}")
        return 1 if found else 0


def cmd_sealed(a):
    try:
        d = sealed.check_seal()
    except sealed.SealError as e:
        print(e)
        return 1
    if a.action == "summary":
        print(json.dumps(sealed.summary(sealed.load_sealed()), ensure_ascii=False))
    print(f"{sealed.active()['id']}: sha256 {d} (pinned in sealed/registry.json) OK")
    return 0


def cmd_harness(a):
    led = ledger_of(a)
    files = hashing.hash_harness()
    tree = hashing.tree_sha(files)
    lock = led.last_harness_lock()
    if a.action == "status":
        if lock and lock["tree_sha256"] == tree:
            print(f"harness {tree[:12]} = lock seq {lock['seq']}")
            return 0
        old = (lock or {}).get("files", {})
        for k in sorted(set(files) | set(old)):
            if files.get(k) != old.get(k):
                print(f"changed: {k}")
        print(f"harness {tree[:12]} not locked")
        return 1
    if not a.reason:
        sys.exit("--reason is required (what changed and who approved it)")
    r = led.append({"kind": "harness-lock", "tree_sha256": tree, "files": files, "reason": a.reason,
                    "by": os.environ.get("USER", "?")})
    paths.HARNESS_LOCK.write_text(json.dumps({"tree_sha256": tree, "seq": r["seq"], "files": files}, indent=1) + "\n")
    print(f"harness {tree[:12]} locked at {led.path} seq {r['seq']}")
    return 0


def cmd_merge_check(a):
    led = ledger_of(a)
    msg = diffscan.git_message(a.repo, a.commit) if a.repo else ""
    found = rules.run("merge", {"commit": a.commit, "commit_message": msg, "ledger_rows": led.rows()})
    for f in found:
        print(f"{f.rule} {f.message}")
    print("merge: " + ("BLOCKED" if found else "OK"))
    return 1 if found else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--ledger", default=argparse.SUPPRESS, help="ledger path (default ledger.jsonl)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    _add = sub.add_parser
    sub.add_parser = lambda *x, **k: _add(*x, parents=[common], **k)
    s = sub.add_parser("card")
    s.add_argument("action", choices=["new", "fill", "check"])
    s.add_argument("card", nargs="?")
    s.add_argument("--id")
    s.add_argument("--author", default=os.environ.get("USER", "agent"))
    for k in ("base-build", "cand-build", "repo", "base", "cand", "model"):
        s.add_argument(f"--{k}")
    s = sub.add_parser("register")
    s.add_argument("card")
    s = sub.add_parser("verify")
    s.add_argument("card")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--fake", action="store_true")
    s.add_argument("--rounds", type=int, default=2)
    s.add_argument("--port", type=int, default=paths.DEFAULT_PORT)
    s.add_argument("--pause", type=float, default=paths.PAUSE_S)
    s.add_argument("--ci", choices=["t", "bootstrap"], default="t")
    s.add_argument("--model", help="model path override (tests)")
    s.add_argument("--fake-effect", type=float, default=0.5)
    s.add_argument("--fake-noise", type=float, default=0.04)
    s.add_argument("--fake-md5-diff", action="store_true")
    s = sub.add_parser("ledger")
    s.add_argument("action", choices=["verify", "show"])
    s.add_argument("--claim")
    s = sub.add_parser("report")
    s.add_argument("--out")
    s.add_argument("--drafts", action="store_true")
    s = sub.add_parser("rules")
    s.add_argument("action", choices=["list", "test", "backtest", "text"])
    s.add_argument("file", nargs="?")
    s = sub.add_parser("sealed")
    s.add_argument("action", choices=["check", "summary"])
    s = sub.add_parser("harness")
    s.add_argument("action", choices=["status", "lock"])
    s.add_argument("--reason")
    s = sub.add_parser("merge-check")
    s.add_argument("commit")
    s.add_argument("--repo")
    s = sub.add_parser("_block")
    s.add_argument("spec")
    s = sub.add_parser("rsi", help="RSI-F: hw gates, playbooks, transfer, calibration, sealed rotation, cycle "
                                   "(fk/rsicli.py)")
    s.add_argument("rest", nargs=argparse.REMAINDER)
    s = sub.add_parser("preserve")
    s.add_argument("target", help="run directory to store, or `check` / `restore`")
    s.add_argument("arg", nargs="*")
    a = ap.parse_args(argv)
    if a.cmd == "card" and a.action == "new" and not a.id:
        a.id = a.card
    if a.cmd == "card" and a.action == "new" and not a.id:
        ap.error("card new needs an ID")
    if a.cmd == "card" and a.action != "new" and not a.card:
        ap.error("card fill/check needs CARD")
    if a.cmd == "_block":
        from fk import block
        return block.main(a.spec)
    if a.cmd == "preserve":
        from fk import evidence
        if a.target == "check":
            probs = evidence.verify_evidence(a.arg[0])
            print("\n".join(probs) or f"{a.arg[0]}: OK")
            return 1 if probs else 0
        if a.target == "restore":
            evidence.restore(a.arg[0], Path(a.arg[1]))
            return 0
        print(json.dumps(evidence.preserve(Path(a.target)), default=str))
        return 0
    if a.cmd == "rsi":
        from fk import rsicli
        return rsicli.main(a.rest, ledger=a.ledger)
    return {"card": cmd_card, "register": cmd_register, "verify": cmd_verify, "ledger": cmd_ledger,
            "report": cmd_report, "rules": cmd_rules, "sealed": cmd_sealed, "harness": cmd_harness,
            "merge-check": cmd_merge_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
