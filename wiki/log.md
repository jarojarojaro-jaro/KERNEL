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

## Powiązane
- [[index|Strona główna]]
- [[KONWENCJE]]
