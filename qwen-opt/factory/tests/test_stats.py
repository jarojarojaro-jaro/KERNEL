import math
import unittest

import _path  # noqa: F401
from fk import stats


class Stats(unittest.TestCase):
    def test_abba(self):
        s = stats.abba_schedule(2)
        self.assertEqual([a for _, _, a in s], list("ABBABAAB"))
        self.assertEqual(len({(r, p) for r, p, _ in s}), 8)

    def test_effect_sign(self):
        self.assertAlmostEqual(stats.effect_pct(100.0, 99.0, "ms_step"), 1.0)
        self.assertAlmostEqual(stats.effect_pct(100.0, 101.0, "tps"), 1.0)

    def test_paired_and_aa(self):
        vals = {(1, 0): ("A", 100.0), (1, 1): ("B", 99.0), (1, 2): ("B", 99.1), (1, 3): ("A", 100.1),
                (2, 0): ("B", 99.0), (2, 1): ("A", 100.0), (2, 2): ("A", 100.0), (2, 3): ("B", 98.9)}
        eff, aa, bb = stats.paired_effects(vals, "ms_step")
        self.assertEqual(len(eff), 4)
        self.assertTrue(all(0.8 < e < 1.2 for e in eff))
        self.assertAlmostEqual(aa[0], -0.1, places=6)
        self.assertEqual(len(bb), 2)

    def test_t_ci_known(self):
        m, lo, hi = stats.t_ci([1.0, 2.0, 3.0])  # sd 1, t(2) 4.303
        self.assertAlmostEqual(m, 2.0)
        self.assertAlmostEqual(hi - m, 4.303 / math.sqrt(3), places=6)
        self.assertTrue(math.isnan(stats.t_ci([1.0])[1]))

    def test_bootstrap_deterministic(self):
        xs = [0.3, 0.5, 0.4, 0.6, 0.45, 0.55, 0.5, 0.42]
        self.assertEqual(stats.bootstrap_ci(xs), stats.bootstrap_ci(xs))
        est, lo, hi = stats.bootstrap_ci(xs)
        self.assertTrue(lo <= est <= hi)

    def test_verdicts(self):
        def v(lo, hi, med, kill=None, mde=0.2):
            return stats.verdict({"ci95": [lo, hi], "median": med}, mde, kill)[0]
        self.assertEqual(v(0.3, 0.7, 0.5), "CONFIRMED")
        self.assertEqual(v(0.05, 0.3, 0.15), "NULL")          # below MDE
        self.assertEqual(v(-0.2, 0.4, 0.1), "NULL")
        self.assertEqual(v(-0.7, -0.3, -0.5), "REGRESSION")
        self.assertEqual(v(-0.1, 0.05, 0.0, kill=0.1), "REFUTED")
        self.assertEqual(v(0.02, 0.08, 0.05, kill=0.1), "REFUTED")  # real but smaller than pre-registered
        self.assertEqual(v(math.nan, math.nan, 0.5), "NULL")

    def test_mde(self):
        self.assertEqual(stats.mde("ms_step", [0.01, -0.02]), 0.2)
        self.assertAlmostEqual(stats.mde("ms_step", [0.3, -0.3]), 0.6)
        self.assertEqual(stats.mde("ms_step", [], card_mde=0.5), 0.5)


if __name__ == "__main__":
    unittest.main()
