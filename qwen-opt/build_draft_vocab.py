#!/usr/bin/env python3
"""Build a frequency-ranked token list for the reduced MTP draft head (LLAMA_MTP_DRAFT_VOCAB).

Counts tokens of (a) local text corpora (docs, code, Polish notes) and (b) text the model itself
generates for a mixed EN/PL/code/math prompt set (thinking on and off), then ranks tokens by count.
Tokens never seen are appended in id order (BPE merge order ~ frequency), so the file is a full ranking.

usage: build_draft_vocab.py OUT_FILE [--gen-tokens 400]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import subprocess
import time
import urllib.request

HOME = os.path.expanduser("~")
BIN = f"{HOME}/llama-master/build-hip/bin"
MODEL = f"{HOME}/models/Qwen3.8-27B-UD-Q4_K_XL.gguf"
ENV = dict(os.environ, LD_LIBRARY_PATH=f"{BIN}:/opt/rocm/core-10.0/lib")
PORT = 8096

PROMPTS = [
    # English prose / knowledge
    "Explain the causes of the French Revolution in detail.",
    "Write a short story about a lighthouse keeper who finds a message in a bottle.",
    "Compare TCP and UDP and explain when to use each.",
    "Summarize the theory of evolution for a high school student.",
    "What are the health benefits and risks of intermittent fasting?",
    "Write a cover letter for a junior data analyst position.",
    # Polish
    "Opisz historię Krakowa od średniowiecza do dziś.",
    "Napisz opowiadanie o kocie, który podróżuje pociągiem po Polsce.",
    "Wyjaśnij, jak działa kredyt hipoteczny i na co uważać przy jego wyborze.",
    "Jakie są zalety i wady pracy zdalnej? Odpowiedz w punktach.",
    "Napisz e-mail do szefa z prośbą o urlop w sierpniu.",
    "Wytłumacz zasadę działania silnika elektrycznego prostym językiem.",
    "Przetłumacz na polski i wyjaśnij: 'The quick brown fox jumps over the lazy dog'.",
    "Podaj przepis na pierogi ruskie krok po kroku.",
    # code
    "Implement a thread-safe bounded queue in C++ with condition variables.",
    "Write a Python script that downloads a web page and counts word frequencies.",
    "Write a Rust function that parses a CSV line handling quoted fields.",
    "Write a bash script that backs up a directory to a tarball with a date in the name.",
    "Implement quicksort and mergesort in JavaScript and compare them.",
    "Write a SQL query that finds the top 5 customers by total order value per year.",
    "Napisz w Pythonie funkcję, która sprawdza, czy liczba jest pierwsza, z komentarzami po polsku.",
    "Write a CUDA kernel for vector addition and the host code to launch it.",
    # math / reasoning
    "Solve: a train travels 300 km at 80 km/h and returns at 120 km/h. What is the average speed?",
    "Prove that the square root of 2 is irrational.",
    "Ile wynosi suma liczb od 1 do 1000? Pokaż rozumowanie.",
    "A bag has 3 red and 5 blue balls. Two are drawn without replacement. What is P(both red)?",
]

CORPORA = [
    f"{HOME}/llama-master/docs/**/*.md",
    f"{HOME}/llama-master/README.md",
    f"{HOME}/llama-master/tools/server/README.md",
    f"{HOME}/llama-master/common/*.cpp",
    f"{HOME}/llama-master/gguf-py/gguf/*.py",
    "/usr/lib/python3.12/*.py",
    f"{HOME}/autokernel-amd/reports/*.md",
    f"{HOME}/autokernel-amd/research/*.md",
    "/tmp/KERNEL/**/*.md",
    f"{HOME}/qwen-opt/*.md",
]


def tokenize_file(path: str) -> list[int]:
    out = subprocess.run([f"{BIN}/llama-tokenize", "-m", MODEL, "-f", path, "--ids", "--log-disable"],
                         env=ENV, capture_output=True, text=True).stdout.strip().splitlines()
    if not out:
        return []
    return json.loads(out[-1])


def chat(prompt: str, max_tokens: int, thinking: bool) -> str:
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.7,
            "chat_template_kwargs": {"enable_thinking": thinking}}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    return (msg.get("reasoning_content") or "") + "\n" + (msg.get("content") or "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--gen-tokens", type=int, default=400)
    a = ap.parse_args()

    counts: collections.Counter[int] = collections.Counter()
    n_files = 0
    for pattern in CORPORA:
        for path in glob.glob(pattern, recursive=True):
            if os.path.getsize(path) > 2_000_000:
                continue
            counts.update(tokenize_file(path))
            n_files += 1
    print(f"corpora: {n_files} files, {sum(counts.values())} tokens")

    srv = subprocess.Popen([f"{BIN}/llama-server", "-m", MODEL, "-ngl", "999", "-fa", "on", "-c", "16384",
                            "--port", str(PORT), "-np", "1", "--no-webui", "--spec-type", "draft-mtp",
                            "--spec-draft-n-max", "3"],
                           env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(300):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5)
                break
            except Exception:  # noqa: BLE001 - not up yet
                time.sleep(1)
        gen_path = "/tmp/draft_vocab_gen.txt"
        with open(gen_path, "w") as f:
            for i, p in enumerate(PROMPTS):
                for thinking in (False, True):
                    f.write(chat(p, a.gen_tokens, thinking) + "\n")
                print(f"generated {i + 1}/{len(PROMPTS)}", flush=True)
    finally:
        srv.terminate()
        srv.wait(30)
    gen = tokenize_file(gen_path)
    # generated text is what the draft head must predict: weight it above the static corpora
    for t in gen:
        counts[t] += 4
    print(f"generated: {len(gen)} tokens")

    n_vocab = 248320
    ranked = [t for t, _ in counts.most_common() if 0 <= t < n_vocab]
    seen = set(ranked)
    ranked += [t for t in range(n_vocab) if t not in seen]
    with open(a.out, "w") as f:
        f.write("\n".join(map(str, ranked)) + "\n")
    print(f"wrote {len(ranked)} ids, {len(seen)} observed")


if __name__ == "__main__":
    main()
