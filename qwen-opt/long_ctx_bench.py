#!/usr/bin/env python3
"""Real long-context run through llama-server: fill the context with N tokens of real text,
then generate. Reports server-side prefill t/s, decode t/s and draft acceptance per depth.

usage: long_ctx_bench.py --label L --bin SERVER [--depths 8000,32000,100000,190000] [--env K=V ...] -- <server args>
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import time
import urllib.request

HOME = os.path.expanduser("~")
PORT = 8095
SOURCES = [f"{HOME}/llama-master/docs/**/*.md", f"{HOME}/autokernel-amd/reports/*.md",
           f"{HOME}/KERNEL/**/*.md", "/usr/lib/python3.12/*.py"]


def corpus(chars: int) -> str:
    parts: list[str] = []
    n = 0
    for pattern in SOURCES:
        for p in sorted(glob.glob(pattern, recursive=True)):
            try:
                t = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            parts.append(t)
            n += len(t)
            if n >= chars:
                return "".join(parts)[:chars]
    return "".join(parts)[:chars]


def post(body: dict) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--bin", required=True)
    ap.add_argument("--depths", default="8000,32000,100000,190000")
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("server_args", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    env = dict(os.environ)
    for kv in a.env:
        k, v = kv.split("=", 1)
        env[k] = v
    log = open(f"{HOME}/qwen-opt/logs/{a.label}.log", "w")
    srv = subprocess.Popen([a.bin, "--port", str(PORT), "--host", "127.0.0.1", "-np", "1", "--no-webui",
                            *[x for x in a.server_args if x != "--"]], env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(600):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5)
                break
            except Exception:  # noqa: BLE001 - not up yet
                time.sleep(1)
        post({"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 16})  # warmup
        for depth in [int(x) for x in a.depths.split(",")]:
            text = corpus(int(depth * 3.3))  # ~3.3 chars per token for this mix
            q = ("Below is a long collection of documents.\n\n" + text +
                 "\n\nWrite a structured summary of the documents above: the main topics, and for each one "
                 "two or three key points.")
            r = post({"messages": [{"role": "user", "content": q}], "max_tokens": 256, "temperature": 0,
                      "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}})
            t = r["timings"]
            acc = (t["draft_n_accepted"] / t["draft_n"]) if t.get("draft_n") else None
            res = {"label": a.label, "prompt_tokens": t["prompt_n"], "prefill_tps": round(t["prompt_per_second"], 1),
                   "prefill_s": round(t["prompt_ms"] / 1000, 1), "decode_tps": round(t["predicted_per_second"], 2),
                   "gen_tokens": t["predicted_n"], "draft_acceptance": round(acc, 3) if acc else None}
            print(json.dumps(res), flush=True)
            with open(f"{HOME}/qwen-opt/long_ctx.jsonl", "a") as f:
                f.write(json.dumps(res) + "\n")
    finally:
        srv.terminate()
        srv.wait(60)
        log.close()


if __name__ == "__main__":
    main()
