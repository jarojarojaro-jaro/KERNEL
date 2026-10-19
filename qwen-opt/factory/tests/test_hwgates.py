"""Hardware gates H0-H11 (fk/hwgates.py): every gate fires on its incident and stays quiet on a clean machine, and the
factory really refuses (Runner, block, G0). No GPU, no locks, no journal: facts are fed in, probes are mocked."""
import json
import subprocess
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import _path  # noqa: F401
from fk import gpu, hwgates, paths
from fk.verify import Verification
from sandbox import Sandbox

CLEAN = {
    "wrap": ["flock", "/tmp/gpu.lock", "flock", "/tmp/quiet.lock"], "block_timeout": 290,
    "locks": {"/tmp/gpu.lock": True, "/tmp/quiet.lock": True},
    "guard": True, "temp_c": {"edge": 40.0, "junction": 48.0, "mem": 56.0},
    "env": {"GGML_HIP_PM4": "0", "GGML_HIP_X": "1"}, "card": {"touched_paths": ["ggml/src/ggml-cuda/mmq.cuh"],
                                                             "ops": ["MUL_MAT"], "switch": {"name": "GGML_HIP_X"}},
    "pm4_safe": False, "halt": None, "initialized": True,
    "builds": {"/b/cand": "t" * 64}, "quarantine": {},
    "faults": [], "gpu_s_day": 600.0, "gpu_s_30d": 3600.0, "hw_invalid_streak": 0,
    "texts": ["+ float t = a * b;"], "power": {"power_cap_uw": "327000000", "perf_level": "auto", "od_sha256": "x"},
    "baseline": {"power_cap_uw": "327000000", "perf_level": "auto", "od_sha256": "x"},
    "port_user": False, "ssd_bytes": 100 << 20, "ssd_day": 10 << 20, "disk_free": 200 << 30,
    "cloud": None, "where": "local",
    "commands": [{"kind": "build", "cmd": "flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 cmake --build b -j2"},
                 {"kind": "script", "cmd": "flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 python3 x.py -t 2"}],
    "load1": 1.0, "nproc": 16,
}

FIRE = {
    "H0": [{"wrap": ["timeout", "290"]}, {"locks": {"/tmp/gpu.lock": False, "/tmp/quiet.lock": True}},
           {"block_timeout": 900}],
    "H1": [{"guard": False}, {"temp_c": {"junction": 70.0, "mem": 50.0}}, {"temp_c": {"junction": 50.0, "mem": 75.0}},
           {"temp_c": {}}],
    "H2": [{"env": {"GGML_HIP_X": "1"}}, {"env": {"GGML_HIP_PM4": "1"}},
           {"env": {"GGML_HIP_PM4": "1"}, "card": {"switch": {"name": "GGML_HIP_PM4"}}, "pm4_safe": False}],
    "H3": [{"halt": {"ts": "2026-10-19 03:00:00", "reason": "page fault in block 05"}},
           {"quarantine": {"t" * 64: {"reason": "page fault"}}}],
    "H4": [{"faults": ["boot 0: amdgpu: [gfxhub] page fault (src_id:0 ring:24 ...)"]}, {"initialized": False}],
    "H5": [{"card": {"touched_paths": ["ggml/src/ggml-cuda/mmq.cuh"], "ops": []}}],
    "H6": [{"gpu_s_day": 3500.0}, {"gpu_s_30d": 15 * 3600 - 100}, {"hw_invalid_streak": 2}],
    "H7": [{"texts": ["echo manual > /sys/class/drm/card0/device/power_dpm_force_performance_level"]},
           {"texts": ["sudo rocm-smi --setpoweroverdrive 300"]}, {"texts": ["echo 's 1 2900' > pp_od_clk_voltage"]},
           {"power": {"power_cap_uw": "250000000", "perf_level": "auto", "od_sha256": "x"}},
           {"power": {"power_cap_uw": "327000000", "perf_level": "manual", "od_sha256": "x"}}],
    "H8": [{"port_user": True}],
    "H9": [{"ssd_bytes": 3 << 30}, {"ssd_day": 600 << 20}, {"disk_free": 5 << 30}],
    "H10": [{"where": "cloud", "cloud": None},
            {"where": "cloud", "cloud": {"watchdog": "/etc/hostname", "deadline_min": 0, "max_usd": 5}},
            {"where": "cloud", "cloud": {"watchdog": "/etc/hostname", "deadline_min": 60}}],
    "H11": [{"commands": [{"kind": "build", "cmd": "nice -n 19 taskset -c 0-1 cmake --build build -j2"}]},  # no lock
            {"commands": [{"kind": "build", "cmd": "flock /tmp/cpuheavy.lock nice -n 10 taskset -c 0-1 "
                                                    "cmake --build build -j2"}]},
            {"commands": [{"kind": "build", "cmd": "flock /tmp/cpuheavy.lock nice -n 19 cmake --build build -j2"}]},
            {"commands": [{"kind": "build", "cmd": "flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-7 "
                                                    "cmake --build build -j2"}]},
            {"commands": [{"kind": "build", "cmd": "flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 "
                                                    "cmake --build build -j6"}]},
            {"commands": [{"kind": "script", "cmd": "python3 heavy.py"}]},
            {"commands": [{"kind": "script", "cmd": "flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 "
                                                     "python3 heavy.py --threads 8"}]},
            {"load1": 9.0}],
}


