import shutil
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from fk import aob, card

IDS = ["fix_mtp_embd_state_rebase", "fix_q8_1_overflow", "neg_pm4_pdl_ceiling", "opt_mmq_epilogue",
       "opt_sampler_slow_path"]


class AobTest(unittest.TestCase):
    def test_all_tasks_load_and_validate(self):
        self.assertEqual(aob.list_tasks(), IDS)
        for tid in IDS:
            t = aob.load_task(tid)
            self.assertEqual(aob.validate_task(t), [], tid)
        neg = aob.load_task("neg_pm4_pdl_ceiling")
        self.assertEqual(neg["gpu_minutes"], 0)
        self.assertEqual(aob.load_task("fix_q8_1_overflow")["status"], "needs-fixture")

    def _copy(self, tid):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(aob.TASKS / tid, tmp / tid)
        return tmp

    def test_leak_refused(self):
        tmp = self._copy("opt_mmq_epilogue")
        ins = tmp / "opt_mmq_epilogue" / "instruction.md"
        ins.write_text(ins.read_text() + "\nSee commit f61994f for a hint.\n")
        p = aob.validate_task(aob.load_task("opt_mmq_epilogue", tmp))
        self.assertTrue(any("oracle commit" in x for x in p), p)
        ins.write_text("Patch 0070 and GGML_HIP_MMQ_EPI\n")
        p = aob.validate_task(aob.load_task("opt_mmq_epilogue", tmp))
        self.assertTrue(any("patch number" in x for x in p) and any("oracle switch" in x for x in p), p)

    def test_neg_gpu_and_pm4_refused(self):
        tmp = self._copy("neg_pm4_pdl_ceiling")
        f = tmp / "neg_pm4_pdl_ceiling" / "task.toml"
        f.write_text(f.read_text().replace("gpu_minutes = 0", "gpu_minutes = 5") + 'env = "GGML_HIP_PM4=1"\n')
        p = aob.validate_task(aob.load_task("neg_pm4_pdl_ceiling", tmp))
        self.assertTrue(any("neg task" in x for x in p) and any("GGML_HIP_PM4" in x for x in p), p)

    def test_reward_opt(self):
        t = aob.load_task("opt_mmq_epilogue")
        r = aob.reward(t, {"verdict": "CONFIRMED", "median": 2.2})
        self.assertAlmostEqual(r["reward"], 0.022)
        self.assertAlmostEqual(r["recovery"], 1.0)
        self.assertFalse(r["needs_human"])
        self.assertEqual(aob.reward(t, {"verdict": "NULL", "median": 2.2})["reward"], 0.0)
        self.assertTrue(aob.reward(t, {"verdict": "CONFIRMED", "median": 5.0})["needs_human"])

    def test_reward_fix_neg(self):
        t = aob.load_task("fix_q8_1_overflow")
        self.assertEqual(aob.reward(t, {"f2p_pass": True, "p2p_pass": True, "f2p": 1.0})["reward"], 1.0)
        self.assertEqual(aob.reward(t, {"f2p_pass": True, "p2p_pass": False, "f2p": 0.5})["reward"], 0.0)
        n = aob.load_task("neg_pm4_pdl_ceiling")
        r = aob.reward(n, {"decision": "kill", "pred_effect_pct": 2.9})
        self.assertEqual((r["reward"], r["estimate"]), (1.0, 1.0))
        r = aob.reward(n, {"decision": "go", "pred_effect_pct": 12.0})
        self.assertEqual(r["reward"], 0.0)
        self.assertEqual(r["estimate"], 0.0)  # |log(12/2.9)| > 1
        self.assertEqual(aob.reward(n, {"decision": "kill", "pred_effect_pct": -1})["estimate"], 0.0)

    def test_make_card_valid(self):
        allowed = ("repo", "commits", "touched_paths", "builds", "model_sha256")
        for tid in IDS:
            t = aob.load_task(tid)
            if t["kind"] == "neg":
                with self.assertRaises(ValueError):
                    aob.make_card(t, "/ws", "a", "b", "agent:X")
                continue
            c = aob.make_card(t, "/ws/src", "aaa", "bbb", "agent:Impl")
            self.assertEqual(c["metric"], t["metric"])
            p = [x for x in card.validate(c, filled=False) if not any(a in x for a in allowed)]
            self.assertEqual(p, [], tid)

    def test_run_plan_gpu_only_via_factory(self):
        plan = aob.run_plan(IDS)
        for s in plan:
            if s["gpu"]:
                self.assertEqual(s["cmd"][:2], ["./factory", "verify"])
        self.assertFalse(any(s["gpu"] for s in plan if s["task"] == "neg_pm4_pdl_ceiling"))

    def test_leak_texts_skips_missing(self):
        out = aob.leak_texts("test", repo="/nonexistent")
        self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
