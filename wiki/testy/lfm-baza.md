---
typ: test
tags: [testy, lfm, baza]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:333-341
status: aktualne
model: lfm2-5-24b-a2b
karta: rx-7900-xtx
wyniki:
  - lfm2-5-24b-a2b | rx-7900-xtx | 173 t/s | czat T=1; Q5_K_M, KV q4_0, bez MTP | 2026-10-14
  - lfm2-5-24b-a2b | rx-7900-xtx | 198.3 t/s | tg128; fork (upstream 169.3) | 2026-10-14
  - lfm2-5-24b-a2b | rx-7900-xtx | 6180 t/s | pp4096; fork | 2026-10-14
---
# 2026-10-14: LFM2.5-24B-A2B — pomiar bazowy

**Pierwszy pomiar LFM2.5 na naszym forku: 173 t/s w czacie, a łatki z kampanii Qwena same dały +17% względem upstreamu (tg128 169.3 → 198.3).**

Warunki: Q5_K_M, ctx 131072, KV q4_0, bez MTP (17.8 GB VRAM); czat 6 promptów × 3 seedy, T=1.
- Czat: 173 t/s równo na wszystkich typach tekstu (5.78 ms/token).
- llama-bench: tg128 198 t/s, pp4096 6124 t/s. Serwer: prefill 2768 (1.7k), 5805 (6.7k), 5172 (29.7k), 3709 (95k) t/s; decode 174 / 172 / 168 / 153 t/s.
- Upstream e60eff95f vs fork (2 przeplatane rundy, `-fa 1`, KV q4_0): tg128 169.3 → 198.3 (+17%), pp4096 6107 → 6180 (+1%).
- Profil rocprofv3 (tg, fork): ~721 kerneli/token, mul_mat_vec_q 71% (2.69 ms, ~680 GB/s), rms_norm 5%, quantize_q8_1 3.7%, bin_bcast 3.5%, topk_moe 3.5%, router F32 2.5%; przerwy ~3.1 µs mediana; bez profilera 5.05 ms/token ≈ 3.8 ms pracy + 1.3 ms przerw/host.
- Sufit: ~1.8 GB na token → ~1.9 ms (~500 t/s).

Plan z tego pomiaru: szybsze MMVQ ekspertów, fuzje małych opów MoE (router + top-k + ważenie, norma + kwantyzacja), mniej kerneli. Spekulacja ograniczona (weryfikacja k tokenów czyta do 4k różnych ekspertów na warstwę).

## Powiązane
- [[lfm2-5-24b-a2b]]
- [[lfm-runda-1]]
- [[sufit-pasma-i-mapa-czasu]]
- [[klasyfikacja-latek]]
