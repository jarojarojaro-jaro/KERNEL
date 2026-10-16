"""R16: no merge of a commit that is UNMEASURED or has no CONFIRMED verdict in the ledger."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R16", "unmeasured-merge", ("merge",), "block", "REFUSE",
    source="patches 0066-0070 were committed with 'UNMEASURED' (no GPU in that round) and measured later; "
           "KERNEL/qwen-opt/patches/llama.cpp-amd-opt/0066..0070",
    lesson="lekcja-commity-bez-pomiaru", failure_mode="07#16")


def check(ctx):
    if "commit" not in ctx:
        return []
    out = []
    if "UNMEASURED" in (ctx.get("commit_message") or ""):
        out.append("commit message says UNMEASURED")
    c = ctx["commit"]
    ok = [r for r in ctx.get("ledger_rows") or [] if r.get("kind") == "verdict" and r.get("verdict") == "CONFIRMED"
          and str((r.get("commits") or {}).get("cand", "")).startswith(c[:9])]
    if not ok:
        out.append(f"no CONFIRMED ledger verdict for {c[:12]}")
    return out
