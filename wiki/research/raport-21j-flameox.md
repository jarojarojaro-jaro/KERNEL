---
typ: research
tags: [research, profilowanie, narzedzia]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21j-flameox.md:1-291
status: aktualne
---
# Raport 21j: flameox – nie instalujemy, bierzemy zasady

**flameox to serwer MCP i CLI w Pythonie (24 093 linii), który uruchamia cudze profilery i zwraca agentowi ograniczone, typowane „dowody” w magazynie sha256 – nie silnik, bez kerneli i bez flame graphów; dla AMD prawie bezużyteczny (tylko `rocprofv3 --output-format pftrace`, pierwsze ≤ 1000 slice'ów bez agregacji per kernel – 0.35% populacji na naszym trace `prof/mtp4`) (raport 21j, CPU, 2026-10-19).**

- Statystyka słabsza niż w fabryce: metryka to `wall_time_ns` całego procesu (z ładowaniem modelu), losowa kolejność zamiast ABBA, bez A/A i MDE, percentile bootstrap – własne demo A/A dało CI [0.58, 29.80] ms dla identycznych programów ([[lekcja-bootstrap-male-n]]).
- Nie instalujemy ani jako narzędzia, ani jako MCP: katalog `tools/list` 1 047 166 B (~70 tys. tokenów opisów i schematów), 20 narzędzi capture pozwala agentowi odpalić GPU z pominięciem fabryki (łamie H0–H2, H8 z [[petla-rsi-f]]), blokuje `LD_LIBRARY_PATH` (od niego zależy wybór buildu w A/B).
- Zasady do przeniesienia: P1 percentile bootstrap tylko przy n ≥ 12, poniżej Student t ([[fabryka-cli]]); P2 inwarianty pokrycia profilu ([[dowod-z-profilu]]); P3 `factory preserve` – magazyn dowodów sha256 + zstd (jeden trace 158.2 → 8.56 MB, ×18.5); P4 werdykt G1 przeliczany z liczb `test-backend-ops`; P5 metadane zegara pomiaru; P6 digest obciążenia bez promptów dla telemetrii produktu.
- Repo: [[flameox]].

## Powiązane
- [[research/_hub|research]]
- [[smokinggun]]
- [[raport-21i-rsi-inference-bench]]
