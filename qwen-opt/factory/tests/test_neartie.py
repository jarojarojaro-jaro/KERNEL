import unittest

import _path  # noqa: F401
from fk import neartie


def tok(i, top):
    return {"id": i, "token": str(i), "logprob": top[0][1], "top_logprobs": [{"id": a, "logprob": b} for a, b in top]}


class NearTie(unittest.TestCase):
    def ref(self, margin):
        return [tok(1, [(1, -0.1), (9, -0.2)]), tok(2, [(2, -0.5), (7, -0.5 - margin)]), tok(3, [(3, -0.1), (8, -3)])]

    def test_identical(self):
        self.assertEqual(neartie.compare(self.ref(0.05), self.ref(0.05))["status"], "IDENTICAL")

    def test_tie_accepted(self):
        cand = [tok(1, [(1, -0.1)]), tok(7, [(7, -0.5)]), tok(4, [(4, -0.1)])]  # later tokens may differ
        r = neartie.compare(self.ref(0.05), cand)
        self.assertEqual((r["status"], r["pos"]), ("NEAR-TIE", 1))
        self.assertAlmostEqual(r["margin"], 0.05)

    def test_margin_too_large(self):
        cand = [tok(1, [(1, -0.1)]), tok(7, [(7, -0.5)])]
        r = neartie.compare(self.ref(0.3), cand)
        self.assertEqual(r["status"], "DIVERGE")
        self.assertIn("margin", r["reason"])

    def test_not_runner_up(self):
        cand = [tok(1, [(1, -0.1)]), tok(5, [(5, -0.5)])]
        self.assertIn("not the runner-up", neartie.compare(self.ref(0.01), cand)["reason"])

    def test_early_end(self):
        self.assertEqual(neartie.compare(self.ref(0.01), self.ref(0.01)[:2])["status"], "DIVERGE")

    def test_gate_and_response_parsing(self):
        resp = {"choices": [{"logprobs": {"content": [
            {"id": 5, "token": "a", "logprob": -0.01, "bytes": [97],
             "top_logprobs": [{"id": 5, "token": "a", "logprob": -0.01}, {"id": 6, "token": "b", "logprob": -4.6}]}]}}]}
        t = neartie.tokens_from_response(resp)
        self.assertEqual(t[0]["top_logprobs"][1]["id"], 6)
        self.assertEqual(neartie.gate({"p0": (t, t)})["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
