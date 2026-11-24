#!/usr/bin/env python3
"""gfx1100 (RDNA3, wave32) binary drift gate: the HIP equivalent of ashhart's sass-and-air-diff/binary_gate.py.

Snapshot sources (merge any of them into one snapshot, keyed by demangled kernel name):
  --trace    rocprofv3 *_kernel_trace.csv : VGPR/SGPR/LDS/scratch of kernels that actually DISPATCHED (served proof)
  --remarks  build log with -Rpass-analysis=kernel-resource-usage   (the `ptxas -v` equivalent)
  --asm      hipcc --save-temps *-hip-amdgcn-amd-amdhsa-gfx1100.s   (instruction-stream sha256, scratch/WMMA/barrier ops,
             "; NumVgprs/ScratchSize/Occupancy" kernel-info) or `llvm-objdump -d` text of an unbundled code object
  --notes    `llvm-readelf --notes code.hsaco` (AMDGPU metadata: .vgpr_count, .vgpr_spill_count, ...)
Snapshot JSON uses binary_gate.py's schema ({"kernels": {name: {sha256, registers, spill_stores, smem_bytes, ...}}}),
so ashhart's `binary_gate.py diff` also accepts it; our `diff` adds occupancy cliffs and scratch.

Exit codes: 0 PASS, 1 REGRESSION, 2 usage/parse error.  Stdlib only.
"""
import argparse, csv, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

# gfx1100/1101/1151: 1536 VGPRs per SIMD lane-slot in wave32, alloc granule 24, max 16 waves/SIMD, 128 KiB LDS per WGP.
# (gfx1102/1103: 1024 VGPRs, granule 16.)  Estimate only; the compiler's "; Occupancy:" wins when present.
ARCH = {"gfx1100": (1536, 24, 16, 131072), "gfx1101": (1536, 24, 16, 131072), "gfx1151": (1536, 24, 16, 131072),
        "gfx1102": (1024, 16, 16, 131072), "gfx1201": (1536, 24, 16, 131072)}


