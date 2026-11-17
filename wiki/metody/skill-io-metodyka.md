---
typ: metoda
tags: [metody, pomiar, szum, spekulacja, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — references/methodology.md:1-55, SKILL.md:78-101 (zasady 1–10), README.md:130-143
status: aktualne
---
# Metodyka pomiaru wg skill-io (methodology.md + zasady SKILL.md) a nasza praktyka

**„Większość wygranych i regresji w strojeniu inferencji to błędy pomiaru” (`methodology.md:3`). Stosujemy prawie całą tę metodykę; braki to bramka igieł i flaga zapętlenia w harnessie. Ich szum ±5–10% (laptopy) to nie nasz przypadek: na XTX w eco 2200 mamy 0,02–0,33% ([[xtxbench-szybki-ab]]).**

| reguła (źródło) | treść | u nas |
|---|---|---|
| liczenie tokenów (`:7`) | z usage serwera albo tokenizera, nie z kawałków strumienia; przy MTP kawałek = kilka tokenów | tak: `spec_sweep` i harnessy biorą `timings` serwera ([[spec-sweep]]) |
| rozmiar promptu (`:8`) | tokenizerem; „32K” z losowych słów to było 58K | tak: xtxbench tnie korpus tokenizerem |
| prompt przed zegarem, unikalny (`:9`) | losowy prefiks, by nie trafić w cache | tak: `cache_prompt=false`, xtxbench `erase` |
| dekod t/s (`:10`) | (tokeny − 1) ÷ czas od pierwszego tokena | liczymy z czasu serwera (`predicted_ms`) |
| prefill (`:11`) | prompt ÷ TTFT na zimno; cache-hit raportować osobno | tak; fill 255k osobno od `pp` |
| cN (`:12`) | tokeny ÷ ściana od pierwszego startu do ostatniego końca | nie dotyczy produkcji (1 slot) |
| szum (`:16-21`) | ≥ 6 próbek, mediana, stały zestaw promptów; losowe prompty zmieniały akceptację 2,4 → 3,7 | tak: 6 promptów × seedy, mediana ([[pomiar-abba]]) |
| przeplot (`:22`) | kontrola, kandydat, kontrola; dryf 53,8 → 49,5 w godzinę | tak: A B B A, A/A kalibracja szumu |
| porównanie silników (`:23`) | bootstrap 95% CI mediana(B)/mediana(A) > 1 | **brak** (mamy Wilson tylko dla jakości) |
| odrzucać zimne pierwsze runy (`:24`) | JIT/cache (36 vs 90 t/s) | tak: rozgrzewka w harnessach |
| spekulacja (`:29-33`) | t/s = a ÷ czas kroku; wyższa akceptacja może być wolniejsza (3,26 vs 2,85, −11…14%); rozjazd greedy przy innych M to numeryka, nie błąd | tak: raportujemy tok/krok i ms/krok; [[2026-11-14-k001-wyciek-stanu-restore]] |
| długi kontekst (`:37-38`) | osobny run; **3 igły** na różnych głębokościach, odpowiedź dokładna | **częściowo**: fill 255k z md5, bez igieł (K-109) |
| zdrowie wyjścia (`:42`) | flagować pętle, błędy, bezczynne GPU; „rekord 117 t/s” był pętlą listy | **częściowo**: pętlę wykryliśmy ręcznie (MMLU-Pro 32 768 tok.) |
| pamięć (`:46-48`) | na pamięci zunifikowanej `drm-resident-*` + anon | XTX dyskretny: `mem_info_vram_used`; fdinfo w K-011 |
| profilowanie (`:52-55`) | graf wyłączony do rozbicia na kernele; czytać ISA | tak: rocprofv3 przy PM4=0, `isa.sh` |

**Zasady twarde SKILL.md** (`:78-101`):
1. Jedna zmiana na eksperyment.
2. Przeplot kontroli i przyjęcie tylko, gdy kandydat bije obie sąsiednie kontrole, a nic nie traci > 3%.
3. Stałe środowisko.
4. Jedno zadanie GPU naraz.
5. Watchdog pamięci.
6. Bramki stabilności: igły 50% i 100% kontekstu, soak, greedy-ekwiwalencja.
7. Nie zabijać serwera w trakcie batcha: „wymuszony stop w prefillu wywołał fault sterownika”.
8. Sprawdzać wyjście, nie tylko prędkość.
9. Logować porażki.
10. Sekrety.

Wszystkie mamy (kolejka, `gpu-guard`, jeden SIGTERM, [[lekcja-pm4-zamienia-fault-w-reset]]) poza bramką igieł z punktu 6.

## Powiązane
- [[skill-io-przeglad]]
- [[pomiar-abba]]
- [[xtxbench-szybki-ab]]
- [[spec-sweep]]
