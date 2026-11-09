#!/usr/bin/env python3
"""CPU self-test of xtxbench (no GPU, no model): a fake llama-server with the slot save/restore/erase, /completion
(token prompts, prefix cache that cannot roll back, like the hybrid GDN state), /tokenize, /apply-template and chat
endpoints, a fake test-backend-ops, and the scenarios below in a temporary XTXBENCH_HOME. Run after editing xtxbench.py:

  python3 selftest.py            -> "selftest: N/N scenarios OK"

Fake engine knobs (env of a fake root's bin/llama-server, or a runtime switch file line): FAKE_GAIN (decode and prefill
speed factor), FAKE_SALT (changes the generated text = not lossless), FAKE_NOISE (relative noise, default 0.0005).
"""
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------------------------------------ fake server
class State:
    slot: list = []
    switch_vals: dict = {}
    switch_mtime = None
    gen = 0


def knob(name, default):
    return float(State.switch_vals.get(name, os.environ.get(name, default)))


def poll_switches():
    path = os.environ.get("GGML_HIP_RUNTIME_SWITCH_FILE")
    if not path or not os.path.exists(path):
        return
    m = os.stat(path).st_mtime_ns
    if m == State.switch_mtime:
        return
    State.switch_mtime = m
    vals = {}
    for ln in open(path):
        if "=" in ln and not ln.startswith("#"):
            k, v = ln.strip().split("=", 1)
            vals[k] = v
    if vals != State.switch_vals:
        State.switch_vals = vals
        State.gen += 1
        desc = "".join(f" {k}={v}" for k, v in sorted(vals.items())) or " (empty)"
        print(f"ggml_cuda_rt_switch: gen {State.gen} from {path}:{desc}", file=sys.stderr, flush=True)


