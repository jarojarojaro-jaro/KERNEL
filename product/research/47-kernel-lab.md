# 47 — Kernel lab (klab): profil per kernel/typ kwantu, ISA, sweep wariantów, gate

Narzędzie: `qwen-opt/klab/klab.py` (README + PLAYBOOK obok). Na żywo: `~/qwen-opt/klab/`.

## Co jest
* `klab profile` — trasa rocprofv3 → tabela per instancja mmvq (typ, ncols, fused, wiersze) i per kernel non-mmvq:
  ms/step, wywołania/step, MB/step (model bajtów z gguf), GB/s, %bw i **lost ms/step vs 926 GB/s**. `--by type|class`.
* `klab trace` — job kolejki (PM4=0), 1 żądanie mvs na `~/llama-topka`.
* `klab isa` / `isadiff` — rozbiór `.hip_fatbin` na bundle per TU, ISA gfx1100, VGPR/SGPR/LDS/scratch/occupancy,
  mix instrukcji (vmem/dot/valu/waitcnt), diff znormalizowany. ~40 s na libggml-hip.
* `klab bench` / `sweep` / `sweep-report` — mikrobench `mmvqbig/bench.hip` (cache-cold, ABAB, bitexact),
  base = topka, wariant = topka (lub `KLAB_VAR_TREE`) + `-D` tylko w tekście wariantu. Zawsze no-op jako szum.
* `klab gate` — `p100_md5.sh` z PM4=1 WA=2 GUARD=1 SVM=0 (md5 c4708318 / 6f14e814 / LFM 894e56e4).

## Profil topka (trasa `klab/traces/now1/off`, 2026-10-21, 31.24 ms/step, 4.92 tok/step)
Busy 26.89 + idle 4.70 ms/step. Model wag 18.42 GB/step = 19.89 ms @ 926 GB/s. **Lost vs roofline 7.00 ms/step**.

Per typ: Q5_K 1.65 ms (776 GB/s, 84 %), IQ4_XS 0.91 (787), Q4_K 0.65 (738), Q6_K 0.59 (763), IQ4_NL 0.14.
Non-mmvq: GDN 0.72, rms_norm_mul_f32_unrolled 0.67 (152 wywołań/step), FA kvq 0.56, gdn_conv_ab 0.26,
unary_gated_op 0.22, set_rows q4_0 0.18, rms_norm_mul_rope 0.18.

Top instancje: Q5_K n5 fused r5120 (ffn_down/ssm_out/attn_out, 73.6/step) **0.72** @756 GB/s; Q6_K n5 fused r5120
0.29 @715; Q5_K gate|up r34816 0.29 @823; IQ4_XS gate|up 0.25; IQ4_XS fused r5120 0.21; r1024 (k/v) razem ≈0.21
@360–420 GB/s. Draft n1: wszystko ≥ 840 GB/s poza r12288/r1024 (≈0.07 łącznie) — nic do wzięcia
(po poprawce MmvqBig2: n1 fused SWIGLU czyta gate+up).

## ISA (klab isa, libggml-hip topka)
| kernel | ins | vmem | v_dot | VGPR | fale/SIMD |
|---|---|---|---|---|---|
| Q5_K n5 fused | 976 | 35 | 160 | 143 | 10 |
| Q6_K n5 fused | 1137 | 83 | 160 | 251 | 5 |
| Q5_K, `MMVQ_KQ_NI=2` | 819 | 35 | 80 | 121 | 10 |
| Q5_K, `MMVQ_KQ_NI=8` | 1620 | 53 | 320 | 133 | 10 |
| Q6_K, `MMVQ_Q6K_NI=1` | 949 | 83 | 80 | 225 | 6 |
| Q6_K, `MMVQ_Q6K_NI=4` | 1448 | 83 | 320 | 254 | 5 |
`MMVQ_DPP_REDUCE`, `MMVQ_BUFFER_LOADS`: ISA n5 identyczne (nie dotyczą ścieżki n5) → drugi no-op w sweepie.
Wniosek: Q6_K n5 to jedyny mmvq z occupancy 5 (251 VGPR) i ~2.4× więcej vmem niż Q5_K — kandydat dla MMVQ-Q6K.

## End-to-end na top lost-ms (Q5_K/Q6_K n5 fused r5120)
Sweep `ni` (7 wariantów: no-op, KQ_NI 2/8, Q6K_NI 1/4, DPP_REDUCE, BUFFER_LOADS) zbudowany (CPU, 8 min),
ISA potwierdzone powyżej; job `klab/jobs/sweep-ni2.jobs` stoi w kolejce GPU (kolejka zatłoczona: >10 runnerów
mmvq-q4k/q6k/g50b/…) — **wyniki GPU jeszcze niezmierzone**. Po wykonaniu: `klab sweep-report ni`; zwycięzca
(> rozrzut no-op na down/out) → gałąź topka + `klab gate` → IntegTopka2. Niebitexact (zmiana NI zmienia kolejność
sumowania) → KLD gate.

## Poprawki modelu bajtów (z review)
* n1 fused SWIGLU r17408 = gate+up (2 macierze) — było 421 GB/s, jest 841.
* Snap wierszy najpierw do kształtów danego typu (Q8_0 fused dawał 123 % bw).
