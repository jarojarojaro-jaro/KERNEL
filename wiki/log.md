---
typ: meta
tags: [meta]
aktualizacja: 2026-10-16
zrodlo: wiki
status: aktualne
---
# Dziennik wiki

**Chronologiczny zapis zmian w wiki (tylko dopisywanie); każdy wpis zaczyna się od `## [data] rodzaj | opis`.**

Ostatnie wpisy: `grep "^## \[" wiki/log.md | tail -5`.

## [2026-10-16] ingest | Zasiew wiki
Szkielet 16 kategorii, `tools/wiki.py` (lint/index/search), 140 notatek z `qwen-opt/NOTES.md`, `STATUS-NEXT.md`, `qwen-opt/research/**`, `qwen-opt/tools/**`, `product/**`, `reports/`, `hardware/`, `~/qwen-opt/cloud/**`, `~/wt/rebase070/REBASE.md`. Wypełnione: metody, kernele, latki, rocm, nvidia, karty, modele, eksperymenty, chmura; częściowo narzedzia, decyzje, lekcje. Puste huby: repo, research, produkt, ludzie-firmy (do uzupełnienia). Lint: 0 błędów.

## [2026-10-16] ingest | Dokończenie wiki (jeden agent)
Nowe notatki: repo/ (30 repo z przeglądu, Strata, TensorFold, ik_llama.cpp, laya-mlx, fork PrismML, speculators/SpecForge, nasze gałęzie i worktree), research/ (raporty 01–08, 10, 12, 13, przegląd 30 repo, runda 6; raportów 09 i 11 nie ma), produkt/ (sekcje PLAN.md + aplikacja „w budowie”), ludzie-firmy/ (23 firmy i projekty), narzedzia/ (+13), lekcje/ (+20: tryby awarii z raportu 07 i lekcje z 2026-10-16), decyzje/ (+9). Naprawione sieroty. Audyt liczb: [[AUDYT]] (1 liczba poprawiona, 23 `zrodlo` uzupełnione). Odświeżony „stan na dziś” w [[index]].

## [2026-10-16] ingest | Prototyp aplikacji (app/REPORT.md)
Przepisana [[aplikacja-w-budowie]] (status aktualne, commit `9f96ff4`); nowe: [[app-system-projektowy]], [[app-landing]], [[app-onboarding-prototyp]], [[app-skrypty-skanu]], [[app-prototyp-desktop]], [[otwarte-decyzje-produktu]]. Audyt: +66 liczb, 0 błędnych.

## [2026-10-16] ingest | Wyniki finalne: chmura NVIDIA, pilot MTP, bit-exact
Nowe: [[raport-09-chmura-3090]], [[raport-09-chmura-5060ti]], [[raport-09-chmura-3060]], [[raport-11-mtp-pl-pilot]], [[2026-10-16-mtp-pl-pilot]], lekcje [[lekcja-fit-mtp-16gb]], [[lekcja-limit-cpu-kontenera]], [[lekcja-md5-wzgledem-upstreamu]], [[lekcja-mtp-glowica-optimum]], [[lekcja-nadpisanie-dzialajacego-skryptu]]. Przepisane z `do-sprawdzenia` na finalne: [[nvidia-wyniki-2026-10-16]], karty 3090/5060 Ti/3060, [[2026-10-16-kampania-nvidia]], [[saluki]], [[bonsai]]; uzupełnione m.in. [[nvfp4]], [[lfm2-5-24b-a2b]], [[glowica-mtp]], [[mmvq-n1-wiersze]], [[fuzje-lfm-moe]], [[latki-na-nvidia]], [[raport-12-bit-exact]], [[lekcja-bit-exact-attention]]. Wydatki końcowe w [[2026-10-16-budzety-chmury]]. „Stan na dziś”: nic nie działa. Audyt: +998 liczb, 0 błędnych.

## [2026-10-16] ingest | Raporty 14 i 15a–15f
Nowe: [[raport-14-nemotron-3090]], [[raport-15a-monokernel]], [[raport-15b-spekulacja-frontier]], [[raport-15c-nowe-silniki]], [[raport-15d-prefill-dlugi-kontekst]], [[raport-15e-kwantyzacja-nowa]], [[raport-15f-agentowa-nauka]] oraz notatki repo/modeli/lekcji/metod z ich sekcji „Do bazy wiedzy” (m.in. [[magnitude]], [[tqllm]], [[swift-1-5]], [[fabryka-v1]], [[zestaw-odlozony]]). Zaktualizowane m.in. [[nvidia-wyniki-2026-10-16]], [[fattn-kvq]], [[tensorfold]], [[ik-llama-cpp]], [[werdykt]], [[otwarte-decyzje-produktu]]. Audyt: 676 liczb, 0 błędnych.

## [2026-10-16] ingest | Raport 12 §13 (walidacja bit-exact) i 16c (kvq na CUDA)
Zaktualizowane: [[2026-10-16-bit-exact]] (run 4: PASS, prędkość na flagach produkcyjnych, regresja nowego drzewa ~5–6%), [[raport-12-bit-exact]], [[fattn-kvq]], [[fa-kv-kwantyzowane-cuda]], [[raport-15d-prefill-dlugi-kontekst]] (korekta MTP@64k), [[harness-chmurowy]]. Nowe: [[2026-10-16-kvq-cuda]], [[raport-16c-kvq-cuda]], [[2026-10-16-kvq-cuda-zostaje]], [[lekcja-kld-szum-kolejnosci]], [[lekcja-vast-authorized-keys]], [[lekcja-pkill-wlasna-powloka]].

## [2026-10-16] ingest | Raport 16h (fabryka v1 zbudowana)
Nowe: [[fabryka-cli]], [[2026-10-16-backtest-regul-fabryki]], [[raport-16h-fabryka-v1]]. Zaktualizowane: [[fabryka-v1]] (status aktualne), [[zestaw-odlozony]], [[pomiar-abba]], [[lekcja-label-to-nie-binarka]], [[lekcja-pdl-sm120]], [[seria-amd-opt]]. `log.md` zwolniony z limitu słów (dziennik), zmiana w `tools/wiki.py` i [[KONWENCJE]].

## [2026-10-16] ingest | Raporty 16d i 16i (Magnitude) + decyzja „badamy Magnitude”
Nowe: [[2026-10-16-magnitude-vs-fork]] (z danymi 9B na 5060 Ti), [[2026-10-16-magnitude-rozklad-wygranej]], [[raport-16d-magnitude-vs-nasz]], [[raport-16i-magnitude]], [[firma-magnitude]], [[kontroler-szerokosci-draftu]], [[sprzezone-probkowanie-draftu]], [[lekcja-sufit-bloku]], [[lekcja-drafter-gleboki-vs-mtp]], [[2026-10-16-badamy-magnitude]]. Zaktualizowane: [[magnitude]] (status aktualne), [[drafter-dflash]], [[mmvq-multikolumnowe]], [[produkt-ryzyka]], [[lekcja-limit-cpu-kontenera]], [[lekcja-pkill-wlasna-powloka]], [[zgodnosc-bitowa-md5]], [[2026-10-16-nemotron-3090]] (KLD PASS).

## Powiązane
- [[index|Strona główna]]
- [[KONWENCJE]]
