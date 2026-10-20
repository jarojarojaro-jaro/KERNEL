#!/usr/bin/env python3
"""fitcalc.py — VRAM and max usable context for a GGUF on one card, from the GGUF header only.

Usage:  fitcalc.py <gguf path | https URL | repo:file> --card 5060ti [--arm T|U1|plain] [--ub 512] [--kv q4_0]
                   [--ctx 131072,204800] [--headroom 512] [--json]
        fitcalc.py --cards            (list card presets)
Reads only the header (HTTP range requests for HF; nothing is downloaded beyond the header).

Model (MiB; calibrated 2026-10-20 on llama-server logs of our fork, see PLAN-NV-V2.md §2):
  loaded(c) = W_gpu + RS + C_main(ub) + c*(kv_main + 10*ub)                       # target context
            + [MTP arm]  C_draft(ub) + c*(kv_mtp + 10*ub)                          # MTP draft context
            + [arm T]    head64k(output type) + emb64k(token_embd type) + 385.2   # reduced draft vocab + iq4_xs requant
            + ovh(card)                                                            # CUDA context, cuBLAS, pools at load
  peak(c, p) = loaded(c) + g*p        g = prompt-length growth (FA f16 K/V conversion pools, graph re-reserve)
  usable ctx = max c with peak(c, p=c) + headroom <= VRAM total
W_gpu = all tensors except token_embd (token_embd stays in host memory: `CPU_Mapped model buffer`).
kv_main = n_full_attn_layers * n_head_kv * (key_len + value_len) * bytes/elem(kv type); kv_mtp the same for nextn layers.
"""
import sys, os, struct, json, argparse, urllib.request, importlib.util

MiB = 1048576.0
BPE = {'q4_0': 18 / 32, 'q8_0': 34 / 32, 'f16': 2.0, 'q5_0': 22 / 32, 'q4_1': 20 / 32}
# ggml type id -> (block elems, block bytes); enough for every type seen in our candidates
QS = {0: (1, 4), 1: (1, 2), 2: (32, 18), 3: (32, 20), 6: (32, 22), 7: (32, 24), 8: (32, 34), 10: (256, 84),
      11: (256, 110), 12: (256, 144), 13: (256, 176), 14: (256, 210), 15: (256, 292), 16: (256, 66), 17: (256, 74),
      18: (256, 98), 19: (256, 50), 20: (32, 18), 21: (256, 110), 22: (256, 82), 23: (256, 136), 29: (256, 56),
      30: (1, 2), 34: (256, 54), 35: (256, 66), 39: (32, 17), 40: (64, 36), 41: (16, 9)}
TNAME = {0: 'F32', 1: 'F16', 2: 'Q4_0', 3: 'Q4_1', 6: 'Q5_0', 7: 'Q5_1', 8: 'Q8_0', 10: 'Q2_K', 11: 'Q3_K', 12: 'Q4_K',
         13: 'Q5_K', 14: 'Q6_K', 15: 'Q8_K', 16: 'IQ2_XXS', 17: 'IQ2_XS', 18: 'IQ3_XXS', 19: 'IQ1_S', 20: 'IQ4_NL',
         21: 'IQ3_S', 22: 'IQ2_S', 23: 'IQ4_XS', 29: 'IQ1_M', 30: 'BF16', 34: 'TQ1_0', 35: 'TQ2_0', 39: 'MXFP4',
         40: 'Q2_0', 41: 'NVFP4'}

