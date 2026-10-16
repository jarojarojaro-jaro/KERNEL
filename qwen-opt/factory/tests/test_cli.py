"""The CLI as other agents call it (subprocess), on a sandbox ledger; runs land in a temp FACTORY_RUNS."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import _path  # noqa: F401
from fk import block
from sandbox import Sandbox

CLI = Path(__file__).resolve().parent.parent / "factory"


class CLI_(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()
        self.env = dict(os.environ, FACTORY_RUNS=str(self.sb.root / "runs"), FACTORY_CACHE=str(self.sb.root / "cache"))

    def tearDown(self):
        self.sb.close()

    def run_cli(self, *args, ok=True):
        r = subprocess.run([str(CLI), *args, "--ledger", str(self.sb.ledger_path)], capture_output=True, text=True,
                           env=self.env, timeout=300)
        if ok is not None:
            self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r.stdout

    def test_flow(self):
        self.sb.make_card(register=False)
        card = str(self.sb.card_path)
        self.assertIn("OK", self.run_cli("card", "check", card))
        self.assertIn("registered", self.run_cli("register", card))
        self.assertIn("already registered", self.run_cli("register", card))
        out = self.run_cli("verify", card, "--fake", "--model", str(self.sb.model), "--pause", "0")
        self.assertEqual(json.loads(out.strip().splitlines()[-1])["verdict"], "CONFIRMED")
        self.assertIn("chain OK", self.run_cli("ledger", "verify"))
        self.assertIn("CONFIRMED", self.run_cli("report"))
        self.assertIn("merge: OK", self.run_cli("merge-check", self.sb.cand))
        self.assertIn("BLOCKED", self.run_cli("merge-check", self.sb.base, ok=False))
        self.assertIn("= lock seq", self.run_cli("harness", "status"))
        self.assertTrue((self.sb.root / "runs").is_dir())

    def test_dry_run_cli(self):
        self.sb.make_card()
        out = self.run_cli("verify", str(self.sb.card_path), "--dry-run", "--model", str(self.sb.model))
        self.assertIn("flock /tmp/gpu.lock flock /tmp/quiet.lock", out)
        self.assertIn("GPU blocks planned", out)

    def test_rules_and_sealed(self):
        self.assertIn("0 mismatches", self.run_cli("rules", "test"))
        self.assertIn("OK", self.run_cli("sealed", "check"))
        out = self.run_cli("rules", "text", str(Path(__file__).resolve().parent.parent /
                                                 "rules/fixtures/road-to-65_s16.txt"), ok=False)
        self.assertIn("1075 GB/s", out)


class BlockRefusal(unittest.TestCase):
    def test_busy_cpu_refuses_block(self):
        sb = Sandbox()
        try:
            spec = sb.root / "spec.json"
            spec.write_text(json.dumps({"name": "x", "kind": "serve", "out": str(sb.root / "out.json"), "port": 18496}))
            busy = {"loadavg": [30.0, 30.0, 30.0], "nproc": 16, "user_server": False, "llama_servers": []}
            with mock.patch("fk.preflight.snapshot", return_value=busy), mock.patch("fk.preflight._pgrep",
                                                                                     return_value=[]), \
                    mock.patch.object(block, "LOAD_RETRIES", 0):
                self.assertEqual(block.main(str(spec)), 98)
            res = json.loads((sb.root / "out.json").read_text())
            self.assertTrue(res["refused"][0].startswith("R15"))
            with mock.patch("fk.preflight._pgrep", return_value=["1 llama-server --port 8080"]):
                self.assertEqual(block.main(str(spec)), 97)
        finally:
            sb.close()


if __name__ == "__main__":
    unittest.main()
