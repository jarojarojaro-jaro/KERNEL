---
typ: test
tags: [testy, pm4, awarie, rdna3]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:6-61,104-130,184-193; journalctl -k -b -2/-1/0; ~/qwen-opt/coupled/logs*/; ~/KERNEL/product/research/17-gpu-page-fault.md:216-247; ~/KERNEL/product/research/17-gpu-page-fault.md:1-208; ~/KERNEL/product/research/17-gpu-page-fault.md:210-425
status: do-sprawdzenia
model: qwen3-8-27b
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 103.7 t/s | dekod MTP; GGML_HIP_PM4=0 (PM4 108.8) | 2026-10-19
  - lfm2-5-24b-a2b | rx-7900-xtx | 259.3 t/s | dekod; GGML_HIP_PM4=0 (PM4 293.6) | 2026-10-19
---
# 2026-10-16/19: page faulty GPU i 10 resetów XTX (analiza bez GPU)

**10 resetów w 3 bootach: 2 z jawnych eksperymentów (`pdl` R0 16.10 15:30:52, `GGML_HIP_PM4_UB` 18.10 19:56:24), 8 to ta sama awaria produkcyjnej ścieżki replayu PM4 w `llama-server` Qwen MTP – SQC(data) @0, `STATUS 0x00801431`, `sq_intr type 2` (MEMVIOL) `priv 0`, po ~110–130 ms „MES failed to response msg=3” i mode1 reset.**

| # | czas (UTC) | proces | kontekst |
|---|---|---|---|
| R1 | 16.10 15:30:52 | `pdl` | X1 wariant R0, zawieszony IB (eksperyment) |
| R2 | 16.10 15:35:06 | `llama-server` (lookup) | równolegle `validate.sh` bez blokady GPU |
| R3, R4, R6 | 18.10 19:47, 19:56, 20:14 | `llama-server` (coupled) | tryby 0 / 2 / 1, request 36, 33, 50 |
| R5 | 18.10 19:56:24 | `llama-bench` | `PM4_UB` bez synchronizacji (eksperyment) |
| R7–R10 | 22:42, 22:57, 23:25, 19.10 00:16 | `llama-server` (coupled) | tryby 0 / 0 / 1 / 0, request 74, 53, 77, 158 |

- Fault przychodzi 0.57–3.20 s po starcie requestu, a „tape of 823 dispatches did not complete within 10 s” dopiero ~10 s później – timeout jest skutkiem ([[lekcja-timeout-tasmy-to-skutek]]).
- E-X4: 7 resetów na 2338 requestów (~1/330), 0 w 901 slotach przed zapełnieniem `--cache-ram` 16 GiB, 7 w 1410 później (~1/200).
- Hipotezy: **H1 (~60%)** wywłaszczenie kolejki KFD w środku IB gubi rejestry SH → `USER_DATA` = 0 → wskaźnik kernargów 0 (w bootach widać `restore_userptr_worker` 64×, `svm_range_restore_work` kończące się 156 ms po R9); H2 (~20%) uszkodzenie kernargów w VRAM; H3 (~10%) uszkodzenie IB w RAM; H4 (~10%) inne. Wszystko `[INFERENCE]`.
- Korekty: R9 to tryb 1 i nie wynikał z kolizji blokad ([[lekcja-nie-odtwarzac-lockow]]); alarmy „serwer na 8080” były fałszywe ([[lekcja-pgrep-f-lapie-powloki]]).
- Produkcja zagrożona: `~/llama-opt` ma PM4 domyślnie i te same flagi; reset zabija serwer użytkownika i zeruje krzywą wentylatora. Plan testu i decyzja: [[testy/2026-10-19-page-faulty-gpu-analiza]], [[otwarte-decyzje-techniczne]].

Ciąg dalszy (§9): [[2026-10-19-pm4-priv-analiza]] – kandydat H1′ (PRIV=0 + ewikcja SVM).

## Ze scalonej notatki: Raport 17: page faulty GPU i resety XTX (16–19.10)

Agent Pm4FaultAnalysis przeanalizował na CPU (journal, logi, kod `hip-pm4.cu`) 10 resetów: 8 to ta sama awaria taśmy PM4 w serwerze Qwen MTP, przyczyna nieudowodniona (H1 wywłaszczenie kolejki w środku IB ~60%), produkcja zagrożona (~1 reset/330 requestów, ~1/200 przy pełnym cache promptu).

**Strażnik `GGML_HIP_PM4_GUARD`** (gałąź `pm4-guard` @ `7cd12f993`, domyślnie 0, tylko skompilowany): `=1` memcmp IB przed replayem z naprawą, obserwacja zdarzeń KFD własnego procesu ([[kfd-smi-eventy]]) i po eviction/restore przez 3000 ms zwykły `cudaGraphLaunch` zamiast taśmy (koszt ~10–20 µs/taśmę `[SZACUNEK]`); `=2` dodatkowo porównanie kernargów z VRAM i znaczniki czasu per dispatch.

**Bezpieczny plan testu (niewykonany, wymaga zgody):** warunki – nikt inny na GPU (`pgrep -x`), 8080 zatrzymany, krzywa wentylatora sprawdzona, [[gpu-guard]] uruchomiony, stop po pierwszym faultcie.
- T0: build `7cd12f993` z `GGML_HIP_PM4=0`, 241 requestów; oczekiwane 0 faultów.
- T1: PM4 + `GUARD=2`, 241 requestów; logi evictionów, 0 „repaired”.
- T2 (tylko po czystym T1): soak ≥ 1000 requestów; kryterium PM4 w produkcji: 0 faultów i cool-down < 10% kroków.
- Opcjonalnie celowa reprodukcja H1 (wymuszona inwalidacja userptr) – kosztuje reset, osobna zgoda.

Rekomendacja: `GGML_HIP_PM4=0` w `run-llm.sh` i blokach agentów (Qwen MTP 108.8 → 103.7 t/s, −4.7%; LFM 293.6 → 259.3, −12%) – decyzja użytkownika ([[otwarte-decyzje-techniczne]]); PM4 nie trafia do produktu bez T2. Wyniki: [[2026-10-19-page-faulty-gpu-analiza]].

**§9 (Pm4Fix, 2026-10-19):** przyczyna wskazana w źródłach – brak `PRIV=1` w dispatchach taśmy na GFX11 + ewikcje SVM z kopii HIP stanu `--cache-ram`; nieudowodniona na GPU; prototypy `b7fb3fe85`; testy S1–S6 (S5 = celowy reset, opcjonalny) czekają na decyzję użytkownika ([[2026-10-19-pm4-priv-analiza]]).

## Powiązane
- [[pm4-replay]]
- [[dekodowanie-page-fault-amdgpu]]
- [[lekcja-pm4-zamienia-fault-w-reset]]
- [[2026-10-18-sprzezone-probkowanie-mtp]]
