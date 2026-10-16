"""R29: HIP/AMDGPU-only constructs in shared CUDA/HIP sources must sit under a HIP guard (nvcc rejects them)."""
import re

from rules import RulePolicy
from rules._util import hip_macros, hip_only_lines

POLICY = RulePolicy(
    "R29", "hip-only-guard", ("static",), "warn", "NEEDS-HUMAN",
    source="0070 added ggml_cuda_mmq_epi_pin (ext_vector_type, asm \"+v\") to mmq-vec-dot.cuh outside any guard: 25 "
           "CUDA TUs failed; fixed in cuda-compat 57e0bdfe4 (#if defined(GGML_USE_HIP))",
    lesson="lekcja-build-cuda-0057-0070", failure_mode="lekcja")

HIP_ONLY = re.compile(r"ext_vector_type|__builtin_amdgcn_|asm\s*(?:volatile\s*)?\([^;]*\"\+?v\"")


def check(ctx):
    out = []
    seed = hip_macros(ctx)
    for path, src in sorted((ctx.get("files_after") or {}).items()):
        if not re.search(r"ggml-cuda/.*\.(cu|cuh)$", path):
            continue
        hip = hip_only_lines(src, seed)
        for n, line in enumerate(src.splitlines(), 1):
            code = line.split("//", 1)[0]
            if n not in hip and HIP_ONLY.search(code):
                out.append(f"{path}:{n}: HIP-only construct outside a HIP guard: {line.strip()[:80]}")
    return out