class EachGate(unittest.TestCase):
    def test_clean_machine_passes_every_gate(self):
        self.assertEqual(hwgates.check(CLEAN), {})

    def test_every_gate_has_firing_cases(self):
        self.assertEqual(set(FIRE), set(hwgates.GATES))

    def _fires(self, gate):
        for over in FIRE[gate]:
            got = hwgates.check({**CLEAN, **over})
            self.assertEqual(set(got), {gate}, f"{gate} {over}: {got}")

    def test_h0_one_gpu_job_locks(self): self._fires("H0")
    def test_h1_guard_and_start_temperature(self): self._fires("H1")
    def test_h2_pm4_off(self): self._fires("H2")
    def test_h3_quarantine_and_halt(self): self._fires("H3")
    def test_h4_kernel_faults_all_boots(self): self._fires("H4")
    def test_h5_kernel_change_needs_ops(self): self._fires("H5")
    def test_h6_gpu_budget_and_streak(self): self._fires("H6")
    def test_h7_no_clock_voltage_power(self): self._fires("H7")
    def test_h8_user_server(self): self._fires("H8")
    def test_h9_ssd_budget(self): self._fires("H9")
    def test_h10_cloud_watchdog(self): self._fires("H10")
    def test_h11_cpu_hygiene(self): self._fires("H11")

    def test_clean_variants(self):
        ok = [("H2", {"env": {"GGML_HIP_PM4": "1"}, "card": {"switch": {"name": "GGML_HIP_PM4_X"}}, "pm4_safe": True}),
              ("H5", {"card": {"touched_paths": ["common/sampling.cpp"], "ops": []}}),
              ("H10", {"where": "cloud", "cloud": {"watchdog": "/etc/hostname", "deadline_min": 60, "max_usd": 5}}),
              ("H7", {"baseline": None}),
              ("H1", {"temp_c": {"junction": 69.0, "mem": 74.0}})]
        for g, over in ok:
            self.assertNotIn(g, hwgates.check({**CLEAN, **over}), f"{g} {over}")


class PowerFacts(unittest.TestCase):
    OD = ("OD_SCLK:\n0: 500Mhz\n1: {sclk}Mhz\nOD_MCLK:\n0: 97Mhz\n1: 1250MHz\nOD_VDDGFX_OFFSET:\n{off}mV\n"
          "OD_FAN_CURVE:\n0: 25C {fan}%\nOD_RANGE:\nSCLK:     500Mhz       5000Mhz\n"
          "VDDGFX_OFFSET:    -450mv          0mv\n")

    def facts(self, sclk=2895, off=0, fan=30, curve="idle"):
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp())
        (d / "hwmon" / "hwmon3").mkdir(parents=True)
        (d / "hwmon" / "hwmon3" / "power1_cap").write_text("327000000\n")
        (d / "power_dpm_force_performance_level").write_text("auto\n")
        (d / "pp_od_clk_voltage").write_text(self.OD.format(sclk=sclk, off=off, fan=fan))
        (d / "gpu_od" / "fan_ctrl").mkdir(parents=True)
        (d / "gpu_od" / "fan_ctrl" / "fan_curve").write_text(curve)
        return hwgates.power_facts(d)

    def h7(self, now):
        return hwgates.check({**CLEAN, "power": now, "baseline": self.facts()}).get("H7")

    def test_fan_curve_flips_do_not_fire(self):
        self.assertFalse(self.h7(self.facts(fan=100, curve="load")))

    def test_clock_and_voltage_changes_fire(self):
        self.assertTrue(self.h7(self.facts(sclk=2500)))
        self.assertTrue(self.h7(self.facts(off=-50)))