def complete(prompt, n_predict, temp, seed, cache_prompt):
    poll_switches()
    n_past = 0
    if cache_prompt and State.slot:
        lcp = 0
        for a, b in zip(State.slot, prompt):
            if a != b:
                break
            lcp += 1
        if lcp == len(State.slot) and lcp < len(prompt):  # extends the cached state: no rollback needed
            n_past = lcp
        # else: the recurrent state cannot roll back -> full re-processing
    prompt_n = len(prompt) - n_past
    gain, noise = knob("FAKE_GAIN", 1.0), knob("FAKE_NOISE", 0.0005)
    jit = lambda: 1 + random.gauss(0, noise)  # noqa: E731
    pp = 700.0 * gain * jit()
    tg = (125.0 - len(prompt) / 6000.0) * gain * jit()
    text = hashlib.sha256(json.dumps([prompt[-64:], len(prompt), temp, seed if temp > 0 else 0,
                                      State.switch_vals.get("FAKE_SALT", os.environ.get("FAKE_SALT", ""))]).encode()).hexdigest()
    State.slot = list(prompt) + [1] * max(0, n_predict - 1)
    time.sleep(0.002)
    return {"content": text, "timings": {"prompt_n": prompt_n, "cache_n": n_past, "prompt_ms": 1000 * prompt_n / pp,
                                         "prompt_per_second": pp, "predicted_n": n_predict,
                                         "predicted_ms": 1000 * n_predict / tg, "predicted_per_second": tg,
                                         "draft_n": n_predict, "draft_n_accepted": n_predict // 2}}


def make_handler(slot_dir):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, obj, code=200):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path == "/health":
                return self.reply({"status": "ok"})
            self.reply({"error": "not found"}, 404)

        def do_POST(self):
            u = urlparse(self.path)
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if u.path == "/tokenize":
                return self.reply({"tokens": [ord(c) % 50000 for c in body["content"]]})
            if u.path == "/apply-template":
                c = body["messages"][0]["content"]
                return self.reply({"prompt": f"<|im_start|>user\n{c}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"})
            if u.path == "/completion":
                return self.reply(complete(body["prompt"], body["n_predict"], body["temperature"], body["seed"],
                                           body.get("cache_prompt", True)))
            if u.path == "/v1/chat/completions":
                toks = [ord(c) for c in body["messages"][0]["content"]]
                r = complete(toks, body.get("max_tokens", 16), body.get("temperature", 1.0), body.get("seed", 0), False)
                return self.reply({"choices": [{"message": {"content": r["content"]}}], "timings": r["timings"]})
            if u.path.startswith("/slots/"):
                action = parse_qs(u.query)["action"][0]
                f = os.path.join(slot_dir, body.get("filename", ""))
                if action == "save":
                    json.dump(State.slot, open(f, "w"))
                    return self.reply({"n_saved": len(State.slot), "n_written": os.path.getsize(f), "timings": {"save_ms": 1.0}})
                if action == "restore":
                    State.slot = json.load(open(f))
                    return self.reply({"n_restored": len(State.slot), "n_read": os.path.getsize(f), "timings": {"restore_ms": 1.0}})
                if action == "erase":
                    n, State.slot = len(State.slot), []
                    return self.reply({"n_erased": n})
            self.reply({"error": "not found"}, 404)

    return H


def serve(argv):
    port = int(argv[argv.index("--port") + 1])
    slot_dir = argv[argv.index("--slot-save-path") + 1]
    random.seed(os.getpid())
    print("fake llama-server listening", file=sys.stderr, flush=True)
    HTTPServer(("127.0.0.1", port), make_handler(slot_dir)).serve_forever()


# ------------------------------------------------------------------------------------------------ scenarios
def fake_root(base, name, env=""):
    root = os.path.join(base, name)
    os.makedirs(os.path.join(root, "bin"), exist_ok=True)
    srv = os.path.join(root, "bin", "llama-server")
    with open(srv, "w") as f:
        f.write(f"#!/bin/bash\nGGML_FAKE_ROOT={name} {env} exec {sys.executable} {os.path.abspath(__file__)} serve \"$@\"\n")
    tbo = os.path.join(root, "bin", "test-backend-ops")
    us = 100.0 / float(env.split("FAKE_GAIN=")[1].split()[0]) if "FAKE_GAIN=" in env else 100.0
    with open(tbo, "w") as f:
        f.write("#!/bin/bash\nif [ \"$1\" = perf ]; then\n"
                f"  echo '  OP(case=1):     100 runs -   {us:.2f} us/run - 1 GFLOP/run'\n"
                f"  echo '  OP(case=2):     100 runs -   {2 * us:.2f} us/run - 1 GFLOP/run'\nelse\n"
                "  echo '  OP(case=1): OK'; echo '  2/2 tests passed'\nfi\n")
    for p in (srv, tbo):
        os.chmod(p, 0o755)
    return root


def main():
    if sys.argv[1:2] == ["serve"]:
        return serve(sys.argv[2:])
    tmp = tempfile.mkdtemp(prefix="xtxbench-selftest-")
    model = os.path.join(tmp, "model.gguf")
    open(model, "w").write("fake model")
    env = dict(os.environ, XTXBENCH_TEST="1", XTXBENCH_HOME=os.path.join(tmp, "home"),
               XTXBENCH_TEST_SERVER=f"{{root}}/bin/llama-server -m {model} --port {{port}} --slot-save-path {{slots}} --log-file {{log}}")
    os.makedirs(os.path.join(tmp, "home"))
    shutil.copy(os.path.join(HERE, "corpus.txt"), os.path.join(tmp, "home", "corpus.txt")) if os.path.exists(
        os.path.join(HERE, "corpus.txt")) else None
    a = fake_root(tmp, "A")
    b_fast = fake_root(tmp, "Bfast", "FAKE_GAIN=1.03")
    b_salt = fake_root(tmp, "Bsalt", "FAKE_SALT=x")
    common = ["--depths", "1700,9400,19900", "--prefill", "4096,8192", "--port", "18999", "--base", a]
    xb = [sys.executable, os.path.join(HERE, "xtxbench.py")]

    def run(name, args, check):
        r = subprocess.run(xb + args + common, env=env, capture_output=True, text=True, timeout=600)
        res = None
        rdir = os.path.join(tmp, "home", "runs")
        mine = sorted(d for d in os.listdir(rdir) if d.endswith(f"-{args[0]}-{args[args.index('--label') + 1]}"))
        if mine and os.path.exists(os.path.join(rdir, mine[-1], "result.json")):
            res = json.load(open(os.path.join(rdir, mine[-1], "result.json")))
        ok = r.returncode == 0 and res is not None and check(res, r.stdout)
        print(f"{'OK  ' if ok else 'FAIL'} {name}: rc={r.returncode} verdict={res and res.get('verdict')} "
              f"rounds={res and res.get('rounds')} decisions={res and {g: d[0] for g, d in res.get('decisions', {}).items()}}")
        if not ok:
            print(r.stdout[-3000:], r.stderr[-3000:])
        return ok

    results = [
        run("A/A restart, first run: snapshots + proof + noise pair", ["t1", "--label", "aa", "--force-restart", "--aa"],
            lambda r, out: r["verdict"] == "KILL" and "A/A: OK" in out and "A0'" in r["rounds"] and r["md5_ok"]
            and "proof: fresh prefill+decode" in out and "snapshot create" in out),
        run("A/A again: snapshots + noise reused", ["t1", "--label", "aa2", "--force-restart", "--aa"],
            lambda r, out: "A0'" not in r["rounds"] and "snapshot create" not in out and "A/A: OK" in out),
        run("restart variant +3%: WIN at once", ["t1", "--label", "fast", "--var", b_fast],
            lambda r, out: r["verdict"] == "PASS" and r["rounds"] == ["A0", "B1"] and r["decisions"]["decode"][0] == "WIN"),
        run("switch variant +0.3%: ambiguous -> A B B A", ["t1", "--label", "sw", "--var-switch", "FAKE_GAIN=1.003",
                                                         "--renoise"],
            lambda r, out: "B2" in r["rounds"] and "A2" in r["rounds"] and "switches -> arm B" in out),
        run("salted variant: md5 change -> KILL", ["t1", "--label", "salt", "--var", b_salt],
            lambda r, out: r["verdict"] == "KILL" and not r["md5_ok"]),
        run("t0 perf A B B A", ["t0", "--label", "fast", "--op", "OP", "--perf", "--var", b_fast],
            lambda r, out: r["correct"] and r["kernel_gain"] and abs(r["gain_pct"] - 3.0) < 0.1),
        run("t2 (+T=1, sweep, long) with own snapshots", ["t2", "--label", "t2", "--var", b_fast, "--own-snap",
                                                          "--long-prefill", "12288", "--fill", "20000"],
            lambda r, out: "sweep" in r["decisions"] and "long" in r["decisions"] and "snapshot create B" in out),
    ]
    print(f"selftest: {sum(results)}/{len(results)} scenarios OK ({tmp})")
    if all(results):
        shutil.rmtree(tmp)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
