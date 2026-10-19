"""Throwaway world for the tests: a git repo with a base and a candidate commit, two fake builds, a fake model, a
ledger with a harness lock, a filled and registered claim card. CPU only, everything under one temp dir."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from fk import card as card_mod
from fk import hashing, paths
from fk.ledger import Ledger

SWITCH = "GGML_HIP_TESTSW"
FAKE_SERVER = Path(__file__).resolve().parent / "fake_llama_server.py"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


class Sandbox:
    def __init__(self, cand_src: str | None = None, extra_files: dict | None = None):
        self.tmp = tempfile.TemporaryDirectory(prefix="factory-test-")
        self.root = Path(self.tmp.name)
        self._saved = (paths.RUNS, paths.CACHE, paths.RSI, paths.RSI_STATE, paths.PLAYBOOKS, paths.EVIDENCE)
        paths.RUNS = self.root / "runs"
        paths.CACHE = self.root / "cache"
        paths.RSI = self.root / "rsi"
        paths.RSI_STATE = self.root / "rsi" / "state"
        paths.PLAYBOOKS = self.root / "playbooks"
        paths.EVIDENCE = self.root / "evidence"
        self.repo = self.root / "llama"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "t")
        src = self.repo / "ggml/src/ggml-cuda/foo.cu"
        src.parent.mkdir(parents=True)
        src.write_text("static void foo() {}\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        src.write_text(cand_src or ('static bool foo_on() { return getenv("%s") == nullptr; }\n'
                                    'static void foo() {}\n' % SWITCH))
        for rel, text in (extra_files or {}).items():
            f = self.repo / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "cand: foo behind " + SWITCH)
        self.cand = git(self.repo, "rev-parse", "HEAD")
        self.base_build = self.build("base", b"")
        self.cand_build = self.build("cand", SWITCH.encode())
        self.model = self.root / "model.gguf"
        self.model.write_bytes(b"GGUF fake model")
        self.ledger_path = self.root / "ledger.jsonl"
        self.ledger = Ledger(self.ledger_path)
        files = hashing.hash_harness()
        self.ledger.append({"kind": "harness-lock", "tree_sha256": hashing.tree_sha(files), "files": files,
                            "reason": "test"})
        self.card_path = self.root / "card.json"

    def build(self, name, switch_bytes):
        b = self.root / name
        (b / "bin").mkdir(parents=True)
        (b / "lib").mkdir()
        for tool in ("llama-server", "llama-bench", "test-backend-ops", "llama-perplexity"):
            f = b / "bin" / tool
            if tool == "llama-server":
                f.write_text(f'#!/bin/sh\n# {name}\nexec python3 {FAKE_SERVER} "$@"\n')
            else:
                f.write_text(f"#!/bin/sh\necho {name} {tool}\n")
            f.chmod(0o755)
        (b / "lib" / "libggml-hip.so.0.26.0").write_bytes(b"\x7fELF hip " + switch_bytes + b" " + name.encode())
        commit = (self.cand if name == "cand" else self.base)[:9].encode()
        (b / "lib" / "libllama-common.so.0.6.0").write_bytes(b"\x7fELF common build " + commit)
        os.symlink("libggml-hip.so.0.26.0", b / "lib" / "libggml-hip.so")
        return b

    def make_card(self, register=True, **over) -> dict:
        over.setdefault("ops", ["MUL_MAT"])  # H5: a kernel change declares its test-backend-ops smoke
        c = card_mod.template("2026-10-17-test-claim", "agent:test", "2026-10-17T10:00:00+0000")
        c.update({
            "hypothesis": "foo behind the switch saves about half a percent of ms per step",
            "mechanism": "test", "profile": "qwen-mtp", "metric": "ms_step",
            "expected": {"effect_pct": 0.5}, "kill": {"effect_pct_below": 0.1},
            "correctness_class": "BIT", "switch": {"name": SWITCH, "on": "1", "off": "0"},
            "probe": {"kind": "log", "env": {"GGML_HIP_PM4_DEBUG": "1"}, "regex": "foo_on"},
            "attacked": {"kernels": ["foo"], "share_ms": 1.0, "source": {"tool": "pm4trace", "env": {}}},
            "repo": str(self.repo), "commits": {"base": self.base, "cand": self.cand},
            "touched_paths": ["ggml/src/ggml-cuda/foo.cu"],
            "builds": {"base": {"dir": str(self.base_build), "sha256": hashing.hash_build(self.base_build)},
                       "cand": {"dir": str(self.cand_build), "sha256": hashing.hash_build(self.cand_build)}},
            "model_sha256": hashing.sha256_file(self.model),
        })
        for k, v in over.items():
            c[k] = v
        self.card_path.write_text(json.dumps(c, indent=1))
        if register:
            self.ledger.append({"kind": "register", "claim_id": c["id"], "claim_sha256": card_mod.card_sha(c),
                                "card": c})
        return c

    def close(self):
        paths.RUNS, paths.CACHE, paths.RSI, paths.RSI_STATE, paths.PLAYBOOKS, paths.EVIDENCE = self._saved
        for f in self.root.rglob("*"):  # evidence payloads are 0444
            if f.is_dir():
                f.chmod(0o755)
        self.tmp.cleanup()
