---
typ: eksperyment
tags: [eksperymenty, rx-7900-xtx, flash-attention, kv, dlugi-kontekst, profil, wynik-negatywny]
aktualizacja: 2026-11-08
zrodlo: ~/qwen-opt/kvq-once/run-1107-2315/summary.txt, kperf.txt, lc.jsonl, sweep.txt, hg-parsed.txt; ~/qwen-opt/kvq-once/run2-1108-0054/summary.txt; ~/qwen-opt/kvq-once/NOTE.txt; gałąź kvq-once 1d0fa32bb (ONCE=1), 47b6be451 (ONCE=2)
status: aktualne
---
# kvq: KV raz na weryfikację MTP (`GGML_HIP_KVQ_ONCE`) i profil kroku przy długim kontekście (2026-11-07/08)

**Profil: przy 199k cały przyrost kroku względem 1.7k to FA (+10.6 ms, 30% czasu GPU). Wariant Sabera (blok = 2 grupy wierszy Q, V dekwantowane raz) jest bitowo identyczny, ale FA spada tylko o 6.1% przy 199k (kill: −10%) → KILL; e2e 199k +1.79%, 94k +0.89%. Przegląd podziałów: domyślne 2 bloki/SM najlepsze → KILL.**

Warunki: final mode (eco 2200, Qwen3.8-27B-Uncensored Q4_K_M, ctx 262 144, KV q4_0, MTP n4), każdy serwer przez `run-topka.sh uncensored`. N = gałąź kvq-once (topka-q63 + łatka, domyślnie wyłączona; N0 = ONCE=0, N1 = ONCE=1), P = produkcja `~/llama-topka`. Job `kvq-once.jobs` 2026-11-07 23:15 – 11-08 00:54.

**Poprawność:** `test-backend-ops` FA q4_0 381/381 przy ONCE 0 i 1; `fa_hash` (wyjście FA bit w bit) identyczny dla kv 4k/98k/196k × nb 1/3/5/8/10/16.

## ONCE=1: kernel (`test-backend-ops perf`, D 256, GQA 6, µs na wywołanie = na warstwę)

| kv, nb | baseline (N0) | teraz (N1) | % |
|---|---|---|---|
| 32k, nb5 | 128.5 | 122.3 | −4.8% |
| 98k, nb5 | 318.8 | 298.9 | −6.2% |
| 196k, nb5 | 616.9 | 572.1 | −7.3% |
| 196k, nb1 | 326.7 | 326.8 | 0% |

nb1 = 658 GB/s (poziom hipfire), nb5 tylko 355 GB/s: weryfikacja (2 kafle) jest ograniczona obliczeniami (dekwant + WMMA na kafel), nie pasmem; ONCE oszczędza tylko dekwant V.

## ONCE=1: e2e (ABBA N0 N1 N1 N0, T=0, 256 tok., rozrzut A/A < 0.1%)

| Pomiar | baseline | teraz | % |
|---|---|---|---|
| decode 1.7k | 124.82 t/s | 124.81 t/s | 0.0% |
| decode 94k | 120.97 t/s | 122.04 t/s | +0.89% |
| decode 199k | 94.12 t/s | 95.81 t/s | +1.79% |
| spec_sweep T=1 (P → N1, ABBA) | 118.2 t/s | 118.0 t/s | −0.1% (szum) |
| md5 T=0 1.7k / 94k / 199k | ebac2533 / 3f0651b0 / da05e1f8 | to samo | bitowo = |
| md5 greedy krótki (po spec_sweep) | c23506c7 (P) | c23506c7 | bitowo = |

md5 krótkiego greedy zależy od tego, czy cache promptu zna już prefiks szablonu: pierwsze żądanie świeżego serwera daje 09c9d3c1 (N0), to samo żądanie po spec_sweep c23506c7. Wartość 0221afd9 z [[2026-11-06-final-mode]] to inna konfiguracja.

## Profil kroku (rocprofv3, PM4 off, ms na krok weryfikacji)

| Kontekst | GPU zajęte | FA (kvq + combine) | udział FA | reszta | FA ONCE=1 | % |
|---|---|---|---|---|---|---|
| 1.7k | 27.0 | 0.66 | 2.4% | 26.3 | 0.69 | +4.5% |
| 94k | 32.0 | 5.70 | 17.8% | 26.3 | 5.40 | −5.3% |
| 199k | 37.6 | 11.32 | 30.1% | 26.3 | 10.63 | **−6.1% → KILL** |

