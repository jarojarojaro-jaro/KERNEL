---
typ: stos
tags: [stos, rocm-10-1, kompilator]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/13-rocm-10.1.md:1-34,122-173; ~/KERNEL/product/research/63c-amd-rocm-llamacpp.md:397-402; ~/KERNEL/product/research/13-rocm-10.1.md:1-33
status: do-sprawdzenia
---
# ROCm 10.1: co daje na gfx1100

**Raport 13 (2026-10-16, bez GPU): 10.1 prawie nic nie zmienia dla gfx1100; ważniejsze okazały się ATT (już w 10.0) i przyczyna zerowych liczników PMC.**

Zainstalowane user-local: tarball TheRock `gfx110X-all-10.1.0` (2.67 GB) w `~/opt/rocm-10.1` (11 GB), AMD clang 24.0.0git. Artefakty porównania ISA: `~/opt/isa101/`.

| funkcja | na gfx1100? |
|---|---|
| PC sampling | nie, tylko Instinct |
| kernel replay (beta) | formalnie tak, tylko PMC |
| ATT / thread trace | tak, „trace-only” (dekoder jest już w 10.0) |
| roofline w Compute Profiler | nie (Instinct, APU Ryzen) |
| hipFile / AIS | nie (Linux · Instinct) |
| WSL2 tech preview | tak, ale PM4 cicho pomijany |
| ROCr | 1.21.0, ta sama wersja co w 10.0 |

LLVM 23 → 24 (ISA naszych gorących TU): ISA różni się w 98% kerneli, ale mix fma/mul/add, WMMA i DPP bez zmian; emulator potwierdził GDN 8/8 ALL IDENTICAL. Czerwone flagi: `flash_attn_ext_kvq<256, 8, Q4_0>` spilluje 8 VGPR (Qwen ma head dim 256), 24 kernele MMVQ zmieniają kubełek occupancy. Clang 10.1 domyślnie używa `--offload-new-driver`; przebudowa nie jest szybsza.

Status: do potwierdzenia testem md5 + hash logitów + pomiar kvq na GPU (raport §10).

Checklista migracji z RDNA-FAST (R63c, 2026-11-05): `__align__(16)` na `__shared__`, jawne szerokie store'y, occupancy 1 dla kafli J32 4-bitowych, cap LDS w occupancy FA ([[lekcja-rocm10-lds-128kb]]); ich bilans 10.1 z poprawkami +3.1% vs 7.2 ([[rdna-fast]]).

## Ze scalonej notatki: Raport 13: ROCm 10.1

ROCm 10.1 nic istotnego nie daje na gfx1100: zostajemy na 10.0, a 10.1 trzymamy obok jako tarball user-local; ważniejsze odkrycia to ATT na gfx1100 i przyczyna PMC = 0.

Data 2026-10-16. Tarball TheRock gfx110X 10.1.0 (2.67 GB), rozpakowany do `~/opt/rocm-10.1` (11 GB); system ma `10.0.0~pre4`.
- PC sampling i roofline HTML: tylko Instinct (APU) – 0 dla nas.
- LLVM 24: ≈0 wydajności, ISA różni się w 98% kerneli, ryzyko spill w kvq D=256.
- CK FMHA: 0, bo llama.cpp nie używa CK. hipFile/AIS: tylko Instinct.
- WSL2 tech preview: RX 7900 XTX na liście, ale pakiet PM4 (0060) jest tam cicho pomijany → blokada 0060 pod WSL2.
- ATT/thread trace działa na gfx1100 już w 10.0 (`rocprofv3 --att`); PMC = 0 prawdopodobnie przez brak stabilnego stanu zasilania z `amd-smi`.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Werdykt w rejestrze „nic istotnego na gfx1100” był za wąski. Raport 13 dał nam trzy rzeczy ważniejsze niż sama wersja: ATT na gfx1100 (dziś narzędzie [[att-gfx1100]]), przyczynę zerowych PMC (stały stan zasilania przez `amd-smi`) i ostrzeżenie, że pod WSL2 taśma PM4 kończy się „sukcesem” bez wykonania kernela ([[wsl2-rocm]]).
- Produkt: AMD dołącza ROCm CLI z Lemonade jako „uruchom GGUF na Radeonie”, a `rocm-doctor` to gotowy wzór diagnostyki L0 (`product/research/13-rocm-10.1.md:26`). To ten sam brak, który pokazał [[inference-stack]]: diagnostyki z komendami po awarii.
- Stan bramki WSL2: w forku duo `pm4_enabled()` sprawdza tylko `GGML_HIP_PM4` i RDNA3, nie obecność `/dev/kfd` (`~/praca/llama-duo/ggml/src/ggml-cuda/hip-pm4.cu:284-287`); aplikacja nie wykrywa WSL (`rg -i wsl app/engine/src/server` = 0). Dziś to nie szkodzi, bo silnik ROCm gfx1100 ma `distribution: local` (`app/engine/data/engines.json:264-272`) i do użytkowników nie trafia; zanim trafi, blokada musi być w kodzie.
- Co bierzemy: przy każdym wydaniu ROCm pytać nie tylko „czy szybciej na gfx1100”, ale też „co się zmienia dla klientów” (WSL2, Windows, APU gfx1151, RDNA4 gfx1201) i „jakie narzędzia diagnostyczne dostajemy”.

## Powiązane
- [[rocm-stos]]
- [[rocprof]]
- [[wsl2-rocm]]
- [[fattn-kvq]]
