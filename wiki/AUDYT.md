---
typ: meta
tags: [meta, audyt]
aktualizacja: 2026-10-16
zrodlo: zrodlo każdej notatki (kolumna „wiersz źródła”); wiki/tools/wiki.py
status: aktualne
---
# Audyt liczb w wiki

**Każda liczba z każdej notatki (t/s, ms, %, $, GB, md5, commity, daty wyników) porównana z plikiem z jej `zrodlo`: 3941 sprawdzonych, 1 błędna i poprawiona, w 23 notatkach uzupełnione `zrodlo`.**

## Metoda (2026-10-16)
1. Dla każdej notatki (bez hubów, `index`, `log`) wyciągnięto tokeny liczbowe i hashe (≥ 2 znaki; pojedyncze cyfry pominięte).
2. `zrodlo` rozwinięte do plików (zakresy `:N-M`, klamry `{a,b}`, katalogi, transkrypt sesji `.jsonl`) albo do wyniku komendy `git` z `zrodlo`.
3. Token szukany najpierw w cytowanych wierszach (±3), potem w całym pliku; warianty zapisu: kropka/przecinek, spacja tysięcy.
4. Ręcznie przejrzane: wszystkie tokeny nieznalezione (56) i wszystkie znalezione poza cytowanymi wierszami (195). Te drugie to głównie identyfikatory (numer raportu „07”, numery łatek, nazwy kart, lata) albo ta sama liczba w innym wierszu tego samego źródła.
5. Liczby z plików binarnych / komend sprawdzone na żywo: `ls`/`stat ~/models`, `amd-smi version`, `wc -l`, `results/*/lb/*.jsonl` (avg_ts zaokrąglone do 0.1), `tbo/summary.txt`, `build/times.jsonl`.
Ograniczenie: automat potwierdza obecność liczby w źródle; kontekst semantyczny sprawdzony ręcznie tylko dla tokenów z punktu 4 i dla notatek pisanych w tej sesji.

## Wynik
| kategoria | liczba |
|---|---|
| OK w cytowanych wierszach | 3688 |
| OK w innym wierszu źródła (przejrzane) | 195 |
| OK po weryfikacji ręcznej | 57 |
| błędne → poprawione | 1 |
| **razem sprawdzonych** | **3941** |

Poprawiona liczba: [[kwanty-gguf]] – rozmiar Qwen3.8-27B UD-Q4_K_XL 16.34 → **16.35 GiB** (`stat`: 17 559 178 144 B; SPEC-QWEN27B.md:21 obcinał).

Uzupełnione `zrodlo` (liczba była prawdziwa, ale nie w cytowanym pliku): [[modele/kwanty-gguf]], [[nvidia/cuda-stos]], [[nvidia/nvidia-wyniki-2026-10-16]], [[karty/rx-7900-xtx]], [[kernele/clamp-q8-1]], [[narzedzia/gpu-keepawake]], [[narzedzia/gdnemu-isadiff]], [[narzedzia/reactor-monitor]], [[narzedzia/loo-py]], [[repo/mtp-train]], [[repo/opt-gdn6]], [[repo/strata]], [[repo/tools6]], [[lekcje/lekcja-zombie-serwery]], [[lekcje/lekcja-bledny-roofline]], [[ludzie-firmy/firma-nvidia]], [[ludzie-firmy/ggml-org]], [[ludzie-firmy/liquidai]], [[decyzje/2026-10-16-prosta-baza-wiedzy]], [[eksperymenty/2026-10-16-rebase-v070]], [[karty/rtx-3090]], [[karty/rtx-5060-ti]], [[latki/patch-manifest]].

Uwaga: w chwili pierwszego audytu raportów 09 i 11 jeszcze nie było; dodano je 2026-10-16 rano (sekcja „Aktualizacja: wyniki finalne” niżej).

