#!/usr/bin/env python3
"""omp sessions run on the local Qwen3.8 -> agent conversations in OpenAI chat format, for the L1 replays
(test-tok-cache on CPU, replay_threads.py on a server). System prompt and tools: the ones omp really sends
(xtxlab/ckpt/omp-capture/s1.json). Output: convs.json = [{"name", "tools", "messages"}]."""
import glob, json, os, sys
CAP = os.path.expanduser("~/qwen-opt/xtxlab/ckpt/omp-capture/s1.json")
cap = json.load(open(CAP))
tools = [{"type": "function", "function": {k: t[k] for k in ("name", "description", "parameters") if k in t}} for t in cap["tools"]]
system = cap["instructions"]
out = sys.argv[1] if len(sys.argv) > 1 else "convs.json"
convs = []
for f in sorted(glob.glob(os.path.expanduser("~/.omp/agent/sessions/-tmp/**/*.jsonl"), recursive=True)):
    msgs, n_qwen = [{"role": "system", "content": system}], 0
    for line in open(f, errors="ignore"):
        if '"message"' not in line:
            continue
        o = json.loads(line)
        if o.get("type") != "message":
            continue
        m = o["message"]
        r = m.get("role")
        text = lambda: "".join(p.get("text", "") for p in m.get("content", []) if isinstance(p, dict) and p.get("type") == "text")
        if r == "user":
            msgs.append({"role": "user", "content": text() if isinstance(m.get("content"), list) else str(m.get("content"))})
        elif r == "assistant":
            n_qwen += "Qwen3.8-27B" in str(m.get("model", ""))
            a = {"role": "assistant", "content": text(),
                 "reasoning_content": "".join(p.get("thinking", "") for p in m["content"] if p["type"] == "thinking")}
            tcs = [{"id": p["id"], "type": "function", "function": {"name": p["name"], "arguments": json.dumps(p.get("arguments", {}), ensure_ascii=False)}}
                   for p in m["content"] if p["type"] == "toolCall"]
            if tcs:
                a["tool_calls"] = tcs
            msgs.append(a)
        elif r == "toolResult":
            msgs.append({"role": "tool", "tool_call_id": m.get("toolCallId", ""), "content": text()})
    if n_qwen >= 20:
        convs.append({"name": os.path.basename(f), "tools": tools, "messages": msgs})
json.dump(convs, open(out, "w"), ensure_ascii=False)
for c in convs:
    n = sum(len(json.dumps(m, ensure_ascii=False)) for m in c["messages"])
    print(f"{c['name']}: {len(c['messages'])} messages, {n/1024:.0f} KiB")
