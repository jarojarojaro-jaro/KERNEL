"""Inside one GPU block (both locks held): one fresh llama-server, its requests, telemetry, clean shutdown.

Request body = spec_sweep.py: messages, max_tokens, temperature, seed, cache_prompt false (+ the client-ui variant:
reasoning_control, logit_bias, n_probs, a JSON grammar, as the web UI and agents send them, rule R05).
Per request: n tokens, ms, draft/accepted, sha256 of the text (rule R35: md5 from the timed runs themselves).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from . import paths

# what the web UI / agents add (lekcja-wolna-sciezka-samplera): reasoning_control, logit_bias, n_probs, a grammar
# (a permissive one: it arms the grammar sampler like a tool-call grammar but accepts any text)
CLIENT_UI = {"reasoning_control": True, "logit_bias": {"0": -0.5}, "n_probs": 1,
             "grammar": "root ::= [^\\x00]*"}


def http(port: int, path: str, body=None, timeout=600):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


class Telemetry(threading.Thread):
    """1 Hz junction temperature, VRAM and GTT use (R09, R14)."""

    def __init__(self, dev: Path = paths.DRM_DEVICE):
        super().__init__(daemon=True)
        self.dev, self.stop_ev = dev, threading.Event()
        self.max = {"max_junction_c": None, "max_vram_used": None, "max_gtt_used": None, "max_power_w": None}
        hw = sorted((dev / "hwmon").glob("hwmon*")) if (dev / "hwmon").exists() else []
        self.hw = hw[0] if hw else None

    def _val(self, p, scale=1.0):
        try:
            return int(Path(p).read_text()) / scale
        except (OSError, ValueError):
            return None

    def sample(self):
        vals = {"max_vram_used": self._val(self.dev / "mem_info_vram_used"),
                "max_gtt_used": self._val(self.dev / "mem_info_gtt_used")}
        if self.hw:
            vals["max_junction_c"] = self._val(self.hw / "temp2_input", 1000.0)
            vals["max_power_w"] = self._val(self.hw / "power1_average", 1e6)
        for k, v in vals.items():
            if v is not None and (self.max[k] is None or v > self.max[k]):
                self.max[k] = v

    def run(self):
        while not self.stop_ev.is_set():
            self.sample()
            self.stop_ev.wait(1.0)


class Server:
    def __init__(self, argv, env, port, log_path, deadline):
        self.argv, self.env, self.port, self.log_path, self.deadline = argv, env, port, Path(log_path), deadline
        self.p = None

    def __enter__(self):
        self.log = open(self.log_path, "w")
        self.p = subprocess.Popen(self.argv, env=self.env, stdout=self.log, stderr=subprocess.STDOUT,
                                  start_new_session=True)
        while time.time() < self.deadline:
            if self.p.poll() is not None:
                raise RuntimeError(f"server exited {self.p.returncode}, see {self.log_path}")
            try:
                if http(self.port, "/health", timeout=2).get("status") == "ok":
                    return self
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError("server not healthy before the block deadline")

    def __exit__(self, *exc):
        """SIGTERM, SIGKILL after 15 s (a DFlash server can hang on SIGTERM, rule R08)."""
        if self.p and self.p.poll() is None:
            os.killpg(self.p.pid, signal.SIGTERM)
            try:
                self.p.wait(15)
            except subprocess.TimeoutExpired:
                os.killpg(self.p.pid, signal.SIGKILL)
                self.p.wait()
        self.log.close()

    def tail(self, n=4000) -> str:
        try:
            return self.log_path.read_text(errors="replace")[-n:]
        except OSError:
            return ""


def block_env(spec: dict) -> dict:
    """Clean environment: no GGML_*/LLAMA_*/HIP_* from the caller (T1), then exactly the spec's variables."""
    env = {k: v for k, v in os.environ.items() if not re.match(r"(GGML|LLAMA|HIP|ROCR|HSA|CUDA)_", k)}
    env.update(spec.get("env") or {})
    env["LD_LIBRARY_PATH"] = f"{spec['lib_dir']}:{paths.ROCM_LIB}"
    return env


def chat_body(entry: dict, tokens: int, temp: float, seed: int, cache_prompt: bool, variant: str) -> dict:
    body = {"messages": entry["messages"], "max_tokens": tokens, "temperature": temp, "seed": seed,
            "cache_prompt": cache_prompt}
    if variant == "client-ui":
        body.update(CLIENT_UI)
    return body


