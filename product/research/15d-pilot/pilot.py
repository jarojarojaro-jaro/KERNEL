#!/usr/bin/env python3
"""PFlash v2 selection replica on CPU (llama.cpp CPU taps + numpy probes/head).

Per case: render a Qwen chat prompt (user = long document + question), get the
post-block-14 tap of Qwen3.5-0.8B from a 15-block GGUF via llama-embedding, then run
the Lucebox segment probe, request probe and scoring head (formulas from
lucebox server/src/pflash/qwen35_drafter.cpp:1540-1700, 2238-2330 and
pflash_selection.cpp:657-739) and the release budget curve. Reports whether the
evidence line survives, for the head, a BM25 baseline and random units.
"""
import json, math, os, re, subprocess, sys, time
import numpy as np
sys.path.insert(0, '/home/jaro/llama-master/gguf-py')
from gguf import GGUFReader

BIN = os.path.expanduser('~/wt/cuda-amdopt-cpu/build-cpu/bin/llama-embedding')
M = os.path.expanduser('~/models/pflash')
DRAFTER = f'{M}/Qwen3.5-0.8B-BF16.gguf'
TRUNC = f'{M}/Qwen3.5-0.8B-BF16-blk0-14.gguf'
OUT = '/tmp/pflash/pilot'
CURVE = [(16384, 0.315), (32768, 0.270), (65536, 0.270), (120000, 0.225)]


def tensor(r, name):
    t = next(t for t in r.tensors if t.name == name)
    a = np.asarray(t.data)
    if t.tensor_type.name == 'BF16':
        a = (a.view(np.uint16).astype(np.uint32) << 16).view(np.float32)
    a = a.astype(np.float32)
    shape = [int(x) for x in reversed(t.shape)]  # numpy order: rows = ne1
    return a.reshape(shape)


def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b); cs.append(256 + n); n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


def load():
    d = GGUFReader(DRAFTER)
    toks = d.fields['tokenizer.ggml.tokens'].contents()
    ttype = d.fields['tokenizer.ggml.token_type'].contents()
    eps = float(d.fields['qwen35.attention.layer_norm_rms_epsilon'].contents())
    blk = {k: tensor(d, f'blk.15.{k}.weight') for k in ('attn_norm', 'attn_q_norm', 'attn_k_norm')}
    seg = GGUFReader(f'{M}/segment-probe.gguf')
    req = GGUFReader(f'{M}/request-probe.gguf')
    head = GGUFReader(f'{M}/seg-scoring-head.gguf')
    P = {k: tensor(seg, f'segmentprobe.{k}') for k in ('norm.weight', 'norm.bias', 'fc1.weight', 'fc1.bias', 'fc2.weight', 'fc2.bias',
                                                       'conv.weight', 'conv.bias', 'subunit.fc2.weight', 'subunit.fc2.bias',
                                                       'subunit.conv.weight', 'subunit.conv.bias')}
    Rq = {k: tensor(req, f'requestprobe.{k}') for k in ('norm.weight', 'norm.bias', 'fc1.weight', 'fc1.bias', 'fc2.weight', 'fc2.bias')}
    H = {k: tensor(head, f'scoringhead.{k}.weight') for k in ('attn_q', 'attn_k')}
    dec = bytes_to_unicode()
    pieces = []
    for s, ty in zip(toks, ttype):
        if ty in (3, 4):  # control / user-defined
            pieces.append(s.encode())
        else:
            pieces.append(bytes(dec.get(ch, ord('?')) for ch in s))
    return dict(pieces=pieces, eps=eps, blk=blk, P=P, R=Rq, H=H)


