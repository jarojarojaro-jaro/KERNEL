#!/usr/bin/env python3
"""Astra-Stop A/B driver for a running llama-server (topka or upstream), plus a </think>-leak scan.

  pelican_ab.py run  --port P --label L --out F.jsonl [--seeds 1-16] [--effort xhigh|medium|low]
                     [--lora-scale S] [--prompt TEXT|@file.txt] [--max 60000] [--temp 1.0]
  pelican_ab.py scan F.jsonl [G.jsonl ...]     # works on tasks.py outputs too (field "content")

--lora-scale S sends the per-request field lora=[{"id":0,"scale":S}] (server started with
--lora astra-stop-lora-unc.gguf --lora-init-without-apply), so both arms run on ONE server; switching the adapter
clears the slot cache (server-context.cpp:1978-1981), so run arms in blocks (ABBA), never interleaved per request.
Sampler: Qwen thinking defaults T 1.0 / top-p 0.95 / top-k 20 (same as the 5090 replay, PREREG.md).
Thinking/answer tokens are re-tokenised through the server's /tokenize (same tokenizer for both arms).
"""
import argparse, json, re, statistics, sys, time, urllib.request
import xml.etree.ElementTree as ET

PELICAN = "Generate an SVG of a pelican riding a bicycle"


def post(port, path, body, timeout=7200):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ntok(port, text):
    return len(post(port, "/tokenize", {"content": text})["tokens"]) if text else 0


def svg_ok(text):
    m = re.findall(r"<svg[\s\S]*?</svg>", text)
    if not m:
        return False
    try:
        ET.fromstring(m[-1])
        return True
    except ET.ParseError:
        return False


def seeds(spec):
    a, _, b = spec.partition("-")
    return list(range(int(a), int(b or a) + 1))


def run(a):
    prompt = open(a.prompt[1:]).read() if a.prompt.startswith("@") else a.prompt
    with open(a.out, "a") as f:
        for s in seeds(a.seeds):
            body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": a.max, "seed": s,
                    "temperature": a.temp, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
                    "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": a.effort}}
            if a.lora_scale is not None:
                body["lora"] = [{"id": 0, "scale": a.lora_scale}]
            t0 = time.time()
            r = post(a.port, "/v1/chat/completions", body)
            dt = time.time() - t0
            ch = r["choices"][0]; m = ch["message"]
            rc, ct = m.get("reasoning_content") or "", m.get("content") or ""
            rec = {"label": a.label, "seed": s, "effort": a.effort, "lora_scale": a.lora_scale,
                   "finish": ch.get("finish_reason"), "wall_s": round(dt, 2),
                   "n_think": ntok(a.port, rc), "n_answer": ntok(a.port, ct),
                   "leak_think_close": ct.count("</think>") + ct.count("<think>"),
                   "svg_ok": svg_ok(ct), "timings": r.get("timings"), "content": ct, "reasoning": rc}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            print(a.label, s, rec["finish"], rec["n_think"], rec["n_answer"], rec["leak_think_close"], rec["svg_ok"],
                  f"{dt:.0f}s", flush=True)


def scan(paths):
    by = {}
    for p in paths:
        for line in open(p):
            r = json.loads(line)
            by.setdefault(r.get("label", p), []).append(r)
    for lab, rs in by.items():
        th = [r["n_think"] for r in rs if "n_think" in r]
        leak = sum(1 for r in rs if "</think>" in (r.get("content") or "") or "<think>" in (r.get("content") or ""))
        tool_leak = sum(1 for r in rs if re.search(r"<tool_call>[\s\S]*?</?think>[\s\S]*?</tool_call>", r.get("content") or ""))
        out = {"n": len(rs), "leak_any": leak, "leak_in_tool_call": tool_leak,
               "finish_stop": sum(r.get("finish") == "stop" for r in rs)}
        if th:
            out.update(think_median=statistics.median(th), think_mean=round(statistics.mean(th), 1),
                       under5k=sum(t < 5000 for t in th))
        if any("svg_ok" in r for r in rs):
            out["svg_ok"] = sum(bool(r.get("svg_ok")) for r in rs)
        if any("wall_s" in r for r in rs):
            out["wall_median_s"] = statistics.median(r["wall_s"] for r in rs if "wall_s" in r)
        print(lab, json.dumps(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "scan"]); ap.add_argument("paths", nargs="*")
    ap.add_argument("--port", type=int, default=8080); ap.add_argument("--label", default="arm")
    ap.add_argument("--out", default="pelican.jsonl"); ap.add_argument("--seeds", default="1-16")
    ap.add_argument("--effort", default="xhigh"); ap.add_argument("--lora-scale", type=float, default=None)
    ap.add_argument("--prompt", default=PELICAN); ap.add_argument("--max", type=int, default=60000)
    ap.add_argument("--temp", type=float, default=1.0)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else scan(a.paths)
