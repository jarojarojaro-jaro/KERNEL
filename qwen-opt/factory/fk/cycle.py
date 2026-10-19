"""`factory rsi cycle PLAN --dry-run | --go [--open] [--stop-topka]`: one RSI-F cycle (report 21h §5.3).

PLAN (rsi/cycles/<name>.json): {"cycle": N, "name", "rotate_sealed": bool, "cards": [claims/...json],
"targets": [transfer target ids to score], "playbooks": [ids], "review_passed": bool | null}

--dry-run  everything that would happen, nothing written, no process touched: live hardware gates H0-H11, the critic
           (calibration prior), the ranked queue with GPU minutes against the H6 budget, sealed rotation status, the
           GPU blocks of every card (verify --dry-run), playbook library and transfer scores.
--go --open  start the cycle: rotate the sealed set (if the plan says so and the cycle has not rotated yet) and lock
           the harness with that reason; records rsi/cycles/<name>.state.json. Cards are written after this.
--go       verification phase: refuses unless the hardware gates pass (H8 may be cleared with --stop-topka: every GPU
           block then stops the user's server INSIDE its lock hold; topka-keeper restarts it once the lock is free);
           (each block re-checks H0-H11); stops at the first hardware stop (H3) or when H6 says the budget is spent;
           then logs calibration, scores transfers (k1-k3), tries playbook promotions and writes
           rsi/cycles/<name>.result.json with the meta metrics.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

from . import calib, card as card_mod, hashing, hwgates, paths, sealed, transfer
from . import playbook as pbm
from .ledger import Ledger


class CycleError(Exception):
    pass


def load_plan(p) -> dict:
    plan = json.loads(Path(p).read_text())
    for k in ("cycle", "name", "cards"):
        if k not in plan:
            raise CycleError(f"plan: missing {k}")
    return plan


def state_path(plan) -> Path:
    return paths.RSI / "cycles" / f"{plan['name']}.state.json"


def load_cycle_state(plan) -> dict:
    p = state_path(plan)
    return json.loads(p.read_text()) if p.exists() else {}


def save_cycle_state(plan, st):
    p = state_path(plan)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, indent=1) + "\n")


# ---------------------------------------------------------------------------------------------- topka (:8080)
def user_server_pids() -> list[int]:
    r = subprocess.run(["ss", "-ltnpH", f"sport = :{paths.USER_PORT}"], capture_output=True, text=True)
    return sorted({int(x) for x in re.findall(r"pid=(\d+)", r.stdout)})


def stop_user_server(log=print, wait_s=60) -> list[dict]:
    """SIGTERM the llama-server listening on :8080 (refuses anything that is not a llama-server)."""
    stopped = []
    for pid in user_server_pids():
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        except OSError:
            continue
        if "llama-server" not in cmd:
            raise CycleError(f":{paths.USER_PORT} is held by pid {pid} `{cmd[:80]}`, not a llama-server: not touching it")
        log(f"  stopping the user's server pid {pid}: {cmd[:120]}")
        os.kill(pid, signal.SIGTERM)
        stopped.append({"pid": pid, "cmd": cmd})
    t = time.time()
    while preflight_listening() and time.time() - t < wait_s:
        time.sleep(3)
    for s in stopped:
        if Path(f"/proc/{s['pid']}").exists():
            os.kill(s["pid"], signal.SIGKILL)
    if stopped:
        time.sleep(5)  # let the driver release VRAM
    return stopped


def preflight_listening() -> bool:
    from .preflight import user_server_listening
    return user_server_listening()


# ---------------------------------------------------------------------------------------------- phases
def gate_report(cards: list[dict]) -> dict:
    """Live gates per card (the block environment the factory would use)."""
    out = {}
    for c in cards:
        dirs = sorted({(c.get("builds") or {}).get(a, {}).get("dir") for a in ("base", "cand")} - {None, ""})
        facts = hwgates.collect({"env": dict(paths.HW_ENV), "card": c, "builds": dirs})
        out[c["id"]] = hwgates.check(facts)
    return out


def budget_minutes(card_paths: list, ledger_path, verify_kw=None) -> dict:
    """GPU minutes per card from its dry-run block plan: blocks x (bench ~45 s, ops ~90 s, greedy/serve ~180 s)."""
    from .verify import Verification
    per = {"bench": 0.75, "ops": 1.5, "greedy": 2.5, "probe": 1.5, "serve": 3.0, "neartie": 2.0, "kld": 3.0}
    out = {}
    for p in card_paths:
        v = Verification(p, mode="dry", ledger_path=ledger_path, log=lambda *a: None, **(verify_kw or {}))
        res = v.run()
        gpu = sum(per.get(b["kind"], 3.0) for b in res["plan"])
        out[v.card["id"]] = {"blocks": len(res["plan"]), "gpu_min": round(gpu, 1),
                             "wall_min": round(gpu + max(0, len(res["plan"]) - 1) * paths.PAUSE_S / 60, 1),
                             "dry_reasons": res["reasons"]}
    return out


def dry_run(plan: dict, led: Ledger, log=print, verify_kw=None) -> dict:
    cards = [card_mod.load(p) for p in plan["cards"]]
    cal = calib.summary(calib.entries(led.rows()))
    mins = budget_minutes(plan["cards"], led.path, verify_kw)
    ranked = calib.rank(cards, cal["prior_p_confirmed"], {k: v["gpu_min"] for k, v in mins.items()})
    gates = gate_report(cards)
    st = load_cycle_state(plan)
    rot = None
    if plan.get("rotate_sealed") and not st.get("rotated"):
        try:
            rot = sealed.rotate(plan["cycle"], dry_run=True)
        except sealed.SealError as e:
            rot = {"error": str(e)}
    used_day = hwgates.gpu_seconds(86400) / 60
    total = sum(v["gpu_min"] for v in mins.values())
    rep = {"cycle": plan["cycle"], "name": plan["name"], "critic": cal, "queue": [
        {"id": c["id"], "score": round(s, 5), **mins[c["id"]]} for s, c in ranked], "gates": gates,
        "budget": {"day_used_min": round(used_day, 1), "planned_min": total, "day_limit_min": hwgates.DAY_GPU_S / 60,
                   "fits_today": used_day + total <= hwgates.DAY_GPU_S / 60},
        "sealed": {"active": sealed.active()["id"], "rotation": rot, "rotated": st.get("rotated")},
        "playbooks": pbm.library(led),
        "transfer": transfer.score(plan.get("targets") or [], led, review_passed=plan.get("review_passed"))
        if plan.get("targets") else None}
    log(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
    return rep


def open_cycle(plan: dict, led: Ledger, by: str, log=print) -> dict:
    st = load_cycle_state(plan)
    if st.get("opened"):
        log(f"cycle {plan['name']} already open since {st['opened']}")
        return st
    st = {"opened": hwgates.utcnow(), "cycle": plan["cycle"]}
    if plan.get("rotate_sealed"):
        r = sealed.rotate(plan["cycle"])
        files = hashing.hash_harness()
        row = led.append({"kind": "harness-lock", "tree_sha256": hashing.tree_sha(files), "files": files,
                          "reason": f"RSI-F cycle {plan['cycle']} ({plan['name']}): sealed rotation {r['from']} -> "
                                    f"{r['to']} ({by})", "by": by})
        paths.HARNESS_LOCK.write_text(json.dumps({"tree_sha256": row["tree_sha256"], "seq": row["seq"],
                                                  "files": files}, indent=1) + "\n")
        st["rotated"] = r
        log(f"sealed {r['from']} -> {r['to']} ({r['sha256'][:12]}), harness locked at seq {row['seq']}")
    save_cycle_state(plan, st)
    return st


def run(plan: dict, led: Ledger, by: str, stop_topka: bool = False, log=print, verify_kw=None) -> dict:
    from .verify import Verification
    st = load_cycle_state(plan)
    if plan.get("rotate_sealed") and not st.get("rotated"):
        raise CycleError("the plan rotates the sealed set: run `--go --open` before the cards are written")
    cards = [(p, card_mod.load(p)) for p in plan["cards"]]
    cal0 = calib.summary(calib.entries(led.rows()))
    ranked = calib.rank([c for _, c in cards], cal0["prior_p_confirmed"])
    order = [next(p for p, c in cards if c["id"] == rc["id"]) for _, rc in ranked]
    nulls = [p for p, c in cards if c.get("null_rebuild")]
    if not nulls and not plan.get("null_rebuild_waived"):
        raise CycleError("no null-rebuild card in the plan (21i A4: one noise probe per cycle; or "
                         "\"null_rebuild_waived\": \"reason\")")
    order = nulls + [p for p in order if p not in nulls]  # the noise probe first: it decides if the cycle may go on
    gates = gate_report([c for _, c in cards])
    blocking = {cid: {g: m for g, m in gs.items() if g not in hwgates.TRANSIENT and not (g == "H8" and stop_topka)}
                for cid, gs in gates.items()}
    blocking = {k: v for k, v in blocking.items() if v}
    if blocking:
        raise CycleError(f"hardware gates refuse the cycle: {json.dumps(blocking, ensure_ascii=False)[:600]}")
    res = {"cycle": plan["cycle"], "name": plan["name"], "started": hwgates.utcnow(), "critic_before": cal0,
           "verdicts": [], "stopped": None, "topka": {"stop_inside_blocks": stop_topka}}
    vids = []
    for p in order:
        c = card_mod.load(p)
        log(f"== verify {c['id']}")
        v = Verification(p, mode="real", ledger_path=led.path, log=log, stop_topka=stop_topka, **(verify_kw or {}))
        r = v.run()
        vids.append(v.vid)
        res["verdicts"].append({"claim_id": c["id"], "verdict": r.get("verdict"), "median": r.get("median"),
                                "ci95": r.get("ci95"), "seq": r.get("seq"), "refused": r.get("refused"),
                                "reasons": (r.get("reasons") or [])[-4:], "vid": v.vid})
        if c.get("null_rebuild") and r.get("stat_verdict") in ("CONFIRMED", "REGRESSION"):
            res["stopped"] = f"null-rebuild probe gave {r.get('stat_verdict')}: rebuild noise > MDE (21i A4)"
            break
        hw = hwgates.load_state()
        if hw.get("halt"):
            res["stopped"] = f"H3 halt: {hw['halt'].get('reason')}"
            break
        if hwgates.check(hwgates.collect({}), only=("H6",)):
            res["stopped"] = "H6 budget or hardware-INVALID streak"
            break
    res["finished"] = hwgates.utcnow()
    res["calibration"] = calib.log(led)
    rows = led.rows()
    secs = sum(r["secs"] for r in hwgates._jsonl("gpu-time.jsonl") if r.get("vid") in vids)
    conf = [v for v in res["verdicts"] if v["seq"] is not None and pbm.is_success(rows[v["seq"]], rows)]
    scored = [v for v in res["verdicts"] if v["verdict"] != "VOID"]
    inv = [v for v in scored if v["verdict"] == "INVALID"]
    res["meta"] = {"gpu_min": round(secs / 60, 1), "verdicts": len(res["verdicts"]), "void": len(res["verdicts"]) -
                   len(scored), "confirmed": len(conf),
                   "confirmed_per_gpu_h": len(conf) / (secs / 3600) if secs else None,
                   "gpu_min_per_confirmed": (secs / 60 / len(conf)) if conf else None,
                   "invalid_agent_rate": len(inv) / len(scored) if scored else None,
                   "median_abs_ratio": res["calibration"].get("median_abs_ratio"),
                   "reward_geomean_by_arm": reward_geomean(rows, [v["seq"] for v in scored if v["seq"] is not None])}
    if plan.get("targets"):
        faults = hwgates.load_state().get("halt")
        res["transfer"] = transfer.score(plan["targets"], led, faults=[faults] if faults else [],
                                         review_passed=plan.get("review_passed"))
    res["promotions"] = []
    for pid in plan.get("playbooks") or []:
        try:
            pb = pbm.accept(pid, led, by)
            res["promotions"].append({"playbook": pid, "status": pb["status"]})
        except pbm.PlaybookError as e:
            res["promotions"].append({"playbook": pid, "status": "unchanged", "why": str(e)[:300]})
    out = paths.RSI / "cycles" / f"{plan['name']}.result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str) + "\n")
    log(f"cycle result -> {out}")
    return res


def reward_geomean(rows: list[dict], seqs: list[int]) -> dict:
    """21i A5: arms are compared by the geomean of 1 + reward (reward > 0 only behind CONFIRMED)."""
    import math
    by = {}
    for s in seqs:
        r = rows[s]
        arm = ((r.get("card") or {}).get("rsi") or {}).get("arm", "-")
        by.setdefault(arm, []).append(1.0 + (r.get("reward") or 0.0))
    return {a: math.exp(sum(map(math.log, v)) / len(v)) for a, v in by.items()}
