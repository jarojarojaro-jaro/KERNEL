#!/usr/bin/env python3
"""16i: rozkład wygranej Magnitude (copy/code-edit) na tok/krok × ms/krok oraz projekcja
szerszej weryfikacji u nas (XTX Qwen3.8-27B) z krzywej vcost. Tylko CPU, czyta gotowe logi.

Definicje (zgodne z xbench.jsonl): kroki = n - accepted; tok/krok = n / kroki;
ms/krok = ms / kroki (ms = czas generacji z serwera); propozycje/krok = draft / kroki.
"""
import collections, csv, json, math, os, statistics

H = os.path.expanduser
RES = H('~/qwen-opt/cloud/results')
RUNS = {'5060ti': f'{RES}/magnitude-vs-5060ti-20261016/x/xbench.jsonl',
        '3090': f'{RES}/magnitude-vs-3090-20261016/x/xbench.jsonl'}
VCOST = H('~/qwen-opt/k4/vcost_qwen-k4b.csv')


def rows(path):
    return [json.loads(l) for l in open(path)]


def agg(rs):
    n = sum(r['n'] for r in rs); acc = sum(r['accepted'] for r in rs); dr = sum(r['draft'] for r in rs)
    ms = sum(r['ms'] for r in rs); steps = n - acc
    return dict(n=n, acc=acc, draft=dr, steps=steps, tok_step=n / steps, ms_step=ms / steps,
                prop_step=dr / steps, acc_rate=acc / dr if dr else 0.0, tps=1000 * n / ms,
                prefill_s=statistics.mean(r['prompt_ms'] for r in rs) / 1000, prompt_n=statistics.mean(r['prompt_n'] for r in rs))


