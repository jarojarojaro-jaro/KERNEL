---
typ: nvidia
tags: [nvidia, wyniki, chmura]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/results/{3090,5060ti}-20261016/tbo/summary.txt:1-8; ~/qwen-opt/cloud/results/{3090,5060ti}-20261016/lb/*.jsonl (avg_ts tg128, zaokrąglone do 0.1); ~/qwen-opt/cloud/results/{3090,5060ti,3060}-20261016/greedy/ (odczyt 2026-10-16 ok. 02:40 UTC); ~/qwen-opt/cloud/PLAN-TESTOW.md:16,76-84; ~/qwen-opt/cloud/bench.sh:16-18,272-294
status: do-sprawdzenia
---
# Wyniki NVIDIA z chmury (stan 2026-10-16, w toku)

**Pierwsza runda na Vast: fork buduje się i przechodzi testy op na RTX 3090, na RTX 5060 Ti padają 2 testy prologu GDN, a greedy md5 forka różni się od upstreamu na każdym modelu, także z wyłączonymi przełącznikami.**

Stan plików w chwili zapisu (kampanie wciąż trwają):
- **test-backend-ops** (fork): RTX 3090 19253/19253; RTX 5060 Ti 19251/19253, FAIL w `GATED_DELTA_NET_PROLOGUE` (q4_K, n_tokens 6 i 8: ERR 0.000505 i 0.000944 przy progu 0.0005).
- **greedy md5:** werdykt `DIFF-BUILD` dla Qwen3.8-27B (plain i spec) i LFM2.5 na 3090 i 5060 Ti oraz dla Saluki i Bonsai na 3060: fork-safe = fork ≠ base, czyli różnicę robi łatka bez przełącznika. PLAN-TESTOW wymienia takie łatki zmieniające numerykę: 0013, 0043, 0001/0002, 0023, 0018. Gałęzie z dodatkowymi wyłącznikami do bisekcji (`cuda-3090-opt`, `cuda-v070-5060ti`) już powstały.
- **llama-bench tg128** (2 rundy ABCDDCBA, ten sam zestaw flag `-fa on -ctk/-ctv <KV> -ngl 999`; „base” = upstream z tymi flagami, „fork” = fork z tymi flagami, „fork-safe” = fork z 31 przełącznikami = 0):
  - 3090, Qwen3.8-27B UD-Q4_K_XL: base 39.0 / 39.0, fork 39.4 / 39.4, fork-safe 40.2 / 40.2 t/s (upstream z domyślnymi flagami: 39.4 / 39.6);
  - 3090, LFM2.5 Q5_K_M: base 237.5 / 236.3, fork 258.2 / 256.9, fork-safe 245.3 t/s;
  - 5060 Ti, Qwen3.8-27B UD-Q3_K_XL: base 28.6, fork 29.0 / 28.9, fork-safe 29.3 t/s;
  - 5060 Ti, LFM2.5 Q4_K_M: base 196.9 / 196.2, fork 201.2 / 199.4, fork-safe 194.8 / 195.7 t/s.
- **spec_sweep:** brak danych w momencie zapisu (plik pusty na 3090).

Wniosek wstępny: na LFM fuzje forka dają zysk w tg na 3090 (~+9% vs base tuned), na Qwenie zmiany ~±2%. Do potwierdzenia po zakończeniu kampanii.

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[latki-na-nvidia]]
- [[rtx-3090]]
- [[rtx-5060-ti]]
- [[harness-chmurowy]]
