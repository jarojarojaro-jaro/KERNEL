---
typ: karta
tags: [karty, amd, maszyna]
aktualizacja: 2026-11-22
zrodlo: ~/kernel/system.md (sekcja „Na jaroserverai”); ~/kernel/zasady-jaroserverai.md; ~/KERNEL/wiki/decyzje/2026-10-20-karta-fabrycznie.md; ~/KERNEL/wiki/decyzje/2026-11-06-profil-eco-2200.md
status: aktualne
karta: jaroserverai
vram: 24 GB (RX 7900 XTX)
pasmo: 960 GB/s
gdzie: dom JARO, Tailscale
stan: zwykle wyłączony; włącza JARO
---
# jaroserverai: maszyna z naszą RX 7900 XTX

**Domowa maszyna JARO z jedyną naszą stałą kartą GPU, [[rx-7900-xtx]] (24 GB, gfx1100): produkcyjny czat na :8080 i wszystkie testy XTX przez kolejkę GPU; zwykle wyłączona, testy tylko na wyraźne polecenie JARO.**

- **Produkcja:** czat :8080 (topka, Qwen3.8-27B-Uncensored Q4_K_M ze spekulacją MTP); startuje go tylko `topka-keeper.sh`, test zatrzymuje go tylko pod własną blokadą GPU i przywraca `chat8080.sh restore`.
- **Kolejka GPU:** `~/qwen-opt/queue/run-jobs.sh` (linie `nazwa|timeout|katalog|polecenie`, FIFO, blokady `/tmp/gpu.lock` i `/tmp/quiet.lock`), jedno zadanie ≤ 15 min, ostatnie zawsze przywraca :8080; strażnik [[gpu-guard]] pilnuje temperatur.
- **Karta:** fabryczne ustawienia ([[2026-10-20-karta-fabrycznie]]), profil eco 2200 MHz ([[2026-11-06-profil-eco-2200]]); absolutne liczby z eco są ~7% niżej niż ze stock, porównujemy tylko w tej samej sesji.
- **PM4:** każdy test naszego forka z jawnym `GGML_HIP_PM4=0` albo `GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0`.
- **CPU:** ciężkie przez `cpuheavy` (2 sloty × 2 rdzenie, nice 19), kompilacje przez `rbuild`; testowe serwery `taskset -c 2-5`.
- **Przerwy:** maszyna znika z Tailscale bez ostrzeżenia (2026-11-20 ~20:52 i ~00:30, 2026-11-21 ~11:48); zadań sprzed przerwy nie zakładamy jako wykonanych.

## Dysk 2026-11-25: 99% zajęte (6,5 GB wolnego z 466 GB)
- Zajętość: modele 217 GB (q36 51, inkling 35, lfm 34, flint 22, nib 18, orca 17, orca-cyber-nano 17, Qwen3.8 UD-Q4_K_XL 17), `~/wt` ok. 65 GB w 153 worktree'ach (ok. 54 GB nieruszane od ponad 5 dni), `~/qwen-opt` 63 GB (mtp-train 11, cloud 6,3, re 6,6, research 4,3, duo 3,8), `~/opt` 14 GB (rocm-10.1 11, cuda-12.8 2,3), `~/rocm-10.2` 11 GB, `/opt` 19 GB, swap 8 GB, dziennik systemowy 2,2 GB.
- Produkcja (:8080) nie zależy od `~/wt`: binarka `~/llama-topka/bin/llama-server`. Lista do usunięcia czeka na zgodę JARO.

## Modele na dysku 2026-11-25 (po skasowaniu lfm, flint, orca-cyber-nano i orca)
- Produkcja i bieżąca praca (4 modele): Qwen3.8-27B Uncensored Q4_K_M (`~/models/orca/`, czat :8080; skasowany przez pomyłkę, pobierany ponownie 2026-11-25), Inkling 2 Mini Uncensored AD-Q4_K 16 GB (Maya), Nib NVFP4-Mixed 17 GB (Nib + LoRA uncensored), Bonsai 2.5 Uncensored Q2_0-mtp 7,4 GB; do tego draftery (Qwen DFlash2 1,1 GB, Qwen DSpark 1,4 GB, Inkling DSpark/MTP/DFlash2 ok. 1,9 GB) i LoRA/mmproj Inklinga.
- Poza tymi czterema: Qwen3.6-35B-A3B Q8_0 35 GB i IQ4_XS 17 GB (`q36`, tylko test K-025), Qwen3.8-27B UD-Q4_K_XL 17 GB (wersja z cenzurą, porównania i przepisy Enigmy), Inkling-2-Mini UD-Q4_K_XL 17 GB (wersja z cenzurą), drobne: qwen-image 175 MB, kb 130 MB, orcacyber 60 MB. Razem ok. 86 GB do decyzji JARO.
- Zabezpieczenie: `run-jobs.sh` nie startuje zadania przy wolnym miejscu < 70 GB (DISK GUARD, commit d73318b), `kol stan` pokazuje wolne miejsce.

## Wyłączanie
- Wyłącza się bez hasła wyłącznie dokładnym poleceniem `sudo -n /usr/bin/systemctl poweroff` (sudoers `jaro-poweroff`, NOPASSWD tylko dla tej ścieżki). `systemctl poweroff` bez sudo, `sudo poweroff` i `systemctl suspend` wymagają hasła (sprawdzone 2026-11-27). Przed wyłączeniem: pusta kolejka, `topka-stop.sh --now`, `sync`.

## Powiązane
- [[stos/topki]] (topka każdego modelu, model czatu :8080 w `topki/xtx/ACTIVE`)
- [[rx-7900-xtx]]
- [[google-colab]]
- [[vast-ai]]
- [[KOLEJKA-TESTOW]]
