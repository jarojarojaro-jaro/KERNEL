#!/usr/bin/env python3
"""K-128: prompt-cache hits per agent turn from llama-server logs (default verbosity).

Per task the log has:
  get_availabl: "selected slot by LCP similarity, f_sim_best = S, f_keep = K"  (before launch)
     K = LCP(new prompt, slot cache) / slot cache length (= previous release n_tokens: prompt + generated incl. <think>)
  print_timing: "prompt eval time ... / N tokens"   N = prompt tokens actually processed (prompt_n)
                "eval time ... / G tokens"          G = generated tokens
  release:      "stop processing: n_tokens = E"     E = prompt_total + G - 1  ->  prompt_total = E - G + 1
cache_n = prompt_total - prompt_n.  lcp = K * prev_E.
Classification of follow-up turns (same slot cache, prev prompt >= 1024):
  held   : lcp >= prev prompt_total - 8   (prefix matches through the old history; only the last answer differs)
  broke  : lcp <  prev prompt_total - 8   (prefix diverges inside history the client already sent before)
Usage: cache_hits.py LOG...
"""
import re, sys

GA = re.compile(r'f_sim_best = ([\d.]+).*f_keep = ([\d.]+)')
LA = re.compile(r'task (\d+) \| processing task')
PE = re.compile(r'task (\d+) \| prompt eval time =\s*[\d.]+ ms /\s*(\d+) tokens')
EV = re.compile(r'task (\d+) \|\s+eval time =\s*[\d.]+ ms /\s*(\d+) tokens')
RL = re.compile(r'task (\d+) \| stop processing: n_tokens = (\d+)')

turns = []  # dict per finished task, in log order
for path in sys.argv[1:]:
    cur, pending = {}, None
    for line in open(path, errors='replace'):
        if 'get_availabl' in line:
            m = GA.search(line); pending = (float(m[1]), float(m[2])) if m else None; continue
        m = LA.search(line)
        if m:
            cur[int(m[1])] = {'sim': pending}; pending = None; continue
        for rx, key in ((PE, 'pn'), (EV, 'g'), (RL, 'end')):
            m = rx.search(line)
            if m:
                d = cur.setdefault(int(m[1]), {'sim': None}); d[key] = int(m[2])
                if key == 'end' and {'pn', 'g'} <= d.keys():
                    cur.pop(int(m[1]))
                    d['pt'] = d['end'] - d['g'] + 1; d['file'] = path.split('/')[-1]; d['task'] = int(m[1])
                    turns.append(d)
                break

tp = tc = 0
stats = {'held': [0, 0, 0, 0], 'broke': [0, 0, 0, 0]}  # turns, prompt tokens, cached tokens, tokens lost vs prev prompt
holes = []
prev = None
for d in turns:
    cn = max(d['pt'] - d['pn'], 0); tp += d['pt']; tc += cn
    if prev and prev['file'] == d['file'] and d['sim'] and prev['pt'] >= 1024 and d['pt'] >= prev['pt']:
        lcp = int(d['sim'][1] * prev['end'])
        k = 'held' if lcp >= prev['pt'] - 8 else 'broke'
        s = stats[k]; s[0] += 1; s[1] += d['pt']; s[2] += cn; s[3] += max(prev['pt'] - lcp, 0)
        if k == 'broke':
            holes.append((d['file'], d['task'], prev['pt'], prev['end'], lcp, d['pt'], cn))
    prev = d

print(f'turns {len(turns)}, prompt tokens {tp}, from cache {tc} ({100 * tc / max(tp, 1):.1f}%)')
for k, (n, p, c, lost) in stats.items():
    print(f'follow-up {k}: {n} turns, prompt {p}, from cache {c} ({100 * c / max(p, 1):.1f}%), history diverged {lost} tokens')
for h in holes[:30]:
    print('  broke file/task/prev_prompt/prev_end/lcp/prompt/cache_n', h)
