---
typ: stos
tags: [stos, produkcja, topka, jaroserverai, karty]
aktualizacja: 2026-11-28
zrodlo: ~/qwen-opt/topki/xtx/*.sh, ~/qwen-opt/tools/topka-{start,stop,keeper,restart}.sh, ~/qwen-opt/l1tok/chat8080.sh (jaroserverai); panel JARO 2026-11-26 00:27
status: aktualne
---
# Topki: najlepszy zmierzony wariant każdego modelu na każdej karcie

**Od 2026-11-26 każdy model ma własną topkę (build + przełączniki + kontekst) na każdej karcie, a czat :8080 na jaroserverai zawsze wstaje z modelem zapisanym w `~/qwen-opt/topki/xtx/ACTIVE`, niezależnie od tego, kto go podnosi (keeper, kolejka, restart, autostart). Wcześniej `topka-keeper.sh` startował `run-topka.sh qwen` (UD-Q4_K_XL z cenzurą), a `chat8080.sh restore` `uncensored` (JARO: „topka ma byc dla kazdego modelu a nie jedna topka”).**

## Jak działa
- `~/qwen-opt/topki/<karta>/<model>.sh`: jedno polecenie startu topki modelu w pierwszym planie, port z `PORT`, `TOPKA_CTX` do kontroli n_ctx.
- `tools/topka-start.sh [model]`: domyślnie model z `ACTIVE`; zapisuje `/tmp/topka-8080.pid`. Jedyne wejście dla `topka-keeper.sh`, `chat8080.sh restore`, `topka-restart.sh` i autostartu z crontaba (`@reboot`).
- `tools/topka-stop.sh`: zatrzymuje dowolny serwer na :8080 (gniazdo + pidfile, całe drzewo procesów, także Maya). Używają go `chat8080.sh stop`, `run-jobs.sh` (linia 65) i keeper.
- Zmiana modelu czatu: `echo bonsai > ~/qwen-opt/topki/xtx/ACTIVE && ~/qwen-opt/tools/topka-restart.sh`.
- Keeper działał 2026-11-25 wieczorem wcale (brak procesu); uruchomiony ponownie 2026-11-26 i dopisany do `@reboot`.

## Tabela topek

| karta | model | topka | wynik (źródło) |
|---|---|---|---|
| RX 7900 XTX | Qwen3.8-27B Uncensored Q4_K_M (**ACTIVE**) | `~/llama-topka-k047` (qprep-spec + K-020 + K-012 `GGML_HIP_K012=1` + K-001c + K-006 THIN/PREFIX + K-047 `GGML_HIP_K047=1`), przełączniki `run-topka.sh`, ctx 262 144; wcześniej `~/llama-topka-k020`, `~/llama-topka` | dekod 1,7k ok. 135, 94k 123,7, 255k 78,7 t/s; [[REKORDY]] (wdrożone 2026-11-26), [[2026-11-09-wdrozenie-topka-q70]] |
| RX 7900 XTX | Qwen3.8-27B UD-Q4_K_XL | to samo, `run-topka.sh qwen`, ctx 204 800 | j.w. |
| RX 7900 XTX | Bonsai 2.5 27B Uncensored Q2_0 | topka-k157, MTP n2, ctx 262 144 | wall T=0,7 145,8 ([[bonsai-2-5-uncensored]]) |
| RX 7900 XTX | Inkling 2 Mini Uncensored AD-Q4_K | Maya `maya-atomic.json` → `~/k134/bin-k200p/maya-ik2` + `IK2_K200=1` (K-158g + K-185 + K-158s + K-200, 2026-11-27) | wall T=0 152,0, T=0,7 149,2; 90k 105,6; **kontekst 557 056** (drafter `IK2_DRAFT_CTX=131072`, `bin-k207p`; 546k: igły 5/5, dekod 56–82 t/s) ([[inkling-2-mini]], [[REKORDY]]) |
| RX 7900 XTX | Inkling 2 Mini GSQ-RCO IQ3_S bez cenzury, **1 048 576** | `topki/xtx/inkling-1m.sh` → Maya `bin-k203p` + `maya-iq3s-1m.json` (K-203, K-206) | wall 104,2 / 101,3; 128k 73–76; 360k 58,1; KL vs plik 0,0019 |
| NVIDIA (3090, 5060 Ti, 3060, 4090, 5090…) | Qwen3.8-27B i inne | przepisy Enigmy per karta | [[final-recipes-nvidia]] |

Modele bez pliku na dysku (LFM, Flint, Qwen3.6-35B) nie mają topki na XTX ([[2026-11-26-bez-pobierania-modeli]]).

## Powiązane
- [[stos/_hub|stos]]
- [[jaroserverai]]
- [[decyzje/2026-10-19-topka-tylko-keeper]]