# Card presets: total MiB as nvidia-smi reports it; ovh = load overhead (CUDA context, cuBLAS, pools) fitted on the FIRST
# measured point of each card and validated on the others (PLAN-NV-V2.md §2, error <= 16 MiB); g = prompt-length growth
# in bytes/token at ub 512 for planning = upper envelope of measured peaks (central value 14e3, --g 14000).
CARDS = {
    '3060':   dict(total=12288, ovh=174, g=18e3,   bw=360,  note='fit 31-3060-3080.md:35,78; check 27-3090-final.md:187'),
    '3080':   dict(total=10240, ovh=417, g=21.6e3, bw=760,  note='fit 31-3060-3080.md:42,62 (ub 256, IQ1_M via cuBLAS)'),
    '3090':   dict(total=24576, ovh=338, g=18e3,   bw=936,  note='fit 27-3090-final.md:207; check :211,:160, 31-3090.md:44'),
    '4060ti': dict(total=16380, ovh=184, g=18e3,   bw=288,  note='fit 31-4060ti.md:62; check :59-61, 29-4060ti.md:70'),
    '4070ti': dict(total=12282, ovh=266, g=18e3,   bw=504,  note='fit 31-4070ti.md:47; check :44-46'),
    '5060ti': dict(total=16311, ovh=194, g=18e3,   bw=448,  note='fit 31-5060ti.md:66 (single point)'),
    '4090':   dict(total=24564, ovh=480, g=18e3,   bw=1008, note='[SZACUNEK] ovh ~ 120 + 2.8 x SM count, no measurement'),
    '5090':   dict(total=32607, ovh=600, g=18e3,   bw=1792, note='[SZACUNEK] ovh ~ 120 + 2.8 x SM count, no measurement'),
    'xtx':    dict(total=24560, ovh=220, g=None,   bw=960,  note='HIP; static part only (fb-qwen-T-p1.log:1)'),
}
# qwen35 (Qwen3.8-27B) graph constants from llama-server logs (kvdbg.server.log / dbg.T.ckpt.server.log, 2026-10-20)
C_MAIN_512, C_DRAFT_512, RS_27B, REQUANT_27B, CB_PER_TOK_PER_UB = 100.29, 80.28, 252.19, 385.2, 10.0


class Buf:
    def __init__(s, src): s.src = src; s.data = b''; s.local = not src.startswith('http')
    def need(s, n):
        if len(s.data) >= n: return
        want = max(n, 2 * len(s.data), 16 << 20)
        if s.local:
            with open(s.src, 'rb') as f: s.data = f.read(want)
        else:
            req = urllib.request.Request(s.src, headers={'Range': f'bytes=0-{want - 1}'})
            s.data = urllib.request.urlopen(req, timeout=300).read()


