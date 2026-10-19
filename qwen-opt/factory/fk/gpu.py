"""How the verifier runs GPU blocks: real (locks + timeout + pauses), dry (print only) or fake (synthetic data).

Real block command (every block, after the pgrep check and the pause):
  flock /tmp/gpu.lock flock /tmp/quiet.lock timeout 290 python3 factory.py _block runs/<vid>/blocks/<n>.json
"""
from __future__ import annotations

import hashlib
import json
import random
import shlex
import subprocess
import sys
import time
from pathlib import Path

from . import hwgates, paths


class Refused(Exception):
    pass


def show(argv) -> str:
    return " ".join(shlex.quote(str(a)) for a in argv)


def block_command(spec_path) -> list[str]:
    return [*paths.GPU_WRAP, "timeout", str(paths.BLOCK_TIMEOUT_S), sys.executable,
            str(paths.FACTORY / "factory.py"), "_block", str(spec_path)]


def inner_command(spec: dict) -> str:
    env = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in sorted((spec.get("env") or {}).items()))
    k = spec["kind"]
    if k == "greedy":
        cmd = show(["bash", spec["script"], spec["bin_dir"], spec["lib_dir"], spec["out_prefix"], spec["model"]])
    elif k in ("serve", "neartie", "probe"):
        cmd = show(spec["argv"])
        n = len(spec.get("prompts") or [])
        if k == "serve":
            p = spec["protocol"]
            cmd += (f"   # then {n} prompts x {len(p['seeds'])} seeds x {len(spec.get('variants', ['plain']))} variant(s), "
                    f"max_tokens {p['tokens']}, T {p['temps']}, cache_prompt {p['cache_prompt']}")
        elif k == "neartie":
            cmd += f"   # then {n} greedy prompts with logprobs, top_logprobs 2"
        else:
            cmd += f"   # then 1 request; log must match /{spec['regex']}/"
    else:
        cmd = show(spec["argv"])
    return f"{env} LD_LIBRARY_PATH={spec['lib_dir']}:{paths.ROCM_LIB} {cmd}".strip()


class Runner:
    def __init__(self, mode: str, blocks_dir: Path | None, pause_s: float = paths.PAUSE_S, log=print, fake=None,
                 card: dict | None = None, vid: str = ""):
        assert mode in ("real", "dry", "fake"), mode
        self.mode, self.dir, self.pause_s, self.log = mode, blocks_dir, pause_s, log
        self.card, self.vid = card, vid
        self.n = 0
        self.fake = FakeGPU(**(fake or {})) if mode == "fake" else None
        self.plan: list[dict] = []

    def block(self, spec: dict) -> dict:
        self.n += 1
        spec = dict(spec, name=f"{self.n:02d}-{spec['name']}", env={**paths.HW_ENV, **(spec.get("env") or {})})
        spec_path = (self.dir / f"{spec['name']}.json") if self.dir else Path(f"runs/<vid>/blocks/{spec['name']}.json")
        spec["out"] = str(spec_path.with_suffix(".out.json"))
        self.plan.append({"name": spec["name"], "kind": spec["kind"], "inner": inner_command(spec)})
        if self.mode == "dry":
            if self.n > 1:
                self.log(f"sleep {self.pause_s:g}")
            self.log(f"# block {spec['name']} ({spec['kind']}, <= {paths.BLOCK_TIMEOUT_S} s)")
            self.log(f"[ -z \"$(ss -ltnH 'sport = :{paths.USER_PORT}')\" ] || exit 3   # + hardware gates H0-H11")
            self.log(show(block_command(spec_path)))
            self.log(f"#   inside: {inner_command(spec)}")
            return {"dry": True, "name": spec["name"], "kind": spec["kind"], "ok": None}
        if self.mode == "fake":
            res = self.fake.result(spec)
            res["name"] = spec["name"]
            spec_path.write_text(json.dumps(spec, indent=1))
            Path(spec["out"]).write_text(json.dumps(res))
            return res
        if self.n > 1:
            time.sleep(self.pause_s)
        build_dir = str(Path(spec["lib_dir"]).parent)
        try:  # H0-H11 (fk/hwgates.py): refuse, never "drop and retry"; transient H1/H11 wait for a cool, quiet box
            hwgates.enforce({"env": spec["env"], "argv": spec.get("argv"), "card": self.card, "builds": [build_dir],
                             "wrap": block_command(spec_path)[:4], "block_timeout": paths.BLOCK_TIMEOUT_S},
                            wait=True, log=self.log)
        except hwgates.HwRefused as e:
            raise Refused(f"hardware gates: {e}")
        spec_path.write_text(json.dumps(spec, indent=1))
        self.log(f"[{time.strftime('%H:%M:%S')}] block {spec['name']}: {inner_command(spec)[:160]}")
        start_utc, t0 = hwgates.utcnow(), time.time()
        r = subprocess.run(block_command(spec_path))
        try:
            res = json.loads(Path(spec["out"]).read_text())
        except (OSError, ValueError):
            res = {"ok": False, "error": f"block exited {r.returncode} without a result (timeout {paths.BLOCK_TIMEOUT_S} s?)"}
        # GPU time = time inside both locks (the block's own clock); waiting for the lock is not ours
        hwgates.record_block(self.vid, spec["name"], res.get("secs") or (0 if r.returncode in (97, 98) else
                                                                         time.time() - t0))
        try:
            hwgates.after_block(start_utc, build_dir, self.vid, spec["name"])
        except hwgates.HardwareStop as e:
            raise Refused(f"H3 hardware stop: {e}")
        if r.returncode in (97, 98):
            raise Refused("; ".join(res.get("refused") or [f"exit {r.returncode}"]))
        res["exit"] = r.returncode
        return res


