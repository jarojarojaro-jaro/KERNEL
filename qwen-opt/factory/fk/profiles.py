"""Measurement profiles: server flags, workload protocol, roofline bytes. Harness-owned (T1 in 15f §5.4): the
implementer picks a profile by name in the claim card, never flags, prompts, token counts, seeds or rounds.

Server flags follow run-llm.sh (production, 2026-10-16); greedy flags are those of fusion/greedy.sh (md5 baselines
Qwen plain c4708318, MTP 6f14e814, LFM 894e56e4 on f61994f58).
"""
from __future__ import annotations

from . import paths

M = paths.MODELS
DRAFT_VOCAB = f"{M}/draft/draft_vocab_qwen38.txt"


def _mtp(kv):
    return ["--spec-type", "draft-mtp", "--spec-draft-n-max", "4", "--spec-draft-vocab", DRAFT_VOCAB,
            "--spec-draft-vocab-n", "65536", "--spec-draft-head-type", "iq4_xs", "--spec-mtp-type", "iq4_xs",
            "-ctkd", kv, "-ctvd", kv]


# protocol of one measurement request (same body as spec_sweep.py): fixed for every run of every arm
PROTOCOL = {"tokens": 400, "temps": [1.0], "seeds": [1, 2], "cache_prompt": False, "warmup": "Hi"}

PROFILES = {
    "qwen-mtp": {
        "model": "qwen", "gguf": f"{M}/Qwen3.8-27B-UD-Q4_K_XL.gguf", "kv": "q4_0", "ctx": 204800,
        "server_args": ["--jinja", "--cache-ram", "16384", "--reasoning-effort", "low"] + _mtp("q4_0"),
        "greedy_model": "qwen", "greedy_modes": ["plain", "mtp"],
        "md5_baseline": {"plain": "c4708318", "mtp": "6f14e814"},
        # active bytes per forward pass: 17.55 GB file - 0.715 GB token_embd (get_rows), 15a-monokernel.md:154
        "bytes_per_pass": 16.83e9, "spec": True,
        "bench": {"kv": "q4_0"}, "kld": None,
    },
    "qwen-plain": {
        "model": "qwen", "gguf": f"{M}/Qwen3.8-27B-UD-Q4_K_XL.gguf", "kv": "q4_0", "ctx": 204800,
        "server_args": ["--jinja", "--cache-ram", "16384", "--reasoning-effort", "low"],
        "greedy_model": "qwen", "greedy_modes": ["plain"],
        "md5_baseline": {"plain": "c4708318"},
        "bytes_per_pass": 16.83e9, "spec": False,
        "bench": {"kv": "q4_0"}, "kld": None,
    },
    "lfm": {
        "model": "lfm", "gguf": f"{M}/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf", "kv": "q8_0", "ctx": 131072,
        "server_args": ["--jinja", "--cache-ram", "16384"],
        "greedy_model": "lfm", "greedy_modes": ["plain"],
        "md5_baseline": {"plain": "894e56e4"},
        # active weights per token from the GGUF header, 15a-monokernel.md:121
        "bytes_per_pass": 1.777e9, "spec": False,
        "bench": {"kv": "q8_0"},
        # the KLD gate of tools/kld_canary.sh (LFM, wikitext-2, 3 x 16k, ub 1, f16-KV reference)
        "kld": {"ref": f"{paths.HOME}/wt/lfm3-prof/ref.kld",
                "text": f"{paths.HOME}/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw", "ctx": 16384, "chunks": 3},
    },
}

SERVER_ENV = {"LLAMA_SERVER_REASONING_CONTROL": "0"}  # as run-llm.sh


def server_argv(profile: dict, bin_dir: str, port: int) -> list[str]:
    p = profile
    return [f"{bin_dir}/llama-server", "-m", p["gguf"], "-ngl", "999", "-fa", "on", "-ctk", p["kv"], "-ctv", p["kv"],
            "-c", str(p["ctx"]), "-np", "1", "--host", "127.0.0.1", "--port", str(port), "--no-webui",
            *p["server_args"]]


def bench_argv(profile: dict, bin_dir: str, metric: str) -> list[str]:
    pn = ["-p", "4096", "-n", "0"] if metric == "pp_tps" else ["-p", "0", "-n", "128"]
    kv = profile["bench"]["kv"]
    return [f"{bin_dir}/llama-bench", "-m", profile["gguf"], "-ngl", "99", "-fa", "1", "-ctk", kv, "-ctv", kv,
            *pn, "-r", "3", "-o", "jsonl"]


def perplexity_argv(profile: dict, bin_dir: str) -> list[str]:
    k = profile["kld"]
    return [f"{bin_dir}/llama-perplexity", "-m", profile["gguf"], "-f", k["text"], "-ngl", "99", "-fa", "on",
            "-c", str(k["ctx"]), "-b", str(k["ctx"]), "-ub", "1", "--chunks", str(k["chunks"]),
            "-ctk", profile["kv"], "-ctv", profile["kv"], "--kl-divergence-base", k["ref"], "--kl-divergence"]


def greedy_argv(profile: dict, bin_dir: str, port: int, mode: str) -> list[str]:
    """The server command line of fusion/greedy.sh for one mode (near-tie runs must see the md5 runs' tokens)."""
    extra = [] if mode == "plain" else ["--spec-type", "draft-mtp", "--spec-draft-n-max", "4", "--spec-draft-vocab",
                                        DRAFT_VOCAB, "--spec-draft-vocab-n", "65536"]
    return [f"{bin_dir}/llama-server", "--port", str(port), "--host", "127.0.0.1", "-np", "1", "--no-webui",
            "-m", profile["gguf"], "-ngl", "999", "-fa", "on", "-ctk", profile["kv"], "-ctv", profile["kv"],
            "-c", "8192", *extra]
