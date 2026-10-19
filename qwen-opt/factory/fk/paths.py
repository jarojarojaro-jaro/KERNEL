"""Fixed locations and limits of the factory. Harness-owned: the implementer never changes these."""
from __future__ import annotations

import os
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
FACTORY = Path(__file__).resolve().parent.parent
QWEN_OPT = FACTORY.parent

LEDGER = FACTORY / "ledger.jsonl"
LEDGER_FAKE = FACTORY / "ledger.fake.jsonl"
RUNS = Path(os.environ.get("FACTORY_RUNS", FACTORY / "runs"))  # logs and block results of each verify
CACHE = Path(os.environ.get("FACTORY_CACHE", FACTORY / "cache"))  # sha256 of large files by (path, size, mtime)
CLAIMS = FACTORY / "claims"
SEALED_DIR = FACTORY / "sealed"
HARNESS_LOCK = FACTORY / "HARNESS.lock"
WIKI_DRAFTS = FACTORY / "wiki-drafts"

# existing tools the verifier wraps (pinned by hash in HARNESS.lock and in every ledger row)
GREEDY_SH = QWEN_OPT / "fusion" / "greedy.sh"
SPEC_SWEEP = QWEN_OPT / "spec_sweep.py"
KLD_GATE = QWEN_OPT / "tools" / "kld_gate.py"
TBO_PARSE = QWEN_OPT / "tools" / "kt" / "tbo_parse.py"   # G1 consistency (21j P4)
EXTERNAL_HARNESS = (GREEDY_SH, SPEC_SWEEP, KLD_GATE, TBO_PARSE)

ROCM_LIB = "/opt/rocm/core-10.0/lib"
MODELS = HOME / "models"

GPU_WRAP = ["flock", "/tmp/gpu.lock", "flock", "/tmp/quiet.lock"]
USER_PORT = 8080          # the user's live server (topka/production); detected with `ss -ltn 'sport = :8080'`
PORT_MIN, PORT_MAX = 18434, 18499
DEFAULT_PORT = 18471
BLOCK_TIMEOUT_S = 290      # one GPU block (inside both locks) never exceeds 5 min
PAUSE_S = 45               # pause between GPU blocks
PEAK_BW = 960e9            # RX 7900 XTX, bytes/s
ROOFLINE_MAX = 0.95        # bytes_per_pass / t_pass must stay below 95 % of peak

DRM_DEVICE = Path("/sys/class/drm/card0/device")

# RSI-F (report 21h §5): playbook library, transfer targets, cycle records; machine state of the hardware gates
PLAYBOOKS = FACTORY / "playbooks"
RSI = Path(os.environ.get("FACTORY_RSI", FACTORY / "rsi"))
RSI_STATE = Path(os.environ.get("FACTORY_RSI_STATE", RSI / "state"))
HW_ENV = {"GGML_HIP_PM4": "0"}  # H2: PM4 replay off in every block (report 17: it causes GPU resets)
GPU_GUARD = QWEN_OPT / "tools" / "gpu-guard.sh"
TOPKA = QWEN_OPT / "run-topka.sh"
TOPKA_LOG = QWEN_OPT / "logs" / "topka-8080.launcher.log"
EVIDENCE = Path(os.environ.get("FACTORY_EVIDENCE", FACTORY / "evidence"))  # sha256-addressed, zstd (fk/evidence.py)
AOB = FACTORY / "aob"      # AMD-Opt Bench aob-v1 (report 21i §5): RSI-F progress measure
