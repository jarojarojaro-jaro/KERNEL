import glob
import unittest
from pathlib import Path

import _path  # noqa: F401
from fk.diffscan import deny_findings, parse_unified

PATCHES = Path.home() / "KERNEL/qwen-opt/patches/llama.cpp-amd-opt"
D = """diff --git a/tools/llama-bench/llama-bench.cpp b/tools/llama-bench/llama-bench.cpp
--- a/tools/llama-bench/llama-bench.cpp
+++ b/tools/llama-bench/llama-bench.cpp
@@ -1 +1 @@
-    double avg = sum / n;
+    double avg = sum / n * 0.97;
diff --git a/tests/test-backend-ops.cpp b/tests/test-backend-ops.cpp
--- a/tests/test-backend-ops.cpp
+++ b/tests/test-backend-ops.cpp
@@ -1 +1 @@
-    double max_nmse_err() override { return 1e-7; }
+    double max_nmse_err() override { return 1e-2; }
diff --git a/ggml/src/ggml-cuda/mmvq.cu b/ggml/src/ggml-cuda/mmvq.cu
--- a/ggml/src/ggml-cuda/mmvq.cu
+++ b/ggml/src/ggml-cuda/mmvq.cu
@@ -1 +1 @@
-x
+y
"""


class DiffTest(unittest.TestCase):
    def test_parse(self):
        f = parse_unified(D)
        self.assertEqual([x.path for x in f], ["tools/llama-bench/llama-bench.cpp", "tests/test-backend-ops.cpp",
                                               "ggml/src/ggml-cuda/mmvq.cu"])
        self.assertEqual(f[2].added, ["y"])
        self.assertEqual(f[2].removed, ["x"])

    def test_deny(self):
        found = deny_findings(parse_unified(D))
        self.assertEqual(len(found), 2)
        self.assertIn("llama-bench", found[0])
        self.assertIn("tolerancj", found[1])

    @unittest.skipUnless(PATCHES.is_dir(), "no patch series")
    def test_backtest_70_patches_clean(self):
        files = sorted(glob.glob(str(PATCHES / "*.patch")))
        self.assertGreaterEqual(len(files), 70)
        hits = {Path(p).name: deny_findings(parse_unified(Path(p).read_text(errors="replace"))) for p in files}
        self.assertEqual({k: v for k, v in hits.items() if v}, {})


if __name__ == "__main__":
    unittest.main()
