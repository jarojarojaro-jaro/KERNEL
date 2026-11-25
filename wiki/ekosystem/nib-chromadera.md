---
typ: ekosystem
tags: [ekosystem, silnik, inkling, rdna3, spekulacja]
aktualizacja: 2026-11-25
zrodlo: https://x.com/Chromadera/status/2125383857604038982 (2026-11-25, link JARO); github.com/Chromadera/nib 2e16cf0 (2026-11-24); HF degenmeowster/Inkling-2-Mini-Nib-Pack; pomiary ~/qwen-opt/queue/logs/nibw-*.log, ~/qwen-opt/nib/out/nib.txt (jaroserverai, 2026-11-25); przegląd kodu podagenta 2026-11-25
status: aktualne
---
# Nib (Chromadera): silnik C++/HIP pod Inkling 2 Mini na 7900 XTX

**Nib na naszym XTX, mierzony tym samym klientem co Maya, szybciej dekoduje Inklinga: przy T=0,7 130,3 t/s z KV q8_0 i 150,6 z q4_0, wobec naszej produkcji 112,5. Wygrywa tanim DSparkiem (graf dla draftu, szerokość z pewności draftu, top-256 na GPU), ale liczy na innych wagach (NVFP4-Mixed, nie uncensored) i z rzadką uwagą Quest powyżej 14k tokenów.**

## Co to jest
- Własny silnik C++17/HIP tylko pod Inkling 2 Mini na gfx1100 (2e16cf0, Apache-2.0); OpenAI API, jeden graf HIP na token (ok. 290 węzłów), DSpark MTP z adaptacyjną szerokością 1–7 (`--spec-threshold 0.8`, lista 32 834 tokenów), weryfikacja z odrzucaniem przy T>0 i top-256 w kernelu.
- Wagi: własna paczka NVFP4 (warstwy MoE 0–19) + Q8_0 (reszta), 16,4 GiB; KLD do ggml Q8_0 0,0033 (README). Drafter `mtp.safetensors` bajt w bajt ten sam co nasz.
- KV q8_0 domyślnie; Quest: 224 strony × 64 tokeny = najwyżej 14 336 tokenów uwagi na warstwę globalną (przybliżenie powyżej), gęsta uwaga do 64k w prefillu.
- README (ich pomiar, greedy BetterBench, 8 slotów): 186,8 t/s ważony dekod, prefill ok. 4000 t/s. Victor Alcazar (X): vs maya-ik2 +25% przy 8k, +86% przy 258k; bez `top_k` ok. 31 t/s, bench pada (issue #1).

## Nasz pomiar (2026-11-25, XTX, PM4 wył., ctx 262 848, 1 slot, bez wizji)
Klient strumieniowy `qwen-opt/nib/wall.py` (tokeny / czas od pierwszego do ostatniego, 4 prompty × 300 tok.), ten sam dla obu silników:

| silnik | T=0 mediana | T=0,7 mediana | TTFT |
|---|---|---|---|
| Maya produkcja (AtomicChat AD-Q4_K, KV q4, lookup + sufiks 128, bez DSpark) | 112,8 / 113,1 | 112,5 / 112,8 | 163–555 ms |
| Nib, KV q8_0, Quest 224 | 139,0 | 130,3 (+16%) | 46–79 ms |
| Nib, KV q4_0, Quest 224 | 169,0 | 150,6 (+34%) | 46–78 ms |

- Rozrzut Nib zależy od treści: JSON 218–227 t/s, kod 126–202, polska proza 77–86 (Maya stale ok. 113).
- xbench (liczby z `timings` silnika): Nib q8 dense T=0,7 105,5–106,9, Q4 greedy 264–274; Maya T=0,7 111,7, Q4 86,8. Prefill 2k/8k z xbench tylko dla Mai (3160/3048), bo Nib nie ma `/tokenize`.
- Bez gfxhub fault; VRAM Nib 22,0–24,2 GB (zajmuje całą kartę).

## Czego uczy nas
- **DSpark może się opłacać przy T=0,7**, jeśli krok draftu i weryfikacji jest tani: u nas (K-139) DSpark przy T=0,7 tracił 11%, u Nib zyskuje. Różnice z kodu: statyczny graf dla draftu per długość (`dspark_mtp.cpp:767-803`, u nas `propose()` z synchronizacją), szerokość z pewności draftu zamiast z czasu (`server.cpp:2721`), top-256 na GPU zamiast sortu do 1000 kandydatów na hoście (`kernels_mtp_verify.hip:155-345`), wagi strumieniowane `slc dlc`.
- TTFT 46 ms vs nasze 163+ ms: narzut `server.py` (Python) i protokołu Mai przy krótkich promptach.
- Nie bierzemy: Quest (stratny > 14k), NVFP4 zamiast naszych wag (inny model, nie uncensored), KV q8 (reguła q4–q6).
- Na ich korzyść liczy się też q4_0 KV: z q4 Nib jest szybszy niż z q8 (mniej pasma), co zgadza się z naszą regułą.

## Dalej
K-158: przenieść do Mai mechanizmy DSpark z Nib (graf draftu, szerokość z pewności, top-k na GPU) i zmierzyć T=0,7 na naszych wagach uncensored; K-159: Nib z wagami uncensored (AtomicChat LoRA wtopiona w paczkę NVFP4) albo nasze AD-Q4_K w Nib, żeby porównać ten sam model.

## Powiązane
- [[inkling-2-mini]]
- [[ekonomia-okna-weryfikacji]]
- [[drafter-dflash]]
