#!/usr/bin/env python3
"""fitcalc.py — VRAM, max usable context and decode t/s for a GGUF on one card, from the GGUF header only.

Usage:  fitcalc.py <gguf path | https URL | repo:file[,repo:file2 ...]> --card 5060ti [--arm T|U1|plain] [--ub 512]
                   [--kv q4_0] [--ctx 131072,204800] [--headroom 512] [--draft <gguf>] [--n-cpu-moe N] [--ram-bw 70]
                   [--depth 0,65536,131072] [--json]
        fitcalc.py --cards            (list card presets)
Reads only the header (HTTP range requests for HF; nothing is downloaded beyond the header). Split GGUFs: pass all
shards comma-separated (tensors are merged; metadata from the first shard that has it).

Memory model (MiB; calibrated 2026-10-20 on llama-server logs of our fork for qwen35, PLAN-NV-V2.md §2):
  loaded(c) = W_gpu + RS + C_main(ub) + KV(c) + c*10*ub                            # target context
            + [MTP arm]  C_draft(ub) + KV_mtp(c) + c*10*ub                         # MTP draft context (nextn in file)
            + [--draft]  W_draft + C_draft(ub) + KV_draft(c) + c*10*ub             # sidecar drafter (MTP file, DFlash..)
            + [arm T]    head64k(output type) + emb64k(token_embd type) + 385.2   # qwen35 only: reduced draft vocab
            + ovh(card)                                                            # CUDA context, cuBLAS, pools at load
  KV(c)     = sum over full-attention layers  c          * (k_dim + v_dim) * bytes/elem(kv type)
            + sum over SWA layers       min(c, pad256(n_swa + ub)) * (k_dim + v_dim) * bytes/elem    (llama.cpp iSWA)
            k_dim/v_dim per layer from the attn_k / attn_v tensor shapes (no attn_v = V is K, still cached, Gemma 4
            global layers); MLA (attn_kv_a_mqa) caches only the latent (kv_lora_rank + rope dims), no V.
  peak(c, p) = loaded(c) + g_eff*p    g_eff = g(card) * (largest per-layer f16 K+V bytes/token of a full layer) / 4096
            (prompt growth: FA K/V conversion pools; 4096 = qwen35 layer; [SZACUNEK] for other archs)
  usable ctx = max c with peak(c, p=c) + headroom <= VRAM total
  RS (recurrent state, f32): GDN (qwen35/qwen35moe) and Mamba-2 (nemotron_h*) computed from ssm.* keys; x1.686 with an
            MTP/draft arm (rollback snapshots, 252.19 / 149.6 MiB measured on qwen35); LFM2 shortconv < 1 MiB.
  W_gpu     = all tensors except token_embd (host) unless the head is tied; minus experts moved to RAM by --n-cpu-moe.
Decode model (t/s; [SZACUNEK], calibrated on our dense U0 points and LocalMaxxing MoE medians, see 33-modele-na-karty.md):
  t_tok = B_w/(eta(card)*BW) + B_kv/(eta_kv*BW) + B_ram/(eta_ram*BW_ram) + n_moe_layers*tau(card) [+ t_sync per CPU MoE layer]
  B_w   = non-expert weights read per token (all except token_embd, MTP/nextn) + routed experts*k/E on GPU + 2*recurrent
  B_kv  = KV cache at the given depth (eta_kv 0.18: FA decode over quantized KV);  B_ram = experts*k/E kept in RAM.
  Validation (report 33 §1.3): LFM2.5-24B Q5_K_M W_gpu 16233 MiB / KV q8_0 @131k 1360 MiB / 1.78 GB per token = logs.
"""
import sys, os, struct, json, argparse, urllib.request

