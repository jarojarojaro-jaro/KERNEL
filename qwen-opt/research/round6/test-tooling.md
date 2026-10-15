# tools6: LOO of the 65 patches, KLD gate canaries, Kernel Tuner scaffolding

The tools are in `~/qwen-opt/tools/`, with the README in Polish. Copies are in `~/KERNEL/qwen-opt/tools/`; they are not committed and `kt/build` is not copied.

Nothing ran on the GPU. All validation used `--dry-run`, fake data, the real `llama-perplexity` logs, or offline clang runs for gfx1100.

## Commits
- `~/wt/tools6`, branch `tools6`, commit `4db68c6ab` on top of c36fd2c87.
  - It adds a compile-time hook to `calc_nwarps`: when the macro `MMVQ_TUNE_NWARPS_N1` is defined, it sets the warp count of the RDNA3 one-column kernels.
  - The ggml build never defines that macro, so the code it compiles is unchanged. Only the Kernel Tuner harness defines it.
  - **UNMEASURED.** Not meant for `amd-opt`.
- No production source changes.

## 1. `loo.py`: patch classification
Output files: `loo/loo-plan.{json,md}`. Every env switch was checked to exist as a string literal in non-comment code at HEAD.

| class | count |
|---|---|
| runtime env switch | **27** |
| runtime CLI switch (0004, 0032) | **2** |
| build-time only | **22**: 8 revert cleanly (0022/35/36/37/40/41/42/45; 0037 is inactive at MTP n=4), 14 conflict (`git merge-tree`) |
| non-speed | **14**: Vulkan 5, fixes 3 (0018/23/43), opt-in 2 (0039/46), tests/tooling/refactor/hygiene 4 |

Conflicting reverts get a list of the later patches that touch the conflicting files.
- 0001/02/16/21 conflict on `mmvq.cu`.
- 0033 is covered by `LLAMA_GDN_REPLAY=0`, which also switches off 0034–0036 and 0038.

Runner:
- Trials run interleaved ABBA under the GPU locks, in blocks of at most 5 minutes with 45 s pauses, on port 18440.
- Results are appended to jsonl; finished trials are skipped on resume, and trial durations are learned from earlier runs.
- The report gives the paired 95 % CI (Student t) and flags NEUTRAL or REMOVAL FASTER.
- Checked on fake data: the synthetic neutral patches (n%7) come out NEUTRAL and the faster ones (n%13) come out REMOVAL FASTER.
- A second `run --fake` appends 0 trials, which shows resume works.
- The block executor was tested with stubs.
- `loo-builds.sh` runs in one scratch worktree with incremental builds: ref plus 7 clean reverts, results to `~/wt/loo-bins/NN`.

## 2. KLD canaries
Files: `kld_canary.sh`, `kld_gate.py`, `perturb_gguf.py`, `kld-canary.md`.

Gate rules:
- **PASS** needs ΔKLD ≤ 2σ, Δsame-top ≥ −2σ and 99.9 % KLD ≤ 1.25× the baseline.
- **IDENTICAL** means every number matches.
- **ERROR** means a different reference was used.

Results on the real logs:

| comparison | result |
|---|---|
| kvq vs vec | PASS (+0.01σ) |
| vec2 vs vec1 | IDENTICAL |
| q4 vs vec | FAIL (+26.8σ, −24.8σ, ×1.68) |

Canaries and expected outcomes:
- **PASS / IDENTICAL:**
  - baseline and baseline2 (determinism);
  - `GGML_HIP_KVQ_Q8=0`.
- **FAIL:**
  - KV q4_0, k8v4, k4v8;
  - 3 of 4 experts;
  - one layer's weights ×1.10 (`ffn_down_exps` and `attn_output`);
  - requant to Q3_K_M.
- **PROBE** (sensitivity only):
  - eps ×100;
  - rope +1 % / +5 %;
  - weights ×1.005 / ×1.02;
  - requant to Q4_K_M.

`perturb_gguf.py` passed its self-test on a fake GGUF (`ALL OK`).

Limitation: the 2σ threshold is about 0.005 KLD, so a bug that adds less than that passes. The PROBE canaries measure where that limit is.

## 3. Kernel Tuner (`kt/`)
- The harnesses include the real ggml translation units: `mmvq_kt.hip` (n=1 MMVQ, MoE gate_up+SWIGLU+q8_1, MoE down+reduce) and `gdn_kt.hip`.
- The tuner's C backend gets a g++ stub that dlopens the precompiled variant for each configuration. `libkt_mem.so` shares the device buffers, and weight copies are rotated so each measurement is cache-cold (256 MiB).
- Shapes come from the GGUFs:
  - 39 n=1 MMVQ shapes (Q4_K/Q5_K/Q6_K/Q8_0);
  - MoE: 2 gate_up and 2 down shapes (E 64, 4 used);
  - GDN: 2 shapes, decode and MTP verify with replay (H 48, Hk 16, S_v 128).
