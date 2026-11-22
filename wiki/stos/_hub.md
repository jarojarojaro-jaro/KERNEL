---
typ: hub
tags: [stos, hub]
aktualizacja: 2026-11-22
zrodlo: wiki/tools/czesci.py; wiki/tools/wiki.py index
status: aktualne
streszczono: 2026-11-22
---
# Silnik i stos GPU

**Nasz fork llama.cpp i gałęzie, ROCm/HIP/PM4/KFD, CUDA, sterowniki i architektury.**

<!-- Jarvo:STRESZCZENIE -->
Produkcja: fork llama.cpp „topka” (`~/llama-topka`, łatki amd-opt) na ROCm 10.0, gfx1100; taśma [[pm4]] tylko z `GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0`, inaczej `GGML_HIP_PM4=0`. ROCm 10.2: wydanie stabilizacyjne, bez nowego GEMV/FA dla gfx1100 (ZRODLA, K-130). CUDA: fork NVIDIA Enigmy (wydania KERNEL).
<!-- /Jarvo:STRESZCZENIE -->

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (39)

- [[init-user-pages-failed|`amdgpu: init_user_pages: Failed to get user pages: -1` przy starcie serwera]] — Każdy start llama-server na XTX wypisuje do logu jądra ~16 tys. wierszy `amdgpu: init_user_pages: Failed to get user pages: -1`; zjawisko trwa co najmniej od 2026-10-25, bez page faultów, resetów i wpływu na wyniki (md5 bramek zgodne).
- [[amd-smi|AMD SMI (amd-smi)]] — Narzędzie i biblioteka AMD do telemetrii i sterowania GPU (moc, zegary, perf-level); w ROCm zastąpiło rocm-smi, działa na Linuksie, natywnego Windows brak.
- [[sm-86-89-120|Architektury NVIDIA: sm_86, sm_89, sm_120]] — Celujemy w trzy generacje kart konsumenckich: Ampere sm_86 (RTX 3060, 3090), Ada sm_89 (RTX 4060 Ti) i Blackwell sm_120 (RTX 5060 Ti); różnią się m.in. obsługą PDL.
- [[bezpieczenstwo-tokenow-specjalnych|Bezpieczeństwo: SAFE_SPECIAL (wejście) i SAFE_TOOLS (wyjście)]] — Dwie dziury lustrzane: tekst z żądania stawał się tokenami sterującymi (32e), a tekst modelu udający marker otwierał prawdziwy tool call (39c); obie zamknięte i domyślnie włączone w `run-topka.sh` od 2026-10-21.
- [[dekodowanie-page-fault-amdgpu|Dekodowanie page faultu amdgpu (gfx11)]] — Jak czytać wpisy `[gfxhub] page fault` i `sq_intr` w `journalctl -k` na RX 7900 XTX: pola `GCVM_L2_PROTECTION_FAULT_STATUS`, typy przerwań SQ i komunikaty MES (raport 17, 2026-10-19).
- [[kfd-ewikcja-kolejek-gfx11|Ewikcja i przywracanie kolejek KFD + MES na gfx11 (Linux 6.8)]] — KFD ewikuje wszystkie kolejki procesu przy unieważnieniu SVM lub userptr, ewikcji TTM i suspendzie; MES dostaje REMOVE_QUEUE, a przy restore ADD_QUEUE z tym samym MQD – pola dispatchu (`compute_pgm_*`, `user_data`, `restart`, `cp_hqd_ib_*`) zapisuje i odtwarza wyłącznie zamknięty firmware (raport 17 §9.2, 2026-10-19).
- [[mec-fw-dispatch-aql-gfx11|Firmware MEC gfx11: co robi z pakietem AQL, a czego nie robi z `DISPATCH_DIRECT`]] — Przy pakiecie AQL firmware MEC ustawia RSRC1 = deskryptor & `0xe4aff3ff` z PRIV wziętym z flagi kolejki (obejście CWSR), RSRC2 = deskryptor & `0x1fbf` | TRAP_PRESENT | LDS z pakietu (granula 512 B, limit 64 KiB), `PGM_HI |= 0x100` i inicjator `0x1065 | W32<<15`; handler `DISPATCH_DIRECT` zapisuje tylko wymiary, START i inicjator, a RSRC1 bierze bez zmian – fale naszej taśmy dostają PRIV wyłącznie od nas (raport 23d, 2026-10-19).
- [[amd-opt|Gałąź amd-opt (produkcja ROCm)]] — Gałąź produkcyjna dla RX 7900 XTX: 70 commitów (łatki 0001–0070) liniowo na upstream `e60eff95f` z 2026-10-09, HEAD `f61994f58` (2026-10-15, epilog MMQ).
- [[amd-opt-v070|Gałąź amd-opt-v070 (rebase na v0.7.0)]] — Łatki `amd-opt` przeniesione na upstream v0.7.0 (`620d2225c`, 2026-10-15): 70 commitów, HEAD `8c942e5a9` (2026-10-16), worktree `~/wt/rebase070`.
- [[batch-invariant|Gałąź batch-invariant (LLAMA_SPEC_BITEXACT)]] — Gałąź `batch-invariant` @ `6e261fdb4` (2026-10-16) = `cuda-v070` + 4 commity: tryb `LLAMA_SPEC_BITEXACT`, w którym dekod spekulacyjny daje te same bity co zwykły.
- [[cuda-compat|Gałąź cuda-compat: poprawki forka dla NVIDIA]] — `amd-opt` nie kompilował się dla CUDA; gałąź `cuda-compat` @ `7b2680760` dodaje 4 commity (2 kompilacyjne, 2 semantyczne), a kod GPU dla gfx1100 zostaje bit w bit ten sam.
- [[mtp-train|Gałąź mtp-train (llama-mtp-extract)]] — Gałąź `mtp-train` @ `532fd1057` (2026-10-16) = `cuda-v070` + 1 commit: narzędzie `llama-mtp-extract` do danych treningowych głowicy MTP.
- [[nemotron-3090|Gałąź nemotron-3090]] — Gałąź `nemotron-3090` @ `e46d34e0e` (2026-10-16, worktree `~/wt/nemotron-opt`) = `cuda-3090-opt` (`3da7a02ec`) + 1 commit z przełącznikami pod Nemotron 3.5 Bolt na Ampere.
- [[opt-gdn6|Gałąź opt-gdn6 (szybki kernel GDN, bitowy z konstrukcji)]] — Gałąź `opt-gdn6` @ `0d89ce56c` (2026-10-15): osobny szybki kernel GDN dla RDNA, zbudowany tak, by był bitowo identyczny; oba commity NIEZMIERZONE (brak GPU w tej rundzie).
- [[opt-mmq6|Gałąź opt-mmq6 (epilog MMQ, łatka 0070)]] — Gałąź `opt-mmq6` @ `ae1ef6a97` (2026-10-15): epilog skal Q4_K/Q5_K w MMQ RDNA3 w operacjach f32 parowalnych w VOPD, bitowo te same sumy; w raporcie oznaczone jako NIEZMIERZONE.
- [[opt-qwen5|Gałąź opt-qwen5 (runda 5 Qwena)]] — Gałąź `opt-qwen5` @ `2aa6999ed` (2026-10-15) z `c36fd2c87`: próby GDN fast i podwójnego bufora y w MMQ, obie wycofane, plus ablacja P0 prefillu MMQ.
- [[opt-samp|Gałąź opt-samp (sampler bez wolnych ścieżek)]] — Gałąź `opt-samp` @ `f4f0deae5` (2026-10-15) z łatkami 0065–0069: szybkie kandydatki top-k w samplerze także z gramatyką, wszystko pod wyłącznikami.
- [[tools6|Gałąź tools6 (LOO, kanarki KLD, Kernel Tuner)]] — Gałąź `tools6` @ `4db68c6ab` (2026-10-15) dodaje tylko hak kompilacji `MMVQ_TUNE_NWARPS_N1` dla Kernel Tunera; reszta rundy to narzędzia w `~/qwen-opt/tools/`.
- [[cuda-v070|Gałęzie cuda-v070, cuda-3090-opt, cuda-v070-5060ti, 3060-opt]] — Nasze łatki na v0.7.0 z poprawkami dla NVIDIA: `cuda-v070` @ `7a538d96f` = `amd-opt-v070` + 4 commity cuda-compat; z niej wychodzą gałęzie kampanii chmurowej na RTX 3090, 5060 Ti i 3060.
- [[galezie-rund|Gałęzie rund optymalizacji (opt-*)]] — Każda runda agentów pracowała w osobnym worktree i gałęzi `opt-*`; zwycięskie commity trafiały do `amd-opt`, reszta zostaje jako zapis eksperymentu.
- [[hip-dyn-data-prefetch|HIP DynDataPrefetch (prefetch L2 przed kernelem)]] — `hipLaunchAttributeExtDynDataPrefetch` (prefetch regionów do L2 przed startem kernela) jest w HIP 7.15 u nas, ale ROCr zwraca 0 regionów dla wszystkiego poniżej gfx12.5, więc na gfx1100 nie działa.
- [[hip-na-windows|HIP na Windows: PAL zamiast ROCr]] — Na natywnym Windows HIP używa runtime PAL, a nie ROCr; dlatego łatki zależne od ROCr (PM4 replay 0060/0061) i profiler rocprofv3 tam nie działają.
- [[hip|HIP: jak piszemy kernele pod gfx1100]] — HIP to CUDA-podobny C++ kompilowany przez AMD clang; llama.cpp kompiluje swój backend CUDA jako HIP, a nasze kernele siedzą w tych samych plikach `ggml-cuda/*.cu`.
- [[hip-kopie-stronicowane-zostawiaja-svm|Kopie HIP z pamięci stronicowanej zostawiają zmapowane zakresy SVM]] — CLR kopiuje pamięć stronicowaną ≥ 64 KiB (develop) / 1 MiB (ROCm 7.0.0) przez „pin” w kawałkach po 32 MiB; libhsakmt rejestruje to przez SVM API (`HSA_USE_SVM` domyślnie, `ACCESS_IN_PLACE`), a unlock zakresu nie usuwa – każdy bufor stanu `--cache-ram` (520 MiB) zostaje zmapowany na GPU do `munmap` (raport 17 §9.3, 2026-10-19).
- [[hip-graph-narzut|Narzut grafu HIP: ~3 µs na kernel]] — Na gfx1100 każda granica kernela w grafie HIP kosztuje ~3.2–3.4 µs bezczynności GPU, niezależnie od typu kernela; przy ~2000 kerneli na krok to 16–19% czasu.
- [[llama-cpp-fork|Nasz fork llama.cpp: repozytoria, gałęzie i worktree]] — Cała praca kernelowa żyje w jednym repo git `~/llama-master` z worktree w `~/wt/`; gałąź produkcyjna to `amd-opt` (70 commitów na upstream `e60eff95f`), a jej odpowiednik na v0.7.0 to `amd-opt-v070`.
- [[pm4|PM4: bufory poleceń procesora poleceń GPU]] — PM4 to format pakietów, które wykonuje command processor (CP) karty AMD; jeden bufor PM4 z wieloma `DISPATCH_DIRECT` omija koszt ~2 µs na każdy pakiet AQL.
- [[rdna3-gfx1100|RDNA3 / gfx1100: architektura, pod którą piszemy]] — gfx1100 (Navi31) to RX 7900 XTX/XT/GRE i W7900/W7800: 96 CU w 48 WGP, natywnie wave32, WMMA bez osobnych tensor core'ów, DPP i VOPD; od tych cech zależy każdy nasz kernel.
- [[rocm-10-1|ROCm 10.1: co daje na gfx1100]] — Raport 13 (2026-10-16, bez GPU): 10.1 prawie nic nie zmienia dla gfx1100; ważniejsze okazały się ATT (już w 10.0) i przyczyna zerowych liczników PMC.
- [[rocm-vs-vulkan|ROCm czy Vulkan na RX 7900 XTX]] — Na początku Vulkan (RADV) dekodował szybciej, a ROCm szybciej przetwarzał prompt; 2026-10-12 ROCm został stałym backendem i od tej pory optymalizujemy tylko pod HIP.
- [[wsl2-rocm|ROCm w WSL2 (tech preview 10.1)]] — ROCm 10.1 działa w WSL2 przez ROCr + `librocdxg` → `/dev/dxg` → sterownik Adrenalin (WDDM), bez `/dev/kfd`; RX 7900 XTX jest na liście, ale nasz PM4 byłby tam po cichu pomijany.
- [[rocprof|rocprofv3 i profilowanie na gfx1100]] — Profilujemy rocprofv3 (ROCprofiler-SDK): trace kerneli w prawdziwym modelu daje mapę czasu kroku; liczniki PMC zwracały u nas 0, a PM4 jest dla profilera niewidoczne.
- [[rocr|ROCr (HSA runtime) i KFD]] — ROCr to linuksowy runtime niskiego poziomu (HSA) pod HIP: kolejki AQL, sygnały, loader code objectów; rozmawia z jądrem przez `/dev/kfd`. Na nim stoi nasz replay PM4.
- [[amdgpu-moc-i-termika|Sterownik amdgpu: limit mocy, termika, usypianie]] — Karta pracuje z limitem 285 W i wyłączonym usypianiem (runtime PM); bez tego model ląduje w RAM i działa ~4 t/s.
- [[cuda-stos|Stos CUDA: jak budujemy fork dla NVIDIA]] — Fork budujemy dla NVIDIA nvcc 12.8 z conda-forge (bez sudo, bez sterownika na serwerze), dla architektur sm_86, sm_89 i sm_120; testy na GPU robimy w chmurze.
- [[rocm-stos|Stos ROCm na naszym serwerze]] — Pracujemy na ROCm 10.0 (`/opt/rocm/core-10.0`, wersja kandydująca 10.0.0~pre4) z RX 7900 XTX (gfx1100); ROCm 10.1 leży obok w katalogu użytkownika do testów.
- [[therock|TheRock: system budowania i wydań ROCm]] — Od ROCm 7.14 (2026-07-15) AMD buduje i wydaje ROCm przez otwarty system TheRock: Core SDK, instalator Runfile (kilka wersji obok siebie), pakiety DEB/RPM, koła Pythona per rodzina gfx i tarballe.
- [[gfx11-pm4-dispatch-priv|Własny dispatch PM4 na GFX11 musi ustawić `COMPUTE_PGM_RSRC1.PRIV=1`]] — Na GFX11 (w tym gfx1100) każdy własny `DISPATCH_DIRECT` musi ustawić `COMPUTE_PGM_RSRC1.PRIV=1` (bit 20) – obejście błędu CWSR DEGFX11_12113; firmware CP robi to sam tylko dla pakietów AQL, więc taśma PM4 kopiująca RSRC1 z deskryptora kernela startuje fale z PRIV=0 (raport 17 §9, 2026-10-19).
- [[kfd-smi-eventy|Zdarzenia KFD SMI (`AMDKFD_IOC_SMI_EVENTS`) bez roota]] — Proces może otworzyć własny `/dev/kfd` i przez `AMDKFD_IOC_SMI_EVENTS` dostawać zdarzenia swoich kolejek (bez roota): `QUEUE_EVICTION` z przyczyną (SVM, userptr, TTM, suspend), `QUEUE_RESTORE`, plus globalne `VMFAULT` i `GPU_PRE_RESET` (raport 17, 2026-10-19).
<!-- AUTO:END -->