MiB = 1048576.0
BPE = {'q4_0': 18 / 32, 'q8_0': 34 / 32, 'f16': 2.0, 'bf16': 2.0, 'q5_0': 22 / 32, 'q4_1': 20 / 32}
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
# eta = decode bandwidth efficiency of plain (U0) decode, measured on Qwen3.8-27B (33-modele-na-karty.md §1.3):
#   3090 43.1 t/s x 16.8 GB / 936 = 0.77 (27-3090-final.md:100); 4060 Ti 18.4 x 13.66 / 288 = 0.87 (31-4060ti.md:19);
#   5060 Ti 26.7 x 13.66 / 448 = 0.81 (31-5060ti.md:10); 4070 Ti 40.8 x 9.36 / 504 = 0.76 (31-4070ti.md:11);
#   3060 20.6 x 9.36 / 360 = 0.54 (Q2_K_XL, 31-3060-3080.md:10); 3080 45.7 x 7.0 / 760 = 0.42 (IQ2_XXS, :9);
#   XTX Vulkan 38.6 x 16.8 / 960 = 0.67 (04-wykrywanie:249). 3060/3080 values are for IQ2/Q2 files (slow kernels);
#   for K-quants >= Q4 we use eta_k (planning) = 0.65 [SZACUNEK]. 4090/5090/Mac: [SZACUNEK].
# tau = extra fixed time per MoE layer per decoded token (router, top-k, gather, more small kernels; dense models have
#       tau = 0 because eta was fitted on dense decode), fitted on LocalMaxxing llama.cpp medians (us), see report 33 §1.3.
CARDS = {
    '3060':   dict(total=12288, ovh=174, g=18e3,   bw=360,  eta=0.54, eta_k=0.65, tau=85, note='fit 31-3060-3080.md:35,78; check 27-3090-final.md:187'),
    '3080':   dict(total=10240, ovh=417, g=21.6e3, bw=760,  eta=0.42, eta_k=0.65, tau=85, note='fit 31-3060-3080.md:42,62 (ub 256, IQ1_M via cuBLAS)'),
    '3090':   dict(total=24576, ovh=338, g=18e3,   bw=936,  eta=0.77, eta_k=0.77, tau=85, note='fit 27-3090-final.md:207; check :211,:160, 31-3090.md:44'),
    '4060ti': dict(total=16380, ovh=184, g=18e3,   bw=288,  eta=0.87, eta_k=0.87, tau=65, note='fit 31-4060ti.md:62; check :59-61, 29-4060ti.md:70'),
    '4070ti': dict(total=12282, ovh=266, g=18e3,   bw=504,  eta=0.76, eta_k=0.76, tau=65, note='fit 31-4070ti.md:47; check :44-46'),
    '5060ti': dict(total=16311, ovh=194, g=18e3,   bw=448,  eta=0.81, eta_k=0.81, tau=40, note='fit 31-5060ti.md:66 (single point)'),
    '4090':   dict(total=24564, ovh=480, g=18e3,   bw=1008, eta=0.78, eta_k=0.78, tau=65, note='[SZACUNEK] ovh ~ 120 + 2.8 x SM count, no measurement'),
    '5090':   dict(total=32607, ovh=600, g=18e3,   bw=1792, eta=0.75, eta_k=0.75, tau=70, note='[SZACUNEK] ovh ~ 120 + 2.8 x SM count, no measurement'),
    'xtx':    dict(total=24560, ovh=220, g=18e3,   bw=960,  eta=0.67, eta_k=0.67, tau=60, note='HIP; static part fb-qwen-T-p1.log:1; g assumed = CUDA'),
    # Apple 16 GB: default Metal working set ~ 2/3 of RAM (recommendedMaxWorkingSetSize ~10.7 GiB); `sudo sysctl
    # iogpu.wired_limit_mb=12288` raises it. ovh/g/eta/tau: [SZACUNEK] (no measurement of ours on Apple).
    'mac16':  dict(total=10922, ovh=150, g=18e3,   bw=120,  eta=0.70, eta_k=0.70, tau=80, note='[SZACUNEK] M4 16 GB, 120 GB/s, default GPU working set'),
    'mac16w': dict(total=12288, ovh=150, g=18e3,   bw=153,  eta=0.70, eta_k=0.70, tau=80, note='[SZACUNEK] M5 16 GB, 153 GB/s, wired_limit 12 GiB'),
}
# qwen35 (Qwen3.8-27B) graph constants from llama-server logs (kvdbg.server.log / dbg.T.ckpt.server.log, 2026-10-20)
C_MAIN_512, C_DRAFT_512, RS_27B, REQUANT_27B, CB_PER_TOK_PER_UB = 100.29, 80.28, 252.19, 385.2, 10.0
RS_SPEC = RS_27B / 149.6           # rollback snapshots with a draft arm
G_REF_LAYER = 4096.0               # qwen35 full-attn layer: 4 kv heads x (256 + 256) x 2 B (f16)


