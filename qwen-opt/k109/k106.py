#!/usr/bin/env python3
"""K-106: prefill-decode interference on the production config (-np 1) on test port 18794. A = 1.7k prompt, 512 tok
T=0 streamed; B = 32k prompt, 16 tok, sent 1.5 s after A starts. Arms: together (A then B overlapped) and sequential
(A alone, B alone). Reports A's token gaps (max/p99), A/B wall, B TTFT, md5 of A and B text in both arms."""
import hashlib, json, statistics as st, threading, time, urllib.request
import bench
URL = "http://127.0.0.1:18794/v1/chat/completions"
docA, _ = bench.document(2575, seed=11)      # ~1.7k tokens (calib 0.66 tok per unit)
docB, _ = bench.document(48500, seed=12)     # ~32k tokens

def stream(prompt, n, out, t_start):
    body = {"messages": [{"role": "user", "content": prompt + "\n\nSummarise the text above."}], "max_tokens": n,
            "temperature": 0, "stream": True, "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); ts, text, timings = [], [], {}
    with urllib.request.urlopen(req, timeout=1200) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                continue
            ev = json.loads(line[5:])
            timings = ev.get("timings") or timings
            for ch in ev.get("choices") or []:
                piece = (ch.get("delta") or {}).get("content") or ""
                if piece:
                    ts.append(time.monotonic()); text.append(piece)
    out.update(t0=t0 - t_start, end=time.monotonic() - t_start, ttft=(ts[0] - t0) if ts else None,
               gaps=[b - a for a, b in zip(ts, ts[1:])], md5=hashlib.md5("".join(text).encode()).hexdigest()[:8],
               prompt_n=timings.get("prompt_n"), n=timings.get("predicted_n"))

def show(tag, r):
    g = sorted(r["gaps"]) or [0]
    print(f"{tag}: start {r['t0']:.2f}s end {r['end']:.2f}s ttft {r['ttft']:.2f}s prompt {r['prompt_n']} n {r['n']} "
          f"gap max {max(g)*1000:.0f} ms p99 {g[int(.99*(len(g)-1))]*1000:.0f} ms md5 {r['md5']}", flush=True)

stream("warm", 8, {}, time.monotonic())
for rep in (1, 2):
    t = time.monotonic(); a, b = {}, {}
    ta = threading.Thread(target=stream, args=(docA, 512, a, t)); ta.start(); time.sleep(1.5)
    stream(docB, 16, b, t); ta.join()
    show(f"together{rep} A", a); show(f"together{rep} B", b)
    t = time.monotonic(); a2 = {}; stream(docA, 512, a2, t); show(f"alone{rep} A", a2)
    t = time.monotonic(); b2 = {}; stream(docB, 16, b2, t); show(f"alone{rep} B", b2)
    print(f"rep{rep}: wall together {max(a['end'], b['end']):.2f}s vs sequential {a2['end'] + b2['end']:.2f}s; "
          f"A md5 {'same' if a['md5'] == a2['md5'] else 'DIFF'}, B md5 {'same' if b['md5'] == b2['md5'] else 'DIFF'}", flush=True)
