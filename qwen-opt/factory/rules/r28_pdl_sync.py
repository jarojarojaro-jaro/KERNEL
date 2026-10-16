"""R28: a kernel launched through ggml_cuda_kernel_launch (PDL on sm_90+) must call ggml_cuda_pdl_sync."""
import re

from rules import RulePolicy
from rules._util import hip_macros, hip_only_lines

POLICY = RulePolicy(
    "R28", "pdl-sync", ("static",), "warn", "NEEDS-HUMAN",
    source="0053 norm_router_topk_f32 and 0057 attn_prep_f32 launched via ggml_cuda_kernel_launch without "
           "ggml_cuda_pdl_sync: stale reads on sm_120; found by review, fixed in cuda-compat 14506801c "
           "(llama-master topk-moe.cu at c15c84e83 vs 14506801c)",
    lesson="lekcja-pdl-sm120", failure_mode="lekcja")

KERNEL = re.compile(r"__global__\s+(?:__launch_bounds__\([^)]*\)\s*)?void\s+(\w+)\s*\(")


def kernels(src: str) -> dict[str, tuple[int, str]]:
    """name -> (line, body) of every __global__ kernel (brace matching from the first { after the signature)."""
    out = {}
    for m in KERNEL.finditer(src):
        i = src.find("{", m.end())
        if i < 0:
            continue
        depth, j = 0, i
        while j < len(src):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out[m.group(1)] = (src.count("\n", 0, m.start()) + 1, src[i:j + 1])
    return out


def check(ctx):
    out = []
    seed = hip_macros(ctx)
    for path, src in sorted((ctx.get("files_after") or {}).items()):
        if not re.search(r"\.(cu|cuh)$", path):
            continue
        hip = hip_only_lines(src, seed)  # HIP has no PDL: kernels compiled only for HIP are exempt
        for name, (line, body) in kernels(src).items():
            if line in hip:
                continue
            if re.search(r"ggml_cuda_kernel_launch\s*\(\s*" + re.escape(name) + r"\b", src) and \
                    "ggml_cuda_pdl_sync" not in body:
                out.append(f"{path}: kernel {name} is launched with PDL but never calls ggml_cuda_pdl_sync()")
    return out