def decomposition():
    out = ['## Rozkład copy/code-edit (suma po żądaniach; fork = nasz MTP n_max=4)', '',
           '| GPU | model | workload | silnik | żądań | tok/krok | ms/krok | propozycje/krok | akcept. propozycji | t/s | prefill s (śr.) |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    pairs = []
    for gpu, path in RUNS.items():
        g = collections.defaultdict(list)
        for r in rows(path):
            if r['kind'] not in ('copy', 'code'):
                continue
            model, _, eng, _ = r['label'].split('|')
            if model not in ('qwen', 'qwen9') or eng not in ('fork', 'mag'):
                continue
            g[(model, r['kind'], eng)].append(r)
        for (model, kind, eng), rs in sorted(g.items()):
            a = agg(rs)
            out.append(f"| {gpu} | {model} | {kind} | {eng} | {len(rs)} | {a['tok_step']:.2f} | {a['ms_step']:.1f} | "
                       f"{a['prop_step']:.2f} | {a['acc_rate']:.3f} | {a['tps']:.1f} | {a['prefill_s']:.1f} |")
        for (model, kind, eng) in sorted(g):
            if eng == 'mag' and (model, kind, 'fork') in g:
                m, f = agg(g[(model, kind, 'mag')]), agg(g[(model, kind, 'fork')])
                pairs.append((gpu, model, kind, m, f))
    out += ['', '## Dekompozycja: speedup = (tok/krok mag / fork) × (ms/krok fork / mag)', '',
            '| GPU | model | workload | speedup | czynnik tok/krok | czynnik ms/krok | t/s mag przy naszym ms/krok |',
            '|---|---|---|---|---|---|---|']
    for gpu, model, kind, m, f in pairs:
        s = m['tps'] / f['tps']; t = m['tok_step'] / f['tok_step']; c = f['ms_step'] / m['ms_step']
        out.append(f"| {gpu} | {model} | {kind} | {s:.2f}× | {t:.2f}× | {c:.2f}× | {1000 * m['tok_step'] / f['ms_step']:.0f} |")
    return out


def per_request():
    out = ['', '## Per żądanie (copy/code; 3090 qwen = Qwen3.8-27B UD-Q4_K_XL, 5060ti qwen9 = Qwen3.5-9B UD-Q4_K_XL)', '',
           '| GPU | model | silnik | element | prompt tok | propozycje | przyjęte | kroki | propozycje/krok | tok/krok | ms/krok | t/s | prefill s |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for gpu, path in RUNS.items():
        seen = set()
        for r in rows(path):
            if r['kind'] not in ('copy', 'code'):
                continue
            model, _, eng, rnd = r['label'].split('|')
            if model not in ('qwen', 'qwen9') or eng not in ('fork', 'mag') or (gpu == '5060ti' and model == 'qwen'):
                continue
            key = (model, eng, r['item'])
            if key in seen:  # jedna runda na silnik (pierwsza w pliku)
                continue
            seen.add(key)
            steps = r['n'] - r['accepted']
            out.append(f"| {gpu} | {model} | {eng}\\|{rnd} | {r['item']} | {r['prompt_n']} | {r['draft']} | {r['accepted']} | {steps} | "
                       f"{r['draft'] / steps:.2f} | {r['n'] / steps:.2f} | {r['ms'] / steps:.1f} | {r['tps']:.1f} | {r['prompt_ms'] / 1000:.1f} |")
    return out


def sweep():
    out = ['', '## Sweep T=1 per prompt (Magnitude vs fork): propozycje/krok pokazują adaptację szerokości', '',
           '| GPU | model | prompt | mag t/s | fork t/s | mag tok/krok | fork tok/krok | mag ms/krok | fork ms/krok | mag propozycje/krok | fork propozycje/krok |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    for gpu, path in RUNS.items():
        sw = {}
        for r in rows(path):
            if r['kind'] == 'sweep':
                model, _, eng, _ = r['label'].split('|')
                if eng in ('mag', 'fork') and model in ('qwen', 'qwen9'):
                    sw.setdefault((model, eng), r)
        for model in ('qwen', 'qwen9'):
            if (model, 'mag') not in sw or (model, 'fork') not in sw:
                continue
            M, F = sw[(model, 'mag')], sw[(model, 'fork')]
            for p in M['prompts']:
                def ps(r):
                    v = r['prompts'][p]; d = sum(x['draft'] for x in r['raw'][p])
                    return v, d / (v['n'] / v['tok_step'])
                (mv, md), (fv, fd) = ps(M), ps(F)
                out.append(f"| {gpu} | {model} | {p} | {mv['tps']:.1f} | {fv['tps']:.1f} | {mv['tok_step']:.2f} | {fv['tok_step']:.2f} | "
                           f"{mv['ms_step']:.1f} | {fv['ms_step']:.1f} | {md:.2f} | {fd:.2f} |")
            out.append(f"| {gpu} | {model} | **mediana** | {M['median_tps']:.1f} | {F['median_tps']:.1f} | | | {M['median_ms_step']:.1f} | {F['median_ms_step']:.1f} | | |")
    return out


def geo_tokens(ps):
    """Oczekiwane tok/krok przy łańcuchu propozycji o warunkowych akceptacjach ps (prefiks) + 1 token celu."""
    e, c = 1.0, 1.0
    for p in ps:
        c *= p; e += c
    return e


def projection():
    vc = {int(r['n_prompt']): 1000 * int(r['n_prompt']) / float(r['avg_ts']) for r in csv.DictReader(open(VCOST))}
    base_step = 27.74  # 15b-spekulacja-frontier.md:255 (PM4, XTX, krótki kontekst, MTP n=4)
    lvl = 0.65         # ms draftu MTP na poziom łańcucha (T1, wiki eksperymenty/2026-10-14-t1-t2-draft.md)
    out = ['', '## Projekcja XTX Qwen3.8-27B, krótki kontekst (d=2048): t/s = tok/krok / (27.74 ms + ΔV(W+1) + Δdraft)', '',
           'ΔV z `vcost_qwen-k4b.csv` (llama-bench, wiersze = propozycje + anchor); Δdraft: łańcuch MTP +0.65 ms/poziom ponad 4 (T1), '
           'ogon lookup 0 ms GPU [INFERENCE]; akceptacja geometryczna (p warunkowe na pozycję).', '',
           '| wariant | propozycje W | wiersze | ΔV ms | krok ms | p MTP | p ogon | tok/krok | t/s | vs MTP4 |', '|---|---|---|---|---|---|---|---|---|---|']
    for pm, pt in ((0.99, 0.99), (0.99, 0.95), (0.95, 0.85)):
        ref = None
        for name, w in (('MTP4 (dziś)', 4), ('MTP4+ogon', 7), ('MTP4+ogon', 11), ('MTP4+ogon', 15), ('łańcuch MTP', 7), ('łańcuch MTP', 15)):
            rws = w + 1
            dv = vc[rws] - vc[5]
            chain = name.startswith('łańcuch')
            step = base_step + dv + (lvl * (w - 4) if chain else 0.0)
            ps = [pm] * min(4, w) + [pm if chain else pt] * (w - 4)
            tok = geo_tokens(ps)
            tps = 1000 * tok / step
            if w == 4:
                ref = tps
            out.append(f"| {name} | {w} | {rws} | {dv:+.2f} | {step:.2f} | {pm} | {'-' if chain or w == 4 else pt} | {tok:.2f} | {tps:.0f} | {tps / ref:.2f}× |")
    out += ['', '## Długi kontekst (3090, 64k): model kafli FA `ceil(6·wiersze/16)` (15b:20) [INFERENCE]', '',
            '| wiersze | kafle | Δattn ms | krok ms (est.) | tok/krok @p=0.99 | t/s |', '|---|---|---|---|---|---|']
    f2k, f64k = 46.5, 64.8  # 3090 fork code-edit ~2k i copy 64k (xbench), W=5 wierszy
    per_tile = (f64k - f2k) / 2
    for rws in (5, 8, 12, 16):
        tiles = math.ceil(6 * rws / 16)
        step = f2k + (vc[rws] - vc[5]) * (46.5 / 27.85) + per_tile * tiles  # ΔV skalowane czasem kroku 3090/XTX [INFERENCE]
        tok = geo_tokens([0.99] * (rws - 1))
        out.append(f"| {rws} | {tiles} | {per_tile * tiles:.1f} | {step:.1f} | {tok:.2f} | {1000 * tok / step:.0f} |")
    return out


if __name__ == '__main__':
    print('\n'.join(decomposition() + per_request() + sweep() + projection()))