def parse(src):
    b = Buf(src); p = [0]
    def rd(n):
        b.need(p[0] + n); v = b.data[p[0]:p[0] + n]; p[0] += n; return v
    u32 = lambda: struct.unpack('<I', rd(4))[0]; u64 = lambda: struct.unpack('<Q', rd(8))[0]
    def s(): return rd(u64()).decode('utf-8', 'replace')
    fmt = {0: 'B', 1: 'b', 2: 'H', 3: 'h', 4: 'I', 5: 'i', 6: 'f', 7: '?', 10: 'Q', 11: 'q', 12: 'd'}
    def val(t):
        if t == 8: return s()
        if t == 9:
            et = u32(); n = u64()
            if et in fmt:
                raw = rd(struct.calcsize('<' + fmt[et]) * n); v = struct.unpack('<' + fmt[et] * n, raw)
                return list(v) if n <= 256 else None
            arr = [val(et) for _ in range(n)]
            return arr if n <= 64 else None
        return struct.unpack('<' + fmt[t], rd(struct.calcsize('<' + fmt[t])))[0]
    assert rd(4) == b'GGUF'; u32(); nt = u64(); nkv = u64()
    kv = {}
    for _ in range(nkv):
        k = s(); kv[k] = val(u32())
    tens = []
    for _ in range(nt):
        name = s(); nd = u32(); dims = [u64() for _ in range(nd)]; t = u32(); u64()
        n = 1
        for d in dims: n *= d
        bs, ts = QS.get(t, (None, None))
        tens.append((name, TNAME.get(t, f'type{t}'), dims, n * ts // bs if bs else None, n))
    return kv, tens


def resolve(src):
    if src.startswith('http') or os.path.exists(os.path.expanduser(src)):
        return os.path.expanduser(src) if not src.startswith('http') else src
    repo, f = src.split(':', 1)
    return f'https://huggingface.co/{repo}/resolve/main/{f}'


def describe(src, file_size=None):
    kv, t = parse(resolve(src))
    arch = kv['general.architecture']; g = lambda k, d=None: kv.get(f'{arch}.{k}', d)
    nb = g('block_count'); nn = g('nextn_predict_layers', 0) or 0
    def li(name):
        try: return int(name.split('.')[1])
        except Exception: return -1
    attn = sorted({li(x[0]) for x in t if x[0].startswith('blk.') and x[0].endswith('attn_k.weight')})
    attn_main = [l for l in attn if l < nb - nn]; attn_mtp = [l for l in attn if l >= nb - nn]
    hk = g('attention.head_count_kv'); hk = hk[attn_main[0]] if isinstance(hk, list) and attn_main else hk
    kl = g('attention.key_length') or (g('embedding_length') // g('attention.head_count'))
    vl = g('attention.value_length') or kl
    unknown = [x for x in t if x[3] is None]
    bytes_all = sum(x[3] or 0 for x in t)
    if unknown and file_size:  # private types (e.g. PrismML PQ2_0/PTQ1_0): attribute the rest of the file to them
        bytes_all = file_size - 0  # header is small vs. weights; documented as an estimate
    emb = next((x for x in t if x[0] == 'token_embd.weight'), None)
    out = next((x for x in t if x[0] == 'output.weight'), None) or emb  # tied head
    bpw = lambda x: 8.0 * x[3] / x[4] if x and x[3] else 4.5
    d = dict(arch=arch, n_layer=nb, nextn=nn, n_attn=len(attn_main), attn_layers=attn_main, n_mtp_attn=len(attn_mtp),
             n_head_kv=hk, key_len=kl, value_len=vl, n_embd=g('embedding_length'), ctx_train=g('context_length'),
             ssm=dict(conv=g('ssm.conv_kernel'), state=g('ssm.state_size'), groups=g('ssm.group_count'),
                      heads=g('ssm.time_step_rank'), inner=g('ssm.inner_size')),
             W_total=bytes_all, unknown_types=sorted({x[1] for x in unknown}),
             token_embd=(emb[1], emb[3]) if emb else None, output=(out[1], out[3]) if out else None,
             W_gpu=bytes_all - (emb[3] or 0 if emb and out is not emb else 0),  # tied head: token_embd must be on GPU
             mtp_bytes=sum(x[3] or 0 for x in t if li(x[0]) >= nb - nn and nn),
             head_bpw=bpw(out), embd_bpw=bpw(emb), vocab=(out[2][1] if out else None))
    # recurrent state per sequence (f32): GDN S = heads * (inner/heads)^2 ... llama.cpp: S = n_v_heads * d_k * d_v
    ss = d['ssm']
    if ss['inner'] and ss['state'] and ss['heads']:
        n_gdn = nb - nn - len(attn_main)
        dv = ss['inner'] // ss['heads']
        S = n_gdn * ss['heads'] * ss['state'] * dv * 4
        R = n_gdn * (ss['conv'] - 1) * (ss['inner'] + 2 * ss['groups'] * ss['state']) * 4
        d['recurrent'] = dict(n_gdn=n_gdn, S_MiB=S / MiB, R_MiB=R / MiB)
    elif arch.startswith('lfm2'):
        d['recurrent'] = dict(n_conv=nb - len(attn_main), note='shortconv state, < 1 MiB')
    return d


def kv_per_tok(d, kvt, mtp=False):
    n = d['n_mtp_attn'] if mtp else d['n_attn']
    return n * d['n_head_kv'] * (d['key_len'] + d['value_len']) * BPE[kvt]


def budget(d, card, arm='T', ub=512, kvt='q4_0', ctx=131072, prompt=None, g=None):
    c = CARDS[card]; prompt = ctx if prompt is None else prompt
    qwen = d['arch'] == 'qwen35'
    rs = RS_27B * (d['recurrent']['S_MiB'] + d['recurrent']['R_MiB']) / 149.6 if qwen and 'recurrent' in d else 1.0
    k = ub / 512.0
    if d['arch'].startswith('lfm2'):  # one log point: 593.09 MiB at ctx 64768, ub 2048 (magnitude-vs-3090 block-0) [SZACUNEK]
        cm, cb = 0.0, 593.09 * (ctx / 64768) * (ub / 2048)
    else:
        cm, cb = C_MAIN_512 * k, ctx * CB_PER_TOK_PER_UB * ub / MiB
    parts = dict(W_gpu=d['W_gpu'] / MiB, RS=rs, C_main=cm, kv_main=ctx * kv_per_tok(d, kvt) / MiB, cb_main=cb)
    has_mtp = d['nextn'] > 0 and arm in ('T', 'U1')
    if has_mtp:
        parts.update(C_draft=C_DRAFT_512 * k, kv_mtp=ctx * kv_per_tok(d, kvt, True) / MiB,
                     cb_draft=ctx * CB_PER_TOK_PER_UB * ub / MiB)
    if has_mtp and arm == 'T':
        parts.update(head64k=65536 * d['n_embd'] * d['head_bpw'] / 8 / MiB,
                     emb64k=65536 * d['n_embd'] * d['embd_bpw'] / 8 / MiB, requant=REQUANT_27B * d['n_embd'] / 5120)
    parts['ovh'] = c['ovh']
    loaded = sum(parts.values())
    gg = c['g'] if g is None else g
    growth = (gg or 0) * prompt / MiB * (1 if has_mtp else 0.5)  # one context instead of two without the draft ctx
    return dict(parts=parts, loaded=loaded, growth=growth, peak=loaded + growth)


def max_ctx(d, card, arm, ub, kvt, headroom, g=None, step=1024):
    tot = CARDS[card]['total']; best = 0
    for c in range(4096, min(d['ctx_train'] or 262144, 262144) + 1, step):
        if budget(d, card, arm, ub, kvt, c, g=g)['peak'] + headroom <= tot: best = c
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gguf', nargs='?'); ap.add_argument('--card'); ap.add_argument('--arm', default='T')
    ap.add_argument('--ub', type=int, default=512); ap.add_argument('--kv', default='q4_0')
    ap.add_argument('--ctx', default='32768,65536,131072,163840,204800'); ap.add_argument('--headroom', type=int, default=512)
    ap.add_argument('--size', type=int, help='file size in bytes (needed for private ggml types)')
    ap.add_argument('--g', type=float, help='prompt growth bytes/token (default: card preset, planning upper envelope)')
    ap.add_argument('--json', action='store_true'); ap.add_argument('--cards', action='store_true')
    a = ap.parse_args()
    if a.cards:
        for k, v in CARDS.items(): print(f'{k:7} {v}')
        return
    d = describe(a.gguf, a.size)
    if a.json and not a.card: print(json.dumps(d, indent=1, default=str)); return
    print(f"{a.gguf}\n arch {d['arch']}, layers {d['n_layer']} (nextn {d['nextn']}), full-attn {d['n_attn']} {d['attn_layers'][:4]}..., "
          f"n_head_kv {d['n_head_kv']}, head_dim {d['key_len']}/{d['value_len']}, ctx_train {d['ctx_train']}")
    print(f" W_gpu {d['W_gpu']/1e9:.3f} GB (token_embd {d['token_embd']} on host), head {d['output'][0] if d['output'] else '-'} "
          f"{d['head_bpw']:.2f} bpw, recurrent {d.get('recurrent')}")
    print(f" KV/token {a.kv}: main {kv_per_tok(d, a.kv):.0f} B, MTP {kv_per_tok(d, a.kv, True):.0f} B")
    if d['unknown_types']: print(f" WARNING private types {d['unknown_types']}: W from --size ({a.size})")
    if not a.card: return
    c = CARDS[a.card]
    print(f" card {a.card}: {c['total']} MiB, ovh {c['ovh']} MiB, growth {a.g or c['g']} B/token ({c['note']}); arm {a.arm}, ub {a.ub}, headroom {a.headroom}")
    print(f" {'ctx':>7} {'loaded':>8} {'+growth':>8} {'peak':>8} {'free':>7}  verdict")
    for cx in [int(x) for x in a.ctx.split(',')]:
        b = budget(d, a.card, a.arm, a.ub, a.kv, cx, g=a.g); free = c['total'] - b['peak']
        print(f" {cx:7d} {b['loaded']:8.0f} {b['growth']:8.0f} {b['peak']:8.0f} {free:7.0f}  {'OK' if free >= a.headroom else 'NO'}")
    b = budget(d, a.card, a.arm, a.ub, a.kv, int(a.ctx.split(',')[-1]), g=a.g)
    print(' parts @%s: ' % a.ctx.split(',')[-1] + ', '.join(f'{k} {v:.0f}' for k, v in b['parts'].items()))
    print(f" max usable ctx (peak after a ctx-long prompt + {a.headroom} MiB): {max_ctx(d, a.card, a.arm, a.ub, a.kv, a.headroom, a.g)}")


if __name__ == '__main__':
    main()
