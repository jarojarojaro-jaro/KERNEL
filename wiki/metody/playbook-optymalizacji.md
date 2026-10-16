---
typ: metoda
tags: [metody, playbook, proces]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:28-35,187-235; ~/KERNEL/product/PLAN.md:224-234
status: aktualne
---
# Playbook optymalizacji

**Każda optymalizacja przechodzi tę samą pętlę: sufit → profil → hipoteza z budżetem → łatka z wyłącznikiem → bramka poprawności → przeplatane A/B → wpis w NOTES.**

Dziesięć kroków (PLAN §4.4, raport 07 §2.2):
1. sufit pasma ([[sufit-pasma-i-mapa-czasu]]);
2. profil per token (rocprofv3);
3. koszt granicy kernela ([[mikrobench-granicy-kernela]]);
4. ablacja ([[ablacja]]);
5. hipoteza z budżetem w µs lub ms/krok, przeliczonym na t/s;
6. łatka z wyłącznikiem env ([[wylacznik-w-kazdej-latce]]);
7. testy op-level (`test-backend-ops` + nowy przypadek na każdą fuzję);
8. bramka: bitowa ([[zgodnosc-bitowa-md5]]) albo KLD ([[bramka-kld-kanarki]]);
9. przeplatane A/B na ms/krok ([[pomiar-abba]]);
10. wpis w NOTES, także dla wyników negatywnych ([[wyniki-negatywne]]).

Na rundę: osobna gałąź i worktree (25 gałęzi `opt-*`, w `~/wt` 40+ katalogów wg raportu 07). Zmianę scalamy tylko przy realnym zysku: GDN fast był bitowy, ale +0.15% to szum, więc nie trafił do `amd-opt`. Po instalacji: greedy md5 = baza i soak (`pm4_soak.py`).

Ten sam schemat przeniesiono na CPU ARM telefonu (`~/telefon/PROMPT-minicpm-speed.md`, etap 0: sufit pasma i SDOT).

## Powiązane
- [[metody/_hub|Metody]]
- [[analiza-platformy]]: obowiązkowy krok od 2026-10-15
- [[dowod-offline]]
- [[kernel-tuner]]: strojenie parametrów zamiast nowej kampanii na pokrewnych kartach
- [[loo]]: które łatki naprawdę coś dają
- [[serializacja-gpu]]
- raport-07-metody
- fabryka-przepisow: playbook jako proces fabryki
