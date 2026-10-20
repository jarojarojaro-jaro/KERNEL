#!/usr/bin/env python3
"""E0 (report 36 §1.3, report 37): fixed PL+EN prose set for decode speed at T=1 on a running llama-server.

8 prose prompts (4 PL, 4 EN) x SEEDS, TOKENS each, thinking off (the output is the prose itself), no prompt cache.
One JSON row per request goes to --out: label, prompt, seed, n, ms, draft, accepted, md5 of the text.
Summaries (t/s = sum tokens / sum time, bootstrap CI over prompts, paired A/B): prose_sum.py.

usage: prose_bench.py --label NAME --port P [--seeds 1,...,8] [--tokens 400] [--out prose.jsonl]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request

PROMPTS = {
    "pl-latarnik": "Napisz opowiadanie (około 800 słów) o starym latarniku, który pewnej sztormowej nocy dostaje sygnał z okrętu, który zatonął 50 lat temu. Opisz dokładnie miejsce, pogodę, jego wspomnienia i zakończ zaskakującym zwrotem akcji.",
    "pl-esej": "Napisz esej (około 700 słów) o tym, jak zmieniło się czytanie książek w epoce telefonów komórkowych. Użyj przykładów z codziennego życia, argumentów za i przeciw oraz osobistego zakończenia.",
    "pl-list": "Napisz długi, ciepły list babci do wnuczki, która właśnie wyjechała na studia do innego miasta. Babcia wspomina własną młodość, daje rady i opowiada, co słychać na wsi.",
    "pl-opis": "Opisz szczegółowo jesienny poranek na targu w małym polskim miasteczku: ludzi, zapachy, rozmowy, stragany i pogodę. Pisz barwną prozą literacką, bez wypunktowań.",
    "en-story": "Write a short story (about 800 words) about a cartographer who discovers that one of her old maps shows a village that does not exist, until she travels there. Use vivid descriptions and dialogue.",
    "en-essay": "Write a reflective essay (about 700 words) on why people keep diaries, drawing on history, psychology and everyday experience. Write in flowing paragraphs, no bullet points.",
    "en-letter": "Write a long letter from a lighthouse keeper in 1910 to his brother in the city, describing the island, the winter storms, the supply boat and his loneliness.",
    "en-travel": "Describe a slow train journey through the mountains in late autumn, in rich literary prose: the passengers, the landscape, the small stations and the changing light.",
}


def chat(port: int, prompt: str, tokens: int, seed: int, think: bool = False) -> dict:
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": tokens, "temperature": 1.0,
            "seed": seed, "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": think}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=600))
    t = d["timings"]
    text = d["choices"][0]["message"].get("content") or ""
    return {"n": t["predicted_n"], "ms": t["predicted_ms"], "draft": t.get("draft_n", 0),
            "accepted": t.get("draft_n_accepted", 0), "md5": hashlib.md5(text.encode()).hexdigest()[:8]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--seeds", default="1,2,3,4,5,6,7,8")
    ap.add_argument("--tokens", type=int, default=400)
    ap.add_argument("--out", default="prose.jsonl")
    ap.add_argument("--think", action="store_true", help="thinking on (server effort, production default low)")
    a = ap.parse_args()
    chat(a.port, "Hi", 16, 0)  # warmup
    n = ms = 0.0
    with open(a.out, "a") as log:
        for seed in map(int, a.seeds.split(",")):
            for name, p in PROMPTS.items():
                r = chat(a.port, p, a.tokens, seed, a.think)
                n += r["n"]; ms += r["ms"]
                log.write(json.dumps({"label": a.label, "time": time.time(), "prompt": name, "seed": seed, **r}) + "\n")
                log.flush()
    print(f"{a.label}: {1000 * n / ms:.2f} t/s over {int(n)} tokens", flush=True)


if __name__ == "__main__":
    main()
