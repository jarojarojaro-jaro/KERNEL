"""`factory verify CARD`: the gate cascade, cheapest first; only this code writes verdict rows into the ledger.

G0 static      card schema, registration (frozen before measuring), ledger chain, sealed seal, harness lock, build and
               model sha256, diff deny-list, switch in diff/tree and compiled into the libs, static rules
G1 build/ops   test-backend-ops -o OP on the candidate (card.ops)
G2 correctness fusion/greedy.sh on fresh servers per mode; class BIT/SAME-TOK: md5 equal; NEAR-TIE: first divergence
               a tie (<= 0.1 logit); KLD: llama-perplexity + tools/kld_gate.py
G3 did it run  probe log (regex on, absent off) | md5 (switch off restores base md5) | timing (A arm = switch off)
G4 ABBA        fresh server per run, A B B A / B A A B, sealed + spec6 prompts, A/A from the two processes per arm
G5 physics     roofline per pass, Amdahl against attacked.share_ms, anomaly breaker
verdict        CONFIRMED | NULL | REFUTED | REGRESSION | INVALID | NEEDS-HUMAN  -> ledger row
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import statistics
import time
from pathlib import Path

import rules

from . import card as card_mod
from . import diffscan, hashing, neartie, paths, profiles, sealed, stats
from .gpu import Refused, Runner
from .ledger import Ledger

SERVE_METRICS = ("ms_step", "ms_token", "tok_step", "tps")
BENCH_METRICS = ("pp_tps", "tg_tps")


def load_kld_gate():
    spec = importlib.util.spec_from_file_location("kld_gate", paths.KLD_GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def set_values(rec: dict, set_name: str, variant: str = "plain") -> dict:
    ps = [p for p in (rec.get("prompts") or {}).values() if p["set"] == set_name and p["variant"] == variant]
    if not ps:
        return {}
    return {m: statistics.median(p[m] for p in ps) for m in SERVE_METRICS if all(m in p for p in ps)}


class Verification:
    def __init__(self, card_path, mode="real", ledger_path=None, rounds=2, port=paths.DEFAULT_PORT,
                 pause_s=paths.PAUSE_S, ci="t", log=print, fake=None, model_path=None):
        self.card_path = Path(card_path)
        self.card = card_mod.load(card_path)
        self.csha = card_mod.card_sha(self.card)
        self.mode, self.rounds, self.port, self.ci, self.log = mode, rounds, port, ci, log
        self.vid = time.strftime("%Y%m%d-%H%M%S") + "-" + str(self.card.get("id", "noid"))
        self.ledger = Ledger(ledger_path or (paths.LEDGER_FAKE if mode == "fake" else paths.LEDGER))
        self.rundir = None if mode == "dry" else paths.RUNS / self.vid
        if self.rundir:
            for d in ("blocks", "logs", "harness", "greedy"):
                (self.rundir / d).mkdir(parents=True, exist_ok=True)
        self.runner = Runner(mode, self.rundir / "blocks" if self.rundir else None, pause_s, log, fake)
        self.profile = profiles.PROFILES.get(self.card.get("profile"), {})
        self.model_path = Path(model_path or self.profile.get("gguf", "/nonexistent"))
        self.gates, self.findings, self.reasons, self.runs = {}, [], [], []
        self.refused = False

    # ------------------------------------------------------------------ helpers
    def p(self, rel):
        return str((self.rundir or Path(f"runs/{self.vid}")) / rel)

    def note(self, gate, msg):
        self.reasons.append(f"{gate}: {msg}")
        self.log(f"  {gate}: {msg}")

    def add_findings(self, gate, found):
        for f in found:
            self.findings.append({**f.as_dict(), "gate": gate})
            self.log(f"  {gate} {f.rule} [{f.severity}/{f.verdict}] {f.message}")
        return [f for f in found if f.severity == "block"]

    @property
    def sw(self):
        return self.card.get("switch") or {}

    def env_on(self):
        return {self.sw.get("name") or "SWITCH": str(self.sw.get("on"))}

    def env_off(self):
        return {self.sw.get("name") or "SWITCH": str(self.sw.get("off"))}

    def build(self, arm):
        return (self.card.get("builds") or {}).get(arm, {}).get("dir", "")

    def base_env(self):
        """G2 reference: the base build, or the candidate with the switch off when the card measures in one binary."""
        return self.env_off() if (self.card.get("probe") or {}).get("kind") == "timing" else {}

    def base_build(self):
        return self.build("cand") if (self.card.get("probe") or {}).get("kind") == "timing" else self.build("base")

    def arm_spec(self, arm):
        """(build dir, env) of the G4 arms; probe timing measures the switch inside the candidate binary."""
        if arm == "B":
            return self.build("cand"), self.env_on()
        if (self.card.get("probe") or {}).get("kind") == "timing":
            return self.build("cand"), self.env_off()
        return self.build("base"), {}

    # ------------------------------------------------------------------ G0
    def g0(self):
        self.log(f"G0 static ({self.card_path})")
        c = self.card
        problems = card_mod.validate(c)
        refuse = []
        chain = self.ledger.verify()
        if chain:
            refuse += [f"ledger: {x}" for x in chain]
        self.registration = self.ledger.registration(c.get("id"), self.csha)
        if not self.registration:
            refuse.append("card not registered (`factory register CARD` freezes it before measuring)")
        try:
            self.sealed_sha = sealed.check_seal()
        except sealed.SealError as e:
            self.sealed_sha = None
            refuse.append(str(e))
        self.harness = hashing.hash_harness()
        self.harness_tree = hashing.tree_sha(self.harness)
        lock = self.ledger.last_harness_lock()
        if not lock or lock.get("tree_sha256") != self.harness_tree:
            changed = sorted(k for k in set(self.harness) | set((lock or {}).get("files", {}))
                             if self.harness.get(k) != (lock or {}).get("files", {}).get(k))
            refuse.append(f"harness differs from the last harness-lock row: {changed[:6]} (`factory harness lock`)")
        # builds and model by sha256
        self.build_sha, mismatch = {}, {}
        for arm in ("base", "cand"):
            d = self.build(arm)
            if not d or not Path(d, "bin", "llama-server").exists():
                problems.append(f"build {arm}: {d!r} has no bin/llama-server")
                continue
            have = hashing.hash_build(d)
            want = (c.get("builds") or {}).get(arm, {}).get("sha256") or {}
            self.build_sha[arm] = have
            mismatch[arm] = sorted(k for k in set(have) | set(want) if have.get(k) != want.get(k))
        self.identity = {"sha_mismatch": mismatch}
        cand = self.build("cand")
        if cand and Path(cand, "lib").is_dir() and self.sw.get("name"):
            self.identity.update(switch=self.sw["name"], switch_hits=hashing.build_contains(cand, self.sw["name"]))
            commit = (c.get("commits") or {}).get("cand", "")
            if commit:
                self.identity.update(commit=commit, commit_hits=hashing.build_contains(cand, commit[:9]))
        base, bcommit = self.build("base"), (c.get("commits") or {}).get("base", "")
        if base and base != cand and bcommit and Path(base, "lib").is_dir():
            self.identity.update(base_commit=bcommit, base_commit_hits=hashing.build_contains(base, bcommit[:9]))
        if self.model_path.exists():
            self.model_sha = hashing.sha256_file(self.model_path)
            if self.model_sha != c.get("model_sha256"):
                problems.append(f"model {self.model_path.name}: sha256 {self.model_sha[:12]} != card")
        else:
            self.model_sha = None
            problems.append(f"model {self.model_path} missing")
        # the implementer's diff
        self.diff, self.files_after, self.hip_headers = None, {}, {}
        repo, cm = c.get("repo"), c.get("commits") or {}
        if repo and cm.get("base") and cm.get("cand"):
            try:
                self.diff = diffscan.git_diff(repo, cm["base"], cm["cand"])
                files = diffscan.parse_unified(self.diff)
                touched = diffscan.touched(files)
                if set(touched) != set(c.get("touched_paths") or []):
                    problems.append(f"touched_paths {sorted(c.get('touched_paths') or [])[:4]} != diff {touched[:4]}")
                name = self.sw.get("name", "")
                if name and name not in diffscan.added_text(files) and not diffscan.git_grep(repo, cm["cand"], name):
                    problems.append(f"switch {name} is neither in the diff nor in the candidate tree")
                for f in touched:
                    if f.endswith((".cu", ".cuh")):
                        src = diffscan.git_show(repo, cm["cand"], f)
                        if src is not None:
                            self.files_after[f] = src
                hdr = diffscan.git_show(repo, cm["cand"], "ggml/src/ggml-cuda/common.cuh")
                if hdr:
                    self.hip_headers["ggml/src/ggml-cuda/common.cuh"] = hdr
            except RuntimeError as e:
                problems.append(str(e))
        self.sealed_entries = sealed.load_sealed() if self.sealed_sha else []
        self.public_entries = sealed.load_public()
        self.touched = sorted(c.get("touched_paths") or [])
        from rules.r05_client_sampler import UI_VARIANT, needs_client_ui
        self.variants = ["plain"] + ([UI_VARIANT] if needs_client_ui(self.touched) else [])
        self.workload = {"prompts": [{"id": e["id"], "set": "sealed", "class": e["class"], "lang": e["lang"]}
                                     for e in self.sealed_entries] +
                                    [{"id": e["id"], "set": "public", "class": e["class"], "lang": e["lang"]}
                                     for e in self.public_entries],
                         "variants": self.variants}
        self.server_argv = {arm: profiles.server_argv(self.profile, f"{self.arm_spec(arm)[0]}/bin", self.port)
                            for arm in ("A", "B")} if self.profile else {}
        ctx = {"card": c, "profile": self.profile, "files_after": self.files_after, "hip_headers": self.hip_headers,
               "server_argv": self.server_argv, "identity": self.identity, "workload": self.workload}
        if self.diff is not None:
            ctx["diff"] = self.diff
        found = rules.run("static", ctx)
        refuse += [f"{f.rule} {f.message}" for f in found if f.verdict == "REFUSE" and f.severity == "block"]
        blocking = self.add_findings("G0", [f for f in found if f.verdict != "REFUSE"])
        for x in refuse:
            self.log(f"  G0 REFUSE {x}")
        for x in problems:
            self.log(f"  G0 problem {x}")
        self.gates["G0"] = {"problems": problems, "refused": refuse, "rules": [f.rule for f in found],
                            "identity": self.identity, "variants": self.variants, "touched": self.touched}
        if refuse:
            self.refused = True
            self.reasons += [f"G0 refused: {x}" for x in refuse]
        self.reasons += [f"G0: {x}" for x in problems] + [f"G0 {f.rule}: {f.message}" for f in blocking]
        return not (refuse or problems or blocking)

    # ------------------------------------------------------------------ G1
    def g1(self):
        ops = self.card.get("ops") or []
        self.log(f"G1 build/op tests ({len(ops)} ops)")
        res = {}
        on = self.env_on()
        for op in ops:
            name, _, params = op.partition("|")  # "MUL_MAT|type_a=q4_K": -o MUL_MAT -p type_a=q4_K
            tag = re.sub(r"[^A-Za-z0-9_]+", "_", op).strip("_")
            argv = [f"{self.build('cand')}/bin/test-backend-ops", "test", "-o", name] + (["-p", params] if params else [])
            r = self.runner.block({"kind": "ops", "name": f"ops-{tag}", "arm": "B", "argv": argv, "env": on,
                                   "lib_dir": f"{self.build('cand')}/lib", "log": self.p(f"logs/ops-{tag}.log")})
            res[op] = {"ok": r.get("ok"), "fails": r.get("fails"), "passed": r.get("passed")}
        self.gates["G1"] = {"ops": res, "note": None if ops else "no ops declared in the card"}
        bad = [op for op, r in res.items() if r["ok"] is False]
        for op in bad:
            self.note("G1", f"test-backend-ops -o {op} failed: {res[op]['fails'][:2]}")
        return not bad

    # ------------------------------------------------------------------ G2
    def greedy(self, tag, build, env):
        modes = self.profile["greedy_modes"]
        if self.rundir:
            sha = hashing.sha256_file(paths.GREEDY_SH, use_cache=False)
            script = self.rundir / "harness" / f"greedy.{sha[:12]}.sh"
            if not script.exists():
                shutil.copy2(paths.GREEDY_SH, script)  # R18: run a hash-named copy, never the live file
        else:
            sha, script = "<sha256>", Path(self.p("harness/greedy.<sha12>.sh"))
        r = self.runner.block({"kind": "greedy", "name": f"greedy-{tag}", "arm": "B" if tag == "cand" else "A",
                               "treated": tag == "cand", "script": str(script), "script_sha256": sha,
                               "bin_dir": f"{build}/bin", "lib_dir": f"{build}/lib",
                               "out_prefix": self.p(f"greedy/{tag}"), "model": self.profile["greedy_model"],
                               "modes": modes, "log": self.p(f"logs/greedy-{tag}.log"),
                               "env": {"PORT": str(self.port), "MODES": " ".join(modes), **env}})
        return r

    def g2(self):
        cls = self.card.get("correctness_class")
        self.log(f"G2 correctness ({cls})")
        on = self.env_on()
        self.greedy_res = {"base": self.greedy("base", self.base_build(), self.base_env()),
                           "cand": self.greedy("cand", self.build("cand"), on)}
        if self.mode == "dry":
            self.gates["G2"] = {"class": cls, "dry": True}
            if cls == "NEAR-TIE":
                self.log("  (if an md5 differs: neartie blocks for base and cand follow)")
            if cls == "KLD":
                self.kld_blocks()
            return True
        md5 = {k: (v.get("md5") or {}) for k, v in self.greedy_res.items()}
        modes = self.profile["greedy_modes"]
        ctx = {"card": self.card, "greedy": md5, "greedy_compared": [[m, m] for m in modes],
               "greedy_requests": [{"pid": f"{k}-{m}", "prompt": p} for k in md5 for m in modes for p in ("p0", "p1")],
               "runs": [{"arm": k, "round": 0, "pos": 0, "ok": v.get("ok"), "error": v.get("error"),
                         "log_tail": v.get("log_tail")} for k, v in self.greedy_res.items()]}
        blocking = self.add_findings("G2", rules.run("correctness", ctx))
        same = all(md5["base"].get(m) and md5["base"].get(m) == md5["cand"].get(m) for m in modes)
        g = {"class": cls, "md5": md5, "identical": same}
        ok = not blocking
        if cls == "NEAR-TIE" and not same:
            g["neartie"] = self.neartie([m for m in modes if md5["base"].get(m) != md5["cand"].get(m)])
            ok = ok and g["neartie"]["verdict"] == "PASS"
            if g["neartie"]["verdict"] != "PASS":
                self.note("G2", f"near-tie gate FAIL: {json.dumps(g['neartie']['prompts'])[:300]}")
        if cls == "KLD":
            g["kld"] = self.kld_blocks()
            ok = ok and g["kld"].get("verdict") in ("PASS", "IDENTICAL")
            if g["kld"].get("verdict") not in ("PASS", "IDENTICAL"):
                self.note("G2", f"KLD gate {g['kld'].get('verdict')}: {g['kld'].get('reasons')}")
        for f in blocking:
            self.reasons.append(f"G2 {f.rule}: {f.message}")
        self.gates["G2"] = g
        return ok

    def neartie(self, modes):
        prompts = ["Explain how a hash map works, then implement one in C with open addressing.",
                   "Napisz krótkie opowiadanie o latarniku i sztormie."]  # fusion/greedy.sh prompts
        out = {}
        on = self.env_on()
        for mode in modes:
            toks = {}
            for tag, build, env in (("base", self.base_build(), self.base_env()), ("cand", self.build("cand"), on)):
                argv = profiles.greedy_argv(self.profile, f"{build}/bin", self.port, mode)
                r = self.runner.block({"kind": "neartie", "name": f"neartie-{mode}-{tag}", "arm": "B" if tag == "cand"
                                       else "A", "treated": tag == "cand", "argv": argv, "env": env,
                                       "lib_dir": f"{build}/lib", "port": self.port, "prompts": prompts,
                                       "tokens": 400, "log": self.p(f"logs/neartie-{mode}-{tag}.log")})
                toks[tag] = r.get("tokens") or {}
            for k in toks["base"]:
                out[f"{mode}/{k}"] = (toks["base"][k], toks["cand"].get(k, []))
        return neartie.gate(out)

    def kld_blocks(self):
        k = self.profile.get("kld")
        if not k:
            self.note("G2", f"profile {self.card.get('profile')} has no KLD reference")
            return {"verdict": "ERROR", "reasons": ["no KLD reference for this profile"]}
        on = self.env_on()
        logs = {}
        for tag, build, env in (("base", self.base_build(), self.base_env()), ("cand", self.build("cand"), on)):
            log = self.p(f"logs/kld-{tag}.log")
            self.runner.block({"kind": "kld", "name": f"kld-{tag}", "arm": "B" if tag == "cand" else "A",
                               "treated": tag == "cand", "argv": profiles.perplexity_argv(self.profile, f"{build}/bin"),
                               "env": env, "lib_dir": f"{build}/lib", "log": log})
            logs[tag] = log
        if self.mode != "real":
            return {"verdict": "PASS" if self.mode == "fake" else None, "fake": True}
        kg = load_kld_gate()
        try:
            b, c = kg.parse(logs["base"]), kg.parse(logs["cand"])
        except kg.LogError as e:
            return {"verdict": "ERROR", "reasons": [str(e)]}
        meta = {t: {"ctx": k["ctx"], "chunks": x["chunks"], "ppl_base": list(x["ppl_base"])}
                for t, x in (("base", b), ("cand", c))}
        self.add_findings("G2", rules.run("correctness", {"kld": meta}))
        g = kg.gate(b, c)
        return {key: g[key] for key in g if key not in ("base", "cand")} | {"logs": logs}

    # ------------------------------------------------------------------ G3
    def g3(self):
        probe = self.card.get("probe") or {}
        kind = probe.get("kind")
        self.log(f"G3 did the change run (probe {kind})")
        g = {"kind": kind, "switch_hits": self.identity.get("switch_hits")}
        ok = True
        name, on, off = self.sw.get("name") or "SWITCH", str(self.sw.get("on")), str(self.sw.get("off"))
        if kind == "log":
            hits = {}
            for tag, val in (("on", on), ("off", off)):
                env = {name: val, **(probe.get("env") or {})}
                argv = profiles.server_argv(dict(self.profile, ctx=8192), f"{self.build('cand')}/bin", self.port)
                r = self.runner.block({"kind": "probe", "name": f"probe-{tag}", "arm": "B" if tag == "on" else "A",
                                       "treated": tag == "on", "argv": argv, "env": env, "regex": probe["regex"],
                                       "lib_dir": f"{self.build('cand')}/lib", "port": self.port,
                                       "log": self.p(f"logs/probe-{tag}.log")})
                hits[tag] = r.get("hit")
            g["hits"] = hits
            if self.mode != "dry":
                if not hits["on"]:
                    ok = False
                    self.note("G3", f"probe /{probe['regex']}/ not in the log with {name}={on}")
                if probe.get("absent_when_off", True) and hits["off"]:
                    ok = False
                    self.note("G3", f"probe /{probe['regex']}/ also with {name}={off}: the switch does not gate it")
        elif kind == "md5":
            r = self.greedy("cand_off", self.build("cand"), {name: off})
            g["md5_off"] = r.get("md5")
            if self.mode != "dry":
                base, cand = self.greedy_res["base"].get("md5") or {}, self.greedy_res["cand"].get("md5") or {}
                if r.get("md5") != base:
                    ok = False
                    self.note("G3", f"{name}={off} does not restore the base md5")
                if cand == base:
                    ok = False
                    self.note("G3", "the switch changes no md5: no visible effect, use probe log or timing")
        elif kind == "timing":
            g["note"] = f"G4 arm A = candidate with {name}={off}: the switch effect is the measured effect"
        self.gates["G3"] = g
        return ok

    # ------------------------------------------------------------------ G4
    def g4(self):
        metric = self.card["metric"]
        sched = stats.abba_schedule(self.rounds)
        self.log(f"G4 ABBA ({self.rounds} rounds, {len(sched)} fresh processes, metric {metric})")
        prompts = [{"set": "sealed", "entry": e} for e in self.sealed_entries] + \
                  [{"set": "public", "entry": e} for e in self.public_entries]
        for r, pos, arm in sched:
            build, env = self.arm_spec(arm)
            base = {"arm": arm, "round": r, "pos": pos, "treated": arm == "B", "lib_dir": f"{build}/lib",
                    "model_family": self.profile["model"], "log": self.p(f"logs/run-r{r}p{pos}{arm}.log")}
            if metric in BENCH_METRICS:
                spec = {**base, "kind": "bench", "name": f"bench-r{r}p{pos}{arm}", "metric": metric, "env": env,
                        "argv": profiles.bench_argv(self.profile, f"{build}/bin", metric)}
            else:
                spec = {**base, "kind": "serve", "name": f"serve-r{r}p{pos}{arm}", "port": self.port,
                        "argv": self.server_argv[arm], "env": {**profiles.SERVER_ENV, **env},
                        "protocol": profiles.PROTOCOL, "prompts": prompts, "variants": self.variants}
            res = self.runner.block(spec)
            if self.mode == "dry":
                continue
            run = {"arm": arm, "round": r, "pos": pos, "kind": spec["kind"], "pid": res.get("pid"), "session": self.vid,
                   "ok": bool(res.get("ok")) and not res.get("error"), "error": res.get("error"),
                   "lib_sha256": self.build_sha.get("cand" if build == self.build("cand") else "base"),
                   "build_info": res.get("build_info") or res.get("build_commit"), "request": res.get("request"),
                   "argv": spec.get("argv"), "env": spec.get("env"), "log": spec["log"],
                   "log_tail": res.get("log_tail"), "telemetry": res.get("telemetry"),
                   "n_tokens": res.get("n_tokens"), "text_sha256": res.get("text_sha256"),
                   "snapshot": res.get("snapshot"), "harness_before": res.get("harness_before"),
                   "harness_after": res.get("harness_after"), "secs": res.get("secs")}
            if metric in BENCH_METRICS:
                run["values"] = {metric: res["avg_ts"]} if "avg_ts" in res else {}
            else:
                run["values"] = set_values(res, "sealed")
                run["values_public"] = set_values(res, "public")
                if len(self.variants) > 1:
                    run["values_ui"] = set_values(res, "sealed", self.variants[1])
            self.runs.append(run)
        if self.mode == "dry":
            self.gates["G4"] = {"dry": True, "schedule": sched}
            return True
        ok_runs = [x for x in self.runs if x["ok"] and metric in x["values"]]

        def summarize(key):
            vals = {(x["round"], x["pos"]): (x["arm"], x[key][metric]) for x in ok_runs if metric in x.get(key, {})}
            eff, aa, bb = stats.paired_effects(vals, metric)
            if not eff:
                return None, aa, bb
            return stats.summarize(eff, self.ci), aa, bb

        self.summary, self.aa, self.bb = summarize("values")
        self.summary_public = summarize("values_public")[0] if metric in SERVE_METRICS else None
        self.summary_ui = summarize("values_ui")[0] if len(self.variants) > 1 else None
        hb = [x["harness_before"] for x in self.runs if x.get("harness_before")]
        ha = [x["harness_after"] for x in self.runs if x.get("harness_after")]
        ctx = {"card": self.card, "profile": self.profile, "runs": self.runs, "workload": self.workload,
               "aa": self.aa, "server_argv": self.server_argv,
               "harness_before": hb[0] if hb else None, "harness_after": ha[-1] if ha else None}
        if metric in BENCH_METRICS:
            ctx.pop("workload")
        blocking = self.add_findings("G4", rules.run("measurement", ctx))
        for f in blocking:
            self.reasons.append(f"G4 {f.rule}: {f.message}")
        self.gates["G4"] = {"metric": metric, "rounds": self.rounds, "schedule": sched, "n_runs": len(self.runs),
                            "n_ok": len(ok_runs), "sealed": self.summary, "public": self.summary_public,
                            "client_ui": self.summary_ui, "aa": self.aa, "bb": self.bb}
        if not self.summary:
            self.note("G4", "no complete ABBA round")
            return False
        return not [f for f in blocking if f.verdict == "INVALID"]

    # ------------------------------------------------------------------ G5
    def g5(self):
        self.log("G5 physics (roofline, Amdahl, anomaly)")
        metric = self.card["metric"]
        saving = None
        if metric in ("ms_step", "ms_token"):
            a = [x["values"][metric] for x in self.runs if x["ok"] and x["arm"] == "A" and metric in x["values"]]
            b = [x["values"][metric] for x in self.runs if x["ok"] and x["arm"] == "B" and metric in x["values"]]
            if a and b:
                saving = statistics.median(a) - statistics.median(b)
        ctx = {"card": self.card, "profile": self.profile, "runs": self.runs, "summary": {"saving_ms": saving}}
        blocking = self.add_findings("G5", rules.run("physics", ctx))
        for f in blocking:
            self.reasons.append(f"G5 {f.rule}: {f.message}")
        exp = (self.card.get("expected") or {}).get("effect_pct")
        med = (self.summary or {}).get("median")
        self.gates["G5"] = {"saving_ms": saving, "share_ms": (self.card.get("attacked") or {}).get("share_ms"),
                            "calibration": (med / exp) if (exp and med is not None) else None}
        return not blocking

    # ------------------------------------------------------------------ run
    def run(self) -> dict:
        self.log(f"verify {self.vid} mode={self.mode} card={self.card.get('id')} sha256={self.csha[:12]}")
        verdict, stat_verdict = None, None
        try:
            ok = self.g0()
            if self.refused and self.mode != "dry":
                verdict = "INVALID"
            elif not ok and self.mode != "dry":
                verdict = "INVALID"
            else:
                for gate in (self.g1, self.g2, self.g3):
                    if not gate() and self.mode != "dry":
                        verdict = "INVALID"
                        break
                if verdict is None:
                    ok4 = self.g4()
                    if self.mode == "dry":
                        self.log("dry run: nothing executed, nothing written")
                        return {"verdict": None, "plan": self.runner.plan, "gates": self.gates,
                                "reasons": self.reasons, "findings": self.findings}
                    ok5 = self.g5() if self.summary else True
                    verdict, stat_verdict = self.decide(ok4, ok5)
        except Refused as e:
            self.refused = True
            verdict = "INVALID"
            self.reasons.append(f"refused: {e}")
        if self.mode == "dry":
            self.log("dry run: nothing executed, nothing written")
            return {"verdict": None, "plan": self.runner.plan, "gates": self.gates, "reasons": self.reasons,
                    "findings": self.findings}
        row = self.ledger_row(verdict, stat_verdict)
        if not self.registration or self.ledger.verify():
            self.log(f"verdict {verdict} NOT written (card not registered or broken ledger)")
            return {**row, "written": False}
        r = self.ledger.append(row)
        self.log(f"verdict {verdict} -> {self.ledger.path} seq {r['seq']} sha256 {r['sha256'][:12]}")
        return {**r, "written": True}

    def decide(self, ok4, ok5):
        metric = self.card["metric"]
        if not ok4 or not ok5:
            return "INVALID", None
        aa_med = statistics.median(self.aa) if self.aa else 0.0
        if abs(aa_med) > stats.AA_MAX[metric]:
            self.note("G4", f"A/A control {aa_med:+.3f} % beyond {stats.AA_MAX[metric]} %: session too noisy")
            return "INVALID", None
        self.mde = stats.mde(metric, self.aa, self.card.get("mde_pct"))
        kill = (self.card.get("kill") or {}).get("effect_pct_below")
        sv, why = stats.verdict(self.summary, self.mde, kill)
        self.reasons.append(f"stat: {why}")
        human = [f["message"] for f in self.findings if f["verdict"] == "NEEDS-HUMAN"]
        pub = self.summary_public
        if pub and not any(map(lambda v: v != v, pub["ci95"])):
            s_lo, s_hi = self.summary["ci95"]
            p_lo, p_hi = pub["ci95"]
            if (s_lo > 0 and p_hi < 0) or (s_hi < 0 and p_lo > 0):
                human.append("sealed and public sets disagree in sign (winner's curse?)")
        if self.card.get("correctness_class") in ("KLD", "NEAR-TIE") and sv == "CONFIRMED":
            human.append(f"numerics change ({self.card['correctness_class']}): human approval before merge (G7)")
        if human:
            self.reasons += [f"NEEDS-HUMAN: {h}" for h in human]
            return "NEEDS-HUMAN", sv
        return sv, sv

    def ledger_row(self, verdict, stat_verdict) -> dict:
        evidence = []
        if self.rundir:
            for f in sorted(self.rundir.rglob("*")):
                if f.is_file():
                    evidence.append({"path": str(f), "sha256": hashing.sha256_file(f, use_cache=False)})
        s = getattr(self, "summary", None)
        snap = next((x.get("snapshot") for x in self.runs if x.get("snapshot")), None)
        return {
            "kind": "verdict", "mode": self.mode, "verify_id": self.vid, "claim_id": self.card.get("id"),
            "claim_sha256": self.csha, "card": self.card, "registered_seq": (self.registration or {}).get("seq"),
            "repo": self.card.get("repo"), "commits": self.card.get("commits"),
            "builds": {arm: {"dir": self.build(arm), "sha256": self.build_sha.get(arm)} for arm in ("base", "cand")}
            if hasattr(self, "build_sha") else None,
            "model": {"path": str(self.model_path), "sha256": getattr(self, "model_sha", None)},
            "profile": self.card.get("profile"), "server_argv": getattr(self, "server_argv", None),
            "env": {arm: self.arm_spec(arm)[1] for arm in ("A", "B")}, "protocol": profiles.PROTOCOL,
            "harness_sha256": getattr(self, "harness_tree", None), "sealed_sha256": getattr(self, "sealed_sha", None),
            "driver": {"serve": "fk/measure.py:serve_run", "greedy": f"fusion/greedy.sh@"
                       f"{(getattr(self, 'harness', {}) or {}).get('ext/fusion/greedy.sh', '')[:12]}",
                       "kld": "tools/kld_gate.py", "bench": "llama-bench -r 3 -o jsonl", "rounds": self.rounds},
            "gates": self.gates, "abba_order": [list(x) for x in stats.abba_schedule(self.rounds)],
            "samples": [{k: v for k, v in x.items() if k not in ("log_tail", "text_sha256", "snapshot", "argv", "env")}
                        for x in self.runs],
            "metric": self.card.get("metric"), "median": (s or {}).get("median"), "ci95": (s or {}).get("ci95"),
            "ci_method": (s or {}).get("ci_method"), "n_pairs": (s or {}).get("n"),
            "aa": {"effects": getattr(self, "aa", None),
                   "median": statistics.median(self.aa) if getattr(self, "aa", None) else None},
            "mde_pct": getattr(self, "mde", None),
            "public": getattr(self, "summary_public", None), "client_ui": getattr(self, "summary_ui", None),
            "expected_effect_pct": (self.card.get("expected") or {}).get("effect_pct"),
            "kill_effect_pct_below": (self.card.get("kill") or {}).get("effect_pct_below"),
            "verdict": verdict, "stat_verdict": stat_verdict, "refused": self.refused, "reasons": self.reasons,
            "findings": self.findings, "hw": snap, "logs": str(self.rundir) if self.rundir else None,
            "evidence": evidence,
        }
