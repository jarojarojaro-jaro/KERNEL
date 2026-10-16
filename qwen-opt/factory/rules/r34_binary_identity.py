"""R34: the measured binaries are the declared ones: sha256 as in the card, the switch compiled in, the commit inside."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R34", "binary-identity", ("static",), "block", "INVALID",
    source="threat T5 (15f §5.4): WSL silently skips PM4 (WSLKMT_VENDOR_PACKET), LD_LIBRARY_PATH picks another build; "
           "in ~/llama-opt f61994f58 is in lib/libllama-common.so.0.6.0 and GGML_HIP_MMQ_EPI in libggml-hip.so.0.26.0",
    lesson="lekcja-label-to-nie-binarka", failure_mode="lekcja")


def check(ctx):
    idt = ctx.get("identity")
    if not idt:
        return []
    out = []
    for arm, bad in sorted((idt.get("sha_mismatch") or {}).items()):
        if bad:
            out.append(f"build {arm}: sha256 differs from the card for {', '.join(bad[:4])}")
    if "switch_hits" in idt and not idt["switch_hits"]:
        out.append(f"switch {idt.get('switch')} not found in any candidate library (not compiled in?)")
    if "commit_hits" in idt and not idt["commit_hits"]:
        out.append(f"commit {idt.get('commit', '')[:9]} not found in the candidate libraries (other build?)")
    if "base_commit_hits" in idt and not idt["base_commit_hits"]:
        out.append(f"base commit {idt.get('base_commit', '')[:9]} not found in the base libraries (other build?)")
    return out