def run_tap(prompt, tag):
    pf = f'{OUT}/{tag}.prompt.txt'
    open(pf, 'w').write(prompt)
    cache = f'{OUT}/{tag}.npz'
    if os.path.exists(cache):
        z = np.load(cache)
        return z['ids'], z['X'], float(z['sec'])
    t0 = time.time()
    p = subprocess.run([BIN, '-m', TRUNC, '-f', pf, '--pooling', 'none', '--embd-normalize', '-1',
                        '--embd-output-format', 'array', '--embd-separator', '<#NOSEP#>', '--verbose-prompt',
                        '-c', '32768', '-b', '32768', '-ub', '32768', '-fa', 'on', '-t', '16', '--no-warmup'],
                       capture_output=True)
    sec = time.time() - t0
    out = p.stdout.decode('utf-8', 'replace')
    err = p.stderr.decode('utf-8', 'replace')
    if p.returncode != 0:
        raise RuntimeError(err[-3000:])
    ids = [int(m.group(1)) for m in re.finditer(r"^\s*(\d+) -> '", out + '\n' + err, re.M)]
    a = [m.start() for m in re.finditer(r'\[\[(?=[-0-9.])', out)][-1]
    body = out[a:out.rindex(']]') + 2]
    rows = body[2:-2].split('],[')
    X = np.array([np.fromstring(r, sep=',', dtype=np.float32) for r in rows], dtype=np.float32)
    ids = np.array(ids[:X.shape[0]], dtype=np.int64)
    assert len(ids) == X.shape[0], (len(ids), X.shape)
    np.savez(cache, ids=ids, X=X, sec=sec)
    return ids, X, sec


def layernorm(x, w, b, eps):
    mu = x.mean(-1, keepdims=True)
    var = ((x - mu) ** 2).mean(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * w + b


def rmsnorm(x, eps):
    return x / np.sqrt((x * x).mean(-1, keepdims=True) + eps)


def gelu_tanh(x):
    return 0.5 * x * (1 + np.tanh(0.7978845608028654 * (x + 0.044715 * x ** 3)))


def gelu_erf(x):
    from math import erf
    v = np.vectorize(erf)
    return 0.5 * x * (1 + v(x / math.sqrt(2)))


def smooth(raw, w, b):
    taps = len(w); rad = taps // 2; S = len(raw)
    acc = raw + b
    for k in range(taps):
        sh = k - rad
        shifted = np.zeros(S, dtype=np.float32)
        if sh >= 0:
            shifted[:S - sh] = raw[sh:]
        else:
            shifted[-sh:] = raw[:S + sh]
        acc = acc + w[k] * shifted
    return 1 / (1 + np.exp(-acc))


def segments(boundary, split, S, forced, line_start, after_blank, thr=0.8, mn=32, mx=512):
    cuts = [0]
    fs = set(c for c in forced if 0 < c < S)
    for t in range(1, S):
        want = t in fs or boundary[t] > thr
        if not want:
            continue
        if t not in fs and t - cuts[-1] < mn:
            continue
        cuts.append(t)
    cuts.append(S)
    spans = []
    for i in range(1, len(cuts)):
        b, e = cuts[i - 1], cuts[i]
        while e - b > mx:
            lo = max(b + mn, b + mx // 2); hi = min(e - mn, b + mx)
            best = -1; bs = 0.0
            for t in range(lo, hi + 1):
                if split[t] > bs:
                    bs = split[t]; best = t
            if best < 0:
                best = b + mx
            for pas in (0, 1):
                al = -1
                for t in range(lo, hi + 1):
                    if not line_start[t] or (pas == 0 and not after_blank[t]):
                        continue
                    if al < 0 or split[t] > split[al]:
                        al = t
                if al >= 0:
                    best = al; break
            spans.append((b, best)); b = best
        spans.append((b, e))
    return spans


def keep_ratio(S):
    if S <= CURVE[0][0]:
        return CURVE[0][1]
    for (a, ra), (b, rb) in zip(CURVE, CURVE[1:]):
        if S <= b:
            return ra + (rb - ra) * (S - a) / (b - a)
    return CURVE[-1][1]


def bm25_scores(units_text, query):
    tok = lambda s: re.findall(r'\w+', s.lower())
    q = set(tok(query))
    docs = [tok(u) for u in units_text]
    N = len(docs); avg = sum(map(len, docs)) / max(1, N)
    df = {w: sum(1 for d in docs if w in d) for w in q}
    out = []
    for d in docs:
        s = 0.0
        for w in q:
            f = d.count(w)
            if f == 0:
                continue
            idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * len(d) / avg))
        out.append(s / max(1, len(d)) ** 0.0)
    return np.array(out)


def select(score, spans, mandatory, budget):
    keep = set(mandatory)
    used = sum(spans[i][1] - spans[i][0] for i in keep)
    for i in np.argsort(-score, kind='stable'):
        i = int(i)
        if i in keep:
            continue
        n = spans[i][1] - spans[i][0]
        if used + n <= budget:
            keep.add(i); used += n
    return keep, used


