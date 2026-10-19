"""RSI-F on CPU: playbook library and its evidence rules, the no-diff review, transfer briefs and scoring (k1-k3),
calibration (Brier), sealed draw, workspace snapshot, cycle dry-run and the 21i/21j verifier additions."""
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import _path  # noqa: F401
from fk import calib, cycle, hwgates, paths, sealed, stats, transfer
from fk import playbook as pbm
from fk.verify import Verification
from sandbox import Sandbox, git

DIFF = """diff --git a/ggml/src/ggml-cuda/mmq.cuh b/ggml/src/ggml-cuda/mmq.cuh
--- a/ggml/src/ggml-cuda/mmq.cuh
+++ b/ggml/src/ggml-cuda/mmq.cuh
@@ -1,3 +1,4 @@
-    sum[l] += dmA[i].x * dsB[j].x * (float) C.x[l];
+    const float2_pinned scale_pair = widen_scales_vopd(dmA[i], dsB[j]);
+    sum[l] = __builtin_fmaf(scale_pair.x, bias_trick_accumulator(C.x[l]), sum[l]);
"""


def verdict_row(led, claim, verdict="CONFIRMED", stat=None, median=1.5, rsi=None, author="agent:Impl-0", p=None,
                expected=1.0, mode="real", refused=False):
    card = {"id": claim, "author": author, "expected": {"effect_pct": expected, **({"p_confirmed": p} if p is not None
                                                                                   else {})},
            "commits": {"base": "f4f0deae5aaaa", "cand": "f61994f58bbbb"}, "switch": {"name": "GGML_HIP_MMQ_EPI"}}
    if rsi:
        card["rsi"] = rsi
    return led.append({"kind": "verdict", "mode": mode, "claim_id": claim, "card": card, "verdict": verdict,
                       "stat_verdict": stat or verdict, "median": median, "ci95": [0.5, 2.5], "refused": refused,
                       "reasons": [], "commits": card["commits"]})


def playbook_json(src, pid="pb-vopd-epilogue", author="agent:Rewriter"):
    return {"id": pid, "title": "Pair the f32 epilogue of an int8 WMMA tile into dual-issue instructions",
            "technique": "Widen the per-step scales to f32 once, keep them opaque to the compiler, and turn the "
                         "int-to-float conversion into a single add so every epilogue op can dual-issue.",
            "applies_when": ["the inner loop of a matrix kernel is VALU-bound next to WMMA"],
            "not_when": ["small tiles where the extra conversions cost more than the pairing saves"],
            "steps": ["profile the kernel share of prefill", "dump the ISA of the inner loop with the build flags",
                      "count unpaired VALU ops", "rewrite behind an env switch", "prove bitwise equality"],
            "profiling": ["rocprofv3 --kernel-trace on llama-bench pp4096 (planner only)"],
            "pitfalls": ["a full unroll spilled registers"], "correctness": "exact f16 products in f32; same order",
            "rules_fired": ["R29"], "source": {"ledger_seq": src["seq"], "ledger_sha256": src["sha256"],
                                               "claim_id": src["claim_id"], "target": "mmq-epi-q4k-q5k"},
            "author": author, "created": "2026-10-19", "expires": "2026-12-31"}


