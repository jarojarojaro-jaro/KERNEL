---
typ: produkt
tags: [produkt, plan, prawo]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:317-331
status: aktualne
---
# Prawo, dystrybucja, prywatność

**Potrzebna spółka z o.o. (podpis Azure w UE, Apple dla organizacji); AI Act art. 50(2) to główne otwarte pytanie; telemetria domyślnie wyłączona; koszt roku 1 ~5.8 tys. zł opłat twardych.**

- Spółka: S24, ~275 zł, 1–3 dni; potem D-U-N-S, Apple $99/rok, Artifact Signing ~$10/mies., Microsoft Store za darmo.
- Podpisany każdy .exe/.dll; profile to podpisane dane (JSON), nie kod.
- AI Act: art. 50(1) informacja w UI; art. 50(2) oznaczanie tekstu – do kancelarii lub KRiBSI, 1–3 miesiące, równolegle z fazą 1.
- RODO/PKE: tylko kategorie sprzętu, bez numerów seryjnych, UUID, hosta; odrzucanie IP.
- CRA: polityka podatności, SBOM; PLD: OC produktu (od 9.12.2026).
- Licencje: NOTICE llama.cpp, ROCm, CUDA; Llama 4 wykluczona; modele uncensored poza katalogiem i marketingiem.
- Z kancelarią i ubezpieczeniem ~30–55 tys. zł `[SZACUNEK]`.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Werdykt „jesteśmy providerem aplikacji czatu” (raport 06 §2.2.3, `product/research/06-produkt-ux-prawo-biznes.md:219-237`) zderzyłem z tym, co wydaliśmy. Aplikacja to głównie lokalny endpoint OpenAI dla innych programów, ale na ekranie gotowości ma panel czatu „Sprawdź na żywo” (`app/engine/src/ui/screens/Ready.svelte:141-142`, `app/engine/src/ui/components/Chat.svelte`, `src/ui/lib/i18n.ts:301`).
- Panel czatu to system AI rozmawiający z człowiekiem, więc art. 50(1) (jasna informacja „rozmawiasz z AI”, obowiązuje od 2.08.2026) nas dotyczy. W kodzie aplikacji nie ma ani tej informacji, ani decyzji o art. 50(2) (`rg -i 'AI Act|watermark|art. 50' app/engine/src` = 0).
- Samo API dla cudzych programów jest bliżej „komponentu” niż systemu (wytyczne odróżniają systemy od komponentów, `06:229`) `[INFERENCE, nie porada prawna]`.
- W Polsce kontrole KRiBSI i kary działają od 28.10.2026 (`06:237`).
- Co bierzemy: komunikat „to jest model AI” w panelu czatu (spełniający dostępność, art. 50(5)) przed każdym wydaniem; opinia o art. 50(2) przed udostępnieniem czatu szerzej; przy decyzjach UX pytać „czy to zmienia naszą rolę w AI Act”.

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-biznes-edycje]]
- [[produkt-stack]]
- [[raport-06-produkt]]
- [[lfm2-5-uncensored]]
