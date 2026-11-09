#!/usr/bin/env python3
"""xtxbench: fast lossless A/B harness for the RX 7900 XTX production engine.

Production = ~/qwen-opt/run-topka.sh uncensored (engine ~/llama-topka, topka-q63; Qwen3.8-27B-Uncensored Q4_K_M, KV q4_0,
MTP n4, ctx 262144, eco 2200). Every server here is that launcher with ROCM_DIR / env / args of the arm, plus
--slot-save-path ~/qwen-opt/xtxbench/slots. GPU modes run ONLY under ~/qwen-opt/queue/run-jobs.sh and never compile.

  xtxbench.py check [arm options]   CPU: binaries (missing -> refused, older than sources -> refused unless
                                    --allow-stale), runtime-switch hook, server grouping, snapshot sets, noise cache
  xtxbench.py prep                  CPU: hash the model and the engines now, so the GPU job does not
  xtxbench.py status                snapshot sets, noise caches, t0 results
  xtxbench.py t0 --op OP [--params P] [--perf] [arm options]
                                    kernel: test-backend-ops OP vs CPU on both arms (+ perf A B B A)
  xtxbench.py t1 [arm options]      snapshot-restored decode at 1.7k/94k/199k (T=0, 256 tokens, md5) + prefill 4k/32k
  xtxbench.py t2 [arm options]      t1 + T=1 decode (seed 42) + spec_sweep T=1 seeds 1,2,3 + prefill 128k + 255k fill

Arm options: --base DIR (default ~/llama-topka), --var DIR (default: base); --base-env/--var-env K=V and --var-args A,B
(server restart); --base-switch/--var-switch NAME=VAL (runtime switch file, one server; needs an engine with the
GGML_HIP_RUNTIME_SWITCH_FILE hook); --force-restart (B on its own server even when the config is identical); --label.

Adaptive rule (default for every test): the session noise n = |A - A'| / A per metric comes from one baseline pair on
the same snapshot (cached per engine key for --noise-ttl-h hours). Each variant starts with ONE pair A -> B per metric
group: |d| >= max(5 n, 0.5%) with one sign at every metric -> WIN/LOSS at once; |d| <= max(n, floor) everywhere and no
t0 kernel gain -> NULL (KILL) at once; otherwise B -> A is added (A B B A) and the group is decided on the means.
See README.md for the exact rules, the snapshot keys and the md5 restore proof.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import mmap
import os
import re
import shlex
import signal
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOME = os.path.expanduser("~")
XB = os.environ.get("XTXBENCH_HOME") or os.path.join(HOME, "qwen-opt", "xtxbench")  # override: selftest.py only
SLOTS = os.path.join(XB, "slots")
CACHE = os.path.join(XB, "cache")
RUNS = os.path.join(XB, "runs")
CORPUS = os.path.join(XB, "corpus.txt")
PROD = os.path.join(HOME, "llama-topka")
RUN_TOPKA = os.path.join(HOME, "qwen-opt", "run-topka.sh")
SPEC_SWEEP = os.path.join(HOME, "qwen-opt", "spec_sweep.py")
VRAM_OK = os.path.join(HOME, "qwen-opt", "lookup", "vram_ok.sh")
ECO = "/usr/local/sbin/xtx-eco"
ROCM_LIB = "/opt/rocm/core-10.0/lib"
HOOK_ENV = "GGML_HIP_RUNTIME_SWITCH_FILE"
PROMPT_VERSION = 1  # part of the snapshot key: bump when the prompt layout below changes
CORPUS_CHARS = 1_300_000
# CPU self-test: no queue / eco / :8080 handling; the server comes from XTXBENCH_TEST_SERVER (format keys: root port
# slots log), e.g. "{root}/bin/llama-server -m small.gguf -c 8192 -t 2 --port {port} --slot-save-path {slots}"
TEST = os.environ.get("XTXBENCH_TEST") == "1"
PROD_ENV = {"GGML_HIP_PM4": "1", "GGML_HIP_PM4_WA": "2", "GGML_HIP_PM4_GUARD": "1", "HSA_USE_SVM": "0"}
KEY_ENV_PREFIX = ("LLAMA_", "GGML_", "HSA_", "HIP_", "ROCR_", "AMD_")
KEY_ENV_SKIP = {HOOK_ENV, "QUEUE_PM4_SAFETY"}
KEY_ARGV_SKIP = {"--port", "--host", "--log-file", "--slot-save-path"}
USER_TEXT = ("Below is a long collection of documents.\n\n",
             "\n\nWrite a structured summary of the documents above: the main topics, and for each one two or three key points.")
GREEDY_PROMPT = "Explain how a hash map works, step by step."
DOC_MARK = "@@XTXBENCH_DOC@@"
SRC_DIRS = ("ggml/src", "ggml/include", "src", "include", "common", "tools/server")
SRC_EXT = (".c", ".cc", ".cpp", ".h", ".hpp", ".cu", ".cuh", ".txt", ".cmake")


def label_n(n: int) -> str:
    return f"{n // 1024}k" if n % 1024 == 0 else f"{n / 1000:g}k"


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, obj):
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:8]


def sha256_cached(path: str) -> str:
    """sha256 of a file, cached by (realpath, size, mtime) in cache/sha.json (the 16.8 GB model hashes once)."""
    path = os.path.realpath(path)
    s = os.stat(path)
    db_path = os.path.join(CACHE, "sha.json")
    e = load_json(db_path, {}).get(path)
    if e and e["size"] == s.st_size and e["mtime_ns"] == s.st_mtime_ns:
        return e["sha256"]
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    db = load_json(db_path, {})
    db[path] = {"size": s.st_size, "mtime_ns": s.st_mtime_ns, "sha256": h.hexdigest()}
    save_json(db_path, db)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------------ arms
def norm_root(p: str) -> str:
    p = os.path.abspath(os.path.expanduser(p))
    if os.path.basename(p) == "bin" and os.path.exists(os.path.join(p, "llama-server")):
        p = os.path.dirname(p)
    return p


def kv_list(items) -> dict:
    out = {}
    for kv in items or []:
        if "=" not in kv:
            sys.exit(f"expected NAME=VALUE, got {kv!r}")
        k, v = kv.split("=", 1)
        out[k] = v
    return out


class Arm:
    def __init__(self, name, root, env, args, switches):
        self.name, self.root, self.env, self.args, self.switches = name, norm_root(root), env, args, switches

    def server_sig(self):
        return (self.root, tuple(sorted(self.env.items())), tuple(self.args))

    def describe(self):
        parts = [self.root.replace(HOME, "~")]
        parts += [f"{k}={v}" for k, v in sorted(self.env.items())]
        parts += [f"args {','.join(self.args)}"] if self.args else []
        parts += [f"switch {k}={v}" for k, v in sorted(self.switches.items())]
        return " ".join(parts)


def engine_files(root: str):
    b = os.path.join(root, "bin")
    names = ["llama-server"] + sorted(n for n in os.listdir(b) if n.startswith("lib") and ".so" in n) if os.path.isdir(b) else []
    return sorted({os.path.realpath(os.path.join(b, n)) for n in names if os.path.exists(os.path.join(b, n))})


def check_engine(root: str, need=("llama-server",), src: str | None = None):
    """-> (errors, warnings, notes). Missing binaries = error; binaries older than their git sources = stale."""
    errors, stale, notes = [], [], []
    for n in need:
        if not os.access(os.path.join(root, "bin", n), os.X_OK):
            errors.append(f"{root}/bin/{n} missing")
    if errors:
        return errors, stale, notes
    if src is None:
        r = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        src = r.stdout.strip() if r.returncode == 0 else None
    if src is None:
        notes.append(f"{root}: install dir, no source tree (staleness not checked; --base-src/--var-src to set one)")
        return errors, stale, notes
    files = [os.path.join(root, "bin", n) for n in need] + engine_files(root)
    oldest = min(os.stat(f).st_mtime for f in files)
    r = subprocess.run(["git", "-C", src, "ls-files", "-z", "--", *SRC_DIRS], capture_output=True)
    newest, newest_f = 0.0, None
    for f in r.stdout.decode().split("\0"):
        if f.endswith(SRC_EXT):
            try:
                m = os.stat(os.path.join(src, f)).st_mtime
            except OSError:
                continue
            if m > newest:
                newest, newest_f = m, f
    if newest > oldest:
        stale.append(f"{root}: binaries ({time.strftime('%F %T', time.localtime(oldest))}) older than {src}/{newest_f} "
                     f"({time.strftime('%F %T', time.localtime(newest))}): rebuild OUTSIDE the GPU window")
    notes.append(f"{root}: sources {src} @ {git_head(src)}")
    return errors, stale, notes


def git_head(src):
    r = subprocess.run(["git", "-C", src, "log", "-1", "--format=%h"], capture_output=True, text=True)
    return r.stdout.strip() or "?"


def has_hook(root: str) -> bool:
    lib = os.path.join(root, "bin", "libggml-hip.so")
    try:
        with open(lib, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
            return m.find(HOOK_ENV.encode()) >= 0
    except (OSError, ValueError):
        return False


# ------------------------------------------------------------------------------------------------------------ run log
class Run:
    def __init__(self, mode, label):
        self.t0 = time.time()
        self.dir = os.path.join(RUNS, time.strftime("%m%d-%H%M%S") + f"-{mode}-{label}")
        os.makedirs(self.dir, exist_ok=True)
        self.stages = []
        self.logf = open(os.path.join(self.dir, "xtxbench.log"), "a")

    def log(self, msg):
        line = f"{time.strftime('%T')} {msg}"
        print(line, flush=True)
        self.logf.write(line + "\n")
        self.logf.flush()

    def record(self, obj):
        with open(os.path.join(self.dir, "results.jsonl"), "a") as f:
            f.write(json.dumps(obj) + "\n")

    @contextlib.contextmanager
    def stage(self, name, cat):
        """cat: once (per engine: snapshots, proof), session (per session: server A start, noise), variant"""
        t = time.time()
        self.log(f"[stage] {name} ...")
        ok = False
        try:
            yield
            ok = True
        finally:
            s = {"stage": name, "cat": cat, "s": round(time.time() - t, 1), "ok": ok}
            self.stages.append(s)
            with open(os.path.join(self.dir, "timings.jsonl"), "a") as f:
                f.write(json.dumps(s) + "\n")
            self.log(f"[stage] {name}: {s['s']:.1f} s{'' if ok else ' (FAILED)'}")


# ------------------------------------------------------------------------------------------------------------ server
def find_server_pid(port: int):
    pat = re.compile(rf"llama-server\0.*--port\0{port}\0")
    for p in os.listdir("/proc"):
        if p.isdigit():
            try:
                cl = open(f"/proc/{p}/cmdline", "rb").read().decode(errors="replace")
            except OSError:
                continue
            if pat.search(cl) or (cl.split("\0")[0].endswith("llama-server") and f"\0--port\0{port}\0" in cl):
                return int(p)
    return None


def alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:  # a zombie counts as gone
        return open(f"/proc/{pid}/stat").read().split(") ")[1][0] != "Z"
    except OSError:
        return False


def stop_pid(pid, log, what, wait=60):
    """ONE SIGTERM, wait up to `wait` s, then SIGKILL."""
    if pid is None or not alive(pid):
        return
    os.kill(pid, signal.SIGTERM)
    t = time.time()
    while time.time() - t < wait:
        if not alive(pid):
            return
        time.sleep(0.5)
    os.kill(pid, signal.SIGKILL)
    log(f"{what}: SIGKILL needed after {wait} s")
    time.sleep(2)


class Server:
    def __init__(self, run, arm, tag, port, switch_file=None):
        self.run, self.arm, self.tag, self.port, self.switch_file = run, arm, tag, port, switch_file
        self.out = os.path.join(run.dir, f"srv-{tag}.out")
        self.logfile = os.path.join(run.dir, f"srv-{tag}.log")
        self.proc = self.pid = None
        self.start_s = None
        self.n_req = 0  # completions since start: md5 is only trusted on the first round of a fresh server

    def start(self):
        if not TEST and os.path.exists(VRAM_OK) and subprocess.run([VRAM_OK]).returncode != 0:
            raise RuntimeError(f"{self.tag}: VRAM busy")
        old = find_server_pid(self.port)
        if old:  # a leftover of an interrupted run would answer /health in place of the new server
            self.run.log(f"port {self.port}: leftover server pid {old}: ONE SIGTERM")
            stop_pid(old, self.run.log, f"leftover :{self.port}")
        env = dict(os.environ)
        env.pop("QUEUE_PM4_SAFETY", None)
        env.update(PROD_ENV)
        env.update(self.arm.env)
        env.update(ROCM_DIR=self.arm.root, PORT=str(self.port), LOG=self.logfile,
                   EXTRA_ARGS=",".join(["--slot-save-path", SLOTS] + self.arm.args))
        if self.switch_file:
            env[HOOK_ENV] = self.switch_file
        if TEST:
            cmd = shlex.split(os.environ["XTXBENCH_TEST_SERVER"].format(root=self.arm.root, port=self.port, slots=SLOTS,
                                                                       log=self.logfile)) + self.arm.args
        else:
            cmd = [RUN_TOPKA, "uncensored"]
        t = time.time()
        self.proc = subprocess.Popen(cmd, env=env, stdout=open(self.out, "w"), stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
        while time.time() - t < 300:
            if self.proc.poll() is not None:
                raise RuntimeError(f"server {self.tag} exited rc={self.proc.returncode}: {self.tail()}")
            try:
                if self.call("/health", timeout=5).get("status") == "ok":
                    break
            except Exception:  # noqa: BLE001 - loading
                pass
            time.sleep(1)
        else:
            self.stop()
            raise RuntimeError(f"server {self.tag} not healthy in 300 s: {self.tail()}")
        self.pid = find_server_pid(self.port) or self.proc.pid
        self.start_s = time.time() - t
        self.n_req = 0
        self.run.log(f"server {self.tag} up in {self.start_s:.1f} s (pid {self.pid}): {self.arm.describe()}")

    def tail(self, n=5):
        try:
            return " | ".join(open(self.out, errors="replace").read().splitlines()[-n:])
        except OSError:
            return "?"

    def stop(self):
        pid = self.pid or find_server_pid(self.port)
        stop_pid(pid, self.run.log, f"server {self.tag}")
        if self.proc is not None:
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                stop_pid(self.proc.pid, self.run.log, f"launcher {self.tag}", 5)
        self.pid = None

    def call(self, path, body=None, timeout=3600):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data,
                                     headers={"Content-Type": "application/json"} if data is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{path}: HTTP {e.code}: {e.read()[:300]!r}") from None

    def slot(self, action, filename=None):
        return self.call(f"/slots/0?action={action}", {"filename": filename} if filename else {}, timeout=900)

    def tokenize(self, text, special):
        return self.call("/tokenize", {"content": text, "add_special": False, "parse_special": special})["tokens"]

    def complete(self, tokens, n_predict, temp=0.0, seed=1, cache_prompt=True):
        body = {"prompt": tokens, "n_predict": n_predict, "temperature": temp, "seed": seed,
                "cache_prompt": cache_prompt, "stream": False}
        t = time.time()
        self.n_req += 1
        r = self.call("/completion", body)
        wall = time.time() - t
        tm = {k: (v if v is not None else 0.0) for k, v in r["timings"].items()}  # inf/NaN arrive as null
        n, acc = tm["predicted_n"], tm.get("draft_n_accepted", 0) or 0
        return {"prompt_n": tm["prompt_n"], "cache_n": tm.get("cache_n"), "prompt_ms": round(tm["prompt_ms"], 1),
                "prefill_tps": round(tm["prompt_per_second"], 2), "decode_tps": round(tm["predicted_per_second"], 3),
                "gen": n, "predicted_ms": round(tm["predicted_ms"], 1), "draft_n": tm.get("draft_n", 0) or 0,
                "accepted": acc, "ms_step": round(tm["predicted_ms"] / max(1, n - acc), 3),
                "md5": md5(r.get("content", "")), "wall_s": round(wall, 2)}

    def greedy_md5(self):
        """the long-standing greedy md5 of the job scripts (chat, T=0, 256 tokens, seed 1): md5 of the content (the
        value in the job logs, e.g. c23506c7) and of reasoning + content (what the arms are compared on)"""
        r = self.call("/v1/chat/completions", {"messages": [{"role": "user", "content": GREEDY_PROMPT}],
                                               "max_tokens": 256, "temperature": 0, "seed": 1}, timeout=600)
        msg = r["choices"][0]["message"]
        return md5(msg.get("content") or ""), md5((msg.get("reasoning_content") or "") + (msg.get("content") or ""))

    def engine_key(self, corpus_sha):
        """key = model sha + engine binary sha + server argv/env (minus port/log/slot path/switch file) + corpus"""
        pid = self.pid
        argv = open(f"/proc/{pid}/cmdline", "rb").read().decode().split("\0")[:-1]
        env = dict(kv.split("=", 1) for kv in open(f"/proc/{pid}/environ", "rb").read().decode(errors="replace")
                   .split("\0") if "=" in kv)
        exe = os.path.realpath(f"/proc/{pid}/exe")
        argv_f, skip = [], False
        for a in argv[1:]:
            if skip:
                skip = False
            elif a in KEY_ARGV_SKIP:
                skip = True
            else:
                argv_f.append(a)
        model = argv[argv.index("-m") + 1] if "-m" in argv else None
        files = {a: sha256_cached(a) for a in argv_f if a != model and os.path.isfile(a) and os.path.getsize(a) < 1 << 28}
        bins = {os.path.basename(f): sha256_cached(f) for f in
                sorted({exe} | set(engine_files(os.path.dirname(os.path.dirname(exe)))))}
        comp = {"model": os.path.basename(model) if model else None, "model_sha": sha256_cached(model) if model else None,
                "bin": bins, "argv": argv_f, "files": files, "corpus": corpus_sha, "prompt_version": PROMPT_VERSION,
                "env": {k: v for k, v in sorted(env.items()) if k.startswith(KEY_ENV_PREFIX) and k not in KEY_ENV_SKIP}}
        comp["engine"] = hashlib.sha256(json.dumps(comp["bin"], sort_keys=True).encode()).hexdigest()[:12]
        return hashlib.sha256(json.dumps(comp, sort_keys=True).encode()).hexdigest()[:16], comp


# ------------------------------------------------------------------------------------------------------------ prompts
def corpus_text():
    """frozen copy of the long_ctx_bench.py corpus (its sources change over time; the snapshots must not)"""
    if not os.path.exists(CORPUS):
        sys.path.insert(0, os.path.join(HOME, "qwen-opt"))
        from long_ctx_bench import corpus  # noqa: PLC0415
        with open(CORPUS + ".tmp", "w") as f:
            f.write(corpus(CORPUS_CHARS))
        os.replace(CORPUS + ".tmp", CORPUS)
    return open(CORPUS).read()


class Prompts:
    """depth D = D document tokens: pre + doc[:D] is the snapshot prefix P, P + post the request (post = the question
    and the assistant turn, thinking off, as /apply-template renders it)"""

    def __init__(self, srv, need):
        text = corpus_text()
        self.corpus_sha = hashlib.sha256(text.encode()).hexdigest()[:16]
        try:
            tpl = srv.call("/apply-template", {"messages": [{"role": "user", "content": USER_TEXT[0] + DOC_MARK + USER_TEXT[1]}],
                                               "chat_template_kwargs": {"enable_thinking": False}})["prompt"]
            pre, post = tpl.split(DOC_MARK)
        except Exception:  # noqa: BLE001 - template endpoint missing: ChatML as the Qwen template renders it
            pre = "<|im_start|>user\n" + USER_TEXT[0]
            post = USER_TEXT[1] + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        self.pre, self.post = srv.tokenize(pre, True), srv.tokenize(post, True)
        self.doc = srv.tokenize(text, False)
        if len(self.doc) < need:  # as ctx262/fill.py: repeat the text
            self.doc = (self.doc * (need // max(1, len(self.doc)) + 1))[:need]
        self.small = self.pre + self.doc[:16] + self.post

    def snap(self, depth):
        p = self.pre + self.doc[:depth]
        return p, p + self.post

    def total(self, n):
        return self.pre + self.doc[:n - len(self.pre) - len(self.post)] + self.post


# ------------------------------------------------------------------------------------------------------------ snapshots
def snap_file(key, depth):
    return f"{key}-d{depth}.bin"


def manifest_path(key):
    return os.path.join(SLOTS, f"{key}.json")


def snapshot_sets():
    out = []
    for p in sorted(os.listdir(SLOTS)) if os.path.isdir(SLOTS) else []:
        if p.endswith(".json"):
            m = load_json(os.path.join(SLOTS, p), None)
            if m:
                out.append(m)
    return sorted(out, key=lambda m: m.get("created", 0))


def snapshot_ok(m, depth):
    e = (m or {}).get("depths", {}).get(str(depth))
    if not e:
        return False
    f = os.path.join(SLOTS, e["file"])
    return os.path.exists(f) and os.path.getsize(f) == e["bytes"]


def gc_snapshots(keep_keys, log, keep=2):
    """automatic invalidation: a new engine/config key makes a new set; only the newest `keep` sets stay on disk"""
    sets = snapshot_sets()
    for m in sets[:-keep]:
        if m["key"] in keep_keys:
            continue
        for e in m.get("depths", {}).values():
            with contextlib.suppress(OSError):
                os.remove(os.path.join(SLOTS, e["file"]))
        with contextlib.suppress(OSError):
            os.remove(manifest_path(m["key"]))
        log(f"snapshots: removed old set {m['key']} ({m.get('comp', {}).get('engine', '?')}, created "
            f"{time.strftime('%F %T', time.localtime(m.get('created', 0)))})")


# ------------------------------------------------------------------------------------------------------------ bench
class Bench:
    def __init__(self, args, mode):
        self.a, self.mode = args, mode
        self.run = Run(mode, args.label)
        self.log = self.run.log
        self.depths = [int(x) for x in args.depths.split(",")]
        self.sizes = [int(x) for x in args.prefill.split(",")]
        self.base = Arm("A", args.base, kv_list(args.base_env), [], kv_list(args.base_switch))
        self.var = Arm("B", args.var or args.base, kv_list(args.var_env),
                       [x for x in (args.var_args or "").split(",") if x], kv_list(args.var_switch))
        self.switching = bool(self.base.switches or self.var.switches)
        self.same_server = self.base.server_sig() == self.var.server_sig() and not args.force_restart
        if self.switching and not self.same_server:
            sys.exit("runtime switches need one server: --base/--var, env and args must be equal (no --force-restart)")
        self.switch_file = os.path.join(self.run.dir, "switches.txt") if self.switching else None
        self.groups = {"decode": [f"decode@{label_n(d)}" for d in self.depths],
                       "prefill": [f"prefill@{label_n(n)}" for n in self.sizes]}
        if mode == "t2":
            self.groups["decodeT1"] = [f"decodeT1@{label_n(d)}" for d in self.depths]
            self.groups["sweep"] = ["sweepT1"]
            self.groups["long"] = [f"prefill@{label_n(args.long_prefill)}", f"fill@{label_n(args.fill)}",
                                   f"filldec@{label_n(args.fill)}"]
        self.rounds = []  # (round id, arm, {metric: rec}, t_start, t_end)
        self.servers = []
        self.prompts = None
        self.key = self.comp = None  # engine key of A (snapshots, noise cache)
        self.snaps = {}  # arm name -> (snapshot key, manifest)
        self.proved = False
        self.a_ref = None
        self.greedy = {}

    # ---------------------------------------------------------------- safety around the GPU window
    def preflight(self):
        errs, stale = [], []
        var_src = self.a.var_src or (self.a.base_src if self.var.root == self.base.root else None)
        checks = {(self.base.root, self.a.base_src), (self.var.root, var_src)}
        for root, src in sorted(checks, key=str):
            e, s, notes = check_engine(root, src=src)
            errs += e
            stale += s
            for n in notes:
                self.log(f"check: {n}")
        if self.switching and not TEST and not has_hook(self.base.root):
            errs.append(f"{self.base.root}: no {HOOK_ENV} hook in libggml-hip.so (use --var-env: restart arms)")
        for s in stale:
            self.log(f"WARNING stale: {s}")
        if errs:
            for e in errs:
                self.log(f"REFUSED: {e}")
            sys.exit(2)
        if stale and not self.a.allow_stale:
            self.log("REFUSED: stale binaries (no compilation in the GPU window); --allow-stale measures them anyway")
            sys.exit(2)
        if TEST:
            return
        if not under_queue():
            self.log("REFUSED: GPU mode outside ~/qwen-opt/queue/run-jobs.sh")
            sys.exit(2)
        eco = eco_status()
        if "sclk cap (state): 2200" not in eco:
            self.log(f"REFUSED: eco 2200 not active: {eco.splitlines()[:1]}")
            sys.exit(3)
        pid = find_server_pid(8080)
        if pid:
            self.log(f":8080 server pid {pid}: ONE SIGTERM (60 s, then SIGKILL)")
            stop_pid(pid, self.log, ":8080")

    def restore_8080(self):
        if TEST or find_server_pid(8080):
            return
        out = os.path.join(self.run.dir, "restore8080.out")
        subprocess.Popen(["setsid", "nohup", RUN_TOPKA, "uncensored"], stdout=open(out, "w"), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True,
                         env={k: v for k, v in os.environ.items() if k not in ("QUEUE_PM4_SAFETY", "GGML_HIP_PM4")})
        t = time.time()
        health, n_ctx = "?", "?"
        while time.time() - t < 240:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5) as r:
                    health = r.read().decode()
                with urllib.request.urlopen("http://127.0.0.1:8080/props", timeout=5) as r:
                    n_ctx = json.loads(r.read())["default_generation_settings"]["n_ctx"]
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        self.log(f"restore :8080 (run-topka.sh uncensored): health={health} n_ctx={n_ctx} in {time.time() - t:.0f} s")

    # ---------------------------------------------------------------- servers and switches
    def start(self, arm, tag, cat):
        srv = Server(self.run, arm, tag, self.a.port, self.switch_file)
        if self.switch_file:
            self.write_switches(arm)
        with self.run.stage(f"server start {tag}", cat):
            srv.start()
        self.servers.append(srv)
        if self.prompts is None:
            need = max(self.depths + self.sizes + ([self.a.long_prefill, self.a.fill] if self.mode == "t2" else []))
            self.prompts = Prompts(srv, need)
        srv.key, srv.comp = srv.engine_key(self.prompts.corpus_sha)
        self.log(f"server {tag} engine key {srv.key}: model {srv.comp['model']} sha {str(srv.comp['model_sha'])[:12]}, "
                 f"engine {srv.comp['engine']}, {len(srv.comp['argv'])} args, {len(srv.comp['env'])} env")
        if arm is self.base and self.key is None:
            self.key, self.comp = srv.key, srv.comp
        return srv

    def write_switches(self, arm):
        body = f"# xtxbench arm {arm.name}\n" + "".join(f"{k}={v}\n" for k, v in sorted(arm.switches.items()))
        with open(self.switch_file + ".tmp", "w") as f:
            f.write(body)
        os.replace(self.switch_file + ".tmp", self.switch_file)

    def flip(self, srv, arm):
        """runtime switch: write the arm's file, run one small request (graph compute -> poll -> re-capture) and
        confirm the generation line in the server output"""
        if not self.switch_file:
            return
        self.write_switches(arm)
        time.sleep(0.05)
        srv.slot("erase")
        srv.complete(self.prompts.small, 4, cache_prompt=False)
        srv.slot("erase")
        want = " ".join(f"{k}={v}" for k, v in sorted(arm.switches.items()))
        gens = [m for ln in open(srv.out, errors="replace")
                if (m := re.search(r"ggml_cuda_rt_switch: gen (\d+) from (\S+): ?(.*)$", ln.rstrip()))]
        got = gens[-1][3].strip() if gens else "(empty)"  # no line yet = the file never held values
        if got != (want or "(empty)"):
            raise RuntimeError(f"switch flip to arm {arm.name} not confirmed: want {want or '(empty)'}, server: {got}")
        self.log(f"switches -> arm {arm.name}: {want or '(none)'}")

    # ---------------------------------------------------------------- snapshots + md5 restore proof
    def ensure_snapshots(self, srv, arm, key, comp, base):
        """snapshot set for `arm` (by default B restores A's set; --own-snap gives B its own, keyed by its engine);
        a missing set is created here, and the first creation (or --prove) runs the md5 restore proof"""
        if base and self.a.snap_compat:
            for m in reversed(snapshot_sets()):
                c = m.get("comp", {})
                if all(c.get(k) == comp.get(k) for k in ("model_sha", "argv", "env", "files", "corpus", "prompt_version")) \
                        and all(snapshot_ok(m, d) for d in self.depths):
                    key = m["key"]
                    self.log(f"snapshots: --snap-compat uses set {key} (engine {c.get('engine')}, same model/flags/env)")
                    break
        m = load_json(manifest_path(key), None) or {"key": key, "comp": comp, "created": time.time(), "depths": {}}
        missing = [d for d in self.depths if not snapshot_ok(m, d)]
        prove = base and (self.a.prove or bool(missing))
        if not missing:
            self.log(f"snapshots: set {key} valid for {','.join(label_n(d) for d in self.depths)}")
        for d in missing:
            P, T = self.prompts.snap(d)
            with self.run.stage(f"snapshot create {arm.name} {label_n(d)}", "once"):
                srv.slot("erase")
                r = srv.complete(P, 1, cache_prompt=True)
                if r["prompt_n"] != len(P):
                    raise RuntimeError(f"snapshot prefill processed {r['prompt_n']} of {len(P)} tokens")
                s = srv.slot("save", snap_file(key, d))
                e = {"depth": d, "file": snap_file(key, d), "n_tokens": s["n_saved"], "bytes": s["n_written"],
                     "save_ms": s["timings"]["save_ms"], "prefill_s": round(r["prompt_ms"] / 1000, 1),
                     "prefill_tps": r["prefill_tps"], "created": time.time()}
                self.log(f"snapshot {label_n(d)}: {len(P)} tokens prefilled in {e['prefill_s']} s ({r['prefill_tps']} t/s), "
                         f"saved {e['bytes'] / 2**20:.0f} MiB in {e['save_ms'] / 1000:.1f} s")
                if prove:  # fresh prefill (in memory) + decode, before any restore
                    e["proof_mem"] = srv.complete(T, self.a.tokens, 0.0, 1, True)
                    self.check_suffix(e["proof_mem"], f"fresh {label_n(d)}")
                    self.log(f"proof {label_n(d)}: fresh prefill + decode md5 {e['proof_mem']['md5']} "
                             f"{e['proof_mem']['decode_tps']} t/s")
                m["depths"][str(d)] = e
                save_json(manifest_path(key), m)
        if missing:
            gc_snapshots({key, self.key}, self.log)
        if prove and not missing:  # --prove on existing snapshots: the fresh in-memory path needs one prefill each
            for d in self.depths:
                P, T = self.prompts.snap(d)
                with self.run.stage(f"proof fresh {label_n(d)}", "once"):
                    srv.slot("erase")
                    srv.complete(P, 1, cache_prompt=True)
                    m["depths"][str(d)]["proof_mem"] = srv.complete(T, self.a.tokens, 0.0, 1, True)
            save_json(manifest_path(key), m)
        if prove:
            for d in self.depths:  # the old method: one cold request (prefill + decode), as lc.py does
                T = self.prompts.snap(d)[1]
                with self.run.stage(f"proof cold {label_n(d)}", "once"):
                    srv.slot("erase")
                    c = srv.complete(T, self.a.tokens, 0.0, 1, cache_prompt=False)
                    m["depths"][str(d)]["proof_cold"] = c
                    self.log(f"proof {label_n(d)}: cold single request md5 {c['md5']} prefill {c['prompt_ms'] / 1000:.1f} s "
                             f"decode {c['decode_tps']} t/s")
            save_json(manifest_path(key), m)
            srv.slot("erase")
        self.snaps[arm.name] = (key, m)
        self.proved = self.proved or prove

    def check_suffix(self, rec, what):
        """a request on a restored/prefilled prefix must process only the question suffix"""
        if rec["prompt_n"] > len(self.prompts.post) + 8:
            raise RuntimeError(f"{what}: the server re-processed {rec['prompt_n']} prompt tokens (suffix "
                               f"{len(self.prompts.post)}): the cached/restored prefix was not used (hybrid state "
                               "rollback?) - snapshots unusable for this config")

    # ---------------------------------------------------------------- measurements
    def m_decode(self, srv, arm, temp, seed, prefix, fresh=False):
        key, man = self.snaps[arm.name]
        out = {}
        for d in self.depths:
            T = self.prompts.snap(d)[1]
            r = srv.slot("restore", snap_file(key, d))
            e = man["depths"][str(d)]
            if r["n_restored"] != e["n_tokens"]:
                raise RuntimeError(f"restore {label_n(d)}: {r['n_restored']} tokens, expected {e['n_tokens']}")
            rec = srv.complete(T, self.a.tokens, temp, seed, True)
            self.check_suffix(rec, f"restored {label_n(d)}")
            rec["restore_ms"] = round(r["timings"]["restore_ms"], 1)
            rec["md5_fresh"] = fresh  # first round after a fresh server start: the only md5 the verdict uses
            rec["value"] = rec["decode_tps"]
            out[f"{prefix}@{label_n(d)}"] = rec
        srv.slot("erase")
        return out

    def m_prefill(self, srv, sizes, prefix="prefill"):
        out = {}
        for n in sizes:
            srv.slot("erase")
            rec = srv.complete(self.prompts.total(n), 1, cache_prompt=False)
            rec["value"] = rec["prefill_tps"]
            out[f"{prefix}@{label_n(n)}"] = rec
        srv.slot("erase")
        return out

    def m_sweep(self, srv, rid):
        srv.slot("erase")
        r = subprocess.run([sys.executable, SPEC_SWEEP, "--label", f"xtx-{self.a.label}-{rid}", "--port", str(srv.port),
                            "--temps", "1.0", "--seeds", "1,2,3"], cwd=self.run.dir, capture_output=True, text=True)
        line = (r.stdout.strip().splitlines() or [""])[-1]
        mm = re.search(r"median\s+([\d.]+) t/s,\s+([\d.]+) ms/step", line)
        if not mm:
            raise RuntimeError(f"spec_sweep failed: {line} {r.stderr[-300:]}")
        srv.slot("erase")
        return {"sweepT1": {"value": float(mm[1]), "ms_step": float(mm[2]), "line": line}}

    def m_long(self, srv):
        out = self.m_prefill(srv, [self.a.long_prefill])
        srv.slot("erase")
        rec = srv.complete(self.prompts.total(self.a.fill), self.a.tokens, 0.0, 1, cache_prompt=False)
        out[f"fill@{label_n(self.a.fill)}"] = dict(rec, value=rec["prefill_tps"])
        out[f"filldec@{label_n(self.a.fill)}"] = dict(rec, value=rec["decode_tps"])
        srv.slot("erase")
        return out

    def measure(self, srv, arm, rid, groups, cat):
        with self.run.stage(f"round {rid} ({','.join(groups)})", cat):
            # a second slot restore on the same server diverges from a fresh prefill (state leaks between requests,
            # GPU A/A 2026-11-09), so only the first round on a freshly started server carries a valid decode md5
            fresh = srv.n_req == 0
            self.flip(srv, arm)
            t = time.time()
            res = {}
            if "decode" in groups:
                res.update(self.m_decode(srv, arm, 0.0, 1, "decode", fresh))
            if "decodeT1" in groups:
                res.update(self.m_decode(srv, arm, 1.0, 42, "decodeT1"))
            if "prefill" in groups:
                res.update(self.m_prefill(srv, self.sizes))
            if "sweep" in groups:
                res.update(self.m_sweep(srv, rid))
            if "long" in groups:
                res.update(self.m_long(srv))
            if srv.tag not in self.greedy:
                srv.slot("erase")
                self.greedy[srv.tag] = (arm.name, srv.greedy_md5())
                srv.slot("erase")
            self.rounds.append((rid, arm.name, res, t, time.time()))
            for m, rec in res.items():
                self.run.record({"round": rid, "arm": arm.name, "server": srv.tag, "metric": m, **rec})
            self.log(f"round {rid}: " + "  ".join(f"{m} {rec['value']:.2f}" + (f" [{rec['md5']}]" if "md5" in rec and
                                                   m.startswith("decode@") else "") for m, rec in res.items()))
        return res

    # ---------------------------------------------------------------- noise + decisions
    def noise_cache(self):
        return os.path.join(CACHE, f"noise-{self.key}.json")

    def load_noise(self, metrics):
        n = load_json(self.noise_cache(), None)
        if self.a.renoise or not n or time.time() - n["measured"] > self.a.noise_ttl_h * 3600:
            return None
        if not all(m in n["values"] for m in metrics):
            return None
        self.log(f"noise: session cache {self.noise_cache()} ({(time.time() - n['measured']) / 60:.0f} min old)")
        return n["values"]

    def proxy_noise(self, noise):
        """t2 'long' metrics have no A-A' pair (one 255k fill is ~9 min): prefill noise / decode noise as proxies"""
        out = dict(noise)
        pf = max([v for k, v in noise.items() if k.startswith("prefill@")] or [0.0])
        dc = max([v for k, v in noise.items() if k.startswith("decode@")] or [0.0])
        for m in self.groups.get("long", []):
            out.setdefault(m, dc if m.startswith("filldec") else pf)
        return out

    def first_pair(self, g, a, b, noise, t0_gain):
        ms = self.groups[g]
        d = {m: b[m]["value"] / a[m]["value"] - 1 for m in ms}
        thr = {m: max(5 * noise[m], self.a.win_floor / 100) for m in ms}
        signs = {d[m] > 0 for m in ms}
        if all(abs(d[m]) >= thr[m] for m in ms) and len(signs) == 1:
            return ("WIN" if signs.pop() else "LOSS"), f"|d| >= max(5n, {self.a.win_floor}%) at every metric, one sign"
        if all(abs(d[m]) <= max(noise[m], self.a.noise_floor / 100) for m in ms) and not t0_gain:
            return "NULL", "|d| <= noise everywhere, no t0 kernel gain"
        return "ABBA", "ambiguous after A -> B"

    def abba(self, g, a1, b1, b2, a2, noise):
        ms = self.groups[g]
        sig_gain, sig_loss, det = [], [], {}
        for m in ms:
            ma, mb = (a1[m]["value"] + a2[m]["value"]) / 2, (b1[m]["value"] + b2[m]["value"]) / 2
            spread = max(noise[m], abs(a2[m]["value"] - a1[m]["value"]) / ma, abs(b2[m]["value"] - b1[m]["value"]) / mb,
                         self.a.noise_floor / 100)
            dd = mb / ma - 1
            det[m] = (dd, spread)
            if dd > 2 * spread:
                sig_gain.append(m)
            elif dd < -max(2 * spread, self.a.max_loss / 100):
                sig_loss.append(m)
        if sig_gain and sig_loss:
            return "MIXED", f"gain at {','.join(sig_gain)}, loss at {','.join(sig_loss)}", det
        if sig_gain:
            return "WIN", f"significant gain (> 2x spread) at {','.join(sig_gain)}, no loss beyond {self.a.max_loss}%", det
        if sig_loss:
            return "LOSS", f"significant loss at {','.join(sig_loss)}", det
        return "NULL", "no significant difference on the A B B A means", det

    def t0_gain(self):
        if self.a.t0 in ("gain", "none"):
            return self.a.t0 == "gain"
        t = load_json(os.path.join(CACHE, f"t0-{self.a.label}.json"), None)
        if not t or time.time() - t["time"] > 7 * 86400:
            return False
        self.log(f"t0 ({time.strftime('%F %T', time.localtime(t['time']))}): kernel gain median {t['gain_pct']:+.2f}%, "
                 f"best {t['best_pct']:+.2f}% -> {'gain' if t['kernel_gain'] else 'no gain'}")
        return t["kernel_gain"]

    # ---------------------------------------------------------------- the A/B procedure
    def go(self):
        self.preflight()
        t_go = time.time()
        srv_a = srv_b = None
        try:
            srv_a = self.start(self.base, "A1", "session")
            self.ensure_snapshots(srv_a, self.base, srv_a.key, srv_a.comp, True)
            self.snaps["B"] = self.snaps["A"]
            all_g = list(self.groups)
            noise = self.load_noise([m for g in all_g if g != "long" for m in self.groups[g]])
            a0 = self.measure(srv_a, self.base, "A0", all_g, "variant")
            a_ref = a0
            if noise is None:
                a1 = self.measure(srv_a, self.base, "A0'", [g for g in all_g if g != "long"], "session")
                noise = {m: abs(a1[m]["value"] - a0[m]["value"]) / a0[m]["value"] for m in a1}
                save_json(self.noise_cache(), {"key": self.key, "measured": time.time(), "run": self.run.dir, "values": noise})
                a_ref = dict(a0, **a1)
            self.a_ref = a_ref
            noise = self.proxy_noise(noise)
            if self.same_server:
                srv_b = srv_a
            else:
                with self.run.stage("server stop A1", "variant"):
                    srv_a.stop()
                srv_b = self.start(self.var, "B1", "variant")
                if self.a.own_snap:
                    self.ensure_snapshots(srv_b, self.var, srv_b.key, srv_b.comp, False)
            b1 = self.measure(srv_b, self.var, "B1", all_g, "variant")
            t0_gain = self.t0_gain()
            dec = {g: self.first_pair(g, a_ref, b1, noise, t0_gain) for g in all_g}
            for g, (d, why) in dec.items():
                self.log(f"decision after A -> B: {g}: {d} ({why})")
            amb = [g for g, (d, _) in dec.items() if d == "ABBA"]
            details = {}
            if amb:
                b2 = self.measure(srv_b, self.var, "B2", amb, "variant")
                if self.same_server:
                    srv_a2 = srv_a
                else:
                    with self.run.stage("server stop B1", "variant"):
                        srv_b.stop()
                    srv_a2 = self.start(self.base, "A2", "variant")
                a2 = self.measure(srv_a2, self.base, "A2", amb, "variant")
                for g in amb:
                    d, why, det = self.abba(g, a_ref, b1, b2, a2, noise)
                    dec[g] = (d, why)
                    details[g] = det
                    self.log(f"decision after A B B A: {g}: {d} ({why})")
            self.decisions, self.details, self.noise = dec, details, noise
            self.summary(time.time() - t_go)
        finally:
            for s in self.servers:
                with contextlib.suppress(Exception):
                    s.stop()
            if not TEST:
                with self.run.stage("restore :8080", "session"):
                    self.restore_8080()

    # ---------------------------------------------------------------- report
    def values(self, rid, m):
        for r, _, res, _, _ in self.rounds:
            if r == rid and m in res:
                return res[m]
        return None

    def summary(self, wall):
        L = []
        p = L.append
        rids = [r for r, *_ in self.rounds]
        p(f"xtxbench {self.mode} · {self.a.label} · {time.strftime('%F %T')} · run {self.run.dir.replace(HOME, '~')}")
        p(f"  A: {self.base.describe()}")
        p(f"  B: {self.var.describe()}" + ("  (same server" + (", runtime switch file)" if self.switching else ")")
                                            if self.same_server else "  (own server)"))
        p(f"  engine key {self.key} (engine {self.comp['engine']}, model sha {str(self.comp['model_sha'])[:12]}); "
          f"snapshots A {self.snaps['A'][0]}, B {self.snaps['B'][0]}")
        p("")
        p(f"{'metric':<16}{'baseline':>10}{'teraz':>10}{'%':>9}{'noise':>8}{'thr':>7}{'runs A/B':>9}  decision")
        n_req = {"A": 0, "B": 0}
        for g, ms in self.groups.items():
            dec, why = self.decisions[g]
            for m in ms:
                a = [rec[m]["value"] for r, arm, rec, *_ in self.rounds if arm == "A" and m in rec]
                b = [rec[m]["value"] for r, arm, rec, *_ in self.rounds if arm == "B" and m in rec]
                n_req["A"] += len(a)
                n_req["B"] += len(b)
                if g in self.details:  # A B B A means (A = the reference pair member + A2)
                    ma = (self.a_ref[m]["value"] + self.values("A2", m)["value"]) / 2
                    mb = statistics.mean(b)
                else:
                    ma, mb = self.a_ref[m]["value"], self.values("B1", m)["value"]
                thr = max(5 * self.noise[m], self.a.win_floor / 100)
                p(f"{m:<16}{ma:>10.2f}{mb:>10.2f}{100 * (mb / ma - 1):>+8.2f}%{100 * self.noise[m]:>7.2f}%"
                  f"{100 * thr:>6.2f}%{len(a):>5}/{len(b):<3}  {dec if m == ms[0] else ''}")
            p(f"{'':<16}-> {g}: {dec} ({why})")
        p("")
        md5_ok = True
        fresh_rounds, md5_na = [], False
        for d in self.depths:
            m = f"decode@{label_n(d)}"
            recs = [(rid, arm, rec[m]) for rid, arm, rec, *_ in self.rounds if m in rec]
            seen = sorted({r["md5"] for _, _, r in recs})
            fresh = {arm: sorted({r["md5"] for _, a2, r in recs if a2 == arm and r.get("md5_fresh")}) for arm in ("A", "B")}
            fresh_rounds += [rid for rid, _, r in recs if r.get("md5_fresh") and rid not in fresh_rounds]
            pr = self.snaps["A"][1]["depths"].get(str(d), {})
            ref = pr["proof_mem"]["md5"] if pr.get("proof_mem") else None
            info = f"; all restores {','.join(seen)} (later restores on the same server leak state: t/s only)"
            if not fresh["B"]:
                p(f"md5 T=0 {m}: n/a ({'same-server' if self.switching else 'no fresh-start B round'}; a separate "
                  f"fresh-start md5 arm is needed){info}")
                md5_na = True
                continue
            cand = sorted(set(fresh["A"]) | set(fresh["B"]) | ({ref} if ref else set()))
            same = len(cand) == 1
            md5_ok &= same
            extra = (f"; A {','.join(fresh['A']) or '-'} B {','.join(fresh['B'])}"
                     + (f", fresh prefill+decode {ref}" if ref else "")
                     + (f", cold single request {pr['proof_cold']['md5']}" if pr.get("proof_cold") else ""))
            p(f"md5 T=0 {m} (first restore per fresh server): {'identical ' + cand[0] if same else 'DIFFERENT'}{extra}{info}")
        proofs = [(d, self.snaps["A"][1]["depths"].get(str(d), {}).get("proof_mem")) for d in self.depths]
        if all(pm for _, pm in proofs):
            fr = {d: {rec[f"decode@{label_n(d)}"]["md5"] for _, _, rec, *_ in self.rounds
                      if f"decode@{label_n(d)}" in rec and rec[f"decode@{label_n(d)}"].get("md5_fresh")} for d, _ in proofs}
            bad = [label_n(d) for d, pm in proofs if fr[d] and {pm["md5"]} != fr[d]]
            p("md5 restore proof: " + ("n/a (no fresh-start round)" if not any(fr.values()) else
                                       f"PASS: first restore + decode on a fresh server == fresh prefill + decode at every "
                                       f"depth (rounds {' '.join(fresh_rounds)})" if not bad else f"FAIL at {','.join(bad)}"))
        gm = sorted({full for _, (_, full) in self.greedy.values()})
        md5_ok &= len(gm) == 1
        p(f"greedy md5 (chat, fresh prefill; content/reasoning+content): "
          f"{', '.join(f'{t}={c}/{f}' for t, (_, (c, f)) in self.greedy.items())} -> {'identical' if len(gm) == 1 else 'DIFFERENT'}")
        if "decodeT1" in self.groups:
            t1 = {d: sorted({rec[f'decodeT1@{label_n(d)}']['md5'] for _, _, rec, *_ in self.rounds if f'decodeT1@{label_n(d)}' in rec})
                  for d in self.depths}
            p("md5 T=1 seed 42 (informational): " + "  ".join(f"{label_n(d)} {'same' if len(v) == 1 else 'diff'}" for d, v in t1.items()))
        # verdict
        tgt = {"any": [g for g in ("decode", "prefill") if g in self.groups], "none": []}.get(self.a.target, [self.a.target])
        reasons, best = [], None
        for g in self.groups:
            d = self.decisions[g][0]
            if d in ("LOSS", "MIXED"):
                reasons.append(f"{g} {d}")
        for g in tgt:
            if self.decisions[g][0] == "WIN":
                gains = []
                for m in self.groups[g]:
                    if g in self.details:
                        dd, spread = self.details[g][m]
                        if dd > 2 * spread:
                            gains.append((dd, m))
                    else:
                        gains.append((self.values("B1", m)["value"] / self.a_ref[m]["value"] - 1, m))
                if gains:
                    gbest = max(gains) if self.a.pass_mode == "max" else (statistics.mean(x for x, _ in gains), g)
                    best = max(best, gbest) if best else gbest
        if not md5_ok and not self.a.allow_md5_change:
            reasons.append("md5 changed (not lossless)")
        if tgt and (best is None or best[0] * 100 < self.a.pass_):
            reasons.append(f"no significant {'/'.join(tgt)} gain >= +{self.a.pass_}%"
                           + (f" (best {100 * best[0]:+.2f}% {best[1]})" if best else ""))
        verdict = "PASS" if not reasons else "KILL"
        mtxt = "md5 n/a (same-server: needs a fresh-start md5 arm)" if md5_na else "md5 ok"
        p(f"VERDICT: {verdict}" + (f" ({best[1]} {100 * best[0]:+.2f}% >= +{self.a.pass_}%, {mtxt})" if verdict == "PASS" and tgt
                                   else f" (regression gate: no LOSS/MIXED, {mtxt})" if verdict == "PASS"
                                   else f" ({'; '.join(reasons)})"))
        if self.a.aa:  # A/A run: any WIN/LOSS/MIXED or md5 change is a false positive of the harness
            fp = [g for g, (d, _) in self.decisions.items() if d in ("WIN", "LOSS", "MIXED")]
            p(f"A/A: {'OK (no false WIN/LOSS, md5 identical)' if not fp and md5_ok else 'FALSE POSITIVE: ' + ', '.join(fp + ([] if md5_ok else ['md5']))}")
        # runs + minutes
        cats = {}
        for s in self.run.stages:
            cats[s["cat"]] = cats.get(s["cat"], 0) + s["s"]
        starts = len(self.servers)
        p("")
        p(f"runs: {n_req['A']} A + {n_req['B']} B measurements, rounds {' '.join(rids)}, {starts} server start(s)")
        p(f"minutes: variant {cats.get('variant', 0) / 60:.1f} · session {cats.get('session', 0) / 60:.1f} (server A, noise"
          f" pair, :8080) · once per engine {cats.get('once', 0) / 60:.1f} (snapshots, proof) · wall {wall / 60:.1f}")
        old = self.old_estimate()
        if old:
            p(f"old method (lc.py-style A B B A with restarts, same metrics): ~{old / 60:.1f} min per variant")
        p("")
        p("stage timings:")
        for s in self.run.stages:
            p(f"  {s['s']:>8.1f} s  {s['cat']:<8} {s['stage']}{'' if s['ok'] else '  FAILED'}")
        text = "\n".join(L)
        print("\n" + text, flush=True)
        with open(os.path.join(self.run.dir, "summary.txt"), "w") as f:
            f.write(text + "\n")
        save_json(os.path.join(self.run.dir, "result.json"), {
            "mode": self.mode, "label": self.a.label, "verdict": verdict, "reasons": reasons, "key": self.key,
            "decisions": self.decisions, "noise": self.noise, "md5_ok": md5_ok, "md5_na": md5_na, "stages": self.run.stages,
            "minutes": {k: round(v / 60, 2) for k, v in cats.items()}, "rounds": [r for r, *_ in self.rounds],
            "old_min": round(old / 60, 1) if old else None})

    def old_estimate(self):
        """4 arms x (server start + one cold request per depth + one prefill request per size + greedy md5)"""
        try:
            start = statistics.mean(s.start_s for s in self.servers if s.start_s)
            cold = 0.0
            for d in self.depths:
                e = self.snaps["A"][1]["depths"][str(d)]
                if e.get("proof_cold"):
                    cold += e["proof_cold"]["wall_s"]
                else:
                    cold += e["prefill_s"] + self.values("A0", f"decode@{label_n(d)}")["wall_s"]
            pre = sum(self.values("A0", m)["wall_s"] for m in self.groups["prefill"])
            return 4 * (start + cold + pre + 5)
        except Exception:  # noqa: BLE001 - informational
            return None


# ------------------------------------------------------------------------------------------------------------ helpers
def under_queue():
    pid = os.getpid()
    for _ in range(12):
        try:
            if "queue/run-jobs.sh" in open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="replace"):
                return True
            pid = int(open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return False
        if pid <= 1:
            return False
    return False


def eco_status():
    for cmd in ([ECO, "status"], ["sudo", "-n", ECO, "status"]):
        with contextlib.suppress(OSError):
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if "sclk cap (state): 2200" in r.stdout:
                return r.stdout
    return r.stdout + r.stderr if "r" in locals() else "xtx-eco not found"


# ------------------------------------------------------------------------------------------------------------ t0
def run_t0(a):
    run = Run("t0", a.label)
    log = run.log
    arms = [Arm("A", a.base, kv_list(a.base_env) | kv_list(a.base_switch), [], {}),
            Arm("B", a.var or a.base, kv_list(a.var_env) | kv_list(a.var_switch), [], {})]
    for arm in arms:
        e, s, notes = check_engine(arm.root, need=("test-backend-ops",))
        if e or (s and not a.allow_stale):
            for x in e + s:
                log(f"REFUSED: {x}")
            sys.exit(2)
    if not TEST and not under_queue():
        log("REFUSED: GPU mode outside ~/qwen-opt/queue/run-jobs.sh")
        sys.exit(2)

    def tbo(arm, *extra):
        env = dict(os.environ, GGML_HIP_PM4="0", LD_LIBRARY_PATH=f"{arm.root}/bin:{ROCM_LIB}", **arm.env)
        cmd = ["taskset", "-c", "2-5", f"{arm.root}/bin/test-backend-ops", *extra, "-o", a.op, "-b", "ROCm0"]
        cmd += ["-p", a.params] if a.params else []
        return subprocess.run(cmd, env=env, capture_output=True, text=True).stdout

    res = {"label": a.label, "op": a.op, "params": a.params, "time": time.time(), "arms": {}}
    fails = {}
    for arm in arms:
        with run.stage(f"t0 check {arm.name}", "variant"):
            out = tbo(arm)
            open(os.path.join(run.dir, f"tbo-{arm.name}.txt"), "w").write(out)
            fails[arm.name] = sorted(set(re.findall(r"^\s*(\S+\(.*\)): FAIL", out, re.M)))
            passed = (re.findall(r"(\d+/\d+) tests passed", out) or ["?"])[-1]
            res["arms"][arm.name] = {"passed": passed, "fails": len(fails[arm.name])}
            log(f"t0 {arm.name}: {a.op} {passed} tests passed, {len(fails[arm.name])} FAIL")
    new = sorted(set(fails["B"]) - set(fails["A"]))
    res["correct"] = not new
    log(f"t0 correctness: {'PASS' if not new else 'FAIL: ' + ', '.join(new[:5])}")
    res["gain_pct"] = res["best_pct"] = 0.0
    res["kernel_gain"] = False
    if a.perf:
        us = {}
        for i, arm in enumerate([arms[0], arms[1], arms[1], arms[0]]):
            with run.stage(f"t0 perf {arm.name}{i}", "variant"):
                out = tbo(arm, "perf")
                for case, v in re.findall(r"^\s*(\S+\(.*\)):\s+\d+ runs -\s+([\d.]+) us/run", out, re.M):
                    us.setdefault(case, {}).setdefault(arm.name, []).append(float(v))
        sp = {c: statistics.mean(v["A"]) / statistics.mean(v["B"]) - 1 for c, v in us.items() if "A" in v and "B" in v}
        if sp:
            res["gain_pct"] = round(100 * statistics.median(sp.values()), 2)
            res["best_pct"] = round(100 * max(sp.values()), 2)
            res["kernel_gain"] = res["gain_pct"] >= 1.0 or res["best_pct"] >= 2.0
            res["cases"] = {c: round(100 * v, 2) for c, v in sp.items()}
            for c, v in sorted(sp.items(), key=lambda x: -x[1])[:20]:
                log(f"  {100 * v:+6.2f}%  {c[:150]}")
        log(f"t0 perf A B B A: {len(sp)} cases, median speed-up {res['gain_pct']:+.2f}%, best {res['best_pct']:+.2f}% -> "
            f"{'kernel gain' if res['kernel_gain'] else 'no kernel gain'} (gain: median >= 1% or best case >= 2%)")
    save_json(os.path.join(CACHE, f"t0-{a.label}.json"), res)
    save_json(os.path.join(run.dir, "result.json"), res)
    return 0 if res["correct"] else 1


# ------------------------------------------------------------------------------------------------------------ CPU modes
def run_check(a):
    ok = True
    for name, root, src in (("base", a.base, a.base_src), ("var", a.var or a.base, a.var_src)):
        root = norm_root(root)
        e, s, notes = check_engine(root, need=("llama-server",), src=src)
        for x in notes:
            print(f"{name}: {x}")
        for x in e:
            print(f"{name}: ERROR {x}")
        for x in s:
            print(f"{name}: WARNING stale {x}")
        print(f"{name}: hook {HOOK_ENV}: {'yes' if has_hook(root) else 'no'}")
        ok &= not e and (not s or a.allow_stale)
    base = Arm("A", a.base, kv_list(a.base_env), [], kv_list(a.base_switch))
    var = Arm("B", a.var or a.base, kv_list(a.var_env), [x for x in (a.var_args or "").split(",") if x], kv_list(a.var_switch))
    same = base.server_sig() == var.server_sig() and not a.force_restart
    print(f"plan: {'one server, ' + ('runtime switch file' if base.switches or var.switches else 'no switch') if same else 'restart per arm'}"
          f"; rounds A0 [A0' noise] B1, if ambiguous B2 A2")
    run_status(a)
    print("check:", "OK" if ok else "REFUSE (fix before submitting)")
    return 0 if ok else 2


def run_status(_a):
    for m in snapshot_sets():
        ds = ", ".join(f"{label_n(int(d))} {e['bytes'] / 2**30:.2f} GiB" + (" ok" if snapshot_ok(m, int(d)) else " MISSING")
                       for d, e in sorted(m.get("depths", {}).items(), key=lambda x: int(x[0])))
        print(f"snapshot set {m['key']}: engine {m.get('comp', {}).get('engine')} created "
              f"{time.strftime('%F %T', time.localtime(m.get('created', 0)))}: {ds}")
    for p in sorted(os.listdir(CACHE)) if os.path.isdir(CACHE) else []:
        if p.startswith("noise-"):
            n = load_json(os.path.join(CACHE, p), {})
            print(f"noise {n.get('key')}: {(time.time() - n.get('measured', 0)) / 3600:.1f} h old: " +
                  "  ".join(f"{k} {100 * v:.2f}%" for k, v in n.get("values", {}).items()))
        if p.startswith("t0-"):
            t = load_json(os.path.join(CACHE, p), {})
            print(f"t0 {t.get('label')}: {t.get('op')} correct={t.get('correct')} gain {t.get('gain_pct')}% "
                  f"best {t.get('best_pct')}% ({time.strftime('%F %T', time.localtime(t.get('time', 0)))})")
    return 0


def run_prep(a):
    model = os.path.join(HOME, "models", "orca", "Qwen3.8-27B-Uncensored-Q4_K_M.gguf")
    t = time.time()
    print(f"model {model}: {sha256_cached(model)[:16]} ({time.time() - t:.0f} s)")
    for root in {norm_root(a.base), norm_root(a.var or a.base)}:
        for f in engine_files(root):
            sha256_cached(f)
        print(f"engine {root}: {len(engine_files(root))} files hashed")
    corpus_text()
    print(f"corpus {CORPUS}: {os.path.getsize(CORPUS)} bytes")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["check", "prep", "status", "t0", "t1", "t2"])
    ap.add_argument("--label", default="ab")
    ap.add_argument("--base", default=PROD)
    ap.add_argument("--var")
    ap.add_argument("--base-src")
    ap.add_argument("--var-src")
    ap.add_argument("--base-env", action="append")
    ap.add_argument("--var-env", action="append")
    ap.add_argument("--var-args", help="comma-separated extra server args for B (restart)")
    ap.add_argument("--base-switch", action="append")
    ap.add_argument("--var-switch", action="append")
    ap.add_argument("--force-restart", action="store_true", help="B on its own server even with an identical config")
    ap.add_argument("--depths", default="1700,94000,199000")
    ap.add_argument("--prefill", default="4096,32768")
    ap.add_argument("--long-prefill", type=int, default=131072, help="t2")
    ap.add_argument("--fill", type=int, default=255000, help="t2: prompt tokens of the fill test")
    ap.add_argument("--tokens", type=int, default=256)
    ap.add_argument("--port", type=int, default=18794)
    ap.add_argument("--target", choices=["decode", "prefill", "any", "none"], default="decode",
                    help="group that must gain; none = regression gate only (host-side features)")
    ap.add_argument("--pass", dest="pass_", type=float, default=1.0, help="PASS threshold, %% gain")
    ap.add_argument("--pass-mode", choices=["max", "mean"], default="max")
    ap.add_argument("--max-loss", type=float, default=0.5, help="%% loss tolerated after A B B A")
    ap.add_argument("--win-floor", type=float, default=0.5, help="%% floor of the immediate WIN/LOSS threshold")
    ap.add_argument("--noise-floor", type=float, default=0.1, help="%% floor of the noise estimate")
    ap.add_argument("--noise-ttl-h", type=float, default=12.0)
    ap.add_argument("--renoise", action="store_true")
    ap.add_argument("--t0", choices=["auto", "gain", "none"], default="auto")
    ap.add_argument("--prove", action="store_true", help="md5 restore proof even when the snapshots exist")
    ap.add_argument("--snap-compat", action="store_true",
                    help="use the newest snapshot set of the same model/flags/env made by another engine binary")
    ap.add_argument("--own-snap", action="store_true",
                    help="B restores snapshots made by its own engine/config (default: A's set, the same start state)")
    ap.add_argument("--aa", action="store_true", help="A/A run: report false positives of the harness")
    ap.add_argument("--allow-stale", action="store_true")
    ap.add_argument("--allow-md5-change", action="store_true")
    ap.add_argument("--op")
    ap.add_argument("--params")
    ap.add_argument("--perf", action="store_true")
    a = ap.parse_args()
    for d in (SLOTS, CACHE, RUNS):
        os.makedirs(d, exist_ok=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    if a.mode == "check":
        return run_check(a)
    if a.mode == "prep":
        return run_prep(a)
    if a.mode == "status":
        return run_status(a)
    if a.mode == "t0":
        if not a.op:
            sys.exit("t0 needs --op")
        return run_t0(a)
    Bench(a, a.mode).go()
    return 0


if __name__ == "__main__":
    sys.exit(main())
