"""End-to-end verifier on fake data: verdicts, refusals, ledger rows, dry-run, and the real block path against a CPU
stand-in llama-server (no GPU, no locks: GPU_WRAP and the pgrep check are replaced in-process)."""
import io
import json
import os
import subprocess
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

import _path  # noqa: F401
from fk import block, gpu, paths, preflight
from fk.verify import Verification
from sandbox import SWITCH, Sandbox


def quiet(*a):
    pass


class FakeMode(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()

    def tearDown(self):
        self.sb.close()

    def verify(self, effect=0.5, rounds=2, **fake):
        v = Verification(self.sb.card_path, mode="fake", ledger_path=self.sb.ledger_path, rounds=rounds, pause_s=0,
                         log=quiet, fake={"effect_pct": effect, **fake}, model_path=self.sb.model)
        return v.run()

    def test_confirmed_row_has_everything(self):
        self.sb.make_card()
        r = self.verify(0.5)
        self.assertEqual(r["verdict"], "CONFIRMED")
        self.assertTrue(r["written"])
        self.assertEqual(self.sb.ledger.verify(), [])
        row = self.sb.ledger.rows()[-1]
        for k in ("commits", "builds", "env", "model", "card", "driver", "samples", "aa", "abba_order", "median",
                  "ci95", "verdict", "evidence", "harness_sha256", "sealed_sha256", "claim_sha256", "logs"):
            self.assertIn(k, row, k)
        self.assertEqual(len(row["samples"]), 8)
        self.assertEqual(row["abba_order"][:4], [[1, 0, "A"], [1, 1, "B"], [1, 2, "B"], [1, 3, "A"]])
        self.assertTrue(all(len(s) == 64 for s in row["builds"]["cand"]["sha256"].values()))
        self.assertGreater(len(row["evidence"]), 10)
        self.assertEqual(row["env"]["B"], {SWITCH: "1"})

    def test_null_refuted_regression(self):
        self.sb.make_card(kill={"effect_pct_below": -5.0})
        self.assertEqual(self.verify(0.0)["verdict"], "NULL")
        self.sb.make_card(kill={"effect_pct_below": 0.1})
        self.assertEqual(self.verify(0.0)["verdict"], "REFUTED")
        self.assertEqual(self.verify(-1.0)["verdict"], "REGRESSION")

    def test_aa_failure_invalid(self):
        self.sb.make_card()
        r = self.verify(0.5, aa_drift_pct=1.0)
        self.assertEqual(r["verdict"], "INVALID")
        self.assertTrue(any("A/A" in x for x in r["reasons"]))

    def test_outlier_run_invalid(self):
        self.sb.make_card()
        r = self.verify(0.5, outlier=["A", 1])
        self.assertEqual(r["verdict"], "INVALID")
        self.assertTrue(any("R21" in x for x in r["reasons"]))

    def test_bit_md5_mismatch_invalid_before_g4(self):
        self.sb.make_card()
        r = self.verify(0.5, md5_diff=True)
        self.assertEqual(r["verdict"], "INVALID")
        self.assertTrue(any("R01" in x for x in r["reasons"]))
        self.assertNotIn("G4", r["gates"])

    def test_neartie_class(self):
        self.sb.make_card(correctness_class="NEAR-TIE")
        r = self.verify(0.5, md5_diff=True)
        self.assertIn("neartie", r["gates"]["G2"])
        self.assertEqual(r["verdict"], "NEEDS-HUMAN")  # confirmed speed, numerics changed: human approves (G7)
        self.assertEqual(r["stat_verdict"], "CONFIRMED")

    def test_unregistered_not_written(self):
        self.sb.make_card(register=False)
        r = self.verify(0.5)
        self.assertFalse(r["written"])
        self.assertTrue(any("not registered" in x for x in r["reasons"]))

    def test_card_changed_after_registration(self):
        c = self.sb.make_card()
        c["expected"]["effect_pct"] = 2.0
        self.sb.card_path.write_text(json.dumps(c))
        self.assertFalse(self.verify(0.5)["written"])

    def test_build_sha_mismatch(self):
        self.sb.make_card()
        (self.sb.cand_build / "lib" / "libggml-hip.so.0.26.0").write_bytes(b"\x7fELF other " + SWITCH.encode())
        r = self.verify(0.5)
        self.assertEqual(r["verdict"], "INVALID")
        self.assertTrue(any("R34" in x for x in r["reasons"]))

    def test_harness_change_refused(self):
        self.sb.make_card()
        with mock.patch("fk.hashing.hash_harness", return_value={"fk/verify.py": "0" * 64}):
            r = self.verify(0.5)
        self.assertEqual(r["verdict"], "INVALID")
        self.assertTrue(r["refused"])
        self.assertNotIn("G4", r["gates"])

    def test_bench_metric(self):
        self.sb.make_card(metric="pp_tps", attacked={"kernels": [], "share_ms": None})
        r = self.verify(1.0)
        self.assertEqual(r["verdict"], "CONFIRMED")
        self.assertEqual(r["metric"], "pp_tps")


class DenyList(unittest.TestCase):
    def test_diff_touching_harness_refused_without_gpu(self):
        sb = Sandbox(extra_files={"tools/llama-bench/llama-bench.cpp": "// faster numbers\n"})
        try:
            sb.make_card(touched_paths=["ggml/src/ggml-cuda/foo.cu", "tools/llama-bench/llama-bench.cpp"])
            v = Verification(sb.card_path, mode="fake", ledger_path=sb.ledger_path, pause_s=0, log=quiet,
                             model_path=sb.model)
            r = v.run()
            self.assertEqual(r["verdict"], "INVALID")
            self.assertTrue(r["refused"])
            self.assertTrue(any("R23" in x and "llama-bench" in x for x in r["reasons"]))
            self.assertEqual(v.runner.n, 0)  # not a single GPU block
        finally:
            sb.close()


class DryRun(unittest.TestCase):
    def test_prints_gpu_commands_runs_nothing(self):
        sb = Sandbox()
        try:
            sb.make_card(ops=["MUL_MAT"])
            before = sb.ledger_path.read_text()
            out = io.StringIO()
            never = mock.Mock(side_effect=AssertionError("executed"))
            with mock.patch.object(gpu, "subprocess", SimpleNamespace(run=never)), \
                    mock.patch("fk.block.main", side_effect=AssertionError("executed")), redirect_stdout(out):
                r = Verification(sb.card_path, mode="dry", ledger_path=sb.ledger_path, rounds=2, model_path=sb.model,
                                 log=print).run()
            text = out.getvalue()
            self.assertIsNone(r["verdict"])
            self.assertEqual(sb.ledger_path.read_text(), before)
            self.assertFalse(paths.RUNS.exists())
            self.assertIn("flock /tmp/gpu.lock flock /tmp/quiet.lock timeout 290", text)
            self.assertIn("pgrep -f 'llama-server.*--port 8080' && exit 3", text)
            self.assertIn("test-backend-ops test -o MUL_MAT", text)
            self.assertIn("sleep 45", text)
            kinds = [p["kind"] for p in r["plan"]]
            self.assertEqual(kinds, ["ops", "greedy", "greedy", "probe", "probe"] + ["serve"] * 8)
        finally:
            sb.close()


IDLE = {"user_server": False, "llama_servers": [], "kfd_procs": [], "power_control": "on", "vram_used": 1 << 20,
        "gtt_used": 1 << 20, "temp_c": {"junction": 45.0}, "loadavg": [0.2, 0.2, 0.2], "nproc": 16,
        "cpu_quota": None, "port_free": True}


def in_process_blocks(argv, *a, **k):
    """Stands in for `flock ... timeout ... factory.py _block SPEC` (and the pgrep check) without locks or GPU."""
    if argv[0] == "pgrep":
        return subprocess.CompletedProcess(argv, 1)
    assert argv[-2] == "_block", argv
    return subprocess.CompletedProcess(argv, block.main(argv[-1]))


class RealPath(unittest.TestCase):
    """mode=real with CPU stand-ins: specs on disk, block.main, measure.serve_run over HTTP, fusion/greedy.sh."""

    @unittest.skipUnless(all(os.path.exists(p) for p in ("/usr/bin/curl", "/usr/bin/jq")), "needs curl and jq")
    def test_real_mode_end_to_end(self):
        sb = Sandbox()
        try:
            sb.make_card()
            port = 18497
            with mock.patch.object(paths, "GPU_WRAP", []), \
                    mock.patch.object(gpu, "subprocess", SimpleNamespace(run=in_process_blocks)), \
                    mock.patch("fk.preflight.snapshot", return_value=dict(IDLE, port=port)), \
                    mock.patch("fk.preflight._pgrep", return_value=[]), \
                    mock.patch.dict(os.environ, {"FAKE_EFFECT": "0.8"}):
                v = Verification(sb.card_path, mode="real", ledger_path=sb.ledger_path, rounds=2, port=port,
                                 pause_s=0, log=quiet, model_path=sb.model)
                r = v.run()
            self.assertEqual(r["verdict"], "CONFIRMED", r["reasons"])
            self.assertAlmostEqual(r["median"], 0.8, delta=0.05)
            g2 = r["gates"]["G2"]
            self.assertTrue(g2["identical"])
            self.assertEqual(set(g2["md5"]["base"]), {"plain", "mtp"})
            self.assertEqual(r["gates"]["G3"]["hits"], {"on": True, "off": False})
            s = r["samples"][0]
            self.assertEqual(s["build_info"], "b8000-fake")
            self.assertEqual(s["request"], {"tokens": 400, "temps": [1.0], "seeds": [1, 2], "cache_prompt": False})
            self.assertEqual(len(s["n_tokens"]), 16)
            self.assertEqual(len({x["pid"] for x in r["samples"]}), 8)  # a fresh process per run
            self.assertEqual(sb.ledger.verify(), [])
        finally:
            sb.close()


if __name__ == "__main__":
    unittest.main()
