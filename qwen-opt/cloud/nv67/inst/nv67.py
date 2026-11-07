#!/usr/bin/env python3
"""NVIDIA campaign 67 driver. Runs ON the Vast host after setup.sh (engines + models in place).

Every arm is a fresh llama-server with exactly Enigma's argument list (app/engine/src/server/engine.ts serverArgs:
-m -c -ngl 999 -fa on -ctk/-ctv KV -b max(2048,ub) -ub -np 1 --jinja) plus the arm's extra flags.
Per arm: VRAM after load, compute/KV buffers from the log, greedy md5 (T=0, 2 prompts x 400), spec_sweep-style
T=1 (6 prompts x seeds 1,2,3 x 400 tokens), prefill of a 4096-token corpus prompt.

Blocks (card.json "blocks"): mem perf pmin abba fill ctxprobe stab moe.
Results: $RES/arms.jsonl (one record per arm), $RES/sweep.jsonl, $RES/smi.csv, $RES/logs/<arm>.log, $RES/summary.json.
usage: nv67.py card.json
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
import sys
import threading
import time
import urllib.request

CFG = json.load(open(sys.argv[1]))
ROOT = os.environ.get("NV_ROOT", "/root")   # local smoke test: NV_ROOT=/tmp/nv67/root
RES = CFG.get("res", f"{ROOT}/res")
ENG = f"{ROOT}/eng"
MOD = f"{ROOT}/models"
PORT = int(os.environ.get("NV_PORT", "18467"))
os.makedirs(f"{RES}/logs", exist_ok=True)
DEADLINE = int(open(f"{ROOT}/qwenbench-deadline").read()) if os.path.exists(f"{ROOT}/qwenbench-deadline") else time.time() + 86400
TOK = int(os.environ.get("NV_TOKENS", "400"))            # sweep/greedy tokens (smoke test: small)
STAB_TOK = int(os.environ.get("NV_STAB_TOKENS", "2048"))
PP_N = int(os.environ.get("NV_PREFILL", "4096"))

PROMPTS = {
    "pl-proza": "Napisz opowiadanie (około 800 słów) o starym latarniku, który pewnej sztormowej nocy dostaje sygnał z okrętu, który zatonął 50 lat temu. Opisz dokładnie miejsce, pogodę, jego wspomnienia i zakończ zaskakującym zwrotem akcji.",
    "pl-tech": "Wyjaśnij krok po kroku, jak działa protokół TCP: nawiązywanie połączenia, numery sekwencyjne, okno przesuwne, kontrola przeciążenia i zamykanie połączenia. Do każdego etapu podaj przykład z liczbami.",
    "pl-kod": "Napisz w Pythonie klasę LRUCache z metodami get i put (O(1)), z type hintami, docstringami i testami w pytest.",
    "en-chat": "Hey! How are you doing today? Tell me a bit about what you like to talk about.",
    "en-tech": "Explain how a B-tree index works in a relational database: node layout, search, insertion with splits, deletion with merges, and why it suits disks. Use a concrete example with numbers.",
    "en-code": "Write a complete Python module implementing a thread-safe LRU cache with TTL expiry: type hints, docstrings, and a full pytest test suite. Write all the code, no placeholders.",
}
GREEDY = ["Explain how a hash map works, then implement one in C with open addressing.",
          "Napisz krótkie opowiadanie o latarniku i sztormie."]
STAB = ["Write a detailed technical design document for a distributed key-value store: replication, consistency, failure handling, and an example deployment.",
        "Napisz szczegółowy przewodnik po historii Krakowa od średniowiecza do dziś, z datami i postaciami.",
        "Implement a small interpreter for arithmetic expressions in Rust with a tokenizer, a Pratt parser and tests.",
        "Describe, step by step, how a modern CPU executes an instruction: fetch, decode, rename, schedule, execute, retire.",
        "Napisz esej o wpływie sztucznej inteligencji na rynek pracy w Polsce, z argumentami za i przeciw.",
        "Write a long story about a lighthouse keeper who receives a signal from a ship that sank fifty years ago."]


def now() -> str:
    return time.strftime("%H:%M:%S")


def say(*a) -> None:
    print(f"=== {now()}", *a, flush=True)


def time_left(need_s: int) -> bool:
    ok = time.time() + need_s < DEADLINE - 600
    if not ok:
        say(f"time budget: skip (needs {need_s}s)")
    return ok


# ---- GPU monitor ------------------------------------------------------------------------------------------------
class Mon:
    def __init__(self) -> None:
        self.label = "idle"
        self.peak: dict[str, int] = {}
        self.f = open(f"{RES}/smi.csv", "a")
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self) -> None:
        q = "memory.used,power.draw,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu,pstate"
        while True:
            try:
                out = subprocess.run(["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, timeout=10).stdout.strip().splitlines()[0]
                mem = int(float(out.split(",")[0]))
                self.peak[self.label] = max(self.peak.get(self.label, 0), mem)
                self.f.write(f"{time.time():.0f},{self.label},{out}\n")
                self.f.flush()
            except Exception:
                pass
            time.sleep(1)

    def reset(self, label: str) -> None:
        self.label = label
        self.peak[label] = 0


MON = Mon()


def vram_used() -> int:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    return int(float(out.split()[0]))


# ---- server ---------------------------------------------------------------------------------------------------------
class Server:
    def __init__(self, label: str, tag: str, args: list[str], env: dict[str, str] | None = None) -> None:
        self.label, self.tag = label, tag
        bindir = open(f"{ENG}/{tag}/.bindir").read().strip()
        self.log = f"{RES}/logs/{label}.log"
        e = dict(os.environ, LD_LIBRARY_PATH=bindir, **(env or {}))
        self.cmd = [f"{bindir}/llama-server", *args, "--host", "127.0.0.1", "--port", str(PORT), "--no-webui"]
        with open(self.log, "w") as lf:
            lf.write(" ".join(self.cmd) + "\n")
        self.ok = False
        try:  # a server left on the port would answer for this arm
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3)
            subprocess.run(["pkill", "-f", f"llama-server.*--port {PORT}"])
            time.sleep(5)
        except Exception:
            pass
        self.p = subprocess.Popen(self.cmd, stdout=open(self.log, "a"), stderr=subprocess.STDOUT, env=e,
                                  stdin=subprocess.DEVNULL)
        t0 = time.time()
        while time.time() - t0 < 900:
            if self.p.poll() is not None:
                break
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3).status == 200:
                    self.ok = True
                    break
            except Exception:
                pass
            time.sleep(1)
        self.load_s = round(time.time() - t0, 1)
        if self.ok:  # health answered: it must be our process, still alive
            time.sleep(1)
            self.ok = self.p.poll() is None
        self.vram_load = vram_used() if self.ok else None

    def tail(self, n: int = 12) -> str:
        try:
            return "".join(open(self.log, errors="replace").readlines()[-n:])
        except Exception:
            return ""

    def stop(self) -> None:
        if self.p.poll() is None:
            self.p.terminate()
            try:
                self.p.wait(60)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait()
        time.sleep(3)

    def props(self) -> dict:
        try:
            return json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/props", timeout=10))
        except Exception:
            return {}

    def n_ctx(self) -> int | None:
        d = self.props()
        return (d.get("default_generation_settings") or {}).get("n_ctx") or d.get("n_ctx")


def post(path: str, body: dict, timeout: int = 1800) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def chat(prompt: str, tokens: int, temp: float, seed: int) -> dict:
    d = post("/v1/chat/completions", {"messages": [{"role": "user", "content": prompt}], "max_tokens": tokens,
                                      "temperature": temp, "seed": seed, "cache_prompt": False})
    t = d["timings"]
    msg = d["choices"][0]["message"]
    text = (msg.get("reasoning_content") or "") + "\x00" + (msg.get("content") or "")
    return {"tps": t["predicted_per_second"], "n": t["predicted_n"], "ms": t["predicted_ms"],
            "draft": t.get("draft_n", 0), "accepted": t.get("draft_n_accepted", 0), "text": text}


def log_buffers(path: str) -> dict:
    """compute/KV/model buffer sizes and offload from a server log (sched_reserve / llama_kv_cache lines)."""
    out: dict = {"compute": [], "kv": [], "model": [], "rs": [], "offload": None, "mtp_ctx_line": None}
    import re
    seen_mtp = False
    for line in open(path, errors="replace"):
        if "creating MTP draft context" in line or "loading draft model" in line:
            seen_mtp = True
        m = re.search(r"(\S+) compute buffer size =\s*([\d.]+) MiB", line)
        if m:
            out["compute"].append({"dev": m.group(1), "mib": float(m.group(2)), "draft": seen_mtp})
        m = re.search(r"(\S+) KV buffer size =\s*([\d.]+) MiB", line)
        if m:
            out["kv"].append({"dev": m.group(1), "mib": float(m.group(2)), "draft": seen_mtp})
        m = re.search(r"(\S+) RS buffer size =\s*([\d.]+) MiB", line)
        if m:
            out["rs"].append({"dev": m.group(1), "mib": float(m.group(2)), "draft": seen_mtp})
        m = re.search(r"(\S+) model buffer size =\s*([\d.]+) MiB", line)
        if m:
            out["model"].append({"dev": m.group(1), "mib": float(m.group(2))})
        m = re.search(r"offloaded (\d+)/(\d+) layers", line)
        if m:
            out["offload"] = f"{m.group(1)}/{m.group(2)}"
    return out


# ---- arms -----------------------------------------------------------------------------------------------------------
M = f"{MOD}/{CFG['model']['file']}"
DRAFT = f"{MOD}/{CFG['draft']['file']}" if CFG.get("draft") else None
PIN, NEW = CFG["engines"]["pin"], CFG["engines"]["new"]
CTX, KV, UB = CFG["ctx"], CFG["kv"], CFG["ub"]
MTP = CFG.get("mtp")  # "self" | "drafter" | None


def base_args(ctx: int = CTX, model: str = M, kv: str = KV, ub: int = UB) -> list[str]:
    # "main_extra": flags every arm of the card's main model needs (e.g. --n-cpu-moe for LFM2.5 on 8-10 GB)
    extra = CFG.get("main_extra", []) if model == M else []
    return ["-m", model, "-c", str(ctx), "-ngl", "999", "-fa", "on", "-ctk", kv, "-ctv", kv,
            "-b", str(max(2048, ub)), "-ub", str(ub), "-np", "1", "--alias", "enigma-test", "--jinja", *extra]


def spec_args(n: int, pmin: float | None = None, extra: list[str] | None = None) -> list[str]:
    a = ["--spec-type", "draft-mtp", "--spec-draft-n-max", str(n)]
    if MTP == "drafter" and DRAFT:
        a += ["-md", DRAFT]
    if pmin is not None:
        a += ["--spec-draft-p-min", str(pmin)]
    return a + (extra or [])


ARMS = open(f"{RES}/arms.jsonl", "a")
DONE: dict[str, dict] = {}
ARM_ENV: dict[str, dict] = {}  # env of fork arms, reused by the recipe's ABBA/fill/stab runs
ARM_MODEL: dict[str, str] = {}  # model file of fork arms that run another file than the card's main model
CORPUS_TOK: list[int] = []


def corpus_tokens(n: int) -> list[int]:
    global CORPUS_TOK
    if not CORPUS_TOK:
        txt = open(f"{ROOT}/nv/corpus.txt").read()
        CORPUS_TOK = post("/tokenize", {"content": txt, "add_special": False})["tokens"]
    reps = n // len(CORPUS_TOK) + 1
    return (CORPUS_TOK * reps)[:n]


def prefill(n: int = PP_N) -> dict:
    vals = []
    for rep in range(2):
        toks = corpus_tokens(n + 64)[rep * 64: rep * 64 + n]  # different start: no prompt-cache reuse
        d = post("/completion", {"prompt": toks, "n_predict": 1, "cache_prompt": False, "temperature": 0})
        vals.append(d["timings"]["prompt_per_second"])
    return {"tps": statistics.median(vals), "runs": vals}


def greedy() -> dict:
    hs, tps = [], []
    for p in GREEDY:
        r = chat(p, TOK, 0.0, 42)
        hs.append(hashlib.md5(r["text"].encode()).hexdigest()[:12])
        tps.append(r["tps"])
    return {"md5": "-".join(hs), "tps": tps}


def sweep(seeds=(1, 2, 3), tokens: int = TOK) -> dict:
    chat("Hi", 16, 0.0, 0)  # warmup
    per = {}
    for name, p in PROMPTS.items():
        runs = [chat(p, tokens, 1.0, s) for s in seeds]
        n, ms = sum(r["n"] for r in runs), sum(r["ms"] for r in runs)
        dr, ac = sum(r["draft"] for r in runs), sum(r["accepted"] for r in runs)
        steps = max(1, n - ac)
        per[name] = {"tps": 1000 * n / ms, "acc": ac / dr if dr else 0.0, "ms_step": ms / steps, "tok_step": n / steps,
                     "runs": [round(r["tps"], 2) for r in runs]}
    med = statistics.median(r["tps"] for r in per.values())
    return {"median_tps": med, "mean_tps": statistics.mean(r["tps"] for r in per.values()),
            "median_ms_step": statistics.median(r["ms_step"] for r in per.values()),
            "acc": statistics.mean(r["acc"] for r in per.values()), "prompts": per}


def run_arm(label: str, tag: str, extra: list[str], what=("greedy", "sweep", "prefill"), ctx: int = CTX,
            env: dict | None = None, model: str = M, kv: str = KV, ub: int = UB, soak_s: int = 0) -> dict:
    if not time_left(600):
        return {}
    say(f"arm {label}: {tag} {' '.join(extra)} ctx={ctx}")
    MON.reset(label)
    s = Server(label, tag, base_args(ctx, model, kv, ub) + extra, env)
    rec: dict = {"arm": label, "engine": tag, "extra": extra, "ctx_req": ctx, "kv": kv, "ub": ub, "model": os.path.basename(model),
                 "ok": s.ok, "load_s": s.load_s, "vram_load_mib": s.vram_load, "t": now()}
    try:
        if not s.ok:
            rec["error"] = s.tail()
        else:
            rec["n_ctx"] = s.n_ctx()
            if "greedy" in what:
                rec["greedy"] = greedy()
            if "sweep" in what:
                rec["sweep"] = sweep()
            if "prefill" in what:
                rec["prefill"] = prefill()
            if "fill" in what:
                rec["fill"] = fill_test(ctx)
            if "stab" in what:
                rec["stab"] = stability(soak_s)
            if "probe" in what:
                chat("Hi", 8, 0.0, 0)
    except Exception as e:  # server died or request failed: recorded, campaign goes on
        rec["error"] = f"{type(e).__name__}: {e}\n{s.tail()}"
        rec["ok"] = False
    finally:
        rec["vram_peak_mib"] = MON.peak.get(label)
        s.stop()
        rec["buffers"] = log_buffers(s.log)
    ARMS.write(json.dumps(rec) + "\n")
    ARMS.flush()
    DONE[label] = rec
    sw = rec.get("sweep", {})
    say(f"arm {label}: ok={rec['ok']} n_ctx={rec.get('n_ctx')} load={rec['vram_load_mib']} peak={rec['vram_peak_mib']} "
        f"sweep={sw.get('median_tps', 0):.2f} acc={sw.get('acc', 0):.3f} md5={rec.get('greedy', {}).get('md5')} "
        f"pp={rec.get('prefill', {}).get('tps', 0):.0f} fill={json.dumps(rec.get('fill'))[:200]}")
    return rec


def fill_test(ctx: int) -> dict:
    """Prompt of ctx - 640 tokens, then 128 greedy tokens: memory at a full context, deep prefill/decode."""
    n = ctx - 640
    toks = corpus_tokens(n)
    t0 = time.time()
    d = post("/completion", {"prompt": toks, "n_predict": 128, "cache_prompt": False, "temperature": 0}, timeout=3600)
    t = d["timings"]
    return {"prompt_n": t["prompt_n"], "prompt_tps": t["prompt_per_second"], "decode_tps": t["predicted_per_second"],
            "predicted_n": t["predicted_n"], "draft": t.get("draft_n", 0), "accepted": t.get("draft_n_accepted", 0),
            "wall_s": round(time.time() - t0, 1), "vram_after_mib": vram_used(), "ok": t["prompt_n"] >= n - 8}


def stability(soak_s: int = 0) -> dict:
    """Long T=1 requests (STAB_TOK tokens each): every STAB prompt once, then repeated until soak_s seconds passed
    (the ~30 min soak of the final phase; stops early before the host deadline)."""
    tps, errs = [], 0
    temps = []
    t0 = time.time()
    i = 0
    while i < len(STAB) or (time.time() - t0 < soak_s and time_left(300)):
        try:
            r = chat(STAB[i % len(STAB)], STAB_TOK, 1.0, 100 + i)
            tps.append(round(r["tps"], 2))
        except Exception as e:
            errs += 1
            say(f"stability request {i} failed: {e}")
        temps.append(subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                                    capture_output=True, text=True).stdout.strip())
        i += 1
    med = statistics.median(tps) if tps else 0
    ok = errs == 0 and len(tps) == i and min(tps) >= 0.8 * med
    return {"tps": tps, "errors": errs, "temps": temps, "min_over_median": round(min(tps) / med, 3) if tps else 0,
            "requests": i, "soak_s": round(time.time() - t0), "vram_after_mib": vram_used(), "ok": ok}


def best_of(labels: list[str]) -> str | None:
    c = [(DONE[l]["sweep"]["median_tps"], l) for l in labels if l in DONE and DONE[l].get("ok") and "sweep" in DONE[l]
         and DONE[l].get("n_ctx") == DONE[l]["ctx_req"]]
    return max(c)[1] if c else None


# ---- campaign -------------------------------------------------------------------------------------------------------
def main() -> None:
    blocks = CFG.get("blocks", ["mem", "perf", "pmin", "abba", "fill", "ctxprobe", "stab"])
    say(f"card {CFG['card']} model {CFG['model']['file']} ctx {CTX} kv {KV} ub {UB} mtp {MTP} blocks {blocks}")
    # warm page cache (cold reads skew the first arm)
    subprocess.run(["dd", f"if={M}", "of=/dev/null", "bs=16M"], capture_output=True)
    if DRAFT:
        subprocess.run(["dd", f"if={DRAFT}", "of=/dev/null", "bs=16M"], capture_output=True)
    lv = ["-lv", "4"]
    # label -> (engine tag, extra args, ubatch, ctx)
    arms_spec: dict[str, tuple[str, list[str], int, int]] = {}
    if "mem" in blocks:
        run_arm("mem-pin-plain", PIN, lv, what=("probe",))
        if MTP:
            run_arm("mem-pin-mtp4", PIN, spec_args(4) + lv, what=("probe",))
            run_arm("mem-new-mtp3", NEW, spec_args(3) + lv, what=("probe",))
            run_arm("mem-new-mtp3-ubd64", NEW, spec_args(3, extra=["--spec-draft-n-ubatch", "64"]) + lv, what=("probe",))
            if MTP == "self":
                run_arm("mem-new-mtp3-q4d", NEW, spec_args(3, extra=["-ctkd", KV, "-ctvd", KV]) + lv, what=("probe",))
        # early answer to "does 262144 fit": buffers (-lv 4) and VRAM at load for plain / MTP / small draft ubatch
        for c in CFG.get("mem_ctx", []):
            for ub2 in sorted({UB, 512, 256}, reverse=True):
                if ub2 > UB:
                    continue
                run_arm(f"mem{c}-ub{ub2}-plain", NEW, lv, what=("probe",), ctx=c, ub=ub2)
                if MTP:
                    for n in (1, 3):
                        run_arm(f"mem{c}-ub{ub2}-mtp{n}", NEW, spec_args(n) + lv, what=("probe",), ctx=c, ub=ub2)
                        run_arm(f"mem{c}-ub{ub2}-mtp{n}-ubd64", NEW, spec_args(n, extra=["--spec-draft-n-ubatch", "64"]) + lv,
                                what=("probe",), ctx=c, ub=ub2)
    if "perf" in blocks:
        base_arms = CFG.get("perf_base", True)  # false: a follow-up card measures only its spec/fork arms
        if base_arms:
            run_arm("P0", PIN, [])            # Enigma today: official pin, baseline config
            run_arm("N0", NEW, [])            # engine bump, baseline config
        if MTP:
            if base_arms:
                run_arm("P4", PIN, spec_args(4))   # Enigma today: optimiser's MTP candidate (n=4)
            # Lossless fallbacks when the draft does not fit at Enigma's config: smaller draft ubatch, smaller -ub (both
            # only move prefill), then the 131072 minimum context. The first variant that loads is measured.
            ubd = ["--spec-draft-n-ubatch", "64"]
            # (suffix, engine tag, extra args, ub, ctx); a card may override them (e.g. the lean-reserve build with a
            # q4_0 draft KV: "spec_variants": [["L", "lean", ["-ctkd", "q4_0", ...], 256, 131072], ...])
            variants = [("", NEW, [], UB, CTX), ("u", NEW, ubd, UB, CTX)]
            for ub2 in (512, 256):
                if ub2 < UB:
                    variants.append((f"u{ub2}", NEW, ubd, ub2, CTX))
            if CTX > 131072:
                variants.append(("u256c131k", NEW, ubd, min(UB, 256), 131072))
            if CFG.get("spec_variants"):
                variants = [(s, CFG["engines"][e], x, u, c) for s, e, x, u, c in CFG["spec_variants"]]
            start = 0
            for n in CFG.get("spec_n", [1, 2, 3, 4]):
                for i, (suf, etag, extra, ub2, ctx2) in enumerate(variants):
                    if i < start:  # a variant that failed for a smaller n fails for a larger one too
                        continue
                    lab = f"N{n}{suf}"
                    r = run_arm(lab, etag, spec_args(n, extra=extra), ub=ub2, ctx=ctx2)
                    if r.get("ok"):
                        arms_spec[lab] = (etag, spec_args(n, extra=extra), ub2, ctx2)
                        start = i
                        break
        # our fork (report 27: cuda-topka2 + its env/flags) at the card's context, same harness and md5 gate
        for fa in CFG.get("fork_arms", []):
            tag = CFG["engines"][fa["engine"]]
            extra = [x.replace("{nv}", f"{ROOT}/nv") for x in fa["extra"]]
            ub2, ctx2 = fa.get("ub", UB), fa.get("ctx", CTX)
            # a fork arm may run its own model file (Bonsai PTQ1_0 / its MTP graft on the PrismML fork)
            fmodel = f"{MOD}/{fa['model']}" if fa.get("model") else M
            r = run_arm(fa["label"], tag, extra, env=fa.get("env"), ub=ub2, ctx=ctx2, model=fmodel,
                        what=tuple(fa.get("what", ["greedy", "sweep", "prefill"])))
            if r.get("ok"):
                arms_spec[fa["label"]] = (tag, extra, ub2, ctx2)
                ARM_ENV[fa["label"]] = fa.get("env") or {}
                ARM_MODEL[fa["label"]] = fmodel
    best_spec = best_of(list(arms_spec))
    if "pmin" in blocks and best_spec:
        tag, args, ub2, ctx2 = arms_spec[best_spec]
        for p in (0.5, 0.8):
            lab = f"{best_spec}p{int(p * 10)}"
            arms_spec[lab] = (tag, args + ["--spec-draft-p-min", str(p)], ub2, ctx2)
            run_arm(lab, tag, arms_spec[lab][1], ub=ub2, ctx=ctx2)
        best_spec = best_of(list(arms_spec))
    # recipe = fastest arm (spec or plain) whose context fit
    plain_best = best_of(["P0", "N0"])
    cands = [l for l in (best_spec, plain_best) if l]
    recipe = best_of(cands) if cands else None
    if recipe in arms_spec:
        rtag, rargs, rub, rctx = arms_spec[recipe]
    else:
        rtag, rargs, rub, rctx = (PIN if recipe == "P0" else NEW), [], UB, CTX
    renv = ARM_ENV.get(recipe or "")
    rmodel = ARM_MODEL.get(recipe or "", M)
    say(f"recipe arm: {recipe} {rtag} {rargs} ub={rub} ctx={rctx} model={os.path.basename(rmodel)}")
    if "abba" in blocks and recipe and recipe != "P0":
        run_arm(f"{recipe}-B", rtag, rargs, ub=rub, ctx=rctx, env=renv, model=rmodel)
        run_arm("P0-B", PIN, [])
    if "fill" in blocks:
        run_arm("fill-P0", PIN, [], what=("fill",))
        if recipe and recipe != "P0":
            run_arm(f"fill-{recipe}", rtag, rargs, what=("fill",), ub=rub, ctx=rctx, env=renv, model=rmodel)
    ctx_max = rctx
    if "ctxprobe" in blocks and recipe:
        for c in CFG.get("ctx_probe", []):
            if c <= ctx_max:
                continue
            r = run_arm(f"ctx{c}-{recipe}", rtag, rargs, what=("fill",), ctx=c, ub=rub, env=renv, model=rmodel)
            if r.get("ok") and r.get("n_ctx") == c and (r.get("fill") or {}).get("ok"):
                ctx_max = c  # every probe runs: the largest one is the question (262144 on 24/32 GB)
    if "stab" in blocks and recipe:
        run_arm(f"stab-{recipe}", rtag, rargs, what=("greedy", "stab"), ub=rub, ctx=rctx, env=renv, model=rmodel,
                soak_s=CFG.get("soak_s", 0))
    if "moe" in blocks and CFG.get("moe"):
        moe_block(CFG["moe"])
    summary = {"card": CFG["card"], "recipe": recipe, "recipe_engine": rtag, "recipe_args": rargs, "recipe_ub": rub,
               "recipe_ctx": rctx, "ctx_max_fill": ctx_max,
               "arms": {k: {"sweep": v.get("sweep", {}).get("median_tps"), "acc": v.get("sweep", {}).get("acc"),
                            "pp": v.get("prefill", {}).get("tps"), "md5": v.get("greedy", {}).get("md5"),
                            "ok": v.get("ok"), "n_ctx": v.get("n_ctx"), "peak": v.get("vram_peak_mib"),
                            "load": v.get("vram_load_mib")} for k, v in DONE.items()}}
    json.dump(summary, open(f"{RES}/summary.json", "w"), indent=1)
    say("campaign done")


def moe_block(c: dict) -> None:
    """66-SYNTEZA #10: MoE with --n-cpu-moe on a <= 16 GB card, MTP n x p-min."""
    model = f"{MOD}/{c['file']}"
    t0 = time.time()
    while not os.path.exists(model + ".ok") and time.time() - t0 < 2400:
        time.sleep(10)
    if not os.path.exists(model + ".ok"):
        say("moe: model download did not finish")
        return
    subprocess.run(["dd", f"if={model}", "of=/dev/null", "bs=16M"], capture_output=True)
    global CORPUS_TOK
    CORPUS_TOK = []
    ncm = None
    ubd = ["--spec-draft-n-ubatch", "64"]
    kw = dict(ctx=c["ctx"], model=model, kv=c["kv"], ub=c["ub"])
    for k in c.get("ncmoe_try", [8, 12, 16, 20, 24]):
        r = run_arm(f"moe-probe-ncm{k}", NEW, ["--n-cpu-moe", str(k), "--spec-type", "draft-mtp", "--spec-draft-n-max", "3"] + ubd,
                    what=("probe",), **kw)
        if r.get("ok") and r.get("n_ctx") == c["ctx"] and r.get("vram_load_mib", 1e9) < c["vram_limit_mib"]:
            ncm = k
            break
    if ncm is None:
        say("moe: no --n-cpu-moe value fits")
        return
    base = ["--n-cpu-moe", str(ncm)]
    labs = {}
    r = run_arm(f"moe-ncm{ncm}-plain", NEW, base, what=("greedy", "sweep", "prefill"), **kw)
    labs[f"moe-ncm{ncm}-plain"] = base
    # 66-SYNTEZA #10 grid (n x p-min); the final phase passes a short grid ([[1,0],[2,0],[3,0]])
    for n, p in c.get("grid", [[1, 0.0], [1, 0.5], [1, 0.8], [2, 0.0], [2, 0.5], [2, 0.8], [4, 0.0], [4, 0.5], [4, 0.8]]):
        lab = f"moe-ncm{ncm}-n{n}p{int(p * 10)}"
        labs[lab] = base + ["--spec-type", "draft-mtp", "--spec-draft-n-max", str(n), "--spec-draft-p-min", str(p)] + ubd
        run_arm(lab, NEW, labs[lab], what=("greedy", "sweep", "prefill"), **kw)
    best = best_of(list(labs))
    if best and c.get("validate", True):
        run_arm(f"fill-{best}", NEW, labs[best], what=("fill",), **kw)
        run_arm(f"stab-{best}", NEW, labs[best], what=("greedy", "stab"), soak_s=c.get("soak_s", 0), **kw)


if __name__ == "__main__":
    main()