class Buf:
    def __init__(s, src): s.src = src; s.data = b''; s.local = not src.startswith('http')
    def need(s, n):
        if len(s.data) >= n: return
        want = max(n, 2 * len(s.data), 16 << 20)
        if s.local:
            with open(s.src, 'rb') as f: s.data = f.read(want)
        else:
            h = {'Range': f'bytes=0-{want - 1}'}
            tok = os.path.expanduser('~/.cache/huggingface/token')
            if 'huggingface.co' in s.src and os.path.exists(tok): h['Authorization'] = 'Bearer ' + open(tok).read().strip()
            s.data = urllib.request.urlopen(urllib.request.Request(s.src, headers=h), timeout=300).read()


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


def load(src):
    """One GGUF or comma-separated shards -> (kv, tensors)."""
    kv, tens = {}, []
    for part in src.split(','):
        k, t = parse(resolve(part.strip()))
        for a, b in k.items(): kv.setdefault(a, b)
        tens += t
    return kv, tens


def li(name):
    try: return int(name.split('.')[1]) if name.startswith('blk.') else -1
    except ValueError: return -1


def describe(src, file_size=None):
    kv, t = load(src)
    arch = kv['general.architecture']; g = lambda k, d=None: kv.get(f'{arch}.{k}', d)
    nb = g('block_count'); nn = g('nextn_predict_layers', 0) or 0
    by = {x[0]: x for x in t}
    is_mtp = lambda l: nn and l >= nb - nn
    # attention layers and per-layer cached K/V widths (elements per token), from tensor shapes
    swa_pat = g('attention.sliding_window_pattern'); n_swa = g('attention.sliding_window') or 0
    layers = []
    for l in sorted({li(x[0]) for x in t if x[0].endswith(('attn_k.weight', 'attn_kv_a_mqa.weight'))}):
        mla = f'blk.{l}.attn_kv_a_mqa.weight' in by
        if mla:
            kd, vd = by[f'blk.{l}.attn_kv_a_mqa.weight'][2][1], 0          # latent (kv_lora_rank + rope) only
        else:
            kd = by[f'blk.{l}.attn_k.weight'][2][1]
            v = by.get(f'blk.{l}.attn_v.weight'); vd = v[2][1] if v else kd  # no attn_v: V = K, still cached
        if isinstance(swa_pat, list): swa = bool(swa_pat[l]) if l < len(swa_pat) else False
        elif arch == 'gpt-oss': swa = l % 2 == 0                            # llama.cpp set_swa_pattern(2)
        else: swa = False
        layers.append(dict(l=l, k=kd, v=vd, swa=swa and n_swa > 0, mtp=bool(is_mtp(l)), mla=mla))
    main = [x for x in layers if not x['mtp']]; mtp = [x for x in layers if x['mtp']]
    unknown = [x for x in t if x[3] is None]
    bytes_all = sum(x[3] or 0 for x in t)
    if unknown and file_size:  # private types (e.g. PrismML PQ2_0/PTQ1_0): attribute the rest of the file to them
        bytes_all = file_size
    emb = by.get('token_embd.weight'); out = by.get('output.weight') or emb  # tied head
    tied = out is emb
    bpw = lambda x: 8.0 * x[3] / x[4] if x and x[3] else 4.5
    exps = [x for x in t if '_exps.' in x[0] and x[0].endswith('.weight') and not is_mtp(li(x[0]))]
    W_exp = sum(x[3] or 0 for x in exps)
    mtp_bytes = sum(x[3] or 0 for x in t if nn and li(x[0]) >= nb - nn)
    n_exp, k_exp = g('expert_count') or 0, g('expert_used_count') or 0
    hk = g('attention.head_count_kv'); kl = g('attention.key_length') or (g('embedding_length') // g('attention.head_count'))
    d = dict(arch=arch, n_layer=nb, nextn=nn, n_attn=len(main), attn_layers=[x['l'] for x in main], n_mtp_attn=len(mtp),
             layers=layers, n_swa=n_swa, n_swa_layers=sum(x['swa'] for x in main), mla=any(x['mla'] for x in main),
             n_head_kv=hk, key_len=kl, value_len=g('attention.value_length') or kl,
             n_embd=g('embedding_length'), ctx_train=g('context_length'),
             ssm=dict(conv=g('ssm.conv_kernel'), state=g('ssm.state_size'), groups=g('ssm.group_count'),
                      heads=g('ssm.time_step_rank'), inner=g('ssm.inner_size')),
             W_total=bytes_all, unknown_types=sorted({x[1] for x in unknown}),
             token_embd=(emb[1], emb[3]) if emb else None, output=(out[1], out[3]) if out else None, tied=tied,
             W_gpu=bytes_all - ((emb[3] or 0) if emb and not tied else 0),  # tied head: token_embd must be on GPU
             mtp_bytes=mtp_bytes, n_exp=n_exp, k_exp=k_exp, W_exp=W_exp,
             W_exp_layer={li(x[0]): 0 for x in exps},
             head_bpw=bpw(out), embd_bpw=bpw(emb), vocab=(out[2][1] if out else None))
    for x in exps: d['W_exp_layer'][li(x[0])] += x[3] or 0
    # recurrent state per sequence (f32)
    ss = d['ssm']; n_attn_all = len(main)
    if ss['inner'] and ss['state'] and ss['heads']:
        dv = ss['inner'] // ss['heads']
        if arch.startswith('nemotron_h'):   # Mamba-2 layers carry ssm_in
            n_rec = len({li(x[0]) for x in t if x[0].endswith('ssm_in.weight')})
        else:                               # GDN: every non-attention, non-MTP block
            n_rec = len({li(x[0]) for x in t if x[0].endswith('ssm_out.weight') and not is_mtp(li(x[0]))})
        S = n_rec * ss['heads'] * ss['state'] * dv * 4
        R = n_rec * (ss['conv'] - 1) * (ss['inner'] + 2 * ss['groups'] * ss['state']) * 4
        d['recurrent'] = dict(n_rec=n_rec, S_MiB=S / MiB, R_MiB=R / MiB)
    elif arch.startswith('lfm2'):
        d['recurrent'] = dict(n_conv=nb - n_attn_all, note='shortconv state, < 1 MiB', S_MiB=0.5, R_MiB=0.0)
    # bytes read per decoded token at depth 0 (weights; KV and recurrent added in decode())
    head = (out[3] or 0) if out else 0
    nonexp = bytes_all - W_exp - mtp_bytes - ((emb[3] or 0) if emb else 0) + (head if tied else 0)
    d['B_dense'] = nonexp; d['B_exp_active'] = W_exp * k_exp / n_exp if n_exp else 0
    return d


def kv_bytes(d, kvt, ctx, ub=512, mtp=False, n_seq=1):
    """KV cache bytes for a context of ctx tokens (iSWA-aware)."""
    b = 0.0
    swa_cells = min(ctx, -(-(d['n_swa'] * n_seq + ub) // 256) * 256) if d['n_swa'] else ctx
    for x in d['layers']:
        if x['mtp'] != mtp: continue
        b += (swa_cells if x['swa'] else ctx) * (x['k'] + x['v']) * BPE[kvt]
    return b


def kv_per_tok(d, kvt, mtp=False):
    """Bytes per token of the layers that grow with context (full attention)."""
    return sum((x['k'] + x['v']) * BPE[kvt] for x in d['layers'] if x['mtp'] == mtp and not x['swa'])


def g_scale(d):
    full = [x for x in d['layers'] if not x['swa'] and not x['mtp']]
    return max(((x['k'] + x['v']) * 2 for x in full), default=G_REF_LAYER) / G_REF_LAYER


def offloaded_bytes(d, n_cpu_moe):
    """Expert bytes of the first n_cpu_moe layers kept in system RAM (llama.cpp --n-cpu-moe N)."""
    return sum(v for l, v in d['W_exp_layer'].items() if 0 <= l < n_cpu_moe) if n_cpu_moe else 0


def rs_mib(d):
    r = d.get('recurrent')
    return (r['S_MiB'] + r['R_MiB']) if r else 0.0


def budget(d, card, arm='T', ub=512, kvt='q4_0', ctx=131072, prompt=None, g=None, draft=None, n_cpu_moe=0):
    c = CARDS[card]; prompt = ctx if prompt is None else prompt
    k = ub / 512.0
    has_mtp = d['nextn'] > 0 and arm in ('T', 'U1')
    spec = has_mtp or draft is not None
    rs = rs_mib(d) * RS_SPEC  # validated value (qwen35 incl. rollback snapshots); conservative for the plain arm
    if d['arch'].startswith('lfm2'):  # one log point (LFM2.5-24B-A2B): 593.09 MiB at ctx 64768, ub 2048 [SZACUNEK]
        cm, cb = 0.0, 593.09 * (ctx / 64768) * (ub / 2048)
    else:
        cm, cb = C_MAIN_512 * k, ctx * CB_PER_TOK_PER_UB * ub / MiB
    off = offloaded_bytes(d, n_cpu_moe)
    parts = dict(W_gpu=(d['W_gpu'] - off) / MiB, RS=rs, C_main=cm, kv_main=kv_bytes(d, kvt, ctx, ub) / MiB, cb_main=cb)
    if has_mtp:
        parts.update(C_draft=C_DRAFT_512 * k, kv_mtp=kv_bytes(d, kvt, ctx, ub, mtp=True) / MiB,
                     cb_draft=ctx * CB_PER_TOK_PER_UB * ub / MiB)
    if draft is not None:  # sidecar drafter: its own weights + context (MTP file: its nextn layer(s))
        parts.update(W_draft=draft['W_gpu'] / MiB, C_draft=C_DRAFT_512 * k,
                     kv_draft=(kv_bytes(draft, kvt, ctx, ub) + kv_bytes(draft, kvt, ctx, ub, mtp=True)) / MiB,
                     cb_draft=ctx * CB_PER_TOK_PER_UB * ub / MiB)
    if has_mtp and arm == 'T' and d['arch'] == 'qwen35':
        parts.update(head64k=65536 * d['n_embd'] * d['head_bpw'] / 8 / MiB,
                     emb64k=65536 * d['n_embd'] * d['embd_bpw'] / 8 / MiB, requant=REQUANT_27B * d['n_embd'] / 5120)
    parts['ovh'] = c['ovh']
    loaded = sum(parts.values())
    gg = (c['g'] if g is None else g) * g_scale(d)
    growth = (gg or 0) * prompt / MiB * (1 if spec else 0.5)  # one context instead of two without the draft ctx
    return dict(parts=parts, loaded=loaded, growth=growth, peak=loaded + growth, offloaded=off)


def max_ctx(d, card, arm, ub, kvt, headroom, g=None, step=1024, draft=None, n_cpu_moe=0):
    tot = CARDS[card]['total']; best = 0
    for c in range(4096, min(d['ctx_train'] or 262144, 262144) + 1, step):
        if budget(d, card, arm, ub, kvt, c, g=g, draft=draft, n_cpu_moe=n_cpu_moe)['peak'] + headroom <= tot: best = c
    return best


def decode(d, card, kvt='q4_0', depth=0, n_cpu_moe=0, ram_bw=70.0, eta_ram=0.7, t_sync_us=30.0, eta=None, eta_kv=0.18):
    """Plain decode t/s (no speculation) at a given context depth. [SZACUNEK]
    eta_kv: FA decode reads the KV cache far below peak bandwidth (quantized K/V dequant, few heads); 0.18 fitted on
    3090 Q4_K_XL tg128 43.1 -> 30.4 t/s at 64k (27-3090-final.md:100,103), 5060 Ti / 5080 / 3060 community depth sweeps."""
    c = CARDS[card]; eta = eta or c['eta_k']
    frac_off = offloaded_bytes(d, n_cpu_moe) / d['W_exp'] if d['W_exp'] else 0.0
    B_exp = d['B_exp_active']
    B_w = d['B_dense'] + B_exp * (1 - frac_off) + 2 * rs_mib(d) * MiB
    B_kv = kv_bytes(d, kvt, depth)
    B_ram = B_exp * frac_off
    t = (B_w / (eta * c['bw'] * 1e9) + B_kv / (eta_kv * c['bw'] * 1e9) + B_ram / (eta_ram * ram_bw * 1e9)
         + len(d['W_exp_layer']) * c['tau'] * 1e-6)
    if n_cpu_moe: t += sum(1 for l in d['W_exp_layer'] if l < n_cpu_moe) * t_sync_us * 1e-6
    return dict(tps=1.0 / t, B_gpu=B_w + B_kv, B_ram=B_ram)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gguf', nargs='?'); ap.add_argument('--card'); ap.add_argument('--arm', default='T')
    ap.add_argument('--ub', type=int, default=512); ap.add_argument('--kv', default='q4_0')
    ap.add_argument('--ctx', default='32768,65536,131072,163840,204800'); ap.add_argument('--headroom', type=int, default=512)
    ap.add_argument('--size', type=int, help='file size in bytes (needed for private ggml types)')
    ap.add_argument('--g', type=float, help='prompt growth bytes/token (default: card preset, planning upper envelope)')
    ap.add_argument('--draft', help='sidecar drafter GGUF (Gemma 4 / Nemotron mtp-*.gguf, DFlash, EAGLE3, small model)')
    ap.add_argument('--n-cpu-moe', type=int, default=0, help='expert tensors of the last N layers in system RAM')
    ap.add_argument('--ram-bw', type=float, default=70.0, help='system RAM GB/s for offloaded experts (70: DDR5-5600 2ch; 45: DDR4-3200 2ch); x eta_ram 0.7')
    ap.add_argument('--depth', default='0,65536,131072', help='context depths for the decode t/s estimate')
    ap.add_argument('--json', action='store_true'); ap.add_argument('--cards', action='store_true')
    a = ap.parse_args()
    if a.cards:
        for k, v in CARDS.items(): print(f'{k:7} {v}')
        return
    d = describe(a.gguf, a.size)
    dr = describe(a.draft) if a.draft else None
    if a.json and not a.card: print(json.dumps({k: v for k, v in d.items() if k != 'layers'}, indent=1, default=str)); return
    print(f"{a.gguf}\n arch {d['arch']}, layers {d['n_layer']} (nextn {d['nextn']}), attn {d['n_attn']} (SWA {d['n_swa_layers']}, "
          f"window {d['n_swa']}{', MLA' if d['mla'] else ''}) {d['attn_layers'][:6]}..., ctx_train {d['ctx_train']}")
    print(f" W_gpu {d['W_gpu']/1e9:.3f} GB (token_embd {d['token_embd']} {'on GPU: tied head' if d['tied'] else 'on host'}), "
          f"head {d['output'][0] if d['output'] else '-'} {d['head_bpw']:.2f} bpw, recurrent {d.get('recurrent')}")
    if d['n_exp']:
        print(f" MoE {d['k_exp']}/{d['n_exp']}: experts {d['W_exp']/1e9:.2f} GB, active bytes/token {(d['B_dense'] + d['B_exp_active'])/1e9:.2f} GB"
              f" (dense {d['B_dense']/1e9:.2f} + experts {d['B_exp_active']/1e9:.2f})")
    else:
        print(f" dense: bytes/token {d['B_dense']/1e9:.2f} GB")
    print(f" KV {a.kv}: full layers {kv_per_tok(d, a.kv):.0f} B/token, SWA part {(kv_bytes(d, a.kv, 262144) - 262144 * kv_per_tok(d, a.kv)) / MiB:.0f} MiB fixed, "
          f"MTP {kv_per_tok(d, a.kv, True):.0f} B/token; prompt growth scale {g_scale(d):.2f}")
    if d['unknown_types']: print(f" WARNING private types {d['unknown_types']}: W from --size ({a.size})")
    if not a.card: return
    c = CARDS[a.card]
    print(f" card {a.card}: {c['total']} MiB, ovh {c['ovh']} MiB, growth {a.g or c['g']} B/token ({c['note']}); arm {a.arm}, ub {a.ub}, "
          f"headroom {a.headroom}{', draft ' + a.draft if a.draft else ''}{', n_cpu_moe %d' % a.n_cpu_moe if a.n_cpu_moe else ''}")
    print(f" {'ctx':>7} {'loaded':>8} {'+growth':>8} {'peak':>8} {'free':>7}  verdict")
    for cx in [int(x) for x in a.ctx.split(',')]:
        b = budget(d, a.card, a.arm, a.ub, a.kv, cx, g=a.g, draft=dr, n_cpu_moe=a.n_cpu_moe); free = c['total'] - b['peak']
        print(f" {cx:7d} {b['loaded']:8.0f} {b['growth']:8.0f} {b['peak']:8.0f} {free:7.0f}  {'OK' if free >= a.headroom else 'NO'}")
    b = budget(d, a.card, a.arm, a.ub, a.kv, int(a.ctx.split(',')[-1]), g=a.g, draft=dr, n_cpu_moe=a.n_cpu_moe)
    print(' parts @%s: ' % a.ctx.split(',')[-1] + ', '.join(f'{k} {v:.0f}' for k, v in b['parts'].items())
          + (f"; experts in RAM {b['offloaded']/1e9:.2f} GB" if a.n_cpu_moe else ''))
    print(f" max usable ctx (peak after a ctx-long prompt + {a.headroom} MiB): "
          f"{max_ctx(d, a.card, a.arm, a.ub, a.kv, a.headroom, a.g, draft=dr, n_cpu_moe=a.n_cpu_moe)}")
    for dp in [int(x) for x in a.depth.split(',')]:
        r = decode(d, a.card, a.kv, dp, a.n_cpu_moe, a.ram_bw)
        print(f" plain decode @depth {dp}: ~{r['tps']:.0f} t/s [SZACUNEK] (GPU {r['B_gpu']/1e9:.2f} GB/token, RAM {r['B_ram']/1e9:.2f} GB/token)")


if __name__ == '__main__':
    main()