- Search space:
  - MMVQ: NWARPS {1,2,4,8} × ROWS {1,2,4};
  - GDN: CPW {1,2,4,8,16} × NUM_WARPS {1,2,4}.
- **Offline compile:** all 53 variants compile for gfx1100 in 1010 s at -j4 (`kt/compile-all.log`).
- **ISA check (`kt.py isacheck`):** at the production configuration, the harness kernels are instruction-for-instruction identical to the production units.
  - n=1 MMVQ Q5_K and gate_up: 383 and 1377 lines.
  - moe_down: n_used 2/4/6/8.
  - GDN lag0 and lag1: 571 and 1045 lines.
- Resource usage per variant (VGPR / occupancy in waves per SIMD):
  - **n=1 Q5_K:** r1 31/16, r2 43/16, r4 58/16 (LDS (nw−1)·rows·128 B).
  - **moe_down Q5_K:** r1 86/16, r2 117/12, r4 176/8.
  - **GDN lag1:**
    - cpw4: 84/16;
    - cpw8: 146/9;
    - cpw16: 256/5 with 80 B/lane of scratch, i.e. spilling, so it should be pruned.
  - **GDN lag0, cpw16:** 211/7.
- **Correctness:**
  - Each configuration is checked against a float64 reference with tolerance 2e-4·(|W|·|y|).
  - The q8_1 copy is checked to fp16 rounding.
  - After tuning, each configuration is also compared bitwise with the production output, and a BUG is flagged if a configuration in the bitwise class is not bitwise.
  - `kt.py fake`: all 45 shapes OK, with the injected error caught.
  - Independent checks: Q8_0 integer dot product (difference 0); GDN per-column recurrence (8.9e-16); lag replay (1.7e-16).
  - A lost quant block is caught in 39–100 % of rows per shape, so it is caught for a shape as a whole.
- **Table:** `kt.py table` writes `kt-table-gfx1100.{json,inc}`.
  - Format: `KT_MMVQ(kernel, type, nrows, ncols, n_used, nwarps, rows, bitwise)` and `KT_GDN(H, Hk, n_tokens, lag, cpw, num_warps, bitwise)`.
  - By default it picks the best configuration that is bitwise equal to production.
  - Checked with `--fake`.

## Pending GPU commands
First check that `pgrep -f "llama-server.*--port 8080"` prints nothing.

```
cd ~/qwen-opt/tools
pgrep -f "llama-server.*--port 8080" || python3 loo.py run --kind env --rounds 2        # flock per block, port 18440
pgrep -f "llama-server.*--port 8080" || python3 loo.py report
loo/loo-builds.sh                                                                         # CPU, flock -s quiet, -j4
pgrep -f "llama-server.*--port 8080" || python3 loo.py run --kind build --rounds 2 && python3 loo.py report
pgrep -f "llama-server.*--port 8080" || ./kld_canary.sh run baseline baseline2 ctl_vec kv_q4 kv_k8v4 kv_k4v8 moe_k3 eps_x100 rope_p1 rope_p5
./kld_canary.sh gate
P=~/qwen-opt/.venv-kt/bin/python; cd ~/qwen-opt/tools/kt
pgrep -f "llama-server.*--port 8080" || flock /tmp/gpu.lock flock /tmp/quiet.lock env KT_GPU_LOCKED=1 $P kt.py tune --kernel gdn
pgrep -f "llama-server.*--port 8080" || flock /tmp/gpu.lock flock /tmp/quiet.lock env KT_GPU_LOCKED=1 $P kt.py tune --kernel moe_down
pgrep -f "llama-server.*--port 8080" || flock /tmp/gpu.lock flock /tmp/quiet.lock env KT_GPU_LOCKED=1 $P kt.py tune --kernel moe_gate_up
for s in $(seq 0 38); do pgrep -f "llama-server.*--port 8080" && break; flock /tmp/gpu.lock flock /tmp/quiet.lock env KT_GPU_LOCKED=1 $P kt.py tune --kernel mmvq_n1 --shape $s; sleep 45; done
$P kt.py table
```

- No llama-server is started by `kt.py` (it needs no port). The `loo.py` and `kld_canary.sh` runs check `pgrep` again before every block.
- Greedy md5 checks are not needed: production code is unchanged.
- [INFERENCE]
  - NSM is 96, which sets the production GDN `num_warps` to 4.
  - GDN q/k/v strides follow the views in `qwen35.cpp`.
  - The pending-row capacity K is `n_rs_seq + 1` = 5.
