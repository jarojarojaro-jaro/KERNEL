# GDN fast kernel, bit-identical by construction (worktree ~/wt/gdn6, branch opt-gdn6)

Both commits are UNMEASURED: I had no GPU access. Every claim below comes from offline compilation and the symbolic
emulation of the compiled ISA.

## Commits (on c36fd2c87)
- `b4e819237` HIP/RDNA GDN: separate fast kernel `gated_delta_net_fast_cuda<128, l2_qk, lag_t>`.
  - Covers the scalar gate without snapshots: Qwen3.8 plain decode and the GATED_DELTA_NET_LAG verify/replay.
  - Uses DPP segment sums.
  - Token t+1's loads, l2 norm and kv are done after token t's update, so the kv and attn chains and their
    butterflies overlap.
  - The last token is peeled and two row buffers ping-pong.
  - `GGML_HIP_GDN_FAST=0` selects the plain kernel.
- `0d89ce56c` fast kernel: the state moves as 16-byte pieces of the warp's 4 columns through 8.5 KB of LDS
  (4 b128 loads and 4 b128 stores per lane).
  - `GGML_HIP_GDN_B128=0` selects the unstaged fast kernel.
  - Staging is only used when the state rows are 16-byte aligned; this is checked at launch.

The plain kernel source is byte-for-byte untouched:
- `git diff c36fd2c87 HEAD`: 379 insertions, 0 deletions.
- Lines 1-312 have the same md5 (`fbd9257c…`) in both versions.
- The `gated_delta_net_l2_qk` kernel and all host logic outside the new `#if GGML_USE_HIP` dispatch block are also
  unchanged.

## Plain kernel ISA is identical
`isadiff.py ~/wt/qwen5-tools/gdn_base.s fast3.s`: **44 base kernels, 44 identical (code + descriptor + metadata)**.
- 8 new kernels are added.
- The script only normalises the module function index in local labels (`.LBBn_`, `.Lfunc_endn`) and comments,
  because the column of a comment shifts with the label width.
- `base.s`, freshly compiled from this worktree at c36fd2c87, matches `gdn_base.s` except for the `__hip_cuid` symbol.

## How the op sequence was pinned (from the ISA, not the C source)
I wrote a symbolic gfx11 wave32 emulator: `~/wt/gdn6-isa/gdnemu.py` with driver `gdncmp.py`.
- **What it executes.** One wave of the compiled `.s` from `isa.sh`.
  - Integer state is concrete: addresses, loop counters, masks, exec, SALU, VALU int ops, `ds_bpermute`, DPP
    `row_xmask`, LDS, `global_load`/`store` b32/b128, VOPD with read-before-write.
  - Every float loaded from memory or taken from a float kernarg is a symbolic leaf.
  - Every float instruction builds a hash-consed DAG node, so equal node means the same IEEE ops on the same operands
    in the same dependency structure.
  - It asserts that every DPP instruction runs with all 32 lanes active, so no source lane is ever disabled.
- **Canonicalisation.** Only IEEE-exact identities are applied:
  - a·b = b·a, a+b = b+a;
  - fma multiplicands commute;
  - a−b = a+(−b);
  - signs move between the operands of a product;
  - −−x = x.
- **Limits of that canonicalisation.**
  - Commuting can only change which NaN payload is returned when both inputs are NaN.
  - LLVM treats fadd/fmul as commutative anyway, so the base kernel's operand order is not pinned by its source
    either.
  - The DPP form is `v_add_f32_dpp dst, partner, self`. The base form is `v_add self, partner`. The partner lanes are
    the same.
- **Validated numerically.** `--numeric` evaluates the base DAGs on random inputs and compares them with a float64
  recurrence: max rel. err 1e-7…1e-4 on every output, and no extra writes. This checks the emulator's addressing and
  op semantics.
- **Validated with negative controls.** Three perturbed builds are flagged DIFF:
  - `s = fma(k, delta, g*s)` instead of `fma(g, s, k*delta)`;
  - sum of squares starting with x0² instead of x1²;
  - butterfly order xor 1/2/4 instead of 4/2/1.

