---
typ: research
tags: [research, pm4, awarie]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:1-208
status: aktualne
---
# Raport 17: page faulty GPU i resety XTX (16–19.10)

**Agent Pm4FaultAnalysis przeanalizował na CPU (journal, logi, kod `hip-pm4.cu`) 10 resetów: 8 to ta sama awaria taśmy PM4 w serwerze Qwen MTP, przyczyna nieudowodniona (H1 wywłaszczenie kolejki w środku IB ~60%), produkcja zagrożona (~1 reset/330 requestów, ~1/200 przy pełnym cache promptu).**

**Strażnik `GGML_HIP_PM4_GUARD`** (gałąź `pm4-guard` @ `7cd12f993`, domyślnie 0, tylko skompilowany): `=1` memcmp IB przed replayem z naprawą, obserwacja zdarzeń KFD własnego procesu ([[kfd-smi-eventy]]) i po eviction/restore przez 3000 ms zwykły `cudaGraphLaunch` zamiast taśmy (koszt ~10–20 µs/taśmę `[SZACUNEK]`); `=2` dodatkowo porównanie kernargów z VRAM i znaczniki czasu per dispatch.

**Bezpieczny plan testu (niewykonany, wymaga zgody):** warunki – nikt inny na GPU (`pgrep -x`), 8080 zatrzymany, krzywa wentylatora sprawdzona, [[gpu-guard]] uruchomiony, stop po pierwszym faultcie.
- T0: build `7cd12f993` z `GGML_HIP_PM4=0`, 241 requestów; oczekiwane 0 faultów.
- T1: PM4 + `GUARD=2`, 241 requestów; logi evictionów, 0 „repaired”.
- T2 (tylko po czystym T1): soak ≥ 1000 requestów; kryterium PM4 w produkcji: 0 faultów i cool-down < 10% kroków.
- Opcjonalnie celowa reprodukcja H1 (wymuszona inwalidacja userptr) – kosztuje reset, osobna zgoda.

Rekomendacja: `GGML_HIP_PM4=0` w `run-llm.sh` i blokach agentów (Qwen MTP 108.8 → 103.7 t/s, −4.7%; LFM 293.6 → 259.3, −12%) – decyzja użytkownika ([[otwarte-decyzje-produktu]]); PM4 nie trafia do produktu bez T2. Wyniki: [[2026-10-19-page-faulty-gpu-analiza]].

## Powiązane
- [[research/_hub|research]]
- [[pm4-replay]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
- [[raport-16k-sprzezone-probkowanie]]
