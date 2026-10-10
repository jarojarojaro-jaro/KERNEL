#!/usr/bin/env python3
"""End-to-end decode benchmark against a freshly started llama-server.

Starts the server with the given args, warms up, runs fixed prompts through the
chat endpoint (temperature 0, fixed max_tokens) and reports server-side timings:
decode t/s (predicted_per_second), prefill t/s and MTP draft acceptance.
Results are appended as one JSON line to results.jsonl.

Usage:
  serve_bench.py --label hip-master-mtp3 --bin ~/llama-master/build-hip/bin/llama-server \
      -- -m MODEL -ngl 999 -fa on -c 32768 --spec-type draft-mtp ...
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROCM_LIB = "/opt/rocm/core-10.0/lib"

PROMPTS = {
    "code": "Write a Python function that implements an LRU cache class with get and put, "
            "with type hints and docstrings. Only code.",
    "prose": "Explain in three paragraphs why the sky appears blue during the day "
             "and red at sunset.",
    "reason": "A train leaves city A at 9:00 at 80 km/h, another leaves city B, 300 km away, "
              "at 10:00 at 100 km/h towards A. When and where do they meet? Show the steps.",
}

PROMPTS_PL = {
    "pl_prose": "Wyjaśnij w trzech akapitach, dlaczego niebo jest niebieskie w dzień, a czerwone o zachodzie słońca.",
    "pl_code": "Napisz w Pythonie klasę LRU cache z metodami get i put, z adnotacjami typów i docstringami po polsku.",
    "pl_reason": "Pociąg wyjeżdża z miasta A o 9:00 z prędkością 80 km/h, drugi wyjeżdża z miasta B, oddalonego o 300 km, "
                 "o 10:00 z prędkością 100 km/h w stronę A. Kiedy i gdzie się spotkają? Pokaż obliczenia.",
}

def post(port: int, path: str, body: dict, timeout: float = 900) -> dict:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_ready(port: int, proc: subprocess.Popen, timeout: float = 600) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited with code {proc.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
                if r.status == 200:
                    return
        except Exception:  # noqa: BLE001 - not up yet
            pass
        time.sleep(1)
    raise TimeoutError("server did not become ready")


def chat(port: int, prompt: str, max_tokens: int, thinking: bool) -> dict:
    body = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "chat_template_kwargs": {"enable_thinking": thinking},
        "cache_prompt": False,
    }
    r = post(port, "/v1/chat/completions", body)
    return r["timings"] | {"finish": r["choices"][0]["finish_reason"]}


def vram_used_mb() -> float | None:
    try:
        out = subprocess.run(["rocm-smi", "--showmeminfo", "vram", "--json"],
                             capture_output=True, text=True, timeout=20).stdout
        d = json.loads(out)
        card = next(iter(d.values()))
        return int(card["VRAM Total Used Memory (B)"]) / 2**20
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--bin", required=True)
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--tokens", type=int, default=256)
    ap.add_argument("--thinking", action="store_true")
    ap.add_argument("--lang", choices=["en", "pl", "all"], default="en", help="prompt set")
    ap.add_argument("--env", action="append", default=[], help="KEY=VALUE for the server")
    ap.add_argument("--out", default=str(HERE / "results.jsonl"))
    ap.add_argument("server_args", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    sargs = [x for x in a.server_args if x != "--"]
    prompts = {"en": PROMPTS, "pl": PROMPTS_PL, "all": PROMPTS | PROMPTS_PL}[a.lang]

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ROCM_LIB + ":" + env.get("LD_LIBRARY_PATH", "")
    for kv in a.env:
        k, v = kv.split("=", 1)
        env[k] = v
    log = open(HERE / "logs" / f"{a.label}.log", "w")
    cmd = [os.path.expanduser(a.bin), "--port", str(a.port), "--host", "127.0.0.1",
           "-np", "1", "--no-webui", *sargs]
    proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        wait_ready(a.port, proc)
        vram = vram_used_mb()
        for _ in range(2):
            for p in prompts.values():
                chat(a.port, p, 64, a.thinking)
        per: dict[str, list[dict]] = {}
        for name, p in prompts.items():
            per[name] = [chat(a.port, p, a.tokens, a.thinking) for _ in range(a.runs)]
    finally:
        proc.terminate()
        try:
            proc.wait(30)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()

    def med(key: str, rows: list[dict]) -> float | None:
        vals = [r[key] for r in rows if r.get(key) is not None]
        return round(statistics.median(vals), 2) if vals else None

    allrows = [r for rows in per.values() for r in rows]
    drafted = sum(r.get("draft_n", 0) or 0 for r in allrows)
    accepted = sum(r.get("draft_n_accepted", 0) or 0 for r in allrows)
    res = {
        "label": a.label,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "bin": a.bin,
        "args": sargs,
        "env": a.env,
        "decode_tps": med("predicted_per_second", allrows),
        "per_prompt_decode": {k: med("predicted_per_second", v) for k, v in per.items()},
        "prefill_tps": med("prompt_per_second", allrows),
        "draft_acceptance": round(accepted / drafted, 3) if drafted else None,
        "vram_mb": round(vram) if vram else None,
    }
    print(json.dumps(res))
    with open(a.out, "a") as f:
        f.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    sys.exit(main())
