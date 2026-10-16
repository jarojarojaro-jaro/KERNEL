"""fk.measure against the CPU stand-in server: request loop, client-ui variant, near-tie tokens, probe, shutdown."""
import os
import sys
import time
import unittest

import _path  # noqa: F401
from fk import measure, profiles, sealed
from sandbox import FAKE_SERVER, SWITCH


def spec(port, tmp, **kw):
    s = {"argv": [sys.executable, str(FAKE_SERVER), "--port", str(port)], "env": {SWITCH: "1"}, "lib_dir": "/x",
         "port": port, "log": os.path.join(tmp, f"srv{port}.log"), "deadline": time.time() + 60}
    s.update(kw)
    return s


class Measure(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_serve_run_with_client_ui(self):
        se, pub = sealed.load_sealed()[:2], sealed.load_public()[:1]
        prompts = [{"set": "sealed", "entry": e} for e in se] + [{"set": "public", "entry": e} for e in pub]
        rec = measure.serve_run(spec(18495, self.tmp.name, protocol=profiles.PROTOCOL, prompts=prompts,
                                     variants=["plain", "client-ui"]))
        keys = set(rec["prompts"])
        self.assertIn(f"sealed/{se[0]['id']}", keys)
        self.assertIn(f"sealed/{se[0]['id']}@client-ui", keys)
        self.assertNotIn(f"public/{pub[0]['id']}@client-ui", keys)
        p = rec["prompts"][f"sealed/{se[0]['id']}"]
        self.assertEqual(p["n"], 800)
        self.assertAlmostEqual(p["ms_step"], 27.74 * 0.995, places=3)
        self.assertGreater(p["tok_step"], 1.0)
        self.assertEqual(rec["n_tokens"][se[0]["id"]], 800)
        self.assertEqual(rec["build_info"], "b8000-fake")
        self.assertEqual(len(rec["text_sha256"]), 3 * 2 + 2)
        self.assertIn("max_junction_c", rec["telemetry"])

    def test_neartie_and_probe(self):
        out = measure.neartie_run(spec(18494, self.tmp.name, prompts=["a", "b"], tokens=16))
        self.assertEqual(len(out["tokens"]["p0"]), 16)
        self.assertEqual(out["tokens"]["p0"][0]["top_logprobs"][1]["logprob"], -2.0)
        hit = measure.probe_run(spec(18493, self.tmp.name, env={SWITCH: "1", "GGML_HIP_PM4_DEBUG": "1"},
                                     regex="foo_on"))
        self.assertTrue(hit["hit"])
        miss = measure.probe_run(spec(18492, self.tmp.name, env={SWITCH: "0", "GGML_HIP_PM4_DEBUG": "1"},
                                      regex="foo_on"))
        self.assertFalse(miss["hit"])

    def test_env_is_scrubbed(self):
        os.environ["GGML_HIP_SNEAKY"] = "1"
        try:
            env = measure.block_env({"env": {"A": "b"}, "lib_dir": "/l"})
        finally:
            del os.environ["GGML_HIP_SNEAKY"]
        self.assertNotIn("GGML_HIP_SNEAKY", env)
        self.assertEqual(env["A"], "b")
        self.assertTrue(env["LD_LIBRARY_PATH"].startswith("/l:"))


if __name__ == "__main__":
    unittest.main()
