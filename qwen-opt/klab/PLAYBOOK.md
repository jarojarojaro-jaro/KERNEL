# Kernel optimization playbook (XTX, Qwen3.8-27B decode)

1. **Trace** the installed build: `klab trace TAG`. One mvs request, PM4=0 (profiling rule), ~3 min GPU.
2. **Rank**: `klab profile traces/TAG/off --by type` and `--by kernel`. Work top-down on *lost ms/step*, not on %bw:
   a 46 %-bw kernel with 0.2 ms is worth less than an 82 %-bw one with 0.7 ms. Idle ms belongs to the host-gap work
   (LatencyHunt), not to kernels.
3. **Read the ISA** of the item: `klab isa ~/llama-topka/bin/libggml-hip.so --kernel 'RE' --out x.isa`. Check VGPR →
   occupancy (≤5 waves/SIMD on a BW-bound kernel = suspect), vmem loads per weight byte (wide `global_load_b128` vs
   dword), `s_waitcnt` count, scratch (must be 0).
4. **Hypothesis → knob**: prefer existing `#ifndef` knobs in `mmvq.cu` (`MMVQ_KQ_NI`, `MMVQ_Q6K_NI`,
   `MMVQ_BUFFER_LOADS`, `MMVQ_DPP_REDUCE`, `MMVQ_R3_*`); a new idea gets its own knob with the production default.
5. **Sweep** on the micro-bench: `klab sweep NAME -- "-DK=a" "-DK=b" ...` (always include a no-op flag set as the noise
   floor), `klab sweep-report NAME`. ≤10 min GPU per idea. Keep: var faster than base by more than the no-op spread on the
   shapes that carry the lost ms. `klab isadiff` base vs variant bench to explain the delta.
6. **Port** the winner to a branch of `~/wt/topka` behind a runtime/compile switch, `rbuild --local` plainly.
7. **Gate** (adoption rule: whatever passes is adopted without asking): `klab gate TAG BIN "SWITCH=0" "SWITCH=1"`
   (md5 Qwen c4708318 / MTP 6f14e814 / LFM 894e56e4, switch on == off); not bitexact → KLD gate
   (`tools/kld_gate.py`, k=2, tail 1.25). Then E0 prose ABBA (`xtxroadmap/prose_bench.py`) + mvs, PM4=1 WA=2 GUARD=1.
   First amdgpu fault → branch stopped.
8. **Hand-off**: branch + commit + switch + numbers to `agent://IntegTopka2` (sole integrator).
9. Re-trace after integration; the next item is the new top of the lost-ms table.