def occupancy(arch, vgpr, lds=0, wg=0):
    total, gran, maxw, lds_wgp = ARCH[arch]
    if vgpr <= 0:
        return None
    occ = min(maxw, total // (-(-vgpr // gran) * gran))
    if lds > 0 and wg > 0:
        waves_per_wg = -(-wg // 32)
        occ = min(occ, (lds_wgp // lds) * waves_per_wg // 4)
    return occ


_demangle_cache = {}


def demangle(names):
    todo = [n for n in names if n not in _demangle_cache]
    exe = shutil.which("llvm-cxxfilt") or shutil.which("c++filt")
    if todo and exe:
        out = subprocess.run([exe], input="\n".join(todo), capture_output=True, text=True).stdout.splitlines()
        _demangle_cache.update(zip(todo, out if len(out) == len(todo) else todo))
    return [_demangle_cache.get(n, n) for n in names]


def key(n):  # rocprof prints "void f<...>(args)"; c++filt drops the return type of templates differently: normalize
    n = n.replace("void ", "", 1) if n.startswith("void ") else n
    return re.sub(r"\s+", " ", n.split(".kd")[0]).strip()


def from_trace(path, arch, snap):
    for r in csv.DictReader(open(path)):
        name = key(r["Kernel_Name"])
        if name.startswith("__amd_rocclr"):
            continue
        k = snap.setdefault(name, {})
        v, s = int(r["VGPR_Count"]), int(r["SGPR_Count"])
        lds, scr = int(r["LDS_Block_Size"]), int(r["Scratch_Size"])
        wg = int(r.get("Workgroup_Size_X") or 1) * int(r.get("Workgroup_Size_Y") or 1) * int(r.get("Workgroup_Size_Z") or 1)
        k.update(registers=v, sgprs=s, agprs=int(r.get("Accum_VGPR_Count") or 0), smem_bytes=lds, scratch_bytes=scr,
                 occupancy_est=occupancy(arch, v, lds, wg), dispatched=k.get("dispatched", 0) + 1)


REMARK = re.compile(r"remark: .*?:\s+(Function Name|SGPRs|VGPRs|AGPRs|ScratchSize \[bytes/lane\]|Occupancy \[waves/SIMD\]|"
                    r"SGPRs Spill|VGPRs Spill|LDS Size \[bytes/block\]):\s*(\S+)")
REMARK_KEYS = {"SGPRs": "sgprs", "VGPRs": "registers", "AGPRs": "agprs", "ScratchSize [bytes/lane]": "scratch_bytes",
               "Occupancy [waves/SIMD]": "occupancy", "SGPRs Spill": "sgpr_spills", "VGPRs Spill": "spill_stores",
               "LDS Size [bytes/block]": "smem_bytes"}


def from_remarks(path, arch, snap):
    cur = None
    raw = []
    for line in open(path, errors="replace"):
        m = REMARK.search(line)
        if not m:
            continue
        f, val = m.group(1), m.group(2)
        if f == "Function Name":
            cur = {"_mangled": val}
            raw.append(cur)
        elif cur is not None:
            cur[REMARK_KEYS[f]] = int(val)
    for rec, name in zip(raw, demangle([r.pop("_mangled") for r in raw])):
        snap.setdefault(key(name), {}).update(rec)


SAVE_TEMPS_FN = re.compile(r"^([A-Za-z_.$][\w.$]*):\s*(?:;.*)?$")       # "_Z3fooPf:" (function label)
OBJDUMP_FN = re.compile(r"^[0-9a-fA-F]+ <([^>]+)>:\s*$")                # "0000000000001900 <_Z3fooPf>:"
KINFO = re.compile(r"^;\s*(NumVgprs|NumAgprs|NumSgprs|ScratchSize|Occupancy|LDSByteSize|codeLenInByte):\s*(\d+)")
KINFO_KEYS = {"NumVgprs": "registers", "NumAgprs": "agprs", "NumSgprs": "sgprs", "ScratchSize": "scratch_bytes",
              "Occupancy": "occupancy", "LDSByteSize": "smem_bytes", "codeLenInByte": "code_bytes"}
SPILL_OP = re.compile(r"^(scratch_(store|load)|buffer_(store|load)_\w+.*\boff(set)?\b.*s\[0:3\])")
SGPR_SPILL = re.compile(r"^v_(writelane|readlane)_b32")
WMMA = re.compile(r"^v_wmma_")
BARRIER = re.compile(r"^s_barrier")
LABEL = re.compile(r"\.LBB\d+_\d+|<[^>]+\+0x[0-9a-f]+>")


def from_asm(path, arch, snap):
    fns, cur, last_fn = {}, None, None
    for line in open(path, errors="replace"):
        s = line.rstrip("\n")
        m = OBJDUMP_FN.match(s) or (SAVE_TEMPS_FN.match(s) if not s.startswith(".") else None)
        if m and not m.group(1).startswith(".L"):
            cur = fns.setdefault(m.group(1), {"ins": [], "info": {}})
            last_fn = m.group(1)
            continue
        if s.strip().startswith("; -- End function"):
            cur = None
            continue
        km = KINFO.match(s.strip())
        if km and last_fn:  # "; Kernel info:" block follows the function (in .AMDGPU.csdata)
            fns[last_fn]["info"][KINFO_KEYS[km.group(1)]] = int(km.group(2))
            continue
        if cur is None:
            continue
        body = s.split(";")[0].split("//")[0].strip()
        body = re.sub(r"^[0-9a-f]+:\s+", "", body)        # objdump address column (use --no-show-raw-insn)
        if not body or body.startswith(".") or body.endswith(":"):
            continue
        cur["ins"].append(LABEL.sub("L", " ".join(body.split())))
    names = list(fns)
    for mangled, name in zip(names, demangle(names)):
        f = fns[mangled]
        if not f["ins"] and not f["info"]:
            continue
        ins = f["ins"]
        rec = {"sha256": hashlib.sha256("\n".join(ins).encode()).hexdigest(), "instructions": len(ins),
               "spill_ops": sum(1 for i in ins if SPILL_OP.match(i)), "sgpr_spill_ops": sum(1 for i in ins if SGPR_SPILL.match(i)),
               "mma_ops": sum(1 for i in ins if WMMA.match(i)), "barrier_ops": sum(1 for i in ins if BARRIER.match(i)),
               **f["info"]}
        snap.setdefault(key(name), {}).update(rec)


def from_notes(path, arch, snap):
    items, cur = [], None
    for line in open(path, errors="replace"):
        if re.match(r"^\s*- \.\w", line):
            cur = {}
            items.append(cur)
        m = re.match(r"^\s*-?\s*\.(\w+):\s*'?([^'\n]*)'?\s*$", line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2)
    ks = [i for i in items if "name" in i and "vgpr_count" in i]
    for it, name in zip(ks, demangle([i["name"] for i in ks])):
        rec = {"registers": int(it["vgpr_count"]), "sgprs": int(it.get("sgpr_count", 0)),
               "spill_stores": int(it.get("vgpr_spill_count", 0)), "sgpr_spills": int(it.get("sgpr_spill_count", 0)),
               "scratch_bytes": int(it.get("private_segment_fixed_size", 0)),
               "smem_bytes": int(it.get("group_segment_fixed_size", 0))}
        rec["occupancy_est"] = occupancy(arch, rec["registers"], rec["smem_bytes"], int(it.get("max_flat_workgroup_size", 0)))
        snap.setdefault(key(name), {}).update(rec)


def cmd_snap(a):
    snap = {}
    for src, fn in (("trace", from_trace), ("remarks", from_remarks), ("asm", from_asm), ("notes", from_notes)):
        for p in getattr(a, src) or []:
            fn(p, a.arch, snap)
    if not snap:
        raise SystemExit("hip_binary_gate: no kernels parsed")
    Path(a.out).write_text(json.dumps({"format": "hip-binary-gate-v1", "arch": a.arch, "kernels": snap}, indent=1) + "\n")
    bad = [n for n, k in snap.items() if k.get("spill_stores") or k.get("scratch_bytes") or k.get("spill_ops")]
    print(f"snapshot: {len(snap)} kernels, {len(bad)} with spills/scratch -> {a.out}")
    for n in bad:
        k = snap[n]
        print(f"  [SCRATCH] {n[:100]}: vgpr_spill={k.get('spill_stores', 0)} scratch={k.get('scratch_bytes', 0)}B "
              f"scratch_ops={k.get('spill_ops', 0)}")
    return 0


STRICT = ("sha256", "instructions", "registers", "sgprs", "agprs", "spill_stores", "sgpr_spills", "spill_ops",
          "scratch_bytes", "smem_bytes", "occupancy", "occupancy_est")
SPILLS = ("spill_stores", "sgpr_spills", "spill_ops", "scratch_bytes")


def cmd_diff(a):
    base = json.loads(Path(a.base).read_text())["kernels"]
    cand = json.loads(Path(a.cand).read_text())["kernels"]
    allow = a.allow_changed or []
    allowed = lambda n: any(p in n for p in allow)
    fails, notes = [], []
    for n in sorted(set(base) | set(cand)):
        b, c = base.get(n), cand.get(n)
        if c is None:
            (notes if allowed(n) else fails).append(f"[MISSING]   {n}")
            continue
        if b is None:
            notes.append(f"[ADDED]     {n}  vgpr={c.get('registers')} occ={c.get('occupancy', c.get('occupancy_est'))}")
            if any(c.get(m) for m in SPILLS) and a.forbid_new_spills:
                fails.append(f"[SPILL]     {n}: new kernel with spills/scratch")
            continue
        d = [f"{m} {b[m]}->{c[m]}" if m != "sha256" else "sha256 changed"
             for m in STRICT if m in b and m in c and b[m] != c[m]]
        if not d:
            continue
        new_spill = [m for m in SPILLS if not b.get(m) and c.get(m)]
        occ_m = "occupancy" if "occupancy" in b and "occupancy" in c else "occupancy_est"
        occ_drop = (b.get(occ_m) or 0) > (c.get(occ_m) or 0) > 0
        if allowed(n):
            notes.append(f"[ALLOWED]   {n}: {', '.join(d)}")
            if a.forbid_new_spills and new_spill:
                fails.append(f"[SPILL]     {n}: {', '.join(new_spill)} 0->nonzero")
            if a.forbid_occupancy_drop and occ_drop:
                fails.append(f"[OCCUPANCY] {n}: {occ_m} {b[occ_m]}->{c[occ_m]} waves/SIMD")
        else:
            fails.append(f"[UNTOUCHED] {n}: {', '.join(d)}")
    for line in notes + fails:
        print("  " + line)
    print(f"binary diff: {len(base)} -> {len(cand)} kernels | failures={len(fails)}")
    print("HIP BINARY GATE: " + ("REGRESSION" if fails else "PASS"))
    return 1 if fails else 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snap")
    for f in ("trace", "remarks", "asm", "notes"):
        s.add_argument(f"--{f}", action="append")
    s.add_argument("--arch", default="gfx1100", choices=sorted(ARCH))
    s.add_argument("--out", required=True)
    d = sub.add_parser("diff")
    d.add_argument("base")
    d.add_argument("cand")
    d.add_argument("--allow-changed", action="append", help="kernel-name substring you meant to change (or remove)")
    d.add_argument("--forbid-new-spills", action="store_true")
    d.add_argument("--forbid-occupancy-drop", action="store_true")
    a = p.parse_args()
    return cmd_snap(a) if a.cmd == "snap" else cmd_diff(a)


if __name__ == "__main__":
    sys.exit(main())
