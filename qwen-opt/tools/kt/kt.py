#!/usr/bin/env python3
"""Kernel Tuner scaffolding for the hot decode kernels of the amd-opt fork on gfx1100 (RX 7900 XTX).

Kernels (harness sources next to this file, compiled from the ~/wt/tools6 tree = amd-opt + MMVQ_TUNE_NWARPS_N1 hook):
  mmvq_n1      mul_mat_vec_q<T, 1, ..., n1_rows>            dense one-token MUL_MAT, T = Q4_K Q5_K Q6_K Q8_0
  moe_gate_up  mul_mat_vec_q<T, 1, fusion, ..., n1_rows>    LFM MoE up + gate (SWIGLU) + q8_1 out (GGML_HIP_GATE_UP_Q8)
  moe_down     mul_mat_vec_q_moe_down_reduce<T, n_used, rpb> LFM MoE down + weighting + residual (GGML_HIP_MOE_DOWN_REDUCE)
  gdn          gated_delta_net_cuda<128, .., l2_qk, lag, cpw>  Qwen GDN decode (plain) and MTP verify (lag replay)

  kt.py shapes  [--json F]                 problem shapes read from the GGUFs (CPU, gguf-py, mmap)
  kt.py space   [--kernel K]               search spaces, production configs, variant count
  kt.py compile [--kernel K] [--all|--prod] [-j 4]   offline gfx1100 builds (CPU) + VGPR/SGPR/LDS/scratch/occupancy
  kt.py fake    [--kernel K]               fake data: generators, numpy references and the verify functions (CPU)
  kt.py stub    [--kernel K]               Kernel Tuner C stub source (also compiled with g++ as a check)
  kt.py table   --results F | --fake       per-shape table (JSON + C include) from tuning results
  kt.py tune    [--kernel K] [--shape I]   ON THE GPU: Kernel Tuner run (re-execs itself under the GPU locks)

Nothing but `tune` touches the GPU: `compile` only runs clang, `fake`/`table` are numpy, `stub` runs g++.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import os
import re
import subprocess
import sys

HOME = os.path.expanduser("~")
KT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("KT_SRC", os.path.join(HOME, "wt", "tools6"))       # ggml tree with the tuning hook
BUILD = os.environ.get("KT_BUILD", os.path.join(KT_DIR, "build"))
GGML_LIB = os.environ.get("KT_GGML_LIB", os.path.join(HOME, "llama-opt", "lib"))
ROCM_LIB = "/opt/rocm/core-10.0/lib"
CLANG = "/opt/rocm/core-10.0/lib/llvm/bin/clang++"
ARCH = "gfx1100"
MODELS = {
    "qwen": os.path.join(HOME, "models", "Qwen3.8-27B-UD-Q4_K_XL.gguf"),
    "lfm": os.path.join(HOME, "models", "lfm", "LFM2.5-24B-A2B-Q5_K_M.gguf"),
    "lfm-unc": os.path.join(HOME, "models", "lfm", "LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf"),
}
GPU_WRAP = ["flock", "/tmp/gpu.lock", "flock", "/tmp/quiet.lock"]
USER_SERVER = "llama-server.*--port 8080"

sys.path.insert(0, os.path.join(SRC, "gguf-py"))

# ggml_type ids and block geometry (ggml.h, ggml-common.h)
TYPES = {"Q8_0": dict(id=8, qk=32, bs=34), "Q4_K": dict(id=12, qk=256, bs=144),
         "Q5_K": dict(id=13, qk=256, bs=176), "Q6_K": dict(id=14, qk=256, bs=210)}
QK8_1, Q8_1_BS, ROW_PAD = 32, 36, 512

# production RDNA3 values at amd-opt c36fd2c87 (mmvq.cu calc_nwarps / GGML_HIP_MMVQ_N1_ROWS / MMVQ_MOE_DOWN_RPB,
# gated_delta_net.cu gdn_cols_per_warp and the num_warps loop)
PROD_NWARPS_N1 = {"Q8_0": 8, "Q6_K": 2, "Q4_K": 1, "Q5_K": 1}
NSM = 96  # multiProcessorCount of the RX 7900 XTX as HIP reports it [INFERENCE: not probed, the GPU is off limits]

SPACE = {
    "mmvq_n1":     dict(NWARPS=[1, 2, 4, 8], ROWS=[1, 2, 4]),
    "moe_gate_up": dict(NWARPS=[1, 2, 4, 8], ROWS=[1, 2, 4]),
    "moe_down":    dict(NWARPS=[1, 2, 4, 8], ROWS=[1, 2, 4]),
    "gdn":         dict(CPW=[1, 2, 4, 8, 16], NUM_WARPS=[1, 2, 4]),
}
# which tunables keep the result bitwise identical to the production config (the others are checked with a tolerance)
BITWISE_KNOBS = {"mmvq_n1": {"ROWS"}, "moe_gate_up": {"ROWS"}, "moe_down": {"ROWS"}, "gdn": {"NUM_WARPS"}}
KERNELS = list(SPACE)


def prod_config(kernel, p):
    if kernel == "gdn":
        nw = 4
        while nw > 1 and p["H"] * (128 // (4 * nw)) < NSM:
            nw //= 2
        return dict(CPW=4, NUM_WARPS=nw)
    rows = 1 if kernel == "moe_down" else (2 if p["nrows"] % 2 == 0 else 1)
    return dict(NWARPS=PROD_NWARPS_N1[p["type"]], ROWS=rows)


def valid(kernel, p, cfg):
    if kernel == "gdn":
        # lanes_per_col = 32/CPW lanes per state column (CPW divides 32), the block covers CPW*NUM_WARPS columns
        return 32 % cfg["CPW"] == 0 and 128 % (cfg["CPW"] * cfg["NUM_WARPS"]) == 0
    if p["nrows"] % cfg["ROWS"]:
        return False
    if kernel == "moe_gate_up" and p.get("with_q8") and 32 % cfg["ROWS"]:
        return False
    return True


def configs(kernel, p=None):
    keys = list(SPACE[kernel])
    out = [{}]
    for k in keys:
        out = [dict(c, **{k: v}) for c in out for v in SPACE[kernel][k]]
    return [c for c in out if p is None or valid(kernel, p, c)]


# ---------------------------------------------------------------------------------------------------------------
# shapes
# ---------------------------------------------------------------------------------------------------------------
def read_shapes():
    import gguf
    probs = {k: [] for k in KERNELS}
    seen = {}
    for model, path in MODELS.items():
        if not os.path.exists(path):
            continue
        r = gguf.GGUFReader(path)
        kv = {}
        for k, f in r.fields.items():
            try:
                kv[k] = f.contents()
            except Exception:
                pass
        arch = kv.get("general.architecture")
        has_output = any(t.name == "output.weight" for t in r.tensors)
        for t in r.tensors:
            ty = t.tensor_type.name
            shape = [int(x) for x in t.shape]
            base = t.name.split(".", 2)[-1] if t.name.startswith("blk.") else t.name
            if ty not in TYPES:
                continue
            if len(shape) == 2 and base.endswith(".weight") and (base != "token_embd.weight" or not has_output):
                if base.startswith(("ssm_alpha", "ssm_beta")):
                    kern_note = "gdn_ab (fused GDN alpha/beta MMVQ)"
                elif base.startswith("shortconv.in_proj"):
                    kern_note = "mmvq_conv (GGML_HIP_INPROJ_CONV)"
                elif base.startswith(("ffn_gate.", "ffn_up.")):
                    kern_note = "dense gate/up GLU fusion"
                else:
                    kern_note = ""
                key = ("mmvq_n1", ty, shape[1], shape[0])
                name = "output (tied token_embd)" if base == "token_embd.weight" else base
                if key not in seen:
                    seen[key] = dict(kernel="mmvq_n1", type=ty, nrows=shape[1], ncols=shape[0], uses=[], counts={},
                                     note=kern_note)
                    probs["mmvq_n1"].append(seen[key])
                # weight matrices per token and model (a fused gate/up launch reads two)
                seen[key]["counts"][model] = seen[key]["counts"].get(model, 0) + 1
                u = f"{model}:{name}"
                if u not in seen[key]["uses"]:
                    seen[key]["uses"].append(u)
            elif len(shape) == 3 and base.startswith(("ffn_gate_exps", "ffn_up_exps", "ffn_down_exps")):
                n_used = int(kv.get(f"{arch}.expert_used_count", 0))
                kernel = "moe_down" if base.startswith("ffn_down") else "moe_gate_up"
                key = (kernel, ty, shape[1], shape[0], shape[2], n_used)
                if key not in seen:
                    seen[key] = dict(kernel=kernel, type=ty, nrows=shape[1], ncols=shape[0], n_expert=shape[2],
                                     n_used=n_used, uses=[], counts={})
                    if kernel == "moe_gate_up":
                        seen[key]["with_q8"] = 1
                    probs[kernel].append(seen[key])
                if kernel == "moe_down" or base.startswith("ffn_up"):  # launches per token (gate+up: one launch)
                    seen[key]["counts"][model] = seen[key]["counts"].get(model, 0) + 1
                u = f"{model}:{base}"
                if u not in seen[key]["uses"]:
                    seen[key]["uses"].append(u)
        if arch == "qwen35":
            S_v = int(kv["qwen35.ssm.state_size"])
            H = int(kv["qwen35.ssm.time_step_rank"])
            Hk = int(kv["qwen35.ssm.group_count"])
            n_gdn = sum(1 for t in r.tensors if t.name.endswith("ssm_a"))
            assert S_v == 128, "the harness instantiates S_v = 128"
            for mode, nt, lag, K, n_pend in (("decode", 1, 0, 1, 0), ("mtp_verify_n4", 5, 1, 5, 2)):
                key = ("gdn", model, mode)
                if key not in seen:
                    seen[key] = dict(kernel="gdn", mode=mode, S_v=S_v, H=H, Hk=Hk, n_tokens=nt, lag=lag, K=K,
                                     n_pend=n_pend, counts={model: n_gdn},
                                     uses=[f"{model}:GATED_DELTA_NET" + ("_LAG" if lag else "")])
                    probs["gdn"].append(seen[key])
    for k in probs:
        probs[k].sort(key=lambda p: (p.get("type", ""), p.get("nrows", 0), p.get("ncols", 0), p.get("mode", "")))
        for i, p in enumerate(probs[k]):
            p["id"] = i
    return probs


def load_shapes(path=None):
    path = path or os.path.join(KT_DIR, "shapes.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    probs = read_shapes()
    with open(path, "w") as f:
        json.dump(probs, f, indent=1)
    return probs


def cmd_shapes(a):
    probs = read_shapes()
    path = a.json or os.path.join(KT_DIR, "shapes.json")
    with open(path, "w") as f:
        json.dump(probs, f, indent=1)
    for k, ps in probs.items():
        print(f"== {k}: {len(ps)} shapes")
        for p in ps:
            cnt = " ".join(f"{m}:{n}" for m, n in p["counts"].items())
            if k == "gdn":
                print(f"  [{p['id']:2d}] {p['mode']:14s} S_v {p['S_v']} H {p['H']} Hk {p['Hk']} n_tokens {p['n_tokens']} "
                      f"lag {p['lag']} K {p['K']} n_pend {p['n_pend']}  per token {cnt}  prod {prod_config(k, p)}")
            else:
                extra = f" E {p['n_expert']} used {p['n_used']}" if "n_expert" in p else ""
                print(f"  [{p['id']:2d}] {p['type']} rows {p['nrows']:6d} K {p['ncols']:5d}{extra}  per token {cnt:22s} "
                      f"prod {prod_config(k, p)}  {p.get('note', '')}  {','.join(p['uses'])[:90]}")
    print(f"wrote {path}")


def cmd_space(a):
    probs = load_shapes()
    for k in ([a.kernel] if a.kernel else KERNELS):
        nvar = len(variant_list(k))
        print(f"== {k}: {SPACE[k]}  ({len(configs(k))} configs, {nvar} compiled variants; bitwise knobs: "
              f"{sorted(BITWISE_KNOBS[k])})")
        for p in probs[k]:
            print(f"  shape {p['id']}: {len(configs(k, p))} valid configs, production {prod_config(k, p)}")


# ---------------------------------------------------------------------------------------------------------------
# offline builds
# ---------------------------------------------------------------------------------------------------------------
def variant_list(kernel):
    """(name, source, defines) of the shared objects a kernel's search space needs (runtime knobs excluded)."""
    if kernel == "gdn":
        return [(f"gdn_cpw{c}", "gdn_kt.hip", {"KT_CPW": c}) for c in SPACE["gdn"]["CPW"]]
    types = sorted({p["type"] for p in load_shapes()[kernel]}) or list(TYPES)
    return [(f"mmvq_{t}_nw{nw}_r{r}", "mmvq_kt.hip",
             {"KT_TYPE": f"GGML_TYPE_{t}", "MMVQ_TUNE_NWARPS_N1": nw, "KT_ROWS": r})
            for t in types for nw in SPACE[kernel]["NWARPS"] for r in SPACE[kernel]["ROWS"]]


