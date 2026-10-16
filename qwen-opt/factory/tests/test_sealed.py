import shutil
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from fk import sealed


class Sealed(unittest.TestCase):
    def test_seal_and_coverage(self):
        self.assertEqual(sealed.check_seal(), sealed.SEALED_SHA256)
        e = sealed.load_sealed()
        s = sealed.summary(e)
        self.assertGreaterEqual(s["n"], 10)
        self.assertEqual(set(s["class"]), {"new-writing", "copy-edit"})
        self.assertEqual(set(s["lang"]), {"pl", "en"})
        self.assertIn("agent-edit", s["domain"])

    def test_tamper_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "prompts.jsonl"
            shutil.copy(sealed.SEALED_FILE, p)
            with open(p, "a") as f:
                f.write("{}\n")
            with self.assertRaises(sealed.SealError):
                sealed.load_sealed(p)

    def test_disjoint_from_public_and_greedy(self):
        pub = sealed.load_public()
        self.assertEqual(len(pub), 6)
        grams = sealed.sealed_ngrams(sealed.load_sealed(), 6)
        pub_grams = set().union(*(sealed.ngrams(p["messages"][0]["content"], 6) for p in pub))
        self.assertEqual(grams & pub_grams, set())
        ids = {e["id"] for e in sealed.load_sealed()}
        self.assertFalse(ids & {p["id"] for p in pub})


if __name__ == "__main__":
    unittest.main()
