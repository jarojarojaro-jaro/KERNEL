#!/usr/bin/env python3
"""R57g quantalloc summaries (qa.jobs). Research only, no adoption without the user's OK.

  qa_sum.py gate   logs/kld.<arm>.<corpus>.log -> table + /tmp/quantalloc/<arm>.PASS for arms that pass the gate
  qa_sum.py abba   prose_sum.py per candidate (labels <x>Aa/<x>Ba/<x>Bb/<x>Ab, A = U4) -> logs/abba.txt
Gate: streamed bytes <= U4 - 0.9 GB (alloc.json), KLD-PL <= 1.10 x U4, same-top-PL >= U4 - 1.0 pp, EAR-PL >= U4 - 0.5 pp.
"""
import json, os, re, subprocess, sys

H = os.path.dirname(os.path.abspath(__file__))
ARMS = {'qa1': 'qa1-iq4-1.0', 'qa2': 'qa2-q4k-1.0', 'qa3': 'qa3-iq4-1.5'}
PAT = {'kld': r'Mean    KLD:\s+([0-9.]+)', 'top': r'Same top p:\s+([0-9.]+)', 'ear': r'Mean EAR  :\s+([0-9.]+)'}


def parse(arm, c):
    p = os.path.join(H, 'logs', f'kld.{arm}.{c}.log')
    t = open(p).read() if os.path.exists(p) else ''
    return {k: float(m[1]) if (m := re.search(v, t)) else None for k, v in PAT.items()}


def gate():
    alloc = json.load(open(os.path.join(H, 'alloc.json')))
    u = {c: parse('U4', c) for c in ('plprose', 'code')}
    if None in u['plprose'].values():
        sys.exit('U4 plprose log incomplete')
    os.makedirs('/tmp/quantalloc', exist_ok=True)
    print('arm  corpus   KLD      top1%   EAR%    dGB')
    for c in ('plprose', 'code'):
        print(f"U4   {c:8s} {u[c]['kld']:.5f} {u[c]['top']:6.2f} {u[c]['ear']:7.3f}   0")
    for arm, key in ARMS.items():
        r = {c: parse(arm, c) for c in ('plprose', 'code')}
        d = alloc[key]['d_streamed_gb']
        for c in ('plprose', 'code'):
            x = r[c]
            print(f"{arm}  {c:8s} {x['kld'] or 0:.5f} {x['top'] or 0:6.2f} {x['ear'] or 0:7.3f} {d:+.3f}")
        p = r['plprose']
        ok = (None not in p.values() and d <= -0.9 and p['kld'] <= 1.10 * u['plprose']['kld']
              and p['top'] >= u['plprose']['top'] - 1.0 and p['ear'] >= u['plprose']['ear'] - 0.5)
        print(f"  -> {arm} {'PASS' if ok else 'FAIL'}")
        if ok:
            open(f'/tmp/quantalloc/{arm}.PASS', 'w').write('gate\n')
    if not any(os.path.exists(f'/tmp/quantalloc/{a}.PASS') for a in ARMS):
        print('STOP RULE: no candidate beats U4 on bytes AND KLD -> drop the idea')


def abba():
    out = []
    for arm in ARMS:
        if not os.path.exists(f'/tmp/quantalloc/{arm}.PASS'):
            continue
        r = subprocess.run([sys.executable, os.path.expanduser('~/qwen-opt/xtxroadmap/prose_sum.py'),
                            os.path.join(H, 'logs', 'prose.jsonl'), arm, 'A'], capture_output=True, text=True)
        out.append(f'== {arm}\n{r.stdout}{r.stderr}')
    open(os.path.join(H, 'logs', 'abba.txt'), 'w').write('\n'.join(out))
    print('\n'.join(out))


{'gate': gate, 'abba': abba}[sys.argv[1]]()
