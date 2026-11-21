#!/usr/bin/env python3
"""Same prompts against any OpenAI-compatible server (Enigma Turbo or llama-server): T=0 tasks of test_serve --bench,
T=0.7 creative, long prompts 2k/8k. Prints decode t/s (timings.predicted_per_second) and prefill t/s."""
import json, os, sys, time, urllib.request
sys.path.insert(0, sys.argv[2])
import test_serve as ts
base = f"http://127.0.0.1:{sys.argv[1]}"
tag = sys.argv[3]

def chat(content, max_tokens, temp=0.0, seed=None):
    body = {"messages": [{"role": "user", "content": content}], "temperature": temp, "max_tokens": max_tokens,
            "stream": False, "cache_prompt": False, "enable_thinking": False, "chat_template_kwargs": {"enable_thinking": False}}
    if seed is not None: body["seed"] = seed
    body.update(json.loads(os.environ.get("XB_EXTRA", "{}")))
    req = urllib.request.Request(f"{base}/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r: d = json.loads(r.read().decode())
    return d.get("timings", {}), time.time() - t0, d["choices"][0]["message"]["content"]

tasks = [("Q1", "What is the capital of France? Answer in one sentence.", 24),
         ("Q2", "What is 2 + 2? Answer in one short sentence.", 24),
         ("Q3", "Name three primary colors in one short sentence.", 24),
         ("Q4", ts.COPY_TASK_1, 160), ("Q5", ts.COPY_TASK_2, 160)]
for name, q, mt in tasks:
    best = []
    for _ in range(2):
        t, wall, _ = chat(q, mt)
        best.append(t.get("predicted_per_second", 0.0))
    print(f"{tag} {name} T=0 decode {max(best):.1f} t/s (n={t.get('predicted_n')})", flush=True)
t, wall, txt = chat("Write a short story (about 150 words) about a lighthouse keeper.", 200, 0.7, 42)
print(f"{tag} Q6 T=0.7 decode {t.get('predicted_per_second', 0):.1f} t/s (n={t.get('predicted_n')})", flush=True)
for n in (2048, 8192):
    p = ts.calibrate_long_prompt(base, n)
    t, wall, _ = chat(p, 64)
    print(f"{tag} L{n} prompt_n {t.get('prompt_n')} prefill {t.get('prompt_per_second', 0):.1f} t/s ({t.get('prompt_ms', 0)/1000:.2f} s) decode {t.get('predicted_per_second', 0):.1f} t/s", flush=True)
