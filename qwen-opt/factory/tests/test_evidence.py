import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from fk import evidence
from fk.hashing import canonical, sha256_bytes

CODECS = ["xz"] + (["zstd"] if shutil.which("zstd") else [])


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.run = t / "run"
        self.store = t / "store"
        (self.run / "sub").mkdir(parents=True)
        self.orig = {
            "a.log": b"hello evidence\n" * 1000,
            "sub/b.log": b"hello evidence\n" * 1000,  # duplicate content of a.log
            "sub/c.json": json.dumps({"t_s": [1.5, 2.5]}).encode(),
        }
        for rel, data in self.orig.items():
            (self.run / rel).write_bytes(data)

    def tearDown(self):
        self.tmp.cleanup()

    def payloads(self):
        return sorted(p for p in (self.store / "sha256").rglob("payload.*"))

    def overwrite(self, p: Path, data: bytes):
        os.chmod(p, 0o644)
        p.write_bytes(data)

    def test_default_codec(self):
        self.assertEqual(evidence.default_codec(), "zstd" if shutil.which("zstd") else "xz")

    def test_preserve_dedup_and_id_stability(self):
        for codec in CODECS:
            with self.subTest(codec=codec):
                store = self.store / codec
                r1 = evidence.preserve(self.run, store, codec=codec)
                self.assertEqual(r1["files"], 3)
                self.assertEqual(r1["new_payloads"], 2)  # a.log and sub/b.log share one payload
                self.assertEqual(r1["bytes_in"], sum(len(v) for v in self.orig.values()))
                payloads = sorted(store.rglob("payload.*"))
                self.assertEqual(len(payloads), 2)
                self.assertTrue(all(p.name == f"payload.{evidence.SUFFIX[codec]}" for p in payloads))
                self.assertEqual(r1["bytes_out"], sum(p.stat().st_size for p in payloads))
                self.assertLess(r1["bytes_out"], r1["bytes_in"])
                files = r1["manifest"]["files"]
                self.assertEqual(sorted(files), sorted(self.orig))
                for rel, data in self.orig.items():
                    sha = sha256_bytes(data)
                    self.assertEqual(files[rel]["sha256"], sha)
                    self.assertEqual(files[rel]["bytes"], len(data))
                    self.assertEqual(files[rel]["codec"], codec)
                    p = evidence.payload_path(store, sha, codec)
                    self.assertEqual(p.parent.parent.name, sha[:2])
                    self.assertEqual(files[rel]["stored_bytes"], p.stat().st_size)
                    self.assertFalse(p.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
                mtimes = [p.stat().st_mtime_ns for p in payloads]

                r2 = evidence.preserve(self.run, store, codec=codec)
                self.assertEqual(r2["evidence_id"], r1["evidence_id"])
                self.assertEqual(r2["new_payloads"], 0)
                self.assertEqual([p.stat().st_mtime_ns for p in payloads], mtimes)  # not rewritten

                mpath = evidence.manifest_path(store, r1["evidence_id"])
                raw = mpath.read_bytes()
                m = json.loads(raw)
                self.assertEqual(raw, canonical(m))
                self.assertIn("created", m)
                self.assertEqual(m["root"], str(self.run))
                no_created = {k: v for k, v in m.items() if k != "created"}
                self.assertEqual(sha256_bytes(canonical(no_created)), r1["evidence_id"])
                self.assertFalse(mpath.stat().st_mode & stat.S_IWUSR)
                self.assertEqual(list(mpath.parent.glob(".*.tmp")), [])

    def test_changed_run_new_id(self):
        r1 = evidence.preserve(self.run, self.store)
        (self.run / "sub" / "c.json").write_bytes(b"{}")
        r2 = evidence.preserve(self.run, self.store)
        self.assertNotEqual(r1["evidence_id"], r2["evidence_id"])
        self.assertEqual(r2["new_payloads"], 1)
        self.assertEqual(evidence.verify_evidence(r1["evidence_id"], self.store), [])  # no GC

    def test_verify_ok_and_tamper(self):
        for codec in CODECS:
            with self.subTest(codec=codec):
                store = self.store / codec
                eid = evidence.preserve(self.run, store, codec=codec)["evidence_id"]
                self.assertEqual(evidence.verify_evidence(eid, store), [])
                p = evidence.payload_path(store, sha256_bytes(self.orig["sub/c.json"]), codec)
                good = p.read_bytes()

                # valid stream of different content -> sha mismatch
                other = self.run.parent / f"other-{codec}"
                other.write_bytes(b"tampered")
                tmp = self.run.parent / f"other-{codec}.cmp"
                evidence._compress(other, tmp, codec)
                self.overwrite(p, tmp.read_bytes())
                probs = evidence.verify_evidence(eid, store)
                self.assertEqual(len(probs), 1)
                self.assertIn("sub/c.json", probs[0])
                self.assertIn("sha256 mismatch", probs[0])

                # corrupt bytes -> decompress failure reported
                self.overwrite(p, b"garbage")
                probs = evidence.verify_evidence(eid, store)
                self.assertEqual(len(probs), 1)
                self.assertIn("sub/c.json", probs[0])

                # missing payload
                p.unlink()
                probs = evidence.verify_evidence(eid, store)
                self.assertEqual(len(probs), 1)
                self.assertIn("payload missing", probs[0])
                with self.assertRaises(evidence.EvidenceError):
                    evidence.restore(eid, self.run.parent / f"dest-{codec}", store)
                p.write_bytes(good)
                self.assertEqual(evidence.verify_evidence(eid, store), [])

    def test_manifest_id_mismatch(self):
        eid = evidence.preserve(self.run, self.store)["evidence_id"]
        mpath = evidence.manifest_path(self.store, eid)
        m = json.loads(mpath.read_bytes())
        m["root"] = "/elsewhere"
        self.overwrite(mpath, canonical(m))
        probs = evidence.verify_evidence(eid, self.store)
        self.assertTrue(any("manifest id mismatch" in s for s in probs))
        self.assertEqual(evidence.verify_evidence("0" * 64, self.store)[0][:16], "manifest missing")
        self.assertIn("bad evidence_id", evidence.verify_evidence("../x", self.store)[0])

    def test_restore_round_trip(self):
        for codec in CODECS:
            with self.subTest(codec=codec):
                store = self.store / codec
                eid = evidence.preserve(self.run, store, codec=codec)["evidence_id"]
                dest = self.run.parent / f"restored-{codec}"
                written = evidence.restore(eid, dest, store)
                self.assertEqual(len(written), 3)
                got = {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                self.assertEqual(got, self.orig)


if __name__ == "__main__":
    unittest.main()