class State(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_kernel_faults_scans_every_boot_since_watermark(self):
        calls = []
        boots = (" -2 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa Fri 2026-10-16 12:20:09 UTC Fri 2026-10-16 18:02:46 UTC\n"
                 " -1 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb Sun 2026-10-18 18:53:17 UTC Sun 2026-10-18 20:26:50 UTC\n"
                 "  0 cccccccccccccccccccccccccccccccc Sun 2026-10-18 20:27:16 UTC Mon 2026-10-19 03:20:00 UTC\n")

        def run(argv, **k):
            calls.append(argv)
            if "--list-boots" in argv:
                return subprocess.CompletedProcess(argv, 0, boots, "")
            out = "2026-10-18T19:47:46+00:00 host kernel: amdgpu: [gfxhub] page fault\n" if "b" * 32 in argv else ""
            return subprocess.CompletedProcess(argv, 0, out, "")
        with mock.patch.object(hwgates.subprocess, "run", side_effect=run):
            lines = hwgates.kernel_faults("2026-10-18 10:00:00")
        scanned = [a[a.index("-b") + 1] for a in calls if "-b" in a]
        self.assertEqual(scanned, ["b" * 32, "c" * 32])  # boot -2 ended before the watermark
        self.assertTrue(all("-k" in a and "--since" in a for a in calls if "-b" in a))
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("boot -1:"))

    def test_fault_after_block_quarantines_build_and_halts(self):
        with mock.patch.object(hwgates, "kernel_faults", return_value=["boot 0: amdgpu page fault"]):
            with self.assertRaises(hwgates.HardwareStop):
                hwgates.after_block("2026-10-19 03:00:00", self.sb.cand_build, "vid1", "05-bench")
        tree = hwgates.build_tree(self.sb.cand_build)
        self.assertIn(tree, hwgates.quarantined())
        self.assertTrue(hwgates.load_state()["halt"])
        f = {**CLEAN, "halt": hwgates.load_state()["halt"], "builds": {str(self.sb.cand_build): tree},
             "quarantine": hwgates.quarantined()}
        self.assertEqual(len(hwgates.h3(f)), 2)
        with mock.patch.object(hwgates, "kernel_faults", return_value=["boot 0: amdgpu page fault"]):
            r = hwgates.ack("read the fault: build quarantined, PM4 off", "human")
        self.assertEqual(r["faults_acknowledged"], 1)
        st = hwgates.load_state()
        self.assertIsNone(st["halt"])
        self.assertIn(tree, hwgates.quarantined())  # the quarantine outlives the ack
        with mock.patch.object(hwgates, "kernel_faults", return_value=[]):
            hwgates.after_block("2026-10-19 03:00:00", self.sb.base_build, "vid1", "06-bench")  # clean: no raise

    def test_budget_and_streak_bookkeeping(self):
        hwgates.record_block("v", "01", 1700.0)
        hwgates.record_block("v", "02", 1700.0)
        self.assertGreater(hwgates.gpu_seconds(86400), 3399)
        self.assertIn("H6", hwgates.check({"gpu_s_day": hwgates.gpu_seconds(86400)}))
        self.assertEqual(hwgates.record_verdict("INVALID", ["G1: block exited -9 without a result (timeout 290 s?)"]), 1)
        self.assertEqual(hwgates.record_verdict("INVALID", ["refused: H3 hardware stop: fault"]), 2)
        self.assertEqual(hwgates.record_verdict("NULL", []), 0)
        self.assertEqual(hwgates.record_verdict("INVALID", ["G2: md5 differs"]), 0)  # not a hardware INVALID

    def test_enforce_waits_on_transient_then_refuses(self):
        hot = {**CLEAN, "temp_c": {"junction": 80.0, "mem": 60.0}}
        sleeps = []
        with mock.patch.object(hwgates, "collect", return_value=dict(hot)), \
                mock.patch.object(hwgates, "temps", return_value={"junction": 80.0, "mem": 60.0}), \
                mock.patch.object(hwgates, "loadavg1", return_value=1.0), \
                mock.patch.object(hwgates, "WAIT_MAX_S", 60):
            with self.assertRaises(hwgates.HwRefused) as e:
                hwgates.enforce({}, wait=True, log=lambda *a: None, sleep=sleeps.append)
        self.assertEqual(set(e.exception.failures), {"H1"})
        self.assertEqual(sleeps, [hwgates.WAIT_POLL_S] * 2)
        with mock.patch.object(hwgates, "collect", return_value=dict(hot)), \
                mock.patch.object(hwgates, "temps", return_value={"junction": 50.0, "mem": 60.0}), \
                mock.patch.object(hwgates, "loadavg1", return_value=1.0):
            hwgates.enforce({}, wait=True, log=lambda *a: None, sleep=lambda s: None)  # cooled down: passes
        with mock.patch.object(hwgates, "collect", return_value={**hot, "port_user": True}):
            with self.assertRaises(hwgates.HwRefused):  # H8 is not transient: no waiting
                hwgates.enforce({}, wait=True, log=lambda *a: None, sleep=lambda s: self.fail("waited"))


