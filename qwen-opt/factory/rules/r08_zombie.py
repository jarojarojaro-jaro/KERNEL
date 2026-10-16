"""R08: no foreign llama-server, no other KFD process, no VRAM held before our server starts."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R08", "zombie-shared-vram", ("preflight",), "block", "REFUSE",
    source="DFlash server hung on SIGTERM, the next MTP run shared VRAM: 5.6 t/s (spec_sweep.jsonl 2026-10-10 22:48); "
           "agent K4 left a server on port 8097 holding VRAM; NOTES.md:160,300",
    lesson="lekcja-zombie-serwery", failure_mode="07#8")

VRAM_IDLE_MAX = 2 << 30


def check(ctx):
    s = ctx.get("snapshot")
    if not s:
        return []
    out = []
    if s.get("user_server"):
        out.append("production llama-server on port 8080 is running")
    for l in s.get("llama_servers") or []:
        out.append(f"foreign llama-server: {l[:120]}")
    for p in s.get("kfd_procs") or []:
        if "keepawake" not in p.get("cmd", ""):
            out.append(f"process {p.get('pid')} holds a KFD (GPU) context: {p.get('cmd', '')[:80]}")
    if (s.get("vram_used") or 0) > VRAM_IDLE_MAX:
        out.append(f"VRAM in use before start: {s['vram_used'] / 2**30:.1f} GiB")
    if s.get("port_free") is False:
        out.append(f"port {s.get('port')} is taken")
    return out