class Playbooks(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()
        self.led = self.sb.ledger

    def tearDown(self):
        self.sb.close()

    def test_only_confirmed_becomes_a_draft(self):
        nul = verdict_row(self.led, "2026-10-17-x", "NULL")
        with self.assertRaises(pbm.PlaybookError):
            pbm.create(playbook_json(nul), self.led, "planner")
        fake = verdict_row(self.led, "2026-10-17-y", "CONFIRMED", mode="fake")
        with self.assertRaises(pbm.PlaybookError):
            pbm.create(playbook_json(fake), self.led, "planner")
        nh = verdict_row(self.led, "2026-10-17-z", "NEEDS-HUMAN", stat="CONFIRMED")
        with self.assertRaises(pbm.PlaybookError):
            pbm.create(playbook_json(nh), self.led, "planner")
        self.led.append({"kind": "note", "note": "human-approval", "verdict_seq": nh["seq"], "by": "human"})
        pb = pbm.create(playbook_json(nh), self.led, "planner")
        self.assertEqual(pb["status"], "draft")
        bad = dict(playbook_json(nh, "pb-bad"), source={**playbook_json(nh)["source"], "ledger_sha256": "0" * 64})
        with self.assertRaises(pbm.PlaybookError):
            pbm.create(bad, self.led, "planner")

    def test_review_finds_every_leak_class_and_passes_clean_text(self):
        src = verdict_row(self.led, "2026-10-17-mmq", median=2.2)
        clean = pbm.review(pbm.text_of(playbook_json(src)), DIFF, src)
        self.assertTrue(clean["pass"], clean)
        leaks = {
            "diff_lines": "copy this: sum[l] += dmA[i].x * dsB[j].x * (float) C.x[l];",
            "new_identifiers": "call widen_scales_vopd before the loop",
            "forbidden_tokens": "see commit f61994f and GGML_HIP_MMQ_EPI",
            "measured_numbers": "expect about +2.2% on pp4096",
        }
        for k, t in leaks.items():
            r = pbm.review(t, DIFF, src)
            self.assertFalse(r["pass"], k)
            self.assertIn(k, r["hits"], (k, r))
        g = pbm.review("const float2_pinned scale_pair widen_scales_vopd dmA i dsB j and more", DIFF, src)
        self.assertIn("diff_8grams", g["hits"])
        s = sealed.load_sealed()[0]["messages"][-1]["content"]
        self.assertIn("sealed_8grams", pbm.review(s, DIFF, src)["hits"])

    def test_lifecycle_to_accepted_needs_a_fresh_transfer(self):
        src = verdict_row(self.led, "2026-10-17-mmq", median=2.2)
        pb = pbm.create(playbook_json(src), self.led, "planner")
        with self.assertRaises(pbm.PlaybookError):
            pbm.do_review(pb["id"], self.led, DIFF, "agent:Rewriter", "pass")  # the author cannot review itself
        pb = pbm.do_review(pb["id"], self.led, DIFF, "agent:Reviewer", "pass")
        self.assertEqual(pb["status"], "candidate")
        self.assertEqual(pbm.ledger_status(self.led.rows(), pb), "candidate")
        with self.assertRaises(pbm.PlaybookError):
            pbm.accept(pb["id"], self.led, "planner")  # no transfer yet
        # a brief note for arm A on another target, then a success of a fresh agent with that brief
        sha = "a" * 64
        self.led.append({"kind": "note", "note": "rsi-brief", "target": "t-q6k", "arm": "A", "playbook": pb["id"],
                         "content_sha256": pbm.content_sha(pb), "brief_sha256": sha})
        rsi = {"playbook": pb["id"], "arm": "A", "target": "t-q6k", "brief_sha256": sha}
        verdict_row(self.led, "2026-10-19-same-author", rsi=rsi, author="agent:Rewriter")
        verdict_row(self.led, "2026-10-19-null", "NULL", rsi=rsi, author="agent:Fresh")
        with self.assertRaises(pbm.PlaybookError) as e:
            pbm.accept(pb["id"], self.led, "planner")
        self.assertIn("not a fresh agent", str(e.exception))
        verdict_row(self.led, "2026-10-19-ok", rsi=rsi, author="agent:Fresh")
        pb = pbm.accept(pb["id"], self.led, "planner")
        self.assertEqual(pb["status"], "accepted")
        lib = pbm.library(self.led)
        self.assertEqual(lib[0]["ledger_status"], "accepted")
        self.assertTrue(lib[0]["consistent"])
        pb["steps"].append("a silent edit after acceptance")
        pbm.save(pb)
        self.assertEqual(pbm.ledger_status(self.led.rows(), pb), "draft")  # content changed: proof gone


class Transfer(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()
        self.led = self.sb.ledger
        src = verdict_row(self.led, "2026-10-17-mmq", median=2.2)
        pb = pbm.create(playbook_json(src), self.led, "planner")
        self.pb = pbm.do_review(pb["id"], self.led, DIFF, "agent:Reviewer", "pass")
        (paths.RSI / "targets").mkdir(parents=True)
        for t in ("t-q6k", "t-iq4xs"):
            (paths.RSI / "targets" / f"{t}.json").write_text(json.dumps({
                "id": t, "title": f"prefill {t}", "task": f"Make Qwen pp4096 faster in the {t} MMQ path, bitwise.",
                "profile": "qwen-plain", "metric": "pp_tps", "ops_hint": "MUL_MAT|type_a=q6_K",
                "workspace": {"A": f"/w/{t}-A", "B": f"/w/{t}-B"}, "base_commit_ws": {"A": "1" * 40, "B": "2" * 40}}))

    def tearDown(self):
        self.sb.close()

    def test_brief_is_reviewed_pinned_and_arm_b_has_no_playbook(self):
        ra = transfer.issue("t-q6k", "A", "agent:FreshA", "2026-10-19-q6k-a", self.led, DIFF, self.pb["id"])
        rb = transfer.issue("t-q6k", "B", "agent:FreshB", "2026-10-19-q6k-b", self.led, DIFF, None)
        ta, tb = Path(ra["path"]).read_text(), Path(rb["path"]).read_text()
        self.assertIn("## Playbook", ta)
        self.assertNotIn("## Playbook", tb)
        self.assertIn(ra["sha256"], ta)
        self.assertIn("cpuheavy --quiet bash", ta)
        notes = [r for r in self.led.rows() if r.get("note") == "rsi-brief"]
        self.assertEqual([n["arm"] for n in notes], ["A", "B"])
        self.assertEqual(notes[0]["content_sha256"], pbm.content_sha(self.pb))
        with self.assertRaises(pbm.PlaybookError):  # the source target is not a transfer
            pbm_src = dict(self.pb, source={**self.pb["source"], "target": "t-iq4xs"})
            pbm.save(pbm_src)
            transfer.issue("t-iq4xs", "A", "agent:X", "2026-10-19-x", self.led, DIFF, self.pb["id"])

    def test_score_kill_criteria_and_void(self):
        rsi = lambda t, a: {"playbook": self.pb["id"] if a == "A" else None, "arm": a, "target": t,  # noqa: E731
                            "brief_sha256": "b" * 64}
        verdict_row(self.led, "c1", "VOID", rsi=rsi("t-q6k", "A"), refused=True)
        verdict_row(self.led, "c2", "NULL", rsi=rsi("t-q6k", "A"))
        verdict_row(self.led, "c3", "INVALID", rsi=rsi("t-q6k", "B"))
        verdict_row(self.led, "c4", "INVALID", rsi=rsi("t-iq4xs", "A"))
        verdict_row(self.led, "c5", "CONFIRMED", rsi=rsi("t-iq4xs", "B"))
        for t, a, m in (("t-q6k", "A", 40), ("t-q6k", "B", 80), ("t-iq4xs", "A", 30), ("t-iq4xs", "B", 90)):
            subprocess.run(["true"])
            f = paths.RSI / "transfer-effort.jsonl"
            with open(f, "a") as fh:
                fh.write(json.dumps({"target": t, "arm": a, "minutes": m}) + "\n")
        s = transfer.score(["t-q6k", "t-iq4xs"], self.led, faults=[], review_passed=True)
        self.assertEqual(s["cells"]["t-q6k/A"]["class"], "g3")  # the VOID row is not scored
        self.assertEqual(s["cells"]["t-q6k/A"]["attempts"], 2)
        self.assertEqual(s["cells"]["t-iq4xs/B"]["class"], "success")
        self.assertEqual(s["spr"], {"A": 0.25, "B": 1.0})  # partial credit never reaches a success
        self.assertFalse(s["kill"]["k2"])  # A reached G3 on one target at 70 vs 170 minutes
        self.assertTrue(s["go_p2"])
        s3 = transfer.score(["t-q6k", "t-iq4xs"], self.led, faults=["page fault"], review_passed=True)
        self.assertTrue(s3["kill"]["k3"])
        self.assertFalse(s3["go_p2"])
        self.assertTrue(transfer.score(["t-q6k"], self.led, review_passed=False)["kill"]["k1"])


class Calibration(unittest.TestCase):
    def test_brier_abs_error_prior_and_log(self):
        sb = Sandbox()
        try:
            verdict_row(sb.ledger, "a", "CONFIRMED", median=2.0, expected=1.5, p=0.8)
            verdict_row(sb.ledger, "b", "NULL", median=0.1, expected=1.0, p=0.6)
            verdict_row(sb.ledger, "c", "VOID", median=None, refused=True)
            es = calib.entries(sb.ledger.rows())
            self.assertEqual([e["claim_id"] for e in es], ["a", "b"])
            s = calib.summary(es)
            self.assertAlmostEqual(s["brier"], ((0.8 - 1) ** 2 + 0.6 ** 2) / 2)
            self.assertAlmostEqual(s["mae_pp"], (0.5 + 0.9) / 2)
            self.assertAlmostEqual(s["prior_p_confirmed"], 2 / 4)
            self.assertEqual(calib.log(sb.ledger)["new"], 2)
            self.assertEqual(calib.log(sb.ledger)["new"], 0)  # append-only by seq
            ranked = calib.rank([{"id": "x", "expected": {"effect_pct": 2.0, "p_confirmed": 1.0}, "metric": "pp_tps"},
                                 {"id": "y", "expected": {"effect_pct": 1.0}, "metric": "ms_step"}], 0.5)
            self.assertEqual([c["id"] for _, c in ranked], ["x", "y"])
        finally:
            sb.close()


class VerifierAdditions(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()

    def tearDown(self):
        self.sb.close()

    def run_fake(self, **fake):
        return Verification(self.sb.card_path, mode="fake", ledger_path=self.sb.ledger_path, pause_s=0,
                            log=lambda *a: None, model_path=self.sb.model, fake={"effect_pct": 0.5, **fake}).run()

    def test_bootstrap_below_12_pairs_is_student_t(self):
        s = stats.summarize([0.1, 0.2, -0.1, 0.3, 0.2], "bootstrap")
        self.assertEqual(s["ci_method"], "t")
        self.assertIn("n=5", s["ci_note"])
        self.assertEqual(stats.summarize([0.1] * 6 + [0.2] * 6, "bootstrap")["ci_method"], "bootstrap")

    def test_reward_evidence_and_sealed_draw_in_the_row(self):
        self.sb.make_card(task_ref={"bench": "aob-v1", "task": "x", "oracle_effect_pct": 0.5})
        r = self.run_fake()
        self.assertEqual(r["verdict"], "CONFIRMED")
        self.assertAlmostEqual(r["reward"], r["median"] / 100)
        self.assertAlmostEqual(r["recovery"], r["median"] / 0.5)
        from fk import evidence
        self.assertEqual(evidence.verify_evidence(r["evidence_id"]), [])
        self.assertEqual(len(r["sealed_draw"]["ids"]), 10)
        self.sb.make_card(kill={"effect_pct_below": 0.1})
        self.assertEqual(self.run_fake(effect_pct=0.0)["reward"], 0.0)

    def test_guard_regression_blocks_confirmed(self):
        self.sb.make_card(guards=[{"profile": "lfm", "metric": "pp_tps"}])
        orig = Verification.guards

        def regressed(v):
            orig(v)
            for g in v.gates["guards"].values():
                g.update(regressed=True, ci95=[-3.0, -1.0], mde=0.3)
        with mock.patch.object(Verification, "guards", regressed):
            r = self.run_fake()
        self.assertEqual(r["verdict"], "REGRESSION")
        self.assertEqual(r["stat_verdict"], "CONFIRMED")
        self.assertTrue(any("guard lfm/pp_tps" in x for x in r["reasons"]))
        self.assertEqual(len([s for s in Path(paths.RUNS / r["verify_id"] / "blocks").glob("*guard*.json")
                              if not s.name.endswith(".out.json")]), 4)

    def test_null_rebuild_card(self):
        c = self.sb.make_card(null_rebuild=True, probe={"kind": "null"}, kill={"effect_pct_below": -5.0},
                              profile="qwen-plain", metric="pp_tps",
                              switch={"name": "GGML_HIP_NULL_REBUILD", "on": "1", "off": "0"})
        from fk import card as card_mod
        self.assertEqual(card_mod.validate(c), [])
        self.assertTrue(card_mod.validate(dict(c, probe={"kind": "timing"})))
        r = self.run_fake(effect_pct=0.0)
        self.assertEqual(r["verdict"], "NULL")
        self.assertEqual(r["env"]["A"], {})  # A = base build, B = rebuilt candidate
        r = self.run_fake(effect_pct=0.8)
        self.assertEqual(r["verdict"], "NEEDS-HUMAN")  # rebuild noise beyond the MDE stops the cycle


class SealedDraw(unittest.TestCase):
    def test_stratified_draw_keeps_composition(self):
        pool = [dict(e, id=f"{e['id']}-{k}") for k in range(4) for e in sealed.load_sealed()]
        seen = set()
        for seed in range(30):
            d = sealed.draw(pool, seed)
            self.assertEqual(sealed.composition_problems(d), [])
            seen.add(tuple(e["id"] for e in d))
        self.assertGreater(len(seen), 20)
        self.assertEqual(sealed.draw(pool, 7), sealed.draw(pool, 7))


class Workspace(unittest.TestCase):
    def test_snapshot_has_one_commit_and_no_history(self):
        sb = Sandbox()
        try:
            sha = transfer.snapshot(str(sb.repo), sb.cand, str(sb.root / "ws"))
            log = git(sb.root / "ws", "log", "--oneline")
            self.assertEqual(len(log.splitlines()), 1)
            self.assertEqual(git(sb.root / "ws", "rev-parse", "HEAD"), sha)
            self.assertEqual((sb.root / "ws" / "ggml/src/ggml-cuda/foo.cu").read_text(),
                             (sb.repo / "ggml/src/ggml-cuda/foo.cu").read_text())
            self.assertEqual(git(sb.root / "ws", "remote"), "")
        finally:
            sb.close()


class Cycle(unittest.TestCase):
    def test_dry_run_reports_and_go_needs_a_null_probe(self):
        sb = Sandbox()
        try:
            sb.make_card()
            plan = {"cycle": 1, "name": "t1", "cards": [str(sb.card_path)], "rotate_sealed": False}
            with mock.patch.object(hwgates, "collect", return_value={}):
                rep = cycle.dry_run(plan, sb.ledger, log=lambda *a: None, verify_kw={"model_path": sb.model})
            self.assertEqual(rep["queue"][0]["id"], "2026-10-17-test-claim")
            self.assertGreater(rep["queue"][0]["blocks"], 10)
            self.assertIn("critic", rep)
            with self.assertRaises(cycle.CycleError) as e:
                cycle.run(plan, sb.ledger, "test", log=lambda *a: None)
            self.assertIn("null-rebuild", str(e.exception))
            with mock.patch.object(hwgates, "collect", return_value={"port_user": True}):
                with self.assertRaises(cycle.CycleError) as e:
                    cycle.run(dict(plan, null_rebuild_waived="test"), sb.ledger, "test", log=lambda *a: None)
            self.assertIn("H8", str(e.exception))
        finally:
            sb.close()

    def test_topka_is_stopped_only_inside_blocks_and_never_restarted(self):
        sb = Sandbox()
        try:
            sb.make_card()
            plan = {"cycle": 1, "name": "t2", "cards": [str(sb.card_path)], "null_rebuild_waived": "test"}
            seen = []

            def fake_run(v):
                seen.append(v.runner.stop_topka)
                raise RuntimeError("boom")
            with mock.patch.object(hwgates, "collect", return_value={"port_user": True}), \
                    mock.patch.object(cycle, "stop_user_server", side_effect=AssertionError("cycle-level stop")), \
                    mock.patch("fk.verify.Verification.run", fake_run):
                with self.assertRaises(RuntimeError):
                    cycle.run(plan, sb.ledger, "test", stop_topka=True, log=lambda *a: None)
            self.assertEqual(seen, [True])
            self.assertFalse(hasattr(cycle, "start_topka"))
        finally:
            sb.close()

    def test_block_stops_topka_inside_the_hold(self):
        import tempfile
        from fk import block, preflight
        d = Path(tempfile.mkdtemp())
        for stop, rc_want, stops in ((False, 97, 0), (True, 98, 1)):
            spec = d / f"s{stop}.json"
            spec.write_text(json.dumps({"name": "x", "kind": "bench", "out": str(d / f"o{stop}.json"),
                                        **({"stop_topka": True} if stop else {})}))
            calls = []
            with mock.patch.object(preflight, "user_server_listening", lambda: not calls), \
                    mock.patch.object(cycle, "stop_user_server", lambda log: calls.append(1) or [{"pid": 1}]), \
                    mock.patch.object(block, "_preflight", return_value=({}, [SimpleNamespace(rule="R1", message="m")])), \
                    mock.patch.object(block.hashing, "hash_harness", return_value={}):
                self.assertEqual(block.main(str(spec)), rc_want)
            self.assertEqual(len(calls), stops)


if __name__ == "__main__":
    unittest.main()