def main():
    L = load()
    cases = json.load(open(f'{OUT}/cases.json'))
    only = sys.argv[1:]  # optional case ids
    res = []
    for c in cases:
        if only and c['id'] not in only:
            continue
        doc = open(f"{OUT}/doc_{c.get('doc', c['lang'])}.txt").read()
        user_head = '<|im_start|>user\n'
        prompt = user_head + doc + '\n\n' + c['question'] + '<|im_end|>\n<|im_start|>assistant\n'
        ids, X, sec = run_tap(prompt, c['id'])
        S = len(ids)
        pb = [L['pieces'][i] for i in ids]
        offs = np.cumsum([0] + [len(p) for p in pb])
        assert b''.join(pb).decode('utf-8', 'replace').startswith('<|im_start|>user'), b''.join(pb[:5])
        pbytes = prompt.encode()
        def tok_span(bstart, bend):
            a = int(np.searchsorted(offs, bstart, 'right') - 1)
            e = int(np.searchsorted(offs, bend, 'left'))
            return a, e
        qb = pbytes.index(c['question'].encode())
        q_span = tok_span(qb, qb + len(c['question'].encode()))
        u_span = tok_span(len(user_head.encode()), pbytes.index(b'<|im_end|>'))
        ev = c['evidence'].encode()
        ev_spans = []
        start = 0
        while True:
            k = pbytes.find(ev, start, qb)
            if k < 0:
                break
            ev_spans.append(tok_span(k, k + len(ev))); start = k + 1
        text = [p.decode('utf-8', 'replace') for p in pb]
        line_start = np.zeros(S + 1, bool); after_blank = np.zeros(S + 1, bool)
        for t in range(S):
            prev = ''.join(text[max(0, t - 2):t])
            line_start[t] = t == 0 or text[t - 1].endswith('\n')
            after_blank[t] = t == 0 or prev.endswith('\n\n')
        # probes
        P, R, H, blk, eps = L['P'], L['R'], L['H'], L['blk'], L['eps']
        h = gelu_tanh(layernorm(X, P['norm.weight'], P['norm.bias'], 1e-5) @ P['fc1.weight'].T + P['fc1.bias'])
        unit_raw = (h @ P['fc2.weight'].reshape(-1) + P['fc2.bias'].reshape(-1)[0]).astype(np.float32)
        sub_raw = (h @ P['subunit.fc2.weight'].reshape(-1) + P['subunit.fc2.bias'].reshape(-1)[0]).astype(np.float32)
        boundary = smooth(unit_raw, P['conv.weight'].reshape(-1), float(P['conv.bias'].reshape(-1)[0]))
        split = smooth(sub_raw, P['subunit.conv.weight'].reshape(-1), float(P['subunit.conv.bias'].reshape(-1)[0]))
        hr = layernorm(X, R['norm.weight'], R['norm.bias'], 1e-5) @ R['fc1.weight'].T + R['fc1.bias']
        hr = 0.5 * hr * (1 + np.vectorize(math.erf)(hr / math.sqrt(2)))
        req = hr @ R['fc2.weight'].reshape(-1) + R['fc2.bias'].reshape(-1)[0]
        forced = [u_span[0], u_span[1]]
        spans = segments(boundary, split, S, forced, line_start, after_blank)
        # request probe: rank units inside the user message by max logit
        u_units = [i for i, (a, e) in enumerate(spans) if a >= u_span[0] and e <= u_span[1]]
        umax = {i: float(req[spans[i][0]:spans[i][1]].max()) for i in u_units}
        ranked = sorted(u_units, key=lambda i: -umax[i])
        top = ranked[0]
        q_set = set(range(*q_span))
        probe_hit = len(q_set & set(range(*spans[top]))) > 0
        q_rank = next(r for r, i in enumerate(ranked) if q_set & set(range(*spans[i])))
        pin, pin_tok = [], 0
        for i in ranked:
            n = spans[i][1] - spans[i][0]
            if pin_tok + n > 512:
                break
            pin.append(i); pin_tok += n
        # head
        xn = rmsnorm(X, eps) * blk['attn_norm']
        K = (xn @ H['attn_k'].T).reshape(S, 2, 256)
        K = rmsnorm(K, eps) * blk['attn_k_norm']
        def mass_for(qidx):
            Q = (xn[qidx] @ H['attn_q'].T).reshape(len(qidx), 8, 256)
            Q = rmsnorm(Q, eps) * blk['attn_q_norm']
            m = np.zeros(S)
            keymask = np.ones(S, bool); keymask[qidx] = False
            for hh in range(8):
                s = Q[:, hh, :] @ K[:, hh // 4, :].T / 16.0
                s[:, ~keymask] = -1e30
                s = s - s.max(1, keepdims=True)
                p = np.exp(s); p /= p.sum(1, keepdims=True)
                m += p.sum(0)
            return m
        arms = {}
        q_probe = list(range(*spans[top]))[:128]
        q_oracle = list(range(*q_span))
        budget = int(round(keep_ratio(S) * S))
        mandatory = set(i for i, (a, e) in enumerate(spans) if e <= u_span[0] or a >= u_span[1])
        ev_units = [set(i for i, (a, e) in enumerate(spans) if a < es[1] and e > es[0]) for es in ev_spans]
        def kept_ev(keep):
            return any(u <= keep for u in ev_units)
        # release blend (pflash_query_candidates.h, defaults tw_share 0.5, end_share 0.25): probe candidate
        # extent at the largest score gap, today's windows (tail 128 + head 256 of the user message), prompt end.
        nrm = lambda m: m / m.sum()
        sc = [umax[i] for i in ranked]
        gaps = [sc[k] - sc[k + 1] for k in range(len(sc) - 1)]
        cut = int(np.argmax(gaps)) + 1 if gaps else 1
        extent = []
        for i in ranked[:cut]:
            toks = list(range(*spans[i]))
            if len(extent) + len(toks) <= 128:
                extent += toks
        if not extent:
            extent = list(range(*spans[top]))[:128]
        tail = list(range(max(u_span[0], u_span[1] - 128), u_span[1]))
        headw = list(range(u_span[0], min(u_span[1], u_span[0] + 256)))
        m_blend = (0.25 * nrm(mass_for(sorted(extent))) + 0.25 * nrm(mass_for(tail)) + 0.25 * nrm(mass_for(headw))
                   + 0.25 * nrm(mass_for([S - 1])))
        for arm, qidx, mand in (('head_probe', q_probe, mandatory | set(pin) | {top}),
                                 ('release_blend', None, mandatory | set(pin) | {top}),
                                 ('head_oracle', q_oracle, mandatory | {i for i in u_units if set(range(*spans[i])) & q_set})):
            m = m_blend if qidx is None else mass_for(qidx)
            dens = np.array([m[a:e].mean() for a, e in spans])
            keep, used = select(dens, spans, mand, budget)
            order = np.argsort(-dens)
            ranks = [min(int(np.where(order == u)[0][0]) for u in us) for us in ev_units]
            arms[arm] = dict(kept=kept_ev(keep), used=used, ev_unit_rank=min(ranks), n_units=len(spans))
        utext = [''.join(text[a:e]) for a, e in spans]
        b = bm25_scores(utext, c['question'])
        mand_o = mandatory | {i for i in u_units if set(range(*spans[i])) & q_set}
        keep, used = select(b, spans, mand_o, budget)
        arms['bm25'] = dict(kept=kept_ev(keep), used=used)
        rng = np.random.default_rng(0)
        hits = 0
        for _ in range(200):
            keep, _u = select(rng.random(len(spans)), spans, mand_o, budget)
            hits += kept_ev(keep)
        arms['random'] = dict(kept_rate=hits / 200)
        arms['top_unit_text'] = ''.join(text[spans[top][0]:spans[top][1]])[:120]
        arms['extent_has_question'] = bool(set(extent) & q_set)
        row = dict(id=c['id'], lang=c['lang'], S=S, budget=budget, ratio=round(budget / S, 3), n_units=len(spans),
                   mean_unit=round(S / len(spans), 1), probe_top_is_question=probe_hit, question_unit_rank=q_rank,
                   tap_sec=round(sec, 1), arms=arms)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        res.append(row)
    with open(f'{OUT}/results.jsonl', 'a') as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