class FactoryRefuses(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_runner_refuses_block_on_gate(self):
        self.sb.make_card()
        never = mock.Mock(side_effect=AssertionError("block executed"))
        with mock.patch.object(gpu, "subprocess", SimpleNamespace(run=never)), \
                mock.patch.object(hwgates, "collect", return_value={**CLEAN, "port_user": True}):
            v = Verification(self.sb.card_path, mode="real", ledger_path=self.sb.ledger_path, pause_s=0,
                             log=lambda *a: None, model_path=self.sb.model)
            r = v.run()
        self.assertEqual(r["verdict"], "VOID")  # 21i A3: a refusal is re-run, never scored
        self.assertIn("H8", r["void_reason"])
        self.assertTrue(r["refused"])
        self.assertTrue(any("H8" in x for x in r["reasons"]), r["reasons"])

    def test_g0_refuses_quarantined_build(self):
        self.sb.make_card()
        hwgates.quarantine(self.sb.cand_build, "page fault in test")
        v = Verification(self.sb.card_path, mode="fake", ledger_path=self.sb.ledger_path, pause_s=0,
                         log=lambda *a: None, model_path=self.sb.model)
        r = v.run()
        self.assertEqual(r["verdict"], "INVALID")
        self.assertTrue(any("H3" in x and "quarantined" in x for x in r["reasons"]), r["reasons"])

    def test_g0_refuses_power_change_in_diff_and_missing_ops(self):
        sb = Sandbox(cand_src='static void foo() { system("echo 300000000 > /sys/class/drm/card0/device/hwmon/'
                              'hwmon2/power1_cap"); getenv("GGML_HIP_TESTSW"); }\n')
        try:
            sb.make_card(ops=[])
            r = Verification(sb.card_path, mode="fake", ledger_path=sb.ledger_path, pause_s=0, log=lambda *a: None,
                             model_path=sb.model).run()
            self.assertEqual(r["verdict"], "INVALID")
            txt = " ".join(r["reasons"])
            self.assertIn("H7", txt)
            self.assertIn("H5", txt)
        finally:
            sb.close()

    def test_block_env_forces_pm4_off(self):
        self.sb.make_card()
        r = Verification(self.sb.card_path, mode="fake", ledger_path=self.sb.ledger_path, pause_s=0,
                         log=lambda *a: None, model_path=self.sb.model).run()
        specs = list((paths.RUNS / r["verify_id"] / "blocks").glob("*[0-9][A-Z].json")) or \
            [p for p in (paths.RUNS / r["verify_id"] / "blocks").glob("*.json") if not p.name.endswith(".out.json")]
        self.assertTrue(specs)
        self.assertTrue(all(json.loads(p.read_text())["env"]["GGML_HIP_PM4"] == "0" for p in specs))
        self.assertEqual(r["hw_env"], {"GGML_HIP_PM4": "0"})


if __name__ == "__main__":
    unittest.main()