def serve_run(spec: dict) -> dict:
    """One measurement run: spec has argv, env, lib_dir, port, log, deadline, prompts [{set, entry}], protocol."""
    proto = spec["protocol"]
    rec = {"request": {k: proto[k] for k in ("tokens", "temps", "seeds", "cache_prompt")}, "prompts": {},
           "text_sha256": {}, "n_tokens": {}}
    tel = Telemetry()
    with Server(spec["argv"], block_env(spec), spec["port"], spec["log"], spec["deadline"]) as srv:
        tel.start()
        rec["pid"] = srv.p.pid
        try:
            rec["build_info"] = http(spec["port"], "/props", timeout=10).get("build_info")
        except Exception as e:
            rec["build_info"] = None
            rec["props_error"] = str(e)
        http(spec["port"], "/v1/chat/completions",
             {"messages": [{"role": "user", "content": proto["warmup"]}], "max_tokens": 16, "temperature": 0})
        for variant in spec.get("variants", ["plain"]):
            # the client-ui variant: sealed prompts, first seed only (keeps a Qwen run inside the 5 min block)
            items = spec["prompts"] if variant == "plain" else [i for i in spec["prompts"] if i["set"] == "sealed"]
            seeds = proto["seeds"] if variant == "plain" else proto["seeds"][:1]
            for item in items:
                e = item["entry"]
                key = f"{item['set']}/{e['id']}" + ("" if variant == "plain" else f"@{variant}")
                runs = []
                for temp in proto["temps"]:
                    for seed in seeds:
                        r = http(spec["port"], "/v1/chat/completions",
                                 chat_body(e, proto["tokens"], temp, seed, proto["cache_prompt"], variant),
                                 timeout=max(5, spec["deadline"] - time.time()))
                        t = r["timings"]
                        msg = r["choices"][0]["message"]
                        text = (msg.get("reasoning_content") or "") + (msg.get("content") or "")
                        rec["text_sha256"][f"{key}/T{temp}/s{seed}"] = hashlib.sha256(text.encode()).hexdigest()
                        runs.append({"n": t["predicted_n"], "ms": t["predicted_ms"], "draft": t.get("draft_n", 0),
                                     "accepted": t.get("draft_n_accepted", 0)})
                n, ms = sum(x["n"] for x in runs), sum(x["ms"] for x in runs)
                dr, ac = sum(x["draft"] for x in runs), sum(x["accepted"] for x in runs)
                steps = n - ac  # each verify step emits its accepted drafts plus one target token
                rec["prompts"][key] = {"set": item["set"], "variant": variant, "class": e.get("class"),
                                       "lang": e.get("lang"), "tps": 1000.0 * n / ms, "ms_step": ms / steps,
                                       "tok_step": n / steps, "ms_token": ms / n, "acc": ac / dr if dr else 0.0,
                                       "n": n, "runs": runs}
                if variant == "plain":
                    rec["n_tokens"][e["id"]] = n
        rec["log_tail"] = srv.tail()
    tel.stop_ev.set()
    rec["telemetry"] = tel.max
    return rec


def neartie_run(spec: dict) -> dict:
    """Greedy tokens with top-2 logprobs of the reference/candidate (fk.neartie)."""
    from .neartie import tokens_from_response
    out = {"tokens": {}}
    with Server(spec["argv"], block_env(spec), spec["port"], spec["log"], spec["deadline"]) as srv:
        out["pid"] = srv.p.pid
        for i, p in enumerate(spec["prompts"]):
            r = http(spec["port"], "/v1/chat/completions",
                     {"messages": [{"role": "user", "content": p}], "max_tokens": spec["tokens"], "temperature": 0,
                      "logprobs": True, "top_logprobs": 2, "chat_template_kwargs": {"enable_thinking": False}},
                     timeout=max(5, spec["deadline"] - time.time()))
            out["tokens"][f"p{i}"] = tokens_from_response(r)
        out["log_tail"] = srv.tail()
    return out


def probe_run(spec: dict) -> dict:
    """Short request with the probe env; reports whether the probe regex shows up in the server log."""
    with Server(spec["argv"], block_env(spec), spec["port"], spec["log"], spec["deadline"]) as srv:
        http(spec["port"], "/v1/chat/completions",
             {"messages": [{"role": "user", "content": "Count from 1 to 20."}], "max_tokens": 64, "temperature": 0})
        time.sleep(1)
        tail = srv.tail(200000)
    return {"hit": bool(re.search(spec["regex"], tail)), "log_tail": tail[-2000:]}
