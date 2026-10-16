import json
import unittest
from pathlib import Path

import _path  # noqa: F401
import rules
from rules.r21_anomaly_breaker import history_flags

SPEC_SWEEP = Path.home() / "qwen-opt/spec_sweep.jsonl"
FUSION_SWEEP = Path.home() / "qwen-opt/fusion/spec_sweep.jsonl"


class Rules(unittest.TestCase):
    def test_every_rule_has_fire_and_clean_fixture(self):
        rs = rules.load_rules()
        self.assertGreaterEqual(len(rs), 36)
        for r in rs:
            cases = rules.load_fixture(r.policy.id)
            self.assertIn("fire", {c["expect"] for c in cases}, r.policy.id)
            self.assertIn("clean", {c["expect"] for c in cases}, r.policy.id)
            for c in cases:
                self.assertTrue(c.get("source"), (r.policy.id, c["name"]))
                got = r.check(c["ctx"])
                self.assertEqual(bool(got), c["expect"] == "fire", (r.policy.id, c["name"], got))

    def test_all_17_failure_modes_covered(self):
        modes = {r.policy.failure_mode for r in rules.load_rules()}
        for n in range(1, 18):
            self.assertIn(f"07#{n}", modes)

    def test_run_by_stage(self):
        f = rules.run("preflight", {"snapshot": {"user_server": True, "loadavg": [0.1, 0, 0], "nproc": 16}})
        self.assertEqual([x.rule for x in f], ["R08"])
        self.assertEqual(rules.run("static", {}), [])

    @unittest.skipUnless(SPEC_SWEEP.exists(), "no spec_sweep.jsonl")
    def test_anomaly_backtest_real_history(self):
        rows = [json.loads(l) for l in SPEC_SWEEP.read_text().splitlines() if l.strip()]
        flags = history_flags(rows)
        self.assertIn(15, [i for i, _, _ in flags])          # 2026-10-10 22:48, 5.6 t/s
        self.assertLessEqual(len(flags) - 1, 0.03 * len(rows))  # X1 kill criterion: FP <= 3 %

    @unittest.skipUnless(FUSION_SWEEP.exists(), "no fusion/spec_sweep.jsonl")
    def test_label_drift_real_history(self):
        rows = [json.loads(l) for l in FUSION_SWEEP.read_text().splitlines() if l.strip()]
        msgs = [f.message for f in rules.run("history", {"history": rows}) if f.rule == "R20"]
        self.assertTrue(any("r1-base-qwen" in m for m in msgs))


if __name__ == "__main__":
    unittest.main()