class FakeGPU:
    """Synthetic but structurally real results, for tests and `verify --fake`.
    effect_pct: candidate speed-up on ms (positive = faster); noise_pct: per-run sd; md5_diff: candidate greedy md5
    differs; probe_hit; aa_drift_pct: second process of each arm slower (A/A failure); outlier: (arm, index) 10x slow."""

    BASE_MS = {"qwen": 27.74, "lfm": 3.41}
    BASE_TPS = {"qwen": {"pp_tps": 1115.0, "tg_tps": 43.2}, "lfm": {"pp_tps": 6175.0, "tg_tps": 294.8}}

    def __init__(self, effect_pct=0.5, noise_pct=0.04, md5_diff=False, probe_hit=True, aa_drift_pct=0.0,
                 outlier=None, seed=1):
        self.effect, self.noise, self.md5_diff, self.probe_hit = effect_pct, noise_pct, md5_diff, probe_hit
        self.aa_drift, self.outlier, self.seed = aa_drift_pct, outlier, seed
        self.counts: dict[str, int] = {}

    def _rnd(self, key):
        return random.Random(f"{self.seed}|{key}")

    def result(self, spec: dict) -> dict:
        k = spec["kind"]
        arm = spec.get("arm", "")
        on = arm == "B" or spec.get("treated", False)
        base = {"ok": True, "secs": 1.0, "harness_before": "h", "harness_after": "h", "pid": 10000 + sum(self.counts.values()),
                "snapshot": {"loadavg": [0.5, 0.5, 0.5], "nproc": 16, "power_control": "on", "vram_used": 30 << 20}}
        self.counts[k] = self.counts.get(k, 0) + 1
        if k == "greedy":
            md5 = {m: hashlib.md5(f"{spec['model']}|{m}|{'cand' if on and self.md5_diff else 'base'}".encode())
                   .hexdigest() for m in spec["modes"]}
            return {**base, "rc": 0, "md5": md5, "log_tail": "main: server is listening"}
        if k == "probe":
            return {**base, "hit": self.probe_hit and on}
        if k == "ops":
            return {**base, "rc": 0, "ok": True, "fails": [], "passed": "12/12 tests passed"}
        if k == "bench":
            model = spec["model_family"]
            v = self.BASE_TPS[model][spec["metric"]] * (1 + (self.effect / 100 if on else 0))
            v *= 1 + self._rnd(spec["name"]).gauss(0, self.noise / 100)
            return {**base, "avg_ts": v, "samples_ts": [v] * 3, "build_commit": "fake"}
        if k == "neartie":
            toks = {f"p{i}": [{"id": j, "token": str(j), "logprob": -0.1,
                               "top_logprobs": [{"id": j, "logprob": -0.1}, {"id": j + 1, "logprob": -0.15}]}
                              for j in range(20)] for i in range(len(spec["prompts"]))}
            if on and self.md5_diff:
                for t in toks.values():
                    t[10] = {"id": 11, "token": "11", "logprob": -0.12, "top_logprobs": []}
            return {**base, "tokens": toks}
        if k == "kld":
            return {**base, "rc": 0, "log": spec["log"]}
        if k == "serve":
            fam = spec["model_family"]
            idx = self.counts[k]
            r = self._rnd(spec["name"])
            seen = self.counts.setdefault(f"serve-{arm}", 0)
            self.counts[f"serve-{arm}"] = seen + 1
            scale = (1 - self.effect / 100 if on else 1.0) * (1 + r.gauss(0, self.noise / 100))
            if seen % 2 == 1:
                scale *= 1 + self.aa_drift / 100
            if self.outlier and self.outlier == [arm, seen]:
                scale *= 10
            rec = {"prompts": {}, "text_sha256": {}, "n_tokens": {}, "build_info": "8000 (fake)",
                   "request": {kk: spec["protocol"][kk] for kk in ("tokens", "temps", "seeds", "cache_prompt")},
                   "telemetry": {"max_junction_c": 80.0, "max_vram_used": 21 << 30, "max_gtt_used": 20 << 20},
                   "log_tail": "srv  update_slots: all slots are idle", "pid": 20000 + idx}
            for variant in spec.get("variants", ["plain"]):
                for item in spec["prompts"]:
                    e = item["entry"]
                    key = f"{item['set']}/{e['id']}" + ("" if variant == "plain" else f"@{variant}")
                    tok_step = 2.4 + (int(hashlib.md5(e["id"].encode()).hexdigest(), 16) % 110) / 100.0
                    ms_step = self.BASE_MS[fam] * scale * (1 + r.gauss(0, self.noise / 200))
                    if fam == "lfm":
                        tok_step = 1.0
                    n = spec["protocol"]["tokens"] * len(spec["protocol"]["seeds"])
                    rec["prompts"][key] = {"set": item["set"], "variant": variant, "class": e.get("class"),
                                           "lang": e.get("lang"), "ms_step": ms_step, "tok_step": tok_step,
                                           "tps": 1000.0 * tok_step / ms_step, "ms_token": ms_step / tok_step, "n": n}
                    rec["n_tokens"][e["id"]] = n
                    for s in spec["protocol"]["seeds"]:
                        rec["text_sha256"][f"{key}/T1.0/s{s}"] = hashlib.sha256(f"{key}{s}".encode()).hexdigest()
            return {**base, **rec}
        raise ValueError(k)
