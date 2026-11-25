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

## Księga czasu Nib vs Maya (K-162, 2026-11-25, XTX, rocprofv3, dekod bez spekulacji, KV q4)
- Wall: Nib `bench` tg128 **117,9 t/s** (8,5 ms/token, d=0, atencja gęsta); Maya produkcja CLI `--gen 129` **97,7 t/s** (10,2 ms/token).
- Czas GPU na token podobny: Nib ok. 7,6 ms, Maya ok. 8,0 ms; Maya ma ok. 700 wywołań kerneli na token, Nib ok. 330. **Uwaga:** ścieżka CLI `--gen` Mai nie jest ścieżką serwera; w serwerze z grafami Maya bez spekulacji robi 127,1 t/s (K-139, rep2 Q1), czyli ok. 7,9 ms/token, więcej niż Nib bez spekulacji (117,9). **Cała przewaga Nib przy T=0,7 (150,6 vs 112,5) to ekonomia DSparka**, nie kernele dekodu.
- Maya (µs/token, wywołania): mv_q8p 2514 (113), experts_q4k_gu 1533 (48), experts_q50_down 883 (48), attn_decode_mma 608 + combine 186, loop_gate_apply 434 + loop_gate_dots 198, attn_res_vec4 430 (99), router_route 340, moe_combine_conv 127, prep_qkv_r 113.
- Nib: moe_nvfp4_ship_fused192 2507 (47), qkv_qkvr_prep_fused 1601 (51), q8_gemv_wo_v2 674 (51), lm-head fdot2 607 (1), dwa fused mix+norm+router+top8 491 + 385, fa_decode_swa_v4 485 + fa_decode 120, mix_dual_ctrl_qkv3_norm 447, mix_rms_norm 208.
- MoE kosztuje u obu tyle samo (2,4–2,5 ms); różnica jest w drobnych kernelach (pętla, bramki, residuale, router: Maya ok. 1,4 ms w 290 wywołaniach vs Nib ok. 1,3 ms w 77) i w przerwach.
- Kolejność portu do Mai (agenci, 2026-11-25): (1) fuzje drobnych kerneli i pełny graf w trybie serwera, (2) tani DSpark (graf rundy, szerokość z pewności, top-k na GPU), (3) atencja (794 vs 605 µs), (4) strumienie wag `slc dlc`.

## Próbkowanie: 150 t/s tylko z top-k 40 (K-167, 2026-11-25, wall.py, KV q4)
- Serwer Nib bez pól próbkowania w zapytaniu bierze `--default-top-k 40 --default-top-p 0.95` (`src/main.cpp:593-595`). Wszystkie nasze liczby Nib przy T=0,7 (150,6) były więc z top-k 40.
- Ten sam klient z jawnym top-k 40 / top-p 0,95: Nib 168,8 (T=0) / 150,8 (T=0,7); Maya produkcja 113,9 / 113,4; Maya K-158 all-sl 100,4 / 93,5.
- Nib z pełnym rozkładem (top_k 0, top_p 1,0): T=0,7 **39,3 t/s**, czyli −74%. Maya na pełnym rozkładzie trzyma ok. 113 t/s.
- Wniosek: porównanie Nib vs Maya przy top-k 40 jest uczciwe (Maya bez zmian), ale „150 t/s” Nib to tylko ścieżka z obciętym rozkładem; klient wysyłający top_k 0 dostaje 39 t/s. Benchmarki T>0 zawsze z jawnym top-k/top-p w zapytaniu i z wpisanymi domyślnymi serwera.

## Nib uncensored: `--lora` AtomicChat (K-165, 2026-11-25)
- Łatka `~/qwen-opt/nib/nib-uncensored.patch` (gałąź `nib-unc`, 018d0fc + eb07c8f na 2e16cf0, 25 plików): adapter rank 1 (24 unikalne warstwy × wo i ffn_down_exps + token_embd, 15 MiB) liczony w każdej ścieżce: decode, weryfikacja MTP, prefill, wiele slotów, embedding kotwicy DSpark; poprawka do x3 przed short-convem, więc rollback MTP zgodny. Bez `--lora` bez zmian w kernelach.
- XTX: selftest z LoRA i bez: rollback bit w bit, 64 tokeny greedy MTP = bez MTP. Odmowy (5 promptów, T=0, 160 tok.): stock 5/5, z LoRA 0/5.
- wall.py KV q4: stock (ta sama binarka) 168,2 / 149,9, **z LoRA 156,6 / 147,3** (T=0 / T=0,7), czyli koszt LoRA −7% przy T=0 i −2% przy T=0,7. Maya produkcja tym samym klientem 113,9 / 113,4: **+30% przy T=0,7 dla wersji bez cenzury**.
- Jakość (K-168, HumanEval+ 164, greedy, bez thinking, max 2048 tok., `qwen-opt/nib/qeval-inkling.sh` + `jakosc-mini.sh eval`): **Nib NVFP4 + LoRA 92,1 / 87,2%** (base / plus), Maya produkcja AD-Q4_K 90,2 / 85,4%; różnica 3 zadania, w granicach szumu, czyli NVFP4 + LoRA nie gorsze. Dekod na kodzie: Nib 209,5 t/s, Maya 124,4 t/s (+68%).
- Zastrzeżenia: wagi NVFP4-Mixed, nie nasze AD-Q4_K (jakość do porównania), Quest stratny powyżej ok. 14k, pełny rozkład (top_k 0) 39 t/s. Zmiana produkcji Inkling = decyzja JARO.

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