The op sequence read off the base ISA, per lane (r = row slot 0..15 of the lane, i = 8r + lane_in_col):
- `sq = x1*x1; sq = fma(x0,x0,sq); sq = fma(xr,xr,sq)` for r = 2..15. This holds for k and for q.
- Segment sum: `t = t + t[lane^4]; t = t + t[lane^2]; t = t + t[lane^1]`.
- `rs = rsqrt_expansion(fma(1/128, sum, l2_eps))`, then `x = l2_scale * (rs * x)`.
- `kv = fma(s0,k0,0); kv = fma(sr,kr,kv)` for r = 1..15, then the segment sum.
- `g = expf_expansion(g_raw)`, then `delta = beta * fma(-g, kv, v)`.
- `s_r = fma(g, s_r, k_r*delta)`. The product k·delta is rounded and g·s is fused.
- `attn = fma(s0,q0,0)` followed by the same fma chain, then the segment sum, then `out = scale * attn`.
- The lagged replay rows use the same kv, delta and s expressions with pending-row k, v, g and beta.

The fast kernel spells every one of these out: `#pragma clang fp contract(off)`, `__builtin_fmaf`, and the same
xor 4/2/1 order through `warp_reduce_sum_dpp<8>`. The expf/rsqrtf expansions come out identical.

## Results (`cmpall.sh base.s fast3.s`, staged and unstaged)
All four variants `<128, l2_qk ∈ {0,1}, lag ∈ {0,1}>` report **ALL IDENTICAL** for every written word of `dst`,
`state` and the pending rows.
- 15 launches per non-lag variant and 29 per lag variant.
- T = 1..5; n_pend = 0..4.
- Both K ≥ T (state written after the replay) and K < T (state written mid-loop).
- With and without the state gather.
- Several (h, z, threadIdx.y) positions, blockDim.y = 2 and 4, and 2 sequences.
- Every ping-pong path (single, pair, loop + both tails) is covered for both the token loop and the replay loop.

Executed float ops per wave are identical (dyncount.py; fma / mul / add, adds include the segment sums):

| case | base | fast | fast + b128 |
|---|---|---|---|
| plain decode T=1 (l2) | 83 / 89 / 14 | 83 / 89 / 14 | 83 / 89 / 14 |
| lag+l2 T=5, n_pend=5 | 590 / 535 / 95 | 590 / 535 / 95 | 590 / 535 / 95 |
| lag+l2 T=9, n_pend=5 | 922 / 891 / 151 | 922 / 891 / 151 | 922 / 891 / 151 |

Per-output DAG cones are the same node in base and fast. For example, attn of the last column at T=1 (l2) is
629 fma / 663 mul / 30 add in both.

## Instruction counts, VGPRs, occupancy
Executed per wave (emulator):

| case | metric | base | fast | fast+b128 |
|---|---|---|---|---|
| decode T=1 (l2) | total instructions (excluding hints) | 476 | 423 | 461 |
| | VALU issue | 230 | 195 | 231 |
| | ds_bpermute | 12 | 0 | 0 |
| | global load b32 | 51 | 49 | 33 + 4 b128 |
| | global store b32 | 17 | 17 | 1 + 4 b128 |
| verify lag+l2 T=5, n_pend=5 | total | 2782 | 2581 | 2606 |
| | VALU issue | 1508 | 1287 | 1321 |
| | ds_bpermute | 75 | 0 | 0 |
| verify lag+l2 T=9, n_pend=5 | total | 4178 | 3867 | 3884 |
| | VALU issue | 2292 | 2019 | 2043 |
| | ds_bpermute | 123 | 0 | 0 |

The gain comes mostly from latency, not instruction count:
- no LDS round trips in the 3 reductions per chain (9 per token);
- the kv(t+1) and attn(t) chains and butterflies are interleaved;
- token t+1's loads are in flight during token t's update.

The VALU count is at the arithmetic floor. In the fast kernel about 1/3 of it is the in-kernel l2 norm, which every
warp of a head repeats.

| kernel <128, l2, lag> | base VGPR / occ | fast | fast + b128 (LDS 8704 B) |
|---|---|---|---|
| l2 + lag (MTP verify) | 84 / 16 | 122 / 10 | 123 / 10 |
| lag (prompt with lag) | 82 / 16 | 120 / 12 | 121 / 10 |
| l2 (plain decode) | 69 / 16 | 106 / 12 | 111 / 12 |
| neither (prompt) | 78 / 16 | 114 / 12 | 119 / 12 |

- No scratch and no spills anywhere; all kernels are at or under 128 VGPRs.
- Qwen3.8 has H = 48 heads at S_v = 128 (gguf `ssm.time_step_rank` 48). That gives 48 × 8 CTAs × 4 waves = 1536
  waves, about 8 per SIMD, which is under the occupancy limit of 10.