def hip_cmd(src, out, defines, shared_libs=True):
    cmd = [CLANG, "-x", "hip", "-DGGML_USE_HIP", "-D__HIP_PLATFORM_AMD__=1", "-DNDEBUG", "-O3", "-std=gnu++17",
           f"--offload-arch={ARCH}", "-fPIC", "-shared", "-I", os.path.join(SRC, "ggml", "src"),
           "-I", os.path.join(SRC, "ggml", "include"), "-Rpass-analysis=kernel-resource-usage"]
    cmd += [f"-D{k}={v}" for k, v in defines.items()]
    cmd += [src, "-o", out, f"-L{ROCM_LIB}", "-lamdhip64"]
    if shared_libs:
        cmd += [f"-L{BUILD}", "-lkt_mem", f"-L{GGML_LIB}", "-lggml-hip", "-lggml-base",
                f"-Wl,-rpath,{BUILD}:{GGML_LIB}:{ROCM_LIB}"]
    return cmd


def src_rev():
    r = subprocess.run(["git", "-C", SRC, "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip()


def parse_resources(stderr):
    """-Rpass-analysis=kernel-resource-usage remarks -> {mangled kernel: {VGPRs, SGPRs, scratch, occupancy, lds}}."""
    res, cur = {}, None
    for line in stderr.splitlines():
        m = re.search(r"remark: Function Name: (\S+)", line)
        if m:
            cur = res.setdefault(m.group(1), {})
            continue
        m = re.search(r"remark:\s+(TotalSGPRs|VGPRs|AGPRs|ScratchSize \[bytes/lane\]|Occupancy \[waves/SIMD\]|"
                      r"SGPRs Spill|VGPRs Spill|LDS Size \[bytes/block\]): (\d+)", line)
        if m and cur is not None:
            key = {"TotalSGPRs": "sgpr", "VGPRs": "vgpr", "AGPRs": "agpr", "ScratchSize [bytes/lane]": "scratch",
                   "Occupancy [waves/SIMD]": "occupancy", "SGPRs Spill": "sgpr_spill", "VGPRs Spill": "vgpr_spill",
                   "LDS Size [bytes/block]": "lds"}[m.group(1)]
            cur[key] = int(m.group(2))
    return res


def harness_kernels(name, res):
    """The kernels a variant's entry points launch (mangled-name patterns of the harness instantiations)."""
    if name.startswith("gdn"):
        c = re.search(r"cpw(\d+)", name).group(1)
        pats = {f"gdn lag{lag}": rf"gated_delta_net_cudaILi128ELb0ELb0ELb1ELb{lag}ELi{c}E" for lag in (0, 1)}
    else:
        t, nw, r = re.match(r"mmvq_(\w+?)_nw(\d+)_r(\d+)", name).groups()
        tid = TYPES[t]["id"]
        n1 = 0 if r == "1" else r
        pats = {"mmvq_n1": rf"mul_mat_vec_qIL9ggml_type{tid}ELi1ELb0ELb0ELb0ELb0ELi{n1}E",
                "moe_gate_up": rf"mul_mat_vec_qIL9ggml_type{tid}ELi1ELb1ELb0ELb0ELb0ELi{n1}E",
                "moe_down": rf"mul_mat_vec_q_moe_down_reduceIL9ggml_type{tid}ELi4ELi{r}E"}
    out = {}
    for label, pat in pats.items():
        hits = [v for k, v in res.items() if re.search(pat, k)]
        if hits:
            out[label] = hits[0]
    return out


def build_one(name, src, defines, force=False):
    os.makedirs(BUILD, exist_ok=True)
    out = os.path.join(BUILD, name + ".so")
    side = os.path.join(BUILD, name + ".json")
    with open(os.path.join(KT_DIR, src), "rb") as f:
        key = hashlib.sha1(f.read() + src_rev().encode() + json.dumps(defines, sort_keys=True).encode()).hexdigest()
    if not force and os.path.exists(out) and os.path.exists(side):
        with open(side) as f:
            if json.load(f).get("key") == key:
                return name, "cached", json.load(open(side))["kernels"]
    cmd = ["flock", "-s", "/tmp/quiet.lock", "nice", "-n", "10"] + hip_cmd(os.path.join(KT_DIR, src), out, defines)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        errs = "\n".join(l for l in r.stderr.splitlines() if "error" in l)[:2000]
        return name, "FAILED", errs
    kernels = harness_kernels(name, parse_resources(r.stderr))
    with open(side, "w") as f:
        json.dump(dict(key=key, defines=defines, src_rev=src_rev(), arch=ARCH, kernels=kernels), f, indent=1)
    return name, "built", kernels


def build_mem():
    os.makedirs(BUILD, exist_ok=True)
    out = os.path.join(BUILD, "libkt_mem.so")
    src = os.path.join(KT_DIR, "kt_mem.hip")
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(src):
        return
    cmd = ["flock", "-s", "/tmp/quiet.lock", "nice", "-n", "10"] + hip_cmd(src, out, {}, shared_libs=False)
    subprocess.run(cmd, check=True, capture_output=True)


def cmd_compile(a):
    build_mem()
    todo = []
    for k in ([a.kernel] if a.kernel else KERNELS):
        vs = variant_list(k)
        if a.prod or not a.all:
            # production configs of the kernel plus one non-production config: a compile check
            want = set()
            for p in load_shapes()[k]:
                pc = prod_config(k, p)
                want.add(variant_name(k, p, pc))
                alt = next(c for c in configs(k, p) if c != pc)
                if not a.prod:
                    want.add(variant_name(k, p, alt))
            vs = [v for v in vs if v[0] in want]
        todo += [v for v in vs if v not in todo]
    print(f"compiling {len(todo)} variants for {ARCH} with -j{a.j} (src {SRC} @ {src_rev()[:9]})", flush=True)
    rows = []
    with cf.ThreadPoolExecutor(max_workers=min(a.j, 4)) as ex:
        for name, status, info in ex.map(lambda v: build_one(*v, force=a.force), todo):
            if status == "FAILED":
                print(f"  {name}: FAILED\n{info}")
                rows.append((name, status, {}))
                continue
            print(f"  {name}: {status}")
            rows.append((name, status, info))
    print("\n| variant | kernel | VGPRs | SGPRs | scratch B/lane | LDS B/block | occupancy waves/SIMD |")
    print("|---|---|---|---|---|---|---|")
    for name, status, info in rows:
        for label, r in sorted(info.items()):
            print(f"| {name} | {label} | {r.get('vgpr')} | {r.get('sgpr')} | {r.get('scratch')} | {r.get('lds')} | "
                  f"{r.get('occupancy')} |")
    if any(s == "FAILED" for _, s, _ in rows):
        sys.exit(1)


def variant_name(kernel, p, cfg):
    if kernel == "gdn":
        return f"gdn_cpw{cfg['CPW']}"
    return f"mmvq_{p['type']}_nw{cfg['NWARPS']}_r{cfg['ROWS']}"


def asm_body(text, sym):
    """Normalized gfx1100 assembly of one kernel (block labels renumbered, comments dropped)."""
    out, on = [], False
    for line in text.splitlines():
        if line.startswith(sym + ":"):
            on = True
        if on:
            if line.startswith(".Lfunc_end"):
                break
            code = line.split(";")[0].rstrip()
            if code.strip():
                out.append(re.sub(r"BB\d+_", "BB_", code))
    return out


def cmd_isacheck(a):
    """The harness kernels at the production configuration vs the production translation units: same ISA (CPU only,
    device-only clang -S of both)."""
    import tempfile
    cases = [  # (production source, harness source, defines, kernel symbol regex)
        ("mmvq.cu", "mmvq_kt.hip", {"KT_TYPE": "GGML_TYPE_Q5_K", "MMVQ_TUNE_NWARPS_N1": 1, "KT_ROWS": 2},
         r"_ZL13mul_mat_vec_qIL9ggml_type13ELi1ELb[01]ELb0ELb0ELb0ELi2E\S*"),
        ("mmvq.cu", "mmvq_kt.hip", {"KT_TYPE": "GGML_TYPE_Q5_K", "MMVQ_TUNE_NWARPS_N1": 1, "KT_ROWS": 1},
         r"_ZL\d+mul_mat_vec_q_moe_down_reduceIL9ggml_type13ELi[2468]ELi1E\S*"),
        ("gated_delta_net.cu", "gdn_kt.hip", {"KT_CPW": 4},
         r"_Z20gated_delta_net_cudaILi128ELb0ELb0ELb1ELb[01]ELi4E\S*"),
    ]
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        def asm(src, defines, name):
            out = os.path.join(d, name + ".s")
            cmd = ["flock", "-s", "/tmp/quiet.lock", "nice", "-n", "10", CLANG, "-x", "hip", "-DGGML_USE_HIP",
                   "-D__HIP_PLATFORM_AMD__=1", "-DNDEBUG", "-O3", "-std=gnu++17", f"--offload-arch={ARCH}",
                   "--cuda-device-only", "-S", "-I", os.path.join(SRC, "ggml", "src"),
                   "-I", os.path.join(SRC, "ggml", "include")] + [f"-D{k}={v}" for k, v in defines.items()] + [src, "-o", out]
            subprocess.run(cmd, check=True, capture_output=True)
            with open(out) as f:
                return f.read()
        jobs = {}
        with cf.ThreadPoolExecutor(max_workers=min(a.j, 4)) as ex:
            for i, (prod, harness, defs, _) in enumerate(cases):
                jobs[("p", prod)] = jobs.get(("p", prod)) or ex.submit(
                    asm, os.path.join(SRC, "ggml", "src", "ggml-cuda", prod), {}, "prod_" + prod)
                jobs[("h", i)] = ex.submit(asm, os.path.join(KT_DIR, harness), defs, f"kt_{i}")
            texts = {k: f.result() for k, f in jobs.items()}
        for i, (prod, harness, defs, pat) in enumerate(cases):
            syms = sorted(set(re.findall(r"^(" + pat + r"):", texts[("p", prod)], re.M)))
            for s in syms:
                x, y = asm_body(texts[("p", prod)], s), asm_body(texts[("h", i)], s)
                same = bool(x) and x == y
                bad += not same
                print(f"{'IDENTICAL' if same else 'DIFFERENT'}  {len(x):5d} lines  {harness} {defs}  {s[:70]}")
    print(f"src {SRC} @ {src_rev()[:9]}: " + ("all identical" if not bad else f"{bad} kernels differ"))
    sys.exit(1 if bad else 0)


# ---------------------------------------------------------------------------------------------------------------
# data, references, verification (numpy)
# ---------------------------------------------------------------------------------------------------------------
def np_():
    import numpy as np
    return np


def gen_weights(rng, ty, nrows, ncols):
    """Random but valid quant blocks: random quant bytes, normal (not subnormal) positive fp16 scales chosen so that
    |w| stays below ~0.25 as in real weights (dot products O(1), no fp16 overflow in the q8_1 copies)."""
    np = np_()
    t = TYPES[ty]
    nb = ncols // t["qk"]
    raw = rng.integers(0, 256, size=(nrows, nb, t["bs"]), dtype=np.uint8)

    def f16(lo, hi):
        return rng.uniform(lo, hi, size=(nrows, nb)).astype(np.float16).view(np.uint8).reshape(nrows, nb, 2)
    if ty == "Q8_0":
        raw[..., 0:2] = f16(1e-4, 1e-3)        # d * q, |q| <= 127
    elif ty in ("Q4_K", "Q5_K"):
        raw[..., 0:2] = f16(1e-4, 3e-4)        # d * sc * q, sc <= 63, q <= 15 / 31
        raw[..., 2:4] = f16(1e-4, 2e-4)        # dmin * m, m <= 63
    elif ty == "Q6_K":
        raw[..., 208:210] = f16(6.2e-5, 1e-4)  # d * sc * q, |sc| <= 128, |q| <= 32
    return raw.reshape(nrows, nb * t["bs"])


def dequant(raw, ty):
    import gguf
    return gguf.quants.dequantize(raw, gguf.GGMLQuantizationType[ty]).astype(np_().float64)


def gen_q8_1(rng, ncols, nvec=1):
    """block_q8_1 rows (half d, half s, int8 qs[32]), padded to 512 columns. d = 2^-e and |q| <= 63, so s = d*sum(q)
    is exact in fp16 and the kernels' K-quant min term (which uses s) equals the dequantized dot product exactly."""
    np = np_()
    npad = (ncols + ROW_PAD - 1) // ROW_PAD * ROW_PAD
    nb = npad // QK8_1
    q = rng.integers(-63, 64, size=(nvec, nb, QK8_1)).astype(np.int8)
    q[:, ncols // QK8_1:, :] = 0
    d = np.exp2(-rng.integers(6, 10, size=(nvec, nb))).astype(np.float64)
    s = d * q.astype(np.int64).sum(axis=2)
    blk = np.zeros((nvec, nb, Q8_1_BS), dtype=np.uint8)
    blk[..., 0:2] = d.astype(np.float16).view(np.uint8).reshape(nvec, nb, 2)
    blk[..., 2:4] = s.astype(np.float16).view(np.uint8).reshape(nvec, nb, 2)
    blk[..., 4:] = q.view(np.uint8)
    y = (q.astype(np.float64) * d[..., None]).reshape(nvec, npad)[:, :ncols]
    assert np.all(s.astype(np.float16).astype(np.float64) == s), "s not exact in fp16"
    return blk.reshape(nvec, nb * Q8_1_BS), y


def silu(x):
    np = np_()
    return x / (1.0 + np.exp(-x))


def make_problem(kernel, p, seed=0, rows=None):
    """Host arrays (Kernel Tuner argument order of the stub), the reference outputs and tolerances."""
    np = np_()
    rng = np.random.default_rng(seed)
    p = dict(p)
    if rows:  # shrink for quick CPU checks (keeps K, n_expert)
        if kernel == "gdn":
            p["H"] = min(p["H"], rows)
            p["Hk"] = min(p["Hk"], p["H"])
        else:
            p["nrows"] = min(p["nrows"], rows)
    if kernel == "mmvq_n1":
        w = gen_weights(rng, p["type"], p["nrows"], p["ncols"])
        yb, y = gen_q8_1(rng, p["ncols"])
        W = dequant(w, p["type"])
        ref = W @ y[0]
        scale = np.abs(W) @ np.abs(y[0])
        dst = np.zeros(p["nrows"], np.float32)
        args = [w.reshape(-1), yb.reshape(-1), dst, np.int32(p["nrows"]), np.int32(p["ncols"]), np.int32(20),
                np.int32(256)]
        return p, args, {2: (ref, 2e-4 * scale + 1e-6)}
    if kernel == "moe_gate_up":
        E, U, N, K = p["n_expert"], p["n_used"], p["nrows"], p["ncols"]
        wu = gen_weights(rng, p["type"], E * N, K)
        wg = gen_weights(rng, p["type"], E * N, K)
        yb, y = gen_q8_1(rng, K)
        ids = rng.choice(E, size=U, replace=False).astype(np.int32)
        up = np.stack([dequant(wu[e * N:(e + 1) * N], p["type"]) @ y[0] for e in ids], axis=0)          # [U, N]
        gate = np.stack([dequant(wg[e * N:(e + 1) * N], p["type"]) @ y[0] for e in ids], axis=0)
        sc_u = np.stack([np.abs(dequant(wu[e * N:(e + 1) * N], p["type"])) @ np.abs(y[0]) for e in ids], axis=0)
        sc_g = np.stack([np.abs(dequant(wg[e * N:(e + 1) * N], p["type"])) @ np.abs(y[0]) for e in ids], axis=0)
        ref = (up * silu(gate)).reshape(-1)
        tol = (2e-4 * sc_u * np.abs(silu(gate)) + np.abs(up) * 2e-4 * sc_g * 1.1 + 1e-6).reshape(-1)
        dst = np.zeros(U * N, np.float32)
        q8 = np.zeros(U * N // QK8_1 * Q8_1_BS, np.uint8)
        args = [wu.reshape(-1), wg.reshape(-1), yb.reshape(-1), ids, dst, q8, np.int32(N), np.int32(K), np.int32(E),
                np.int32(U), np.int32(p.get("with_q8", 1)), np.int32(20), np.int32(256)]
        return p, args, {4: (ref, tol), 5: ("q8_of", 4)}
    if kernel == "moe_down":
        E, U, N, K = p["n_expert"], p["n_used"], p["nrows"], p["ncols"]
        w = gen_weights(rng, p["type"], E * N, K)
        yb, y = gen_q8_1(rng, K, nvec=U)
        ids = rng.choice(E, size=U, replace=False).astype(np.int32)
        wt = rng.dirichlet(np.ones(U)).astype(np.float32)
        res = rng.normal(0, 1, N).astype(np.float32)
        ref = res.astype(np.float64).copy()
        scale = np.abs(res).astype(np.float64)
        for j, e in enumerate(ids):
            We = dequant(w[e * N:(e + 1) * N], p["type"])
            ref += float(wt[j]) * (We @ y[j])
            scale += float(wt[j]) * (np.abs(We) @ np.abs(y[j]))
        dst = np.zeros(N, np.float32)
        args = [w.reshape(-1), yb.reshape(-1), ids, wt, res, dst, np.int32(N), np.int32(K), np.int32(E), np.int32(U),
                np.int32(20), np.int32(256)]
        return p, args, {5: (ref, 2e-4 * scale + 1e-6)}
    if kernel == "gdn":
        S, H, Hk, T, K = 128, p["H"], p["Hk"], p["n_tokens"], p["K"]
        row = 2 * Hk * S + H * S
        R = H * (2 * S + 2)
        qkv = rng.normal(0, 1, (T, row)).astype(np.float32)
        g = (-np.abs(rng.normal(0, 0.1, (T, H)))).astype(np.float32)        # log decay <= 0
        beta = rng.uniform(0, 1, (T, H)).astype(np.float32)
        s_in = rng.normal(0, 0.1, (H, S, S)).astype(np.float32)              # [h][col][i] = S[i][col]
        pend = np.zeros((2, K, R), np.float32)
        n_pend = p["n_pend"] if p["lag"] else 0
        for j in range(n_pend):  # read plane 0: post-norm k, v, raw g, beta per row
            kk = rng.normal(0, 1, (H, S))
            kk /= np.linalg.norm(kk, axis=1, keepdims=True)     # post-norm k of the previous verify rows
            pend[0, j, :H * S] = kk.reshape(-1)
            pend[0, j, H * S:2 * H * S] = rng.normal(0, 1, H * S)
            pend[0, j, 2 * H * S:2 * H * S + H] = -np.abs(rng.normal(0, 0.1, H))
            pend[0, j, 2 * H * S + H:] = rng.uniform(0, 1, H)
        attn_ref, s_ref, pend_ref = gdn_reference(qkv, g, beta, s_in, pend, H, Hk, T, p["lag"], K, n_pend, 1e-6)
        attn = np.zeros((T, H, S), np.float32)
        s_out = np.zeros((H, S, S), np.float32)
        args = [qkv.reshape(-1), g.reshape(-1), beta.reshape(-1), s_in.reshape(-1), attn.reshape(-1),
                s_out.reshape(-1), pend.reshape(-1), np.int32(H), np.int32(Hk), np.int32(T), np.int32(p["lag"]),
                np.int32(K), np.int32(n_pend), np.int32(4), np.float32(1e-6), np.int32(50)]
        tol = lambda r: 1e-4 * (1 + np.abs(r))  # noqa: E731
        out = {4: (attn_ref.reshape(-1), tol(attn_ref).reshape(-1)), 5: (s_ref.reshape(-1), tol(s_ref).reshape(-1))}
        if p["lag"]:
            out[6] = (pend_ref.reshape(-1), tol(pend_ref).reshape(-1))
        return p, args, out
    raise ValueError(kernel)


def gdn_reference(qkv, g, beta, s_in, pend, H, Hk, T, lag, K, n_pend, l2_eps):
    """float64 GATED_DELTA_NET(_LAG) of one sequence, the kernel's math (l2_qk fused, scalar gate)."""
    np = np_()
    S = 128
    R = H * (2 * S + 2)
    qkv = qkv.astype(np.float64)
    St = s_in.astype(np.float64).transpose(0, 2, 1).copy()           # [h][i][col] = S[i][col]
    pend_out = pend.astype(np.float64).copy()
    for j in range(n_pend):                                          # replay of the pending rows
        rowp = pend[0, j].astype(np.float64)
        for h in range(H):
            k = rowp[h * S:(h + 1) * S]
            v = rowp[H * S + h * S:H * S + (h + 1) * S]
            gv = math.exp(rowp[2 * H * S + h])
            b = rowp[2 * H * S + H + h]
            kv = St[h].T @ k
            delta = (v - gv * kv) * b
            St[h] = gv * St[h] + np.outer(k, delta)
    w = T - min(T, K) if lag else T
    s_commit = St.copy() if (lag and w == 0) else None
    attn = np.zeros((T, H, S))
    for t in range(T):
        for h in range(H):
            hk = h % Hk
            q = qkv[t, hk * S:(hk + 1) * S]
            k = qkv[t, Hk * S + hk * S:Hk * S + (hk + 1) * S]
            v = qkv[t, 2 * Hk * S + h * S:2 * Hk * S + (h + 1) * S]
            q = q / np.sqrt(np.sum(q * q) / S + l2_eps)
            k = k / np.sqrt(np.sum(k * k) / S + l2_eps)
            gv = math.exp(g[t, h])
            kv = St[h].T @ k
            delta = (v - gv * kv) * beta[t, h]
            St[h] = gv * St[h] + np.outer(k, delta)
            attn[t, h] = (St[h].T @ q) / math.sqrt(S)
            if lag and t >= w:
                r = t - w
                pend_out[1, r, h * S:(h + 1) * S] = k
                pend_out[1, r, H * S + h * S:H * S + (h + 1) * S] = v
                pend_out[1, r, 2 * H * S + h] = g[t, h]
                pend_out[1, r, 2 * H * S + H + h] = beta[t, h]
        if lag and t == w - 1:
            s_commit = St.copy()
    s_final = s_commit if lag else St
    return attn, s_final.transpose(0, 2, 1), pend_out


def q8_1_check(dst, q8):
    """The GGML_HIP_GATE_UP_Q8 copy: block g = quantize_q8_1(dst[32g:32g+32]) (d = amax/127, s = sum): dequantized
    values within d/2 of dst, d and s within fp16 rounding."""
    np = np_()
    blk = q8.reshape(-1, Q8_1_BS)
    d = blk[:, 0:2].copy().view(np.float16).astype(np.float64).reshape(-1)
    s = blk[:, 2:4].copy().view(np.float16).astype(np.float64).reshape(-1)
    q = blk[:, 4:].copy().view(np.int8).astype(np.float64)
    x = dst.astype(np.float64).reshape(-1, QK8_1)
    amax = np.abs(x).max(axis=1)
    d_exact = amax / 127
    half_ulp = 2.0 ** -11                      # relative rounding of a float -> fp16 conversion
    ok_d = np.all(np.abs(d - d_exact) <= d_exact * half_ulp + 1e-9)
    # q = round(x / d_fp32), stored d is its fp16 rounding: |q*d - x| <= d/2 + |q| * |d - d_fp32|
    ok_q = np.all(np.abs(q * d[:, None] - x) <= d[:, None] * 0.5 + 127 * np.abs(d - d_exact)[:, None] + 1e-6)
    # the kernel's fp32 sum differs from the float64 one by far less than 1e-5 * amax (32 terms)
    ok_s = np.all(np.abs(s - x.sum(axis=1)) <= np.abs(x.sum(axis=1)) * half_ulp + 1e-5 * amax + 1e-6)
    return bool(ok_d and ok_q and ok_s)


def make_verify(checks, quiet=False):
    """Kernel Tuner verify function. checks: {arg index: (float64 reference, tolerance) | ("q8_of", dst index)}.
    The tolerance is 2e-4 of the dot product of the magnitudes (|W| @ |y|): fp32 accumulation in any order stays far
    below it, a lost or duplicated quant block (>= 1/K_blocks of it) does not. Bitwise equality with the production
    configuration is checked separately (cmd_tune)."""
    np = np_()

    def say(msg):
        if not quiet:
            print(msg)

    def verify(answer, result_host, atol=None):
        for i, chk in checks.items():
            got = np.asarray(result_host[i])
            if isinstance(chk[0], str):
                if not q8_1_check(np.asarray(result_host[chk[1]]), got):
                    say(f"  verify: q8_1 copy of arg {chk[1]} wrong")
                    return False
                continue
            ref, tol = chk
            err = np.abs(got.astype(np.float64) - ref)
            if not np.all(np.isfinite(got)) or np.any(err > tol):
                j = int(np.argmax(err - tol))
                say(f"  verify: arg {i}: {int(np.sum(err > tol))} values off, worst [{j}] {got[j]} vs {ref[j]} "
                    f"(tol {tol[j] if np.ndim(tol) else tol})")
                return False
        return True
    return verify


def cmd_fake(a):
    """CPU-only: fake data for every shape (shrunk), reference sanity, verify-function self-test."""
    np = np_()
    probs = load_shapes()
    ok = True
    for k in ([a.kernel] if a.kernel else KERNELS):
        for p in probs[k]:
            p2, args, checks = make_problem(k, p, seed=p["id"], rows=a.rows)
            # simulated kernel output: the reference rounded to fp32 (+ the q8_1 copy quantized from it)
            res = [x.copy() if isinstance(x, np.ndarray) else x for x in args]
            for i, chk in checks.items():
                if not isinstance(chk[0], str):
                    res[i][:] = chk[0].astype(np.float32).reshape(res[i].shape)
            for i, chk in checks.items():
                if isinstance(chk[0], str):
                    res[i][:] = quantize_q8_1(res[chk[1]]).reshape(-1)
            v = make_verify(checks)
            good = v(None, res)
            # an injected error in one output value must be caught
            bad = [x.copy() if isinstance(x, np.ndarray) else x for x in res]
            i0 = next(i for i, c in checks.items() if not isinstance(c[0], str))
            ref, tol = checks[i0]
            j = int(np.argmax(np.abs(ref)))
            bad[i0][j] = np.float32(ref[j] + 50 * (tol[j] if np.ndim(tol) else tol))
            caught = not make_verify(checks, quiet=True)(None, bad)
            extra = ""
            if k == "mmvq_n1":
                extra = f" | {independent_mmvq_check(p2, args, checks)}"
            if k == "gdn":
                extra = f" | {independent_gdn_check(p2, args, checks)}"
            st = "OK" if good and caught else "FAIL"
            ok &= st == "OK"
            print(f"{k:12s} shape {p['id']:2d} {shape_str(k, p2):46s} verify(ref)={good} injected-error-caught={caught} "
                  f"-> {st}{extra}")
    print("fake: all OK" if ok else "fake: FAILURES")
    sys.exit(0 if ok else 1)


def independent_mmvq_check(p, args, checks):
    """Decode the q8_1 activations from their bytes (not from the generator's floats); for Q8_0 also the integer dot
    product sum_b dW_b*dy_b*sum(qW*qy) as the kernel computes it. Then the share of rows in which dropping one quant
    block (a typical indexing bug) moves the result past the tolerance."""
    np = np_()
    t = TYPES[p["type"]]
    nrows, K = p["nrows"], p["ncols"]
    ref, tol = checks[2]
    yb = args[1].reshape(-1, Q8_1_BS)[:K // QK8_1]
    dy = yb[:, 0:2].copy().view(np.float16).astype(np.float64).reshape(-1)
    qy = yb[:, 4:].copy().view(np.int8).astype(np.int64)
    y = (qy * dy[:, None]).reshape(-1)
    W = dequant(args[0].reshape(nrows, -1), p["type"])
    msg = f"max|ref - W.y(bytes)| {np.max(np.abs(W @ y - ref)):.1e}"
    if p["type"] == "Q8_0":
        wb = args[0].reshape(nrows, K // 32, 34)
        dw = wb[..., 0:2].copy().view(np.float16).astype(np.float64)[..., 0]
        qw = wb[..., 2:].copy().view(np.int8).astype(np.int64)
        dot = (dw * dy[None, :] * (qw * qy[None]).sum(axis=2)).sum(axis=1)
        msg += f", int-dot {np.max(np.abs(dot - ref)):.1e}"
    lost = W[:, :t["qk"]] @ y[:t["qk"]]
    msg += f", lost-block caught in {100 * np.mean(np.abs(lost) > tol):.0f}% of rows"
    return msg


def quantize_q8_1(x):
    """numpy quantize_q8_1 of float32 values (d = amax/127, q = round(x/d), s = sum(x)); for the fake self-test."""
    np = np_()
    x = np.asarray(x, np.float64).reshape(-1, QK8_1)
    amax = np.abs(x).max(axis=1)
    d = amax / 127
    q = np.where(d[:, None] > 0, np.round(x / np.where(d[:, None] > 0, d[:, None], 1)), 0).astype(np.int8)
    blk = np.zeros((x.shape[0], Q8_1_BS), np.uint8)
    blk[:, 0:2] = d.astype(np.float16).view(np.uint8).reshape(-1, 2)
    blk[:, 2:4] = x.sum(axis=1).astype(np.float16).view(np.uint8).reshape(-1, 2)
    blk[:, 4:] = q.view(np.uint8)
    return blk


def independent_gdn_check(p, args, checks):
    """Second formulation of the recurrence (per column, scalar loops over a small head subset) vs gdn_reference."""
    np = np_()
    S, H, Hk, T = 128, p["H"], p["Hk"], p["n_tokens"]
    if p["lag"]:
        # w = 0 (n_tokens <= K): the committed state is the input state after the n_pend replayed rows; the last
        # n_tokens rows go to the write plane
        R = H * (2 * S + 2)
        pend = args[6].reshape(2, p["K"], R).astype(np.float64)
        M = args[3].reshape(H, S, S).astype(np.float64).copy()
        s_ref = checks[5][0].reshape(H, S, S)
        worst = 0.0
        for h in range(min(H, 2)):
            for j in range(p["n_pend"]):
                row = pend[0, j]
                k = row[h * S:(h + 1) * S]
                gv = math.exp(row[2 * H * S + h])
                b = row[2 * H * S + H + h]
                for col in range(S):
                    delta = (row[H * S + h * S + col] - gv * float(np.dot(M[h, col], k))) * b
                    M[h, col] = gv * M[h, col] + k * delta
            worst = max(worst, float(np.max(np.abs(M[h] - s_ref[h]))))
        v_ok = np.array_equal(checks[6][0].reshape(2, p["K"], R)[1, :T, H * S:2 * H * S],
                              args[0].reshape(T, -1)[:, 2 * Hk * S:].astype(np.float64))
        return f"independent replay of {p['n_pend']} pending rows (2 heads): max |diff| {worst:.1e}, pending v rows {v_ok}"
    qkv = args[0].reshape(T, -1).astype(np.float64)
    g = args[1].reshape(T, H)
    beta = args[2].reshape(T, H)
    M = args[3].reshape(H, S, S).astype(np.float64).copy()   # M[h][col][i]
    attn_ref = checks[4][0].reshape(T, H, S)
    worst = 0.0
    for h in range(min(H, 2)):
        hk = h % Hk
        for t in range(T):
            q = qkv[t, hk * S:(hk + 1) * S]
            k = qkv[t, Hk * S + hk * S:Hk * S + (hk + 1) * S]
            q = q * (1.0 / math.sqrt(sum(x * x for x in q) / S + 1e-6))
            k = k * (1.0 / math.sqrt(sum(x * x for x in k) / S + 1e-6))
            gv = math.exp(float(g[t, h]))
            for col in range(S):
                kv = float(np.dot(M[h, col], k))
                delta = (qkv[t, 2 * Hk * S + h * S + col] - gv * kv) * float(beta[t, h])
                M[h, col] = gv * M[h, col] + k * delta
                a = float(np.dot(M[h, col], q)) / math.sqrt(S)
                worst = max(worst, abs(a - attn_ref[t, h, col]))
    return f"independent per-column recurrence (2 heads): max |diff| {worst:.1e}"


def shape_str(k, p):
    if k == "gdn":
        return f"{p['mode']} H{p['H']} Hk{p['Hk']} T{p['n_tokens']} lag{p['lag']}"
    e = f" E{p['n_expert']}/{p['n_used']}" if "n_expert" in p else ""
    return f"{p['type']} {p['nrows']}x{p['ncols']}{e}"


# ---------------------------------------------------------------------------------------------------------------
# Kernel Tuner stub (C backend): dlopens the precompiled variant of the configuration
# ---------------------------------------------------------------------------------------------------------------
STUB_SIG = {
    "mmvq_n1": ("kt_mmvq_n1", "const uint8_t * w, const uint8_t * y, float * dst, int nrows, int ncols, int iters, "
                "int cold_mb", "w, y, dst, nrows, ncols, iters, cold_mb"),
    "moe_gate_up": ("kt_moe_gate_up", "const uint8_t * wu, const uint8_t * wg, const uint8_t * y, const int32_t * ids, "
                    "float * dst, uint8_t * q8, int nrows, int ncols, int n_expert, int n_used, int with_q8, "
                    "int iters, int cold_mb", "wu, wg, y, ids, dst, q8, nrows, ncols, n_expert, n_used, with_q8, "
                    "iters, cold_mb"),
    "moe_down": ("kt_moe_down", "const uint8_t * w, const uint8_t * y, const int32_t * ids, const float * wt, "
                 "const float * res, float * dst, int nrows, int ncols, int n_expert, int n_used, int iters, "
                 "int cold_mb", "w, y, ids, wt, res, dst, nrows, ncols, n_expert, n_used, iters, cold_mb"),
    "gdn": ("kt_gdn", "const float * qkv, const float * g, const float * beta, const float * s_in, float * attn, "
            "float * s_out, float * pend, int H, int Hk, int n_tokens, int lag, int K, int n_pend, int num_warps_arg, "
            "float l2_eps, int iters", "qkv, g, beta, s_in, attn, s_out, pend, H, Hk, n_tokens, lag, K, n_pend, "
            "NUM_WARPS, l2_eps, iters"),
}


def stub_source(kernel):
    fn, params, call = STUB_SIG[kernel]
    if kernel == "gdn":
        path = 'KT_BUILD_DIR "/gdn_cpw" KT_S(CPW) ".so"'
    else:
        path = 'KT_BUILD_DIR "/mmvq_" KT_S(KT_TYPE_NAME) "_nw" KT_S(NWARPS) "_r" KT_S(ROWS) ".so"'
    proto = re.sub(r"\b(w|y|dst|wu|wg|ids|q8|wt|res|qkv|g|beta|s_in|attn|s_out|pend|nrows|ncols|n_expert|n_used|"
                   r"with_q8|iters|cold_mb|H|Hk|n_tokens|lag|K|n_pend|num_warps_arg|l2_eps)\b(?=\s*(,|$))", "", params)
    return f"""// Kernel Tuner C-backend stub for {kernel}: the tunables arrive as #defines; the configuration's variant was built
// offline by kt.py compile and is dlopened here (libkt_mem.so shares the device buffers between variants).
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#define KT_S2(x) #x
#define KT_S(x) KT_S2(x)
typedef float (*kt_fn)({proto});
extern "C" float {fn}({params}) {{
    static kt_fn f = 0;
    if (!f) {{
        const char * path = {path};
        void * h = dlopen(path, RTLD_NOW | RTLD_LOCAL);
        if (!h) {{ fprintf(stderr, "kt stub: %s\\n", dlerror()); return 1e30f; }}
        f = (kt_fn) dlsym(h, "{fn}");
        if (!f) {{ fprintf(stderr, "kt stub: %s\\n", dlerror()); return 1e30f; }}
    }}
    return f({call});
}}
"""


def stub_options(kernel, p):
    opts = ["-fPIC", "-O1", f'-DKT_BUILD_DIR="{BUILD}"']
    if kernel != "gdn":
        opts.append(f"-DKT_TYPE_NAME={p['type']}")
    return opts


def cmd_stub(a):
    import tempfile
    probs = load_shapes()
    for k in ([a.kernel] if a.kernel else KERNELS):
        src = stub_source(k)
        p = probs[k][0]
        cfg = prod_config(k, p)
        defs = "".join(f"#define {kk} {v}\n" for kk, v in cfg.items())
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "stub.cc")
            with open(f, "w") as fh:
                fh.write(defs + src)
            r = subprocess.run(["g++", "-c", f, "-o", os.path.join(d, "stub.o")] + stub_options(k, p),
                               capture_output=True, text=True)
            r2 = subprocess.run(["g++", os.path.join(d, "stub.o"), "-shared", "-o", os.path.join(d, "stub.so")],
                                capture_output=True, text=True) if r.returncode == 0 else r
            nm = subprocess.run(["nm", "-D", "--defined-only", os.path.join(d, "stub.so")], capture_output=True,
                                text=True).stdout if r2.returncode == 0 else ""
        status = "compiles (g++), exports " + STUB_SIG[k][0] if STUB_SIG[k][0] in nm else "FAILED " + r.stderr + r2.stderr
        print(f"== {k}: stub {status}; config {cfg} -> {variant_name(k, p, cfg)}.so")
        if a.show:
            print(defs + src)


# ---------------------------------------------------------------------------------------------------------------
# tuning (GPU) and the per-shape table
# ---------------------------------------------------------------------------------------------------------------
def gpu_guard():
    if subprocess.run(["pgrep", "-f", USER_SERVER], capture_output=True).returncode == 0:
        sys.exit("refusing: the user's llama-server on port 8080 is running")
    if os.environ.get("KT_GPU_LOCKED") != "1":
        env = dict(os.environ, KT_GPU_LOCKED="1")
        os.execvpe(GPU_WRAP[0], GPU_WRAP + [sys.executable] + sys.argv, env)


def run_variant(k, p, cfg, args):
    """One call of the variant of cfg on copies of args (ctypes, no Kernel Tuner): (ms, output arrays)."""
    import ctypes
    np = np_()
    lib = ctypes.CDLL(os.path.join(BUILD, variant_name(k, p, cfg) + ".so"))
    fn = getattr(lib, STUB_SIG[k][0])
    fn.restype = ctypes.c_float
    xs = [x.copy() if isinstance(x, np.ndarray) else x for x in args]
    if k == "gdn":
        xs[13] = np.int32(cfg["NUM_WARPS"])
    cargs = [x.ctypes.data_as(ctypes.c_void_p) if isinstance(x, np.ndarray) else
             (ctypes.c_float(float(x)) if isinstance(x, np.float32) else ctypes.c_int(int(x))) for x in xs]
    return fn(*cargs), xs


def cmd_tune(a):
    np = np_()
    probs = load_shapes()
    if a.dry_run:
        n = 0
        for k in ([a.kernel] if a.kernel else KERNELS):
            for p in probs[k]:
                if a.shape is not None and p["id"] != a.shape:
                    continue
                cs = configs(k, p)
                miss = [c for c in cs if not os.path.exists(os.path.join(BUILD, variant_name(k, p, c) + ".so"))]
                n += len(cs)
                print(f"{k} shape {p['id']} {shape_str(k, p)}: {len(cs)} configs, production {prod_config(k, p)}, "
                      f"variants missing {len(miss)}")
        argv = " ".join(x for x in sys.argv if x != "--dry-run")
        print(f"would run {n} configurations x {a.iterations} timed calls under: {' '.join(GPU_WRAP)} "
              f"{sys.executable} {argv} (refuses while pgrep -f '{USER_SERVER}' matches)")
        return
    gpu_guard()
    import kernel_tuner  # only now: its HIP backend loads the HIP runtime
    os.makedirs(os.path.join(KT_DIR, "results"), exist_ok=True)
    for k in ([a.kernel] if a.kernel else KERNELS):
        for p in probs[k]:
            if a.shape is not None and p["id"] != a.shape:
                continue
            missing = [variant_name(k, p, c) for c in configs(k, p)
                       if not os.path.exists(os.path.join(BUILD, variant_name(k, p, c) + ".so"))]
            if missing:
                sys.exit(f"{k} shape {p['id']}: variants not built ({missing[:4]}...): kt.py compile --kernel {k} --all")
            _, args, checks = make_problem(k, p, seed=p["id"])
            pc = prod_config(k, p)
            outs = [i for i, c in checks.items() if not isinstance(c[0], str)]
            # the production configuration: CPU reference check, then its outputs are the bitwise reference
            _, prod_out = run_variant(k, p, pc, args)
            if not make_verify(checks)(None, prod_out):
                sys.exit(f"{k} shape {p['id']}: the production configuration fails the CPU reference check")
            exact = {i: prod_out[i].copy() for i in outs}
            name = f"{k}_{p['id']}"
            # Kernel Tuner: every configuration within the CPU reference tolerance (answer arrays only mark the outputs
            # to read back; the custom verify compares against the float64 references)
            answer = [x if i in checks else None for i, x in enumerate(args)]
            res, _env = kernel_tuner.tune_kernel(
                STUB_SIG[k][0], stub_source(k), 1, args, {kk: list(v) for kk, v in SPACE[k].items()}, lang="C",
                compiler="g++", compiler_options=stub_options(k, p), answer=answer, verify=make_verify(checks),
                restrictions=lambda c, _p=p, _k=k: valid(_k, _p, c), iterations=a.iterations,
                cache=os.path.join(KT_DIR, "results", name + ".cache.json"), verbose=True)
            rows = []
            for r in res:
                cfg = {kk: int(r[kk]) for kk in SPACE[k]}
                t = r.get("time")
                row = dict(cfg, time=float(t) if isinstance(t, (int, float, np.floating)) else str(t))
                if isinstance(row["time"], float):
                    # bitwise against the production outputs (one more run); a config in the bitwise class that is
                    # not bitwise is a harness or kernel bug
                    _, out = run_variant(k, p, cfg, args)
                    row["bitwise"] = all(np.array_equal(out[i].view(np.uint32), exact[i].view(np.uint32)) for i in outs)
                    row["bitwise_class"] = all(cfg[kk] == pc[kk] for kk in SPACE[k] if kk not in BITWISE_KNOBS[k])
                    if row["bitwise_class"] and not row["bitwise"]:
                        print(f"  BUG: {cfg} should be bitwise equal to production {pc} but is not")
                rows.append(row)
            with open(os.path.join(KT_DIR, "results", name + ".json"), "w") as f:
                json.dump(dict(kernel=k, shape=p, prod=pc, results=rows), f, indent=1)
            print(f"wrote results/{name}.json ({len(rows)} configs)")


def cmd_table(a):
    import glob
    if a.fake:
        results = fake_results()
    else:
        results = []
        for f in sorted(glob.glob(a.results or os.path.join(KT_DIR, "results", "*.json"))):
            if f.endswith(".cache.json"):
                continue
            with open(f) as fh:
                results.append(json.load(fh))
    rows = []
    for r in results:
        k, p, pc = r["kernel"], r["shape"], r["prod"]
        ok = [x for x in r["results"] if isinstance(x.get("time"), (int, float)) and x["time"] < 1e29]
        if not a.any:  # the fork's rule: speed changes are bit-identical, so only bitwise configurations qualify
            ok = [x for x in ok if x.get("bitwise", x.get("bitwise_class"))]
        if not ok:
            continue
        best = min(ok, key=lambda x: x["time"])
        prod = next((x for x in ok if all(x[kk] == pc[kk] for kk in SPACE[k])), None)
        cfg = {kk: best[kk] for kk in SPACE[k]}
        rows.append(dict(arch=ARCH, kernel=k, type=p.get("type", "F32"), nrows=p.get("nrows", p.get("H", 0)),
                         ncols=p.get("ncols", p.get("Hk", 0)), n_expert=p.get("n_expert", 0), n_used=p.get("n_used", 0),
                         lag=p.get("lag", 0),
                         mode=p.get("mode", ""), n_tokens=p.get("n_tokens", 1), counts=p.get("counts", {}),
                         best=cfg, best_us=round(best["time"] * 1e3, 2), prod=pc,
                         prod_us=round(prod["time"] * 1e3, 2) if prod else None,
                         speedup=round(prod["time"] / best["time"], 4) if prod else None,
                         bitwise=bool(best.get("bitwise", best.get("bitwise_class")))))
    out = a.out or os.path.join(KT_DIR, "kt-table-" + ARCH + (".fake" if a.fake else ""))
    with open(out + ".json", "w") as f:
        json.dump(rows, f, indent=1)
    inc = ["// Generated by ~/qwen-opt/tools/kt/kt.py table" + (" (FAKE DATA)" if a.fake else "") + f" for {ARCH}.",
           "// One entry per decode shape: the fastest configuration found by Kernel Tuner"
           + (" (any numerics)." if a.any else " among those bitwise equal to production."),
           "// KT_MMVQ(kernel, type, nrows, ncols, n_used, nwarps, rows_per_block, bitwise_vs_production)",
           "// KT_GDN(H, Hk, n_tokens, lag, cols_per_warp, num_warps, bitwise_vs_production)"]
    for r in rows:
        if r["kernel"] == "gdn":
            inc.append(f"KT_GDN({r_shape(r)}, {r['best']['CPW']}, {r['best']['NUM_WARPS']}, {int(r['bitwise'])})")
        else:
            inc.append(f"KT_MMVQ(KT_{r['kernel'].upper()}, GGML_TYPE_{r['type']}, {r['nrows']}, {r['ncols']}, "
                       f"{r['n_used']}, {r['best']['NWARPS']}, {r['best']['ROWS']}, {int(r['bitwise'])})")
    with open(out + ".inc", "w") as f:
        f.write("\n".join(inc) + "\n")
    print("| kernel | shape | launches/step | production | us | best | us | speedup | bitwise |")
    print("|---|---|---|---|---|---|---|---|---|")
    saved = {}
    for r in rows:
        shp = f"{r['type']} {r['nrows']}x{r['ncols']}" if r["kernel"] != "gdn" else f"{r['mode']} T{r['n_tokens']}"
        cnt = " ".join(f"{m}:{n}" for m, n in r["counts"].items())
        print(f"| {r['kernel']} | {shp} | {cnt} | {r['prod']} | {r['prod_us']} | {r['best']} | {r['best_us']} | "
              f"{r['speedup']} | {r['bitwise']} |")
        if r["prod_us"]:
            for m, n in r["counts"].items():
                key = f"{m} {'MTP verify' if r['kernel'] == 'gdn' and r['lag'] else 'one-token step'}"
                saved[key] = saved.get(key, 0.0) + (r["prod_us"] - r["best_us"]) * n
    print("\nproduction - best, summed over the launches of a step (isolated cache-cold kernel times, upper bound):")
    for key, us in sorted(saved.items()):
        print(f"  {key}: {us:.1f} us")
    print(f"wrote {out}.json and {out}.inc")


def r_shape(r):
    return f"{r['nrows']}, {r['ncols']}, {r['n_tokens']}, {r['lag']}"


def fake_results():
    """Synthetic Kernel Tuner results for every shape: validates the table path without a GPU."""
    import random
    probs = load_shapes()
    out = []
    for k, ps in probs.items():
        for p in ps:
            rnd = random.Random(f"{k}{p['id']}")
            pc = prod_config(k, p)
            res = []
            for c in configs(k, p):
                t = 0.05 * (0.85 + 0.3 * rnd.random())   # some configurations beat production (0.05 ms)
                if c == pc:
                    t = 0.05
                bc = all(c[kk] == pc[kk] for kk in SPACE[k] if kk not in BITWISE_KNOBS[k])
                res.append(dict(c, time=t, bitwise_class=bc, bitwise=bc))
            out.append(dict(kernel=k, shape=p, prod=pc, results=res))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["shapes", "space", "compile", "isacheck", "fake", "stub", "table", "tune"])
    ap.add_argument("--kernel", choices=KERNELS)
    ap.add_argument("--json")
    ap.add_argument("--all", action="store_true", help="compile: every variant of the search space")
    ap.add_argument("--prod", action="store_true", help="compile: only the production configurations")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("--rows", type=int, default=64, help="fake: rows (heads for gdn) of the shrunk problems")
    ap.add_argument("--show", action="store_true", help="stub: print the source")
    ap.add_argument("--results")
    ap.add_argument("--out")
    ap.add_argument("--fake", action="store_true", help="table: synthetic results")
    ap.add_argument("--any", action="store_true", help="table: also non-bitwise configurations (KLD gate needed)")
    ap.add_argument("--shape", type=int)
    ap.add_argument("--iterations", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true", help="tune: list what would run, no GPU")
    a = ap.parse_args()
    {"shapes": cmd_shapes, "space": cmd_space, "compile": cmd_compile, "fake": cmd_fake, "stub": cmd_stub,
     "table": cmd_table, "tune": cmd_tune, "isacheck": cmd_isacheck}[a.cmd](a)


if __name__ == "__main__":
    main()
