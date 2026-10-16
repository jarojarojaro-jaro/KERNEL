"""R06: an Amdahl budget taken from rocprofv3 while PM4 replay is on is not evidence (rocprof sees no PM4 dispatches)."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R06", "pm4-profile-source", ("static",), "block", "INVALID",
    source="after 0060 kernels go through the PM4 tape and rocprofv3 does not see them, PMC counters read 0; profile "
           "with GGML_HIP_PM4=0 or GGML_HIP_PM4_DEBUG=3 (pm4trace); NOTES.md:256, 0061",
    lesson="pm4-niewidoczne-w-rocprof", failure_mode="07#6")


def check(ctx):
    src = ((ctx.get("card") or {}).get("attacked") or {}).get("source") or {}
    if src.get("tool") not in ("rocprofv3", "rocprof"):
        return []
    if str((src.get("env") or {}).get("GGML_HIP_PM4", "1")) != "0":
        return ["attacked.share_ms comes from rocprofv3 with PM4 on: profile with GGML_HIP_PM4=0 or PM4_DEBUG=3"]
    return []
