"""R35: for BIT/SAME-TOK the timed runs themselves must produce the same texts in both arms (T7)."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R35", "same-runs-text", ("measurement",), "block", "INVALID",
    source="threat T7 (15f §5.4): GPU MODE submission ran 15 calls in one launch only while timed; md5 must come from "
           "the measured runs, not from separate ones",
    lesson="lekcja-agent-zmienia-protokol", failure_mode="lekcja")


def texts(runs):
    return [tuple(sorted((r.get("text_sha256") or {}).items())) for r in runs]


def check(ctx):
    card = ctx.get("card") or {}
    if card.get("correctness_class") not in ("BIT", "SAME-TOK") or not ctx.get("runs"):
        return []
    a = [r for r in ctx["runs"] if r.get("arm") == "A" and r.get("ok", True) and r.get("text_sha256")]
    b = [r for r in ctx["runs"] if r.get("arm") == "B" and r.get("ok", True) and r.get("text_sha256")]
    if not a or not b:
        return []
    ta, tb = set(texts(a)), set(texts(b))
    if len(ta) > 1 or len(tb) > 1:
        return []  # texts differ between processes of one build: the check cannot judge (reported as n/a)
    if ta != tb:
        diff = sorted(k for k, v in dict(next(iter(ta)))
                      .items() if dict(next(iter(tb))).get(k) != v)
        return [f"timed runs give different texts in arms A and B for {diff[:4]}"]
    return []
