#!/usr/bin/env python3
"""L1 host-side measurements on a running llama-server (66-SYNTEZA items 7 and 8), one arm.

  replay : 2 agent threads (recorded omp conversations, convs.json + plan.json), interleaved turn by turn inside the
           75-120k token window, max_tokens 16; per turn: wall, prompt_n / cache_n / prompt_ms, and the server log's
           "ap tokenize" / "ap chat" lines (LLAMA_SERVER_AP_TIMING=1).
  stream : one long greedy answer (12288 tokens, ignore_eos) with stream false and true; per run: wall, server process
           CPU (utime+stime), timings, and ms/token over the last 2k tokens from the log's tg_3s lines.
  md5    : the final-mode greedy check (content md5[:8], 256 tokens).
Results: one JSON line per item appended to --out.

usage: suite.py --label L --port P --log SERVER_LOG --out results.jsonl [--only replay,stream,md5]
"""
import argparse, hashlib, json, os, re, subprocess, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def post(port, body, timeout=1800):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def server_pid(port):
    out = subprocess.run(["pgrep", "-f", f"llama-server.*--port {port}( |$)"], capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else None


def cpu_s(pid):
    f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
    return (int(f[11]) + int(f[12])) / os.sysconf("SC_CLK_TCK")


def log_from(path, off):
    with open(path, errors="ignore") as f:
        f.seek(off)
        return f.read()


def replay(a, emit):
    convs = {c["name"]: c for c in json.load(open(os.path.join(HERE, "convs.json")))}
    plan = json.load(open(os.path.join(HERE, "plan.json")))  # {"threads": [{"name", "turns": [k...]}]}
    seq = []
    n = max(len(t["turns"]) for t in plan["threads"])
    for i in range(n):
        for t in plan["threads"]:
            if i < len(t["turns"]):
                seq.append((t["name"], t["turns"][i]))
    for idx, (name, k) in enumerate(seq):
        c = convs[name]
        body = {"messages": c["messages"][:k], "tools": c["tools"], "max_tokens": 16, "temperature": 0, "seed": 1}
        off = os.path.getsize(a.log)
        t0 = time.perf_counter()
        r = json.load(post(a.port, body))
        wall = 1000 * (time.perf_counter() - t0)
        time.sleep(0.3)  # the log lines of this request are flushed
        txt = log_from(a.log, off)
        tok = [float(x) for x in re.findall(r"ap tokenize: \d+ tokens, ([0-9.]+) ms", txt)]
        tmpl = [float(x) for x in re.findall(r"ap chat: .*?template ([0-9.]+) ms", txt)]
        mism = len(re.findall(r"tokenize cache: MISMATCH", txt))
        t = r["timings"]
        row = {"label": a.label, "item": "replay", "i": idx, "thread": name[:24], "turn": k, "prompt_tokens": t.get("prompt_n", 0) + t.get("cache_n", 0),
               "prompt_n": t["prompt_n"], "cache_n": t.get("cache_n"), "prompt_ms": round(t["prompt_ms"], 1), "wall_ms": round(wall, 1),
               "tokenize_ms": tok[0] if tok else None, "template_ms": tmpl[0] if tmpl else None, "tok_mismatch": mism}
        emit(row)


def stream_long(a, emit):
    prompt = ("Write an exhaustive technical handbook about building a production-grade HTTP/1.1 and HTTP/2 server in C++: "
              "architecture, parsing, connection management, TLS, flow control, testing, benchmarking, deployment. "
              "Include long code listings for every component and explain each listing in detail.")
    pid = server_pid(a.port)
    for stream in [m == "true" for m in a.stream_modes.split(",")]:
        body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": a.gen_tokens, "temperature": 0, "seed": 1,
                "ignore_eos": True, "cache_prompt": False, "stream": stream}
        if stream:
            body["stream_options"] = {"include_usage": True}
            body["timings_per_token"] = False
        off = os.path.getsize(a.log)
        c0 = cpu_s(pid)
        t0 = time.perf_counter()
        resp = post(a.port, body)
        timings, n_chunks, text = None, 0, []
        if stream:
            for line in resp:
                line = line.strip()
                if not line.startswith(b"data: ") or line == b"data: [DONE]":
                    continue
                o = json.loads(line[6:])
                n_chunks += 1
                for ch in o.get("choices", []):
                    d = ch.get("delta", {})
                    text.append((d.get("reasoning_content") or "") + (d.get("content") or ""))
                if "timings" in o:
                    timings = o["timings"]
        else:
            o = json.load(resp)
            timings = o["timings"]
            m = o["choices"][0]["message"]
            text.append((m.get("reasoning_content") or "") + (m.get("content") or ""))
        wall = time.perf_counter() - t0
        cpu = cpu_s(pid) - c0
        time.sleep(0.3)
        txt = log_from(a.log, off)
        # tg_3s windows: tokens per window / rate -> ms over the windows that end in the last 2k tokens
        lines = [(int(n), float(r)) for n, r in re.findall(r"n_gen = +(\d+), tg = +[0-9.]+ t/s, tg_3s = +([0-9.]+) t/s", txt)]
        tail_tok, tail_ms, prev = 0, 0.0, None
        for n, r in lines:
            if prev is not None and n >= a.gen_tokens - 2048 and r > 0:
                tail_tok += n - prev
                tail_ms += 1000.0 * (n - prev) / r
            prev = n
        steps = timings["predicted_n"] - timings.get("draft_n_accepted", 0) if timings else None
        row = {"label": a.label, "item": "stream", "stream": stream, "wall_s": round(wall, 2), "server_cpu_s": round(cpu, 2),
               "chunks": n_chunks, "predicted_n": timings and timings["predicted_n"], "tps": timings and round(timings["predicted_per_second"], 2),
               "steps": steps, "ms_per_step": timings and steps and round(timings["predicted_ms"] / steps, 3),
               "tail_ms_per_token": round(tail_ms / tail_tok, 4) if tail_tok else None, "tail_tokens": tail_tok,
               "text_md5": hashlib.md5("".join(text).encode()).hexdigest()[:8]}
        emit(row)


def md5(a, emit):
    o = json.load(post(a.port, {"messages": [{"role": "user", "content": "Explain how a hash map works, step by step."}],
                                "max_tokens": 256, "temperature": 0, "seed": 1}))
    emit({"label": a.label, "item": "md5", "md5": hashlib.md5(o["choices"][0]["message"]["content"].encode()).hexdigest()[:8],
          "tps": round(o["timings"]["predicted_per_second"], 2)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="replay,stream,md5")
    ap.add_argument("--gen-tokens", type=int, default=12288)
    ap.add_argument("--stream-modes", default="false,true")
    a = ap.parse_args()

    def emit(row):
        print(json.dumps(row), flush=True)
        with open(a.out, "a") as f:
            f.write(json.dumps(row) + "\n")

    for item in a.only.split(","):
        {"replay": replay, "stream": stream_long, "md5": md5}[item](a, emit)


if __name__ == "__main__":
    main()