- Reszta stała (26.3 ms), więc FA = 100% nachylenia 1.7k → 199k (+10.6 ms).
- 19.9 wywołań kvq na krok: 16 weryfikacji + ~4 draftu MTP; atencja draftu po pełnym kontekście ~1.3 ms na krok przy 199k.
- Ślad hosta (`LLAMA_HOSTGAP_TRACE=16`, PM4 on, P): ściana 26.97 → 37.85 ms, taśmy GPU 26.5 → 36.9 ms (1.7k → 199k); `graph→inputs` (budowa maski KQ) 35 → 355 µs (0.9% kroku, ponad próg 0.2 ms: poz. 9 z [[raport-66-synteza]] żyje, [[maska-kq-host-dlugi-ctx]]).

## Przegląd podziałów (poz. 3)

| Pokrętło (FA nb5, 32k–196k) | vs domyślne |
|---|---|
| `GGML_HIP_KVQ_BLOCKS_PER_SM=1` | +24…30% |
| `=3` | +5…28% |
| `=4` | +0…7% |
| `GGML_HIP_KVQ_MIN_SPLIT` 64/128/256 | 0% |

Domyślne 2 bloki/SM najlepsze → KILL, KLD zbędne.

## ONCE=2 (K też raz) — nie zmierzone

Wariant 47b6be451: każda fala pary dekwantuje połowę każdego bloku K i liczy KQ dla obu kafli (łańcuch WMMA `KQ_part[g]`), częściowe KQ drugiego kafla przez bufor VT 0 w LDS; bitowo z konstrukcji, 236 VGPR, 0 spilli, LDS 54.0 KB, zbudowany w `~/wt/kvq-once/build-hip`. Pierwszy job (`kvq-once2.jobs`, 00:54) zakleszczył się na etapie budowania: `cpuheavy` w jobie czekał na slot CPU zajęty przez `cpuheavy --quiet`, które czekały na quiet.lock trzymany przez kolejkę ([[lekcja-cpuheavy-w-jobie-kolejki]]); przerwany (BUILD FAILED, serwer odtworzony). Ponowienie `kvq-once2b.jobs` anulowane przed startem (koniec testów 2026-11-08, decyzja użytkownika). **Nie zmierzone.**

Okno uwagi draftu MTP: już istnieje (`--spec-mtp-window`, łatka 0046, [[latki-spekulacji]]) i przegrało przy 27k/62k (W=8192: akceptacja 3.31 → 2.78, 105 → 90 t/s). Ponowny pomiar przy 94k/199k (`mtpw.jobs`, xtxbench t1, W 4k/16k/64k) anulowany przed startem. **Nie zmierzone.**

## Stan / do wznowienia
- Gałąź `kvq-once` w `~/wt/kvq-once` (1d0fa32bb ONCE=1, 47b6be451 ONCE=2), build `build-hip` aktualny; łatki i skrypty w `qwen-opt/patches/kvq-once/` i `qwen-opt/kvq-once/` (KERNEL). Produkcja nietknięta (oba przełączniki domyślnie wyłączone, nic nie wdrożone).
- Wznowienie ONCE=2: `run-jobs.sh ~/qwen-opt/kvq-once/kvq-once2b.jobs` (~50 min: check + fa_hash, kperf ONCE 0/1/2, pmc odczyt DRAM, md5 + spec ABBA, long 199k ABBA). Bramka: FA ≥ −10% przy 199k i bitowo =. Cel dla nb5 przy 98k: ~172 µs (czas nb1).
- Wznowienie okna MTP: `run-jobs.sh ~/qwen-opt/kvq-once/mtpw.jobs`; kill, jeśli akceptacja spada > 1–2% (zysk maks. ~1.3 ms na krok przy 199k).
- Profil: kolejne cele z tego pomiaru to atencja draftu MTP (~1.3 ms przy 199k) i maska KQ na hoście (355 µs przy 199k).

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[kv-raz-na-weryfikacje]]
- [[fattn-kvq]]
- [[raport-66-synteza]]
- [[qwen3-8-27b]]
- [[lekcja-cpuheavy-w-jobie-kolejki]]
