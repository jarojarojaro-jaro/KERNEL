import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from fk.ledger import GENESIS, Ledger, LedgerError


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / "ledger.jsonl"
        self.led = Ledger(self.p)
        for i in range(3):
            self.led.append({"kind": "note", "i": i})

    def tearDown(self):
        self.tmp.cleanup()

    def lines(self):
        return self.p.read_text().splitlines()

    def write(self, lines):
        os.chmod(self.p, 0o644)
        self.p.write_text("\n".join(lines) + "\n")

    def test_chain(self):
        rows = self.led.rows()
        self.assertEqual(rows[0]["prev_sha256"], GENESIS)
        self.assertEqual(rows[2]["prev_sha256"], rows[1]["sha256"])
        self.assertEqual(self.led.verify(), [])
        self.assertFalse(os.stat(self.p).st_mode & stat.S_IWUSR)  # read-only between appends

    def test_edit_detected(self):
        ls = self.lines()
        r = json.loads(ls[1])
        r["i"] = 99
        ls[1] = json.dumps(r)
        self.write(ls)
        self.assertTrue(any("content changed" in x for x in self.led.verify()))
        with self.assertRaises(LedgerError):
            self.led.append({"kind": "note"})

    def test_delete_and_truncate_detected(self):
        ls = self.lines()
        self.write([ls[0], ls[2]])
        self.assertTrue(self.led.verify())
        self.write(ls[:2])  # tail cut: only the head file shows it
        self.assertTrue(any("head" in x for x in self.led.verify()))

    def test_unknown_kind(self):
        with self.assertRaises(LedgerError):
            self.led.append({"kind": "whatever"})


if __name__ == "__main__":
    unittest.main()
