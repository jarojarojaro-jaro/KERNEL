"""Replay tests for the llama-server log / GET /slots parsing (python3 test_sensors.py).

The sample lines are copied verbatim from ~/qwen-opt/logs/server-2026-11-06_132917.log;
test_real_logs additionally replays every server-*.log found there.
"""
import glob
import os
import re
import tempfile
import time
import unittest

from sensors import LlamaLog

PREFILL = """\
76.54.221.722 I slot      release: id  0 | task 3307 | stop processing: n_tokens = 476, truncated = 0
76.54.392.116 I slot launch_slot_: id  0 | task 3437 | processing task, is_child = 0
76.58.858.471 I slot print_timing: id  0 | task 3437 | prompt processing, n_tokens =   4096, progress = 0.34, t =   3.40 s / 1206.00 tokens per second
77.01.015.959 I slot print_timing: id  0 | task 3437 | prompt processing, n_tokens =   6144, progress = 0.51, t =   5.54 s / 1108.86 tokens per second
77.03.212.031 I slot print_timing: id  0 | task 3437 | prompt processing, n_tokens =   8192, progress = 0.68, t =   7.72 s / 1061.33 tokens per second
77.05.439.740 I slot print_timing: id  0 | task 3437 | prompt processing, n_tokens =  10240, progress = 0.86, t =   9.93 s / 1031.24 tokens per second
77.06.824.188 I slot print_timing: id  0 | task 3437 | prompt processing, n_tokens =  11446, progress = 0.96, t =  11.62 s / 985.21 tokens per second
77.07.409.651 I slot print_timing: id  0 | task 3437 | prompt processing, n_tokens =  11958, progress = 1.00, t =  12.45 s / 960.26 tokens per second
77.07.450.892 I slot print_timing: id  0 | task 3437 | prompt eval time =   13058.76 ms / 11962 tokens (    1.09 ms per token,   916.01 tokens per second)
77.07.450.894 I slot print_timing: id  0 | task 3437 |        eval time =       0.00 ms /     1 tokens (    0.00 ms per token,     0.00 tokens per second)
77.07.451.250 I slot      release: id  0 | task 3437 | stop processing: n_tokens = 11962, truncated = 0
""".splitlines()

DECODE = """\
0.27.752.373 I slot launch_slot_: id  0 | task 153 | processing task, is_child = 0
0.31.029.788 I slot print_timing: id  0 | task 153 | n_gen =    314, tg = 103.91 t/s, tg_3s = 104.24 t/s
0.31.889.372 I slot print_timing: id  0 | task 153 | prompt eval time =     265.18 ms /   116 tokens (    2.29 ms per token,   437.43 tokens per second)
0.31.889.375 I slot print_timing: id  0 | task 153 |        eval time =    3871.80 ms /   400 tokens (    9.70 ms per token,   103.05 tokens per second)
0.31.889.409 I slot      release: id  0 | task 153 | stop processing: n_tokens = 515, truncated = 0
""".splitlines()

PP_RE = re.compile(r"prompt processing, n_tokens = +(\d+), progress = ([\d.]+), "
                   r"t = +([\d.]+) s / ([\d.]+) tokens per second")


class Tail:
    """A log file that grows line by line, read through LlamaLog.poll() like the monitor."""

    def __init__(self):
        fd, self.path = tempfile.mkstemp(suffix=".log")
        os.close(fd)
        self.log = LlamaLog(self.path)
        self.log.poll()                     # first poll = history (not fresh)

    def add(self, line):
        with open(self.path, "a") as f:
            f.write(line + "\n")
        self.log.poll()

    def close(self):
        os.unlink(self.path)


