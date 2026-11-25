# klab — kernel lab (Qwen3.8-27B decode, RX 7900 XTX / gfx1100)

Live copy: `~/qwen-opt/klab/klab.py` (mirrored here as `klab.py`). Python: `~/qwen-opt/.venv/bin/python` (needs gguf-py
from `~/wt/topka`). All GPU work goes through `~/qwen-opt/queue/run-jobs.sh`; klab only writes a jobs file into
`~/qwen-opt/klab/jobs/` and starts the queue runner in the background (it waits for the GPU + quiet locks).

| step | command | GPU | output |
|---|---|---|---|
| 1 trace | `klab trace TAG [--bin ~/llama-topka]` | queue, PM4=0, rocprofv3 kernel trace, 1 mvs request | `klab/traces/TAG/off/` |
| 2 profile | `klab profile DIR [--by kernel\|class\|type] [--md]` | no | lost-ms table |
| 3 ISA | `klab isa LIB_OR_BENCH --kernel RE [--out F]` | no | ins / vmem / dot / valu / waitcnt / VGPR / occupancy / LDS / scratch |
| 4 ISA diff | `klab isadiff A B --kernel RE [--full]` | no | stat deltas + normalized unified diff |
| 5 micro-bench | `klab bench VAR -- -DFLAG=V ...` | queue, PM4=0 | `klab/logs/bench-VAR.log` |
| 6 sweep | `klab sweep NAME -- "-DA=1" "-DA=2 -DB=1" ...` then `klab sweep-report NAME` | queue, PM4=0 | one log per flag set |
| 7 gate | `klab gate TAG BIN [ARM_ENV...]` | queue, PM4=1 WA=2 GUARD=1 SVM=0 | `/tmp/p100-gate/TAG.PASS` (md5 Qwen c4708318/6f14e814, LFM 894e56e4) |
| 8 hand-off (K-021 PoC-A) | `klab handoff-build`, then queue `~/qwen-opt/queue/k021.jobs` | queue, PM4=0 (no PM4 ring) | `~/qwen-opt/k021/logs/{smoke,measure}.log`, line `VERDICT K-021 PoC-A` |

## profile model
* Step segmentation: the timed request is the trace segment after the last ≥1 s idle gap; per-step numbers = segment
  totals / `client.jsonl` steps.
* Bytes: every `mul_mat_vec_q<type, ncols, fused>` launch gets rows = grid blocks × rows-per-block, snapped to a row
  count of the model's 2-D weights (gguf); fused gate|up = 2×17408 rows, GDN fused qkv+gate = 16384 rows, draft head
  65536 rows. Rows 5120 (ffn_down 17408 cols vs ssm_out/attn_output 6144 cols) use the per-type mean of the gguf.
  Bits/weight: Q8_0 8.5, Q4_K 4.5, Q5_K 5.5, Q6_K 6.5625, IQ4_XS 4.25, IQ4_NL 4.5, Q3_K/IQ3_S 3.4375. Activations
  are ignored (≤0.1 % of the traffic). Label = estimate; `MB/st` × steps ≈ model size + draft.
* lost ms = measured − bytes / `--bw` (926 GB/s = measured peak copy BW of the card at stock). Kernels with no byte
  model (norms, GDN, FA, …) count fully as lost. Idle (GPU gaps) is printed separately.

## micro-bench
`bench` reuses `~/qwen-opt/mmvqbig/bench.hip` (cache-cold: copies > 96 MB Infinity Cache, ABAB rounds, hipEvent):
base = `~/wt/topka` mmvq kernel section, variant = `KLAB_VAR_TREE` (default the same tree) with the `-D` flags
prepended to the variant's kernel text only. Columns: base_us var_us GB/s_b GB/s_v delta bitexact. A flag that changes
the reduction order is not bitexact → needs the md5/KLD gate before adoption.

## hand-off (K-021 PoC-A)
`klab/handoff/handoff.hip` (standalone, plain HIP): chain of Q5_K-shaped n=5 MMVQ stages (r5120/r1024 × c5120) with an
all-to-all dependency and a redundant per-column "norm", int `v_dot4` (bit-exact by construction). Arms: one kernel per
stage (stream, HIP graph; G = 96/192/rows÷8), persistent grid without sync (`O`, lower bound), persistent hand-off
with one counter (`H1`) or ticket relay into 16 flag lines (`H16`), weights of 0/1/2 rows per wave in VGPRs before the
wait (`pP`), empty-kernel graph (`E`). µs/stage = (T(200) − T(40)) / 160, 31 interleaved trials, median. Every timed
run of a checked arm starts from zeroed outputs and is compared bytewise with the CPU-validated reference. Spins are
bounded (error word + abort flag), host watchdog `_exit(3)`. Verdict: handoff = H − O; kill if > 0.3 µs or if less
than 30 % of the "no boundary" gain stays (vs the HIP boundary, and vs a PM4 estimate = 0.46 µs + tail/ramp).

## ISA
`.hip_fatbin` is split into its per-TU offload bundles (`__CLANG_OFFLOAD_BUNDLE__`/`CCOB`), each unbundled for
`hipv4-amdgcn-amd-amdhsa--gfx1100`, disassembled with ROCm llvm-objdump, metadata from `llvm-readelf --notes`.
Occupancy = waves/SIMD from VGPRs (wave32, 1536 VGPRs, granule 24, max 16). ~40 s for libggml-hip.

See `PLAYBOOK.md` for the end-to-end procedure and report 47 (`product/research/47-kernel-lab.md`).
