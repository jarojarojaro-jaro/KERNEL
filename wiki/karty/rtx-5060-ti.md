---
typ: karta
tags: [karty, nvidia, sm-120]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/hardware/rx-7900-xtx.md:36-46,105; ~/KERNEL/product/PLAN.md:287; ~/qwen-opt/cloud/PLAN-TESTOW.md:90,100,132; ~/qwen-opt/cloud/results/5060ti-20261016/ (hw.json, tbo, greedy, lb; 2026-10-16); ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:17,104,305
status: do-sprawdzenia
---
# NVIDIA RTX 5060 Ti 16 GB (lokalnie + wynajem)

**Blackwell sm_120 z 16 GB; druga karta w naszym serwerze (PNY OC) i #3 w Steam — najważniejsza karta NVIDIA dla produktu; jedyna w planie z PDL.**

- Parametry (hardware, „do weryfikacji”): GB206, 16 GB GDDR7 128-bit, ~448 GB/s (~2× wolniej niż XTX w decode), tensor core'y 5. gen. z FP8 i FP4. Na wynajętej instancji: limit mocy 180 W, PCIe 4.0 x8, sterownik 580.173.02.
- Rola lokalnie: referencja CUDA, draft model, dodatkowa pamięć (24 + 16 GB); w systemie na razie brak sterownika NVIDIA.
- Rynek: Steam 4.06% (#3), Vast ~$0.165/h, nowa ~$474–680; pozycja 1 na liście zakupów (PLAN §5.2).
- Kampania 2026-10-16 (Vast): build sm_120 503 s; test-backend-ops 19251/19253 — 2 FAIL w `GATED_DELTA_NET_PROLOGUE` (ERR minimalnie ponad próg 0.0005); greedy `DIFF-BUILD`; tg128 Qwen3.8-27B UD-Q3_K_XL upstream 28.6 / fork 29.0 t/s, LFM2.5 Q4_K_M upstream 196.9 / fork 201.2 t/s.
- PDL na sm_120 wymagał poprawki 3 w `cuda-compat` (0053, 0057).

## Powiązane
- [[karty/_hub|Karty]]
- [[nvidia-wyniki-2026-10-16]]
- [[sm-86-89-120]]
- [[cuda-compat]]
- [[rx-7900-xtx]]
