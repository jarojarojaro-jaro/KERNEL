import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from fk import paths, sealed


class Sealed(unittest.TestCase):
    def test_seal_and_coverage(self):
        self.assertEqual(sealed.check_seal(), sealed.active()["sha256"])
        e = sealed.load_sealed()
        s = sealed.summary(e)
        self.assertGreaterEqual(s["n"], 10)
        self.assertEqual(set(s["class"]), {"new-writing", "copy-edit"})
        self.assertEqual(set(s["lang"]), {"pl", "en"})
        self.assertIn("agent-edit", s["domain"])
        self.assertEqual(sealed.composition_problems(e), [])

    def test_tamper_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "prompts.jsonl"
            shutil.copyfile(sealed.active()["path"], p)
            with open(p, "a") as f:
                f.write("{}\n")
            with self.assertRaises(sealed.SealError):
                sealed.load_sealed(p, sealed.active()["sha256"])

    def test_disjoint_from_public_and_greedy(self):
        pub = sealed.load_public()
        self.assertEqual(len(pub), 6)
        allp = sealed.load_all()
        grams = sealed.sealed_ngrams(allp, 6)
        pub_grams = set().union(*(sealed.ngrams(p["messages"][0]["content"], 6) for p in pub))
        self.assertEqual(grams & pub_grams, set())
        ids = [e["id"] for e in allp]
        self.assertEqual(len(ids), len(set(ids)))  # no prompt is in two sets
        self.assertFalse(set(ids) & {p["id"] for p in pub})


class Rotation(unittest.TestCase):
    """Each RSI cycle activates the next never-used pool set; the old set is never reused."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = paths.SEALED_DIR
        d = Path(self.tmp.name)
        for f in ("registry.json", "prompts.jsonl", "pool.jsonl"):
            shutil.copyfile(self.saved / f, d / f)
        paths.SEALED_DIR = d

    def tearDown(self):
        paths.SEALED_DIR = self.saved
        for f in Path(self.tmp.name).iterdir():
            os.chmod(f, 0o644)
        self.tmp.cleanup()

    def test_rotate_through_pool(self):
        pool_sets = sorted({e["set"] for e in sealed.load_pool()})
        self.assertGreaterEqual(len(pool_sets), 1)
        v1 = sealed.active()
        plan = sealed.rotate(1, dry_run=True)
        self.assertEqual(sealed.active()["id"], v1["id"])  # dry run changes nothing
        r = sealed.rotate(1)
        self.assertEqual(r["to"], plan["to"])
        a = sealed.active()
        self.assertEqual(a["id"], plan["to"])
        self.assertNotEqual(a["sha256"], v1["sha256"])
        e = sealed.load_sealed()
        self.assertEqual(sealed.composition_problems(e), [])
        self.assertFalse({x["id"] for x in e} & {x["id"] for x in sealed.load_sealed(v1["path"], v1["sha256"])})
        self.assertNotIn(a["id"], {x["set"] for x in sealed.load_pool()})  # burned: gone from the pool
        self.assertEqual(sealed.prompt_set_id(), f"{a['id']}+spec6")
        for _ in pool_sets[1:]:
            sealed.rotate(2)
        with self.assertRaises(sealed.SealError):
            sealed.rotate(9)  # pool exhausted
        reg = json.loads((paths.SEALED_DIR / "registry.json").read_text())
        self.assertEqual(len(reg["sets"]), 1 + len(pool_sets))


if __name__ == "__main__":
    unittest.main()
