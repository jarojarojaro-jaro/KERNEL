import unittest

import _path  # noqa: F401
import rules
from fk import preflight


class Preflight(unittest.TestCase):
    def test_snapshot_shape(self):
        s = preflight.snapshot(port=18499)  # /proc, /sys and pgrep only
        for k in ("user_server", "llama_servers", "kfd_procs", "power_control", "vram_used", "gtt_used", "temp_c",
                  "loadavg", "nproc", "port_free"):
            self.assertIn(k, s)
        rules.run("preflight", {"snapshot": s})  # must not raise on a real snapshot

    def test_port_free(self):
        self.assertIsInstance(preflight.port_free(18498), bool)


if __name__ == "__main__":
    unittest.main()
