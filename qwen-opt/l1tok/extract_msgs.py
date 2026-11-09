#!/usr/bin/env python3
"""Recorded Qwen3.8 assistant turns from omp sessions -> msgs.jsonl (reasoning, content, tool calls) for the
L1 parser diff test (test-chat-stream-inc). Only messages whose model is the local Qwen3.8-27B."""
import glob, json, os, sys
out = sys.argv[1] if len(sys.argv) > 1 else "msgs.jsonl"
files = sorted(glob.glob(os.path.expanduser("~/.omp/agent/sessions/-tmp/**/*.jsonl"), recursive=True))
seen, n = set(), 0
with open(out, "w") as fo:
    for f in files:
        for line in open(f, errors="ignore"):
            if '"assistant"' not in line or "Qwen3.8-27B" not in line:
                continue
            o = json.loads(line)
            m = o.get("message") or {}
            if o.get("type") != "message" or m.get("role") != "assistant" or "Qwen3.8-27B" not in str(m.get("model", "")):
                continue
            rs, ct, tcs = [], [], []
            for p in m.get("content", []):
                if p["type"] == "thinking":
                    rs.append(p.get("thinking", ""))
                elif p["type"] == "text":
                    ct.append(p.get("text", ""))
                elif p["type"] == "toolCall":
                    tcs.append({"name": p["name"], "arguments": p.get("arguments", {})})
            rec = {"reasoning": "".join(rs), "content": "".join(ct), "tool_calls": tcs}
            key = json.dumps(rec, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
print(f"{n} messages -> {out}")
