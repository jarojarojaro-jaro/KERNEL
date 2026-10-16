"""R23: the implementer's diff must not touch what measures it (G0 deny-list, fk/diffscan.py)."""
from fk.diffscan import deny_findings
from rules import RulePolicy
from rules._util import diff_files

POLICY = RulePolicy(
    "R23", "deny-list", ("static",), "block", "REFUSE",
    source="threat T1 (15f §5.4): speed-up by changing the measuring surface (Sakana §6.3 protocol switch; "
           "GPU MODE timer monkeypatch); backtest: 0 of 70 amd-opt patches hit the list",
    lesson="lekcja-agent-zmienia-protokol", failure_mode="lekcja")


def check(ctx):
    f = diff_files(ctx)
    return deny_findings(f) if f is not None else []