## Tabela (notatka, liczby, wiersz źródła, status)
| notatka | liczby | wiersz źródła | status |
|---|---|---|---|
| [[chmura/amd-dev-cloud]] | 05 | 05-chmura-gpu-do-testow.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[chmura/amd-dev-cloud]] | 1.75, 1.99, 2.39, 2.99 | 05-chmura-gpu-do-testow.md:114 | OK |
| [[chmura/amd-dev-cloud]] | 10, 25 | 05-chmura-gpu-do-testow.md:164 | OK |
| [[chmura/amd-dev-cloud]] | 100, 30 | 05-chmura-gpu-do-testow.md:39 | OK |
| [[chmura/amd-dev-cloud]] | 14 | 05-chmura-gpu-do-testow.md:40 | OK |
| [[chmura/amd-dev-cloud]] | 50 | 05-chmura-gpu-do-testow.md:113 | OK |
| [[chmura/harness-chmurowy]] | 0.3 | PLAN-TESTOW.md:38 | OK |
| [[chmura/harness-chmurowy]] | 0.98, 12.8, 24 | PLAN-TESTOW.md:36 | OK |
| [[chmura/harness-chmurowy]] | 15 | PLAN-TESTOW.md:47 | OK |
| [[chmura/harness-chmurowy]] | 20 | PLAN-TESTOW.md:40 | OK |
| [[chmura/harness-chmurowy]] | 600 | PLAN-TESTOW.md:13 | OK |
| [[chmura/radeony-do-wynajecia]] | 0.04, 0.17, 9070 | 05-chmura-gpu-do-testow.md:23 | OK |
| [[chmura/radeony-do-wynajecia]] | 0.22 | 05-chmura-gpu-do-testow.md:28 | OK |
| [[chmura/radeony-do-wynajecia]] | 0.471 | 05-chmura-gpu-do-testow.md:24 | OK |
| [[chmura/radeony-do-wynajecia]] | 0.49 | 05-chmura-gpu-do-testow.md:29 | OK |
| [[chmura/radeony-do-wynajecia]] | 0.635, 2.54 | 05-chmura-gpu-do-testow.md:140 | OK |
| [[chmura/radeony-do-wynajecia]] | 05 | 05-chmura-gpu-do-testow.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[chmura/radeony-do-wynajecia]] | 1,470, 694 | 05-chmura-gpu-do-testow.md:258 | OK |
| [[chmura/radeony-do-wynajecia]] | 129, 179, 270 | 05-chmura-gpu-do-testow.md:26 | OK |
| [[chmura/radeony-do-wynajecia]] | 2026 | 05-chmura-gpu-do-testow.md:75 | OK |
| [[chmura/radeony-do-wynajecia]] | 24 | 05-chmura-gpu-do-testow.md:27 | OK |
| [[chmura/radeony-do-wynajecia]] | 299 | 05-chmura-gpu-do-testow.md:72 | OK |
| [[chmura/radeony-do-wynajecia]] | 395 | 05-chmura-gpu-do-testow.md:25 | OK |
| [[chmura/radeony-do-wynajecia]] | 7900 | 05-chmura-gpu-do-testow.md:22 | OK |
| [[chmura/runpod]] | 0.22, 0.50, 22 | 05-chmura-gpu-do-testow.md:99 | OK |
| [[chmura/runpod]] | 0.34, 0.89 | 05-chmura-gpu-do-testow.md:103 | OK |
| [[chmura/runpod]] | 0.69, 1.19 | 05-chmura-gpu-do-testow.md:108 | OK |
| [[chmura/runpod]] | 05 | 05-chmura-gpu-do-testow.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[chmura/runpod]] | 1.11 | PLAN-TESTOW.md:11 | OK |
| [[chmura/runpod]] | 2.39, 3070, 5090 | 05-chmura-gpu-do-testow.md:67 | OK |
| [[chmura/runpod]] | 2026 | 05-chmura-gpu-do-testow.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[chmura/runpod]] | 3.0 | PLAN-TESTOW.md:12 | OK |
| [[chmura/runpod]] | 3060 | 05-chmura-gpu-do-testow.md:68 | OK |
| [[chmura/runpod]] | 3090, 4090 | 05-chmura-gpu-do-testow.md:69 | OK |
| [[chmura/salad]] | 0.04, 0.17, 7800, 9060, 9070 | 05-chmura-gpu-do-testow.md:23 | OK |
| [[chmura/salad]] | 0.09, 3090 | 05-chmura-gpu-do-testow.md:21 | OK |
| [[chmura/salad]] | 0060 | 05-chmura-gpu-do-testow.md:26 | OK |
| [[chmura/salad]] | 05 | 05-chmura-gpu-do-testow.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[chmura/salad]] | 20 | 05-chmura-gpu-do-testow.md:365 | OK |
| [[chmura/salad]] | 3060 | 05-chmura-gpu-do-testow.md:68 | OK |
| [[chmura/salad]] | 5090 | 05-chmura-gpu-do-testow.md:19 | OK |
| [[chmura/salad]] | 7.1 | 05-chmura-gpu-do-testow.md:136 | OK |
| [[chmura/salad]] | 7900 | 05-chmura-gpu-do-testow.md:22 | OK |
| [[chmura/vast-ai]] | 0.08, 3060 | 05-chmura-gpu-do-testow.md:14 | OK |
| [[chmura/vast-ai]] | 0.097 | PLAN-TESTOW.md:99 | OK |
| [[chmura/vast-ai]] | 0.165, 163 | 05-chmura-gpu-do-testow.md:104 | OK |
| [[chmura/vast-ai]] | 0.188 | 05-chmura-gpu-do-testow.md:110 | OK |
| [[chmura/vast-ai]] | 0.228, 162 | 05-chmura-gpu-do-testow.md:99 | OK |
| [[chmura/vast-ai]] | 0.232 | PLAN-TESTOW.md:101 | OK |
| [[chmura/vast-ai]] | 0.294 | 05-chmura-gpu-do-testow.md:105 | OK |
| [[chmura/vast-ai]] | 0.507, 318 | 05-chmura-gpu-do-testow.md:103 | OK |
| [[chmura/vast-ai]] | 0.734 | 05-chmura-gpu-do-testow.md:108 | OK |
| [[chmura/vast-ai]] | 05 | 05-chmura-gpu-do-testow.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[chmura/vast-ai]] | 1.8 | PLAN-TESTOW.md:11 | OK |
| [[chmura/vast-ai]] | 10, 2026 | 05-chmura-gpu-do-testow.md:13 | OK |
| [[chmura/vast-ai]] | 2.5 | PLAN-TESTOW.md:5 | OK |
| [[chmura/vast-ai]] | 3090 | 05-chmura-gpu-do-testow.md:15 | OK |
| [[chmura/vast-ai]] | 4090 | 05-chmura-gpu-do-testow.md:16 | OK |
| [[chmura/vast-ai]] | 445, 5090 | 05-chmura-gpu-do-testow.md:19 | OK |
| [[chmura/vast-ai]] | 50 | 05-chmura-gpu-do-testow.md:66 | OK |
| [[chmura/vast-ai]] | 5060 | 05-chmura-gpu-do-testow.md:17 | OK |
| [[chmura/vast-ai]] | 5070 | 05-chmura-gpu-do-testow.md:18 | OK |
| [[chmura/vast-ai]] | 80 | 05-chmura-gpu-do-testow.md:21 | OK |
| [[decyzje/2026-10-09-limit-mocy-odlozony]] | 20, 2026 | NOTES.md:109 | OK |
| [[decyzje/2026-10-09-limit-mocy-odlozony]] | 272, 303, 350 | NOTES.md:110 | OK |
| [[decyzje/2026-10-09-limit-mocy-odlozony]] | 285 | NOTES.md:126 | OK (inny wiersz źródła, sprawdzone) |
| [[decyzje/2026-10-12-rocm-domyslny]] | 0006 | NOTES.md:187 | OK |
| [[decyzje/2026-10-12-rocm-domyslny]] | 0010, 2026 | NOTES.md:190 | OK |
| [[decyzje/2026-10-14-lfm-kv-q8]] | 0.044, 0.128 | 07-nasze-metody-uogolnienie.md:449 | OK |
| [[decyzje/2026-10-14-lfm-kv-q8]] | 0055 | NOTES.md:139 | OK (inny wiersz źródła, sprawdzone) |
| [[decyzje/2026-10-14-lfm-kv-q8]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[decyzje/2026-10-14-lfm-kv-q8]] | 144, 187, 2.6, 30.1, 98 | NOTES.md:354 | OK |
| [[decyzje/2026-10-14-lfm-kv-q8]] | 2026 | NOTES.md:353 | OK |
| [[decyzje/2026-10-15-czat-na-web-ui-llama]] | 12 | PLAN.md:491 | OK |
| [[decyzje/2026-10-15-czat-na-web-ui-llama]] | 2026 | PLAN.md:116 | OK |
| [[decyzje/2026-10-15-czat-na-web-ui-llama]] | 3.3 | PLAN.md:115 | OK |
| [[decyzje/2026-10-15-karty-kupujemy]] | 12, 3060 | PLAN.md:288 | OK |
| [[decyzje/2026-10-15-karty-kupujemy]] | 16, 5060 | PLAN.md:287 | OK |
| [[decyzje/2026-10-15-karty-kupujemy]] | 2026, 3090, 4090, 5090 | PLAN.md:282 | OK |
| [[decyzje/2026-10-15-karty-kupujemy]] | 5.2 | PLAN.md:281 | OK |
| [[decyzje/2026-10-15-karty-kupujemy]] | 5070 | PLAN.md:290 | OK |
| [[decyzje/2026-10-15-karty-kupujemy]] | 9070 | PLAN.md:289 | OK |
| [[decyzje/2026-10-15-linux-i-analiza-platformy]] | 2026 | PLAN.md:27 | OK |
| [[decyzje/2026-10-15-linux-i-analiza-platformy]] | 5.1 | PLAN.md:274 | OK |
| [[decyzje/2026-10-15-open-core]] | 12 | PLAN.md:491 | OK |
| [[decyzje/2026-10-15-open-core]] | 2026 | PLAN.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[decyzje/2026-10-15-reasoning-control-off]] | 00, 2026 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:4329 | OK |
| [[decyzje/2026-10-15-reasoning-control-off]] | 0065, 14 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:4331 | OK |
| [[decyzje/2026-10-15-reasoning-control-off]] | 255.6, 291.4 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:4380 | OK |
| [[decyzje/2026-10-15-zakaz-gpu-w-nocy]] | 00, 02, 2026, 45 | qwen-round5.md:7 | OK |
| [[decyzje/2026-10-16-bez-lokalnego-gpu]] | 00, 2026 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5300 | OK |
| [[decyzje/2026-10-16-bez-lokalnego-gpu]] | 02, 46 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5590 | OK |
| [[decyzje/2026-10-16-bez-lokalnego-gpu]] | 20 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5301 | OK |
| [[decyzje/2026-10-16-bez-lokalnego-gpu]] | 45 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5591 | OK |
| [[decyzje/2026-10-16-bez-lokalnego-gpu]] | 56, 7900 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5302 | OK |
| [[decyzje/2026-10-16-bez-lokalnego-gpu]] | 77240, 77240c9b3 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5574 | OK (inny wiersz źródła, sprawdzone) |
| [[decyzje/2026-10-16-budzety-chmury]] | 00, 01, 2026, 38, 52 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5283 | OK |
| [[decyzje/2026-10-16-budzety-chmury]] | 02, 31 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5287 | OK |
| [[decyzje/2026-10-16-budzety-chmury]] | 35 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5395 | OK |
| [[decyzje/2026-10-16-landing-i-konto]] | 00, 2026, 36, 38 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5233 | OK |
| [[decyzje/2026-10-16-landing-i-konto]] | 571, 571e505 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5247 | OK |
| [[decyzje/2026-10-16-landing-i-konto]] | 8.1 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5248 | OK |
| [[decyzje/2026-10-16-landing-i-konto]] | c04dfdc | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5254 | OK (inny wiersz źródła, sprawdzone) |
| [[decyzje/2026-10-16-najpierw-wynajem-na-vast]] | 00, 2026, 23, 3060, 3090, 5060, 52 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5211 | OK |
| [[decyzje/2026-10-16-najpierw-wynajem-na-vast]] | 39 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5214 | OK |
| [[decyzje/2026-10-16-najpierw-wynajem-na-vast]] | 5.2 | PLAN.md:281 | OK |
| [[decyzje/2026-10-16-prosta-baza-wiedzy]] | 2026 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5478 | OK |
| [[decyzje/2026-10-16-runpod-drugi-pod]] | 02, 2026, 38 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5553 | OK |
| [[decyzje/2026-10-16-saluki-bonsai-na-3060]] | 0.8 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5371 | OK |
| [[decyzje/2026-10-16-saluki-bonsai-na-3060]] | 00, 01, 2026, 52 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5283 | OK |
| [[decyzje/2026-10-16-saluki-bonsai-na-3060]] | 08, 26 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5287 | OK |
| [[decyzje/2026-10-16-saluki-bonsai-na-3060]] | 27, 3060, 3090, 5060 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5286 | OK |
| [[decyzje/2026-10-16-wiki-jeden-agent]] | 02, 17, 2026, 23 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5503 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 10.0, 7900 | NOTES.md:1 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 1044, 850 | NOTES.md:16 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 116, 22.0 | 2026-10-09-rx7900xtx-qwen38-27b.md:15 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 127 | NOTES.md:48 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 131072 | SPEC-QWEN27B.md:70 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 2026 | 2026-10-09-rx7900xtx-qwen38-27b.md:1 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 204800 | NOTES.md:6 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 22.3, 59.4, 91.8 | NOTES.md:13 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 22.8, 47.4, 59, 59.2, b356fa262 | NOTES.md:10 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 23, 23.2, 60.2, 64, 85.5 | NOTES.md:11 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 25.2 | 2026-10-09-rx7900xtx-qwen38-27b.md:4 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 256 | NOTES.md:3 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 296, 621 | 2026-10-09-rx7900xtx-qwen38-27b.md:23 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 40 | SPEC-QWEN27B.md:75 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 43 | 2026-10-09-rx7900xtx-qwen38-27b.md:31 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 58 | NOTES.md:42 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 69 | 2026-10-09-rx7900xtx-qwen38-27b.md:21 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 7.5 | 2026-10-09-rx7900xtx-qwen38-27b.md:25 | OK |
| [[eksperymenty/2026-10-09-pierwsze-pomiary]] | 92 | SPEC-QWEN27B.md:58 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 0.0, 81.9 | NOTES.md:140 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 0.3, 80.7 | NOTES.md:135 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 0.5 | NOTES.md:136 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 0.7, 79.5 | NOTES.md:139 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 1.0, 64, 80.5 | NOTES.md:133 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 120 | NOTES.md:158 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 15 | NOTES.md:119 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 2026 | NOTES.md:122 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 204800 | NOTES.md:148 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 285, 90.6, 94.1, 94.7 | NOTES.md:126 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 3.5 | NOTES.md:145 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 4.4, 92 | NOTES.md:124 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 400 | NOTES.md:129 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 47 | NOTES.md:137 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 47.0 | NOTES.md:138 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 71.9 | NOTES.md:156 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 75.0 | NOTES.md:134 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 81.1 | NOTES.md:154 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 86.2 | NOTES.md:153 | OK |
| [[eksperymenty/2026-10-10-sweep-mtp-dflash]] | 86.3 | NOTES.md:151 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 0.7, 24 | NOTES.md:210 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 1.2, 517 | NOTES.md:211 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 1.4, 536 | NOTES.md:212 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 1.7, 78.6, 92.9 | NOTES.md:199 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 1024, 2048, 204800, 24.5, 512 | NOTES.md:218 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 1040, 1050 | NOTES.md:217 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 16384, 8192 | NOTES.md:213 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 2026 | NOTES.md:190 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 25, 3.8, 91, 99.8 | STATUS-NEXT.md:41 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 27 | NOTES.md:206 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 27332, 31.9 | NOTES.md:209 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 28 | NOTES.md:195 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 29.5, 62.4, 74.4 | NOTES.md:201 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 41.65, 41.69 | NOTES.md:216 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 43.0, 65, 70.9, 94 | NOTES.md:202 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 6.6, 75.5, 81.4 | NOTES.md:200 | OK |
| [[eksperymenty/2026-10-12-cache-promptu-i-a7]] | 71.6 | NOTES.md:204 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 0.0067, 0.0098, 6.182, 6.191, 96.5 | NOTES.md:225 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 1.7, 106.9, 43.0, 77.7, 78.6, 94 | NOTES.md:234 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 1308, 2156, 4.30, 6.99 | NOTES.md:223 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 16 | NOTES.md:232 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 2026 | NOTES.md:221 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 3.23, 972 | NOTES.md:230 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 33.79, 35.67, 88.1, 90.4 | NOTES.md:239 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 34.52, 36.38, 86.4, 88.5 | NOTES.md:231 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 35.83, 37.71, 39.6, 41.7, 74.8, 78.5, 83.3, 85.3 | NOTES.md:224 | OK |
| [[eksperymenty/2026-10-12-fuzje-a3-a6]] | 85.2, 87.6 | NOTES.md:233 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 1.7, 40 | RESULTS.md:98 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 107, 127, 35, 69 207 | RESULTS.md:15 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 11, 3.04, 3.93 | RESULTS.md:68 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 12.1 | RESULTS.md:108 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 2.14, 4096, 71, 74 | RESULTS.md:9 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 2.3, 3.7, 7.4 | RESULTS.md:21 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 2026, c90db29c6 | RESULTS.md:5 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 2048 | RESULTS.md:100 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 25 | RESULTS.md:91 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 27 | RESULTS.md:3 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 30, 57 | RESULTS.md:13 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 45 | RESULTS.md:109 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 5.3, 60 | RESULTS.md:102 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 97.3, 98.2, 99.0, 99.6 | RESULTS.md:40 | OK |
| [[eksperymenty/2026-10-12-mtp-trening-faza1]] | 98.4 | RESULTS.md:35 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 1.7, 13.3, 15.0, 683, 750, 78.6, 92, 92.4 | NOTES.md:175 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 1000 | NOTES.md:173 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 1200, 15.5 | NOTES.md:184 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 165, 260, 397, 43.0, 43.9, 666, 94 | NOTES.md:178 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 20.3, 21.2, 6.6, 746, 75.5, 80, 80.9, 924 | NOTES.md:176 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 2026, 204800, 256, 64 | NOTES.md:172 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 29.5, 50.2, 62.4, 624, 66.1, 863 | NOTES.md:177 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 38.4, 41.5, 41.8, 44.5, 73.8, 74.4, 74.5 | NOTES.md:183 | OK |
| [[eksperymenty/2026-10-12-rocm-vs-vulkan]] | 44 | NOTES.md:180 | OK |
| [[eksperymenty/2026-10-12-vulkan-krok-po-kroku]] | 0.0036, 0.0042, 512, 6.2099, 6.2226 | NOTES.md:167 | OK |
| [[eksperymenty/2026-10-12-vulkan-krok-po-kroku]] | 0.3, 39.92, 4.8, 41.46, 41.93, 43.73, 5.2 | NOTES.md:166 | OK |
| [[eksperymenty/2026-10-12-vulkan-krok-po-kroku]] | 0.5, 13.6, 48, 68, 68e163cf4, 8.6 | NOTES.md:164 | OK |
| [[eksperymenty/2026-10-12-vulkan-krok-po-kroku]] | 1.3, 1.9, 579, 614, 663, 665, 690, 699, 6c7801bf6, 81, 81e5fb913, afbb23886, f6e5de112 | NOTES.md:165 | OK |
| [[eksperymenty/2026-10-12-vulkan-krok-po-kroku]] | 2026, 204800, 285 | NOTES.md:162 | OK |
| [[eksperymenty/2026-10-12-vulkan-krok-po-kroku]] | 284, 87, 90 | NOTES.md:170 | OK |
| [[eksperymenty/2026-10-12-vulkan-krok-po-kroku]] | 80.3, 80.5 | NOTES.md:163 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 0021 | NOTES.md:176 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 0022, 22.1, 24.3 | NOTES.md:245 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 1280, 16 | NOTES.md:250 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 2026, 60, 60ce2a71f, 9f83f1f81 | NOTES.md:241 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 28.4, 31.0 | NOTES.md:254 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 32 | NOTES.md:242 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 32.02, 33.17 | NOTES.md:255 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 33.79, 35.67, 88.1 | NOTES.md:239 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 40 | NOTES.md:249 | OK |
| [[eksperymenty/2026-10-13-k1-mmvq]] | 94.7, 95.4 | NOTES.md:246 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 0023 | NOTES.md:11 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 0024 | NOTES.md:210 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 0025 | NOTES.md:25 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 0026 | NOTES.md:350 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 0027 | NOTES.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 0028 | NOTES.md:195 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 1.84, 1.87, 2.68 | NOTES.md:263 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 16.8, 4.3 | NOTES.md:262 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 17.7 | NOTES.md:268 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 2.8, 3.18, 831 | NOTES.md:273 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 2026, 849b69978, ba90baf3a | NOTES.md:258 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 30.68, 32.14, 97.8 | NOTES.md:274 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 32.50, 99.6, 9f83f1f81 | NOTES.md:266 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 33.17 | NOTES.md:255 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 4.51, 5.87, 5120 | NOTES.md:261 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 4.68, 4.90, 5.54 | NOTES.md:264 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 65504 | NOTES.md:259 | OK |
| [[eksperymenty/2026-10-13-k2-male-kernele]] | 972 | NOTES.md:265 | OK |
| [[eksperymenty/2026-10-13-k3-host]] | 0.65 | NOTES.md:281 | OK |
| [[eksperymenty/2026-10-13-k3-host]] | 0029, 101.5, 103.7, 29.46, 30.97 | NOTES.md:279 | OK |
| [[eksperymenty/2026-10-13-k3-host]] | 0031 | NOTES.md:195 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k3-host]] | 0047 | NOTES.md:10 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k3-host]] | 1.1, 140, 375, 645, 963 | NOTES.md:278 | OK |
| [[eksperymenty/2026-10-13-k3-host]] | 1.7, 109.4, 126.0, 29.5, 6.6, 88.3, 94, 98.8 | NOTES.md:280 | OK |
| [[eksperymenty/2026-10-13-k3-host]] | 16, 248 | NOTES.md:277 | OK |
| [[eksperymenty/2026-10-13-k3-host]] | 2026, 2eb088419, 35, 35d04b446, 56, 56be15abf | NOTES.md:276 | OK |
| [[eksperymenty/2026-10-13-k3-host]] | 32.14, 97.8 | NOTES.md:274 | OK |
| [[eksperymenty/2026-10-13-k4-i-hw-queues]] | 0.43, 32.1, 35.0, 49.2, 51.0 | NOTES.md:298 | OK |
| [[eksperymenty/2026-10-13-k4-i-hw-queues]] | 0037 | NOTES.md:224 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-k4-i-hw-queues]] | 16, 2026, d3a0973ae | NOTES.md:297 | OK |
| [[eksperymenty/2026-10-13-k4-i-hw-queues]] | 2305 | NOTES.md:302 | OK |
| [[eksperymenty/2026-10-13-k4-i-hw-queues]] | 29.30, 29.39 | NOTES.md:303 | OK |
| [[eksperymenty/2026-10-13-k4-i-hw-queues]] | 4 101.7, 470, 5 105.4 | NOTES.md:299 | OK |
| [[eksperymenty/2026-10-13-k4-i-hw-queues]] | 8097 | NOTES.md:300 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 0.4 | NOTES.md:284 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 0.64, 0036, 1.35, 102.9, 106.1, 28.27, 29.36 | NOTES.md:293 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 0032 | NOTES.md:298 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 0033 | NOTES.md:96 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-13-s2-s4]] | 10, 2026, 343, 343c2fbbb | NOTES.md:283 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 100.6, 100.7, 103.2, 3.008, 3.063, 78, 85, 86, 92, 99.8 | NOTES.md:286 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 15 | NOTES.md:294 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 195, 638, 748, 793 | NOTES.md:292 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 28.74, 29.46, 29.76, 3.62, 30.97, 4.82 | NOTES.md:285 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 308 | NOTES.md:287 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 3f8c8ddff, b1a203959 | NOTES.md:290 | OK |
| [[eksperymenty/2026-10-13-s2-s4]] | 720 | NOTES.md:291 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 0.5, 1.6, 2.46, 2.78, 2.98, 27, 3.31, 62, 72, 8192, 83, 90 | NOTES.md:327 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 0040, 32 | NOTES.md:321 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 0045 | NOTES.md:307 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 0047 | NOTES.md:10 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 0b5b15d17, e84abb808 | NOTES.md:326 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 1.7, 130.2, 766, 818 | NOTES.md:331 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 100.6, 97.5 | NOTES.md:330 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 1024, 15 | NOTES.md:324 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 104.2, 106.5, 27.90, 28.94 | NOTES.md:329 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 105 | NOTES.md:318 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 123, 141, 29.5, 6.6, 666, 668, 762, 767, 867, 870, 906, 913, 94, 941, 943, 956, 962 | NOTES.md:322 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 139, 204800, 236, 305 | NOTES.md:328 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 2026, 575e3d893, 6aacfea49 | NOTES.md:320 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 29.40 | NOTES.md:323 | OK |
| [[eksperymenty/2026-10-14-prefill-k5-t3]] | 89 | NOTES.md:317 | OK |
| [[eksperymenty/2026-10-14-t1-t2-draft]] | 0.65, 1.6 | NOTES.md:309 | OK |
| [[eksperymenty/2026-10-14-t1-t2-draft]] | 102.4 | NOTES.md:312 | OK |
| [[eksperymenty/2026-10-14-t1-t2-draft]] | 102.6, 28.28, 29.36 | NOTES.md:318 | OK |
| [[eksperymenty/2026-10-14-t1-t2-draft]] | 102.7, 103.0, 103.5, 104.7, 105.0, 108.4, 4 104.7, 82.6, 84.6, 88.4, 89.3, 93.5, 95.9, 96.5, 96.7 | NOTES.md:308 | OK |
| [[eksperymenty/2026-10-14-t1-t2-draft]] | 103.6, 79.8, 88.8 | NOTES.md:311 | OK |
| [[eksperymenty/2026-10-14-t1-t2-draft]] | 12, 1391, 1585, 30.9, 32.2, 34.2, 36.4, 37.2, 40.8, 41.1, 45.7, 832, 834, d3a0973ae | NOTES.md:307 | OK |
| [[eksperymenty/2026-10-14-t1-t2-draft]] | 2026, 7e9c73d8b, 87, b9b476c87 | NOTES.md:305 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 0.8, 11, 312, 800 | NOTES.md:384 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 0065, 0069, 2026 | NOTES.md:381 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 0066, 128 | NOTES.md:383 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 101.6, 109.5, 256.9, 292.9 | NOTES.md:389 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 104.6, 293, 293.2, 293.3 | NOTES.md:388 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 104.8, 113.2, 254.2, 294.3 | NOTES.md:391 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 105.4, 257.1, 292.6, 98.9 | NOTES.md:392 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 107.0, 2048, 99.3 | NOTES.md:390 | OK |
| [[eksperymenty/2026-10-15-sampler]] | 255 | STATUS-NEXT.md:21 | OK |
| [[eksperymenty/2026-10-16-bit-exact]] | 12 | 12-bit-exact-spekulacja.md:1 | OK |
| [[eksperymenty/2026-10-16-bit-exact]] | 16, 2026 | 12-bit-exact-spekulacja.md:3 | OK |
| [[eksperymenty/2026-10-16-bit-exact]] | 23335 | 12-bit-exact-spekulacja.md:24 | OK |
| [[eksperymenty/2026-10-16-bit-exact]] | 6f14e814, c4708318 | 12-bit-exact-spekulacja.md:8 | OK |
| [[eksperymenty/2026-10-16-kampania-nvidia]] | 19253 | summary.txt:4 | OK |
| [[eksperymenty/2026-10-16-kampania-nvidia]] | 2.5 | PLAN-TESTOW.md:5 | OK |
| [[eksperymenty/2026-10-16-kampania-nvidia]] | 2026 | PLAN-TESTOW.md:3 | OK |
| [[eksperymenty/2026-10-16-kampania-nvidia]] | 3060 | PLAN-TESTOW.md:91 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-16-kampania-nvidia]] | 3090 | PLAN-TESTOW.md:89 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-16-kampania-nvidia]] | 31 | PLAN-TESTOW.md:58 | OK |
| [[eksperymenty/2026-10-16-kampania-nvidia]] | 32 | PLAN-TESTOW.md:154 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/2026-10-16-kampania-nvidia]] | 5060 | PLAN-TESTOW.md:159 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 0006 | REBASE.md:17 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 0010, 10 | REBASE.md:15 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 0018 | REBASE.md:24 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 07, 29274 | REBASE.md:133 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 13 | REBASE.md:182 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 141, 60, 620, 620d2225c, e60eff95f | REBASE.md:3 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 1bb2b9fcb | REBASE.md:115 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 20, 39 | REBASE.md:140 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 2026 | git:1 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 29 | REBASE.md:25 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 29353 | REBASE.md:122 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 30257 | REBASE.md:146 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 33, 38 | REBASE.md:169 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 46 | REBASE.md:26 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 59 | REBASE.md:98 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 69, 8c942e5a9 | REBASE.md:5 | OK |
| [[eksperymenty/2026-10-16-rebase-v070]] | 70 | REBASE.md:1 | OK |
| [[eksperymenty/lfm-baza]] | 1.3, 2.69, 3.1, 3.5, 3.7, 3.8, 5.05, 680, 71, 721 | NOTES.md:340 | OK |
| [[eksperymenty/lfm-baza]] | 1.7 | NOTES.md:331 | OK |
| [[eksperymenty/lfm-baza]] | 1.8, 1.9, 500 | NOTES.md:338 | OK |
| [[eksperymenty/lfm-baza]] | 131072, 17, 17.8 | NOTES.md:334 | OK |
| [[eksperymenty/lfm-baza]] | 153, 168, 172, 174, 198, 2768, 29.7, 3709, 5172, 5805, 6.7, 6124, 95 | NOTES.md:336 | OK |
| [[eksperymenty/lfm-baza]] | 169.3, 198.3, 6107, 6180, e60eff95f | NOTES.md:339 | OK |
| [[eksperymenty/lfm-baza]] | 173, 5.78 | NOTES.md:335 | OK |
| [[eksperymenty/lfm-baza]] | 2.5, 2026 | NOTES.md:333 | OK |
| [[eksperymenty/lfm-runda-1]] | 0048, 0052, 2026 | NOTES.md:343 | OK |
| [[eksperymenty/lfm-runda-1]] | 0049, 4.979, 5.067, 682, 720 | NOTES.md:346 | OK |
| [[eksperymenty/lfm-runda-1]] | 0050, 4.800, 595 | NOTES.md:347 | OK |
| [[eksperymenty/lfm-runda-1]] | 0051, 4.642, 4.817, 521 | NOTES.md:348 | OK |
| [[eksperymenty/lfm-runda-1]] | 1.05, 5.11, 5.79 | NOTES.md:345 | OK |
| [[eksperymenty/lfm-runda-1]] | 172.9, 197.4, 217, 218.6, 219, 220.4, 26, 29.12, 29.17, 4.536, e84abb808 | NOTES.md:350 | OK |
| [[eksperymenty/lfm-runda-1]] | 4.474, 4.490 | NOTES.md:351 | OK |
| [[eksperymenty/lfm-runda-1]] | 4.509, 4.610 | NOTES.md:349 | OK |
| [[eksperymenty/lfm-runda-2]] | 0.5, 0.8, 2.53 | NOTES.md:358 | OK |
| [[eksperymenty/lfm-runda-2]] | 0053, 0054, 2026 | NOTES.md:353 | OK |
| [[eksperymenty/lfm-runda-2]] | 0055 | NOTES.md:362 | OK |
| [[eksperymenty/lfm-runda-2]] | 12.7, 131, 144, 18.6, 187, 19.3, 2.6, 30.1, 32, 5.0, 98 | NOTES.md:354 | OK |
| [[eksperymenty/lfm-runda-2]] | 217 | NOTES.md:350 | OK |
| [[eksperymenty/lfm-runda-2]] | 221.3, 223, 238, 243, 244.1, 2c7ee8a2, 3000, 4.097, 4.519, 64, 6f14e814, bcdf324d3, c4708318 | NOTES.md:357 | OK |
| [[eksperymenty/lfm-runda-2]] | 24.3, 27.2 | NOTES.md:359 | OK |
| [[eksperymenty/lfm-runda-2]] | 4.100, 4.231, 416 | NOTES.md:356 | OK |
| [[eksperymenty/lfm-runda-2]] | 4.246, 4.451, 445, 521 | NOTES.md:355 | OK |
| [[eksperymenty/lfm-runda-3]] | 0 241.1, 152.4, 191.4, 205.4, 231.0, 237, 241.1, 243, 25.6, 251, 252, 262.1, 305, 416, 56, 5909, 5909da1f1, 894, 894e56e4 | NOTES.md:368 | OK |
| [[eksperymenty/lfm-runda-3]] | 0.044171, 0.044196, 0.128, 16, 32, 4.099, 4.121, 4.526, 4.875, 5.462, 6.561, 64, 85.2, 92.25, 92.35, 98 | NOTES.md:363 | OK |
| [[eksperymenty/lfm-runda-3]] | 0055, 0059, 2026 | NOTES.md:362 | OK |
| [[eksperymenty/lfm-runda-3]] | 0056, 3.973, 4.070 | NOTES.md:364 | OK |
| [[eksperymenty/lfm-runda-3]] | 0057, 3.907, 4.043 | NOTES.md:365 | OK |
| [[eksperymenty/lfm-runda-3]] | 0058, 3.879, 3.928 | NOTES.md:366 | OK |
| [[eksperymenty/lfm-runda-3]] | 12, 3.806, 3.840 | NOTES.md:367 | OK |
| [[eksperymenty/lfm-runda-3]] | 12.9, 13, 14.4 | NOTES.md:369 | OK |
| [[eksperymenty/lfm-runda-3]] | 6.3 | NOTES.md:370 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 0.5, 0.9 | NOTES.md:379 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 0060, 0064, 2026 | NOTES.md:372 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 0061, 0062, 0063, 3.402, 3.424, 3.458, 3.706, 3.887, 3.933 | NOTES.md:374 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 101.72, 108.82, 27.812, 29.218 | lfm-decode-round4.md:13 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 103.7, 108.8, 259.3, 27.80, 29.16, 293.6 | NOTES.md:375 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 193.40, 212.95, 98304 | lfm-decode-round4.md:11 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 2.75, 20 | NOTES.md:373 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 258.48, 294.84 | lfm-decode-round4.md:10 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 259.13, 259.31, 293.43, 293.75 | lfm-decode-round4.md:12 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 270 | NOTES.md:377 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 3072 | NOTES.md:378 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | 9d493cf6e | lfm-decode-round4.md:3 | OK |
| [[eksperymenty/lfm-runda-4-pm4]] | e41c2330e | lfm-decode-round4.md:6 | OK |
| [[eksperymenty/qwen-runda-5]] | 0 109 | STATUS-NEXT.md:10 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/qwen-runda-5]] | 0.3 | qwen-round5.md:44 | OK |
| [[eksperymenty/qwen-runda-5]] | 00, 02, 15, 2026, 45 | qwen-round5.md:7 | OK |
| [[eksperymenty/qwen-runda-5]] | 0070 | qwen-round5.md:43 | OK |
| [[eksperymenty/qwen-runda-5]] | 0b7b073b, 58, 58e578967, c4708318 | qwen-round5.md:11 | OK |
| [[eksperymenty/qwen-runda-5]] | 104.8, 38.3, 44.2, 89.7 | qwen-round5.md:26 | OK |
| [[eksperymenty/qwen-runda-5]] | 1065, 1091, 2.6 | qwen-round5.md:18 | OK |
| [[eksperymenty/qwen-runda-5]] | 11 | qwen-round5.md:21 | OK |
| [[eksperymenty/qwen-runda-5]] | 16 | qwen-round5.md:25 | OK |
| [[eksperymenty/qwen-runda-5]] | 2 106 | ręcznie | OK: artefakt parsera („2” i „1066” osobno, oba w QWEN5-ROUND5.md:18) |
| [[eksperymenty/qwen-runda-5]] | 2.5 | qwen-round5.md:27 | OK |
| [[eksperymenty/qwen-runda-5]] | 2aa6999ed | qwen-round5.md:19 | OK |
| [[eksperymenty/qwen-runda-5]] | 318 | STATUS-NEXT.md:28 | OK |
| [[eksperymenty/qwen-runda-5]] | 56 | qwen-round5.md:15 | OK |
| [[eksperymenty/qwen-runda-5]] | 5b1fdbc2f | qwen-round5.md:14 | OK |
| [[eksperymenty/qwen-runda-5]] | 66 | qwen-round5.md:22 | OK |
| [[eksperymenty/qwen-runda-5]] | 83, 94 | qwen-round5.md:13 | OK |
| [[eksperymenty/qwen-runda-5]] | a6f218d0e | qwen-round5.md:17 | OK |
| [[eksperymenty/qwen-runda-5]] | bbac7d7ae | qwen-round5.md:61 | OK |
| [[eksperymenty/qwen-runda-5]] | c36fd2c87 | qwen-round5.md:1 | OK |
| [[eksperymenty/runda-6]] | 0.15, 0.7, 67 | NOTES.md:398 | OK |
| [[eksperymenty/runda-6]] | 0.3 | STATUS-NEXT.md:29 | OK |
| [[eksperymenty/runda-6]] | 0070, 70, f61994f58 | STATUS-NEXT.md:5 | OK |
| [[eksperymenty/runda-6]] | 0d89ce56c, b4e819237 | STATUS-NEXT.md:35 | OK |
| [[eksperymenty/runda-6]] | 1.9, 1099.5, 1123.2 | NOTES.md:397 | OK |
| [[eksperymenty/runda-6]] | 2.2 | STATUS-NEXT.md:3 | OK |
| [[eksperymenty/runda-6]] | 2026 | STATUS-NEXT.md:1 | OK |
| [[eksperymenty/runda-6]] | 4db68c6ab | test-tooling.md:8 | OK |
| [[eksperymenty/runda-6]] | ae1ef6a97 | STATUS-NEXT.md:36 | OK |
| [[eksperymenty/stan-2026-10-15]] | 07 | 07-nasze-metody-uogolnienie.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[eksperymenty/stan-2026-10-15]] | 109.0, 1115, 27.74, 43.2 | STATUS-NEXT.md:10 | OK |
| [[eksperymenty/stan-2026-10-15]] | 1109, 115.5, 26.68, 44.0 | STATUS-NEXT.md:11 | OK |
| [[eksperymenty/stan-2026-10-15]] | 128, 4096 | STATUS-NEXT.md:7 | OK |
| [[eksperymenty/stan-2026-10-15]] | 14, 6f14e814, 894, 894e56e4, c4708318 | STATUS-NEXT.md:15 | OK |
| [[eksperymenty/stan-2026-10-15]] | 2026 | STATUS-NEXT.md:6 | OK |
| [[eksperymenty/stan-2026-10-15]] | 264.3, 267.3, 3.74, 6291 | STATUS-NEXT.md:13 | OK |
| [[eksperymenty/stan-2026-10-15]] | 27.80 | 07-nasze-metody-uogolnienie.md:171 | OK |
| [[eksperymenty/stan-2026-10-15]] | 28.94 | 07-nasze-metody-uogolnienie.md:170 | OK |
| [[eksperymenty/stan-2026-10-15]] | 289.7, 293.7, 3.41, 6175 | STATUS-NEXT.md:12 | OK |
| [[eksperymenty/stan-2026-10-15]] | 29.36 | 07-nasze-metody-uogolnienie.md:169 | OK |
| [[eksperymenty/stan-2026-10-15]] | 29.76 | 07-nasze-metody-uogolnienie.md:168 | OK |
| [[eksperymenty/stan-2026-10-15]] | 30.97 | 07-nasze-metody-uogolnienie.md:167 | OK |
| [[eksperymenty/stan-2026-10-15]] | 32.14 | 07-nasze-metody-uogolnienie.md:166 | OK |
| [[eksperymenty/stan-2026-10-15]] | 33.17 | 07-nasze-metody-uogolnienie.md:165 | OK |
| [[eksperymenty/stan-2026-10-15]] | 35.67 | 07-nasze-metody-uogolnienie.md:164 | OK |
| [[eksperymenty/stan-2026-10-15]] | 36.38 | 07-nasze-metody-uogolnienie.md:163 | OK |
| [[eksperymenty/stan-2026-10-15]] | 37.71 | 07-nasze-metody-uogolnienie.md:162 | OK |
| [[eksperymenty/stan-2026-10-15]] | 41.7 | 07-nasze-metody-uogolnienie.md:161 | OK |
| [[eksperymenty/stan-2026-10-15]] | 70, f61994f58 | STATUS-NEXT.md:5 | OK |
| [[karty/arc-b580-i-mac]] | 0.22, 24 | PLAN.md:295 | OK |
| [[karty/arc-b580-i-mac]] | 0.49, 64 | 05-chmura-gpu-do-testow.md:29 | OK |
| [[karty/arc-b580-i-mac]] | 07 | PLAN.md:20 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/arc-b580-i-mac]] | 1.97 | 05-chmura-gpu-do-testow.md:121 | OK |
| [[karty/arc-b580-i-mac]] | 12 | PLAN.md:288 | OK |
| [[karty/arc-b580-i-mac]] | 129, 179, 70 | 05-chmura-gpu-do-testow.md:26 | OK |
| [[karty/arc-b580-i-mac]] | 149 | 05-chmura-gpu-do-testow.md:28 | OK |
| [[karty/arc-b580-i-mac]] | 16 | PLAN.md:289 | OK |
| [[karty/arc-b580-i-mac]] | 270 | PLAN.md:291 | OK |
| [[karty/arc-b580-i-mac]] | 370 | 05-chmura-gpu-do-testow.md:241 | OK |
| [[karty/arc-b580-i-mac]] | 5.2 | PLAN.md:30 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/arc-b580-i-mac]] | 650, 799 | 05-chmura-gpu-do-testow.md:242 | OK |
| [[karty/arc-b580-i-mac]] | 800 | PLAN.md:292 | OK |
| [[karty/inne-karty-nvidia]] | 0.153, 4060 | 05-chmura-gpu-do-testow.md:100 | OK |
| [[karty/inne-karty-nvidia]] | 0.176, 4070 | 05-chmura-gpu-do-testow.md:101 | OK |
| [[karty/inne-karty-nvidia]] | 0.294 | 05-chmura-gpu-do-testow.md:105 | OK |
| [[karty/inne-karty-nvidia]] | 0.40, 2.11, 2.85, 6.15 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[karty/inne-karty-nvidia]] | 0.507, 0.89 | 05-chmura-gpu-do-testow.md:103 | OK |
| [[karty/inne-karty-nvidia]] | 0.734, 1.19, 32 | 05-chmura-gpu-do-testow.md:108 | OK |
| [[karty/inne-karty-nvidia]] | 05, 5.2 | PLAN.md:281 | OK |
| [[karty/inne-karty-nvidia]] | 09 | 05-chmura-gpu-do-testow.md:21 | OK |
| [[karty/inne-karty-nvidia]] | 12 | 05-chmura-gpu-do-testow.md:98 | OK |
| [[karty/inne-karty-nvidia]] | 152, 296, 71, 96 | issues.md:34 | OK |
| [[karty/inne-karty-nvidia]] | 16 | 05-chmura-gpu-do-testow.md:17 | OK |
| [[karty/inne-karty-nvidia]] | 2,185 | 05-chmura-gpu-do-testow.md:235 | OK |
| [[karty/inne-karty-nvidia]] | 2.1, 358, 57, 65, 76 | spec-host.md:156 | OK |
| [[karty/inne-karty-nvidia]] | 2026 | 05-chmura-gpu-do-testow.md:13 | OK |
| [[karty/inne-karty-nvidia]] | 24 | 05-chmura-gpu-do-testow.md:99 | OK |
| [[karty/inne-karty-nvidia]] | 27 | 05-chmura-gpu-do-testow.md:102 | OK |
| [[karty/inne-karty-nvidia]] | 3090 | 05-chmura-gpu-do-testow.md:15 | OK |
| [[karty/inne-karty-nvidia]] | 4090 | 05-chmura-gpu-do-testow.md:16 | OK |
| [[karty/inne-karty-nvidia]] | 445, 5090 | 05-chmura-gpu-do-testow.md:19 | OK |
| [[karty/inne-karty-nvidia]] | 5070 | 05-chmura-gpu-do-testow.md:18 | OK |
| [[karty/inne-karty-nvidia]] | 7,444 | 05-chmura-gpu-do-testow.md:236 | OK |
| [[karty/inne-karty-nvidia]] | 86 | 05-chmura-gpu-do-testow.md:232 | OK |
| [[karty/mi300x]] | 05, 2026 | Optymalizacja kerneli na AMD.md:21 | OK |
| [[karty/mi300x]] | 1.75, 1.99, 2.99 | 05-chmura-gpu-do-testow.md:114 | OK |
| [[karty/mi300x]] | 100, 30 | 05-chmura-gpu-do-testow.md:39 | OK |
| [[karty/mi300x]] | 1307, 2615 | Optymalizacja kerneli na AMD.md:23 | OK |
| [[karty/mi300x]] | 2.39 | 05-chmura-gpu-do-testow.md:67 | OK |
| [[karty/mi300x]] | 256, 64 | Optymalizacja kerneli na AMD.md:15 | OK |
| [[karty/radeon-ai-pro-r9700]] | 0.471 | 05-chmura-gpu-do-testow.md:24 | OK |
| [[karty/radeon-ai-pro-r9700]] | 05 | Optymalizacja kerneli na AMD.md:86 | OK |
| [[karty/radeon-ai-pro-r9700]] | 07 | Optymalizacja kerneli na AMD.md:11 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/radeon-ai-pro-r9700]] | 138.8, 98.0 | Optymalizacja kerneli na AMD.md:80 | OK |
| [[karty/radeon-ai-pro-r9700]] | 14, 27, 29, 29.1, 42.8 | Optymalizacja kerneli na AMD.md:84 | OK |
| [[karty/radeon-ai-pro-r9700]] | 15, 152.7, 5908, 91 | Optymalizacja kerneli na AMD.md:75 | OK |
| [[karty/radeon-ai-pro-r9700]] | 199 | 05-chmura-gpu-do-testow.md:119 | OK |
| [[karty/radeon-ai-pro-r9700]] | 28 | 05-chmura-gpu-do-testow.md:364 | OK |
| [[karty/radeon-ai-pro-r9700]] | 32 | Optymalizacja kerneli na AMD.md:5 | OK |
| [[karty/radeon-ai-pro-r9700]] | 33 | rx-7900-xtx.md:135 | OK |
| [[karty/radeon-ai-pro-r9700]] | 46.0, 53.0 | Optymalizacja kerneli na AMD.md:97 | OK |
| [[karty/radeon-ai-pro-r9700]] | 60 | 05-chmura-gpu-do-testow.md:26 | OK |
| [[karty/radeon-ai-pro-r9700]] | 64, 640 | Optymalizacja kerneli na AMD.md:15 | OK |
| [[karty/radeon-ai-pro-r9700]] | 7.2 | Optymalizacja kerneli na AMD.md:77 | OK |
| [[karty/radeon-ai-pro-r9700]] | 9070 | Optymalizacja kerneli na AMD.md:7 | OK |
| [[karty/rtx-3060]] | 0.10 | PLAN-TESTOW.md:102 | OK |
| [[karty/rtx-3060]] | 0.15010, 7.6665 | summary.md:38 | OK |
| [[karty/rtx-3060]] | 10.2, 3060 | PLAN-TESTOW.md:91 | OK |
| [[karty/rtx-3060]] | 1139 | times.jsonl:2 | OK |
| [[karty/rtx-3060]] | 1151 | times.jsonl:1 | OK |
| [[karty/rtx-3060]] | 1157 | times.jsonl:3 | OK |
| [[karty/rtx-3060]] | 12 | PLAN-TESTOW.md:90 | OK |
| [[karty/rtx-3060]] | 2026, 3.66 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[karty/rtx-3060]] | 257 | PLAN.md:288 | OK |
| [[karty/rtx-3060]] | 27 | PLAN-TESTOW.md:89 | OK |
| [[karty/rtx-3060]] | 512 | PLAN-TESTOW.md:69 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/rtx-3060]] | 569.90 | summary.md:5 | OK |
| [[karty/rtx-3060]] | 573.37 | summary.md:6 | OK |
| [[karty/rtx-3060]] | 64 | summary.md:15 | OK |
| [[karty/rtx-3060]] | 8.6154 | summary.md:36 | OK |
| [[karty/rtx-3060]] | 8.6171 | summary.md:34 | OK |
| [[karty/rtx-3090]] | 0.09 | PLAN-TESTOW.md:99 | OK |
| [[karty/rtx-3090]] | 0.23 | 05-chmura-gpu-do-testow.md:15 | OK |
| [[karty/rtx-3090]] | 0.32, 7900 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[karty/rtx-3090]] | 02 | hw.json:7 | OK |
| [[karty/rtx-3090]] | 1,224 | 05-chmura-gpu-do-testow.md:233 | OK |
| [[karty/rtx-3090]] | 1360 | qwen38-27b.fork-safe.r4.jsonl:1 | OK |
| [[karty/rtx-3090]] | 1411 | qwen38-27b.base-default.r1.jsonl:1 | OK |
| [[karty/rtx-3090]] | 162 | 05-chmura-gpu-do-testow.md:99 | OK |
| [[karty/rtx-3090]] | 19253 | summary.txt:2 | OK |
| [[karty/rtx-3090]] | 2026 | 05-chmura-gpu-do-testow.md:13 | OK |
| [[karty/rtx-3090]] | 236.3, 237.5, 256.9, 258.2, 39.0, 39.4, 40.2 | ręcznie | OK: lb/*.jsonl avg_ts tg128 zaokrąglone do 0.1 (wyciąg 2026-10-16) |
| [[karty/rtx-3090]] | 24, 3090 | PLAN-TESTOW.md:89 | OK |
| [[karty/rtx-3090]] | 300 | hw.json:13 | OK |
| [[karty/rtx-3090]] | 350 | hw.json:14 | OK |
| [[karty/rtx-3090]] | 41.55, 59.8, 66.39 | 02-autotuning-i-agenci-kerneli.md:257 | OK |
| [[karty/rtx-3090]] | 615.71 | hw.json:6 | OK |
| [[karty/rtx-3090]] | 787 | times.jsonl:2 | OK |
| [[karty/rtx-3090]] | 999 | lfm25-24b-q5.fork-tuned.r3.jsonl:1 | OK |
| [[karty/rtx-5060-ti]] | 0.0005 | ręcznie | OK: tbo/summary.txt: ERR 0.000505463 / 0.000944348 > 0.000500000 (zaokrąglone) |
| [[karty/rtx-5060-ti]] | 0.165 | 05-chmura-gpu-do-testow.md:104 | OK |
| [[karty/rtx-5060-ti]] | 0053 | PLAN-TESTOW.md:154 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/rtx-5060-ti]] | 0057 | PLAN-TESTOW.md:148 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/rtx-5060-ti]] | 128 | rx-7900-xtx.md:33 | OK |
| [[karty/rtx-5060-ti]] | 16, 5060 | rx-7900-xtx.md:36 | OK |
| [[karty/rtx-5060-ti]] | 180 | gpu-monitor.csv:2 | OK |
| [[karty/rtx-5060-ti]] | 19251 | summary.txt:4 | OK |
| [[karty/rtx-5060-ti]] | 196.9, 201.2, 29.0 | ręcznie | OK: lb/*.jsonl avg_ts tg128 zaokrąglone do 0.1 (wyciąg 2026-10-16) |
| [[karty/rtx-5060-ti]] | 2026 | rx-7900-xtx.md:34 | OK |
| [[karty/rtx-5060-ti]] | 24 | rx-7900-xtx.md:43 | OK |
| [[karty/rtx-5060-ti]] | 28.6 | greedy.tsv:13 | OK |
| [[karty/rtx-5060-ti]] | 4.0 | PLAN-TESTOW.md:99 | OK |
| [[karty/rtx-5060-ti]] | 4.06 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[karty/rtx-5060-ti]] | 448 | rx-7900-xtx.md:38 | OK |
| [[karty/rtx-5060-ti]] | 474, 680 | PLAN.md:287 | OK |
| [[karty/rtx-5060-ti]] | 5.2 | PLAN.md:30 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/rtx-5060-ti]] | 503 | gpu-monitor.csv:227 | OK |
| [[karty/rtx-5060-ti]] | 580.173 | nvidia-smi-q.txt:5 | OK |
| [[karty/rx-7900-xtx]] | 0.40 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[karty/rx-7900-xtx]] | 05 | NOTES.md:229 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/rx-7900-xtx]] | 1,821, 837 | 05-chmura-gpu-do-testow.md:239 | OK |
| [[karty/rx-7900-xtx]] | 109, 109.0, 1115 | STATUS-NEXT.md:10 | OK |
| [[karty/rx-7900-xtx]] | 115.5 | STATUS-NEXT.md:11 | OK |
| [[karty/rx-7900-xtx]] | 123 | rx-7900-xtx.md:17 | OK |
| [[karty/rx-7900-xtx]] | 128, 16, 192 | rx-7900-xtx.md:13 | OK |
| [[karty/rx-7900-xtx]] | 170.1 | rx-7900-xtx.md:33 | OK |
| [[karty/rx-7900-xtx]] | 19, 51 | rx-7900-xtx.md:107 | OK |
| [[karty/rx-7900-xtx]] | 190.9 | rx-7900-xtx.md:32 | OK |
| [[karty/rx-7900-xtx]] | 2026 | rx-7900-xtx.md:3 | OK |
| [[karty/rx-7900-xtx]] | 24, 384, 960 | rx-7900-xtx.md:16 | OK |
| [[karty/rx-7900-xtx]] | 267.3 | STATUS-NEXT.md:13 | OK |
| [[karty/rx-7900-xtx]] | 285 | NOTES.md:126 | OK |
| [[karty/rx-7900-xtx]] | 293.7, 6175 | STATUS-NEXT.md:12 | OK |
| [[karty/rx-7900-xtx]] | 294 | NOTES.md:375 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/rx-7900-xtx]] | 48, 96 | rx-7900-xtx.md:11 | OK |
| [[karty/rx-7900-xtx]] | 5060 | rx-7900-xtx.md:36 | OK |
| [[karty/rx-7900-xtx]] | 64 | rx-7900-xtx.md:12 | OK |
| [[karty/rx-7900-xtx]] | 7 570 | rx-7900-xtx.md:110 | OK |
| [[karty/rx-7900-xtx]] | 70 | rx-7900-xtx.md:29 | OK |
| [[karty/rx-7900-xtx]] | 7900 | rx-7900-xtx.md:6 | OK |
| [[karty/rx-9070-xt]] | 0.070 | 05-chmura-gpu-do-testow.md:118 | OK |
| [[karty/rx-9070-xt]] | 07 | Optymalizacja kerneli na AMD.md:11 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/rx-9070-xt]] | 1,470 | 05-chmura-gpu-do-testow.md:258 | OK |
| [[karty/rx-9070-xt]] | 1.42 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[karty/rx-9070-xt]] | 10, 131.5, 2026, 5048 | Optymalizacja kerneli na AMD.md:75 | OK |
| [[karty/rx-9070-xt]] | 101.3, 137.1 | Optymalizacja kerneli na AMD.md:79 | OK |
| [[karty/rx-9070-xt]] | 16 | PLAN.md:287 | OK |
| [[karty/rx-9070-xt]] | 20, 256, 64, 640 | Optymalizacja kerneli na AMD.md:15 | OK |
| [[karty/rx-9070-xt]] | 30 | 07-nasze-metody-uogolnienie.md:391 | OK |
| [[karty/rx-9070-xt]] | 5.2 | PLAN.md:30 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/rx-9070-xt]] | 60 | 05-chmura-gpu-do-testow.md:120 | OK |
| [[karty/rx-9070-xt]] | 618, 753, 815 | 05-chmura-gpu-do-testow.md:240 | OK |
| [[karty/rx-9070-xt]] | 694 | PLAN.md:289 | OK |
| [[karty/rx-9070-xt]] | 7.2 | Optymalizacja kerneli na AMD.md:77 | OK |
| [[karty/rx-9070-xt]] | 9070 | Optymalizacja kerneli na AMD.md:7 | OK |
| [[karty/strix-halo]] | 0022 | 05-chmura-gpu-do-testow.md:28 | OK |
| [[karty/strix-halo]] | 0040, 0070, 212, 256 | Optymalizacja kerneli na AMD.md:15 | OK |
| [[karty/strix-halo]] | 0060 | 05-chmura-gpu-do-testow.md:26 | OK |
| [[karty/strix-halo]] | 08, 20.56, 24.64 | Optymalizacja kerneli na AMD.md:84 | OK |
| [[karty/strix-halo]] | 125, 1293, 53.8 | Optymalizacja kerneli na AMD.md:104 | OK |
| [[karty/strix-halo]] | 128 | Optymalizacja kerneli na AMD.md:11 | OK (inny wiersz źródła, sprawdzone) |
| [[karty/strix-halo]] | 24437, 41 | Optymalizacja kerneli na AMD.md:88 | OK |
| [[karty/strix-halo]] | 299 | 05-chmura-gpu-do-testow.md:138 | OK |
| [[karty/strix-halo]] | 395 | 05-chmura-gpu-do-testow.md:25 | OK |
| [[karty/strix-halo]] | 8060 | Optymalizacja kerneli na AMD.md:7 | OK |
| [[kernele/argmax-dpp]] | 0020 | 07-nasze-metody-uogolnienie.md:104 | OK |
| [[kernele/argmax-dpp]] | 0026 | 07-nasze-metody-uogolnienie.md:99 | OK |
| [[kernele/argmax-dpp]] | 08 | NOTES.md:373 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/argmax-dpp]] | 16, 16.8, 4.3 | NOTES.md:262 | OK |
| [[kernele/argmax-dpp]] | 2026 | NOTES.md:109 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/argmax-dpp]] | 32.14 | 07-nasze-metody-uogolnienie.md:102 | OK |
| [[kernele/argmax-dpp]] | 33.17 | NOTES.md:265 | OK |
| [[kernele/attn-prep-fwht]] | 0.207 | 07-nasze-metody-uogolnienie.md:183 | OK |
| [[kernele/attn-prep-fwht]] | 0019, 12, 2026 | NOTES.md:228 | OK |
| [[kernele/attn-prep-fwht]] | 0055 | NOTES.md:362 | OK |
| [[kernele/attn-prep-fwht]] | 0057, 3.907, 4.043 | NOTES.md:365 | OK |
| [[kernele/attn-prep-fwht]] | 0058, 3.879, 3.928 | NOTES.md:366 | OK |
| [[kernele/attn-prep-fwht]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/attn-prep-fwht]] | 1004, 31.17 | 07-nasze-metody-uogolnienie.md:92 | OK |
| [[kernele/attn-prep-fwht]] | 31.01 | 07-nasze-metody-uogolnienie.md:94 | OK |
| [[kernele/attn-prep-fwht]] | 64 | NOTES.md:363 | OK |
| [[kernele/attn-prep-fwht]] | 972 | NOTES.md:230 | OK |
| [[kernele/cache-q8-1]] | 0003, 1308 | NOTES.md:230 | OK |
| [[kernele/cache-q8-1]] | 0015, 1052, 37.04, 37.73 | 07-nasze-metody-uogolnienie.md:90 | OK |
| [[kernele/cache-q8-1]] | 0049, 4.979, 5.067, 682, 720 | NOTES.md:346 | OK |
| [[kernele/cache-q8-1]] | 0056, 3.973, 4.070 | NOTES.md:364 | OK |
| [[kernele/cache-q8-1]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/cache-q8-1]] | 3a05006a0 | NOTES.md:89 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/clamp-q8-1]] | 0023, 23606 | 07-nasze-metody-uogolnienie.md:98 | OK |
| [[kernele/clamp-q8-1]] | 07 | README.md:68 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/clamp-q8-1]] | 2026 | NOTES.md:258 | OK |
| [[kernele/clamp-q8-1]] | 2444 | NOTES.md:78 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/clamp-q8-1]] | 4017 | NOTES.md:195 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/clamp-q8-1]] | 53 | README.md:163 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/clamp-q8-1]] | 606 | README.md:21 | OK |
| [[kernele/clamp-q8-1]] | 65504 | NOTES.md:259 | OK |
| [[kernele/clamp-q8-1]] | 9f83f1f81 | NOTES.md:241 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/conv-lag]] | 0014, 12, 2026 | NOTES.md:221 | OK |
| [[kernele/conv-lag]] | 0038 | 07-nasze-metody-uogolnienie.md:113 | OK |
| [[kernele/conv-lag]] | 102.6, 28.28, 29.36 | NOTES.md:318 | OK |
| [[kernele/conv-lag]] | 105.0 | NOTES.md:308 | OK |
| [[kernele/conv-lag]] | 1391, 1585, 30.9, 32.2, 34.2, 36.4, 37.2, 40.8, 41.1, 45.7, 832, 834 | NOTES.md:307 | OK |
| [[kernele/conv-lag]] | 470 | NOTES.md:299 | OK |
| [[kernele/conv-lag]] | b9b476c87 | NOTES.md:305 | OK |
| [[kernele/conv-lag]] | d3a0973ae | NOTES.md:297 | OK |
| [[kernele/fattn-kvq]] | 0.044171, 0.044196, 128.7, 223.5, 5.462, 6.561 | NOTES.md:363 | OK |
| [[kernele/fattn-kvq]] | 0011 | NOTES.md:179 | OK |
| [[kernele/fattn-kvq]] | 0055 | NOTES.md:362 | OK |
| [[kernele/fattn-kvq]] | 0058, 3.879, 3.928 | NOTES.md:366 | OK |
| [[kernele/fattn-kvq]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/fattn-kvq]] | 120.6 | NOTES.md:187 | OK |
| [[kernele/fattn-kvq]] | 2026 | NOTES.md:182 | OK |
| [[kernele/fattn-kvq]] | 36.7, 68.2 | NOTES.md:195 | OK |
| [[kernele/fattn-kvq]] | 40, 40c9bacdc | NOTES.md:193 | OK |
| [[kernele/fattn-kvq]] | 43.0, 65, 70.9 | NOTES.md:202 | OK |
| [[kernele/fattn-kvq]] | 64 | NOTES.md:357 | OK |
| [[kernele/fattn-kvq]] | 94 | NOTES.md:180 | OK |
| [[kernele/fattn-kvq]] | 98 | NOTES.md:354 | OK |
| [[kernele/fuzje-lfm-moe]] | 0.565, 34 | 07-nasze-metody-uogolnienie.md:180 | OK |
| [[kernele/fuzje-lfm-moe]] | 0049, 4.979, 5.067, 682, 720 | NOTES.md:346 | OK |
| [[kernele/fuzje-lfm-moe]] | 0051, 4.642, 4.817, 521 | NOTES.md:348 | OK |
| [[kernele/fuzje-lfm-moe]] | 0053 | NOTES.md:353 | OK |
| [[kernele/fuzje-lfm-moe]] | 0056, 3.973, 4.070 | NOTES.md:364 | OK |
| [[kernele/fuzje-lfm-moe]] | 07 | NOTES.md:338 | OK |
| [[kernele/fuzje-lfm-moe]] | 13 | 07-nasze-metody-uogolnienie.md:123 | OK |
| [[kernele/fuzje-lfm-moe]] | 2.5, 3.5, 3.7, 38, 71, 721 | NOTES.md:340 | OK |
| [[kernele/fuzje-lfm-moe]] | 2026 | NOTES.md:343 | OK |
| [[kernele/fuzje-lfm-moe]] | 4.246, 4.451, 445 | NOTES.md:355 | OK |
| [[kernele/fuzje-lfm-moe]] | 56 | NOTES.md:160 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/fuzje-lfm-moe]] | 64 | NOTES.md:337 | OK |
| [[kernele/fuzje-weryfikacji]] | 0.0067, 0.0098, 6.182, 6.191 | NOTES.md:225 | OK |
| [[kernele/fuzje-weryfikacji]] | 0012, 0014, 2026, 6da87d000, 92, 92b14b8b2, a180bea04 | NOTES.md:221 | OK |
| [[kernele/fuzje-weryfikacji]] | 0013 | 07-nasze-metody-uogolnienie.md:87 | OK |
| [[kernele/fuzje-weryfikacji]] | 0015 | 07-nasze-metody-uogolnienie.md:90 | OK |
| [[kernele/fuzje-weryfikacji]] | 0018 | 07-nasze-metody-uogolnienie.md:84 | OK |
| [[kernele/fuzje-weryfikacji]] | 0019, b1f8c19ac, b9db88004 | NOTES.md:228 | OK |
| [[kernele/fuzje-weryfikacji]] | 1308, 2156, 4.30, 6.99 | NOTES.md:223 | OK |
| [[kernele/fuzje-weryfikacji]] | 3.23, 972 | NOTES.md:230 | OK |
| [[kernele/fuzje-weryfikacji]] | 30103, 6.1, 9.05 | NOTES.md:229 | OK |
| [[kernele/fuzje-weryfikacji]] | 34.52, 36.38, 86.4, 88.5 | NOTES.md:231 | OK |
| [[kernele/fuzje-weryfikacji]] | 35.83, 37.71, 39.6, 41.7, 74.8, 78.5, 83.3, 85.3 | NOTES.md:224 | OK |
| [[kernele/gdn-fast]] | 0.1 | gdn-bitwise.md:183 | OK |
| [[kernele/gdn-fast]] | 0.15, 0.7 | gdn-bitwise.md:182 | OK |
| [[kernele/gdn-fast]] | 0b7b073b, 58, 58e578967 | qwen-round5.md:11 | OK |
| [[kernele/gdn-fast]] | 0d89ce56c, 16 | gdn-bitwise.md:14 | OK |
| [[kernele/gdn-fast]] | 1.5, 14.27, 14.49 | gdn-bitwise.md:180 | OK |
| [[kernele/gdn-fast]] | 120 | gdn-bitwise.md:123 | OK |
| [[kernele/gdn-fast]] | 132.1, 153.7 | gdn-bitwise.md:181 | OK |
| [[kernele/gdn-fast]] | 14, c4708318 | gdn-bitwise.md:179 | OK |
| [[kernele/gdn-fast]] | 2026 | gdn-bitwise.md:176 | OK |
| [[kernele/gdn-fast]] | 379 | gdn-bitwise.md:20 | OK |
| [[kernele/gdn-fast]] | 423, 476 | gdn-bitwise.md:100 | OK |
| [[kernele/gdn-fast]] | 5b1fdbc2f | qwen-round5.md:14 | OK |
| [[kernele/gdn-fast]] | 67 | gdn-bitwise.md:177 | OK |
| [[kernele/gdn-fast]] | 83, 94 | qwen-round5.md:13 | OK |
| [[kernele/gdn-fast]] | b4e819237 | gdn-bitwise.md:7 | OK |
| [[kernele/gdn-fuzje-k2]] | 0.33, 0028 | 07-nasze-metody-uogolnienie.md:103 | OK |
| [[kernele/gdn-fuzje-k2]] | 0027 | 07-nasze-metody-uogolnienie.md:102 | OK |
| [[kernele/gdn-fuzje-k2]] | 0045, 1082, 1108, 2.4 | 07-nasze-metody-uogolnienie.md:120 | OK |
| [[kernele/gdn-fuzje-k2]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/gdn-fuzje-k2]] | 1.84, 1.87, 2.68 | NOTES.md:263 | OK |
| [[kernele/gdn-fuzje-k2]] | 2026 | NOTES.md:320 | OK |
| [[kernele/gdn-fuzje-k2]] | 32.17 | NOTES.md:265 | OK |
| [[kernele/gdn-fuzje-k2]] | 32.50 | NOTES.md:266 | OK |
| [[kernele/gdn-fuzje-k2]] | 4.68, 4.90, 5.54 | NOTES.md:264 | OK |
| [[kernele/gdn-replay]] | 0.64, 0035, 0036, 1.35, 102.9, 106.1, 28.27, 29.36 | NOTES.md:293 | OK |
| [[kernele/gdn-replay]] | 0033 | 07-nasze-metody-uogolnienie.md:108 | OK |
| [[kernele/gdn-replay]] | 0034 | 07-nasze-metody-uogolnienie.md:109 | OK |
| [[kernele/gdn-replay]] | 0038 | 07-nasze-metody-uogolnienie.md:113 | OK |
| [[kernele/gdn-replay]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/gdn-replay]] | 10, 2026, 3f8c8ddff, b1a203959 | NOTES.md:290 | OK |
| [[kernele/gdn-replay]] | 15, 48 | NOTES.md:294 | OK |
| [[kernele/gdn-replay]] | 195, 638, 748, 793 | NOTES.md:292 | OK |
| [[kernele/gdn-replay]] | 661 | 07-nasze-metody-uogolnienie.md:110 | OK |
| [[kernele/gdn-replay]] | 720 | NOTES.md:291 | OK |
| [[kernele/lfm-shortconv]] | 0.366, 22 | 07-nasze-metody-uogolnienie.md:182 | OK |
| [[kernele/lfm-shortconv]] | 0050, 4.800, 595 | NOTES.md:347 | OK |
| [[kernele/lfm-shortconv]] | 0054 | NOTES.md:353 | OK |
| [[kernele/lfm-shortconv]] | 0062, 3.402, 3.458 | NOTES.md:374 | OK |
| [[kernele/lfm-shortconv]] | 08 | NOTES.md:373 | OK |
| [[kernele/lfm-shortconv]] | 12.2, 13.6, 14.6, 2560, 3072 | NOTES.md:378 | OK |
| [[kernele/lfm-shortconv]] | 30, 32 | NOTES.md:337 | OK |
| [[kernele/lfm-shortconv]] | 4.100, 4.231, 416 | NOTES.md:356 | OK |
| [[kernele/lfm-shortconv]] | 4.979 | NOTES.md:346 | OK |
| [[kernele/lfm-shortconv]] | 445 | NOTES.md:355 | OK |
| [[kernele/lfm-shortconv]] | 96 | 07-nasze-metody-uogolnienie.md:137 | OK |
| [[kernele/mmq-epilog]] | 0.3 | mmq-epilogue.md:166 | OK |
| [[kernele/mmq-epilog]] | 0070, 2026, f61994f58 | mmq-epilogue.md:159 | OK |
| [[kernele/mmq-epilog]] | 1.9 | mmq-epilogue.md:165 | OK |
| [[kernele/mmq-epilog]] | 1099.5, 1123.2, 2.2 | mmq-epilogue.md:164 | OK |
| [[kernele/mmq-epilog]] | 128, 16 | mmq-epilogue.md:10 | OK |
| [[kernele/mmq-epilog]] | 178, 237, 243, 298 | mmq-epilogue.md:47 | OK |
| [[kernele/mmq-epilog]] | 19 | mmq-epilogue.md:81 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/mmq-epilog]] | 2048 | mmq-epilogue.md:161 | OK |
| [[kernele/mmq-epilog]] | 2486, 933 | mmq-epilogue.md:160 | OK |
| [[kernele/mmq-epilog]] | 48 | mmq-epilogue.md:32 | OK |
| [[kernele/mmq-epilog]] | 512 | mmq-epilogue.md:38 | OK |
| [[kernele/mmq-epilog]] | 64 | mmq-epilogue.md:11 | OK |
| [[kernele/mmq-epilog]] | 66 | NOTES.md:118 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/mmq-epilog]] | ae1ef6a97 | mmq-epilogue.md:7 | OK |
| [[kernele/mmvq-multikolumnowe]] | 0001 | NOTES.md:42 | OK |
| [[kernele/mmvq-multikolumnowe]] | 0002 | NOTES.md:35 | OK |
| [[kernele/mmvq-multikolumnowe]] | 0021 | 07-nasze-metody-uogolnienie.md:96 | OK |
| [[kernele/mmvq-multikolumnowe]] | 0022, 22.1, 24.3 | NOTES.md:245 | OK |
| [[kernele/mmvq-multikolumnowe]] | 08 | 07-nasze-metody-uogolnienie.md:97 | OK |
| [[kernele/mmvq-multikolumnowe]] | 132, 272 | NOTES.md:75 | OK |
| [[kernele/mmvq-multikolumnowe]] | 17408, 5120 | NOTES.md:67 | OK |
| [[kernele/mmvq-multikolumnowe]] | 2026, 60ce2a71f, 9f83f1f81 | NOTES.md:241 | OK |
| [[kernele/mmvq-multikolumnowe]] | 240, 340, 700 | NOTES.md:56 | OK |
| [[kernele/mmvq-multikolumnowe]] | 2444 | NOTES.md:78 | OK |
| [[kernele/mmvq-multikolumnowe]] | 296, 621 | NOTES.md:71 | OK |
| [[kernele/mmvq-multikolumnowe]] | 32 | NOTES.md:88 | OK |
| [[kernele/mmvq-multikolumnowe]] | 32.02, 33.17 | NOTES.md:255 | OK |
| [[kernele/mmvq-multikolumnowe]] | 33.79, 35.67, 88.1, 90.4 | NOTES.md:239 | OK |
| [[kernele/mmvq-multikolumnowe]] | 60, 68.6, 95 | NOTES.md:43 | OK |
| [[kernele/mmvq-multikolumnowe]] | 72, 72cfa5656, 95a0c83d6 | NOTES.md:89 | OK |
| [[kernele/mmvq-multikolumnowe]] | 7900 | NOTES.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/mmvq-multikolumnowe]] | 82.3 | NOTES.md:44 | OK |
| [[kernele/mmvq-multikolumnowe]] | 94.7, 95.4 | NOTES.md:246 | OK |
| [[kernele/mmvq-n1-wiersze]] | 0.135, 0059 | 07-nasze-metody-uogolnienie.md:184 | OK |
| [[kernele/mmvq-n1-wiersze]] | 0052, 4.509, 4.610 | NOTES.md:349 | OK |
| [[kernele/mmvq-n1-wiersze]] | 0064, 2026 | NOTES.md:372 | OK |
| [[kernele/mmvq-n1-wiersze]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/mmvq-n1-wiersze]] | 2.2 | 07-nasze-metody-uogolnienie.md:127 | OK |
| [[kernele/mmvq-n1-wiersze]] | 3.706, 3.933 | NOTES.md:374 | OK |
| [[kernele/mmvq-n1-wiersze]] | 39 | NOTES.md:135 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/mmvq-n1-wiersze]] | 6.1 | 07-nasze-metody-uogolnienie.md:139 | OK |
| [[kernele/mtp-draft-graf]] | 0.2 | NOTES.md:238 | OK |
| [[kernele/mtp-draft-graf]] | 0004, 86.4 | NOTES.md:233 | OK |
| [[kernele/mtp-draft-graf]] | 0020, 36.39, 88.0 | 07-nasze-metody-uogolnienie.md:95 | OK |
| [[kernele/mtp-draft-graf]] | 0030 | NOTES.md:274 | OK |
| [[kernele/mtp-draft-graf]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/mtp-draft-graf]] | 1.19, 104, 180, 42, 64 | NOTES.md:237 | OK |
| [[kernele/mtp-draft-graf]] | 2026, c90db29c6 | NOTES.md:236 | OK |
| [[kernele/mtp-draft-graf]] | 31.59 | 07-nasze-metody-uogolnienie.md:105 | OK |
| [[kernele/mtp-draft-graf]] | 31.89 | 07-nasze-metody-uogolnienie.md:104 | OK |
| [[kernele/mtp-draft-graf]] | 33.79, 35.67, 88.1, 90.4 | NOTES.md:239 | OK |
| [[kernele/para-mmvq]] | 0024, 0025, 0026, 911 | 07-nasze-metody-uogolnienie.md:99 | OK |
| [[kernele/para-mmvq]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/para-mmvq]] | 2026 | NOTES.md:258 | OK |
| [[kernele/para-mmvq]] | 30.68 | NOTES.md:274 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/para-mmvq]] | 32.14, 97.8 | 07-nasze-metody-uogolnienie.md:102 | OK |
| [[kernele/para-mmvq]] | 33.17, 972 | NOTES.md:265 | OK |
| [[kernele/para-mmvq]] | 99.6 | NOTES.md:266 | OK |
| [[kernele/pm4-replay]] | 0.46, 0.86 | lfm-decode-round4.md:51 | OK |
| [[kernele/pm4-replay]] | 0060, 2026 | NOTES.md:372 | OK |
| [[kernele/pm4-replay]] | 0061, 0063 | NOTES.md:374 | OK |
| [[kernele/pm4-replay]] | 103.7, 108.8, 109.9, 115.3, 259.3, 27.80, 29.16, 293.6 | NOTES.md:375 | OK |
| [[kernele/pm4-replay]] | 2.75 | lfm-decode-round4.md:57 | OK |
| [[kernele/pm4-replay]] | 20 | lfm-decode-round4.md:52 | OK |
| [[kernele/pm4-replay]] | 257.3, 292.1, 3.424, 3.887 | lfm-decode-round4.md:94 | OK |
| [[kernele/pm4-replay]] | 304 | lfm-decode-round4.md:92 | OK |
| [[kernele/prefill-mmq-fa]] | 0.0135 | 07-nasze-metody-uogolnienie.md:118 | OK |
| [[kernele/prefill-mmq-fa]] | 0040, 249, 32, 48, 5120, 932 | NOTES.md:321 | OK |
| [[kernele/prefill-mmq-fa]] | 0041, 897, 936 | 07-nasze-metody-uogolnienie.md:116 | OK |
| [[kernele/prefill-mmq-fa]] | 0042, 0043, 256, 3.42, 4.36, 40.2, 49.0 | 07-nasze-metody-uogolnienie.md:117 | OK |
| [[kernele/prefill-mmq-fa]] | 0044 | 07-nasze-metody-uogolnienie.md:119 | OK |
| [[kernele/prefill-mmq-fa]] | 0045, 1082, 1108, 2.4 | 07-nasze-metody-uogolnienie.md:120 | OK |
| [[kernele/prefill-mmq-fa]] | 1024, 15 | NOTES.md:324 | OK |
| [[kernele/prefill-mmq-fa]] | 1059, 1080 | 07-nasze-metody-uogolnienie.md:115 | OK |
| [[kernele/prefill-mmq-fa]] | 123, 141, 29.5, 6.6, 666, 668, 762, 767, 867, 870, 906, 913, 94, 941, 943, 956, 962 | NOTES.md:322 | OK |
| [[kernele/prefill-mmq-fa]] | 2026 | NOTES.md:320 | OK |
| [[kernele/rmsnorm-dpp]] | 0025 | 07-nasze-metody-uogolnienie.md:99 | OK |
| [[kernele/rmsnorm-dpp]] | 2000 | NOTES.md:93 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/rmsnorm-dpp]] | 2026 | NOTES.md:258 | OK |
| [[kernele/rmsnorm-dpp]] | 2048, 8192 | 07-nasze-metody-uogolnienie.md:100 | OK |
| [[kernele/rmsnorm-dpp]] | 4.51, 5.87, 5120 | NOTES.md:261 | OK |
| [[kernele/sampler-fast-path]] | 0031 | 07-nasze-metody-uogolnienie.md:104 | OK |
| [[kernele/sampler-fast-path]] | 0048 | NOTES.md:343 | OK |
| [[kernele/sampler-fast-path]] | 0065 | NOTES.md:281 | OK |
| [[kernele/sampler-fast-path]] | 0066, 64 | NOTES.md:383 | OK |
| [[kernele/sampler-fast-path]] | 0069 | NOTES.md:381 | OK |
| [[kernele/sampler-fast-path]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/sampler-fast-path]] | 1.05, 128, 5.11, 5.79 | NOTES.md:345 | OK |
| [[kernele/sampler-fast-path]] | 104.8, 113.2, 254.2, 294.3 | NOTES.md:391 | OK |
| [[kernele/sampler-fast-path]] | 107.0, 99.3 | NOTES.md:390 | OK |
| [[kernele/sampler-fast-path]] | 140, 645 | NOTES.md:278 | OK |
| [[kernele/sampler-fast-path]] | 2026 | NOTES.md:276 | OK |
| [[kernele/sampler-fast-path]] | 248 | NOTES.md:277 | OK |
| [[kernele/sampler-fast-path]] | 256.9, 292.9 | NOTES.md:389 | OK |
| [[kernele/sampler-fast-path]] | 312 | NOTES.md:384 | OK |
| [[kernele/vulkan-mmvq]] | 0.0036, 0.0042, 512 | NOTES.md:167 | OK |
| [[kernele/vulkan-mmvq]] | 0.3, 39.92, 4.8, 41.46, 41.93, 43.73, 5.2 | NOTES.md:166 | OK |
| [[kernele/vulkan-mmvq]] | 0.5, 13.6, 48, 8.6 | NOTES.md:164 | OK |
| [[kernele/vulkan-mmvq]] | 0006, 0008 | NOTES.md:160 | OK |
| [[kernele/vulkan-mmvq]] | 0007 | NOTES.md:163 | OK |
| [[kernele/vulkan-mmvq]] | 0009, 1.3, 1.9, 614, 690 | NOTES.md:165 | OK |
| [[kernele/vulkan-mmvq]] | 0010, 2026 | NOTES.md:162 | OK |
| [[kernele/vulkan-mmvq]] | 1024, 18.1, 4096, 9.7 | 07-nasze-metody-uogolnienie.md:84 | OK |
| [[kernele/vulkan-mmvq]] | 256 | 07-nasze-metody-uogolnienie.md:81 | OK |
| [[kernele/wmma-small-n]] | 0.0006, 0.0122, 0.0124, 0.0128, 0037 | 07-nasze-metody-uogolnienie.md:112 | OK |
| [[kernele/wmma-small-n]] | 0.43, 32.1, 35.0, 49.2, 51.0 | NOTES.md:298 | OK |
| [[kernele/wmma-small-n]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[kernele/wmma-small-n]] | 16, 2026, d3a0973ae | NOTES.md:297 | OK |
| [[kernele/wmma-small-n]] | 4 101.7, 470, 5 105.4 | NOTES.md:299 | OK |
| [[latki/klasyfikacja-latek]] | 0001 | 07-nasze-metody-uogolnienie.md:5 | OK |
| [[latki/klasyfikacja-latek]] | 0006, 0008, 0011, 0013, 0037, 0055, 45, 70 | 07-nasze-metody-uogolnienie.md:7 | OK |
| [[latki/klasyfikacja-latek]] | 0009 | 07-nasze-metody-uogolnienie.md:26 | OK |
| [[latki/klasyfikacja-latek]] | 07, 28, 3.40, 34, 5.07 | 07-nasze-metody-uogolnienie.md:24 | OK |
| [[latki/klasyfikacja-latek]] | 08 | 07-nasze-metody-uogolnienie.md:97 | OK (inny wiersz źródła, sprawdzone) |
| [[latki/klasyfikacja-latek]] | 10 | 07-nasze-metody-uogolnienie.md:15 | OK |
| [[latki/klasyfikacja-latek]] | 12 | 07-nasze-metody-uogolnienie.md:14 | OK |
| [[latki/klasyfikacja-latek]] | 18 | 07-nasze-metody-uogolnienie.md:13 | OK |
| [[latki/klasyfikacja-latek]] | 22 | 07-nasze-metody-uogolnienie.md:12 | OK |
| [[latki/klasyfikacja-latek]] | 27.74, 30, 41.7, 48 | 07-nasze-metody-uogolnienie.md:23 | OK |
| [[latki/klasyfikacja-latek]] | 38 | 07-nasze-metody-uogolnienie.md:27 | OK |
| [[latki/latki-do-upstreamu]] | 0003 | 07-nasze-metody-uogolnienie.md:436 | OK |
| [[latki/latki-do-upstreamu]] | 0015 | 07-nasze-metody-uogolnienie.md:442 | OK |
| [[latki/latki-do-upstreamu]] | 0023 | 07-nasze-metody-uogolnienie.md:440 | OK |
| [[latki/latki-do-upstreamu]] | 0029, 0059 | 07-nasze-metody-uogolnienie.md:441 | OK |
| [[latki/latki-do-upstreamu]] | 0031, 0048, 0066, 0069 | 07-nasze-metody-uogolnienie.md:438 | OK |
| [[latki/latki-do-upstreamu]] | 0047 | 07-nasze-metody-uogolnienie.md:439 | OK |
| [[latki/latki-do-upstreamu]] | 07 | 07-nasze-metody-uogolnienie.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[latki/latki-do-upstreamu]] | 143, 33, 69 | PLAN.md:45 | OK |
| [[latki/latki-do-upstreamu]] | 2026, 70 | 07-nasze-metody-uogolnienie.md:472 | OK |
| [[latki/latki-do-upstreamu]] | 3.1 | PLAN.md:42 | OK |
| [[latki/latki-hostowe]] | 0029, 101.5, 30.97 | NOTES.md:279 | OK |
| [[latki/latki-hostowe]] | 0031 | NOTES.md:327 | OK |
| [[latki/latki-hostowe]] | 0047, 102.6, 29.36 | 07-nasze-metody-uogolnienie.md:122 | OK |
| [[latki/latki-hostowe]] | 0059, 12, 3.806, 3.840 | NOTES.md:367 | OK |
| [[latki/latki-hostowe]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[latki/latki-hostowe]] | 104.2, 28.94 | NOTES.md:329 | OK |
| [[latki/latki-hostowe]] | 140, 375, 645, 963 | NOTES.md:278 | OK |
| [[latki/latki-hostowe]] | 16 | NOTES.md:277 | OK |
| [[latki/latki-hostowe]] | 2026 | NOTES.md:276 | OK |
| [[latki/latki-hostowe]] | 204800, 236 | NOTES.md:328 | OK |
| [[latki/latki-hostowe]] | 31.89, 32.20 | 07-nasze-metody-uogolnienie.md:104 | OK |
| [[latki/latki-hostowe]] | 32.14, 97.8 | NOTES.md:274 | OK |
| [[latki/latki-oczekujace]] | 0.15 | gdn-bitwise.md:182 | OK |
| [[latki/latki-oczekujace]] | 0001 | gdn-bitwise.md:177 | OK |
| [[latki/latki-oczekujace]] | 0002, 0006 | qwen-round5.md:81 | OK |
| [[latki/latki-oczekujace]] | 0003 | qwen-round5.md:85 | OK |
| [[latki/latki-oczekujace]] | 0004 | qwen-round5.md:78 | OK |
| [[latki/latki-oczekujace]] | 0005 | qwen-round5.md:87 | OK |
| [[latki/latki-oczekujace]] | 0007 | qwen-round5.md:83 | OK |
| [[latki/latki-oczekujace]] | 15, 2026 | gdn-bitwise.md:176 | OK |
| [[latki/latki-oczekujace]] | 16 | 0001-HIP-RDNA-GDN-separate-bit-identical-fast-kernel-DPP-.patch:28 | OK |
| [[latki/latki-oczekujace]] | 2.6 | qwen-round5.md:18 | OK (inny wiersz źródła, sprawdzone) |
| [[latki/latki-spekulacji]] | 0.4 | NOTES.md:284 | OK |
| [[latki/latki-spekulacji]] | 0004 | NOTES.md:83 | OK |
| [[latki/latki-spekulacji]] | 0032, 16, 32, 48, 64, 7.5, 96 | NOTES.md:88 | OK |
| [[latki/latki-spekulacji]] | 0039 | 07-nasze-metody-uogolnienie.md:114 | OK |
| [[latki/latki-spekulacji]] | 0041 | NOTES.md:307 | OK |
| [[latki/latki-spekulacji]] | 0046, 3.62, 4.82 | NOTES.md:285 | OK |
| [[latki/latki-spekulacji]] | 100.6 | NOTES.md:286 | OK |
| [[latki/latki-spekulacji]] | 103.6 | NOTES.md:311 | OK |
| [[latki/latki-spekulacji]] | 105, 4 102.7 | NOTES.md:308 | OK |
| [[latki/latki-spekulacji]] | 2.78, 3.31, 8192, 90 | NOTES.md:327 | OK |
| [[latki/latki-spekulacji]] | 2026 | NOTES.md:283 | OK |
| [[latki/latki-spekulacji]] | 6.6, 94 | NOTES.md:280 | OK |
| [[latki/latki-spekulacji]] | 913 | NOTES.md:322 | OK |
| [[latki/latki-spekulacji]] | 936 | 07-nasze-metody-uogolnienie.md:116 | OK |
| [[latki/latki-spekulacji]] | 97.5 | NOTES.md:330 | OK |
| [[latki/patch-manifest]] | 0001, 0019, 19 | 08-analiza-platformy-latek.md:5 | OK |
| [[latki/patch-manifest]] | 0057 | patch-manifest.json:74 | OK |
| [[latki/patch-manifest]] | 0060, 0070, 2026, 70, e60eff95f, f61994f58 | 08-analiza-platformy-latek.md:3 | OK |
| [[latki/patch-manifest]] | 1.736 | patch-manifest.json:49 | OK |
| [[latki/patch-manifest]] | 13.96, 14, 14.14, 27.74, 41, 41.7 | patch-manifest.json:48 | OK |
| [[latki/patch-manifest]] | 193 | ręcznie | OK: stat: 193045 B ≈ 193 KB |
| [[latki/patch-manifest]] | 30 | patch-manifest.json:666 | OK |
| [[latki/patch-manifest]] | 47 | patch-manifest.json:3679 | OK |
| [[latki/patch-manifest]] | 56 | 08-analiza-platformy-latek.md:188 | OK (inny wiersz źródła, sprawdzone) |
| [[latki/seria-amd-opt]] | 0001, 0070, 70 | 07-nasze-metody-uogolnienie.md:51 | OK |
| [[latki/seria-amd-opt]] | 0005, 0012, 0018 | 07-nasze-metody-uogolnienie.md:152 | OK |
| [[latki/seria-amd-opt]] | 0006, 0010, 2026, e60eff95f, f61994f58 | 07-nasze-metody-uogolnienie.md:53 | OK |
| [[latki/seria-amd-opt]] | 0011 | 07-nasze-metody-uogolnienie.md:153 | OK |
| [[latki/seria-amd-opt]] | 0019, 0033, 0038 | 07-nasze-metody-uogolnienie.md:163 | OK |
| [[latki/seria-amd-opt]] | 0020 | 07-nasze-metody-uogolnienie.md:164 | OK |
| [[latki/seria-amd-opt]] | 0021 | 07-nasze-metody-uogolnienie.md:165 | OK |
| [[latki/seria-amd-opt]] | 0028, 0032 | 07-nasze-metody-uogolnienie.md:166 | OK |
| [[latki/seria-amd-opt]] | 0029 | 07-nasze-metody-uogolnienie.md:167 | OK |
| [[latki/seria-amd-opt]] | 0039 | 0042-CUDA-HIP-RDNA-FA-MMA-D-256-prompt-tile-keeps-Q-in-SR.patch:10 | OK |
| [[latki/seria-amd-opt]] | 0047, 0048, 0064, 0069 | 07-nasze-metody-uogolnienie.md:155 | OK |
| [[latki/seria-amd-opt]] | 0065 | 07-nasze-metody-uogolnienie.md:154 | OK |
| [[latki/seria-amd-opt]] | 07 | 0060-HIP-RDNA3-replay-a-captured-decode-graph-as-one-PM4-.patch:769 | OK |
| [[latki/seria-amd-opt]] | 16 | README.md:16 | OK |
| [[latki/seria-amd-opt]] | 30103 | 0018-CUDA-HIP-fix-race-in-flash_attn_ext_f16_process_tile.patch:5 | OK |
| [[latki/seria-amd-opt]] | 59 | README.md:1 | OK |
| [[latki/wylaczniki-env]] | 0004, 0049 | NOTES.md:346 | OK |
| [[latki/wylaczniki-env]] | 0024, 0027 | NOTES.md:359 | OK |
| [[latki/wylaczniki-env]] | 0025 | NOTES.md:363 | OK |
| [[latki/wylaczniki-env]] | 0026, 0029 | NOTES.md:350 | OK |
| [[latki/wylaczniki-env]] | 0028 | NOTES.md:369 | OK |
| [[latki/wylaczniki-env]] | 0030, 0032 | NOTES.md:354 | OK |
| [[latki/wylaczniki-env]] | 0031 | patch-manifest.json:667 | OK |
| [[latki/wylaczniki-env]] | 0033 | patch-manifest.json:1600 | OK |
| [[latki/wylaczniki-env]] | 0034 | patch-manifest.json:56 | OK |
| [[latki/wylaczniki-env]] | 0036 | patch-manifest.json:1301 | OK |
| [[latki/wylaczniki-env]] | 0038 | patch-manifest.json:2529 | OK |
| [[latki/wylaczniki-env]] | 0039 | patch-manifest.json:1031 | OK |
| [[latki/wylaczniki-env]] | 0046 | NOTES.md:373 | OK |
| [[latki/wylaczniki-env]] | 0047 | patch-manifest.json:3534 | OK |
| [[latki/wylaczniki-env]] | 0048, 0052 | NOTES.md:343 | OK |
| [[latki/wylaczniki-env]] | 0050 | NOTES.md:347 | OK |
| [[latki/wylaczniki-env]] | 0051 | NOTES.md:348 | OK |
| [[latki/wylaczniki-env]] | 0053, 0054 | NOTES.md:353 | OK |
| [[latki/wylaczniki-env]] | 0055, 0059 | NOTES.md:362 | OK |
| [[latki/wylaczniki-env]] | 0056 | NOTES.md:364 | OK |
| [[latki/wylaczniki-env]] | 0057 | NOTES.md:365 | OK |
| [[latki/wylaczniki-env]] | 0058 | NOTES.md:366 | OK |
| [[latki/wylaczniki-env]] | 0060 | NOTES.md:372 | OK |
| [[latki/wylaczniki-env]] | 0061, 0062 | NOTES.md:374 | OK |
| [[latki/wylaczniki-env]] | 0064 | NOTES.md:357 | OK |
| [[latki/wylaczniki-env]] | 0065, 0069 | NOTES.md:381 | OK |
| [[latki/wylaczniki-env]] | 0066 | NOTES.md:383 | OK |
| [[latki/wylaczniki-env]] | 0070 | patch-manifest.json:8 | OK |
| [[lekcje/baco-runtime-suspend]] | 04 | NOTES.md:221 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/baco-runtime-suspend]] | 10, 2026 | NOTES.md:122 | OK |
| [[lekcje/baco-runtime-suspend]] | 20, 285, 90.6, 94.1, 94.7 | NOTES.md:126 | OK |
| [[lekcje/baco-runtime-suspend]] | 23.8, 35, 4.4, 92 | NOTES.md:124 | OK |
| [[lekcje/determinizm-fma]] | 0025, 83, 94 | 07-nasze-metody-uogolnienie.md:262 | OK |
| [[lekcje/determinizm-fma]] | 129, 229 | 07-nasze-metody-uogolnienie.md:265 | OK |
| [[lekcje/determinizm-fma]] | 270 | 07-nasze-metody-uogolnienie.md:264 | OK |
| [[lekcje/lekcja-5060ti-bezczynna]] | 01, 2026, 24, 5060 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5369 | OK |
| [[lekcje/lekcja-bit-exact-attention]] | 0.33, 10, 16, 2026, 368, 6144 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5568 | OK |
| [[lekcje/lekcja-bit-exact-attention]] | 77240, 77240c9b3 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5574 | OK |
| [[lekcje/lekcja-bit-exact-attention]] | 7900 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:16 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-bledny-roofline]] | 100 | 07-nasze-metody-uogolnienie.md:129 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-bledny-roofline]] | 1075, 112, 12 | 07-nasze-metody-uogolnienie.md:273 | OK |
| [[lekcje/lekcja-bledny-roofline]] | 7900 | 07-nasze-metody-uogolnienie.md:315 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-bledny-roofline]] | 960 | NOTES.md:54 | OK |
| [[lekcje/lekcja-brak-column-w-obrazie]] | 12.8, 2026, 5060 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5423 | OK |
| [[lekcje/lekcja-build-cuda-0057-0070]] | 0053 | CUDA-AUDIT.md:10 | OK |
| [[lekcje/lekcja-build-cuda-0057-0070]] | 0056 | CUDA-AUDIT.md:11 | OK |
| [[lekcje/lekcja-build-cuda-0057-0070]] | 0057, 25 | CUDA-AUDIT.md:7 | OK |
| [[lekcje/lekcja-build-cuda-0057-0070]] | 0070 | CUDA-AUDIT.md:3 | OK |
| [[lekcje/lekcja-build-cuda-0057-0070]] | 12 | CUDA-AUDIT.md:22 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-build-cuda-0057-0070]] | 579, 835 | CUDA-AUDIT.md:8 | OK |
| [[lekcje/lekcja-commity-bez-pomiaru]] | 0066, 0070, 16 | 07-nasze-metody-uogolnienie.md:277 | OK |
| [[lekcje/lekcja-commity-bez-pomiaru]] | 2026 | 07-nasze-metody-uogolnienie.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-jeden-prompt]] | 120 | 07-nasze-metody-uogolnienie.md:274 | OK |
| [[lekcje/lekcja-jeden-prompt]] | 13 | 07-nasze-metody-uogolnienie.md:272 | OK |
| [[lekcje/lekcja-jeden-prompt]] | 307.9 | 07-nasze-metody-uogolnienie.md:408 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-kolejnosc-akumulacji-fa]] | 0.0135, 0043 | 07-nasze-metody-uogolnienie.md:263 | OK |
| [[lekcje/lekcja-kolejnosc-akumulacji-fa]] | 07 | 07-nasze-metody-uogolnienie.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-losowe-spowolnienia]] | 0.11 | NOTES.md:359 | OK |
| [[lekcje/lekcja-losowe-spowolnienia]] | 17, 24.3, 27.2 | 07-nasze-metody-uogolnienie.md:278 | OK |
| [[lekcje/lekcja-losowe-spowolnienia]] | 3072 | 07-nasze-metody-uogolnienie.md:137 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-mikrobench-klamie]] | 07 | 07-nasze-metody-uogolnienie.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-mikrobench-klamie]] | 96 | 07-nasze-metody-uogolnienie.md:137 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-mtp-embd-state]] | 20, 39 | REBASE.md:140 | OK |
| [[lekcje/lekcja-mtp-embd-state]] | 30257, 781, 781dbc5ac | REBASE.md:146 | OK |
| [[lekcje/lekcja-mtp-embd-state]] | 7e9c73d8b | REBASE.md:148 | OK |
| [[lekcje/lekcja-mtp-embd-state]] | 8c942e5a9 | REBASE.md:150 | OK |
| [[lekcje/lekcja-mtp-embd-state]] | c90db29c6 | REBASE.md:147 | OK |
| [[lekcje/lekcja-obciazenie-cpu]] | 15 | 07-nasze-metody-uogolnienie.md:276 | OK |
| [[lekcje/lekcja-obciazenie-cpu]] | 3.4 | 07-nasze-metody-uogolnienie.md:383 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-obciazenie-cpu]] | 3090 | ręcznie | OK: nazwa karty (identyfikator) |
| [[lekcje/lekcja-oom-ub2048]] | 2026 | NOTES.md:215 | OK |
| [[lekcje/lekcja-oom-ub2048]] | 2048, 204800, 24.5, 512 | NOTES.md:218 | OK |
| [[lekcje/lekcja-pdl-sm120]] | 0053, 0057 | CUDA-AUDIT.md:182 | OK |
| [[lekcje/lekcja-pdl-sm120]] | 14506801, 14506801c | CUDA-AUDIT.md:76 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-siatka-pelna-fala]] | 0062, 11, 13.6, 14.6, 3072, 96 | 07-nasze-metody-uogolnienie.md:272 | OK |
| [[lekcje/lekcja-siatka-pelna-fala]] | 12.2, 25.5, 2560, 26.2 | NOTES.md:378 | OK |
| [[lekcje/lekcja-siatka-pelna-fala]] | 2026 | NOTES.md:381 | OK |
| [[lekcje/lekcja-siatka-pelna-fala]] | 3.402, 3.458 | 07-nasze-metody-uogolnienie.md:137 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-slaby-cpu-3090]] | 0.10, 0.201, 0.305, 2014, 28, 3.4 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5379 | OK |
| [[lekcje/lekcja-slaby-cpu-3090]] | 16, 2026, 3090 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5317 | OK |
| [[lekcje/lekcja-slaby-cpu-3090]] | 20, 30, 35, 498 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5320 | OK |
| [[lekcje/lekcja-spekulacja-zmienia-numeryke]] | 12 | 07-nasze-metody-uogolnienie.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-spekulacja-zmienia-numeryke]] | 129, 229 | 07-nasze-metody-uogolnienie.md:265 | OK |
| [[lekcje/lekcja-spekulacja-zmienia-numeryke]] | 6f14e814, 7900, c4708318 | 12-bit-exact-spekulacja.md:8 | OK |
| [[lekcje/lekcja-szum-t-s-przy-t1]] | 10 | 07-nasze-metody-uogolnienie.md:271 | OK |
| [[lekcje/lekcja-ten-sam-serwer-pending-h]] | 07 | 07-nasze-metody-uogolnienie.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-ten-sam-serwer-pending-h]] | 2026, c09ac6aab | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5512 | OK |
| [[lekcje/lekcja-ten-sam-serwer-pending-h]] | 270 | 07-nasze-metody-uogolnienie.md:264 | OK |
| [[lekcje/lekcja-ten-sam-serwer-pending-h]] | e60eff95f | NOTES.md:377 | OK |
| [[lekcje/lekcja-vast-cli-klucz]] | 1.8 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5352 | OK |
| [[lekcje/lekcja-vast-cli-klucz]] | 2026 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5350 | OK |
| [[lekcje/lekcja-vast-cli-klucz]] | 403 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5355 | OK |
| [[lekcje/lekcja-vast-cli-klucz]] | 600 | env.sh:3 | OK |
| [[lekcje/lekcja-wolna-sciezka-samplera]] | 0048, 0065, 0069, 1.05, 128, 255, 293 | 07-nasze-metody-uogolnienie.md:266 | OK |
| [[lekcje/lekcja-wolna-sciezka-samplera]] | 2026 | NOTES.md:381 | OK |
| [[lekcje/lekcja-wolna-sciezka-samplera]] | 255.6, 291.4 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:4380 | OK |
| [[lekcje/lekcja-wolna-sciezka-samplera]] | 512 | 07-nasze-metody-uogolnienie.md:83 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcje/lekcja-zombie-serwery]] | 15, 5.6, 8097 | 07-nasze-metody-uogolnienie.md:269 | OK |
| [[lekcje/lekcja-zombie-serwery]] | 18433, 18499 | 07-nasze-metody-uogolnienie.md:256 | OK |
| [[lekcje/lekcja-zombie-serwery]] | 8080 | loo.py:11 | OK |
| [[lekcje/pm4-niewidoczne-w-rocprof]] | 0060 | NOTES.md:372 | OK |
| [[lekcje/pm4-niewidoczne-w-rocprof]] | 13 | NOTES.md:96 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/conway-research]] | 10 | 10-post-training.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/conway-research]] | 2025, 7.89, 79.2, 84, 88, 96.7 | 10-post-training.md:337 | OK |
| [[ludzie-firmy/conway-research]] | 27 | 10-post-training.md:137 | OK |
| [[ludzie-firmy/conway-research]] | 3060 | 10-post-training.md:364 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/firma-amd]] | 0.2 | 13-rocm-10.1.md:26 | OK |
| [[ludzie-firmy/firma-amd]] | 01.2026 | 01-konkurencja.md:58 | OK |
| [[ludzie-firmy/firma-amd]] | 100, 30 | 05-chmura-gpu-do-testow.md:39 | OK |
| [[ludzie-firmy/firma-amd]] | 14 | 01-konkurencja.md:42 | OK |
| [[ludzie-firmy/firma-amd]] | 2026 | 01-konkurencja.md:46 | OK |
| [[ludzie-firmy/firma-amd]] | 7900 | 05-chmura-gpu-do-testow.md:40 | OK |
| [[ludzie-firmy/firma-nvidia]] | 06 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:48 | OK |
| [[ludzie-firmy/firma-nvidia]] | 1.9, 5090 | 01-konkurencja.md:57 | OK |
| [[ludzie-firmy/firma-nvidia]] | 12,93 | 06-produkt-ux-prawo-biznes.md:19 | OK |
| [[ludzie-firmy/firma-nvidia]] | 2026 | 01-konkurencja.md:46 | OK |
| [[ludzie-firmy/firma-nvidia]] | 76 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:47 | OK |
| [[ludzie-firmy/firma-runpod]] | 10 | 05-chmura-gpu-do-testow.md:66 | OK |
| [[ludzie-firmy/firma-runpod]] | 2.39, 3070 | 05-chmura-gpu-do-testow.md:67 | OK |
| [[ludzie-firmy/firma-runpod]] | 5090 | 05-chmura-gpu-do-testow.md:19 | OK |
| [[ludzie-firmy/firma-runpod]] | 80 | 05-chmura-gpu-do-testow.md:21 | OK |
| [[ludzie-firmy/firma-salad]] | 0.04, 0.17, 7800, 9060, 9070 | 05-chmura-gpu-do-testow.md:23 | OK |
| [[ludzie-firmy/firma-salad]] | 0.09, 3090 | 05-chmura-gpu-do-testow.md:21 | OK |
| [[ludzie-firmy/firma-salad]] | 7900 | 05-chmura-gpu-do-testow.md:22 | OK |
| [[ludzie-firmy/firma-vast-ai]] | 0.08, 3060 | 05-chmura-gpu-do-testow.md:14 | OK |
| [[ludzie-firmy/firma-vast-ai]] | 0.16, 5060 | 05-chmura-gpu-do-testow.md:17 | OK |
| [[ludzie-firmy/firma-vast-ai]] | 0.23, 3090 | 05-chmura-gpu-do-testow.md:15 | OK |
| [[ludzie-firmy/firma-vast-ai]] | 0.29, 5070 | 05-chmura-gpu-do-testow.md:18 | OK |
| [[ludzie-firmy/firma-vast-ai]] | 0.51, 4090 | 05-chmura-gpu-do-testow.md:16 | OK |
| [[ludzie-firmy/firma-vast-ai]] | 0.73, 445, 5090 | 05-chmura-gpu-do-testow.md:19 | OK |
| [[ludzie-firmy/firma-vast-ai]] | 2026, 21, 30 | 05-chmura-gpu-do-testow.md:7 | OK |
| [[ludzie-firmy/firma-vast-ai]] | 80 | 05-chmura-gpu-do-testow.md:21 | OK |
| [[ludzie-firmy/ggml-org]] | 2026, 24, 33, 69 | 03-silniki-i-stack.md:21 | OK |
| [[ludzie-firmy/ggml-org]] | e60eff95f | git:1 | OK |
| [[ludzie-firmy/gigagpu]] | 05 | 05-chmura-gpu-do-testow.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/gigagpu]] | 129, 179, 270 | 05-chmura-gpu-do-testow.md:26 | OK |
| [[ludzie-firmy/gigagpu]] | 395 | 05-chmura-gpu-do-testow.md:25 | OK |
| [[ludzie-firmy/gigagpu]] | 9070 | 05-chmura-gpu-do-testow.md:23 | OK |
| [[ludzie-firmy/hostkey]] | 0.47 | PLAN.md:293 | OK |
| [[ludzie-firmy/hostkey]] | 0.471 | 05-chmura-gpu-do-testow.md:24 | OK |
| [[ludzie-firmy/hostkey]] | 5.2 | PLAN.md:30 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/hostkey]] | 7900 | 05-chmura-gpu-do-testow.md:22 | OK |
| [[ludzie-firmy/hostkey]] | 9070 | 05-chmura-gpu-do-testow.md:23 | OK |
| [[ludzie-firmy/hugging-face]] | 04 | 06-produkt-ux-prawo-biznes.md:342 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/hugging-face]] | 12,93 | 06-produkt-ux-prawo-biznes.md:19 | OK |
| [[ludzie-firmy/hugging-face]] | 2026 | 03-silniki-i-stack.md:118 | OK |
| [[ludzie-firmy/hugging-face]] | 25 | 03-silniki-i-stack.md:66 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/ista-daslab]] | 50.03, 56.28 | 10-post-training.md:334 | OK |
| [[ludzie-firmy/jan]] | 0.8 | 03-silniki-i-stack.md:39 | OK |
| [[ludzie-firmy/jan]] | 13 | 03-silniki-i-stack.md:38 | OK |
| [[ludzie-firmy/jan]] | 45.0 | 01-konkurencja.md:158 | OK |
| [[ludzie-firmy/jan]] | 530, 95 | 03-silniki-i-stack.md:416 | OK |
| [[ludzie-firmy/lemonade]] | 0.2 | 13-rocm-10.1.md:26 | OK |
| [[ludzie-firmy/lemonade]] | 10, 2026 | 01-konkurencja.md:46 | OK |
| [[ludzie-firmy/liquidai]] | 10, 2026 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:313 | OK |
| [[ludzie-firmy/lm-studio]] | 100, 20 | 06-produkt-ux-prawo-biznes.md:20 | OK |
| [[ludzie-firmy/lm-studio]] | 61, 74.7 | 01-konkurencja.md:36 | OK |
| [[ludzie-firmy/metr-sakana]] | 1.49, 3.13 | 02-autotuning-i-agenci-kerneli.md:35 | OK |
| [[ludzie-firmy/metr-sakana]] | 1.81, 20, 2025 | 02-autotuning-i-agenci-kerneli.md:31 | OK |
| [[ludzie-firmy/metr-sakana]] | 10 | 02-autotuning-i-agenci-kerneli.md:192 | OK |
| [[ludzie-firmy/metr-sakana]] | 100, 2.01, 35, 93 | 02-autotuning-i-agenci-kerneli.md:191 | OK |
| [[ludzie-firmy/ollama]] | 1,5 | 03-silniki-i-stack.md:38 | OK |
| [[ludzie-firmy/ollama]] | 1.3 | 01-konkurencja.md:144 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/ollama]] | 165, 190 | 01-konkurencja.md:49 | OK |
| [[ludzie-firmy/ollama]] | 2026 | 01-konkurencja.md:46 | OK |
| [[ludzie-firmy/ollama]] | 65 | 06-produkt-ux-prawo-biznes.md:17 | OK |
| [[ludzie-firmy/prismml]] | 1.76, 20, 27, 5.93, 98.2 | 10-post-training.md:329 | OK |
| [[ludzie-firmy/prismml]] | 3060 | 10-post-training.md:364 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/qwen-alibaba]] | 04 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/qwen-alibaba]] | 16, 27 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:40 | OK |
| [[ludzie-firmy/qwen-alibaba]] | 17,56, 24 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:41 | OK |
| [[ludzie-firmy/qwen-alibaba]] | 40 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:45 | OK |
| [[ludzie-firmy/scaleway]] | 0.22, 149, 16 | 05-chmura-gpu-do-testow.md:28 | OK |
| [[ludzie-firmy/scaleway]] | 0.49, 64 | 05-chmura-gpu-do-testow.md:29 | OK |
| [[ludzie-firmy/scaleway]] | 08 | 05-chmura-gpu-do-testow.md:75 | OK |
| [[ludzie-firmy/scaleway]] | 24 | 05-chmura-gpu-do-testow.md:27 | OK |
| [[ludzie-firmy/thinking-machines]] | 02 | 02-autotuning-i-agenci-kerneli.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[ludzie-firmy/thinking-machines]] | 10.09 | 12-bit-exact-spekulacja.md:16 | OK |
| [[ludzie-firmy/thinking-machines]] | 1000, 12, 34, 78 | 02-autotuning-i-agenci-kerneli.md:225 | OK |
| [[ludzie-firmy/thinking-machines]] | 60 | 02-autotuning-i-agenci-kerneli.md:222 | OK |
| [[ludzie-firmy/turbollm]] | 285, 61, 74.7 | 01-konkurencja.md:36 | OK |
| [[ludzie-firmy/unsloth]] | 0,0137, 0,0192, 18,49, 19,17 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:360 | OK |
| [[ludzie-firmy/unsloth]] | 04 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:363 | OK |
| [[ludzie-firmy/unsloth]] | 10, 3.0 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:359 | OK |
| [[ludzie-firmy/unsloth]] | 2026 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:361 | OK |
| [[ludzie-firmy/unsloth]] | 66.9 | 10-post-training.md:339 | OK |
| [[metody/ablacja]] | 0070 | qwen-round5.md:43 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/ablacja]] | 1085, 1094, 1173, 7.6 | qwen-round5.md:20 | OK |
| [[metody/ablacja]] | 11, 11.9, 1131, 1219, 3.0, 3.8, 3254 | qwen-round5.md:21 | OK |
| [[metody/ablacja]] | 12 | qwen-round5.md:23 | OK |
| [[metody/ablacja]] | 2.2 | STATUS-NEXT.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/ablacja]] | 2.6 | qwen-round5.md:18 | OK |
| [[metody/ablacja]] | 2026 | STATUS-NEXT.md:24 | OK |
| [[metody/ablacja]] | 66 | qwen-round5.md:22 | OK |
| [[metody/analiza-platformy]] | 0001 | PLAN.md:26 | OK |
| [[metody/analiza-platformy]] | 0021, 0025 | 08-analiza-platformy-latek.md:24 | OK |
| [[metody/analiza-platformy]] | 0048, 0065, 0069 | 08-analiza-platformy-latek.md:39 | OK |
| [[metody/analiza-platformy]] | 0060 | PLAN.md:258 | OK |
| [[metody/analiza-platformy]] | 0061 | 08-analiza-platformy-latek.md:19 | OK |
| [[metody/analiza-platformy]] | 08 | PLAN.md:257 | OK |
| [[metody/analiza-platformy]] | 2026, 4.5 | PLAN.md:27 | OK |
| [[metody/analiza-platformy]] | 70 | PLAN.md:266 | OK |
| [[metody/bramka-kld-kanarki]] | 0.000025, 0.01 | kld-canary.md:27 | OK |
| [[metody/bramka-kld-kanarki]] | 0.005 | kld-canary.md:32 | OK |
| [[metody/bramka-kld-kanarki]] | 0.084188, 26.8 | kld-canary.md:29 | OK |
| [[metody/bramka-kld-kanarki]] | 0055 | NOTES.md:362 | OK |
| [[metody/bramka-kld-kanarki]] | 1.10 | kld-canary.md:58 | OK |
| [[metody/bramka-kld-kanarki]] | 1.25 | kld-canary.md:15 | OK |
| [[metody/bramka-kld-kanarki]] | 16384 | kld-canary.md:3 | OK |
| [[metody/bramka-kld-kanarki]] | 24573 | kld-canary.md:4 | OK |
| [[metody/bramka-kld-kanarki]] | 6.3 | NOTES.md:370 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/dowod-offline]] | 00, 02, 2026, 45 | qwen-round5.md:7 | OK |
| [[metody/dowod-offline]] | 0066, 0070 | 07-nasze-metody-uogolnienie.md:37 | OK |
| [[metody/dowod-offline]] | 2.2 | 07-nasze-metody-uogolnienie.md:280 | OK |
| [[metody/dowod-offline]] | 67 | gdn-bitwise.md:177 | OK |
| [[metody/dowod-offline]] | 8080 | qwen-round5.md:88 | OK |
| [[metody/emulator-isa]] | 0d89ce56c | gdn-bitwise.md:174 | OK |
| [[metody/emulator-isa]] | 2026 | gdn-bitwise.md:176 | OK |
| [[metody/emulator-isa]] | 44 | gdn-bitwise.md:26 | OK |
| [[metody/emulator-isa]] | 67 | gdn-bitwise.md:177 | OK |
| [[metody/emulator-isa]] | 83 | gdn-bitwise.md:88 | OK |
| [[metody/emulator-isa]] | b4e819237 | gdn-bitwise.md:7 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/kernel-tuner]] | 1,2, 16, 4,8 | README.md:57 | OK |
| [[metody/kernel-tuner]] | 1010 | test-tooling.md:82 | OK |
| [[metody/kernel-tuner]] | 256 | test-tooling.md:74 | OK |
| [[metody/kernel-tuner]] | 39 | README.md:56 | OK |
| [[metody/kernel-tuner]] | 4db68c6ab | test-tooling.md:8 | OK |
| [[metody/kernel-tuner]] | 53 | README.md:62 | OK |
| [[metody/kernel-tuner]] | 64 | README.md:75 | OK |
| [[metody/loo]] | 0001 | README.md:8 | OK |
| [[metody/loo]] | 0004, 0032 | README.md:15 | OK |
| [[metody/loo]] | 0022, 14, 22 | README.md:16 | OK |
| [[metody/loo]] | 0033, 0034, 0038 | test-tooling.md:26 | OK |
| [[metody/loo]] | 0036 | test-tooling.md:21 | OK |
| [[metody/loo]] | 18440 | test-tooling.md:29 | OK |
| [[metody/loo]] | 27 | README.md:14 | OK |
| [[metody/loo]] | 3.8 | README.md:29 | OK |
| [[metody/loo]] | 4.1 | PLAN.md:163 | OK |
| [[metody/loo]] | 45 | README.md:21 | OK |
| [[metody/loo]] | 65, c36fd2c87 | README.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/loo]] | 95 | README.md:30 | OK |
| [[metody/mikrobench-granicy-kernela]] | 0.46, 0.86, 2.08, 2.75 | NOTES.md:373 | OK |
| [[metody/mikrobench-granicy-kernela]] | 0.5, 0.8, 11, 2.53 | NOTES.md:358 | OK |
| [[metody/mikrobench-granicy-kernela]] | 0060, 2026 | NOTES.md:372 | OK |
| [[metody/mikrobench-granicy-kernela]] | 10.0, 7900 | NOTES.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/mikrobench-granicy-kernela]] | 3.424, 3.887 | NOTES.md:374 | OK |
| [[metody/mikrobench-granicy-kernela]] | 358, 373 | 07-nasze-metody-uogolnienie.md:214 | OK |
| [[metody/ms-na-krok]] | 2.9 | README.md:179 | OK |
| [[metody/ms-na-krok]] | 2026 | NOTES.md:283 | OK |
| [[metody/ms-na-krok]] | 29.76, 30.97 | NOTES.md:285 | OK |
| [[metody/ms-na-krok]] | 3.008, 3.063 | NOTES.md:286 | OK |
| [[metody/ms-na-krok]] | 3.16, 35.7 | README.md:178 | OK |
| [[metody/playbook-optymalizacji]] | 0.15 | 07-nasze-metody-uogolnienie.md:234 | OK |
| [[metody/playbook-optymalizacji]] | 07 | PLAN.md:224 | OK |
| [[metody/playbook-optymalizacji]] | 10, 25, 40 | 07-nasze-metody-uogolnienie.md:38 | OK |
| [[metody/playbook-optymalizacji]] | 2.2, 4.4 | 07-nasze-metody-uogolnienie.md:27 | OK |
| [[metody/pomiar-abba]] | 0.3 | NOTES.md:166 | OK |
| [[metody/pomiar-abba]] | 02 | 02-autotuning-i-agenci-kerneli.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/pomiar-abba]] | 12 | 07-nasze-metody-uogolnienie.md:273 | OK |
| [[metody/pomiar-abba]] | 163.1, 98.5 | 02-autotuning-i-agenci-kerneli.md:50 | OK |
| [[metody/pomiar-abba]] | 17.3, 26.7 | 02-autotuning-i-agenci-kerneli.md:47 | OK |
| [[metody/pomiar-abba]] | 2026 | NOTES.md:362 | OK |
| [[metody/pomiar-abba]] | 22 | 02-autotuning-i-agenci-kerneli.md:49 | OK |
| [[metody/pomiar-abba]] | 24.3, 27.2 | 07-nasze-metody-uogolnienie.md:278 | OK |
| [[metody/pomiar-abba]] | 95 | 07-nasze-metody-uogolnienie.md:233 | OK |
| [[metody/serializacja-gpu]] | 07 | 07-nasze-metody-uogolnienie.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/serializacja-gpu]] | 15, 5.6, 8097 | 07-nasze-metody-uogolnienie.md:269 | OK |
| [[metody/serializacja-gpu]] | 18433, 18499, 8080 | README.md:5 | OK |
| [[metody/serializacja-gpu]] | 2026 | NOTES.md:162 | OK |
| [[metody/sufit-pasma-i-mapa-czasu]] | 1.3, 3.8, 680, 71, 721 | NOTES.md:340 | OK |
| [[metody/sufit-pasma-i-mapa-czasu]] | 1.8, 1.9, 500 | 07-nasze-metody-uogolnienie.md:193 | OK |
| [[metody/sufit-pasma-i-mapa-czasu]] | 112 | NOTES.md:104 | OK |
| [[metody/sufit-pasma-i-mapa-czasu]] | 16, 3.2 | 07-nasze-metody-uogolnienie.md:204 | OK |
| [[metody/sufit-pasma-i-mapa-czasu]] | 1900, 2100 | NOTES.md:57 | OK |
| [[metody/sufit-pasma-i-mapa-czasu]] | 2026 | NOTES.md:343 | OK |
| [[metody/sufit-pasma-i-mapa-czasu]] | 3.1, 5.05 | 07-nasze-metody-uogolnienie.md:201 | OK |
| [[metody/sufit-pasma-i-mapa-czasu]] | 81, 88, 960 | 07-nasze-metody-uogolnienie.md:192 | OK |
| [[metody/wylacznik-w-kazdej-latce]] | 0024 | 07-nasze-metody-uogolnienie.md:222 | OK |
| [[metody/wylacznik-w-kazdej-latce]] | 0063 | NOTES.md:374 | OK |
| [[metody/wylacznik-w-kazdej-latce]] | 08, 27 | NOTES.md:373 | OK |
| [[metody/wylacznik-w-kazdej-latce]] | 128 | NOTES.md:383 | OK |
| [[metody/wyniki-negatywne]] | 0.15 | 07-nasze-metody-uogolnienie.md:234 | OK |
| [[metody/wyniki-negatywne]] | 1075, 112 | NOTES.md:104 | OK |
| [[metody/wyniki-negatywne]] | 111, 76, 82 | NOTES.md:100 | OK |
| [[metody/wyniki-negatywne]] | 12.9, 14.4 | NOTES.md:369 | OK |
| [[metody/wyniki-negatywne]] | 2.7, 400 | NOTES.md:105 | OK |
| [[metody/wyniki-negatywne]] | 4.474, 4.490 | NOTES.md:351 | OK |
| [[metody/wyniki-negatywne]] | 96 | NOTES.md:96 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 07 | qwen-round5.md:23 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 0b7b073b, 58, 58e578967 | qwen-round5.md:11 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 129, 229 | 07-nasze-metody-uogolnienie.md:265 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 2.2 | 07-nasze-metody-uogolnienie.md:27 | OK (inny wiersz źródła, sprawdzone) |
| [[metody/zgodnosc-bitowa-md5]] | 2026, 45 | qwen-round5.md:7 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 2048, 3000, 64 | 07-nasze-metody-uogolnienie.md:228 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 270 | 07-nasze-metody-uogolnienie.md:264 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 6f14e814, c4708318 | NOTES.md:357 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 83, 94 | 07-nasze-metody-uogolnienie.md:262 | OK |
| [[metody/zgodnosc-bitowa-md5]] | 894, 894e56e4 | STATUS-NEXT.md:15 | OK |
| [[metody/zgodnosc-bitowa-md5]] | e60eff95f | NOTES.md:377 | OK |
| [[modele/bonsai]] | 0.17549, 8.6154 | summary.md:36 | OK |
| [[modele/bonsai]] | 0.17552 | summary.md:35 | OK |
| [[modele/bonsai]] | 0.17553, 8.6171 | summary.md:34 | OK |
| [[modele/bonsai]] | 1.75, 2.13, 5.95, 7.21 | bonsai-README.md:44 | OK |
| [[modele/bonsai]] | 1.76, 1024, 128, 20, 5.93, 7.3, 88.4, 98.2 | 10-post-training.md:329 | OK |
| [[modele/bonsai]] | 10 | 10-post-training.md:386 | OK |
| [[modele/bonsai]] | 18 | 10-post-training.md:128 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/bonsai]] | 2026 | 10-post-training.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/bonsai]] | 27 | 10-post-training.md:137 | OK |
| [[modele/bonsai]] | 3060 | 10-post-training.md:364 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/bonsai]] | 512 | 10-post-training.md:273 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/bonsai]] | 64 | bonsai-README.md:60 | OK |
| [[modele/drafter-dflash]] | 1.06 | ręcznie | OK: ls ~/models: Qwen3.8-27B-DFlash2-Q4_K_M.gguf = 1.06 GiB (2026-10-16) |
| [[modele/drafter-dflash]] | 104.8, 89.7 | qwen-round5.md:26 | OK |
| [[modele/drafter-dflash]] | 112, 6 111 | NOTES.md:46 | OK |
| [[modele/drafter-dflash]] | 115.7 | NOTES.md:47 | OK |
| [[modele/drafter-dflash]] | 120 | NOTES.md:158 | OK |
| [[modele/drafter-dflash]] | 15, 40 | drafters.md:10 | OK |
| [[modele/drafter-dflash]] | 20, 24 | drafters.md:28 | OK |
| [[modele/drafter-dflash]] | 2026 | drafters.md:45 | OK |
| [[modele/drafter-dflash]] | 2048 | drafters.md:30 | OK |
| [[modele/drafter-dflash]] | 285 | NOTES.md:146 | OK |
| [[modele/drafter-dflash]] | 3.74, 4.10 | drafters.md:11 | OK |
| [[modele/drafter-dflash]] | 5.02, 5.46 | drafters.md:51 | OK |
| [[modele/drafter-dflash]] | 5120 | drafters.md:46 | OK |
| [[modele/drafter-dflash]] | 65, 78 | NOTES.md:50 | OK |
| [[modele/drafter-dflash]] | 71.9 | NOTES.md:156 | OK |
| [[modele/drafter-dflash]] | 81.1 | NOTES.md:154 | OK |
| [[modele/drafter-dflash]] | 86.3 | NOTES.md:151 | OK |
| [[modele/drafter-dflash]] | 90.6 | NOTES.md:152 | OK |
| [[modele/drafter-dflash]] | 97.7 | NOTES.md:45 | OK |
| [[modele/glowica-mtp]] | 0.72 | RESULTS.md:75 | OK |
| [[modele/glowica-mtp]] | 0.78, 0.87, 0.89 | RESULTS.md:80 | OK |
| [[modele/glowica-mtp]] | 109 | NOTES.md:280 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/glowica-mtp]] | 11, 3.11, 3.93 | RESULTS.md:54 | OK |
| [[modele/glowica-mtp]] | 2.48 | RESULTS.md:65 | OK |
| [[modele/glowica-mtp]] | 2.68 | RESULTS.md:60 | OK |
| [[modele/glowica-mtp]] | 2.97, 3.04 | RESULTS.md:55 | OK |
| [[modele/glowica-mtp]] | 2026 | RESULTS.md:5 | OK |
| [[modele/glowica-mtp]] | 3.76 | RESULTS.md:63 | OK |
| [[modele/glowica-mtp]] | 3.89 | RESULTS.md:59 | OK |
| [[modele/glowica-mtp]] | 3.96 | RESULTS.md:57 | OK |
| [[modele/glowica-mtp]] | 4 102.7 | NOTES.md:316 | OK |
| [[modele/glowica-mtp]] | 5 103.0 | NOTES.md:317 | OK |
| [[modele/glowica-mtp]] | 64 | RESULTS.md:3 | OK |
| [[modele/glowica-mtp]] | 69 207 | RESULTS.md:15 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/kwanty-gguf]] | 0.044 | ręcznie | OK: NOTES.md:363 i kld-canary.md:52: 0.044171 (zaokrąglone) |
| [[modele/kwanty-gguf]] | 0.128 | NOTES.md:363 | OK |
| [[modele/kwanty-gguf]] | 0.4 | NOTES.md:284 | OK |
| [[modele/kwanty-gguf]] | 0032, 16, 16.34 | SPEC-QWEN27B.md:21 | OK |
| [[modele/kwanty-gguf]] | 0055 | NOTES.md:362 | OK |
| [[modele/kwanty-gguf]] | 10.2 | PLAN-TESTOW.md:91 | OK |
| [[modele/kwanty-gguf]] | 100.6 | NOTES.md:286 | OK |
| [[modele/kwanty-gguf]] | 12, 2.6, 30.1 | NOTES.md:354 | OK |
| [[modele/kwanty-gguf]] | 12.2, 15.86 | PLAN-TESTOW.md:90 | OK |
| [[modele/kwanty-gguf]] | 15.66 | ręcznie | OK: ls ~/models: Qwen3.8-27B-Uncensored-Q4_K_M.gguf = 15.66 GiB (2026-10-16) |
| [[modele/kwanty-gguf]] | 16.35 | — | poprawione (było 16.34 GiB za SPEC; stat 17 559 178 144 B = 16.35 GiB) |
| [[modele/kwanty-gguf]] | 16.8, 17.1, 24 | qwen3.8-27b.md:21 | OK |
| [[modele/kwanty-gguf]] | 17 559 178 144 | ręcznie | OK: ls ~/models: Qwen3.8-27B-UD-Q4_K_XL.gguf (stat) = 17 559 178 144 GiB (2026-10-16) |
| [[modele/kwanty-gguf]] | 20.9, 22.9 | qwen3.8-27b.md:22 | OK |
| [[modele/kwanty-gguf]] | 29 | qwen3.8-27b.md:23 | OK |
| [[modele/kwanty-gguf]] | 3.62, 4.82 | NOTES.md:285 | OK |
| [[modele/kwanty-gguf]] | 94, 98 | NOTES.md:280 | OK |
| [[modele/kwanty-gguf]] | 97.5 | NOTES.md:330 | OK |
| [[modele/lfm2-5-24b-a2b]] | 0.044 | ręcznie | OK: NOTES.md:363: 0.044171 (zaokrąglone) |
| [[modele/lfm2-5-24b-a2b]] | 0.128 | NOTES.md:363 | OK |
| [[modele/lfm2-5-24b-a2b]] | 1.48 | ręcznie | OK: ls ~/models: LFM2.5-2.6B-QAD-Q4_0.gguf = 1.48 GiB (2026-10-16) |
| [[modele/lfm2-5-24b-a2b]] | 1.8, 1.9, 500 | NOTES.md:338 | OK |
| [[modele/lfm2-5-24b-a2b]] | 10, 2026, 24 | NOTES.md:333 | OK |
| [[modele/lfm2-5-24b-a2b]] | 128, 198 | NOTES.md:336 | OK |
| [[modele/lfm2-5-24b-a2b]] | 131072 | NOTES.md:334 | OK |
| [[modele/lfm2-5-24b-a2b]] | 15.1, 1536, 16, 2048, 205, 30, 32, 40, 64 | NOTES.md:337 | OK |
| [[modele/lfm2-5-24b-a2b]] | 15.86 | ręcznie | OK: ls ~/models: LFM2.5-24B-A2B-Q5_K_M.gguf = 15.86 GiB (2026-10-16) |
| [[modele/lfm2-5-24b-a2b]] | 169.3 | NOTES.md:339 | OK |
| [[modele/lfm2-5-24b-a2b]] | 173 | NOTES.md:335 | OK |
| [[modele/lfm2-5-24b-a2b]] | 289.7, 293.7, 3.41, 6175 | STATUS-NEXT.md:12 | OK |
| [[modele/lfm2-5-24b-a2b]] | 294 | NOTES.md:375 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/lfm2-5-24b-a2b]] | 7900 | NOTES.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/lfm2-5-uncensored]] | 0064, 2026 | NOTES.md:372 | OK |
| [[modele/lfm2-5-uncensored]] | 16.10 | ręcznie | OK: ls ~/models: LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf = 16.10 GiB (2026-10-16) |
| [[modele/lfm2-5-uncensored]] | 264, 264.3, 267.3, 3.74, 6291 | STATUS-NEXT.md:13 | OK |
| [[modele/lfm2-5-uncensored]] | 3.706, 3.933 | lfm-decode-round4.md:14 | OK |
| [[modele/lfm2-5-uncensored]] | 33 | lfm-decode-round4.md:132 | OK |
| [[modele/modele-katalogowe]] | 06 | 06-produkt-ux-prawo-biznes.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/modele-katalogowe]] | 1.17, 2.69 | 06-produkt-ux-prawo-biznes.md:95 | OK |
| [[modele/modele-katalogowe]] | 1.62, 3.22, 62 | 06-produkt-ux-prawo-biznes.md:97 | OK |
| [[modele/modele-katalogowe]] | 11 | 06-produkt-ux-prawo-biznes.md:363 | OK |
| [[modele/modele-katalogowe]] | 12, 72.3 | 06-produkt-ux-prawo-biznes.md:448 | OK |
| [[modele/modele-katalogowe]] | 2.0 | 06-produkt-ux-prawo-biznes.md:50 | OK |
| [[modele/modele-katalogowe]] | 2026 | 06-produkt-ux-prawo-biznes.md:48 | OK |
| [[modele/modele-katalogowe]] | 3060 | PLAN-TESTOW.md:91 | OK |
| [[modele/modele-katalogowe]] | 3090 | PLAN-TESTOW.md:89 | OK |
| [[modele/modele-katalogowe]] | 4060, 5060 | PLAN-TESTOW.md:90 | OK |
| [[modele/modele-katalogowe]] | 48, 9070 | local_llm_practice.md:36 | OK |
| [[modele/modele-telefon]] | 07 | 07-nasze-metody-uogolnienie.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/modele-telefon]] | 100, 500 | PROMPT-optymalizacja-modeli.md:147 | OK |
| [[modele/modele-telefon]] | 134, 271 | PROMPT-optymalizacja-modeli.md:163 | OK |
| [[modele/modele-telefon]] | 14.8 | PROMPT-optymalizacja-modeli.md:144 | OK |
| [[modele/modele-telefon]] | 15, 150, 249 | PROMPT-optymalizacja-modeli.md:129 | OK |
| [[modele/modele-telefon]] | 17 | 07-nasze-metody-uogolnienie.md:395 | OK |
| [[modele/modele-telefon]] | 18, 35 | PROMPT-optymalizacja-modeli.md:56 | OK |
| [[modele/modele-telefon]] | 2.8, 200, 300 | PROMPT-minicpm-speed.md:21 | OK |
| [[modele/modele-telefon]] | 20 | PROMPT-optymalizacja-modeli.md:58 | OK |
| [[modele/modele-telefon]] | 350, 670 | PROMPT-optymalizacja-modeli.md:130 | OK |
| [[modele/modele-telefon]] | 4.7 | PROMPT-optymalizacja-modeli.md:1 | OK |
| [[modele/modele-telefon]] | 50 | PROMPT-minicpm-speed.md:14 | OK |
| [[modele/modele-telefon]] | 87 | PROMPT-optymalizacja-modeli.md:83 | OK |
| [[modele/qwen3-8-27b-uncensored]] | 0.87 | ręcznie | OK: ls ~/models: mmproj-…-f16.gguf = 0.87 GiB (2026-10-16) |
| [[modele/qwen3-8-27b-uncensored]] | 1109, 115.5, 26.68, 44.0 | STATUS-NEXT.md:11 | OK |
| [[modele/qwen3-8-27b-uncensored]] | 15.66 | ręcznie | OK: ls ~/models: Qwen3.8-27B-Uncensored-Q4_K_M.gguf = 15.66 GiB (2026-10-16) |
| [[modele/qwen3-8-27b-uncensored]] | 2.0 | qwen3.8-27b.md:35 | OK |
| [[modele/qwen3-8-27b-uncensored]] | 2026 | run-llm.sh:6 | OK |
| [[modele/qwen3-8-27b]] | 0.7, 2.9, 27.32, 3.1, 7.9 | SPEC-QWEN27B.md:21 | OK |
| [[modele/qwen3-8-27b]] | 1.7, 130.2 | NOTES.md:331 | OK |
| [[modele/qwen3-8-27b]] | 100.6, 105.2, 29.5 | NOTES.md:330 | OK |
| [[modele/qwen3-8-27b]] | 109, 109.0, 1115, 27.74, 43.2 | STATUS-NEXT.md:10 | OK |
| [[modele/qwen3-8-27b]] | 13 | qwen3.8-27b.md:19 | OK |
| [[modele/qwen3-8-27b]] | 16, 27, 48, 5120, 64 | qwen3.8-27b.md:6 | OK |
| [[modele/qwen3-8-27b]] | 16.35 | ręcznie | OK: ls ~/models: Qwen3.8-27B-UD-Q4_K_XL.gguf = 16.35 GiB (2026-10-16) |
| [[modele/qwen3-8-27b]] | 2.0 | 06-produkt-ux-prawo-biznes.md:50 | OK |
| [[modele/qwen3-8-27b]] | 2026, 7900 | qwen3.8-27b.md:3 | OK |
| [[modele/qwen3-8-27b]] | 204800 | NOTES.md:6 | OK |
| [[modele/qwen3-8-27b]] | 248 320 | SPEC-QWEN27B.md:26 | OK |
| [[modele/qwen3-8-27b]] | 256 | NOTES.md:3 | OK |
| [[modele/qwen3-8-27b]] | 262 144 | SPEC-QWEN27B.md:27 | OK |
| [[modele/qwen3-8-27b]] | 59.2 | NOTES.md:10 | OK |
| [[modele/qwen3-8-27b]] | 94 | NOTES.md:329 | OK |
| [[modele/saluki]] | 0.15010, 7.6665 | summary.md:38 | OK |
| [[modele/saluki]] | 1.0 | 10-post-training.md:139 | OK |
| [[modele/saluki]] | 10 | 10-post-training.md:386 | OK |
| [[modele/saluki]] | 12 | saluki-head.json:1336 | OK |
| [[modele/saluki]] | 2025, 7.89, 79.2, 84, 88, 96, 96.7 | 10-post-training.md:337 | OK |
| [[modele/saluki]] | 2026 | saluki-README.md:104 | OK |
| [[modele/saluki]] | 27 | 10-post-training.md:42 | OK |
| [[modele/saluki]] | 3060 | 10-post-training.md:364 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/saluki]] | 35, 42 | saluki-README.md:29 | OK |
| [[modele/saluki]] | 512 | 10-post-training.md:273 | OK (inny wiersz źródła, sprawdzone) |
| [[modele/saluki]] | 569.90 | summary.md:5 | OK |
| [[modele/saluki]] | 573.37 | summary.md:6 | OK |
| [[modele/saluki]] | 629, 928 | saluki-README.md:37 | OK |
| [[modele/saluki]] | 64 | saluki-head.json:27 | OK |
| [[narzedzia/det-probe]] | 2026 | NOTES.md:109 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/det-probe]] | 270, e60eff95f | NOTES.md:377 | OK |
| [[narzedzia/gdnemu-isadiff]] | 12 | mmvqemu.py:200 | OK |
| [[narzedzia/gdnemu-isadiff]] | 58 | gdn.s:1132 | OK |
| [[narzedzia/gdnemu-isadiff]] | 862 | 12-bit-exact-spekulacja.md:98 | OK |
| [[narzedzia/gdnemu-isadiff]] | 869 | ręcznie | OK: wc -l gdnemu.py = 869 |
| [[narzedzia/gpu-keepawake]] | 12 | NOTES.md:162 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/gpu-keepawake]] | 4.4, 92 | NOTES.md:124 | OK |
| [[narzedzia/greedy-check]] | 18433 | greedy.sh:4 | OK |
| [[narzedzia/greedy-check]] | 2026 | 07-nasze-metody-uogolnienie.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/greedy-check]] | 2048, 3000, 64 | 07-nasze-metody-uogolnienie.md:228 | OK |
| [[narzedzia/greedy-check]] | 6f14e814, c4708318 | mmq-epilogue.md:144 | OK |
| [[narzedzia/greedy-check]] | 894, 894e56e4 | mmq-epilogue.md:145 | OK |
| [[narzedzia/kld-canary]] | 0.000025 | kld-canary.md:27 | OK |
| [[narzedzia/kld-canary]] | 0.005 | kld-canary.md:32 | OK |
| [[narzedzia/kld-canary]] | 0.084188 | kld-canary.md:29 | OK |
| [[narzedzia/kld-canary]] | 1.005, 1.02, 1.10 | kld-canary.md:58 | OK |
| [[narzedzia/kld-canary]] | 1.25 | kld_gate.py:4 | OK |
| [[narzedzia/kld-canary]] | 11 | perturb_gguf.py:11 | OK |
| [[narzedzia/kld-canary]] | 16384 | kld_canary.sh:3 | OK |
| [[narzedzia/llama-bx-diff]] | 6e261fdb4 | git:6 | OK |
| [[narzedzia/loo-py]] | 14, 22 | REPORT.md:21 | OK |
| [[narzedzia/loo-py]] | 18433, 18499, 45 | loo.py:12 | OK |
| [[narzedzia/loo-py]] | 2026 | git:1 | OK |
| [[narzedzia/loo-py]] | 27 | REPORT.md:19 | OK |
| [[narzedzia/loo-py]] | 65 | loo.py:141 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/loo-py]] | 8080 | loo.py:11 | OK |
| [[narzedzia/loo-py]] | 95 | loo.py:8 | OK |
| [[narzedzia/pm4-soak]] | 0060 | NOTES.md:374 | OK |
| [[narzedzia/pm4-soak]] | 2048, 256 | NOTES.md:376 | OK |
| [[narzedzia/pm4-soak]] | 240 | pm4_soak.py:7 | OK |
| [[narzedzia/reactor-monitor]] | 1045 | ręcznie | OK: wc -l reactor.py = 1045 |
| [[narzedzia/reactor-monitor]] | 16 | README.md:13 | OK |
| [[narzedzia/reactor-monitor]] | 24 | README.md:5 | OK |
| [[narzedzia/reactor-monitor]] | 285 | README.md:11 | OK |
| [[narzedzia/reactor-monitor]] | 3.12 | README.md:4 | OK |
| [[narzedzia/reactor-monitor]] | 7900 | README.md:3 | OK |
| [[narzedzia/run-llm-sh]] | 0065 | STATUS-NEXT.md:16 | OK |
| [[narzedzia/run-llm-sh]] | 109 | run-llm.sh:7 | OK |
| [[narzedzia/run-llm-sh]] | 115 | run-llm.sh:8 | OK |
| [[narzedzia/run-llm-sh]] | 127.0, 8080 | run-llm.sh:13 | OK |
| [[narzedzia/run-llm-sh]] | 131072, 294 | run-llm.sh:10 | OK |
| [[narzedzia/run-llm-sh]] | 16384 | run-llm.sh:109 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/run-llm-sh]] | 2026, 204800, 64 | run-llm.sh:6 | OK |
| [[narzedzia/run-llm-sh]] | 264 | run-llm.sh:11 | OK |
| [[narzedzia/run-llm-sh]] | 7900 | run-llm.sh:2 | OK |
| [[narzedzia/samp-ab]] | 0.05, 0.8, 0.95, 11, 40 | samp_ab.py:13 | OK |
| [[narzedzia/samp-ab]] | 0065, 0069, 2026 | NOTES.md:381 | OK |
| [[narzedzia/samp-ab]] | 800 | samp_ab.py:28 | OK |
| [[narzedzia/serve-bench]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/serve-bench]] | 10 | NOTES.md:1 | OK |
| [[narzedzia/serve-bench]] | 2.4 | 07-nasze-metody-uogolnienie.md:120 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/serve-bench]] | 2026 | NOTES.md:109 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/serve-bench]] | 256 | NOTES.md:3 | OK |
| [[narzedzia/serve-bench]] | 49 | 07-nasze-metody-uogolnienie.md:241 | OK |
| [[narzedzia/serve-bench]] | 59.2 | NOTES.md:10 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/serve-bench]] | 92 | NOTES.md:124 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/skrypty-chmury]] | 12.8 | bootstrap.sh:2 | OK |
| [[narzedzia/skrypty-chmury]] | 600 | env.sh:3 | OK |
| [[narzedzia/skrypty-chmury]] | e60eff95f | push.sh:2 | OK |
| [[narzedzia/spec-sweep]] | 07 | 07-nasze-metody-uogolnienie.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/spec-sweep]] | 1,2, 400 | spec_sweep.py:7 | OK |
| [[narzedzia/spec-sweep]] | 1.0 | spec_sweep.sh:8 | OK |
| [[narzedzia/spec-sweep]] | 14 | 07-nasze-metody-uogolnienie.md:102 | OK (inny wiersz źródła, sprawdzone) |
| [[narzedzia/spec-sweep]] | 15, 182 | 07-nasze-metody-uogolnienie.md:242 | OK |
| [[narzedzia/spec-sweep]] | 2.15, 6.8 | 07-nasze-metody-uogolnienie.md:301 | OK |
| [[narzedzia/spec-sweep]] | 2026 | NOTES.md:162 | OK |
| [[narzedzia/ss-zrzut-ekranu]] | 2026 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5195 | OK |
| [[nvidia/cuda-compat]] | 0053 | CUDA-AUDIT.md:10 | OK |
| [[nvidia/cuda-compat]] | 0056 | CUDA-AUDIT.md:11 | OK |
| [[nvidia/cuda-compat]] | 0057, 21, 25 | CUDA-AUDIT.md:7 | OK |
| [[nvidia/cuda-compat]] | 0070 | CUDA-AUDIT.md:3 | OK |
| [[nvidia/cuda-compat]] | 14506801, 14506801c | CUDA-AUDIT.md:76 | OK |
| [[nvidia/cuda-compat]] | 57, 57e0bdfe4 | CUDA-AUDIT.md:74 | OK |
| [[nvidia/cuda-compat]] | 579, 7b2680760, 835 | CUDA-AUDIT.md:8 | OK |
| [[nvidia/cuda-compat]] | 780365407 | CUDA-AUDIT.md:75 | OK |
| [[nvidia/cuda-compat]] | 7a538d96f | git:1 | OK |
| [[nvidia/cuda-compat]] | b479c67dd | ręcznie | OK: git log 8c942e5a9..cuda-v070 |
| [[nvidia/cuda-stos]] | 1140, 1160 | ręcznie | OK: przybliżenie 1139/1151/1157 s z results/3060-20261016/build/times.jsonl:1-3 |
| [[nvidia/cuda-stos]] | 12.8, 2.3, 5.4 | CUDA-AUDIT.md:22 | OK |
| [[nvidia/cuda-stos]] | 120, 86, 89 | CUDA-AUDIT.md:37 | OK |
| [[nvidia/cuda-stos]] | 13.3 | CUDA-AUDIT.md:34 | OK |
| [[nvidia/cuda-stos]] | 155 | CUDA-AUDIT.md:50 | OK |
| [[nvidia/cuda-stos]] | 16, 5060 | rx-7900-xtx.md:36 | OK |
| [[nvidia/cuda-stos]] | 2026 | rx-7900-xtx.md:34 | OK |
| [[nvidia/cuda-stos]] | 3060, 3090 | CUDA-AUDIT.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/cuda-stos]] | 3090 615.71, 580.173 | hw.json:6 | OK |
| [[nvidia/cuda-stos]] | 4.5, 835 | CUDA-AUDIT.md:48 | OK |
| [[nvidia/cuda-stos]] | 501, 80, 860 | times.jsonl:1 | OK |
| [[nvidia/cuda-stos]] | 503, 787 | times.jsonl:2 | OK |
| [[nvidia/cuda-stos]] | 799 | CUDA-AUDIT.md:46 | OK |
| [[nvidia/latki-na-nvidia]] | 0.0067 | CUDA-AUDIT.md:118 | OK |
| [[nvidia/latki-na-nvidia]] | 0001, 35 | CUDA-AUDIT.md:13 | OK |
| [[nvidia/latki-na-nvidia]] | 0003 | CUDA-AUDIT.md:15 | OK |
| [[nvidia/latki-na-nvidia]] | 0012 | CUDA-AUDIT.md:117 | OK |
| [[nvidia/latki-na-nvidia]] | 0013 | CUDA-AUDIT.md:12 | OK |
| [[nvidia/latki-na-nvidia]] | 0017 | CUDA-AUDIT.md:122 | OK |
| [[nvidia/latki-na-nvidia]] | 0018 | CUDA-AUDIT.md:123 | OK |
| [[nvidia/latki-na-nvidia]] | 0019 | CUDA-AUDIT.md:124 | OK |
| [[nvidia/latki-na-nvidia]] | 0023 | CUDA-AUDIT.md:16 | OK |
| [[nvidia/latki-na-nvidia]] | 0024 | CUDA-AUDIT.md:129 | OK |
| [[nvidia/latki-na-nvidia]] | 0027 | CUDA-AUDIT.md:132 | OK |
| [[nvidia/latki-na-nvidia]] | 0028 | CUDA-AUDIT.md:133 | OK |
| [[nvidia/latki-na-nvidia]] | 0033, 0036 | CUDA-AUDIT.md:136 | OK |
| [[nvidia/latki-na-nvidia]] | 0038 | CUDA-AUDIT.md:138 | OK |
| [[nvidia/latki-na-nvidia]] | 0043 | CUDA-AUDIT.md:17 | OK |
| [[nvidia/latki-na-nvidia]] | 0045 | CUDA-AUDIT.md:18 | OK |
| [[nvidia/latki-na-nvidia]] | 0049 | CUDA-AUDIT.md:147 | OK |
| [[nvidia/latki-na-nvidia]] | 0051 | CUDA-AUDIT.md:149 | OK |
| [[nvidia/latki-na-nvidia]] | 0053, 0057 | CUDA-AUDIT.md:10 | OK |
| [[nvidia/latki-na-nvidia]] | 0056 | CUDA-AUDIT.md:11 | OK |
| [[nvidia/latki-na-nvidia]] | 31 | PLAN-TESTOW.md:16 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/latki-na-nvidia]] | 70 | CUDA-AUDIT.md:99 | OK |
| [[nvidia/nvfp4]] | 0004 | rx-7900-xtx.md:38 | OK |
| [[nvidia/nvfp4]] | 0012 | rx-7900-xtx.md:13 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/nvfp4]] | 01 | 01-konkurencja.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/nvfp4]] | 1.14 | 22-lucebox.md:90 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/nvfp4]] | 2.5 | 01-konkurencja.md:200 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/nvfp4]] | 5060 | rx-7900-xtx.md:36 | OK |
| [[nvidia/nvfp4]] | 7900 | rx-7900-xtx.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 0.0005, 0.000505, 0.000944 | ręcznie | OK: tbo/summary.txt: ERR 0.000505463 / 0.000944348 > 0.000500000 (zaokrąglone) |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 0001 | summary.txt:1 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 0013 | PLAN-TESTOW.md:77 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 0018 | PLAN-TESTOW.md:81 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 0023 | PLAN-TESTOW.md:80 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 0043 | PLAN-TESTOW.md:78 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 19251 | summary.txt:4 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 194.8, 195.7, 196.2, 196.9, 199.4, 201.2, 236.3, 237.5, 245.3, 256.9, 258.2, 28.6, 28.9, 29.0, 29.3, 39.0, 39.4, 39.6, 40.2 | ręcznie | OK: lb/*.jsonl avg_ts tg128 zaokrąglone do 0.1 (wyciąg 2026-10-16) |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 2026, 3090 | lfm25-24b-q5.fork-tuned.r3.jsonl:1 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 3060 | PLAN-TESTOW.md:91 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 3090 192 | lfm25-24b-q4.fork-safe.r4.jsonl:3 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 31 | summary.txt:2 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 5060 | qwen38-27b-q3.fork-tuned.r6.jsonl:1 | OK |
| [[nvidia/nvidia-wyniki-2026-10-16]] | 999 | bench.sh:272 | OK |
| [[nvidia/sm-86-89-120]] | 0025, 0057 | CUDA-AUDIT.md:7 | OK |
| [[nvidia/sm-86-89-120]] | 0053 | CUDA-AUDIT.md:10 | OK |
| [[nvidia/sm-86-89-120]] | 1024,1 | CUDA-AUDIT.md:130 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia/sm-86-89-120]] | 12 | CUDA-AUDIT.md:178 | OK |
| [[nvidia/sm-86-89-120]] | 120, 16, 3060, 3090, 4060, 5060, 86 | CUDA-AUDIT.md:3 | OK |
| [[nvidia/sm-86-89-120]] | 147 | CUDA-AUDIT.md:40 | OK |
| [[nvidia/sm-86-89-120]] | 24 | PLAN-TESTOW.md:89 | OK |
| [[nvidia/sm-86-89-120]] | 32 | CUDA-AUDIT.md:181 | OK |
| [[nvidia/sm-86-89-120]] | 48 | CUDA-AUDIT.md:226 | OK |
| [[nvidia/sm-86-89-120]] | 64 | CUDA-AUDIT.md:222 | OK |
| [[nvidia/sm-86-89-120]] | 90 | CUDA-AUDIT.md:176 | OK |
| [[produkt/aplikacja-w-budowie]] | 2026 | docs.ts:15 | OK |
| [[produkt/aplikacja-w-budowie]] | 3.3, 8.1 | bun.lock:147 | OK |
| [[produkt/produkt-analiza-platformy]] | 0060 | PLAN.md:258 | OK |
| [[produkt/produkt-analiza-platformy]] | 10.1 | PLAN.md:257 | OK |
| [[produkt/produkt-analiza-platformy]] | 30 | PLAN.md:259 | OK |
| [[produkt/produkt-analiza-platformy]] | 4.4, 92 | PLAN.md:261 | OK |
| [[produkt/produkt-analiza-platformy]] | 4.5 | PLAN.md:252 | OK |
| [[produkt/produkt-anatomia-l0-l3]] | 1.5, 2.2, 38.8, 85.6 | PLAN.md:71 | OK |
| [[produkt/produkt-anatomia-l0-l3]] | 109, 198, 294, 30, 70 | PLAN.md:73 | OK |
| [[produkt/produkt-anatomia-l0-l3]] | 15 | PLAN.md:72 | OK |
| [[produkt/produkt-anatomia-l0-l3]] | 20, 4.4, 92 | PLAN.md:70 | OK |
| [[produkt/produkt-architektura]] | 0003 | PLAN.md:166 | OK |
| [[produkt/produkt-architektura]] | 0029, 0031, 0047, 0069 | PLAN.md:168 | OK |
| [[produkt/produkt-architektura]] | 10 | PLAN.md:164 | OK |
| [[produkt/produkt-architektura]] | 24 | PLAN.md:187 | OK |
| [[produkt/produkt-architektura]] | 300 | PLAN.md:173 | OK |
| [[produkt/produkt-biznes-edycje]] | 149, 299 | PLAN.md:340 | OK |
| [[produkt/produkt-budzet]] | 1.2, 1.5, 150, 2.5, 3.5, 50, 500, 600 | PLAN.md:468 | OK |
| [[produkt/produkt-budzet]] | 10 | PLAN.md:464 | OK |
| [[produkt/produkt-budzet]] | 20, 30 | PLAN.md:470 | OK |
| [[produkt/produkt-budzet]] | 270, 3060, 6700, 700, 7800, 9070 | PLAN.md:469 | OK |
| [[produkt/produkt-dla-kogo-i-ekrany]] | 10 | PLAN.md:98 | OK |
| [[produkt/produkt-dla-kogo-i-ekrany]] | 2026 | PLAN.md:116 | OK |
| [[produkt/produkt-dla-kogo-i-ekrany]] | 3060, 5090, 7800, 9070 | PLAN.md:92 | OK |
| [[produkt/produkt-dla-kogo-i-ekrany]] | 60 | PLAN.md:102 | OK |
| [[produkt/produkt-fabryka]] | 10 | PLAN.md:224 | OK |
| [[produkt/produkt-landing-i-onboarding]] | 2.2 | PLAN.md:371 | OK |
| [[produkt/produkt-landing-i-onboarding]] | 2026 | PLAN.md:358 | OK |
| [[produkt/produkt-landing-i-onboarding]] | 50 | PLAN.md:369 | OK |
| [[produkt/produkt-optymalizacja-u-uzytkownika]] | 30 | PLAN.md:201 | OK |
| [[produkt/produkt-optymalizacja-u-uzytkownika]] | 60 | PLAN.md:208 | OK |
| [[produkt/produkt-platformy-i-lab]] | 0.22 | PLAN.md:295 | OK |
| [[produkt/produkt-platformy-i-lab]] | 0.47 | PLAN.md:293 | OK |
| [[produkt/produkt-platformy-i-lab]] | 1,200, 7900, 800 | PLAN.md:292 | OK |
| [[produkt/produkt-platformy-i-lab]] | 12, 257, 3060 | PLAN.md:288 | OK |
| [[produkt/produkt-platformy-i-lab]] | 16, 474, 5060, 680 | PLAN.md:287 | OK |
| [[produkt/produkt-platformy-i-lab]] | 2026 | PLAN.md:275 | OK |
| [[produkt/produkt-platformy-i-lab]] | 270 | PLAN.md:291 | OK |
| [[produkt/produkt-platformy-i-lab]] | 3090, 4090, 5090 | PLAN.md:282 | OK |
| [[produkt/produkt-platformy-i-lab]] | 4060, 4070 | PLAN.md:296 | OK |
| [[produkt/produkt-platformy-i-lab]] | 5070, 6.15 | PLAN.md:290 | OK |
| [[produkt/produkt-platformy-i-lab]] | 694, 9070 | PLAN.md:289 | OK |
| [[produkt/produkt-platformy-i-lab]] | 76 | PLAN.md:277 | OK |
| [[produkt/produkt-prawo]] | 10, 275, 99 | PLAN.md:319 | OK |
| [[produkt/produkt-prawo]] | 30, 5.8, 55 | PLAN.md:331 | OK |
| [[produkt/produkt-prawo]] | 50 | PLAN.md:322 | OK |
| [[produkt/produkt-prawo]] | 9.12 | PLAN.md:325 | OK |
| [[produkt/produkt-roadmapa]] | 1.3 | PLAN.md:443 | OK |
| [[produkt/produkt-roadmapa]] | 10 | PLAN.md:422 | OK |
| [[produkt/produkt-roadmapa]] | 12, 3060, 5060 | PLAN.md:428 | OK |
| [[produkt/produkt-roadmapa]] | 500 | PLAN.md:452 | OK |
| [[produkt/produkt-roadmapa]] | 70 | PLAN.md:427 | OK |
| [[produkt/produkt-ryzyka]] | 50 | PLAN.md:484 | OK |
| [[produkt/produkt-ryzyka]] | 7900 | PLAN.md:479 | OK |
| [[produkt/produkt-stack]] | 127.0 | PLAN.md:309 | OK |
| [[produkt/produkt-stack]] | 15 | PLAN.md:307 | OK |
| [[produkt/werdykt]] | 1.5, 2.2 | PLAN.md:17 | OK |
| [[produkt/werdykt]] | 109, 40 | PLAN.md:16 | OK |
| [[produkt/werdykt]] | 12 | PLAN.md:26 | OK |
| [[produkt/werdykt]] | 15, 2026 | PLAN.md:3 | OK |
| [[produkt/werdykt]] | 30 | PLAN.md:10 | OK |
| [[produkt/werdykt]] | 70 | PLAN.md:18 | OK |
| [[repo/a-hamdi-gpu]] | 10 000, 220, 89.9 | 02-a-hamdi-gpu.md:13 | OK |
| [[repo/a-hamdi-gpu]] | 100 | 02-a-hamdi-gpu.md:1 | OK |
| [[repo/a-hamdi-gpu]] | 18.6, 34.3 | 02-a-hamdi-gpu.md:14 | OK |
| [[repo/a-hamdi-gpu]] | 2025, a9b0a17c | 02-a-hamdi-gpu.md:3 | OK |
| [[repo/a-hamdi-gpu]] | 512, 52.4 | 02-a-hamdi-gpu.md:15 | OK |
| [[repo/a-hamdi-gpu]] | 7900 | 02-a-hamdi-gpu.md:22 | OK |
| [[repo/ako4all]] | 175 | 21-ako4all.md:9 | OK |
| [[repo/ako4all]] | 2026, bbd0e1c | 21-ako4all.md:3 | OK |
| [[repo/ako4all]] | 54 | 21-ako4all.md:203 | OK |
| [[repo/amd-opt-v070]] | 0018 | 2026-10-16-rebase-v070.md:13 | OK |
| [[repo/amd-opt-v070]] | 2026, 70 | 2026-10-16-rebase-v070.md:8 | OK |
| [[repo/amd-opt-v070]] | 30257 | 2026-10-16-rebase-v070.md:15 | OK |
| [[repo/amd-opt-v070]] | 60, 69 | 2026-10-16-rebase-v070.md:10 | OK |
| [[repo/amd-opt-v070]] | 620, 620d2225c, 8c942e5a9 | 2026-10-16-rebase-v070.md:12 | OK |
| [[repo/amd-opt]] | 0001, 0070, 70 | seria-amd-opt.md:5 | OK |
| [[repo/amd-opt]] | 0057 | git:10 | OK |
| [[repo/amd-opt]] | 2026 | seria-amd-opt.md:4 | OK |
| [[repo/amd-opt]] | 7900 | ręcznie | OK: nazwa karty (identyfikator) |
| [[repo/amd-opt]] | c36fd2c87 | git:6 | OK |
| [[repo/amd-opt]] | e60eff95f, f61994f58 | seria-amd-opt.md:10 | OK |
| [[repo/atrex-kernel-agent]] | 1.55 | 25-atrex-kernel-agent.md:5 | OK |
| [[repo/atrex-kernel-agent]] | 2026, 5ad94ff | 25-atrex-kernel-agent.md:3 | OK |
| [[repo/atrex-kernel-agent]] | 3.7, 72.7 | 25-atrex-kernel-agent.md:43 | OK |
| [[repo/auto-gpu-kernel]] | 11.3, 20.6 | REPOS-PODSUMOWANIE.md:24 | OK |
| [[repo/auto-gpu-kernel]] | 128 | 14-auto-gpu-kernel.md:9 | OK |
| [[repo/auto-gpu-kernel]] | 16, 48 | 14-auto-gpu-kernel.md:15 | OK |
| [[repo/auto-gpu-kernel]] | 2026 | 14-auto-gpu-kernel.md:1 | OK |
| [[repo/auto-gpu-kernel]] | 54, db02153 | 14-auto-gpu-kernel.md:3 | OK |
| [[repo/auto-gpu-kernel]] | 54e3c5f | 14-auto-gpu-kernel.md:7 | OK |
| [[repo/batch-invariant]] | 2026, 6e261fdb4 | git:1 | OK |
| [[repo/batch-invariant]] | 204, 204f108de | git:3 | OK |
| [[repo/batch-invariant]] | 77240, 77240c9b3 | git:2 | OK |
| [[repo/batch-invariant]] | c09ac6aab | git:4 | OK |
| [[repo/blocksparse]] | 2020, 89074, 89074c5 | 12-blocksparse.md:3 | OK |
| [[repo/cuda-compat-galaz]] | 0053 | cuda-compat.md:16 | OK |
| [[repo/cuda-compat-galaz]] | 0056 | cuda-compat.md:17 | OK |
| [[repo/cuda-compat-galaz]] | 0057, 0070 | cuda-compat.md:14 | OK |
| [[repo/cuda-compat-galaz]] | 25, 579 | cuda-compat.md:19 | OK |
| [[repo/cuda-compat-galaz]] | 74 | git:52 | OK |
| [[repo/cuda-compat-galaz]] | 7b2680760 | cuda-compat.md:10 | OK |
| [[repo/cuda-compat-galaz]] | e60eff95f | git:112 | OK |
| [[repo/cuda-rust]] | 0.3, 2068.88, 96.35 | 29-cuda-rust.md:9 | OK |
| [[repo/cuda-rust]] | 0.81, 2.5 | REPOS-PODSUMOWANIE.md:39 | OK |
| [[repo/cuda-rust]] | 2026, bc46b1f | 29-cuda-rust.md:3 | OK |
| [[repo/cuda-rust]] | 5090 | 29-cuda-rust.md:11 | OK |
| [[repo/cuda-v070]] | 0053, 5dae6224f, 74 | git:2 | OK |
| [[repo/cuda-v070]] | 0056, 2026, 7a538d96f | git:1 | OK |
| [[repo/cuda-v070]] | 2600, 2600ad94a | git:12 | OK |
| [[repo/cuda-v070]] | 3060 | git:17 | OK |
| [[repo/cuda-v070]] | 3090 | git:21 | OK |
| [[repo/cuda-v070]] | 398, 398ded98d | git:3 | OK |
| [[repo/cuda-v070]] | 5060 | git:24 | OK |
| [[repo/cuda-v070]] | b479c67dd | git:4 | OK |
| [[repo/cuda-v070]] | da4748c4f | git:8 | OK |
| [[repo/cutile-python]] | 0.2, 0.45 | 13-cutile-python.md:47 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/cutile-python]] | 2026, d9d8520 | 13-cutile-python.md:3 | OK |
| [[repo/cutile-python]] | 32 | 13-cutile-python.md:11 | OK |
| [[repo/deepgemm]] | 0.2, 0.4 | REPOS-PODSUMOWANIE.md:51 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/deepgemm]] | 12 | REPOS-PODSUMOWANIE.md:18 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/deepgemm]] | 1fc9c66, 2026 | 03-deepgemm.md:3 | OK |
| [[repo/falkon]] | 04, 04f168e, 2026 | 24-falkon.md:3 | OK |
| [[repo/falkon]] | 20, 40 | REPOS-PODSUMOWANIE.md:34 | OK |
| [[repo/flashinfer-bench-starter-kit]] | 1.54, 2.05 | 27-flashinfer-bench-starter-kit.md:113 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/flashinfer-bench-starter-kit]] | 2.98 | 27-flashinfer-bench-starter-kit.md:114 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/flashinfer-bench-starter-kit]] | 2026, 75, 75ccd05 | 27-flashinfer-bench-starter-kit.md:3 | OK |
| [[repo/flashinfer]] | 0.6 | 07-flashinfer.md:107 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/flashinfer]] | 2026, 2895577 | 07-flashinfer.md:3 | OK |
| [[repo/flashinfer]] | 94 | 07-flashinfer.md:106 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/galezie-rund]] | 0d89ce56c | git:15 | OK |
| [[repo/galezie-rund]] | 16, 2026 | git:1 | OK |
| [[repo/galezie-rund]] | 2aa6999ed | git:28 | OK |
| [[repo/galezie-rund]] | 343, 343c2fbbb | git:29 | OK |
| [[repo/galezie-rund]] | 35, 35d04b446 | git:18 | OK |
| [[repo/galezie-rund]] | 3b053e5e2 | git:21 | OK |
| [[repo/galezie-rund]] | 40, 40c9bacdc | git:12 | OK |
| [[repo/galezie-rund]] | 4db68c6ab | git:34 | OK |
| [[repo/galezie-rund]] | 575, 575e3d893 | git:20 | OK |
| [[repo/galezie-rund]] | 5909, 5909da1f1 | git:22 | OK |
| [[repo/galezie-rund]] | 68, 68e163cf4 | git:11 | OK |
| [[repo/galezie-rund]] | 6c7801bf6 | git:26 | OK |
| [[repo/galezie-rund]] | 7e9c73d8b | git:33 | OK |
| [[repo/galezie-rund]] | 849, 849b69978 | git:17 | OK |
| [[repo/galezie-rund]] | 9d493cf6e | git:23 | OK |
| [[repo/galezie-rund]] | 9f83f1f81 | git:16 | OK |
| [[repo/galezie-rund]] | ae1ef6a97 | git:25 | OK |
| [[repo/galezie-rund]] | b1a203959 | git:31 | OK |
| [[repo/galezie-rund]] | b1f8c19ac | git:13 | OK |
| [[repo/galezie-rund]] | c90db29c6 | git:27 | OK |
| [[repo/galezie-rund]] | ce934a304 | git:14 | OK |
| [[repo/galezie-rund]] | d3a0973ae | git:19 | OK |
| [[repo/galezie-rund]] | e41c2330e | git:24 | OK |
| [[repo/galezie-rund]] | e84abb808 | git:30 | OK |
| [[repo/galezie-rund]] | f4f0deae5 | git:32 | OK |
| [[repo/gpu-kernel-engineer-from-scratch]] | 2026, ba738db | 19-gpu-kernel-engineer-from-scratch.md:3 | OK |
| [[repo/gpu-kernel-engineer-from-scratch]] | 48 | 19-gpu-kernel-engineer-from-scratch.md:7 | OK |
| [[repo/gpu-mode-reference-kernels]] | 2026, f3295bb6 | 09-gpu-mode-reference-kernels.md:3 | OK |
| [[repo/hipfire]] | 10, 1ff5182, 2026, 7900 | 30-hipfire.md:3 | OK |
| [[repo/hipfire]] | 104, 76.4 | 30-hipfire.md:17 | OK |
| [[repo/hipfire]] | 13, 307.9 | 30-hipfire.md:18 | OK |
| [[repo/hipfire]] | 219.6, 251.8, 35, 603 | REPOS-PODSUMOWANIE.md:40 | OK |
| [[repo/hipfire]] | 30 | 30-hipfire.md:1 | OK |
| [[repo/hipfire]] | 3000 | 30-hipfire.md:20 | OK |
| [[repo/hipfire]] | 4.25 | 30-hipfire.md:7 | OK |
| [[repo/how-to-optimize-in-gpu]] | 10.3, 16384, 8.4 | 08-how-to-optimize-in-gpu.md:21 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/how-to-optimize-in-gpu]] | 2023, 5d2def3e | 08-how-to-optimize-in-gpu.md:3 | OK |
| [[repo/how-to-optimize-in-gpu]] | 900 | 08-how-to-optimize-in-gpu.md:7 | OK |
| [[repo/ik-llama-cpp]] | 03 | 03-silniki-i-stack.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/ik-llama-cpp]] | 2024 | 03-silniki-i-stack.md:126 | OK |
| [[repo/ik-llama-cpp]] | 2026 | 03-silniki-i-stack.md:138 | OK |
| [[repo/ik-llama-cpp]] | 3,27 | 03-silniki-i-stack.md:129 | OK |
| [[repo/keops]] | 0.1, 29, 3.4, 4.10 | 20-keops.md:68 | OK |
| [[repo/keops]] | 0.3, 1.5 | 20-keops.md:133 | OK |
| [[repo/keops]] | 100, 2.4 | 20-keops.md:7 | OK |
| [[repo/keops]] | 2026, ef72bc90 | 20-keops.md:3 | OK |
| [[repo/kernel-tuner-repo]] | 20 | 26-kernel-tuner.md:11 | OK |
| [[repo/kernel-tuner-repo]] | 2026, 8e71bbf | 26-kernel-tuner.md:3 | OK |
| [[repo/kernelagent]] | 1.56, 2.02 | 06-kernelagent.md:21 | OK |
| [[repo/kernelagent]] | 2026, e0647170 | 06-kernelagent.md:3 | OK |
| [[repo/kernelbench]] | 100, 20, 50 | 04-kernelbench.md:7 | OK |
| [[repo/kernelbench]] | 2026, 423217, 423217d9 | 04-kernelbench.md:3 | OK |
| [[repo/laya-mlx]] | 0.1, 193, 27, 33, 464 | 10-post-training.md:42 | OK |
| [[repo/laya-mlx]] | 10 | 10-post-training.md:39 | OK |
| [[repo/laya-mlx]] | 13.4, 7.4 | 10-post-training.md:277 | OK |
| [[repo/laya-mlx]] | 2.2, 74 | 10-post-training.md:293 | OK |
| [[repo/laya-mlx]] | 2026 | 10-post-training.md:284 | OK |
| [[repo/laya-mlx]] | 322, 421 | 10-post-training.md:273 | OK |
| [[repo/llama-cpp-fork]] | 2026, 3060 | git:1 | OK |
| [[repo/llama-cpp-fork]] | 620, 620d2225c | git:73 | OK |
| [[repo/llama-cpp-fork]] | 70 | git:25 | OK |
| [[repo/llama-cpp-fork]] | b356fa262 | git:9 | OK |
| [[repo/llama-cpp-fork]] | e60eff95f | git:36 | OK |
| [[repo/llama-cpp-fork]] | f61994f58 | git:2 | OK |
| [[repo/lucebox]] | 1.5 | 22-lucebox.md:107 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/lucebox]] | 1.55, 267, 413 | 22-lucebox.md:46 | OK |
| [[repo/lucebox]] | 110, 130, 175, 300 | 22-lucebox.md:86 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/lucebox]] | 16 208.1, 32.3, 8 133.9 | 22-lucebox.md:15 | OK |
| [[repo/lucebox]] | 2026, 3090, 54132, 54132ca | 22-lucebox.md:3 | OK |
| [[repo/mixbench]] | 2026, 2070, a8cab0c | 23-mixbench.md:3 | OK |
| [[repo/mixbench]] | 33, 512 | 23-mixbench.md:7 | OK |
| [[repo/mixbench]] | 50 | 23-mixbench.md:78 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/mixbench]] | 720 | 23-mixbench.md:98 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/mkernel]] | 2026, 97, 97e916b | 16-mkernel.md:3 | OK |
| [[repo/mtp-train]] | 10, 17 | 10-post-training.md:32 | OK |
| [[repo/mtp-train]] | 2026, 532, 532fd1057 | git:1 | OK |
| [[repo/nvidia-open-gpu-kernel-modules]] | 2026, 6.8, 615.78, ca2d03e | 01-nvidia-open-gpu-kernel-modules.md:3 | OK |
| [[repo/nvidia-open-gpu-kernel-modules]] | 24.3, 27.2 | 01-nvidia-open-gpu-kernel-modules.md:31 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/nvidia-open-gpu-kernel-modules]] | 64 | 01-nvidia-open-gpu-kernel-modules.md:9 | OK |
| [[repo/opt-gdn6]] | 0d89ce56c, 16, 8.5 | REPORT.md:14 | OK |
| [[repo/opt-gdn6]] | 128, b4e819237 | REPORT.md:7 | OK |
| [[repo/opt-gdn6]] | 2026 | QWEN5-ROUND5.md:7 | OK |
| [[repo/opt-gdn6]] | 379 | REPORT.md:20 | OK |
| [[repo/opt-gdn6]] | 83, 94 | QWEN5-ROUND5.md:13 | OK |
| [[repo/opt-gdn6]] | c36fd2c87 | REPORT.md:6 | OK |
| [[repo/opt-mmq6]] | 0070 | REPORT.md:68 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/opt-mmq6]] | 128, 16 | REPORT.md:10 | OK |
| [[repo/opt-mmq6]] | 2026 | REPORT.md:159 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/opt-mmq6]] | 32, ae1ef6a97 | REPORT.md:7 | OK |
| [[repo/opt-mmq6]] | 64 | REPORT.md:11 | OK |
| [[repo/opt-qwen5]] | 0.61, 0.918 | QWEN5-ROUND5.md:22 | OK |
| [[repo/opt-qwen5]] | 00, 02, 2026, 45 | QWEN5-ROUND5.md:7 | OK |
| [[repo/opt-qwen5]] | 0b7b073b, c4708318 | QWEN5-ROUND5.md:11 | OK |
| [[repo/opt-qwen5]] | 1066, 1097, 2.6 | QWEN5-ROUND5.md:18 | OK |
| [[repo/opt-qwen5]] | 1094, 1173, 7.6 | QWEN5-ROUND5.md:20 | OK |
| [[repo/opt-qwen5]] | 11.9, 1219, 3.0, 3254 | QWEN5-ROUND5.md:21 | OK |
| [[repo/opt-qwen5]] | 2aa6999ed | QWEN5-ROUND5.md:19 | OK |
| [[repo/opt-qwen5]] | 5b1fdbc2f | QWEN5-ROUND5.md:14 | OK |
| [[repo/opt-qwen5]] | c36fd2c87 | QWEN5-ROUND5.md:1 | OK |
| [[repo/opt-samp]] | 0065, 0069 | seria-amd-opt.md:24 | OK |
| [[repo/opt-samp]] | 2026 | seria-amd-opt.md:23 | OK |
| [[repo/opt-samp]] | f4f0deae5 | git:32 | OK |
| [[repo/pplx-kernels]] | 1.31, 194.7, 256 | 05-pplx-kernels.md:9 | OK |
| [[repo/pplx-kernels]] | 41.6, 41.7 | 05-pplx-kernels.md:20 | OK |
| [[repo/pplx-kernels]] | f70d1eb7 | 05-pplx-kernels.md:3 | OK |
| [[repo/prism-llama-cpp]] | 0.17549, 0.17553, 8.6154, 8.6171 | bonsai.md:15 | OK |
| [[repo/prism-llama-cpp]] | 1,0, 1.76, 128, 20, 27, 5.93, 98.2 | 10-post-training.md:329 | OK |
| [[repo/prism-llama-cpp]] | 10, 2026 | bonsai.md:4 | OK |
| [[repo/prism-llama-cpp]] | 3060 | bonsai.md:5 | OK |
| [[repo/pygpubench]] | 0.5 | 28-pygpubench.md:63 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/pygpubench]] | 2026, 286841, 286841bf | 28-pygpubench.md:3 | OK |
| [[repo/pygpubench]] | 96 | 28-pygpubench.md:42 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/speculators-specforge]] | 0.6, 10, 80 | 10-post-training.md:86 | OK |
| [[repo/speculators-specforge]] | 2.2, 2.4, 3.74 | 10-post-training.md:87 | OK |
| [[repo/speculators-specforge]] | 3090 | 10-post-training.md:50 | OK |
| [[repo/strata]] | 0.0000, 11.7, 14.3 | README.md:23 | OK |
| [[repo/strata]] | 12, 1892, 19, 2026, 2231, 49, a0116b27 | README.md:3 | OK |
| [[repo/strata]] | 125 | README.md:31 | OK |
| [[repo/strata]] | 28.8 | README.md:34 | OK |
| [[repo/strata]] | 335 | README.md:194 | OK |
| [[repo/strata]] | 36, 48 | README.md:32 | OK |
| [[repo/strata]] | 39 | REPOS-PODSUMOWANIE.md:82 | OK |
| [[repo/strata]] | 512 | README.md:33 | OK |
| [[repo/strata]] | 7900 | README.md:1 | OK |
| [[repo/strata]] | 888 | issues.md:8 | OK |
| [[repo/tensara]] | 160 | 18-tensara.md:16 | OK |
| [[repo/tensara]] | 20 | 18-tensara.md:15 | OK |
| [[repo/tensara]] | 2026, fae96618 | 18-tensara.md:3 | OK |
| [[repo/tensorfold]] | 0efbd447, 12, 1560, 18, 2026, 235, 32, 552 | README.md:3 | OK |
| [[repo/tensorfold]] | 1.2, 1.4 | README.md:14 | OK |
| [[repo/tensorfold]] | 100 | README.md:9 | OK |
| [[repo/tensorfold]] | 126, 95.7 | README.md:21 | OK |
| [[repo/tensorfold]] | 16 | README.md:10 | OK |
| [[repo/tensorfold]] | 25.8, 27.2 | README.md:20 | OK |
| [[repo/tensorfold]] | 27 | README.md:1 | OK |
| [[repo/tensorfold]] | 490 | README.md:16 | OK |
| [[repo/tilegym]] | 2026, c742afc | 17-tilegym.md:3 | OK |
| [[repo/tilegym]] | 39 | 17-tilegym.md:86 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/tilegym]] | 888 | 17-tilegym.md:52 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/tilelang]] | 19, 19da924, 2026 | 10-tilelang.md:3 | OK |
| [[repo/tokamax]] | 2026, b500ee4 | 15-tokamax.md:3 | OK |
| [[repo/tokamax]] | 48 | 15-tokamax.md:7 | OK |
| [[repo/tools6]] | 14, 22 | REPORT.md:21 | OK |
| [[repo/tools6]] | 2026 | git:1 | OK |
| [[repo/tools6]] | 27 | REPORT.md:19 | OK |
| [[repo/tools6]] | 4db68c6ab | REPORT.md:8 | OK |
| [[repo/tools6]] | 65 | REPORT.md:1 | OK |
| [[repo/vllm-xpu-kernels]] | 0.15, 0.3 | 11-vllm-xpu-kernels.md:75 | OK (inny wiersz źródła, sprawdzone) |
| [[repo/vllm-xpu-kernels]] | 2026, 6b30c9b9 | 11-vllm-xpu-kernels.md:3 | OK |
| [[research/raport-01-konkurencja]] | 01, 10, 2026 | 01-konkurencja.md:1 | OK |
| [[research/raport-01-konkurencja]] | 14.4, 23.0 | 01-konkurencja.md:42 | OK |
| [[research/raport-01-konkurencja]] | 165, 190 | 01-konkurencja.md:49 | OK |
| [[research/raport-01-konkurencja]] | 25, 25.4 | 01-konkurencja.md:41 | OK |
| [[research/raport-01-konkurencja]] | 285, 61, 74.7 | 01-konkurencja.md:36 | OK |
| [[research/raport-01-konkurencja]] | 38 | 01-konkurencja.md:23 | OK |
| [[research/raport-01-konkurencja]] | 68.6, 7900, 85.6, 97.7 | 01-konkurencja.md:66 | OK |
| [[research/raport-02-autotuning]] | 02, 1.81 | 02-autotuning-i-agenci-kerneli.md:31 | OK |
| [[research/raport-02-autotuning]] | 1.0001 | 02-autotuning-i-agenci-kerneli.md:34 | OK |
| [[research/raport-02-autotuning]] | 1.41 | 02-autotuning-i-agenci-kerneli.md:32 | OK |
| [[research/raport-02-autotuning]] | 1.49, 3.13 | 02-autotuning-i-agenci-kerneli.md:35 | OK |
| [[research/raport-02-autotuning]] | 109, 59, 92 | 02-autotuning-i-agenci-kerneli.md:14 | OK |
| [[research/raport-02-autotuning]] | 131.7, 71.8 | 02-autotuning-i-agenci-kerneli.md:20 | OK |
| [[research/raport-02-autotuning]] | 15, 20 | 02-autotuning-i-agenci-kerneli.md:24 | OK |
| [[research/raport-02-autotuning]] | 163.1, 98.5 | 02-autotuning-i-agenci-kerneli.md:50 | OK |
| [[research/raport-02-autotuning]] | 22 | 02-autotuning-i-agenci-kerneli.md:26 | OK |
| [[research/raport-02-autotuning]] | 4.4 | 02-autotuning-i-agenci-kerneli.md:22 | OK |
| [[research/raport-03-silniki]] | 03 | 03-silniki-i-stack.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[research/raport-03-silniki]] | 10, 11 401, 2026, 24, 33, 69, 70, 803 | 03-silniki-i-stack.md:21 | OK |
| [[research/raport-03-silniki]] | 127.0 | 03-silniki-i-stack.md:40 | OK |
| [[research/raport-03-silniki]] | 147, 183, 254, 31, 373, 404, 654 | 03-silniki-i-stack.md:38 | OK |
| [[research/raport-03-silniki]] | 21, 87 | 03-silniki-i-stack.md:37 | OK |
| [[research/raport-03-silniki]] | 9.99, 99 | 03-silniki-i-stack.md:43 | OK |
| [[research/raport-04-sprzet]] | 0,1, 204 800, 22 569, 22 593 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:25 | OK |
| [[research/raport-04-sprzet]] | 0,31, 0,55, 169, 295, 70 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:30 | OK |
| [[research/raport-04-sprzet]] | 0,61, 0,67 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:29 | OK |
| [[research/raport-04-sprzet]] | 04 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[research/raport-04-sprzet]] | 09, 16,7, 76 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:47 | OK |
| [[research/raport-04-sprzet]] | 131 072, 17 996, 17 997, 24 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:26 | OK |
| [[research/raport-04-sprzet]] | 16, 32.0, 4080 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:19 | OK |
| [[research/raport-04-sprzet]] | 26,71, 27,21 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:48 | OK |
| [[research/raport-04-sprzet]] | 30 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:16 | OK |
| [[research/raport-04-sprzet]] | 32 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:18 | OK |
| [[research/raport-05-chmura]] | 0.04, 0.17, 7800, 9070 | 05-chmura-gpu-do-testow.md:23 | OK |
| [[research/raport-05-chmura]] | 0.08, 3060 | 05-chmura-gpu-do-testow.md:14 | OK |
| [[research/raport-05-chmura]] | 0.16, 16, 5060 | 05-chmura-gpu-do-testow.md:17 | OK |
| [[research/raport-05-chmura]] | 0.22 | 05-chmura-gpu-do-testow.md:28 | OK |
| [[research/raport-05-chmura]] | 0.23, 3090 | 05-chmura-gpu-do-testow.md:15 | OK |
| [[research/raport-05-chmura]] | 0.29, 5070 | 05-chmura-gpu-do-testow.md:18 | OK |
| [[research/raport-05-chmura]] | 0.471 | 05-chmura-gpu-do-testow.md:24 | OK |
| [[research/raport-05-chmura]] | 0.51, 4090 | 05-chmura-gpu-do-testow.md:16 | OK |
| [[research/raport-05-chmura]] | 0.73, 445, 5090 | 05-chmura-gpu-do-testow.md:19 | OK |
| [[research/raport-05-chmura]] | 05 | 05-chmura-gpu-do-testow.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[research/raport-05-chmura]] | 1,224 | 05-chmura-gpu-do-testow.md:43 | OK |
| [[research/raport-05-chmura]] | 1.2, 1.5, 2.5, 3.5, 500, 600 | 05-chmura-gpu-do-testow.md:58 | OK |
| [[research/raport-05-chmura]] | 190, 80 | 05-chmura-gpu-do-testow.md:21 | OK |
| [[research/raport-05-chmura]] | 2026 | 05-chmura-gpu-do-testow.md:13 | OK |
| [[research/raport-05-chmura]] | 24 | 05-chmura-gpu-do-testow.md:27 | OK |
| [[research/raport-05-chmura]] | 257 | 05-chmura-gpu-do-testow.md:47 | OK |
| [[research/raport-05-chmura]] | 694 | 05-chmura-gpu-do-testow.md:46 | OK |
| [[research/raport-05-chmura]] | 7900 | 05-chmura-gpu-do-testow.md:22 | OK |
| [[research/raport-05-chmura]] | 837 | 05-chmura-gpu-do-testow.md:45 | OK |
| [[research/raport-05-chmura]] | 90 | 05-chmura-gpu-do-testow.md:42 | OK |
| [[research/raport-06-produkt]] | 06 | 06-produkt-ux-prawo-biznes.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[research/raport-06-produkt]] | 1,17, 109, 2,69, 40, 90 | 06-produkt-ux-prawo-biznes.md:24 | OK |
| [[research/raport-06-produkt]] | 10 | 06-produkt-ux-prawo-biznes.md:34 | OK |
| [[research/raport-06-produkt]] | 12,93 | 06-produkt-ux-prawo-biznes.md:19 | OK |
| [[research/raport-06-produkt]] | 200 | 06-produkt-ux-prawo-biznes.md:37 | OK |
| [[research/raport-06-produkt]] | 2026, 65 | 06-produkt-ux-prawo-biznes.md:17 | OK |
| [[research/raport-06-produkt]] | 39, 79 | 06-produkt-ux-prawo-biznes.md:57 | OK |
| [[research/raport-06-produkt]] | 50 | 06-produkt-ux-prawo-biznes.md:36 | OK |
| [[research/raport-07-metody]] | 0011, 45 | 07-nasze-metody-uogolnienie.md:7 | OK |
| [[research/raport-07-metody]] | 07, 3.40, 5.07 | 07-nasze-metody-uogolnienie.md:24 | OK |
| [[research/raport-07-metody]] | 10, 12, 70 | 07-nasze-metody-uogolnienie.md:3 | OK |
| [[research/raport-07-metody]] | 11, 169.3, 17, 198, 198.3, 295, 49 | 07-nasze-metody-uogolnienie.md:26 | OK |
| [[research/raport-07-metody]] | 18 | 07-nasze-metody-uogolnienie.md:13 | OK |
| [[research/raport-07-metody]] | 182, 20, 35, 6.4, 6.8 | 07-nasze-metody-uogolnienie.md:38 | OK |
| [[research/raport-07-metody]] | 2.2, 38.8, 60, 85.6 | 07-nasze-metody-uogolnienie.md:27 | OK |
| [[research/raport-07-metody]] | 22 | 07-nasze-metody-uogolnienie.md:12 | OK |
| [[research/raport-07-metody]] | 27, 27.74, 30, 41.7, 48 | 07-nasze-metody-uogolnienie.md:23 | OK |
| [[research/raport-08-platforma]] | 0001 | 08-analiza-platformy-latek.md:12 | OK |
| [[research/raport-08-platforma]] | 0022 | 08-analiza-platformy-latek.md:27 | OK |
| [[research/raport-08-platforma]] | 0042 | 08-analiza-platformy-latek.md:26 | OK |
| [[research/raport-08-platforma]] | 0048, 0065, 0069, 13, 15 | 08-analiza-platformy-latek.md:39 | OK |
| [[research/raport-08-platforma]] | 0054 | 08-analiza-platformy-latek.md:25 | OK |
| [[research/raport-08-platforma]] | 0060, 0061 | 08-analiza-platformy-latek.md:19 | OK |
| [[research/raport-08-platforma]] | 07 | 08-analiza-platformy-latek.md:23 | OK |
| [[research/raport-08-platforma]] | 08, 70 | 08-analiza-platformy-latek.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[research/raport-08-platforma]] | 1.736, 14, 14.14 | 08-analiza-platformy-latek.md:29 | OK |
| [[research/raport-08-platforma]] | 16 | 08-analiza-platformy-latek.md:36 | OK |
| [[research/raport-08-platforma]] | 25 | 08-analiza-platformy-latek.md:35 | OK |
| [[research/raport-08-platforma]] | 73 | 08-analiza-platformy-latek.md:34 | OK |
| [[research/raport-10-post-training]] | 0.21, 3090 | 10-post-training.md:13 | OK |
| [[research/raport-10-post-training]] | 0.73, 80 | 10-post-training.md:18 | OK |
| [[research/raport-10-post-training]] | 00, 30 | 10-post-training.md:9 | OK |
| [[research/raport-10-post-training]] | 1.83, 2.73, 3.0, 3.3, 4.2, 6.8 | 10-post-training.md:31 | OK |
| [[research/raport-10-post-training]] | 10 | 10-post-training.md:1 | OK |
| [[research/raport-10-post-training]] | 14 | 10-post-training.md:42 | OK |
| [[research/raport-10-post-training]] | 16, 2026 | 10-post-training.md:3 | OK |
| [[research/raport-10-post-training]] | 17 | 10-post-training.md:32 | OK |
| [[research/raport-10-post-training]] | 2.2, 2.4, 3.74 | 10-post-training.md:35 | OK |
| [[research/raport-10-post-training]] | 3.07 | 10-post-training.md:20 | OK |
| [[research/raport-12-bit-exact]] | 0.3, 1.3 | 12-bit-exact-spekulacja.md:91 | OK |
| [[research/raport-12-bit-exact]] | 0.5, 32 | 12-bit-exact-spekulacja.md:87 | OK |
| [[research/raport-12-bit-exact]] | 1.5, 98 | 12-bit-exact-spekulacja.md:88 | OK |
| [[research/raport-12-bit-exact]] | 12 | 12-bit-exact-spekulacja.md:1 | OK |
| [[research/raport-12-bit-exact]] | 2026, 8c942e5a9 | 12-bit-exact-spekulacja.md:3 | OK |
| [[research/raport-12-bit-exact]] | 36 | 12-bit-exact-spekulacja.md:106 | OK |
| [[research/raport-12-bit-exact]] | 6f14e814, c4708318 | 12-bit-exact-spekulacja.md:8 | OK |
| [[research/raport-12-bit-exact]] | 862 | 12-bit-exact-spekulacja.md:98 | OK |
| [[research/raport-13-rocm-10-1]] | 0060, 7900 | 13-rocm-10.1.md:24 | OK |
| [[research/raport-13-rocm-10-1]] | 10.0 | 13-rocm-10.1.md:5 | OK |
| [[research/raport-13-rocm-10-1]] | 10.1, 13 | 13-rocm-10.1.md:1 | OK |
| [[research/raport-13-rocm-10-1]] | 11, 2.67, 24 | 13-rocm-10.1.md:4 | OK |
| [[research/raport-13-rocm-10-1]] | 2026 | 13-rocm-10.1.md:3 | OK |
| [[research/raport-13-rocm-10-1]] | 256, 98 | 13-rocm-10.1.md:20 | OK |
| [[research/repos-30-przeglad]] | 10, 2026 | REPOS-PODSUMOWANIE.md:3 | OK |
| [[research/repos-30-przeglad]] | 104, 2.5, 240, 28.9, 4.1, 416 | REPOS-PODSUMOWANIE.md:5 | OK |
| [[research/repos-30-przeglad]] | 110, 130, 175 | REPOS-PODSUMOWANIE.md:63 | OK |
| [[research/repos-30-przeglad]] | 16 | REPOS-PODSUMOWANIE.md:20 | OK |
| [[research/repos-30-przeglad]] | 219.6, 251.8 | REPOS-PODSUMOWANIE.md:40 | OK |
| [[research/repos-30-przeglad]] | 30 | REPOS-PODSUMOWANIE.md:1 | OK |
| [[research/repos-30-przeglad]] | 300 | REPOS-PODSUMOWANIE.md:49 | OK |
| [[research/repos-30-przeglad]] | 39 | REPOS-PODSUMOWANIE.md:82 | OK |
| [[research/repos-30-przeglad]] | 54 | REPOS-PODSUMOWANIE.md:31 | OK |
| [[research/runda-6-raporty]] | 0070 | mmq-epilogue.md:68 | OK (inny wiersz źródła, sprawdzone) |
| [[research/runda-6-raporty]] | 0d89ce56c | gdn-bitwise.md:14 | OK |
| [[research/runda-6-raporty]] | 14, 22 | test-tooling.md:21 | OK |
| [[research/runda-6-raporty]] | 2026 | gdn-bitwise.md:176 | OK (inny wiersz źródła, sprawdzone) |
| [[research/runda-6-raporty]] | 27 | test-tooling.md:19 | OK |
| [[research/runda-6-raporty]] | 379 | gdn-bitwise.md:20 | OK |
| [[research/runda-6-raporty]] | 64 | mmq-epilogue.md:11 | OK |
| [[research/runda-6-raporty]] | ae1ef6a97 | mmq-epilogue.md:7 | OK |
| [[research/runda-6-raporty]] | b4e819237 | gdn-bitwise.md:7 | OK |
| [[rocm/amd-smi]] | 10.0 | 13-rocm-10.1.md:27 | OK |
| [[rocm/amd-smi]] | 10.1 | 13-rocm-10.1.md:28 | OK |
| [[rocm/amd-smi]] | 13 | 13-rocm-10.1.md:267 | OK |
| [[rocm/amd-smi]] | 2026 | 13-rocm-10.1.md:276 | OK |
| [[rocm/amd-smi]] | 27.0 | ręcznie | OK: amd-smi version: AMDSMI Tool 27.0.0 (2026-10-16) |
| [[rocm/amd-smi]] | 27.1 | 13-rocm-10.1.md:265 | OK |
| [[rocm/amd-smi]] | 5.3 | 13-rocm-10.1.md:279 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 10, 20, 2026 | NOTES.md:109 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 106, 196, 281, 66, 76 | NOTES.md:118 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 15 | NOTES.md:104 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 25, 40 | NOTES.md:119 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 272, 303, 350 | NOTES.md:110 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 285, 90, 90.6, 94.1, 94.7 | NOTES.md:126 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 305 | NOTES.md:112 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 4.4, 92 | NOTES.md:124 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 64 | NOTES.md:145 | OK |
| [[rocm/amdgpu-moc-i-termika]] | 67, 85, 88 | NOTES.md:146 | OK |
| [[rocm/hip-graph-narzut]] | 0.5 | rr-hip.md:86 | OK (inny wiersz źródła, sprawdzone) |
| [[rocm/hip-graph-narzut]] | 0.876, 3.865, 6409 | rr-hip.md:20 | OK |
| [[rocm/hip-graph-narzut]] | 0.9 | rr-hip.md:160 | OK (inny wiersz źródła, sprawdzone) |
| [[rocm/hip-graph-narzut]] | 16, 2026 | rr-hip.md:3 | OK |
| [[rocm/hip-graph-narzut]] | 19, 3.2, 3.22, 3.23, 3.27, 3.4, 7.13 | rr-hip.md:18 | OK |
| [[rocm/hip-graph-narzut]] | 2000 | NOTES.md:93 | OK |
| [[rocm/hip-graph-narzut]] | 2156 | NOTES.md:223 | OK (inny wiersz źródła, sprawdzone) |
| [[rocm/hip-graph-narzut]] | 2188, 29.8, 36.7, 36.9 | rr-hip.md:12 | OK |
| [[rocm/hip-graph-narzut]] | 3.3 | rr-hip.md:74 | OK (inny wiersz źródła, sprawdzone) |
| [[rocm/hip-graph-narzut]] | 830 | NOTES.md:265 | OK (inny wiersz źródła, sprawdzone) |
| [[rocm/hip-na-windows]] | 0019, 0057 | 08-analiza-platformy-latek.md:42 | OK |
| [[rocm/hip-na-windows]] | 0060, 2026, 8900 | 08-analiza-platformy-latek.md:19 | OK |
| [[rocm/hip-na-windows]] | 08 | PLAN.md:257 | OK |
| [[rocm/hip-na-windows]] | 10.0 | 08-analiza-platformy-latek.md:65 | OK |
| [[rocm/hip-na-windows]] | 6713 | 08-analiza-platformy-latek.md:56 | OK |
| [[rocm/hip-na-windows]] | 7.2 | 08-analiza-platformy-latek.md:52 | OK |
| [[rocm/hip]] | 128, 32 | Optymalizacja kerneli na AMD.md:27 | OK |
| [[rocm/hip]] | 131 | gdn-bitwise.md:130 | OK |
| [[rocm/hip]] | 2026 | NOTES.md:241 | OK |
| [[rocm/hip]] | 40 | NOTES.md:249 | OK |
| [[rocm/pm4]] | 0.262 | lfm-decode-round4.md:44 | OK |
| [[rocm/pm4]] | 0.731 | lfm-decode-round4.md:43 | OK |
| [[rocm/pm4]] | 0.858 | lfm-decode-round4.md:40 | OK |
| [[rocm/pm4]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[rocm/pm4]] | 1.874 | lfm-decode-round4.md:39 | OK |
| [[rocm/pm4]] | 10.0 | lfm-decode-round4.md:18 | OK |
| [[rocm/pm4]] | 13 | 13-rocm-10.1.md:243 | OK |
| [[rocm/pm4]] | 2.754 | lfm-decode-round4.md:30 | OK |
| [[rocm/pm4]] | 2026 | NOTES.md:372 | OK |
| [[rocm/rdna3-gfx1100]] | 12, 128, 1536, 16, 192, 256 | rx-7900-xtx.md:13 | OK |
| [[rocm/rdna3-gfx1100]] | 123 | rx-7900-xtx.md:17 | OK |
| [[rocm/rdna3-gfx1100]] | 24, 384, 960 | rx-7900-xtx.md:16 | OK |
| [[rocm/rdna3-gfx1100]] | 32, 48, 96 | rx-7900-xtx.md:11 | OK |
| [[rocm/rdna3-gfx1100]] | 512 | Optymalizacja kerneli na AMD.md:11 | OK |
| [[rocm/rdna3-gfx1100]] | 7600, 7800 | Optymalizacja kerneli na AMD.md:7 | OK |
| [[rocm/rdna3-gfx1100]] | 7900 | rx-7900-xtx.md:6 | OK |
| [[rocm/rocm-10-1]] | 1.21 | 13-rocm-10.1.md:27 | OK |
| [[rocm/rocm-10-1]] | 10, 10.1, 13 | 13-rocm-10.1.md:1 | OK |
| [[rocm/rocm-10-1]] | 10.0, 23 | 13-rocm-10.1.md:5 | OK |
| [[rocm/rocm-10-1]] | 11, 2.67, 24, 24.0 | 13-rocm-10.1.md:4 | OK |
| [[rocm/rocm-10-1]] | 2026 | 13-rocm-10.1.md:3 | OK |
| [[rocm/rocm-10-1]] | 256, 98 | 13-rocm-10.1.md:20 | OK |
| [[rocm/rocm-stos]] | 1.21 | 13-rocm-10.1.md:27 | OK |
| [[rocm/rocm-stos]] | 10.0, 2026, 7.14, 7900 | Optymalizacja kerneli na AMD.md:31 | OK |
| [[rocm/rocm-stos]] | 10.1 | Optymalizacja kerneli na AMD.md:29 | OK |
| [[rocm/rocm-stos]] | 13 | rocm_stack.md:11 | OK |
| [[rocm/rocm-stos]] | 23.0 | 13-rocm-10.1.md:5 | OK |
| [[rocm/rocm-stos]] | 27.0 | ręcznie | OK: amd-smi version: AMDSMI Tool 27.0.0 (2026-10-16) |
| [[rocm/rocm-stos]] | 31.50 | ręcznie | OK: ~/amdgpu-install_31.50.315000-1_all.deb |
| [[rocm/rocm-stos]] | 6.8 | 13-rocm-10.1.md:23 | OK (inny wiersz źródła, sprawdzone) |
| [[rocm/rocm-vs-vulkan]] | 03, 170.1, 190.9, 20934, 25, 7900 | Optymalizacja kerneli na AMD.md:75 | OK |
| [[rocm/rocm-vs-vulkan]] | 1.7, 13.3, 15, 15.0 | NOTES.md:175 | OK |
| [[rocm/rocm-vs-vulkan]] | 1000 | NOTES.md:173 | OK |
| [[rocm/rocm-vs-vulkan]] | 1044, 16, 622, 850, 890 | NOTES.md:16 | OK |
| [[rocm/rocm-vs-vulkan]] | 109 | NOTES.md:280 | OK (inny wiersz źródła, sprawdzone) |
| [[rocm/rocm-vs-vulkan]] | 11 | NOTES.md:179 | OK |
| [[rocm/rocm-vs-vulkan]] | 165, 260, 94 | NOTES.md:178 | OK |
| [[rocm/rocm-vs-vulkan]] | 20.3, 21.2, 6.6 | NOTES.md:176 | OK |
| [[rocm/rocm-vs-vulkan]] | 2026 | NOTES.md:172 | OK |
| [[rocm/rocm-vs-vulkan]] | 204800 | NOTES.md:6 | OK |
| [[rocm/rocm-vs-vulkan]] | 29.5, 50.2, 62.4 | NOTES.md:177 | OK |
| [[rocm/rocm-vs-vulkan]] | 64, 85.5 | NOTES.md:11 | OK |
| [[rocm/rocm-vs-vulkan]] | 88.1 | NOTES.md:12 | OK |
| [[rocm/rocm-vs-vulkan]] | 91.8 | NOTES.md:13 | OK |
| [[rocm/rocprof]] | 0060 | NOTES.md:372 | OK |
| [[rocm/rocprof]] | 10.0 | 13-rocm-10.1.md:18 | OK |
| [[rocm/rocprof]] | 1200, 15.5 | NOTES.md:184 | OK |
| [[rocm/rocprof]] | 13 | NOTES.md:258 | OK |
| [[rocm/rocprof]] | 2026 | NOTES.md:182 | OK |
| [[rocm/rocr]] | 0060, 2026, 8900 | 08-analiza-platformy-latek.md:19 | OK |
| [[rocm/rocr]] | 1.21 | 13-rocm-10.1.md:27 | OK |
| [[rocm/rocr]] | 10.1 | 13-rocm-10.1.md:28 | OK |
| [[rocm/rocr]] | 2.08 | lfm-decode-round4.md:47 | OK |
| [[rocm/rocr]] | 2.75 | lfm-decode-round4.md:57 | OK |
| [[rocm/therock]] | 0060 | 03-silniki-i-stack.md:605 | OK |
| [[rocm/therock]] | 03, 10, 10.1, 2026, 7.14 | rocm_stack.md:11 | OK |
| [[rocm/therock]] | 0a20260930, 10.2, 604 | 03-silniki-i-stack.md:71 | OK |
| [[rocm/therock]] | 100, 50 | 03-silniki-i-stack.md:70 | OK |
| [[rocm/therock]] | 183, 654 | 03-silniki-i-stack.md:608 | OK |
| [[rocm/therock]] | 700 | 03-silniki-i-stack.md:364 | OK |
| [[rocm/therock]] | 947 | 03-silniki-i-stack.md:367 | OK |
| [[rocm/wsl2-rocm]] | 0060, 7900 | 13-rocm-10.1.md:24 | OK |
| [[rocm/wsl2-rocm]] | 10.1 | 13-rocm-10.1.md:30 | OK |
| [[rocm/wsl2-rocm]] | 13 | 13-rocm-10.1.md:243 | OK |
| [[rocm/wsl2-rocm]] | 4.5 | 13-rocm-10.1.md:253 | OK |
| [[rocm/wsl2-rocm]] | 7800, 9070 | 13-rocm-10.1.md:226 | OK |
| [[rocm/wsl2-rocm]] | 8791 | 13-rocm-10.1.md:224 | OK |
| [[aplikacja-w-budowie]] | 0,12, 2026, 3090, 47, 5060, 56 | app/REPORT.md, DESIGN.md, APP-ARCHITECTURE.md, scan/TEST-linux.txt, PLAN.md | OK |
| [[aplikacja-w-budowie]] | 9f96ff4 | git log -1 9f96ff4 | OK: commit istnieje |
| [[app-system-projektowy]] | #07080D, #3B6E00, #3DD6FF, #5BE49B, #C8FF3D, #FF4D8D, #FFB23E, 07080, 110, 270, 32, 4,5 | app/REPORT.md, DESIGN.md, APP-ARCHITECTURE.md, scan/TEST-linux.txt, PLAN.md | OK |
| [[app-landing]] | 100, 109,0, 1280, 2.70, 200, 249, 3090, 38,8, 390, 4.14, 47, 50, 7900, 96, 98 | app/REPORT.md, DESIGN.md, APP-ARCHITECTURE.md, scan/TEST-linux.txt, PLAN.md | OK |
| [[app-onboarding-prototyp]] | 0,31, 0,55, 0,67, 04, 1,5, 2,2, 2.0, 24, 59, 64, 7900, 8628 | app/REPORT.md, DESIGN.md, APP-ARCHITECTURE.md, scan/TEST-linux.txt, PLAN.md | OK |
| [[app-skrypty-skanu]] | 03, 2026, 30, 31, 65521 | app/REPORT.md, DESIGN.md, APP-ARCHITECTURE.md, scan/TEST-linux.txt, PLAN.md | OK |
| [[app-prototyp-desktop]] | 0600, 11500, 13, 256 | app/REPORT.md, DESIGN.md, APP-ARCHITECTURE.md, scan/TEST-linux.txt, PLAN.md | OK |
| [[otwarte-decyzje-produktu]] | 11500, 127.0, 149, 18433, 19, 2026, 299, 39, 50, 79, 8.1 | app/REPORT.md, DESIGN.md, APP-ARCHITECTURE.md, scan/TEST-linux.txt, PLAN.md | OK |

## Aktualizacja: wyniki finalne (raporty 09, 11, 12; 2026-10-16 rano)
Ta sama metoda dla 41 notatek nowych lub zmienionych (raporty 09 ×3, 11, 12; karty, NVIDIA, eksperymenty, modele, lekcje, kernele, repo, chmura, index): **998 liczb sprawdzonych, 0 błędnych**; 913 w cytowanych wierszach, 77 w innym wierszu tego samego źródła (przejrzane ręcznie), 8 ręcznie. Przy okazji poprawione stare twierdzenie w [[latki-na-nvidia]]: łatka 0043 na NVIDIA nie zmienia bitów (no-op), wbrew wcześniejszemu wpisowi z PLAN-TESTOW. Uzupełniono `zrodlo` w [[rtx-3090]] (czas buildu 787 s z `build/times.jsonl`).

| notatka | liczby | wiersz źródła | status |
|---|---|---|---|
| [[raport-09-chmura-3090]] | 0.40 | 09-chmura-3090.md:165 | OK |
| [[raport-09-chmura-3090]] | 0.90, 1.90 | 09-chmura-3090.md:183 | OK |
| [[raport-09-chmura-3090]] | 0001 | 09-chmura-3090.md:9 | OK |
| [[raport-09-chmura-3090]] | 0013 | 09-chmura-3090.md:81 | OK |
| [[raport-09-chmura-3090]] | 08 | 09-chmura-3090.md:3 | OK |
| [[raport-09-chmura-3090]] | 09, 2026, 3090 | 09-chmura-3090.md:1 | OK |
| [[raport-09-chmura-3090]] | 1.23, 2.0 | 09-chmura-3090.md:196 | OK |
| [[raport-09-chmura-3090]] | 1.4 | 09-chmura-3090.md:108 | OK |
| [[raport-09-chmura-3090]] | 1.46, 264 | 09-chmura-3090.md:197 | OK |
| [[raport-09-chmura-3090]] | 132.4, 144.2 | 09-chmura-3090.md:83 | OK |
| [[raport-09-chmura-3090]] | 176.0 | 09-chmura-3090.md:58 | OK |
| [[raport-09-chmura-3090]] | 18 | 09-chmura-3090.md:31 | OK |
| [[raport-09-chmura-3090]] | 180, 180.2 | 09-chmura-3090.md:57 | OK |
| [[raport-09-chmura-3090]] | 180.5 | 09-chmura-3090.md:172 | OK |
| [[raport-09-chmura-3090]] | 1956 | 09-chmura-3090.md:137 | OK |
| [[raport-09-chmura-3090]] | 249.3 | 09-chmura-3090.md:59 | OK |
| [[raport-09-chmura-3090]] | 256.8 | 09-chmura-3090.md:123 | OK |
| [[raport-09-chmura-3090]] | 263.9, 284.5 | 09-chmura-3090.md:61 | OK |
| [[raport-09-chmura-3090]] | 30, 41 | 09-chmura-3090.md:155 | OK |
| [[raport-09-chmura-3090]] | 300, 350 | 09-chmura-3090.md:16 | OK |
| [[raport-09-chmura-3090]] | 357 | 09-chmura-3090.md:140 | OK |
| [[raport-09-chmura-3090]] | 38.4, 78, 78.0 | 09-chmura-3090.md:49 | OK |
| [[raport-09-chmura-3090]] | 38.9, 39 | 09-chmura-3090.md:46 | OK |
| [[raport-09-chmura-3090]] | 39.0, 63.3 | 09-chmura-3090.md:47 | OK |
| [[raport-09-chmura-3090]] | 3da7a02ec | 09-chmura-3090.md:110 | OK |
| [[raport-09-chmura-3090]] | 40.1 | 09-chmura-3090.md:122 | OK |
| [[raport-09-chmura-3090]] | 43.0 | 09-chmura-3090.md:51 | OK |
| [[raport-09-chmura-3090]] | 4589, 4589b2ea, eac36830 | 09-chmura-3090.md:67 | OK |
| [[raport-09-chmura-3090]] | 6.5 | 09-chmura-3090.md:93 | OK |
| [[raport-09-chmura-3090]] | 64 | 09-chmura-3090.md:133 | OK |
| [[raport-09-chmura-3090]] | 69.5 | 09-chmura-3090.md:48 | OK |
| [[raport-09-chmura-3090]] | 7.2, 8.5 | 09-chmura-3090.md:103 | OK |
| [[raport-09-chmura-3090]] | 7.68 | 09-chmura-3090.md:18 | OK |
| [[raport-09-chmura-3090]] | 74.5 | 09-chmura-3090.md:50 | OK |
| [[raport-09-chmura-3090]] | 795 | 09-chmura-3090.md:138 | OK |
| [[raport-09-chmura-3090]] | 8.7 | 09-chmura-3090.md:107 | OK |
| [[raport-09-chmura-3090]] | 80 | 09-chmura-3090.md:13 | OK |
| [[raport-09-chmura-3090]] | 908 | 09-chmura-3090.md:139 | OK |
| [[raport-09-chmura-3090]] | 91 | 09-chmura-3090.md:146 | OK |
| [[raport-09-chmura-3090]] | 949, 949a753b | 09-chmura-3090.md:70 | OK |
| [[raport-09-chmura-5060ti]] | 0.0265 | 09-chmura-5060ti.md:174 | OK |
| [[raport-09-chmura-5060ti]] | 0.0865 | 09-chmura-5060ti.md:175 | OK |
| [[raport-09-chmura-5060ti]] | 0.2029, 226.8 | 09-chmura-5060ti.md:177 | OK |
| [[raport-09-chmura-5060ti]] | 08 | 09-chmura-5060ti.md:80 | OK |
| [[raport-09-chmura-5060ti]] | 09, 16, 5060 | 09-chmura-5060ti.md:1 | OK |
| [[raport-09-chmura-5060ti]] | 1.05, 165.5, 207.7, 65 | 09-chmura-5060ti.md:86 | OK |
| [[raport-09-chmura-5060ti]] | 1.1826 | 09-chmura-5060ti.md:178 | OK |
| [[raport-09-chmura-5060ti]] | 1.38, 1.84 | 09-chmura-5060ti.md:200 | OK |
| [[raport-09-chmura-5060ti]] | 1.41, 148 | 09-chmura-5060ti.md:201 | OK |
| [[raport-09-chmura-5060ti]] | 1.7, 2.7, 69 | 09-chmura-5060ti.md:124 | OK |
| [[raport-09-chmura-5060ti]] | 120.9 | 09-chmura-5060ti.md:166 | OK |
| [[raport-09-chmura-5060ti]] | 180 | 09-chmura-5060ti.md:14 | OK |
| [[raport-09-chmura-5060ti]] | 19251, 5.0, 5.05, 9.44 | 09-chmura-5060ti.md:35 | OK |
| [[raport-09-chmura-5060ti]] | 2.48, 48.58 | 09-chmura-5060ti.md:71 | OK |
| [[raport-09-chmura-5060ti]] | 2.55, 37, 68.36 | 09-chmura-5060ti.md:68 | OK |
| [[raport-09-chmura-5060ti]] | 2026 | 09-chmura-5060ti.md:3 | OK |
| [[raport-09-chmura-5060ti]] | 2048, 56 | 09-chmura-5060ti.md:156 | OK |
| [[raport-09-chmura-5060ti]] | 208 | 09-chmura-5060ti.md:109 | OK |
| [[raport-09-chmura-5060ti]] | 28, 448 | 09-chmura-5060ti.md:15 | OK |
| [[raport-09-chmura-5060ti]] | 31 | 09-chmura-5060ti.md:31 | OK |
| [[raport-09-chmura-5060ti]] | 31.8, 7.7 | 09-chmura-5060ti.md:89 | OK |
| [[raport-09-chmura-5060ti]] | 435 | 09-chmura-5060ti.md:147 | OK |
| [[raport-09-chmura-5060ti]] | 5.24 | 09-chmura-5060ti.md:191 | OK |
| [[raport-09-chmura-5060ti]] | 5.8, 51.7 | 09-chmura-5060ti.md:119 | OK |
| [[raport-09-chmura-5060ti]] | 52.81 | 09-chmura-5060ti.md:160 | OK |
| [[raport-09-chmura-5060ti]] | 7.68, 7502 | 09-chmura-5060ti.md:16 | OK |
| [[raport-09-chmura-5060ti]] | 71 | 09-chmura-5060ti.md:184 | OK |
| [[raport-09-chmura-5060ti]] | 81 | 09-chmura-5060ti.md:81 | OK |
| [[raport-09-chmura-5060ti]] | 85 | 09-chmura-5060ti.md:150 | OK |
| [[raport-09-chmura-5060ti]] | 908 | 09-chmura-5060ti.md:146 | OK |
| [[raport-09-chmura-5060ti]] | 99 | 09-chmura-5060ti.md:28 | OK |
| [[raport-09-chmura-3060]] | 0.000206, 0.000323 | 09-chmura-3060.md:125 | OK |
| [[raport-09-chmura-3060]] | 0.000612, 0.000650, 65 | 09-chmura-3060.md:124 | OK |
| [[raport-09-chmura-3060]] | 0.82 | 09-chmura-3060.md:229 | OK |
| [[raport-09-chmura-3060]] | 0001 | 09-chmura-3060.md:5 | OK |
| [[raport-09-chmura-3060]] | 0013 | 09-chmura-3060.md:12 | OK |
| [[raport-09-chmura-3060]] | 08 | 09-chmura-3060.md:118 | OK |
| [[raport-09-chmura-3060]] | 09, 12, 27, 3060 | 09-chmura-3060.md:1 | OK |
| [[raport-09-chmura-3060]] | 1.5 | 09-chmura-3060.md:27 | OK |
| [[raport-09-chmura-3060]] | 1024 | 09-chmura-3060.md:32 | OK |
| [[raport-09-chmura-3060]] | 12.6 | 09-chmura-3060.md:159 | OK |
| [[raport-09-chmura-3060]] | 16, 2026 | 09-chmura-3060.md:3 | OK |
| [[raport-09-chmura-3060]] | 170 | 09-chmura-3060.md:14 | OK |
| [[raport-09-chmura-3060]] | 2.39 | 09-chmura-3060.md:136 | OK |
| [[raport-09-chmura-3060]] | 21 | 09-chmura-3060.md:36 | OK |
| [[raport-09-chmura-3060]] | 22.3, 44.75, 6.8 | 09-chmura-3060.md:102 | OK |
| [[raport-09-chmura-3060]] | 22.5, 9.7 | 09-chmura-3060.md:19 | OK |
| [[raport-09-chmura-3060]] | 23.4 | 09-chmura-3060.md:62 | OK |
| [[raport-09-chmura-3060]] | 3.7, 5.7 | 09-chmura-3060.md:154 | OK |
| [[raport-09-chmura-3060]] | 33.15 | 09-chmura-3060.md:106 | OK |
| [[raport-09-chmura-3060]] | 35.5 | 09-chmura-3060.md:214 | OK |
| [[raport-09-chmura-3060]] | 35.51 | 09-chmura-3060.md:107 | OK |
| [[raport-09-chmura-3060]] | 4.8, 7.1 | 09-chmura-3060.md:182 | OK |
| [[raport-09-chmura-3060]] | 512 | 09-chmura-3060.md:43 | OK |
| [[raport-09-chmura-3060]] | 64 | 09-chmura-3060.md:26 | OK |
| [[raport-09-chmura-3060]] | 7.6665 | 09-chmura-3060.md:47 | OK |
| [[raport-09-chmura-3060]] | 7b344114d | 09-chmura-3060.md:113 | OK |
| [[raport-09-chmura-3060]] | 8.6154, 8.6171 | 09-chmura-3060.md:38 | OK |
| [[raport-11-mtp-pl-pilot]] | 0.02 | 11-mtp-pl-pilot.md:88 | OK |
| [[raport-11-mtp-pl-pilot]] | 0.1, 0.65, 0.9 | 11-mtp-pl-pilot.md:20 | OK |
| [[raport-11-mtp-pl-pilot]] | 0.2, 1.7 | 11-mtp-pl-pilot.md:6 | OK |
| [[raport-11-mtp-pl-pilot]] | 0.21 | 11-mtp-pl-pilot.md:87 | OK |
| [[raport-11-mtp-pl-pilot]] | 0.39 | 11-mtp-pl-pilot.md:60 | OK |
| [[raport-11-mtp-pl-pilot]] | 0.45, 3.281 | 11-mtp-pl-pilot.md:80 | OK |
| [[raport-11-mtp-pl-pilot]] | 1.71, 3.235 | 11-mtp-pl-pilot.md:86 | OK |
| [[raport-11-mtp-pl-pilot]] | 10, 11, 2026, 27 | 11-mtp-pl-pilot.md:1 | OK |
| [[raport-11-mtp-pl-pilot]] | 2.14 | 11-mtp-pl-pilot.md:8 | OK |
| [[raport-11-mtp-pl-pilot]] | 2.3 | 11-mtp-pl-pilot.md:5 | OK |
| [[raport-11-mtp-pl-pilot]] | 2.65 | 11-mtp-pl-pilot.md:78 | OK |
| [[raport-11-mtp-pl-pilot]] | 2.71 | 11-mtp-pl-pilot.md:111 | OK |
| [[raport-11-mtp-pl-pilot]] | 21 | 11-mtp-pl-pilot.md:47 | OK |
| [[raport-11-mtp-pl-pilot]] | 3.009, 3.812 | 11-mtp-pl-pilot.md:70 | OK |
| [[raport-11-mtp-pl-pilot]] | 3.266 | 11-mtp-pl-pilot.md:38 | OK |
| [[raport-11-mtp-pl-pilot]] | 3.960 | 11-mtp-pl-pilot.md:68 | OK |
| [[raport-11-mtp-pl-pilot]] | 351 008 768 | 11-mtp-pl-pilot.md:28 | OK |
| [[raport-11-mtp-pl-pilot]] | 7.65 | 11-mtp-pl-pilot.md:171 | OK |
| [[raport-11-mtp-pl-pilot]] | 7f63dec8 | ręcznie | OK: skrót hasha 7f63dec872e319cb… (11-mtp-pl-pilot.md:129) |
| [[raport-11-mtp-pl-pilot]] | 96 | 11-mtp-pl-pilot.md:174 | OK |
| [[raport-12-bit-exact]] | 0.3, 1.3 | 12-bit-exact-spekulacja.md:91 | OK |
| [[raport-12-bit-exact]] | 0.5, 32 | 12-bit-exact-spekulacja.md:87 | OK |
| [[raport-12-bit-exact]] | 1.19, 368 | 12-bit-exact-spekulacja.md:156 | OK |
| [[raport-12-bit-exact]] | 12 | 12-bit-exact-spekulacja.md:1 | OK |
| [[raport-12-bit-exact]] | 2026 | 12-bit-exact-spekulacja.md:3 | OK |
| [[raport-12-bit-exact]] | 36 | 12-bit-exact-spekulacja.md:106 | OK |
| [[raport-12-bit-exact]] | 4c6d328b, 8cca9b70, c09ac6aab | 12-bit-exact-spekulacja.md:146 | OK |
| [[raport-12-bit-exact]] | 6e261fdb4 | 12-bit-exact-spekulacja.md:182 | OK |
| [[raport-12-bit-exact]] | 6f14e814, c4708318 | 12-bit-exact-spekulacja.md:8 | OK |
| [[raport-12-bit-exact]] | 77240, 77240c9b3 | 12-bit-exact-spekulacja.md:163 | OK |
| [[raport-12-bit-exact]] | 862 | 12-bit-exact-spekulacja.md:98 | OK |
| [[nvidia-wyniki-2026-10-16]] | 0.40 | 09-chmura-3090.md:165 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia-wyniki-2026-10-16]] | 0.82 | 09-chmura-3060.md:229 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia-wyniki-2026-10-16]] | 0.90 | 09-chmura-3090.md:183 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia-wyniki-2026-10-16]] | 0001 | 09-chmura-3090.md:40 | OK |
| [[nvidia-wyniki-2026-10-16]] | 0013 | 09-chmura-3090.md:199 | OK |
| [[nvidia-wyniki-2026-10-16]] | 1.05 | 09-chmura-5060ti.md:86 | OK |
| [[nvidia-wyniki-2026-10-16]] | 1.23, 2.00 | 09-chmura-3090.md:218 | OK |
| [[nvidia-wyniki-2026-10-16]] | 1.38, 1.84 | 09-chmura-5060ti.md:234 | OK |
| [[nvidia-wyniki-2026-10-16]] | 1.4 | 09-chmura-3090.md:108 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia-wyniki-2026-10-16]] | 1.41, 1.44 | 09-chmura-5060ti.md:252 | OK |
| [[nvidia-wyniki-2026-10-16]] | 1.46, 1.50 | 09-chmura-3090.md:233 | OK |
| [[nvidia-wyniki-2026-10-16]] | 144.47, 147.69, 207.86 | 09-chmura-5060ti.md:240 | OK |
| [[nvidia-wyniki-2026-10-16]] | 176.0 | 09-chmura-3090.md:58 | OK |
| [[nvidia-wyniki-2026-10-16]] | 180.2 | 09-chmura-3090.md:57 | OK |
| [[nvidia-wyniki-2026-10-16]] | 180.5 | 09-chmura-3090.md:224 | OK |
| [[nvidia-wyniki-2026-10-16]] | 19251 | 09-chmura-5060ti.md:35 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia-wyniki-2026-10-16]] | 1956 | 09-chmura-3090.md:137 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia-wyniki-2026-10-16]] | 2.0 | 09-chmura-3090.md:196 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia-wyniki-2026-10-16]] | 2026 | 09-chmura-3090.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[nvidia-wyniki-2026-10-16]] | 22.1 | 09-chmura-3090.md:46 | OK |
| [[nvidia-wyniki-2026-10-16]] | 22.3 | 09-chmura-3060.md:102 | OK |
| [[nvidia-wyniki-2026-10-16]] | 23.4 | 09-chmura-3060.md:62 | OK |
| [[nvidia-wyniki-2026-10-16]] | 263.9 | 09-chmura-3090.md:61 | OK |
| [[nvidia-wyniki-2026-10-16]] | 27 | 09-chmura-3090.md:42 | OK |
| [[nvidia-wyniki-2026-10-16]] | 28.07, 37.32, 51.66 | 09-chmura-5060ti.md:222 | OK |
| [[nvidia-wyniki-2026-10-16]] | 3060 | 09-chmura-3060.md:113 | OK |
| [[nvidia-wyniki-2026-10-16]] | 3090 | 09-chmura-5060ti.md:89 | OK |
| [[nvidia-wyniki-2026-10-16]] | 3090 192 | ręcznie | OK: artefakt parsera („3090” i „19253” osobno w źródle) |
| [[nvidia-wyniki-2026-10-16]] | 31, 78.0 | 09-chmura-3090.md:49 | OK |
| [[nvidia-wyniki-2026-10-16]] | 33.1, 35.5 | 09-chmura-3060.md:258 | OK |
| [[nvidia-wyniki-2026-10-16]] | 39.0, 63.3 | 09-chmura-3090.md:47 | OK |
| [[nvidia-wyniki-2026-10-16]] | 5060 | 09-chmura-5060ti.md:216 | OK |
| [[nvidia-wyniki-2026-10-16]] | 795 | 09-chmura-3090.md:138 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3090]] | 0.23 | 05-chmura-gpu-do-testow.md:15 | OK |
| [[rtx-3090]] | 0.32, 7900 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[rtx-3090]] | 0.90 | 09-chmura-3090.md:183 | OK |
| [[rtx-3090]] | 02, 24 | 09-chmura-3090.md:13 | OK |
| [[rtx-3090]] | 1,224 | 05-chmura-gpu-do-testow.md:233 | OK |
| [[rtx-3090]] | 1.23, 39 | 09-chmura-3090.md:196 | OK |
| [[rtx-3090]] | 1350, 300, 350 | 09-chmura-3090.md:16 | OK |
| [[rtx-3090]] | 140.8, 147.7 | 09-chmura-3090.md:153 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3090]] | 162 | 05-chmura-gpu-do-testow.md:99 | OK |
| [[rtx-3090]] | 180, 264 | 09-chmura-3090.md:197 | OK |
| [[rtx-3090]] | 180.2 | 09-chmura-3090.md:57 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3090]] | 19253 | 09-chmura-3090.md:38 | OK |
| [[rtx-3090]] | 2026, 3090 | 09-chmura-3090.md:1 | OK |
| [[rtx-3090]] | 256.8, 284.5 | 09-chmura-3090.md:123 | OK |
| [[rtx-3090]] | 26.7 | 02-autotuning-i-agenci-kerneli.md:256 | OK |
| [[rtx-3090]] | 263.9, 78 | 09-chmura-3090.md:125 | OK |
| [[rtx-3090]] | 27.2 | 09-chmura-3090.md:152 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3090]] | 38.4, 78.0 | 09-chmura-3090.md:49 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3090]] | 38.9 | 09-chmura-3090.md:46 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3090]] | 3da7a02ec | 09-chmura-3090.md:110 | OK |
| [[rtx-3090]] | 40.1, 43.0 | 09-chmura-3090.md:122 | OK |
| [[rtx-3090]] | 41.55, 59.8, 66.39 | 02-autotuning-i-agenci-kerneli.md:257 | OK |
| [[rtx-3090]] | 615.71 | 09-chmura-3090.md:14 | OK |
| [[rtx-3090]] | 63.3 | 09-chmura-3090.md:47 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3090]] | 64 | 09-chmura-3090.md:133 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3090]] | 7.68 | 09-chmura-3090.md:18 | OK |
| [[rtx-3090]] | 787 | times.jsonl:2 | OK |
| [[rtx-5060-ti]] | 0.165 | 05-chmura-gpu-do-testow.md:104 | OK |
| [[rtx-5060-ti]] | 0053, 0057, 43 | 09-chmura-5060ti.md:69 | OK |
| [[rtx-5060-ti]] | 1.05, 65 | 09-chmura-5060ti.md:86 | OK |
| [[rtx-5060-ti]] | 120, 448 | rx-7900-xtx.md:38 | OK |
| [[rtx-5060-ti]] | 128 | rx-7900-xtx.md:33 | OK |
| [[rtx-5060-ti]] | 147.69, 207.86 | 09-chmura-5060ti.md:240 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-5060-ti]] | 148 | 09-chmura-5060ti.md:201 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-5060-ti]] | 16, 5060 | rx-7900-xtx.md:36 | OK |
| [[rtx-5060-ti]] | 180 | 09-chmura-5060ti.md:14 | OK |
| [[rtx-5060-ti]] | 19251 | 09-chmura-5060ti.md:35 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-5060-ti]] | 2.7 | 09-chmura-5060ti.md:124 | OK |
| [[rtx-5060-ti]] | 2026 | rx-7900-xtx.md:34 | OK |
| [[rtx-5060-ti]] | 208 | 09-chmura-5060ti.md:109 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-5060-ti]] | 226.8 | 09-chmura-5060ti.md:177 | OK |
| [[rtx-5060-ti]] | 28 | 09-chmura-5060ti.md:15 | OK |
| [[rtx-5060-ti]] | 28.07, 51.66 | 09-chmura-5060ti.md:222 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-5060-ti]] | 4.06 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[rtx-5060-ti]] | 474, 680 | PLAN.md:287 | OK |
| [[rtx-5060-ti]] | 5.2 | PLAN.md:30 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-5060-ti]] | 503 | 09-chmura-5060ti.md:23 | OK |
| [[rtx-5060-ti]] | 51.7 | 09-chmura-5060ti.md:119 | OK |
| [[rtx-5060-ti]] | 580.173 | 09-chmura-5060ti.md:12 | OK |
| [[rtx-5060-ti]] | 7.68 | 09-chmura-5060ti.md:16 | OK |
| [[rtx-5060-ti]] | 7.7 | 09-chmura-5060ti.md:89 | OK |
| [[rtx-5060-ti]] | 81 | 09-chmura-5060ti.md:81 | OK |
| [[rtx-3060]] | 0.82 | 09-chmura-3060.md:229 | OK |
| [[rtx-3060]] | 1024 | 09-chmura-3060.md:77 | OK |
| [[rtx-3060]] | 1139, 1151, 1157 | 09-chmura-3060.md:17 | OK |
| [[rtx-3060]] | 12, 27, 3060 | 09-chmura-3060.md:1 | OK |
| [[rtx-3060]] | 170 | 09-chmura-3060.md:14 | OK |
| [[rtx-3060]] | 2026 | 09-chmura-3060.md:3 | OK |
| [[rtx-3060]] | 22.1 | 09-chmura-3060.md:217 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3060]] | 22.5, 9.7 | 09-chmura-3060.md:19 | OK |
| [[rtx-3060]] | 23.4 | 09-chmura-3060.md:62 | OK |
| [[rtx-3060]] | 257 | PLAN.md:288 | OK |
| [[rtx-3060]] | 3.66 | 05-chmura-gpu-do-testow.md:305 | OK |
| [[rtx-3060]] | 3.7, 5.7 | 09-chmura-3060.md:154 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3060]] | 32 | 09-chmura-3060.md:73 | OK |
| [[rtx-3060]] | 35.5 | 09-chmura-3060.md:214 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3060]] | 4.8, 7.1 | 09-chmura-3060.md:182 | OK (inny wiersz źródła, sprawdzone) |
| [[rtx-3060]] | 44.75, 6.8 | 09-chmura-3060.md:102 | OK |
| [[rtx-3060]] | 595.71 | 09-chmura-3060.md:12 | OK |
| [[rtx-3060]] | 7.6665 | 09-chmura-3060.md:47 | OK (inny wiersz źródła, sprawdzone) |
| [[2026-10-16-kampania-nvidia]] | 0.82 | 09-chmura-3060.md:229 | OK |
| [[2026-10-16-kampania-nvidia]] | 0.90 | 09-chmura-3090.md:183 | OK |
| [[2026-10-16-kampania-nvidia]] | 0001, 2026 | PLAN-TESTOW.md:3 | OK |
| [[2026-10-16-kampania-nvidia]] | 0013, 31 | PLAN-TESTOW.md:58 | OK |
| [[2026-10-16-kampania-nvidia]] | 1.05 | 09-chmura-5060ti.md:191 | OK |
| [[2026-10-16-kampania-nvidia]] | 1.4 | 09-chmura-3090.md:108 | OK (inny wiersz źródła, sprawdzone) |
| [[2026-10-16-kampania-nvidia]] | 2.0 | PLAN-TESTOW.md:99 | OK (inny wiersz źródła, sprawdzone) |
| [[2026-10-16-kampania-nvidia]] | 2.77 | ręcznie | OK: suma 0.90 + 1.05 + 0.82 z raportów 09 (i wiadomość Main) |
| [[2026-10-16-kampania-nvidia]] | 3060 | 09-chmura-3060.md:1 | OK |
| [[2026-10-16-kampania-nvidia]] | 3090 | 09-chmura-3090.md:1 | OK |
| [[2026-10-16-kampania-nvidia]] | 5060 | PLAN-TESTOW.md:159 | OK |
| [[2026-10-16-bit-exact]] | 1.19, 368 | 12-bit-exact-spekulacja.md:156 | OK |
| [[2026-10-16-bit-exact]] | 2026 | 12-bit-exact-spekulacja.md:3 | OK |
| [[2026-10-16-bit-exact]] | 23335 | 12-bit-exact-spekulacja.md:24 | OK (inny wiersz źródła, sprawdzone) |
| [[2026-10-16-bit-exact]] | 4c6d328b, 8cca9b70, c09ac6aab | 12-bit-exact-spekulacja.md:146 | OK |
| [[2026-10-16-bit-exact]] | 6e261fdb4 | 12-bit-exact-spekulacja.md:182 | OK |
| [[2026-10-16-bit-exact]] | 6f14e814, c4708318 | 12-bit-exact-spekulacja.md:8 | OK |
| [[2026-10-16-bit-exact]] | 77240, 77240c9b3 | 12-bit-exact-spekulacja.md:163 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 0.02 | 11-mtp-pl-pilot.md:88 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 0.1, 0.9 | 11-mtp-pl-pilot.md:86 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 0.2, 1.7 | 11-mtp-pl-pilot.md:6 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 0.21, 0.39 | 11-mtp-pl-pilot.md:87 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 0.45 | 11-mtp-pl-pilot.md:80 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 1.32 | ręcznie | OK: 1 317 337 tokenów (11-mtp-pl-pilot.md:58), zaokrąglone |
| [[2026-10-16-mtp-pl-pilot]] | 10, 2026, 27 | 11-mtp-pl-pilot.md:1 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 100, 140 | 11-mtp-pl-pilot.md:60 | OK (inny wiersz źródła, sprawdzone) |
| [[2026-10-16-mtp-pl-pilot]] | 2.14, 3.50 | 11-mtp-pl-pilot.md:8 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 2.3 | 11-mtp-pl-pilot.md:5 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 21, 3.266 | 11-mtp-pl-pilot.md:68 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 3.268 | 11-mtp-pl-pilot.md:121 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 32 | 11-mtp-pl-pilot.md:72 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 78.3, 78.5 | 11-mtp-pl-pilot.md:111 | OK |
| [[2026-10-16-mtp-pl-pilot]] | 78.7, 78.9 | 11-mtp-pl-pilot.md:110 | OK |
| [[saluki]] | 0.000612, 0.000650 | 09-chmura-3060.md:124 | OK |
| [[saluki]] | 0.09 | 09-chmura-3060.md:190 | OK (inny wiersz źródła, sprawdzone) |
| [[saluki]] | 0.150, 7.6665 | 09-chmura-3060.md:47 | OK |
| [[saluki]] | 1.0 | 10-post-training.md:139 | OK |
| [[saluki]] | 10 | 10-post-training.md:386 | OK |
| [[saluki]] | 11, 34 | 09-chmura-3060.md:27 | OK |
| [[saluki]] | 12 | 09-chmura-3060.md:84 | OK |
| [[saluki]] | 2.4, 4.8 | 09-chmura-3060.md:209 | OK |
| [[saluki]] | 2025, 79.2, 84, 88, 96.7 | 10-post-training.md:337 | OK |
| [[saluki]] | 2026 | saluki-README.md:104 | OK |
| [[saluki]] | 22.1 | 09-chmura-3060.md:217 | OK |
| [[saluki]] | 23, 23.4 | 09-chmura-3060.md:62 | OK |
| [[saluki]] | 27 | 10-post-training.md:42 | OK |
| [[saluki]] | 3060 | 09-chmura-3060.md:23 | OK |
| [[saluki]] | 512 | 09-chmura-3060.md:43 | OK |
| [[saluki]] | 64 | 09-chmura-3060.md:26 | OK |
| [[saluki]] | 7.90 | 09-chmura-3060.md:25 | OK |
| [[saluki]] | 9.7 | 09-chmura-3060.md:19 | OK |
| [[bonsai]] | 0.000206, 0.000323 | 09-chmura-3060.md:125 | OK |
| [[bonsai]] | 1.2 | 10-post-training.md:141 | OK |
| [[bonsai]] | 10 | 10-post-training.md:386 | OK |
| [[bonsai]] | 1024, 128, 20, 98.2 | 10-post-training.md:329 | OK |
| [[bonsai]] | 124, 18, 3060, 7.63 | 09-chmura-3060.md:36 | OK |
| [[bonsai]] | 142, 143, e3de715 | 09-chmura-3060.md:31 | OK |
| [[bonsai]] | 2026 | 09-chmura-3060.md:196 | OK |
| [[bonsai]] | 21, 7.21 | bonsai-README.md:44 | OK |
| [[bonsai]] | 256 | 09-chmura-3060.md:39 | OK |
| [[bonsai]] | 27 | 10-post-training.md:137 | OK |
| [[bonsai]] | 28 | 10-post-training.md:334 | OK |
| [[bonsai]] | 33.15 | 09-chmura-3060.md:106 | OK |
| [[bonsai]] | 34 | 09-chmura-3060.md:27 | OK |
| [[bonsai]] | 35.51 | 09-chmura-3060.md:107 | OK |
| [[bonsai]] | 36.45 | 09-chmura-3060.md:101 | OK |
| [[bonsai]] | 44.75, 6.8 | 09-chmura-3060.md:102 | OK |
| [[bonsai]] | 64 | bonsai-README.md:60 | OK |
| [[bonsai]] | 65 | 09-chmura-3060.md:124 | OK |
| [[bonsai]] | 7.1 | 09-chmura-3060.md:182 | OK |
| [[bonsai]] | 8.6154, 8.6171 | 09-chmura-3060.md:38 | OK |
| [[nvfp4]] | 0.0265 | 09-chmura-5060ti.md:174 | OK |
| [[nvfp4]] | 0.0865, 14.86, 1730, 1747 | 09-chmura-5060ti.md:175 | OK |
| [[nvfp4]] | 0004 | rx-7900-xtx.md:38 | OK |
| [[nvfp4]] | 0012 | 09-chmura-5060ti.md:189 | OK |
| [[nvfp4]] | 01 | 01-konkurencja.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[nvfp4]] | 09 | 01-konkurencja.md:90 | OK (inny wiersz źródła, sprawdzone) |
| [[nvfp4]] | 1.14 | 22-lucebox.md:90 | OK (inny wiersz źródła, sprawdzone) |
| [[nvfp4]] | 1.1826, 1.857, 7270, 7663 | 09-chmura-5060ti.md:178 | OK |
| [[nvfp4]] | 16, 5060 | rx-7900-xtx.md:36 | OK |
| [[nvfp4]] | 2.5 | 09-chmura-5060ti.md:256 | OK |
| [[nvfp4]] | 2026 | 01-konkurencja.md:330 | OK |
| [[nvfp4]] | 21.9 | 09-chmura-5060ti.md:265 | OK |
| [[nvfp4]] | 65 | roadmap.md:244 | OK |
| [[nvfp4]] | 69, 71, 81 | 09-chmura-5060ti.md:184 | OK |
| [[nvfp4]] | 7900 | rx-7900-xtx.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[lfm2-5-24b-a2b]] | 0.044 | ręcznie | OK: NOTES.md:363: 0.044171 (zaokrąglone) |
| [[lfm2-5-24b-a2b]] | 0.128 | NOTES.md:363 | OK |
| [[lfm2-5-24b-a2b]] | 0.2008 | 09-chmura-5060ti.md:176 | OK |
| [[lfm2-5-24b-a2b]] | 0.2029, 0.869, 13.58, 164.5, 226.8 | 09-chmura-5060ti.md:177 | OK |
| [[lfm2-5-24b-a2b]] | 09 | NOTES.md:109 | OK (inny wiersz źródła, sprawdzone) |
| [[lfm2-5-24b-a2b]] | 1.48 | ręcznie | OK: ls ~/models: LFM2.5-2.6B-QAD-Q4_0.gguf 1.48 GiB |
| [[lfm2-5-24b-a2b]] | 1.8, 1.9, 500 | NOTES.md:338 | OK |
| [[lfm2-5-24b-a2b]] | 10, 2026, 24 | NOTES.md:333 | OK |
| [[lfm2-5-24b-a2b]] | 120.9, 15.86 | 09-chmura-5060ti.md:166 | OK |
| [[lfm2-5-24b-a2b]] | 128, 198 | NOTES.md:336 | OK |
| [[lfm2-5-24b-a2b]] | 131072 | NOTES.md:334 | OK |
| [[lfm2-5-24b-a2b]] | 147.69, 207.86 | 09-chmura-5060ti.md:240 | OK (inny wiersz źródła, sprawdzone) |
| [[lfm2-5-24b-a2b]] | 15.1, 1536, 16, 2048, 205, 30, 32, 40, 64 | NOTES.md:337 | OK |
| [[lfm2-5-24b-a2b]] | 169.3 | NOTES.md:339 | OK |
| [[lfm2-5-24b-a2b]] | 173 | NOTES.md:335 | OK |
| [[lfm2-5-24b-a2b]] | 180.2 | 09-chmura-3090.md:57 | OK |
| [[lfm2-5-24b-a2b]] | 263.9 | 09-chmura-3090.md:61 | OK |
| [[lfm2-5-24b-a2b]] | 289.7, 293.7, 3.41, 6175 | STATUS-NEXT.md:12 | OK |
| [[lfm2-5-24b-a2b]] | 294 | NOTES.md:375 | OK (inny wiersz źródła, sprawdzone) |
| [[lfm2-5-24b-a2b]] | 3090 | 09-chmura-5060ti.md:89 | OK |
| [[lfm2-5-24b-a2b]] | 38 | NOTES.md:340 | OK |
| [[lfm2-5-24b-a2b]] | 5060 | 09-chmura-5060ti.md:195 | OK |
| [[lfm2-5-24b-a2b]] | 56 | STATUS-NEXT.md:15 | OK |
| [[lfm2-5-24b-a2b]] | 7900 | NOTES.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[glowica-mtp]] | 0.2 | 11-mtp-pl-pilot.md:6 | OK |
| [[glowica-mtp]] | 0.39 | NOTES.md:135 | OK |
| [[glowica-mtp]] | 0.45 | 11-mtp-pl-pilot.md:80 | OK |
| [[glowica-mtp]] | 0.72 | RESULTS.md:75 | OK |
| [[glowica-mtp]] | 0.78, 0.87, 0.89 | RESULTS.md:80 | OK |
| [[glowica-mtp]] | 1.7 | RESULTS.md:98 | OK |
| [[glowica-mtp]] | 10, 2026 | RESULTS.md:5 | OK |
| [[glowica-mtp]] | 109 | NOTES.md:280 | OK (inny wiersz źródła, sprawdzone) |
| [[glowica-mtp]] | 11, 3.11, 3.93 | RESULTS.md:54 | OK |
| [[glowica-mtp]] | 2.3, 2.68 | RESULTS.md:60 | OK |
| [[glowica-mtp]] | 2.48 | RESULTS.md:65 | OK |
| [[glowica-mtp]] | 2.97, 3.04 | RESULTS.md:55 | OK |
| [[glowica-mtp]] | 21, 3.96 | RESULTS.md:57 | OK |
| [[glowica-mtp]] | 3.266, 3.960 | 11-mtp-pl-pilot.md:68 | OK |
| [[glowica-mtp]] | 3.76 | RESULTS.md:63 | OK |
| [[glowica-mtp]] | 3.89 | RESULTS.md:59 | OK |
| [[glowica-mtp]] | 351 008 768 | 11-mtp-pl-pilot.md:28 | OK |
| [[glowica-mtp]] | 4 102.7 | NOTES.md:316 | OK |
| [[glowica-mtp]] | 5 103.0 | NOTES.md:317 | OK |
| [[glowica-mtp]] | 64 | RESULTS.md:3 | OK |
| [[glowica-mtp]] | 69 207 | RESULTS.md:15 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcja-fit-mtp-16gb]] | 14, 14.0, 14.5, 24, 3090, 31.8, 45.5, 6.3, 7.7, 760 | 09-chmura-5060ti.md:89 | OK |
| [[lekcja-fit-mtp-16gb]] | 16 | 09-chmura-5060ti.md:27 | OK |
| [[lekcja-fit-mtp-16gb]] | 2026 | 09-chmura-5060ti.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcja-fit-mtp-16gb]] | 32 | 09-chmura-5060ti.md:19 | OK |
| [[lekcja-fit-mtp-16gb]] | 5060 | 09-chmura-5060ti.md:193 | OK |
| [[lekcja-fit-mtp-16gb]] | 99 | 09-chmura-5060ti.md:28 | OK |
| [[lekcja-limit-cpu-kontenera]] | 30, 7.65 | 11-mtp-pl-pilot.md:171 | OK |
| [[lekcja-limit-cpu-kontenera]] | 3090 | 09-chmura-5060ti.md:15 | OK |
| [[lekcja-limit-cpu-kontenera]] | 32 | 09-chmura-5060ti.md:19 | OK |
| [[lekcja-limit-cpu-kontenera]] | 5060 | 09-chmura-5060ti.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcja-limit-cpu-kontenera]] | 64, 7.68 | 09-chmura-5060ti.md:16 | OK |
| [[lekcja-limit-cpu-kontenera]] | 7.7 | 09-chmura-5060ti.md:89 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcja-limit-cpu-kontenera]] | 96 | 11-mtp-pl-pilot.md:174 | OK |
| [[lekcja-md5-wzgledem-upstreamu]] | 0.000612, 0.000650 | 09-chmura-3060.md:124 | OK |
| [[lekcja-md5-wzgledem-upstreamu]] | 0001 | 09-chmura-3090.md:80 | OK |
| [[lekcja-md5-wzgledem-upstreamu]] | 0013 | 09-chmura-3090.md:81 | OK |
| [[lekcja-md5-wzgledem-upstreamu]] | 0043, 3090 | 09-chmura-5060ti.md:55 | OK |
| [[lekcja-md5-wzgledem-upstreamu]] | 3060 | 09-chmura-3060.md:113 | OK |
| [[lekcja-md5-wzgledem-upstreamu]] | 31 | 09-chmura-3090.md:74 | OK |
| [[lekcja-md5-wzgledem-upstreamu]] | 949, 949a753b | 09-chmura-3090.md:70 | OK |
| [[lekcja-mtp-glowica-optimum]] | 0.2, 1.7 | 11-mtp-pl-pilot.md:6 | OK |
| [[lekcja-mtp-glowica-optimum]] | 0.307, 0.317 | 11-mtp-pl-pilot.md:91 | OK |
| [[lekcja-mtp-glowica-optimum]] | 10 | 11-mtp-pl-pilot.md:1 | OK |
| [[lekcja-mtp-glowica-optimum]] | 17 | 10-post-training.md:32 | OK |
| [[lekcja-mtp-glowica-optimum]] | 21 | 11-mtp-pl-pilot.md:87 | OK |
| [[lekcja-mtp-glowica-optimum]] | 3.235 | 11-mtp-pl-pilot.md:86 | OK |
| [[lekcja-mtp-glowica-optimum]] | 3.281 | 11-mtp-pl-pilot.md:80 | OK |
| [[lekcja-mtp-glowica-optimum]] | 33 | 11-mtp-pl-pilot.md:181 | OK |
| [[lekcja-nadpisanie-dzialajacego-skryptu]] | 5060 | 09-chmura-5060ti.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcja-bit-exact-attention]] | 0.33 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5568 | OK |
| [[lekcja-bit-exact-attention]] | 1.19, 368, 6144 | 12-bit-exact-spekulacja.md:156 | OK |
| [[lekcja-bit-exact-attention]] | 16, 2026 | 12-bit-exact-spekulacja.md:154 | OK |
| [[lekcja-bit-exact-attention]] | 6e261fdb4 | 12-bit-exact-spekulacja.md:182 | OK |
| [[lekcja-bit-exact-attention]] | 77240, 77240c9b3 | 12-bit-exact-spekulacja.md:163 | OK |
| [[lekcja-bit-exact-attention]] | 7900 | 12-bit-exact-spekulacja.md:8 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcja-obciazenie-cpu]] | 15 | 07-nasze-metody-uogolnienie.md:276 | OK |
| [[lekcja-obciazenie-cpu]] | 2026 | NOTES.md:172 | OK |
| [[lekcja-obciazenie-cpu]] | 22.5, 9.7 | 09-chmura-3060.md:19 | OK |
| [[lekcja-obciazenie-cpu]] | 3.4 | 07-nasze-metody-uogolnienie.md:383 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcja-obciazenie-cpu]] | 3060 | 09-chmura-3060.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[lekcja-obciazenie-cpu]] | 3090 | ręcznie | OK: nazwa karty |
| [[zgodnosc-bitowa-md5]] | 0001 | 07-nasze-metody-uogolnienie.md:229 | OK |
| [[zgodnosc-bitowa-md5]] | 0013 | NOTES.md:378 | OK |
| [[zgodnosc-bitowa-md5]] | 07 | qwen-round5.md:23 | OK |
| [[zgodnosc-bitowa-md5]] | 0b7b073b, 58, 58e578967 | qwen-round5.md:11 | OK |
| [[zgodnosc-bitowa-md5]] | 129, 229 | 07-nasze-metody-uogolnienie.md:265 | OK |
| [[zgodnosc-bitowa-md5]] | 2.2 | 07-nasze-metody-uogolnienie.md:27 | OK (inny wiersz źródła, sprawdzone) |
| [[zgodnosc-bitowa-md5]] | 2026, 45 | qwen-round5.md:7 | OK |
| [[zgodnosc-bitowa-md5]] | 2048, 3000, 64 | 07-nasze-metody-uogolnienie.md:228 | OK |
| [[zgodnosc-bitowa-md5]] | 270 | 07-nasze-metody-uogolnienie.md:264 | OK |
| [[zgodnosc-bitowa-md5]] | 3060 | 09-chmura-3060.md:113 | OK |
| [[zgodnosc-bitowa-md5]] | 6f14e814, c4708318 | NOTES.md:357 | OK |
| [[zgodnosc-bitowa-md5]] | 83, 94 | 07-nasze-metody-uogolnienie.md:262 | OK |
| [[zgodnosc-bitowa-md5]] | 894, 894e56e4 | STATUS-NEXT.md:15 | OK |
| [[zgodnosc-bitowa-md5]] | e60eff95f | NOTES.md:377 | OK |
| [[mmvq-n1-wiersze]] | 0.135, 0059 | 07-nasze-metody-uogolnienie.md:184 | OK |
| [[mmvq-n1-wiersze]] | 0052, 4.509, 4.610 | NOTES.md:349 | OK |
| [[mmvq-n1-wiersze]] | 0064, 2026 | NOTES.md:372 | OK |
| [[mmvq-n1-wiersze]] | 007000, 007000aaa, 71412, 71412d9c6 | git:1 | OK |
| [[mmvq-n1-wiersze]] | 07 | NOTES.md:338 | OK (inny wiersz źródła, sprawdzone) |
| [[mmvq-n1-wiersze]] | 1.7 | 09-chmura-3090.md:104 | OK |
| [[mmvq-n1-wiersze]] | 12.6, 21 | 09-chmura-3060.md:159 | OK |
| [[mmvq-n1-wiersze]] | 15 | 09-chmura-5060ti.md:207 | OK |
| [[mmvq-n1-wiersze]] | 2.2 | 07-nasze-metody-uogolnienie.md:127 | OK |
| [[mmvq-n1-wiersze]] | 2.7, 87 | 09-chmura-3090.md:113 | OK |
| [[mmvq-n1-wiersze]] | 3.706, 3.933 | NOTES.md:374 | OK |
| [[mmvq-n1-wiersze]] | 3060 | 09-chmura-3090.md:114 | OK |
| [[mmvq-n1-wiersze]] | 3090, 3da7a02ec | 09-chmura-3090.md:110 | OK |
| [[mmvq-n1-wiersze]] | 39 | NOTES.md:135 | OK (inny wiersz źródła, sprawdzone) |
| [[mmvq-n1-wiersze]] | 5.0, 5.8, 7.2, 8.5 | 09-chmura-3090.md:103 | OK |
| [[mmvq-n1-wiersze]] | 5060 | 09-chmura-3090.md:112 | OK |
| [[mmvq-n1-wiersze]] | 6.1 | 07-nasze-metody-uogolnienie.md:139 | OK |
| [[fuzje-lfm-moe]] | 0.565, 34 | 07-nasze-metody-uogolnienie.md:180 | OK |
| [[fuzje-lfm-moe]] | 0049, 4.979, 5.067, 682, 720 | NOTES.md:346 | OK |
| [[fuzje-lfm-moe]] | 0051, 4.642, 4.817, 521 | NOTES.md:348 | OK |
| [[fuzje-lfm-moe]] | 0053 | NOTES.md:353 | OK |
| [[fuzje-lfm-moe]] | 0056, 3.973, 4.070 | NOTES.md:364 | OK |
| [[fuzje-lfm-moe]] | 07 | NOTES.md:338 | OK |
| [[fuzje-lfm-moe]] | 1.2 | 09-chmura-3090.md:98 | OK |
| [[fuzje-lfm-moe]] | 1.6, 4.6 | 09-chmura-3090.md:94 | OK |
| [[fuzje-lfm-moe]] | 13 | 07-nasze-metody-uogolnienie.md:123 | OK |
| [[fuzje-lfm-moe]] | 2.1 | 09-chmura-3090.md:95 | OK |
| [[fuzje-lfm-moe]] | 2.2 | 07-nasze-metody-uogolnienie.md:127 | OK |
| [[fuzje-lfm-moe]] | 2.38, 5.34 | 09-chmura-5060ti.md:97 | OK |
| [[fuzje-lfm-moe]] | 2.39 | 09-chmura-3060.md:136 | OK |
| [[fuzje-lfm-moe]] | 2.5, 3.5, 3.7, 38, 71, 721 | NOTES.md:340 | OK |
| [[fuzje-lfm-moe]] | 2026 | NOTES.md:343 | OK |
| [[fuzje-lfm-moe]] | 3060 | 09-chmura-3090.md:114 | OK |
| [[fuzje-lfm-moe]] | 3090 | 09-chmura-3090.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[fuzje-lfm-moe]] | 3da7a02ec | 09-chmura-3090.md:110 | OK (inny wiersz źródła, sprawdzone) |
| [[fuzje-lfm-moe]] | 4.246, 4.451, 445 | NOTES.md:355 | OK |
| [[fuzje-lfm-moe]] | 4.99 | 09-chmura-5060ti.md:98 | OK |
| [[fuzje-lfm-moe]] | 5060 | 09-chmura-3090.md:112 | OK |
| [[fuzje-lfm-moe]] | 56 | NOTES.md:160 | OK (inny wiersz źródła, sprawdzone) |
| [[fuzje-lfm-moe]] | 6.5 | 09-chmura-3090.md:93 | OK |
| [[fuzje-lfm-moe]] | 64 | NOTES.md:337 | OK |
| [[latki-na-nvidia]] | 0001, 35 | CUDA-AUDIT.md:13 | OK |
| [[latki-na-nvidia]] | 0003 | CUDA-AUDIT.md:15 | OK |
| [[latki-na-nvidia]] | 0012 | CUDA-AUDIT.md:117 | OK |
| [[latki-na-nvidia]] | 0013 | CUDA-AUDIT.md:12 | OK |
| [[latki-na-nvidia]] | 0017 | CUDA-AUDIT.md:122 | OK |
| [[latki-na-nvidia]] | 0018 | CUDA-AUDIT.md:123 | OK |
| [[latki-na-nvidia]] | 0019 | CUDA-AUDIT.md:124 | OK |
| [[latki-na-nvidia]] | 0023 | CUDA-AUDIT.md:16 | OK |
| [[latki-na-nvidia]] | 0024 | CUDA-AUDIT.md:129 | OK |
| [[latki-na-nvidia]] | 0027 | CUDA-AUDIT.md:132 | OK |
| [[latki-na-nvidia]] | 0028 | CUDA-AUDIT.md:133 | OK |
| [[latki-na-nvidia]] | 0033, 0036 | CUDA-AUDIT.md:136 | OK |
| [[latki-na-nvidia]] | 0038 | CUDA-AUDIT.md:138 | OK |
| [[latki-na-nvidia]] | 0043 | CUDA-AUDIT.md:17 | OK |
| [[latki-na-nvidia]] | 0045 | CUDA-AUDIT.md:18 | OK |
| [[latki-na-nvidia]] | 0049 | CUDA-AUDIT.md:147 | OK |
| [[latki-na-nvidia]] | 0051 | CUDA-AUDIT.md:149 | OK |
| [[latki-na-nvidia]] | 0053, 0057, 5060 | CUDA-AUDIT.md:10 | OK |
| [[latki-na-nvidia]] | 0056 | CUDA-AUDIT.md:11 | OK |
| [[latki-na-nvidia]] | 128 | 09-chmura-3090.md:89 | OK |
| [[latki-na-nvidia]] | 165.5, 207.7 | 09-chmura-5060ti.md:110 | OK |
| [[latki-na-nvidia]] | 2026 | CUDA-AUDIT.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[latki-na-nvidia]] | 3060 | 09-chmura-3060.md:113 | OK |
| [[latki-na-nvidia]] | 3090 | 09-chmura-5060ti.md:55 | OK |
| [[latki-na-nvidia]] | 31 | 09-chmura-3090.md:74 | OK |
| [[latki-na-nvidia]] | 6.9 | 09-chmura-3090.md:104 | OK |
| [[latki-na-nvidia]] | 70 | CUDA-AUDIT.md:99 | OK |
| [[sm-86-89-120]] | 0025, 0057 | CUDA-AUDIT.md:7 | OK |
| [[sm-86-89-120]] | 0053 | CUDA-AUDIT.md:10 | OK |
| [[sm-86-89-120]] | 1.7 | 09-chmura-3090.md:104 | OK |
| [[sm-86-89-120]] | 1024,1 | CUDA-AUDIT.md:130 | OK (inny wiersz źródła, sprawdzone) |
| [[sm-86-89-120]] | 12 | CUDA-AUDIT.md:178 | OK |
| [[sm-86-89-120]] | 120, 16, 2026, 3060, 3090, 4060, 5060, 86 | CUDA-AUDIT.md:3 | OK |
| [[sm-86-89-120]] | 147 | CUDA-AUDIT.md:40 | OK |
| [[sm-86-89-120]] | 2.7 | 09-chmura-3090.md:113 | OK |
| [[sm-86-89-120]] | 24 | PLAN-TESTOW.md:89 | OK |
| [[sm-86-89-120]] | 32 | CUDA-AUDIT.md:181 | OK |
| [[sm-86-89-120]] | 48 | CUDA-AUDIT.md:226 | OK |
| [[sm-86-89-120]] | 64 | CUDA-AUDIT.md:222 | OK |
| [[sm-86-89-120]] | 8.5 | 09-chmura-3090.md:103 | OK |
| [[sm-86-89-120]] | 90 | CUDA-AUDIT.md:176 | OK |
| [[cuda-v070]] | 0013, 7b344114d | git:12 | OK |
| [[cuda-v070]] | 0053, 5dae6224f, 74 | git:2 | OK |
| [[cuda-v070]] | 0056, 2026, 7a538d96f | git:1 | OK |
| [[cuda-v070]] | 0488, 0488cba76 | git:9 | OK |
| [[cuda-v070]] | 3060 | git:13 | OK |
| [[cuda-v070]] | 3090 | git:17 | OK |
| [[cuda-v070]] | 398, 398ded98d | git:3 | OK |
| [[cuda-v070]] | 3da7a02ec | git:5 | OK |
| [[cuda-v070]] | 5060 | git:20 | OK |
| [[cuda-v070]] | 71412, 71412d9c6 | git:11 | OK |
| [[cuda-v070]] | b479c67dd | git:4 | OK |
| [[mtp-train]] | 0.2 | 11-mtp-pl-pilot.md:6 | OK |
| [[mtp-train]] | 10, 17 | 10-post-training.md:32 | OK |
| [[mtp-train]] | 2026 | 11-mtp-pl-pilot.md:1 | OK |
| [[mtp-train]] | 532, 532fd1057 | 11-mtp-pl-pilot.md:17 | OK |
| [[batch-invariant]] | 2026 | 12-bit-exact-spekulacja.md:154 | OK |
| [[batch-invariant]] | 204, 204f108de | git:3 | OK |
| [[batch-invariant]] | 6e261fdb4 | 12-bit-exact-spekulacja.md:182 | OK |
| [[batch-invariant]] | 77240, 77240c9b3 | 12-bit-exact-spekulacja.md:163 | OK |
| [[batch-invariant]] | c09ac6aab | git:4 | OK |
| [[2026-10-16-budzety-chmury]] | 0.82 | 09-chmura-3060.md:229 | OK |
| [[2026-10-16-budzety-chmury]] | 0.90 | 09-chmura-3090.md:183 | OK |
| [[2026-10-16-budzety-chmury]] | 00, 01, 2026, 38, 52 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5283 | OK |
| [[2026-10-16-budzety-chmury]] | 02, 31 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5287 | OK |
| [[2026-10-16-budzety-chmury]] | 1.05 | 09-chmura-5060ti.md:191 | OK |
| [[2026-10-16-budzety-chmury]] | 2.14 | 11-mtp-pl-pilot.md:8 | OK |
| [[2026-10-16-budzety-chmury]] | 2.77 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:1996 | OK (inny wiersz źródła, sprawdzone) |
| [[2026-10-16-budzety-chmury]] | 3060, 3090, 5060 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5286 | OK |
| [[2026-10-16-budzety-chmury]] | 35 | 2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5395 | OK |
| [[vast-ai]] | 0.08, 3060 | 05-chmura-gpu-do-testow.md:14 | OK |
| [[vast-ai]] | 0.097 | PLAN-TESTOW.md:99 | OK |
| [[vast-ai]] | 0.165, 163 | 05-chmura-gpu-do-testow.md:104 | OK |
| [[vast-ai]] | 0.188 | 05-chmura-gpu-do-testow.md:110 | OK |
| [[vast-ai]] | 0.228, 162 | 05-chmura-gpu-do-testow.md:99 | OK |
| [[vast-ai]] | 0.232 | PLAN-TESTOW.md:101 | OK |
| [[vast-ai]] | 0.294 | 05-chmura-gpu-do-testow.md:105 | OK |
| [[vast-ai]] | 0.507, 318 | 05-chmura-gpu-do-testow.md:103 | OK |
| [[vast-ai]] | 0.734 | 05-chmura-gpu-do-testow.md:108 | OK |
| [[vast-ai]] | 0.82 | 09-chmura-3060.md:229 | OK |
| [[vast-ai]] | 0.90 | 09-chmura-3090.md:183 | OK |
| [[vast-ai]] | 05, 1.05 | 09-chmura-5060ti.md:191 | OK |
| [[vast-ai]] | 1.8 | PLAN-TESTOW.md:11 | OK |
| [[vast-ai]] | 10, 2026 | 05-chmura-gpu-do-testow.md:13 | OK |
| [[vast-ai]] | 2.5 | PLAN-TESTOW.md:5 | OK |
| [[vast-ai]] | 2.77 | ręcznie | OK: suma 0.90 + 1.05 + 0.82 z raportów 09 (i wiadomość Main) |
| [[vast-ai]] | 3090 | 05-chmura-gpu-do-testow.md:15 | OK |
| [[vast-ai]] | 4090 | 05-chmura-gpu-do-testow.md:16 | OK |
| [[vast-ai]] | 445, 5090 | 05-chmura-gpu-do-testow.md:19 | OK |
| [[vast-ai]] | 50 | 05-chmura-gpu-do-testow.md:66 | OK |
| [[vast-ai]] | 5060 | 05-chmura-gpu-do-testow.md:17 | OK |
| [[vast-ai]] | 5070 | 05-chmura-gpu-do-testow.md:18 | OK |
| [[vast-ai]] | 64 | 05-chmura-gpu-do-testow.md:121 | OK |
| [[vast-ai]] | 7.7 | 09-chmura-5060ti.md:89 | OK (inny wiersz źródła, sprawdzone) |
| [[vast-ai]] | 80 | 05-chmura-gpu-do-testow.md:21 | OK |
| [[runpod]] | 0.22, 0.50, 22 | 05-chmura-gpu-do-testow.md:99 | OK |
| [[runpod]] | 0.34, 0.89 | 05-chmura-gpu-do-testow.md:103 | OK |
| [[runpod]] | 0.59 | 05-chmura-gpu-do-testow.md:111 | OK |
| [[runpod]] | 0.69, 1.19 | 05-chmura-gpu-do-testow.md:108 | OK |
| [[runpod]] | 05 | 11-mtp-pl-pilot.md:169 | OK |
| [[runpod]] | 1.11 | PLAN-TESTOW.md:11 | OK |
| [[runpod]] | 150 | 05-chmura-gpu-do-testow.md:101 | OK |
| [[runpod]] | 2.14, 3.50 | 11-mtp-pl-pilot.md:8 | OK |
| [[runpod]] | 2.39, 3070, 5090 | 05-chmura-gpu-do-testow.md:67 | OK |
| [[runpod]] | 2026 | 05-chmura-gpu-do-testow.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[runpod]] | 3.0 | PLAN-TESTOW.md:12 | OK |
| [[runpod]] | 3060 | 05-chmura-gpu-do-testow.md:68 | OK |
| [[runpod]] | 3090, 4090 | 05-chmura-gpu-do-testow.md:69 | OK |
| [[runpod]] | 48 | 11-mtp-pl-pilot.md:168 | OK |
| [[runpod]] | 7.65 | 11-mtp-pl-pilot.md:171 | OK |
| [[runpod]] | 96 | 11-mtp-pl-pilot.md:174 | OK |
| [[ollama]] | 0.40 | 09-chmura-3090.md:165 | OK |
| [[ollama]] | 1,5 | 03-silniki-i-stack.md:38 | OK |
| [[ollama]] | 1.3 | 01-konkurencja.md:144 | OK (inny wiersz źródła, sprawdzone) |
| [[ollama]] | 165, 190 | 01-konkurencja.md:49 | OK |
| [[ollama]] | 180.5 | 09-chmura-3090.md:172 | OK |
| [[ollama]] | 2026 | 01-konkurencja.md:46 | OK |
| [[ollama]] | 3090 | 01-konkurencja.md:410 | OK (inny wiersz źródła, sprawdzone) |
| [[ollama]] | 39.0 | 09-chmura-3090.md:171 | OK |
| [[ollama]] | 65 | 06-produkt-ux-prawo-biznes.md:17 | OK |
| [[liquidai]] | 10, 2026 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:313 | OK |
| [[liquidai]] | 13.58, 226.8 | 09-chmura-5060ti.md:177 | OK |
| [[liquidai]] | 24.8 | 09-chmura-5060ti.md:277 | OK |
| [[liquidai]] | 5060 | 04-wykrywanie-sprzetu-i-dobor-modeli.md:148 | OK (inny wiersz źródła, sprawdzone) |
| [[prismml]] | 1.76, 20, 27, 5.93, 98.2 | 10-post-training.md:329 | OK |
| [[prismml]] | 142 | 09-chmura-3060.md:31 | OK |
| [[prismml]] | 2026 | 10-post-training.md:3 | OK (inny wiersz źródła, sprawdzone) |
| [[prismml]] | 3060 | 09-chmura-3060.md:36 | OK |
| [[prismml]] | 44.75 | 09-chmura-3060.md:102 | OK |
| [[raport-08-platforma]] | 0001 | 08-analiza-platformy-latek.md:12 | OK |
| [[raport-08-platforma]] | 0022 | 08-analiza-platformy-latek.md:27 | OK |
| [[raport-08-platforma]] | 0042 | 08-analiza-platformy-latek.md:26 | OK |
| [[raport-08-platforma]] | 0048, 0065, 0069, 13, 15 | 08-analiza-platformy-latek.md:39 | OK |
| [[raport-08-platforma]] | 0054 | 08-analiza-platformy-latek.md:25 | OK |
| [[raport-08-platforma]] | 0060, 0061, 2026 | 08-analiza-platformy-latek.md:19 | OK |
| [[raport-08-platforma]] | 07 | 08-analiza-platformy-latek.md:23 | OK |
| [[raport-08-platforma]] | 08 | 09-chmura-3090.md:157 | OK |
| [[raport-08-platforma]] | 09 | 09-chmura-3090.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[raport-08-platforma]] | 1.23 | 09-chmura-3090.md:196 | OK (inny wiersz źródła, sprawdzone) |
| [[raport-08-platforma]] | 1.50 | 09-chmura-3090.md:197 | OK (inny wiersz źródła, sprawdzone) |
| [[raport-08-platforma]] | 1.736, 14, 14.14 | 08-analiza-platformy-latek.md:29 | OK |
| [[raport-08-platforma]] | 16 | 08-analiza-platformy-latek.md:36 | OK |
| [[raport-08-platforma]] | 25 | 08-analiza-platformy-latek.md:35 | OK |
| [[raport-08-platforma]] | 27 | 09-chmura-3090.md:160 | OK |
| [[raport-08-platforma]] | 70 | 08-analiza-platformy-latek.md:1 | OK (inny wiersz źródła, sprawdzone) |
| [[raport-08-platforma]] | 73 | 08-analiza-platformy-latek.md:34 | OK |
| [[raport-10-post-training]] | 0.2, 1.7 | 11-mtp-pl-pilot.md:6 | OK |
| [[raport-10-post-training]] | 0.21, 3090 | 10-post-training.md:13 | OK |
| [[raport-10-post-training]] | 0.73, 80 | 10-post-training.md:18 | OK |
| [[raport-10-post-training]] | 00, 30 | 10-post-training.md:9 | OK |
| [[raport-10-post-training]] | 1.83, 2.73, 3.0, 3.3, 4.2, 6.8 | 10-post-training.md:31 | OK |
| [[raport-10-post-training]] | 10 | 10-post-training.md:1 | OK |
| [[raport-10-post-training]] | 11 | 10-post-training.md:39 | OK |
| [[raport-10-post-training]] | 14 | 10-post-training.md:42 | OK |
| [[raport-10-post-training]] | 16, 2026 | 10-post-training.md:3 | OK |
| [[raport-10-post-training]] | 17 | 10-post-training.md:32 | OK |
| [[raport-10-post-training]] | 2.2, 2.4, 3.74 | 10-post-training.md:35 | OK |
| [[raport-10-post-training]] | 3.07 | 10-post-training.md:20 | OK |
| [[index]] | 0001 | STATUS-NEXT.md:3 | OK |
| [[index]] | 0013 | 09-chmura-3090.md:199 | OK |
| [[index]] | 10, 2026 | STATUS-NEXT.md:6 | OK |
| [[index]] | 109.0, 1115, 27, 27.74, 43.2 | STATUS-NEXT.md:10 | OK |
| [[index]] | 11 | 09-chmura-5060ti.md:226 | OK |
| [[index]] | 1109, 115.5, 26, 26.68, 44.0 | STATUS-NEXT.md:11 | OK |
| [[index]] | 128, 4096 | STATUS-NEXT.md:7 | OK |
| [[index]] | 13 | 09-chmura-5060ti.md:216 | OK |
| [[index]] | 14 | STATUS-NEXT.md:15 | OK |
| [[index]] | 144.47, 147.69, 207.86 | 09-chmura-5060ti.md:240 | OK |
| [[index]] | 16 | 09-chmura-3090.md:233 | OK |
| [[index]] | 17 | 09-chmura-3090.md:203 | OK |
| [[index]] | 176.0, 180.2, 263.9 | 09-chmura-3090.md:224 | OK |
| [[index]] | 2.14 | 09-chmura-3090.md:211 | OK |
| [[index]] | 2.77 | 11-mtp-pl-pilot.md:112 | OK (inny wiersz źródła, sprawdzone) |
| [[index]] | 22, 22.1 | 09-chmura-3090.md:215 | OK |
| [[index]] | 22.3, 23.4 | 09-chmura-3060.md:242 | OK |
| [[index]] | 23 | 09-chmura-3090.md:214 | OK |
| [[index]] | 25 | 09-chmura-5060ti.md:236 | OK |
| [[index]] | 264.3, 267.3, 3.74, 6291 | STATUS-NEXT.md:13 | OK |
| [[index]] | 28.07, 37.32, 51.66 | 09-chmura-5060ti.md:222 | OK |
| [[index]] | 286 | AUDYT.md:297 | OK |
| [[index]] | 289.7, 293.7, 3.41, 6175 | STATUS-NEXT.md:12 | OK |
| [[index]] | 33.1, 35.5 | 09-chmura-3060.md:258 | OK |
| [[index]] | 39.0, 49, 63.3, 78.0 | 09-chmura-3090.md:209 | OK |
| [[index]] | 44.8 | 09-chmura-5060ti.md:227 | OK |
| [[index]] | 70, f61994f58 | STATUS-NEXT.md:5 | OK |
| [[index]] | 7900 | 11-mtp-pl-pilot.md:9 | OK |


## Aktualizacja: raporty 14 i 15a–15f (2026-10-16)
Automatyczna kontrola 44 notatek, których `zrodlo` zaczyna się od raportu 14/15: 676 liczb, 675 znalezionych w raportach 14/15, ich katalogach skryptów lub `BENCHMARKI-NVIDIA-2026-10-16.md`; jedna (`02153` w `repo/auto-gpu-kernel`) pochodzi z raportu repo 14-auto-gpu-kernel (OK). Liczby ze źródeł pierwotnych sprawdzone ręcznie: `spec_sweep.jsonl` (incydent 5.618 t/s), `server-context.cpp:5171` (`build_info`), `ggml-quants.c:384` i `llama-graph.cpp:1595-1601` (NVFP4), `hip_runtime_api.h:1670-1700,2110-2116`, 70 plików łatek. Błędnych: 0.

## Aktualizacja: 12 §13, 16c, 16d, 16h, 16i (2026-10-16)
Liczby w nowych i zmienionych notatkach przepisane ręcznie z wierszy podanych w `zrodlo` (raporty 12, 14 §13, 16c, 16d, 16h, 16i; `/tmp/bxv/summary.txt:71-103` dla prędkości bit-exact). Rozbieżność źródeł: Magnitude 9B copy 64k 175.8 t/s (16d, mediana) vs 174.8 (16i, suma żądań) – w notatkach obie z opisem; za kanoniczne przyjęto 16d (decyzja Main). Pominięte celowo (repo publiczne): adres IP hosta z 16c §8, ID instancji, kredyt Vast. Błędnych: 0.

## Aktualizacja: 16e i incydent nadpisania (2026-10-18)
Liczby z 16e przepisane z wierszy w `zrodlo` (raport 16e i `quantkld-20261016/*/speed.md`, `kld-all/kld.md`); błędnych 0. **Uwaga:** `results/3060-20261016/build/times.jsonl` (źródło wiersza [[nvidia/cuda-stos]] wyżej) i `hw/*` zostały 2026-10-16 nadpisane danymi innej instancji – weryfikacja z audytu 2026-10-16 była przed nadpisaniem, dziś pliku nie da się użyć ponownie ([[lekcja-unikalny-katalog-wynikow]]).

## Aktualizacja: 16c §9, 16j, landing, chłodzenie (2026-10-18)
Liczby przepisane z wierszy w `zrodlo` (16c:191-252, 16j:7-110, `app/REPORT.md:238-260`, `REDESIGN.md:154-169`, `scripts/qa/README.md`); juror r7 7/7/6 i „wrapper omp ukrył ostrzeżenia” tylko w sekcji „Do bazy wiedzy” LandingWow (transkrypt, wiersz 1224) – w REDESIGN.md brak wiersza r7. Temperatury przed/po restarcie z komunikatu Main; odczyt pod obciążeniem (3402 RPM, 71/78 °C) z sysfs przez WikiIngest. Źródła `/tmp/bxv/summary.txt` i `/tmp/bxd/*` utracone przy restarcie 2026-10-18 ~18:53 UTC, przed archiwizacją (nie ma ich w `tmp-archive-20261018`); kanoniczne źródło: raport 12 §13; liczby z nich sprawdzone 2026-10-16, przed utratą. Błędnych: 0.

## Aktualizacja: 16g (2026-10-18)
Liczby w 7 nowych i 5 zmienionych notatkach przepisane z wierszy 16g podanych w `zrodlo` (tabele §1–§3, §5) i `lfm-decode-round4.md:154-159` (objaw 285 W z rundy 4). `lekcja-limit-mocy-285w` ma `status: do-sprawdzenia`, bo przyczyna (limit mocy) to hipoteza. Błędnych: 0.

## Aktualizacja: 16a (2026-10-18)
Liczby z 16a (tabele §1–§3) przepisane z wierszy w `zrodlo`; „16 kopii flagi” i ułamki 6/29/35/44% z §1–§2. Błędnych: 0.

## Aktualizacja: 16f i wentylator (2026-10-18)
Liczby 16f przepisane z tabel E1–E5 (wiersze w `zrodlo`). Wentylator: progi z `fan.sh:16-18` (FAN=90, BUSY=10, IDLE_HOLD=20; od 2026-10-19 FAN=100 i nagłówek poprawiony), przyczyny i weryfikacja (3320–3500 RPM, 73/74 °C, ~1800 RPM, 88–90 °C) z komunikatu Main; Chrome ~90% rdzenia przez 3 h z komunikatu Main. Błędnych: 0.

## Aktualizacja: 16k i bezpieczeństwo (2026-10-19)
Liczby 16k z tabel §4–§5 (wiersze w `zrodlo`); progi strażnika z `gpu-guard.sh:1-45`; „10 resetów w bootach −2/−1/0” i 90 °C VRAM z komunikatu Main (nie sprawdzane przez WikiIngest). Błędnych: 0.

## Aktualizacja: 16b (2026-10-19)
Liczby z tabel 16b §2–§5 (wiersze w `zrodlo`, w tym `e3_summary.txt`, `e4_summary.txt`, `e2_table.txt`). Copy W16 355.0 t/s pochodzi z serii po naprawie wentylatorów (W8 w tej serii 235.8, nie 230.6) – opisane w notatce. Błędnych: 0.

## Aktualizacja: raport 17 (2026-10-19)
Liczby z tabel i §0–§7 raportu 17 (wiersze w `zrodlo`); koszt PM4=0 (108.8 → 103.7, 293.6 → 259.3 t/s) zgodny z wcześniejszym audytem `NOTES.md:375`. Poprawione 2 notatki: reset 23:25 przypisany wcześniej kolizji blokad. Błędnych: 0 (poza tą korektą).

## Aktualizacja: REKORDY (2026-10-19)
Każda liczba w [[REKORDY]] sprawdzona skryptem względem cytowanego wiersza (47 par plik:wiersz); 5 odwołań poprawionych o 1 wiersz (16c:120, 14:95-97, 16e:247/249, 12:323). Wiersze `spec_sweep.jsonl` (113, 86, 172, 189–191) odczytane bezpośrednio. Błędnych liczb: 0.

## Aktualizacja: raport 20 (2026-10-19)
Liczby z 20-build-topka.md:14-17,65-72; alarm z `gpu-guard.log:3`, progi z `gpu-guard.sh:38`; „0 RPM do ~70 °C” z komentarza `gpu-guard.sh:36-37`, `fan_zero_rpm_enable` od 6.13 z komunikatu Main (jądro tu: 6.8.0-138). Błędnych: 0.

## Aktualizacja: raport 17 §9 (2026-10-19)
Liczby z 17-gpu-page-fault.md:210-425 (vmstat, timeouty MES 107–128 ms, doorbell `0x100a`, progi restore 1/1/100 ms). Notatki `decyzje/2026-10-19-pm4-w-serwerach` (proponowanej w §9.7) nie ma – decyzja PM4 jest otwarta, więc trafiła do `otwarte-decyzje-produktu`. Błędnych: 0.

## Powiązane
- [[index|Strona główna]]
- [[KONWENCJE]]
- [[wiki-py]]
- [[log]]
