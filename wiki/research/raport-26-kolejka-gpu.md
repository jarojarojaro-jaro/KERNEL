---
typ: research
tags: [research, kolejka, pm4, wyniki]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:3-24
status: aktualne
---
# Raport 26: kolejka GPU 2026-10-19 wieczorem – testy odłożone przez pauzę

**PM4 `WA=2` + GUARD + `HSA_USE_SVM=0` wdrożone w topce (Qwen czat 111.0/110.8 → 115.3/115.8 t/s, +4.2%; LFM tg128 +11.1%; 1205 zapytań bez błędu), a bariera LDS (24a), MMVQ n=1 wide (24f) i ogon OOV (21o) odrzucone (2026-10-19).**

- Jeden test na raz przez `run-queue.sh`/`run-jobs.sh`, kontrola logu jądra po każdym; 0 błędów GPU, max hotspot 71 °C (`26:3`).
- Górna granica fuzji norm: tg128 40.82 → 42.69 t/s (+4.6%) → „robić” (`26:13`); realizacja nieudana ([[raport-24l-fuzja-norm]]).
- Profil W16: bezczynność GPU +1.6 ms → [[raport-24m-weryfikacja-gpu]] (`26:14`).
- Wpadki: podgląd landingu zabrał port `greedy.sh`; `orphan-guard.sh` zabił serwer z kolejki – właścicielem jest teraz każdy przodek z blokadą (`26:18-19`).
- PM4: [[pm4-replay]], [[2026-10-19-pm4-priv-analiza]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[pm4-replay]]
- [[2026-10-19-pm4-priv-analiza]]
- [[raport-24a-bariera-lds]]
- [[raport-24f-mmvq-fa]]
- [[raport-21o-gemma]]
