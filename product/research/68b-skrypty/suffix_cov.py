#!/usr/bin/env python3
"""R68b: proxy for 'global suffix cache' (report 18 #6, AgSpec) on the real omp session of 2026-11-06 (CPU only).

Word-level proxy (regex tokens, not BPE): for every token the model emitted (thinking, text, tool-call args) count
whether a 3-gram suffix lookup predicts it correctly from
  (S) the session so far (everything the model has seen or emitted before; = today's context lookup, upper bound),
  (G) a global corpus of other omp sessions on this machine (static, built before the session).
Reports the share of emitted tokens predicted by S, by G only (S misses), and by output category.
Only aggregate counts are printed; no session content leaves this script.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

TOK = re.compile(r"\w+|[^\w\s]|\n")
N = 3


def texts_of(msg):
    """(category, text, is_output) blocks of one omp message."""
    out = []
    role = msg.get("role")
    for b in msg.get("content") or []:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if role == "assistant":
            if t == "thinking":
                out.append(("thinking", b.get("thinking", ""), True))
            elif t == "text":
                out.append(("text", b.get("text", ""), True))
            elif t == "toolCall":
                args = b.get("arguments") or {}
                for k, v in args.items():
                    if isinstance(v, str):
                        out.append((f"tool:{b.get('name')}", v, True))
        elif t == "text":
            out.append(("ctx", b.get("text", ""), False))
    return out


def session_messages(path):
    for line in open(path, encoding="utf-8", errors="ignore"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") == "message" and isinstance(o.get("message"), dict):
            yield o["message"]


def main():
    target = Path(sys.argv[1])
    root = Path.home() / ".omp/agent/sessions"
    t0 = target.stat().st_mtime - 3600  # sessions written before the target session (causal corpus)
    others = sorted((p for p in root.rglob("*.jsonl") if p != target and p.stat().st_mtime < t0),
                    key=lambda p: p.stat().st_mtime)[-400:]
    gidx, gtok = {}, []
    for p in others:
        for m in session_messages(p):
            for _, txt, _ in texts_of(m):
                gtok.extend(TOK.findall(txt))
    for i in range(N, len(gtok)):
        gidx[tuple(gtok[i - N:i])] = i
    print(f"global corpus: {len(others)} sessions, {len(gtok)} tokens, {len(gidx)} 3-grams")
    stok, sidx = [], {}
    cnt = Counter()

    def push(toks):
        for t in toks:
            stok.append(t)
            if len(stok) > N:
                sidx[tuple(stok[-N - 1:-1])] = len(stok) - 1

    for m in session_messages(target):
        for cat, txt, is_out in texts_of(m):
            toks = TOK.findall(txt)
            if not is_out:
                push(toks)
                continue
            run_s = run_g = 0
            for t in toks:
                cnt[(cat, "n")] += 1
                hit_s = hit_g = False
                if len(stok) >= N:
                    key = tuple(stok[-N:])
                    ps = sidx.get(key)
                    hit_s = ps is not None and stok[ps] == t
                    pg = gidx.get(key)
                    hit_g = pg is not None and gtok[pg] == t
                    if hit_s:
                        cnt[(cat, "s")] += 1
                    elif hit_g:
                        cnt[(cat, "g_only")] += 1
                # tail proxy: token beyond depth 4 of a run of consecutive correct lookups (what MTP-4 cannot reach)
                run_s = run_s + 1 if hit_s else 0
                run_g = run_g + 1 if hit_g else 0
                if run_s > 4:
                    cnt[(cat, "s_tail")] += 1
                elif run_g > 4:
                    cnt[(cat, "g_tail_only")] += 1
                push([t])
    cats = sorted({c for c, _ in cnt})
    tot = Counter()
    for c in cats:
        n, s, g = cnt[(c, "n")], cnt[(c, "s")], cnt[(c, "g_only")]
        st, gt = cnt[(c, "s_tail")], cnt[(c, "g_tail_only")]
        for k, v in (("n", n), ("s", s), ("g", g), ("st", st), ("gt", gt)):
            tot[k] += v
        print(f"{c:14s} tokens {n:7d}  session {s / n * 100:5.1f}%  global-only {g / n * 100:5.1f}%  "
              f"tail>4: session {st / n * 100:5.1f}%  global-only {gt / n * 100:5.1f}%")
    n = tot["n"]
    print(f"{'ALL':14s} tokens {n:7d}  session {tot['s'] / n * 100:5.1f}%  global-only {tot['g'] / n * 100:5.1f}%  "
          f"tail>4: session {tot['st'] / n * 100:5.1f}%  global-only {tot['gt'] / n * 100:5.1f}%")


if __name__ == "__main__":
    main()
