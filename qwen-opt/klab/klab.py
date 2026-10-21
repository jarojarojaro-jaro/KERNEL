#!/usr/bin/env python3
"""klab — kernel lab for Qwen3.8-27B decode on the RX 7900 XTX (gfx1100). README: ~/KERNEL/qwen-opt/klab/README.md

  klab profile DIR [--bw 926] [--by kernel|type|class] [--top 40] [--md]
        DIR = a prof_block.sh arm dir (client.jsonl + *kernel_trace.csv). Per kernel instance (mmvq: quant type, ncols,
        fusion flag, rows) ms/step, calls/step, est. weight bytes, GB/s and LOST ms/step vs the --bw roofline
        (lost = t - bytes/bw; kernels without a byte model count fully as lost). CPU only.
  klab trace TAG [--bin ~/llama-topka] [--tokens 512]       queue job: rocprofv3 kernel trace (PM4=0) -> klab/traces/TAG
  klab isa LIB_OR_BENCH [--kernel RE] [--out F]              ISA dump + per-kernel stats (VGPR/SGPR/LDS/scratch/occupancy,
                                                             instruction mix) from the gfx1100 code object. CPU only.
  klab isadiff A B --kernel RE                               stats side by side + unified diff of normalized ISA. CPU only.
  klab bench VAR [--filter F] [--rounds 5] [-- CLANG_FLAGS]  build mmvqbig bench (base = ~/wt/topka, var = ~/wt/mmvqbig
                                                             + flags) as klab/build/VAR and queue it (PM4=0). Results
                                                             in klab/logs/bench-VAR.log: us base/var, GB/s, bitexact.
  klab sweep NAME FLAGSET...                                 one bench per FLAGSET ("-DA=1 -DB=2"), one queue file, then
                                                             `klab sweep-report NAME` ranks them (bitexact only).
  klab gate TAG BIN [ARM_ENV...]                             queue job: p100_md5.sh (PM4=1 WA=2 GUARD=1, md5 Qwen
                                                             c4708318/6f14e814, LFM 894e56e4; switch on == off).
Every GPU action goes through ~/qwen-opt/queue/run-jobs.sh (started in the background; it waits for the locks).
"""
from __future__ import annotations

import argparse
import collections
import csv
import difflib
import glob
import json
import os
import re
import subprocess
import sys

HOME = os.path.expanduser("~")
K = os.path.join(HOME, "qwen-opt", "klab")
QUEUE = os.path.join(HOME, "qwen-opt", "queue", "run-jobs.sh")
MODEL = os.path.join(HOME, "models", "Qwen3.8-27B-UD-Q4_K_XL.gguf")
OBJDUMP = "/opt/rocm/core-10.0/llvm/bin/llvm-objdump"
BUNDLER = "/opt/rocm/core-10.0/llvm/bin/clang-offload-bundler"

# ggml type id -> (name, bits per weight)
QT = {0: ("F32", 32), 1: ("F16", 16), 8: ("Q8_0", 8.5), 11: ("Q3_K", 3.4375), 12: ("Q4_K", 4.5), 13: ("Q5_K", 5.5),
      14: ("Q6_K", 6.5625), 20: ("IQ4_NL", 4.5), 21: ("IQ3_S", 3.4375), 23: ("IQ4_XS", 4.25)}


