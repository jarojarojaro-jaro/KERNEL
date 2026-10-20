# 38 — GDN checkpoints without the slow host copy (`LLAMA_CKPT_VRAM`)

Branch `ckpt-vram` (llama.cpp, local), commit `2f035f316` on top of topka `b659634fd`. Switch: `LLAMA_CKPT_VRAM=0` (default, previous behaviour), `=1` checkpoint copies in VRAM (pinned fallback), `=2` pinned host staging.
Follows report 35 E2: checkpoint copies were 12–14% of fresh 2k TTFT and 41–81% of agent-turn TTFT.

## Measurements (XTX, Qwen3.8-27B, topka profile PM4=1 WA=2 GUARD=1, queue q38-main 2026-10-20)

Fresh-prompt TTFT, median wall / prompt_ms [ms]; A = off (A1, A2), B = `=1`, C = `=2`, order A1 C1 B1 A2:

| n | A1 | A2 | B (=1) | C (=2) | C vs mean A |
|---|---|---|---|---|---|
| 2048 | 2941/2531 | 2617/2231 | 2144/1959 | 2160/1948 | −22% |
| 8192 | 8735/8238 | 8478/8023 | 7986/7761 | 8060/7813 | −6% |
| 32768 | 34866/34478 | 34499/34163 | 34144/33908 | 34434/34173 | −1% |

Agent replay (prompt_ms, second run): S1-grow 1305/1185 → 780 (B) / 763 (C); S2-turn2 687/579 → 160 / 197; S1-start (cache hit) 626/539 → 344 / 282.
Checkpoint create: 148–174 ms (host) → 15.5 ms (VRAM) / 14.9 ms (pinned). Restore unchanged, 36–46 ms.

VRAM peak (load 23359 MiB): off 23878, `=1` 24199 (**+321 MiB**, 1× low-VRAM warning), `=2` 23913 (+35 MiB).

## Correctness
- test-save-load-state LFM + Qwen: PASS (PM4=0 first contact).
- greedy md5, off and `=2`: Qwen plain c4708318, MTP 6f14e814, LFM 894e56e4 — identical to the references.
- Prompt-cache eviction (`--cache-ram 2048`) + slot save/erase/restore: off == `=2`, md5 eedf9c44 (step by step).

## Decision
Adopt `LLAMA_CKPT_VRAM=2` (pinned): the same gain as `=1` without the VRAM cost/warning. `=1` stays available but is not the default. Adoption handed to IntegTopka (merge `ckpt-vram`, default in `run-topka.sh`, md5 gate on the installed binary).
