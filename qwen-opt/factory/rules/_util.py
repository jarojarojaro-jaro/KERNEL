"""Helpers shared by the rules."""
from __future__ import annotations

import re
import statistics

from fk.diffscan import parse_unified


def diff_files(ctx):
    if "diff" not in ctx:
        return None
    return parse_unified(ctx["diff"])


def touched(ctx) -> list[str] | None:
    f = diff_files(ctx)
    if f is None:
        return (ctx.get("card") or {}).get("touched_paths")
    return sorted({x.path for x in f})


def ok_runs(ctx):
    return [r for r in ctx.get("runs") or [] if r.get("ok", True)]


def by_arm(ctx) -> dict[str, list[dict]]:
    out = {}
    for r in ok_runs(ctx):
        out.setdefault(r["arm"], []).append(r)
    return out


def metric_of(ctx) -> str | None:
    return (ctx.get("card") or {}).get("metric")


def med(xs):
    return statistics.median(xs) if xs else None


# HIP-only conditions; AMD_*_AVAILABLE (AMD_WMMA_AVAILABLE, AMD_MFMA_AVAILABLE) are defined only for HIP in common.cuh
HIP_GUARD = re.compile(r"GGML_USE_HIP|__HIP_PLATFORM_AMD__|\bRDNA\w*|\bCDNA\w*|\bGCN\w*|GGML_HIP\w*|__gfx\w+|"
                       r"\bAMD_\w+")


def hip_only_lines(src: str, seed: set[str] | None = None, derived_out: set[str] | None = None) -> set[int]:
    """1-based line numbers inside preprocessor branches that only HIP compiles. A macro #defined inside such a
    branch (e.g. V_DOT2_F32_F16_AVAILABLE, FATTN_KVQ_AVAILABLE) makes later #if/#ifdef on it HIP-only as well;
    seed: such macros from other headers (common.cuh); derived_out collects the ones defined here."""
    derived: set[str] = set(seed or ())
    stack: list[list[bool]] = []  # [branch is HIP-only, the #else branch is HIP-only]
    out = set()

    def hip_cond(cond: str) -> bool:
        if "||" in cond:  # HIP-only only if every alternative is
            return all(hip_cond(part) for part in cond.split("||"))
        if HIP_GUARD.search(cond):
            return True
        return any(re.search(r"\b" + re.escape(m) + r"\b", cond) for m in derived)

    for n, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        m = re.match(r"#\s*(ifdef|ifndef|if|elif|else|endif|define)\b\s*(.*)", s)
        if m:
            kw, cond = m.group(1), re.sub(r"//.*|/\*.*?\*/", "", m.group(2))
            if kw in ("if", "ifdef", "ifndef"):
                neg = kw == "ifndef" or (kw == "if" and cond.lstrip().startswith("!"))
                simple_neg = neg and not re.search(r"&&|\|\|", cond)
                hip = hip_cond(cond)
                stack.append([hip and not neg, hip and simple_neg])
            elif kw == "elif" and stack:
                stack[-1] = [hip_cond(cond) and not cond.lstrip().startswith("!"), False]
            elif kw == "else" and stack:
                stack[-1] = [stack[-1][1], False]
            elif kw == "endif" and stack:
                stack.pop()
            elif kw == "define" and any(f[0] for f in stack) and cond.split():
                derived.add(cond.split()[0].split("(")[0])
            continue
        if any(f[0] for f in stack):
            out.add(n)
    if derived_out is not None:
        derived_out |= derived
    return out


def hip_macros(ctx) -> set[str]:
    """HIP-only macros defined in ctx['hip_headers'] (the verifier passes common.cuh of the candidate) and in every
    file of files_after (two passes, so the order of files does not matter)."""
    seed: set[str] = set()
    srcs = list((ctx.get("hip_headers") or {}).values()) + list((ctx.get("files_after") or {}).values())
    for _ in range(2):
        for s in srcs:
            hip_only_lines(s, seed, seed)
    return seed
