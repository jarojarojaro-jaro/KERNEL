"""R27: upstream -fit on mis-sizes speculative buffers; never measure spec with -fit on."""
from rules import RulePolicy

POLICY = RulePolicy(
    "R27", "fit-with-spec", ("static", "measurement"), "block", "INVALID",
    source="RTX 5060 Ti 16 GB, upstream -fit on + MTP: 7.7 t/s (MTP work left on CPU), -fit off -ngl 99 -t 8: 31.8; "
           "Nemotron DFlash on 3090: 67 vs 95 t/s (2026-10-16)",
    lesson="lekcja-fit-mtp-16gb", failure_mode="lekcja")


def check(ctx):
    out = []
    for arm, argv in sorted((ctx.get("server_argv") or {}).items()):
        a = list(argv)
        fit = any(x in ("-fit", "--fit") and i + 1 < len(a) and a[i + 1] == "on" for i, x in enumerate(a))
        spec = "--spec-type" in a or "-md" in a
        if fit and spec:
            out.append(f"arm {arm}: -fit on with speculative decoding")
    return out
