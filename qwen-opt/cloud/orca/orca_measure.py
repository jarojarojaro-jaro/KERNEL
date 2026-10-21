#!/usr/bin/env python3
"""Measurements for the OrcaCyber-Nano-1.0 campaign on a rented RTX 3090. Runs ON the instance.

Subcommands
  long    --port P --label L --ctx C --fracs 0.5,0.8 [--tokens 128] --out FILE
          builds a synthetic prompt of frac*C tokens, measures TTFT (prompt_ms), prefill t/s,
          decode t/s and peak VRAM/power during the request. A rejected prompt (context too
          small / OOM) is recorded as ok=false with the server's error text.
  md5     --port P --label L --out FILE          greedy (T=0) 2x400 tokens, writes the text, prints md5
  summary --dir RESULTS                          builds summary.md from the jsonl/tsv files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request

PARA = (
    "The harbour master logged every ship that entered the bay: its flag, its draught, the hour it crossed "
    "the bar, and whether the pilot boat went out to meet it. On the night of the great storm the log ran "
    "to eleven pages, and the last entry was written by a hand that was not his. Years later a clerk found "
    "the page folded inside a ledger, and the ink had bled through into the numbers of the following month. "
)

PROMPTS = [
    "Explain how a hash map works, then implement one in C with open addressing.",
    "Napisz krótkie opowiadanie o latarniku i sztormie.",
]


def gpu() -> tuple[float, float, float] | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,power.draw,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10).stdout.strip().splitlines()[0]
        m, p, u = (float(x) for x in out.split(","))
        return m, p, u
    except Exception:
        return None


class Peak:
    def __init__(self) -> None:
        self.v = [0.0, 0.0, 0.0]
        self._stop = threading.Event()
        self.t: threading.Thread | None = None

    def __enter__(self):
        def loop():
            while not self._stop.is_set():
                g = gpu()
                if g:
                    for i in range(3):
                        self.v[i] = max(self.v[i], g[i])
                self._stop.wait(0.5)
        self.t = threading.Thread(target=loop, daemon=True)
        self.t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        if self.t:
            self.t.join(timeout=2)


def post(port: int, path: str, body: dict, timeout: float = 3600) -> tuple[int, dict]:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw[:1000]}


def chat(port: int, prompt: str, tokens: int, temp: float, seed: int) -> tuple[int, dict]:
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": tokens,
            "temperature": temp, "seed": seed, "cache_prompt": False}
    code, resp = post(port, "/v1/chat/completions", body)
    if code != 200 and "chat_template_kwargs" not in body:
        # Orca's template may not know enable_thinking; retry without the kwargs before giving up
        body["chat_template_kwargs"] = {"enable_thinking": False}
        code, resp = post(port, "/v1/chat/completions", body)
    return code, resp


def append(path: str, rec: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def cmd_long(a) -> None:
    for frac in (float(x) for x in a.fracs.split(",")):
        target = max(1, int(a.ctx * frac))
        chars = target * 4
        text = (PARA * (chars // len(PARA) + 1))[:chars] + "\n\nIn one sentence: what did the harbour master log first?"
        with Peak() as pk:
            t0 = time.time()
            code, resp = chat(a.port, text, a.tokens, 0.0, 1)
            wall = time.time() - t0
        rec = {"label": a.label, "ctx": a.ctx, "frac": frac, "target_tokens": target,
               "ok": code == 200, "wall_s": round(wall, 2), "peak_vram_mib": pk.v[0], "peak_w": pk.v[1]}
        if code == 200:
            t = resp.get("timings", {})
            rec.update({"prompt_n": t.get("prompt_n"), "prompt_ms": t.get("prompt_ms"),
                        "prefill_tps": t.get("prompt_per_second"),
                        "predicted_n": t.get("predicted_n"), "tps": t.get("predicted_per_second"),
                        "draft_n": t.get("draft_n"), "draft_n_accepted": t.get("draft_n_accepted"),
                        "ttft_ms": t.get("prompt_ms")})
        else:
            rec["error"] = str(resp)[:500]
        print(json.dumps({k: rec[k] for k in ("label", "ctx", "frac", "ok", "prompt_n", "ttft_ms", "tps",
                                              "prefill_tps", "peak_vram_mib") if k in rec}), flush=True)
        append(a.out, rec)


def cmd_md5(a) -> None:
    text = ""
    for p in PROMPTS:
        code, resp = chat(a.port, p, 400, 0.0, 1)
        if code != 200:
            text += f"ERROR {code} {str(resp)[:300]}\n"
            continue
        msg = resp["choices"][0]["message"]
        text += (msg.get("reasoning_content") or "") + (msg.get("content") or "") + "\n"
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        f.write(text)
    print(hashlib.md5(text.encode()).hexdigest()[:12])


def _rows(path: str) -> list[dict]:
    try:
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        return []


def cmd_summary(a) -> None:
    res = a.dir
    out: list[str] = [f"# OrcaCyber-Nano-1.0 na RTX 3090 — {time.strftime('%Y-%m-%d')}\n"]
    probe = _rows(os.path.join(res, "probe", "servers.jsonl"))
    depth = _rows(os.path.join(res, "probe", "long.jsonl"))
    if probe:
        out.append("## Kontekst (KV q4_0, `-ngl 999 -fit off`)\n")
        out.append("| ctx żądany | n_ctx | wynik | VRAM MiB | load s | głębokość 0.8 |")
        out.append("|---|---|---|---|---|---|")
        for r in probe:
            d = next((x for x in depth if x.get("label", "").startswith(r["label"])), {})
            out.append(f"| {r.get('requested_ctx')} | {r.get('n_ctx', '?')} | {'OK' if r.get('ok') else 'FAIL'} | "
                       f"{r.get('vram_mib', '?')} | {r.get('load_s', '?')} | "
                       f"{'ok' if d.get('ok') else ('event: ' + str(d.get('error', 'n/a'))[:40] if d else '-')} |")
        out.append("")
    sw = _rows(os.path.join(res, "sweep", "spec_sweep.jsonl"))
    if sw:
        out.append("## Drafter / KV / flagi (T=1, 6 promptów × 2 seedy, 400 tok, ctx 32768)\n")
        out.append("| konfiguracja | median t/s | ms/krok |")
        out.append("|---|---|---|")
        for r in sorted(sw, key=lambda x: -x["median_tps"]):
            out.append(f"| {r['label']} | {r['median_tps']:.1f} | {r['median_ms_step']:.2f} |")
        out.append("")
    lg = _rows(os.path.join(res, "long", "long.jsonl"))
    if lg:
        out.append("## Długi kontekst\n")
        out.append("| konfiguracja | ctx | frakcja | prompt tok | TTFT ms | prefill t/s | decode t/s | VRAM MiB |")
        out.append("|---|---|---|---|---|---|---|---|")
        for r in lg:
            out.append(f"| {r['label']} | {r['ctx']} | {r['frac']} | {r.get('prompt_n', '-')} | "
                       f"{r.get('ttft_ms', '-')} | {r.get('prefill_tps', '-')} | "
                       f"{r.get('tps', '-')} | {r.get('peak_vram_mib', '-')} |")
        out.append("")
    md = os.path.join(res, "greedy", "md5.tsv")
    if os.path.exists(md):
        out.append("## Greedy md5 (T=0)\n```\n" + open(md).read().strip() + "\n```\n")
    with open(os.path.join(res, "summary.md"), "w") as f:
        f.write("\n".join(out))
    print("\n".join(out))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("long"); p.add_argument("--port", type=int, default=18433)
    p.add_argument("--label", required=True); p.add_argument("--ctx", type=int, required=True)
    p.add_argument("--fracs", default="0.5,0.8"); p.add_argument("--tokens", type=int, default=128)
    p.add_argument("--out", required=True)
    m = sub.add_parser("md5"); m.add_argument("--port", type=int, default=18433)
    m.add_argument("--label", required=True); m.add_argument("--out", required=True)
    s = sub.add_parser("summary"); s.add_argument("--dir", required=True)
    a = ap.parse_args()
    {"long": cmd_long, "md5": cmd_md5, "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    main()
