# 21k – morluto/smokinggun: czy to coś dla nas?

Data: 2026-10-19. Źródło: https://github.com/morluto/smokinggun, klon `~/qwen-opt/research-src/smokinggun` (HEAD `cf3a387`, 2026-08-29). Nic nie było budowane ani uruchamiane, bo do werdyktu wystarczył kod.

## Werdykt: NIE STOSUJE SIĘ do naszej pracy nad GPU i inferencją

Nazwa sugeruje szukanie przyczyny regresji („smoking gun”), ale narzędzie tego nie robi. Ma dwie funkcje:

1. **Statyczny skaner złożoności algorytmicznej kodu CPU.** Używa tree-sitter na 13 językach. Ma sześć reguł, wszystkie dotyczą wzorców w pętlach: `membership-in-loop`, `nested-or-callback-loop`, `sort-in-loop`, `typescript-call-in-loop`, `typescript-collection-operation-in-loop` i `python-collection-membership-in-loop` (`src/scanners/*`, `fixtures/corpus/labels.json`). Mapa rozszerzeń nie obejmuje `.cu`, `.cuh` ani `.hip` (`src/scanners/structural-finding.ts:7-30`), więc kerneli ggml-cuda i ggml-hip w ogóle nie widzi. Problemy w llama.cpp to bandwidth, occupancy, LDS i synchronizacja. Wzorce typu O(n²) w pętlach hosta w tym kodzie nie występują.
2. **Import gotowych wyników benchmarków i porównanie baseline z candidate.** Obsługiwane formaty: hyperfine, pyperf, Google Benchmark, criterion i JMH (`src/adapters/benchmarks.ts:14-22`), do tego pprof i podsumowanie Perfetto (`src/adapters/profiles.ts`). Gate promocji zwraca `eligible`, `blocked` albo `inconclusive` wraz z listą powodów (`src/measurements/compare.ts:285-397`). Polityka statystyczna to tylko „mediana lepsza o X%” lub „rozłączne IQR” (`compare.ts:399-411`). Porównywane środowisko to wyłącznie `node/platform/arch` (`compare.ts:268-270`). Narzędzie z założenia niczego nie uruchamia (README, `docs/architecture.md`).

Nie robi nic z tego, o co pytaliśmy:
- nie bisektuje regresji;
- nie analizuje kerneli ani trace'ów GPU (Perfetto zna tylko jako zaimportowane podsumowanie SQL);
- nie diagnozuje faultów GPU, więc nie pomoże przy PM4 page fault z raportu 17;
- nie szuka rozbieżności numerycznych, więc nie zastąpi pracy bit-exact z raportu 12 ani `llama-bx-diff`.

**Jedyna część, która się z nami pokrywa (gate z dowodami), jest u nas silniejsza.** Fabryka v1 (`~/qwen-opt/factory/README.md:19,75,86,103-116`) już:
- przypina sha256 binarek, `.so`, modelu i zestawu odłożonego;
- liczy ABBA + A/A z 95% CI (t-Student lub bootstrap) zamiast samej mediany lub IQR;
- ma bogatszą taksonomię werdyktów (CONFIRMED/NULL/REFUTED/REGRESSION/INVALID/UNMEASURED/NEEDS-HUMAN);
- prowadzi ledger z łańcuchem hashy. Smokinggun ma odpowiednik w postaci parent-linked commitów investigation z compare-and-swap (`docs/architecture.md` §5).

Zasadę smokinggun „brak dowodu ≠ pusty wynik” realizuje u nas werdykt UNMEASURED. Nie ma więc czego adoptować. Nie ma też żadnych implikacji dla bezpieczeństwa sprzętu, bo narzędzie jest offline, read-only i nie wykonuje kodu.

## Fakty o projekcie

| Pole | Wartość | Źródło |
|---|---|---|
| Język / runtime | TypeScript, Node ≥ 22.18, oclif CLI, web-tree-sitter (WASM grammars), zod | `package.json` |
| Rozmiar | ok. 8,7 tys. linii TS bez testów | `wc -l` na `src/**/*.ts` |
| Wersja | 5.0.0 (w 5.0.0 usunięto system „executable adapter”, więc import-only) | `CHANGELOG.md` |
| Licencja | MIT | `LICENSE` |
| Dojrzałość | repo od 2026-08-05, 52 commity (42 autora, reszta boty), ostatni commit na `main` 2026-08-29; 32 gwiazdki, 3 forki, 12 otwartych issues (stan 2026-10-19) | `git log`, GitHub API |
| Jakość | vitest + coverage gate, oxlint, knip, etykietowany korpus fixture'ów (16 przypadków) | `AGENTS.md`, `fixtures/corpus/labels.json` |
| Twierdzenia | „Findings are candidates, not proof”; skan jest offline i read-only; pomiary to wyłącznie importowane artefakty | README |

Twierdzeń nie da się zakwestionować, bo są skromne. Mocno trzymanych granic (immutable capture, content-addressed reports) dotrzymuje kod `compare.ts` i `architecture.md`. Problem nie leży w jakości, tylko w dziedzinie: to narzędzie dla agentów, które optymalizują algorytmikę aplikacji CPU (JS, Python, Java itd.).

Powiązanie z `morluto/flameox` (ten sam autor, analizuje go ResFlameox): według ResFlameox flameox nigdzie nie odwołuje się do smokinggun (grep: 0 trafień). Jedynym wejściem „static candidates” w flameox jest SARIF (`inspect_performance_candidates`). Smokinggun potrafi emitować SARIF (`scan --format sarif`), więc jedyny możliwy styk to SARIF ze skanu, a to są kandydaci pętlowi z kodu CPU, bez wartości dla kerneli. Werdykt pozostaje bez zmian.

## Do bazy wiedzy

- **morluto/smokinggun (MIT, TS/Node, v5.0.0, ostatni commit na `main` 2026-08-29):** statyczny skaner wzorców złożoności w pętlach (tree-sitter, 13 języków, bez `.cu`/`.hip`) plus import-only porównanie hyperfine/pyperf/GoogleBench/criterion/JMH/pprof/Perfetto z gate'em eligible/blocked/inconclusive. **Nie stosuje się do optymalizacji GPU i inferencji:** nie bisektuje, nie analizuje kerneli ani faultów, nie szuka rozbieżności numerycznych. Jego gate jest słabszy od fabryki v1 (porównuje tylko mediana/IQR i node/platform/arch, a fabryka sha256 + ABBA CI). Nie adoptować. Źródło: 21k-smokinggun.md.