- One fix was needed on the way: the staged kernels first came out at 131/130 VGPRs with 80 B of scratch. HIP
  `float4` copies left `tmp[]` in scratch, so I switched to an `ext_vector_type(4)`. I also took the mid-loop lagged
  state write off the staging path.

## Build
`~/wt/gdn6/build` is configured with the qwen5 cmake flags (GGML_HIP=ON, GPU_TARGETS=gfx1100, Release, …). It built
completely (`cmake --build -j4`) and is installed to `~/wt/gdn6/inst`.
- `~/wt/gdn6-isa/logits_dump` is `~/wt/gdn-tools/logits_dump.cpp` rebuilt against this tree. It does a 200-token
  prefill, 6-token verifies with rollbacks, and single-token decodes, and writes raw logits.
- Offline tools are in `~/wt/gdn6-isa`: `gdnemu.py`, `gdncmp.py`, `cmpall.sh`, `isadiff.py`, `dyncount.py`,
  `fn.sh`, and `base.s` / `fast3.s`.

## Pending GPU commands (none run)
Run every block from a shell where `pgrep -f "llama-server.*--port 8080"` prints nothing. Each block starts with that
check.

```bash
# P1 backend tests (tolerance vs CPU): fast, fast without b128, plain
cd ~/wt/gdn6 && ! pgrep -f "llama-server.*--port 8080" && for e in "GGML_HIP_GDN_FAST=1" "GGML_HIP_GDN_FAST=1 GGML_HIP_GDN_B128=0" "GGML_HIP_GDN_FAST=0"; do echo "== $e"; env $e LD_LIBRARY_PATH=$HOME/wt/gdn6/inst/lib:/opt/rocm/core-10.0/lib flock /tmp/gpu.lock flock /tmp/quiet.lock inst/bin/test-backend-ops -o GATED_DELTA_NET,GATED_DELTA_NET_PROLOGUE,GATED_DELTA_NET_CACHE_FUSION,GATED_DELTA_NET_LAG 2>&1 | tail -4; done

# P2 bitwise logits A/B (all 4 GDN variants: n_rs=0 plain + prefill, n_rs=5 lag replay/verify); md5 must agree within each n_rs
cd ~/wt/gdn6-isa && ! pgrep -f "llama-server.*--port 8080" && for nrs in 0 5; do for e in "GGML_HIP_GDN_FAST=0" "GGML_HIP_GDN_FAST=1" "GGML_HIP_GDN_FAST=1 GGML_HIP_GDN_B128=0"; do env $e LD_LIBRARY_PATH=$HOME/wt/gdn6/inst/lib:/opt/rocm/core-10.0/lib flock /tmp/gpu.lock flock /tmp/quiet.lock ./logits_dump $HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf /tmp/gdn6_logits_${nrs}_$(echo $e | tr ' =' '__').bin $nrs 2>/dev/null; done; md5sum /tmp/gdn6_logits_${nrs}_*.bin; done

# P3 greedy md5 vs baselines: plain c4708318411479c9530911e310f865bd, mtp 6f14e814bb6408aeea23a1dc50e96ba1 (fresh servers)
! pgrep -f "llama-server.*--port 8080" && flock /tmp/gpu.lock flock /tmp/quiet.lock env PORT=18441 ~/qwen-opt/fusion/greedy.sh ~/wt/gdn6/inst/bin ~/wt/gdn6/inst/lib /tmp/gdn6g_fast qwen
! pgrep -f "llama-server.*--port 8080" && flock /tmp/gpu.lock flock /tmp/quiet.lock env PORT=18442 GGML_HIP_GDN_B128=0 ~/qwen-opt/fusion/greedy.sh ~/wt/gdn6/inst/bin ~/wt/gdn6/inst/lib /tmp/gdn6g_nob128 qwen
! pgrep -f "llama-server.*--port 8080" && flock /tmp/gpu.lock flock /tmp/quiet.lock env PORT=18443 GGML_HIP_GDN_FAST=0 ~/qwen-opt/fusion/greedy.sh ~/wt/gdn6/inst/bin ~/wt/gdn6/inst/lib /tmp/gdn6g_plain qwen

# P4 GDN kernel time (rocprofv3, PM4 replay off so kernels are traced): gated_delta_net_* rows of *kernel_stats.csv
cd ~/wt/gdn6-isa && ! pgrep -f "llama-server.*--port 8080" && for e in "GGML_HIP_GDN_FAST=0" "GGML_HIP_GDN_FAST=1" "GGML_HIP_GDN_FAST=1 GGML_HIP_GDN_B128=0"; do d=/tmp/gdn6_prof_$(echo $e | tr ' =' '__'); rm -rf $d; env $e GGML_HIP_PM4=0 LD_LIBRARY_PATH=$HOME/wt/gdn6/inst/lib:/opt/rocm/core-10.0/lib flock /tmp/gpu.lock flock /tmp/quiet.lock /opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --stats --output-format csv -d $d -o run -- ./logits_dump $HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf /tmp/gdn6_prof.bin 5 2>/dev/null; echo "== $e"; grep -h gated_delta_net $(find $d -name '*kernel_stats.csv'); done

# P5 llama-bench A/B, interleaved (tg128 = plain-decode kernel, pp512 = prompt kernel)
cd ~/wt/gdn6 && ! pgrep -f "llama-server.*--port 8080" && for r in 1 2 3; do for e in "GGML_HIP_GDN_FAST=1" "GGML_HIP_GDN_FAST=0" "GGML_HIP_GDN_FAST=1 GGML_HIP_GDN_B128=0"; do echo "== round $r $e"; env $e LD_LIBRARY_PATH=$HOME/wt/gdn6/inst/lib:/opt/rocm/core-10.0/lib flock /tmp/gpu.lock flock /tmp/quiet.lock inst/bin/llama-bench -m $HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 512 -n 128 -r 5 -o md 2>/dev/null | tail -2; done; done

# P6 MTP end-to-end (verify = lag+l2 kernel), interleaved env on/off, 3 seeds
cd ~/qwen-opt && ! pgrep -f "llama-server.*--port 8080" && SEEDS=1,2,3 PORT=18445 RUN_ARGS="qwen mtp" ROCM_DIR=$HOME/wt/gdn6/inst flock /tmp/gpu.lock flock /tmp/quiet.lock ./spec_sweep.sh "GGML_HIP_GDN_FAST=1 LABEL=gdn6_fast" "GGML_HIP_GDN_FAST=0 LABEL=gdn6_plain" "GGML_HIP_GDN_FAST=1 GGML_HIP_GDN_B128=0 LABEL=gdn6_nob128" "GGML_HIP_GDN_FAST=1 LABEL=gdn6_fast" "GGML_HIP_GDN_FAST=0 LABEL=gdn6_plain" "GGML_HIP_GDN_FAST=1 GGML_HIP_GDN_B128=0 LABEL=gdn6_nob128"
```

