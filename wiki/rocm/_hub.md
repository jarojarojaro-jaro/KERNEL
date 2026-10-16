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
## Notatki (14)

- [[amd-smi|AMD SMI (amd-smi)]] — Narzędzie i biblioteka AMD do telemetrii i sterowania GPU (moc, zegary, perf-level); w ROCm zastąpiło rocm-smi, działa na Linuksie, natywnego Windows brak.
- [[hip-na-windows|HIP na Windows: PAL zamiast ROCr]] — Na natywnym Windows HIP używa runtime PAL, a nie ROCr; dlatego łatki zależne od ROCr (PM4 replay 0060/0061) i profiler rocprofv3 tam nie działają.
- [[hip|HIP: jak piszemy kernele pod gfx1100]] — HIP to CUDA-podobny C++ kompilowany przez AMD clang; llama.cpp kompiluje swój backend CUDA jako HIP, a nasze kernele siedzą w tych samych plikach `ggml-cuda/*.cu`.
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
<!-- AUTO:END -->