class LogReplay(unittest.TestCase):
    def setUp(self):
        self.t = Tail()
        self.log = self.t.log

    def tearDown(self):
        self.t.close()

    def test_prefill_live(self):
        lg = self.log
        self.t.add(PREFILL[0])
        self.assertEqual(lg.phase, "idle")
        self.t.add(PREFILL[1])                       # launch_slot_
        self.assertEqual(lg.phase, "prefill")
        self.assertIsNone(lg.prefill_rate)
        t_before = time.monotonic()
        self.t.add(PREFILL[2])
        self.assertEqual(lg.phase, "prefill")
        self.assertEqual((lg.prefill_n, lg.prefill_progress, lg.prefill_rate),
                         (4096, 0.34, 1206.0))
        self.assertGreaterEqual(lg.prefill_ts, t_before)
        self.assertEqual(lg.live_prefill(), 1206.0)
        self.assertEqual(lg.live_rate(), 0.0)
        for ln in PREFILL[3:8]:
            self.t.add(ln)
        self.assertEqual((lg.prefill_n, lg.prefill_progress, lg.prefill_rate),
                         (11958, 1.0, 960.26))
        self.assertEqual(lg.prefill_peak, 1206.0)
        self.t.add(PREFILL[8])               # prompt eval time
        self.assertEqual((lg.last_prompt, lg.last_prompt_n), (916.01, 11962))
        for ln in PREFILL[9:]:
            self.t.add(ln)
        self.assertEqual(lg.phase, "idle")
        self.assertEqual(lg.live_prefill(), 0.0)
        self.assertEqual(lg.live_rate(), 0.0)
        self.assertEqual(lg.last_prompt, 916.01)     # kept after the request

    def test_eta(self):
        for ln in PREFILL[1:5]:
            self.t.add(ln)
        # 4096 -> 8192 tokens moved progress 0.34 -> 0.68: ~12 048 total, ~3 856 left
        self.assertIsNotNone(self.log.eta)
        self.assertAlmostEqual(self.log.eta, 3856 / (4096 / 4.32), delta=0.3)

    def test_decode_from_log(self):
        lg = self.log
        self.t.add(DECODE[0])
        self.t.add(DECODE[1])
        self.assertEqual(lg.phase, "decode")
        self.assertEqual(lg.live_rate(), 104.24)
        self.assertEqual(lg.n_generated(), 314)
        for ln in DECODE[2:]:
            self.t.add(ln)
        self.assertEqual(lg.phase, "idle")
        self.assertEqual(lg.live_rate(), 0.0)        # no 5 s afterglow once released
        self.assertEqual((lg.last_prompt, lg.last_eval), (437.43, 103.05))

    def test_history_is_not_live(self):
        with open(self.t.path, "a") as f:
            f.write("\n".join(PREFILL[:5]) + "\n")
        lg = LlamaLog(self.t.path)
        lg.poll()
        self.assertEqual(lg.phase, "prefill")        # mid-prefill when the monitor starts
        self.assertEqual(lg.prefill_n, 8192)
        self.assertEqual(lg.prefill_ts, 0.0)
        self.assertEqual(lg.events, 0)

    def test_slots_decode_rate(self):
        lg = self.log
        self.t.add(DECODE[0])
        t = time.monotonic() + 0.01                  # snapshots taken after the launch line
        lg.from_slots((t, [(0, 153, True, 0, 116)]))
        self.assertEqual(lg.phase, "prefill")
        lg.from_slots((t + 0.25, [(0, 153, True, 10, 116)]))
        self.assertEqual(lg.phase, "decode")
        lg.from_slots((t + 0.5, [(0, 153, True, 35, 116)]))
        lg.from_slots((t + 0.75, [(0, 153, True, 60, 116)]))
        self.assertAlmostEqual(lg.live_rate(), 100.0, delta=0.5)
        self.assertEqual(lg.n_generated(), 60)
        lg.from_slots((t + 1.0, [(0, 153, False, 60, 116)]))
        self.assertEqual(lg.phase, "idle")
        self.assertEqual(lg.live_rate(), 0.0)
        self.assertFalse(lg.active)

    def test_stale_slots_ignored_after_release(self):
        lg = self.log
        self.t.add(DECODE[0])
        snap = (time.monotonic(), [(0, 153, True, 50, 116)])
        for ln in DECODE[1:]:
            self.t.add(ln)
        lg.from_slots(snap)                          # taken before the release line
        self.assertEqual(lg.phase, "idle")


class RealLogs(unittest.TestCase):
    def test_real_logs(self):
        files = sorted(glob.glob(os.path.expanduser("~/qwen-opt/logs/server-*.log")))
        if not files:
            self.skipTest("no server logs")
        n_pp = 0
        for path in files:
            lg = LlamaLog(path)
            with open(path, "rb") as f:
                for raw in f:
                    ln = raw.rstrip(b"\n")
                    lg._line(ln, True)
                    m = PP_RE.search(ln.decode("utf-8", "replace"))
                    if m and b"print_timing" in ln:
                        n_pp += 1
                        self.assertEqual(lg.phase, "prefill")
                        self.assertEqual(lg.prefill_n, int(m.group(1)))
                        self.assertEqual(lg.prefill_progress, float(m.group(2)))
                        self.assertEqual(lg.prefill_rate, float(m.group(4)))
        print("\nreplayed %d logs, %d live prefill lines" % (len(files), n_pp))


if __name__ == "__main__":
    unittest.main(verbosity=2)
