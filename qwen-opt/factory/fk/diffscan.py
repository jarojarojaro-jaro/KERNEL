"""Unified diff parsing and the G0 deny-list: the implementer's diff must not touch what measures it.

Deny-list (llama.cpp side of the diff; the harness side is pinned by HARNESS.lock):
  paths   llama-bench, llama-perplexity (KLD), build-info (binary identity), anything named like our harness
  content server timing fields (t/s, ms, draft counts reported in /v1 timings), weakened test-backend-ops cases
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass, field


@dataclass
class FileDiff:
    path: str
    old_path: str | None = None
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


def parse_unified(text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    cur = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.+?) b/(.+)$", line)
            cur = FileDiff(path=m.group(2) if m else line.split()[-1], old_path=m.group(1) if m else None)
            files.append(cur)
        elif line.startswith("+++ ") or line.startswith("--- "):
            if cur is None:  # plain diff without the git header
                p = line[4:].split("\t")[0]
                if line.startswith("+++ "):
                    cur = FileDiff(path=p[2:] if p.startswith("b/") else p)
                    files.append(cur)
            continue
        elif cur is not None and line.startswith("+"):
            cur.added.append(line[1:])
        elif cur is not None and line.startswith("-"):
            cur.removed.append(line[1:])
    return files


def git_diff(repo: str, base: str, cand: str) -> str:
    r = subprocess.run(["git", "-C", repo, "diff", "--no-color", "-U3", base, cand], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git diff {base} {cand} in {repo}: {r.stderr.strip()}")
    return r.stdout


def git_show(repo: str, rev: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def git_grep(repo: str, rev: str, needle: str) -> bool:
    r = subprocess.run(["git", "-C", repo, "grep", "-q", "-F", needle, rev], capture_output=True)
    return r.returncode == 0


def git_message(repo: str, rev: str) -> str:
    r = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%B", rev], capture_output=True, text=True)
    return r.stdout


PATH_DENY = [
    ("tools/llama-bench/*", "llama-bench mierzy pp/tg"),
    ("tools/perplexity/*", "llama-perplexity liczy KLD"),
    ("common/build-info*", "build_info to tożsamość binarki"),
    ("cmake/build-info*", "build_info to tożsamość binarki"),
    ("*spec_sweep*", "protokół pomiaru spec_sweep"),
    ("factory/*", "weryfikator"),
    ("*/factory/*", "weryfikator"),
    ("*greedy*.sh", "bramka md5"),
    ("*kld_gate*", "bramka KLD"),
    ("*kld_canary*", "bramka KLD"),
    ("*loo.py", "harness LOO"),
    ("cloud/bench.sh", "harness chmurowy"),
    ("*run-llm.sh", "flagi serwera produkcji"),
]
TIMING_RE = re.compile(r"\b(predicted_per_second|predicted_ms|predicted_n|prompt_per_second|prompt_ms|prompt_n|"
                       r"draft_n_accepted|draft_n|t_token_generation|t_prompt_processing|n_decoded|timings)\b")
TEST_WEAKEN_RE = re.compile(r"(test_cases\.emplace_back|make_unique<test_|max_nmse_err|max_maa_err|max_err\b)")


def deny_findings(files: list[FileDiff]) -> list[str]:
    out = []
    for f in files:
        for p in {f.path, f.old_path} - {None}:
            for pat, why in PATH_DENY:
                if fnmatch.fnmatch(p, pat):
                    out.append(f"{p}: ścieżka na denyliście ({why})")
        if f.path.startswith("tools/server/"):
            for line in f.added + f.removed:
                m = TIMING_RE.search(line)
                if m:
                    out.append(f"{f.path}: zmienia pole pomiaru czasu `{m.group(1)}` w serwerze: {line.strip()[:100]}")
                    break
        if f.path.endswith("tests/test-backend-ops.cpp"):
            for line in f.removed:
                if TEST_WEAKEN_RE.search(line):
                    out.append(f"{f.path}: usuwa albo zmienia istniejący test/tolerancję: {line.strip()[:100]}")
                    break
    return out


def touched(files: list[FileDiff]) -> list[str]:
    return sorted({f.path for f in files})


def added_text(files: list[FileDiff]) -> str:
    return "\n".join(l for f in files for l in f.added)