# ----------------------------------------------------------------------------------------------------------- shapes
def model_shapes(path: str = MODEL) -> dict:
    """rows -> {type: [ncols...]} of the 2-D weights (+ fused gate|up = 2*ffn rows, draft head 65536 rows)."""
    cache = os.path.join(K, "shapes.json")
    if os.path.exists(cache):
        return {int(r): {int(t): v for t, v in d.items()} for r, d in json.load(open(cache)).items()}
    sys.path.insert(0, os.path.join(HOME, "wt", "topka", "gguf-py"))
    import gguf  # noqa: E402
    out: dict = collections.defaultdict(lambda: collections.defaultdict(list))
    for t in gguf.GGUFReader(path).tensors:
        if len(t.shape) == 2 and t.tensor_type.value != 0:
            ncols, rows = int(t.shape[0]), int(t.shape[1])
            out[rows][int(t.tensor_type.value)].append(ncols)
            if "ffn_gate" in t.name:
                out[2 * rows][int(t.tensor_type.value)].append(ncols)
    for ty in QT:
        out[65536][ty].append(5120)        # MTP/draft head over the 65536-token draft vocab
        out[16384][ty].append(5120)        # GDN fused attn_qkv (10240) + attn_gate (6144) launch
    os.makedirs(K, exist_ok=True)
    json.dump(out, open(cache, "w"))
    return {r: dict(d) for r, d in out.items()}


MMVQ = re.compile(r"void mul_mat_vec_q<\(ggml_type\)(\d+), (\d+), (true|false)")


def kname(n: str) -> str:
    m = MMVQ.match(n)
    if m:
        return f"mmvq {QT.get(int(m.group(1)), (m.group(1),))[0]} n{m.group(2)}{' fused' if m.group(3) == 'true' else ''}"
    n = n.replace("void ", "")
    return re.sub(r"[<(].*", "", n)[:44]


def mmvq_bytes(n: str, gx: int, wx: int, wy: int, shapes: dict) -> tuple[int, int] | None:
    """(rows, weight bytes) of one mmvq launch; rows snapped to a model row count via rows-per-block guesses."""
    m = MMVQ.match(n)
    if not m:
        return None
    ty, nc = int(m.group(1)), int(m.group(2))
    blocks = gx // max(wx, 1)
    pref = {1: (wy, 1, 2, 4), 2: (2, 1, 4), 3: (2, 1, 4), 4: (2, 1, 4)}.get(nc, (4, 2, 1, 8))
    for typed in (True, False):            # first a row count this quant type really has, then any type's
        for rpb in pref:
            rows = blocks * rpb
            if m.group(3) == "true" and rows == 17408:
                rows *= 2                  # fused SWIGLU launch (n1): grid covers 17408 rows, reads gate AND up
            if rows in shapes and (not typed or ty in shapes[rows]):
                cols = shapes[rows].get(ty) or [c for v in shapes[rows].values() for c in v]
                ncols = sum(cols) / len(cols)
                return rows, int(rows * ncols * QT.get(ty, ("", 8))[1] / 8)
    return blocks * pref[0], 0


def load_trace(d: str) -> tuple[list, dict]:
    cl = [json.loads(x) for x in open(os.path.join(d, "client.jsonl"))][-1]
    f = glob.glob(os.path.join(d, "**", "*kernel_trace.csv"), recursive=True)[0]
    rows = []
    for r in csv.DictReader(open(f)):
        rows.append((int(r["Start_Timestamp"]), int(r["End_Timestamp"]), r["Kernel_Name"], int(r["Grid_Size_X"]),
                     int(r["Workgroup_Size_X"]), int(r["Workgroup_Size_Y"]), int(r["VGPR_Count"]),
                     int(r["LDS_Block_Size"])))
    rows.sort()
    cut = 0
    for i in range(1, len(rows)):
        if rows[i][0] - rows[i - 1][1] > 1e9:
            cut = i
    return rows[cut:], cl


