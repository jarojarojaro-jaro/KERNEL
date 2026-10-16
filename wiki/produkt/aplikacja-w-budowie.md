---
typ: produkt
tags: [produkt, app, landing]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/app/REPORT.md:1-30,48,111-116; git -C ~/KERNEL log -1 9f96ff4
status: aktualne
---
# Aplikacja (~/KERNEL/app): stan prototypu

**Pierwsze elementy produktu zbudowane lokalnie przez AppStudio (2026-10-16, commit `9f96ff4`): system projektowy „Tacho”, statyczna strona SvelteKit PL/EN (47 stron), prototyp onboardingu, skrypty skanu, prototyp aplikacji desktop (8 ekranów), makieta TUI i dokument architektury; nic nie jest wdrożone.**

Dokumenty: [REPORT.md](../../app/REPORT.md), [DESIGN.md](../../app/design/DESIGN.md), [APP-ARCHITECTURE.md](../../app/design/APP-ARCHITECTURE.md).

- Lokalnego GPU nie używano: Chrome do zrzutów z `--disable-gpu`, `strace` potwierdził brak otwarć `/dev/dri` i `/dev/kfd`.
- Wszystkie liczby wydajności na stronie pochodzą z jednego rejestru `landing/src/lib/data/measurements.ts` (plik i linia źródła); bez mnożników „×” i bez słupka „typowa aplikacja”, dopóki nie zmierzymy Ollamy/LM Studio (E1).
- Wyniki z chmury wczytuje `scripts/sync-results.ts` z `~/qwen-opt/cloud/results/*/scorecard.json`; na dziś tylko RTX 3090, pokazany jako „wstępne” z md5 `DIFF-BUILD`.
- Zrzuty ekranu: 56 plików w `app/screens/`.
- Do zrobienia: `scan.ps1` na prawdziwym Windowsie i `scan-macos.sh` na Macu, przesunięcie układu w EN hero (CLS do 0,12), scorecardy 5060 Ti/3060, pomiar E1.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-system-projektowy]]
- [[app-landing]]
- [[app-onboarding-prototyp]]
- [[app-skrypty-skanu]]
- [[app-prototyp-desktop]]
- [[otwarte-decyzje-produktu]]
- [[produkt-landing-i-onboarding]]
- [[nvidia-wyniki-2026-10-16]]
