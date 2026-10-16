"""R32: both arms run the identical server command line (only the build directory and nothing else differs)."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R32", "arms-same-flags", ("static", "measurement"), "block", "INVALID",
    source="MTP pilot (11-mtp-pl-pilot.md:80,182): the MTP block in Q6_K instead of IQ4_XS alone is +0.45% tok/step "
           "offline; a flag like --spec-mtp-type differing between arms fakes a kernel effect",
    lesson="lekcja-mtp-glowica-optimum", failure_mode="lekcja")


def normalize(argv):
    out = []
    for i, a in enumerate(argv):
        if i == 0:
            out.append(a.rsplit("/", 1)[-1])
        elif argv[i - 1] == "--port":
            out.append("<port>")
        else:
            out.append(a)
    return out


def check(ctx):
    sa = ctx.get("server_argv") or {}
    if "A" not in sa or "B" not in sa:
        return []
    a, b = normalize(sa["A"]), normalize(sa["B"])
    if a == b:
        return []
    diff = [f"{x!r} vs {y!r}" for x, y in zip(a, b) if x != y] or [f"length {len(a)} vs {len(b)}"]
    return ["server flags differ between arms: " + "; ".join(diff[:4])]
