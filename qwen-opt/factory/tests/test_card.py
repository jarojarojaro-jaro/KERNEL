import unittest

import _path  # noqa: F401
from fk import card
from sandbox import Sandbox


class CardTest(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_template_is_incomplete(self):
        probs = card.validate(card.template("2026-10-17-x", "a", "now"))
        self.assertTrue(any("hypothesis" in p for p in probs))
        self.assertTrue(any("effect_pct" in p for p in probs))

    def test_filled_card_valid(self):
        self.assertEqual(card.validate(self.sb.make_card(register=False)), [])

    def test_bad_fields(self):
        c = self.sb.make_card(register=False, metric="kernel_us", correctness_class="BIT",
                              probe={"kind": "md5"}, prompt_set={"id": "spec6", "sealed_sha256": "x"})
        probs = " | ".join(card.validate(c))
        for needle in ("not an end-to-end metric", "probe md5 cannot", "prompt_set.id", "sealed_sha256"):
            self.assertIn(needle, probs)

    def test_ms_metric_needs_amdahl_share(self):
        c = self.sb.make_card(register=False, attacked={"kernels": [], "share_ms": None})
        self.assertTrue(any("share_ms" in p for p in card.validate(c)))

    def test_sha_changes_with_content(self):
        c = self.sb.make_card(register=False)
        s = card.card_sha(c)
        c["expected"]["effect_pct"] = 5.0
        self.assertNotEqual(s, card.card_sha(c))


if __name__ == "__main__":
    unittest.main()