What to expect:
- P2 and P3 must match the baselines and each other bit for bit.
- If P2 differs for `GGML_HIP_GDN_FAST=1` only, the emulation missed a hardware semantic. Candidates: DPP or VOPD
  behaviour, or the in-order guarantee of same-wave LDS accesses (b128 only).
- P4 is the direct GDN number. The round-5 notes put GDN at about 638 µs per verify over 48 layers, which is about 2%
  of a step, so end-to-end gains in P5/P6 will be small and can sit inside the noise.
- If b128 does not win in P4, it can stay off with `GGML_HIP_GDN_B128=0`, or commit `0d89ce56c` can be dropped.

## GPU results (2026-10-15, MEASURED)
- P1 test-backend-ops GATED_DELTA_NET*: 67/67 pass for fast, fast without b128, plain.
- P2 logits (logits_dump, n_rs 0 and 5): md5 identical across all 3 modes (c4040715… / b74b21ce…).
- P3 greedy md5 (fresh servers): fast, nob128 and plain all = plain c4708318… and MTP 6f14e814… (baselines).
- P4 rocprofv3 (PM4 off, logits_dump n_rs=5), avg per call: decode/verify kernel 14.49 -> 14.27 us (-1.5%; nob128 14.73),
  prompt kernel 153.7 -> 132.1 us (-14%; nob128 136.1). 48 layers -> ~10 us per decode step (~0.04% of a 28 ms MTP step).
- P5 llama-bench Qwen, 2 interleaved rounds: tg128 43.46/43.38 vs 43.40/43.31 (+0.15%), pp512 1051/1044 vs 1043/1037 (+0.7%, sd ±120).
- Verdict: bitwise confirmed on hardware, gain inside noise end to end. NOT merged into amd-opt (379 lines for ~0.1%);
  branch kept for a future GDN-heavy workload (long prefill of hybrid models).
