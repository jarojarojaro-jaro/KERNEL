---
typ: lekcja
tags: [lekcje, landing, svelte]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/app/REPORT.md:238-260; ~/KERNEL/app/design/REDESIGN.md:154-169; ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8/LandingWow.jsonl:1224
status: aktualne
---
# Element blokowy w `<p>` → hydration_mismatch → puste liczniki

**`SourceTip` renderował popover blokowy (`div`/`p`/`ul`) wewnątrz `<p>`; przeglądarka naprawiła HTML, Svelte 5 zgłosił `hydration_mismatch` i przebudował stronę, więc intro, wyścig i liczniki restartowały się albo zostawały puste w przeglądarce użytkownika (landing, rundy 6–8, 2026-10-16/18).**

- Ostrzeżeń nie było widać przez wrapper przeglądarki omp; pokazało je dopiero puppeteer-core podłączone wprost do Chrome (`scripts/qa/hyd.ts`).
- Intro startujące od `opacity: 0` zawodziło przy wolnym ładowaniu: test hero 12/40 świeżych ładowań przed poprawką, 40/40 po przejściu na intro tylko z `transform`.

Reguły: popovery wyłącznie z elementów inline (phrasing content); wartości końcowe liczników w HTML z SSR; po każdej zmianie strony sprawdzać ostrzeżenia hydracji bezpośrednio przez CDP, nie przez wrapper.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[app-landing]]
- [[landing-qa]]
- [[lekcja-mikrobench-klamie]]
