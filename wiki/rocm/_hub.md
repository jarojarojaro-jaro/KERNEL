---
typ: hub
tags: [rocm, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# ROCm i stos AMD

**Stos AMD, na którym pracujemy: ROCm, HIP, ROCr, PM4, rocprof, sterownik, ISA RDNA3.**

ROCm jest domyślnym backendem od 2026-10-12 (Vulkan tylko jako opcja). Kernele pisane pod ten stos: [[kernele/_hub|Kernele]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (21)

- [[amd-smi|AMD SMI (amd-smi)]] — Narzędzie i biblioteka AMD do telemetrii i sterowania GPU (moc, zegary, perf-level); w ROCm zastąpiło rocm-smi, działa na Linuksie, natywnego Windows brak.
- [[dekodowanie-page-fault-amdgpu|Dekodowanie page faultu amdgpu (gfx11)]] — Jak czytać wpisy `[gfxhub] page fault` i `sq_intr` w `journalctl -k` na RX 7900 XTX: pola `GCVM_L2_PROTECTION_FAULT_STATUS`, typy przerwań SQ i komunikaty MES (raport 17, 2026-10-19).
- [[kfd-ewikcja-kolejek-gfx11|Ewikcja i przywracanie kolejek KFD + MES na gfx11 (Linux 6.8)]] — KFD ewikuje wszystkie kolejki procesu przy unieważnieniu SVM lub userptr, ewikcji TTM i suspendzie; MES dostaje REMOVE_QUEUE, a przy restore ADD_QUEUE z tym samym MQD – pola dispatchu (`compute_pgm_*`, `user_data`, `restart`, `cp_hqd_ib_*`) zapisuje i odtwarza wyłącznie zamknięty firmware (raport 17 §9.2, 2026-10-19).
- [[hip-dyn-data-prefetch|HIP DynDataPrefetch (prefetch L2 przed kernelem)]] — `hipLaunchAttributeExtDynDataPrefetch` (prefetch regionów do L2 przed startem kernela) jest w HIP 7.15 u nas, ale ROCr zwraca 0 regionów dla wszystkiego poniżej gfx12.5, więc na gfx1100 nie działa.
- [[hip-na-windows|HIP na Windows: PAL zamiast ROCr]] — Na natywnym Windows HIP używa runtime PAL, a nie ROCr; dlatego łatki zależne od ROCr (PM4 replay 0060/0061) i profiler rocprofv3 tam nie działają.
- [[hip|HIP: jak piszemy kernele pod gfx1100]] — HIP to CUDA-podobny C++ kompilowany przez AMD clang; llama.cpp kompiluje swój backend CUDA jako HIP, a nasze kernele siedzą w tych samych plikach `ggml-cuda/*.cu`.
- [[hip-kopie-stronicowane-zostawiaja-svm|Kopie HIP z pamięci stronicowanej zostawiają zmapowane zakresy SVM]] — CLR kopiuje pamięć stronicowaną ≥ 64 KiB (develop) / 1 MiB (ROCm 7.0.0) przez „pin” w kawałkach po 32 MiB; libhsakmt rejestruje to przez SVM API (`HSA_USE_SVM` domyślnie, `ACCESS_IN_PLACE`), a unlock zakresu nie usuwa – każdy bufor stanu `--cache-ram` (520 MiB) zostaje zmapowany na GPU do `munmap` (raport 17 §9.3, 2026-10-19).
- [[hip-graph-narzut|Narzut grafu HIP: ~3 µs na kernel]] — Na gfx1100 każda granica kernela w grafie HIP kosztuje ~3.2–3.4 µs bezczynności GPU, niezależnie od typu kernela; przy ~2000 kerneli na krok to 16–19% czasu.
- [[pm4|PM4: bufory poleceń procesora poleceń GPU]] — PM4 to format pakietów, które wykonuje command processor (CP) karty AMD; jeden bufor PM4 z wieloma `DISPATCH_DIRECT` omija koszt ~2 µs na każdy pakiet AQL.
- [[rdna3-gfx1100|RDNA3 / gfx1100: architektura, pod którą piszemy]] — gfx1100 (Navi31) to RX 7900 XTX/XT/GRE i W7900/W7800: 96 CU w 48 WGP, natywnie wave32, WMMA bez osobnych tensor core'ów, DPP i VOPD; od tych cech zależy każdy nasz kernel.
- [[rocm-10-1|ROCm 10.1: co daje na gfx1100]] — Raport 13 (2026-10-16, bez GPU): 10.1 prawie nic nie zmienia dla gfx1100; ważniejsze okazały się ATT (już w 10.0) i przyczyna zerowych liczników PMC.
- [[rocm-vs-vulkan|ROCm czy Vulkan na RX 7900 XTX]] — Na początku Vulkan (RADV) dekodował szybciej, a ROCm szybciej przetwarzał prompt; 2026-10-12 ROCm został stałym backendem i od tej pory optymalizujemy tylko pod HIP.
- [[wsl2-rocm|ROCm w WSL2 (tech preview 10.1)]] — ROCm 10.1 działa w WSL2 przez ROCr + `librocdxg` → `/dev/dxg` → sterownik Adrenalin (WDDM), bez `/dev/kfd`; RX 7900 XTX jest na liście, ale nasz PM4 byłby tam po cichu pomijany.
- [[rocprof|rocprofv3 i profilowanie na gfx1100]] — Profilujemy rocprofv3 (ROCprofiler-SDK): trace kerneli w prawdziwym modelu daje mapę czasu kroku; liczniki PMC zwracały u nas 0, a PM4 jest dla profilera niewidoczne.
- [[rocr|ROCr (HSA runtime) i KFD]] — ROCr to linuksowy runtime niskiego poziomu (HSA) pod HIP: kolejki AQL, sygnały, loader code objectów; rozmawia z jądrem przez `/dev/kfd`. Na nim stoi nasz replay PM4.
- [[amdgpu-moc-i-termika|Sterownik amdgpu: limit mocy, termika, usypianie]] — Karta pracuje z limitem 285 W i wyłączonym usypianiem (runtime PM); bez tego model ląduje w RAM i działa ~4 t/s.
- [[rocm-stos|Stos ROCm na naszym serwerze]] — Pracujemy na ROCm 10.0 (`/opt/rocm/core-10.0`, wersja kandydująca 10.0.0~pre4) z RX 7900 XTX (gfx1100); ROCm 10.1 leży obok w katalogu użytkownika do testów.
- [[therock|TheRock: system budowania i wydań ROCm]] — Od ROCm 7.14 (2026-07-15) AMD buduje i wydaje ROCm przez otwarty system TheRock: Core SDK, instalator Runfile (kilka wersji obok siebie), pakiety DEB/RPM, koła Pythona per rodzina gfx i tarballe.
- [[gfx11-pm4-dispatch-priv|Własny dispatch PM4 na GFX11 musi ustawić `COMPUTE_PGM_RSRC1.PRIV=1`]] — Na GFX11 (w tym gfx1100) każdy własny `DISPATCH_DIRECT` musi ustawić `COMPUTE_PGM_RSRC1.PRIV=1` (bit 20) – obejście błędu CWSR DEGFX11_12113; firmware CP robi to sam tylko dla pakietów AQL, więc taśma PM4 kopiująca RSRC1 z deskryptora kernela startuje fale z PRIV=0 (raport 17 §9, 2026-10-19).
- [[trwala-siatka-bez-pm4|XTX bez PM4: trwała siatka wraca do gry (warunkowo)]] — Bez PM4 granica między kernelami kosztuje 2.75 µs w HIP graph, a podłoga pakietu AQL to 2.08 µs nawet bez fence'ów, podczas gdy bariera trwałej siatki to 0.48–0.77 µs; jeśli PM4 nie da się zabezpieczyć, trwały blok MoE na warstwę LFM jest jedyną bezstratną drogą do odzyskania części −12% (szacunek +8–10% względem PM4-off) (raport 21b, 2026-10-19).
- [[kfd-smi-eventy|Zdarzenia KFD SMI (`AMDKFD_IOC_SMI_EVENTS`) bez roota]] — Proces może otworzyć własny `/dev/kfd` i przez `AMDKFD_IOC_SMI_EVENTS` dostawać zdarzenia swoich kolejek (bez roota): `QUEUE_EVICTION` z przyczyną (SVM, userptr, TTM, suspend), `QUEUE_RESTORE`, plus globalne `VMFAULT` i `GPU_PRE_RESET` (raport 17, 2026-10-19).
<!-- AUTO:END -->
