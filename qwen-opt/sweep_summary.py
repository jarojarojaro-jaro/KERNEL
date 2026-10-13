#!/usr/bin/env python3
"""Summarize the last N spec_sweep.jsonl rows: mean and median t/s, ms/step, chat/prose t/s.

usage: sweep_summary.py [N=30]
"""
import json
import sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
rows = [json.loads(line) for line in open("spec_sweep.jsonl")][-n:]
for r in rows:
    p = r["prompts"]
    mean = sum(v["tps"] for v in p.values()) / len(p)
    chat = p.get("en-chat", {}).get("tps", 0)
    prose = p.get("pl-proza", {}).get("tps", 0)
    print(f"{r['label'][:60]:60s} mean {mean:6.1f} med {r['median_tps']:6.1f} "
          f"ms {r.get('median_ms_step', 0):5.2f} chat {chat:5.1f} proza {prose:5.1f}")
