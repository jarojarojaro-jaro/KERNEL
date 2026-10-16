import unittest

import _path  # noqa: F401
from fk import report
from fk.verify import Verification
from sandbox import Sandbox


class Report(unittest.TestCase):
    def test_render_from_fake_ledger(self):
        sb = Sandbox()
        try:
            sb.make_card()
            Verification(sb.card_path, mode="fake", ledger_path=sb.ledger_path, pause_s=0, log=lambda *a: None,
                         fake={"effect_pct": 0.0}, model_path=sb.model).run()
            md = report.render(sb.ledger.rows(), sb.ledger.verify())
            self.assertIn("nienaruszony", md)
            self.assertIn("2026-10-17-test-claim", md)
            self.assertIn("Wyniki negatywne", md)
            self.assertIn("ledger:", md)
            row = [r for r in sb.ledger.rows() if r["kind"] == "verdict"][0]
            name, note = report.wiki_draft(row)
            self.assertTrue(name.startswith("2026-10-17-"))
            self.assertIn("typ: eksperyment", note)
            self.assertIn("## Powiązane", note)
        finally:
            sb.close()


if __name__ == "__main__":
    unittest.main()
