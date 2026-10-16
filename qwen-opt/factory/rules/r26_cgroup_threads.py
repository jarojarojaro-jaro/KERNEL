"""R26: in a container the CPU quota, not nproc, sets llama.cpp threads (-t)."""
import math

from rules import RulePolicy

POLICY = RulePolicy(
    "R26", "cgroup-threads", ("preflight", "static"), "warn", "NEEDS-HUMAN",
    source="RunPod A40: nproc 96, cgroup quota 7.65 CPU, llama-server took 96 threads (needs -t 6 -tb 6); Vast 5060 Ti "
           "nproc 64 vs 7.68",
    lesson="lekcja-limit-cpu-kontenera", failure_mode="lekcja")


def threads(argv):
    for i, a in enumerate(argv or []):
        if a in ("-t", "--threads") and i + 1 < len(argv):
            return int(argv[i + 1])
    return None


def check(ctx):
    s = ctx.get("snapshot") or {}
    q = s.get("cpu_quota")
    if not q or q >= (s.get("nproc") or 0):
        return []
    out = []
    for arm, argv in sorted((ctx.get("server_argv") or {}).items()):
        t = threads(argv)
        if t is None or t > math.ceil(q):
            out.append(f"arm {arm}: threads {t or 'default=nproc ' + str(s.get('nproc'))} > cgroup quota {q:.2f}")
    return out