def profile(a) -> None:
    seg, cl = load_trace(a.dir)
    steps = cl["steps"]
    shapes = model_shapes()
    wall = (seg[-1][1] - seg[0][0]) / 1e6 / steps
    agg: dict = collections.defaultdict(lambda: [0, 0.0, 0, 0, 0])   # calls, ns, bytes, rows, vgpr
    for s, e, n, gx, wx, wy, vg, lds in seg:
        rb = mmvq_bytes(n, gx, wx, wy, shapes)
        if a.by == "type":
            key = kname(n).split(" n")[0] if rb else "non-mmvq " + kname(n)
        elif a.by == "class":
            key = re.sub(r" (fused)$", "", kname(n)) if rb else kname(n)
        else:
            key = f"{kname(n)} r{rb[0]}" if rb else kname(n)
        g = agg[key]
        g[0] += 1; g[1] += e - s; g[2] += rb[1] if rb else 0; g[3] = rb[0] if rb else 0; g[4] = max(g[4], vg)
    bw = a.bw * 1e9
    tab = []
    for k, (c, ns, by, rows, vg) in agg.items():
        t = ns / 1e6 / steps
        ideal = by / bw * 1e3 / steps if by else 0.0
        gbs = by / ns if by and ns else 0.0
        tab.append((t - ideal, k, c / steps, t, by / steps / 1e6, gbs, vg))
    tab.sort(reverse=True)
    busy = sum(r[3] for r in tab)
    lost = sum(r[0] for r in tab)
    mb = sum(r[4] for r in tab)
    hdr = (f"{a.dir}: {steps} steps, client {cl['ms_step']:.2f} ms/step, trace wall {wall:.2f}, busy {busy:.2f}, "
           f"idle {wall - busy:.2f} ms/step; modelled weight traffic {mb:.0f} MB/step = "
           f"{mb / a.bw:.2f} ms @ {a.bw:.0f} GB/s; lost vs roofline {lost:.2f} ms/step (+ idle)")
    print(hdr)
    sep = "|" if a.md else " "
    cols = ["lost ms", "kernel", "calls/st", "ms/st", "MB/st", "GB/s", "%bw", "VGPR"]
    if a.md:
        print("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
    else:
        print(f"{'lost':>7} {'kernel':46s} {'calls':>6} {'ms':>7} {'MB':>7} {'GB/s':>6} {'%bw':>5} {'vgpr':>4}")
    for lo, k, c, t, m, g, vg in tab[:a.top]:
        if a.md:
            print(f"| {lo:.3f} | {k} | {c:.1f} | {t:.3f} | {m:.0f} | {g:.0f} | {100 * g / a.bw:.0f} | {vg} |")
        else:
            print(f"{lo:7.3f} {k:46s} {c:6.1f} {t:7.3f} {m:7.0f} {g:6.0f} {100 * g / a.bw:5.0f} {vg:4d}")
    del sep


# -------------------------------------------------------------------------------------------------------------- ISA
def code_objects(path: str, tmp: str) -> list[str]:
    """gfx1100 code objects of every offload bundle inside the .hip_fatbin section (one bundle per HIP TU)."""
    fb = os.path.join(tmp, "fatbin")
    subprocess.run(["objcopy", "-O", "binary", "--only-section=.hip_fatbin", os.path.realpath(path), fb], check=True)
    data = open(fb, "rb").read()
    starts = sorted(set(m.start() for mag in (rb"__CLANG_OFFLOAD_BUNDLE__", rb"CCOB") for m in re.finditer(mag, data)))
    objs = []
    for i, pos in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(data)
        sl = os.path.join(tmp, f"b{i}.bundle")
        open(sl, "wb").write(data[pos:end])
        out = os.path.join(tmp, f"b{i}.co")
        r = subprocess.run([BUNDLER, "--unbundle", "--type=o", f"--input={sl}",
                            "--targets=hipv4-amdgcn-amd-amdhsa--gfx1100", f"--output={out}"], capture_output=True)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            objs.append(out)
    return objs


def isa_text(path: str) -> str:
    """Disassemble every gfx1100 code object inside PATH (shared lib or executable with a HIP fatbin)."""
    tmp = f"/tmp/klab-isa-{os.getpid()}"
    os.makedirs(tmp, exist_ok=True)
    objs = code_objects(path, tmp)
    txt = []
    for o in objs:
        txt.append(subprocess.run([OBJDUMP, "-d", "--no-show-raw-insn", o], capture_output=True,
                                  text=True).stdout)
        txt.append(subprocess.run(["/opt/rocm/core-10.0/llvm/bin/llvm-readelf", "--notes", o], capture_output=True,
                                  text=True).stdout)
    subprocess.run(["rm", "-rf", tmp])
    return "\n".join(txt)


def isa_split(txt: str) -> tuple[dict, dict]:
    funcs, cur = {}, None
    for ln in txt.splitlines():
        m = re.match(r"^[0-9a-f]+ <(.*)>:$", ln)
        if m:
            cur = m.group(1); funcs[cur] = []; continue
        if cur and ln.startswith("\t") or (cur and ln.startswith(" ")):
            ins = ln.split("//")[0].strip()
            if ins:
                funcs[cur].append(ins)
        elif not ln.strip():
            cur = None
    meta = {}
    for blk in re.split(r"\n\s*- \.(?:agpr_count|args):", txt):
        nm = re.search(r"\.symbol:\s+(\S+?)(\.kd)?\s", blk)
        if not nm:
            continue
        g = lambda k: int(re.search(rf"\.{k}:\s+(\d+)", blk).group(1)) if re.search(rf"\.{k}:\s+(\d+)", blk) else -1
        meta[nm.group(1)] = dict(vgpr=g("vgpr_count"), sgpr=g("sgpr_count"), lds=g("group_segment_fixed_size"),
                                 scratch=g("private_segment_fixed_size"))
    names = sorted(set(funcs) | set(meta))
    dem = subprocess.run(["c++filt"], input="\n".join(names), capture_output=True, text=True).stdout.splitlines()
    dm = dict(zip(names, dem)) if len(dem) == len(names) else {n: n for n in names}
    return {dm[k]: v for k, v in funcs.items()}, {dm[k]: v for k, v in meta.items()}


MIX = [("vmem_load", r"^(global|buffer|flat)_load"), ("smem", r"^s_(load|buffer_load)"), ("lds", r"^ds_"),
       ("dot", r"^v_dot"), ("valu", r"^v_"), ("salu", r"^s_(?!waitcnt|load|branch|cbranch)"), ("waitcnt", r"^s_waitcnt"),
       ("branch", r"^s_(c?branch)"), ("dpp/perm", r"(dpp|_perm|permlane|swizzle)")]


def stats(ins: list) -> dict:
    d = collections.Counter(len=len(ins))
    for i in ins:
        for k, p in MIX:
            if re.search(p, i):
                d[k] += 1
                if k in ("vmem_load", "smem", "lds", "dot"):
                    pass
    return d


def occupancy(vgpr: int) -> int:   # waves/SIMD on gfx1100 wave32 (1536 VGPRs per lane, granule 24 -> 16 waves max)
    return max(1, min(16, 1536 // max(24, -(-vgpr // 24) * 24))) if vgpr > 0 else -1


def isa(a) -> None:
    txt = isa_text(a.lib)
    funcs, meta = isa_split(txt)
    rx = re.compile(a.kernel)
    sel = [f for f in funcs if rx.search(f)]
    if a.out:
        with open(a.out, "w") as fo:
            for f in sel:
                fo.write(f"<{f}>:\n" + "\n".join(funcs[f]) + "\n\n")
    print(f"{'kernel':90s} {'ins':>5} {'vmem':>4} {'dot':>4} {'valu':>5} {'wait':>4} {'vgpr':>4} {'occ':>3} {'lds':>5} {'scr':>3}")
    for f in sel:
        st = stats(funcs[f])
        mk = meta.get(f, {})
        print(f"{f[:90]:90s} {st['len']:5d} {st['vmem_load']:4d} {st['dot']:4d} {st['valu']:5d} {st['waitcnt']:4d} "
              f"{mk.get('vgpr', -1):4d} {occupancy(mk.get('vgpr', -1)):3d} {mk.get('lds', -1):5d} {mk.get('scratch', -1):3d}")


def norm(ins: list) -> list:
    return [re.sub(r"0x[0-9a-f]+|\b[0-9a-f]{6,}\b", "#", i) for i in ins]


def isadiff(a) -> None:
    fa, ma = isa_split(isa_text(a.a))
    fb, mb = isa_split(isa_text(a.b))
    rx = re.compile(a.kernel)
    for f in sorted(set(fa) | set(fb)):
        if not rx.search(f):
            continue
        x, y = fa.get(f, []), fb.get(f, [])
        sx, sy = stats(x), stats(y)
        print(f"== {f[:120]}\n   " + "  ".join(f"{k}:{sx[k]}->{sy[k]}" for k in ["len"] + [m for m, _ in MIX]
                                             if sx[k] != sy[k]) or "   identical stats")
        if a.full:
            sys.stdout.writelines(l + "\n" for l in difflib.unified_diff(norm(x), norm(y), "A", "B", n=1))


# ------------------------------------------------------------------------------------------------------ GPU (queue)
def enqueue(name: str, lines: list[str]) -> str:
    os.makedirs(os.path.join(K, "jobs"), exist_ok=True)
    jf = os.path.join(K, "jobs", f"{name}.jobs")
    open(jf, "w").write("\n".join(lines) + "\n")
    subprocess.Popen(["setsid", "nohup", QUEUE, jf], stdout=open(jf + ".out", "w"), stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL)
    print(f"queued {jf} (logs ~/qwen-opt/queue/logs/<job>.log)")
    return jf


def trace(a) -> None:
    out = os.path.join(K, "traces")
    enqueue(f"trace-{a.tag}", [f"klab-trace-{a.tag}|1500|~/qwen-opt/vcost|export GGML_HIP_PM4=0; BIN={a.bin} "
                               f"TOKENS={a.tokens} OUT=../klab/traces/{a.tag} taskset -c 2-5 ./prof_block.sh off"])
    print(f"-> klab profile {out}/{a.tag}/off")


def build_bench(var: str, flags: list[str], var_tree: str | None = None) -> str:
    """mmvqbig/bench.hip (cache-cold n=5 mmvq, base vs var, bitexact) with base = ~/wt/topka's kernel section and
    var = KLAB_VAR_TREE's (default ~/wt/topka, so pure -D sweeps compare like with like). -D flags are prepended to
    the VARIANT's kernel text only (base keeps its defaults; the #ifndef defaults in the var text are skipped). CPU."""
    vt = var_tree or os.environ.get("KLAB_VAR_TREE", os.path.join(HOME, "wt", "topka"))
    d = os.path.join(K, "build", var)
    os.makedirs(d, exist_ok=True)
    cut = lambda src: open(src).read().split("// Dedicated MoE multi-token kernel.")[0]
    open(os.path.join(d, "kern_base.inc"), "w").write(cut(f"{HOME}/wt/topka/ggml/src/ggml-cuda/mmvq.cu"))
    defines = "".join(f"#undef {m.group(1)}\n#define {m.group(1)} {m.group(2) or 1}\n"
                      for m in (re.match(r"-D(\w+)(?:=(.*))?$", f) for f in flags) if m)
    open(os.path.join(d, "kern_var.inc"), "w").write(defines + cut(f"{vt}/ggml/src/ggml-cuda/mmvq.cu"))
    fm = open(f"{HOME}/wt/topka/build-hip/ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/flags.make").read()
    defs = re.search(r"^HIP_DEFINES = (.*)$", fm, re.M).group(1).split()
    incs = re.search(r"^HIP_INCLUDES = (.*)$", fm, re.M).group(1).replace(
        f"{HOME}/wt/topka/", vt.rstrip("/") + "/").split()
    cmd = [os.path.join(HOME, "qwen-opt", "tools", "cpuheavy"), "--quiet", "/opt/rocm/core-10.0/lib/llvm/bin/clang++",
           "-x", "hip", *defs, *incs, f"-I{vt}/ggml/src/ggml-cuda", f"-I{d}", "-O3", "-DNDEBUG", "-std=gnu++17",
           "--offload-arch=gfx1100", "-Wno-unused-function", "-Wno-unused-variable", "-Wno-macro-redefined",
           *[f for f in flags if not f.startswith("-D")], "-save-temps=obj",
           os.path.join(HOME, "qwen-opt", "mmvqbig", "bench.hip"), "-o", os.path.join(d, "bench"),
           f"-L{HOME}/llama-topka/bin", "-lggml-base", f"-Wl,-rpath,{HOME}/llama-topka/bin:/opt/rocm/core-10.0/lib"]
    subprocess.run(cmd, check=True, cwd=d)
    return os.path.join(d, "bench")


def bench(a) -> None:
    b = build_bench(a.var, a.flags)
    log = os.path.join(K, "logs", f"bench-{a.var}.log")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    enqueue(f"bench-{a.var}", [f"klab-bench-{a.var}|600|/tmp|export GGML_HIP_PM4=0 LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib; {b} {a.filter} {a.rounds} "
                               f"2>&1 | tee {log}"])


def sweep(a) -> None:
    lines = []
    os.makedirs(os.path.join(K, "logs"), exist_ok=True)
    for i, fs in enumerate(a.flagsets):
        var = f"{a.name}-{i}"
        b = build_bench(var, fs.split())
        log = os.path.join(K, "logs", f"bench-{var}.log")
        open(log + ".flags", "w").write(fs)
        lines.append(f"klab-sw-{var}|600|/tmp|export GGML_HIP_PM4=0 LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib; {b} {a.filter} {a.rounds} 2>&1 | tee {log}")
    enqueue(f"sweep-{a.name}", lines)


def sweep_report(a) -> None:
    for log in sorted(glob.glob(os.path.join(K, "logs", f"bench-{a.name}-*.log"))):
        fl = open(log + ".flags").read() if os.path.exists(log + ".flags") else ""
        print(f"## {os.path.basename(log)}  [{fl}]")
        print(open(log).read().strip()[-3000:])


def gate(a) -> None:
    arms = " ".join(f'"{x}"' for x in (a.arms or ["X=0"]))
    enqueue(f"gate-{a.tag}", [f"klab-gate-{a.tag}|1800|~/qwen-opt/xtxroadmap|export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 "
                              f"GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0; LFM=1 ./p100_md5.sh {a.tag} {a.bin} {arms}"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("profile"); p.add_argument("dir"); p.add_argument("--bw", type=float, default=926.0)
    p.add_argument("--by", choices=["kernel", "type", "class"], default="kernel"); p.add_argument("--top", type=int, default=40)
    p.add_argument("--md", action="store_true"); p.set_defaults(f=profile)
    p = sp.add_parser("trace"); p.add_argument("tag"); p.add_argument("--bin", default=os.path.join(HOME, "llama-topka"))
    p.add_argument("--tokens", type=int, default=512); p.set_defaults(f=trace)
    p = sp.add_parser("isa"); p.add_argument("lib"); p.add_argument("--kernel", default="mul_mat_vec_q")
    p.add_argument("--out"); p.set_defaults(f=isa)
    p = sp.add_parser("isadiff"); p.add_argument("a"); p.add_argument("b"); p.add_argument("--kernel", required=True)
    p.add_argument("--full", action="store_true"); p.set_defaults(f=isadiff)
    p = sp.add_parser("bench"); p.add_argument("var"); p.add_argument("--filter", default="''")
    p.add_argument("--rounds", type=int, default=5); p.add_argument("flags", nargs="*"); p.set_defaults(f=bench)
    p = sp.add_parser("sweep"); p.add_argument("name"); p.add_argument("flagsets", nargs="+")
    p.add_argument("--filter", default="''"); p.add_argument("--rounds", type=int, default=5); p.set_defaults(f=sweep)
    p = sp.add_parser("sweep-report"); p.add_argument("name"); p.set_defaults(f=sweep_report)
    p = sp.add_parser("gate"); p.add_argument("tag"); p.add_argument("bin"); p.add_argument("arms", nargs="*")
    p.set_defaults(f=gate)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
