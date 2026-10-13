# Strata (Niko1221/Strata): jak autor myśli i iteruje, i co z tego przenieść na Qwen3.8-27B na jednym 7900 XTX

Stan: klon z pełną historią w `~/research/Strata`, HEAD `a0116b27` (2026-10-12, = tag `v0.1.43.1`), plus otwarte PR-y z 2026-10-12/13 (#2020, #2226, #2231). Repo ma 1892 commity w 19 dni i 49 tagów. Niko1221 napisał 1150 commitów, reszta to PR-y społeczności, które autor przenosi ręcznie. Nic nie było budowane ani uruchamiane na GPU. Ścieżki `plik:linia` są względem korzenia repo, `#N` to https://github.com/Niko1221/Strata/issues/N lub /pull/N. Liczby z naszego setupu pochodzą z `~/qwen-opt/NOTES.md` i `~/KERNEL/qwen-opt/research/v2/roadmap.md`. Oszacowania oznaczam [INFERENCE].

Szczegóły (z cytatami) są w raportach cząstkowych:
- `local://strata-timeline.md`: wersja po wersji;
- `local://strata-kernels.md`: kernele decode/verify i HIP;
- `local://strata-spec-host.md`: MTP, verify, host, cache;
- `local://strata-prefill.md`: prefill, attention, KV;
- `local://strata-method.md`: metodologia i ok. 50 wyników negatywnych;
- `local://strata-issues.md`: issues i PR-y, ok. 75 wątków.

**Co nowego od poprzednich notatek** (`strata.md`, stan 2026-10-06, wersja 0.1.40):
- 0.1.40.2–0.1.43.1:
  - interleaved q8_1 MMVQ z tablicami wierszy per architektura;
  - wiersze hipBLASLt dla małych T na gfx1100;
  - route tail skip i mierzony udział PCIe (pierwsze domyślne zmiany, które zmieniają bity);
  - cięcie węzłów grafu na gfx12 (+1.6–2%);
  - wycofanie domyślnego `STRATA_ADAPT_OVERLAP` (−21% u użytkowników; przyczyna: affinity wątku callbacków);
  - rejection sampling, Gumbel i re-probe w DraftPolicy;
  - clamp q8_1 (#606).
- Otwarte PR-y:
  - **#2231**: bitowo identyczne poprawki decode na RX 7900 XTX, **+11.7% chat / +14.3% agent decode, KL 0.0000**;
  - **#2226**: persistent kernel z grid barrier (gfx1030);
  - **#2020**: F16 WMMA zamiast int8 dla K-quantów w prefill (gfx11).

---

## 1. Czym jest Strata: architektura i komponenty

- **Silnik pod jeden model**: Qwen3.8-Flash-Next, 125B MoE, ok. 6B aktywnych parametrów.
  - Ma 48 warstw: 36 Gated DeltaNet i 12 Qwen Sparse Attention (2 głowy KV, top-k ≈2048 komórek na zapytanie).
  - W każdej warstwie jest 512 ekspertów, z których wybieranych jest top-10.
  - Ma też tablicę n-gram (PLE) o rozmiarze 28.8 GB i wbudowaną głowicę MTP (paper `docs/paper/Strata-Paper.pdf` §2, Tabela 1).
  - Kod to ok. 200k linii C++/CUDA/HIP (+SYCL), serwer w Pythonie z API OpenAI/Anthropic i instalator „one-click”.
- **Trzy poziomy pamięci** (paper §3.1, Fig. 1):
  - VRAM: część gęsta (ok. 3.5 GB czytane na token), KV, stan rekurencyjny, głowica MTP i adaptacyjny cache ekspertów, który wypełnia resztę VRAM.
  - Pinned RAM: wszystkie eksperci; CPU liczy „chybione” eksperty w miejscu (AVX-512/AVX2).
  - SSD: tablica PLE, czytane jest 16 wierszy na token, krok wcześniej.
- **Jedna warstwa = trzech wykonawców naraz** (paper §3.2):
  - GPU liczy mixer i router, po czym „dzwoni doorbellem” (volatile store do mapowanej pamięci).
  - CPU kręci się na tym słowie, dzieli eksperty na trzy grupy: trafione w VRAM, kopiowane DMA przez PCIe i liczone na CPU.
  - Cały 48-warstwowy przebieg to **jeden przechwycony graf na każdy rozmiar okna T** (`src/core/verify.cpp:1846-1971`, `run` przy :2147).
- **Spekulacja**: własna warstwa MTP modelu.
  - Okno verify ma do 4 tokenów, a draft ma zredukowany słownik (40 525 → 106 299 id).
  - Wynik jest bitowo identyczny z greedy (paper §3.3).
  - Rollback GDN odbywa się przez **replay**, bez snapshotów (`src/kernels/cuda/verify_kernels.cu:396-463`).
- **Backend HIP**:
  - te same pliki `.cu` przez `include/strata/hip_compat/` (wave32) i osobny shim wave64 dla gfx906;
  - `sudot4`/`sdot4` jako dp4a, `v_perm_b32`, SWAR, DPP;
  - tablice hipBLASLt per (arch, wersja biblioteki);
  - WMMA w prompt attention i GEMM prefill.
- **Narzędzia wbudowane w silnik**:
  - `STRATA_DECODE_TIMING`, `STRATA_VERIFY_PROFILE` (znaczniki czasu GPU w grafie), `STRATA_VERIFY_NODES`, `STRATA_DUMMY_NODES` (koszt pustego węzła);
  - ok. 100 testów `*_parity` (memcmp), `tools/ab_engine.py`, `tools/strata_bench.py`, `tools/calibrate.py`;
  - `STRATA_LOGPOS` (teacher-forced logprob do KL).

## 2. Ewolucja wersja po wersji (fazy i punkty zwrotne)

Pełna tabela 49 tagów: `local://strata-timeline.md` §2. Tutaj fazy, z liczbami.

| Faza | Tagi (daty) | Co się działo | Zmierzone efekty / powód |
|---|---|---|---|
| 0. Prywatna prehistoria | przed `01529aaa` | Root commit to już 219 plików / 50k linii, z paperem. W komentarzach widać ok. 330 numerowanych „rund” i ledger decyzji L1–L123 (`Memory/LEDGER.md`, niepubliczny; np. `src/kernels/cuda/gr.cu:173-215`, `router_top10.cu:20-34`) | Kolejność: oracle w Pythonie (`ref/load.py`), potem kernel „najprostszy poprawny” (`s2_gemv_q8.cu:1-15`), potem szybki |
| A. Wydanie i stabilizacja | 0.1.0–0.1.12 (09-24..27) | Conversation cache (checkpoint = sam stan rekurencyjny, ok. 118 MB), KV streaming ≥64K, prompt lookup „tylko tam, gdzie zmierzono zysk” | Follow-up 12.9 s → 0.3 s (0.1.3); 262K decode 50.9 → 62.6 (0.1.5); kod +6–11% z lookup (0.1.7, `bbe8944e`) |
| B. Pierwsze uderzenie w prefill | 0.1.13–0.1.15 | Chunki do 8192, MMQ dla ekspertów, streaming ekspertów następnej warstwy | 32K prompt 572 → 1290 tok/s (5070) |
| C. Open source i społeczność | 0.1.16–0.1.20 | MIT, `--calibrate` (ustawienie zostaje tylko przy >3% zysku) | — |
| D. Literowany plan perf (C-/D-/E-/F-) i HIP | 0.1.21–0.1.26 | QSA prompt attention na tensor cores (D-1), **per-token kernele batchowane na całe okno** (`4a50d4ce`), port HIP (#121, 0.1.25), batched MTP prompt pass (E-9, `a402eefd`) | 81 → 89 / 105 → 118 tok/s (bitowo); draft prompt pass 0.9 s → 0.07 s na 32K; hipBLASLt na 7900 XTX: prompt +42–59% |
| E. Szerokość sprzętu i formatów | 0.1.27–0.1.35 | CJK draft vocab, SWAR/`v_perm` na HIP (`600d7307`), router HIP bez części szeregowych (`a2be1670`), **commit bez sync** (`a1e4fb4c`) | R9700 decode +15% i +12%; +5.6% decode z usunięcia ok. 0.45 ms `cudaStreamSynchronize` na rundę |
| F. Drugie uderzenie: fused int8 prefill, mniej launchy w decode | 0.1.36–0.1.39 | Fused int8 tensor-core experts (pierwsza domyślna zmiana bitów, uzasadniona KL), zero-doorbell verify graph (#646, `a36be1db`) | Prompt +21–22%; decode +6% (10 par) |
| G. Merge forka i „opt-in wszystko” | 0.1.40–0.1.40.4 | Fuzje z forka Eddoursula (F4 interleaved q8_1 `ffac97f7`, F7 self-commit `352cad8f`), pakiet #783, tabele `arch_defaults` (domyślnie tylko przełączniki bitowo dokładne, `9708b549`), przepisanie historii 10-06 | 3060 +4.2% decode (12/12 par); Strix Halo +4% decode |
| H. Domyślne zmiany bitów pod kontrolą KL i wycofania | 0.1.41–0.1.43.1 | Route tail skip (KL 0.003–0.006 przy podłodze 0.0007), mierzony udział PCIe `L/(L+1.85R)`, cięcie węzłów na gfx12 (`7fc02cb5`, `a9917a55`), wycofanie `ADAPT_OVERLAP` (`661ff293`) | +13–16% (tail skip), +30% (3060, PCIe share), +1.6–2.0% (węzły gfx12); ADAPT_OVERLAP −21% u użytkowników, wycofany w <1 dzień |
| Po tagach (otwarte PR-y) | #2231, #2226, #2020 | Bitowe mikro-poprawki gfx1100; persistent kernel; F16 WMMA dla K-quantów | +11.7% decode na 7900 XTX; −2.8…−4.2% ms/okno na gfx1030; +15.6% prefill 32K na gfx1151 |

Wnioski z przebiegu historii:
- **Najpierw system, potem kernele.** Wielkie skoki (2x prefill, KV streaming, adaptacyjny cache, MTP) dotyczą rozmieszczenia bajtów. Kernele dają +5–15% na krok. Na końcu autor schodzi do pojedynczych węzłów grafu (+1.6–2%), a społeczność do µs na kernel (#2231).
- **Kolejność regresji i cofnięć jest jawna.** W 1892 commitach są tylko 4 reverty. Nieudane pomysły zostają jako opt-in z liczbami w docs (np. `STRATA_GDN_CHUNKED`, Foresight, `GR_DOWN_MAX4` `46d01366`).
- **Punkty zwrotne w polityce:**
  - 0.1.36: pierwsza domyślna zmiana bitów, za KL vs FP16;
  - 0.1.40: domyślnie per-arch tylko przełączniki bitowe;
  - 0.1.42: zmiana jakości decode za teacher-forced KL vs podłoga szumu;
  - 0.1.43.1: „bezpieczny default to taki, który nie może kosztować prędkości” (#2010).

## 3. Metodologia autora: jak mierzy, stawia hipotezy, decyduje, porzuca

1. **Spis bajtów, potem rozkład czasu.**
   - Projekt wynika z policzenia, ile bajtów czyta się na token, dla każdego tensora (paper Tabela 1). Potem przychodzi rozkład jednej rundy verify: Q2_0 34.3 ms = GPU 14.6 + CPU experts 13.4 + draft 2.0 + inne 4.3, 3.23 tok/rundę (paper Tabela 5).
   - Z tego wynika wniosek „silnik jest zbalansowany, przyspieszenie jednej strony da maksymalnie ok. 1/3”. Późniejsze dźwignie po stronie CPU go potwierdziły: tail skip daje +13–16% przy hit rate 75–90% i 0% przy 99.7% (`docs/DETAILS.md:1651-1661`).
2. **Model kosztu z jawną kalibracją.**
   - Udział PCIe `L/(L+1.85R)`: stała dopasowana na 3 maszynach, „ląduje w kroku od optimum, nie na nim” (`DETAILS.md:1671-1676`).
   - DraftPolicy uczy się online kosztu okna per T zamiast używać zgadniętego kosztu (`include/strata/spec/draft_policy.hpp`). Wcześniejszy, parametryczny `Controller` został porzucony, choć skompilowany i przetestowany (`local://strata-spec-host.md` §2).
3. **Szybkość i numeryka to osobne bramki.**
   - Zmiana „perf” musi dawać te same bity i mieć wyłącznik `STRATA_X=0`, który przywraca starą ścieżkę bajt w bajt.
   - Zmiana numeryki jest opt-in, dopóki nie przejdzie teacher-forced KL na realnych oknach verify z draftami MTP (28 promptów, 6 języków, ok. 6000 tokenów) obok dwóch odniesień:
     - podłogi (ten sam silnik uruchomiony dwa razy, 0.0006–0.0007);
     - skali (Q2_0 vs IQ3_XXS = 0.10) (`DETAILS.md:1631-1649`).
   - Dla szybkiego kernela, który zmienia numerykę: jego KL vs FP16 musi być ≤ KL obecnego (PF_FUSED został opt-in przy 0.00388 vs 0.00340 mimo +15–19%).
4. **A/B = przeplatane pary całych silników.**
   - Jeden binarny plik, ramiona różnią się tylko env. Świeży proces na ramię, rozgrzewka, kolejność naprzemienna, mediany i licznik „k/n par szybszych” (`tools/ab_engine.py`; `DETAILS.md:1693-1695`).
   - Nigdy nie porównuje się do starej liczby: w #1373 binarka 0.1.39 skakała w ciągu jednego wieczoru 135 → 75–127 tok/s, a „−20%” okazało się +12.9%.
   - **Ten sam prompt w obu ramionach pary.** Unikalne znaczniki w promptach zmieniały tekst, a z nim akceptację MTP, co dało fałszywe +2.8% (#832). Kontrola pozytywna pokazała rozdzielczość harnessu ok. 2–3%.
5. **Próg decyzji ≥3%, liczony na najgorszym kształcie.**
   - Tabela wierszy MMVQ_IL: komórka jest niezerowa tylko wtedy, gdy najgorszy kształt klasy zyskuje ≥3%, a przy dwóch kartach musi zyskać ta gorsza (`docs/MMVQ_IL_TABLE.md:13,31-32`).
   - `calibrate.py MIN_GAIN = 0.03`, margines DraftPolicy 0.03.
6. **Mikrobenchmark nigdy sam nie wybiera konfiguracji.**
   - „Microkernel speedups alone were not sufficient” (`docs/AMD_HIP_PERFORMANCE.md:144-145`).
   - PR #2231: bench IL przy back-to-back launchach zawyżał zysk 2/4 wierszy o 20–60%, więc tabelę gfx1100 wzięto z czasów rocprofv3 **wewnątrz** dekodowania 4K.
   - Mikrobenche rotują kopie wag, żeby nie trafiać w L2 (`src/kernels/mmvq_il_parity.cpp:11`).
   - Zła komórka tabeli kosztowała −15% decode na 4090 (#1842).
7. **Mierz okazję, zanim zbudujesz.**
   - `STRATA_LOOKAHEAD_STATS` i offline replay polityki cache powstały przed prefetcherem.
   - `STRATA_MTP_TOP2` pokazało, że drugi kandydat draftu był celem w 0 z 14 odrzuceń, więc drzewa draftów nie mają sensu (#2227).
   - Foresight zbudowano mimo wszystko i wyszedł ujemny (0.91–1.00x).
8. **Wyniki zależne od platformy trzymane w tabelach per-arch.**
   - Ten sam przełącznik daje +6% na A4000 i −21% na laptopie 5090 (ADAPT_OVERLAP).
   - Stream fork daje +45% po wyłączeniu na R9700, ale −5…13% po wyłączeniu na 2× 6900 XT.
   - „Decode-half” ze Strix Halo dał −4% na dyskretnym gfx1201 (#1478).
   - Defaulty idą do `arch_defaults.cpp` tylko po pomiarze na danej karcie. Wynik jednego reportera nie zmienia defaultu na sprzęcie, którego autor nie ma (#1386).
9. **Root-cause zamiast obchodzenia.**
   - Brak fence po store doorbella kosztował ok. 10 ms/token. Host „naprawiał” to wywołaniem drivera w każdej iteracji: „a 10-22 µs driver call per iteration is a very expensive substitute for one fence instruction” (`src/kernels/cuda/elementwise.cu:186-215`).
   - Wątek callbacków CUDA dziedziczył affinity jednego rdzenia, przez co callback trwał ok. 1000 µs zamiast 4 µs (#1964, `0e20d9ae`).
   - W kampanii A770 każdy krok hipotezy podaje dowód i to, co by ją obaliło (`docs/A770_SPEED_SPEC.md:535-761`).
10. **Ponowne testy, gdy zmienia się reżim.** „The old result is not wrong; it is about a different kernel” (`gr.cu:173-215`): 4 akumulatory nic nie dawały, póki limitem był FP64, a po przejściu na FP32 zaczęło liczyć się occupancy.
11. **Styl commitów jako protokół.** Kolejność: mechanizm → twierdzenie o równoważności („bitwise the multi-column kernel’s”) → wyłącznik → test parity → liczby (sprzęt, model, liczba par) → czego nie ruszono → autorstwo (`ffac97f7`, `b08cf3e1`). Release notes mają sekcje: Faster / Fixes / New opt-ins (także z ujemnymi liczbami) / Answers can differ (tabela KL) / Not fixed.
12. **Wzorzec pracy [INFERENCE].** Workflow wielu agentów AI: równoległe „streams”, blokada GPU w `bench_vs_llama.py`, ledger, numerowane rundy, przepisanie historii usuwające trailery Claude (#1276, P#1892). Tempo 84–189 commitów dziennie jest możliwe dzięki bramkom bitowym i wyłącznikom: każda zmiana jest tania do odwrócenia i bisekcji.

## 4. Katalog technik (mechanizm → zmierzony zysk)

### 4a. Decode / verify (GPU)
| Technika | Mechanizm | Zysk (sprzęt) | Źródło |
|---|---|---|---|
| Graf per rozmiar okna T + wejścia z mapowanej pamięci | `exec_[T]`, tokeny/pozycje/n_keep zapisywane przez host do pinned mapped, kopiowane przez pierwsze węzły grafu (`copy_i32_from_mapped`) → zero aktualizacji grafu i zero memcpy+sync na krok | baza architektury | `verify.cpp:606,887-896,1990,2172` |
| Per-token kernele raz na okno | router, normy, RoPE, casty, combine dla T tokenów w jednym launchu; szablony exact-T 1..8 | 81→89 / 105→118 tok/s; okno 15.10→13.07 ms (−13.4%, #783) | `4a50d4ce`, `ae3b249f` |
| Async commit, bez host sync | commit na tym samym streamie, drafter czyta tylko końcowe wiersze; event tylko gdy sesję dotyka ktoś inny | +5.6% (128.6→135.8, NVIDIA) | `a1e4fb4c`, `verify.cpp:2494-2522` |
| **GDN rollback przez replay** | okno czyta stan read-only (`__ldg`), zapisuje tylko per-token q/k/v/g/β; graf commit odtwarza n_keep tokenów kernelem tylko-stan (192×128); T=1 commituje sam siebie | commit 44→39 µs (1 wiersz), 61→46 µs (6 wierszy) na warstwę, gfx1151, h_v 48 = nasza geometria | `verify_kernels.cu:169-219,396-463`, `352cad8f` |
| Siatka GDN jako dźwignia latencji | 4 bloki × 32 kolumny na głowę (192 bloki) zamiast 1 bloku na głowę; norma wyjścia jako osobny kernel | okno 30.1→26.7 µs; „24 bloki = 0.28 ms/warstwę dla 12.6 MB, co karta 643 GB/s robi w 0.020 ms” | `e3c3d6ba`, `gdn.cu:17-31` |
| MMVQ load/apply | dekodowanie bloku wag raz na (wiersz, blok), apply na każdą kolumnę, bitowo = 1-kol | baza multi-col | `native_mmvq.cu:818-1020` |
| Interleaved q8_1 (2–4 kol) | jeden `int4` load = ten sam int wszystkich kolumn; warp ma całe wiersze, bez LDS i `__syncthreads`; wiersze/warp z tabeli per (typ, ncols, klasa wierszy) | +4.2% (3060), +1.3–2.2% (5070); gfx1100: wygrywa tylko w klasach ≥4096 wierszy, wariant „plain” nigdy | `ffac97f7`, `q8_1_il.cuh`, PR #2231 |
| **Pair launch** (konkatenacja siatki) | bloki `[0,n1)` liczą macierz 1, dalsze macierz 2, ten sam kod wątku → **zero dodatkowych rejestrów**; też gate GEMV jako dodatkowy blok launchu routera; KV append K i V w 1 siatce | gfx1151 −1.9% czasu okna | `native_mmvq.cu:2406-2441`, `b08cf3e1` |
| Producent pisze q8_1 (i kopię IL) konsumenta | norma GDN kwantyzuje wynik do bloków out-proj; HC-up pisze obraz q8_1 | harness −11…17%, silnik ok. 0 (gfx1151); część +11.7% (#2231) | `22abb92d`, `a9917a55` |
| Wait złożony w następującą kopię, norma z rejestrów | −2 węzły/warstwę; „pusty węzeł” zmierzony przez `STRATA_DUMMY_NODES` = 2.4 µs (gfx1201) / 2.7 µs (gfx1100) | +1.6–2.0% decode (R9700) | `7fc02cb5`, `verify.cpp:225-228,1075` |
| **Latencja małych kerneli (gfx1100)** | DPP `row_xmask`/`permlanex16` zamiast `ds_bpermute` (hipcc w ROCm 10 nie robi tego sam), brak bezczynnych grup wierszy, multi-block argmax z merge w ostatnim bloku, 16 loadów w locie zamiast łańcucha | GDN out-norm 9.3→2.0 µs/warstwę; argmax 12→5.6 µs; skan 31→9.4 µs; MTP row select 12→2.2 µs; razem **+11.7% decode, KL 0** (7900 XTX) | PR #2231, `3e4aa1d6` |
| TSUM | P sum na końcu warpa jednym transponowanym butterfly: P−1+(5−log2 P) ruchów zamiast 5P | 54.21→52.10 ms/okno (gfx1151, zastosowane szeroko) | `2a1c54e7`, `s26_tsum.cuh` |
| Router bez części szeregowych | drzewo zamiast 512 szeregowych dodawań FP64, z dowodem bitowości (fallback, gdy przedział `tree*(1±2^-40)` nie mapuje na jeden float) | 39→9–12 µs/wywołanie; +12% R9700 (u użytkownika +1–4% przy rozrzucie 12–20%) | `a2be1670`, #432 |
| SWAR/`v_perm_b32` | `__byte_perm` w HIP indeksował tablicę w pamięci prywatnej (scratch) | +15% decode R9700 | `600d7307` |
| Persistent kernel z grid barrier | 3 zależne mini-launche → 1 kernel, 80 bloków, 2 bariery; walidacja przy starcie z timeoutem 50 ms (API occupancy w HIP kłamało) | 55.1→38.9 µs; −2.8…−4.2% ms/okno (gfx1030) | PR #2226 |
| Planar repack Q6_K/Q8_0 | wyrównane dword loady non-temporal | głowa 1 kol −5%, **4 kol 0%**; Q8 6144→2560 +2–4% w izolacji, −3% w silniku | `5cf0079b`, `96f4065a` |
| Clamp q8_1 | d i sum klamrowane do ±65504 (bitowo dla skończonych bloków) | brak NaN → „jeden powtarzany token” (= llama.cpp#23606) | `7a0e3023`, `include/strata/kernels/q8_1_finite.hpp` |

### 4b. Spekulacja i host
| Technika | Zysk / wynik | Źródło |
|---|---|---|
| MTP draft head na zredukowanym słowniku, z pokryciem językowym | CJK +15–38%, FR akceptacja 0.505→0.597; pełny słownik +4 pp akceptacji, ale −2.1% prędkości (4090D) | `e227683e`, #597, #2227 |
| `--mtp-q4`: Q4_0 kopie projekcji draftu i podzbioru głowy | draft ms/okno 2.55→2.23 (−13%), tokeny/krok 2.64→2.63 | `e35a061f` |
| Front warstwy draftu raz; catch-up tylko do zaakceptowanego wiersza | mniej pracy draftu (brak izolowanej liczby) | `ca833116`, `3fd0460b` |
| `--mtp-window` (atencja MTP tylko na ostatnich N komórkach) | 8192: 64K +3.5%, 32K −0.4% (gfx1151); domyślnie 32768 | `docs/STRIX_HALO.md:126-127`, `mtp.cpp:329-360` |
| Lookup/suffix drafting zamiast MTP **tylko gdy 1. token = draft MTP 0** i polityka E[tok]/koszt(T) z mierzonym kosztem | kod +6–11%, reszta bez zmian; „zawsze dłuższy” −2–8% | `bbe8944e`, `draft_policy.hpp:1-14`, `48d2e6ca` |
| Batched MTP prompt pass | 0.9 s→0.07 s na 32K | `a402eefd` |
| Spin na mapowanej pamięci (volatile + `__threadfence_system`, na HIP fence także *po* store) | brak fence: ok. 10 ms/token; polling `cudaStreamQuery` −3% → koniec okna zostaje blokującym sync | `elementwise.cu:186-215`, `5865998a` |
| `hipStreamWriteValue32` zamiast host function | 6.7 µs vs 15 µs (gfx1100) | PR #2231 |
| Affinity: pin wątku hosta, reszta wątków poza jego rdzeniem, rozgrzanie wątku callbacków przed pinem | +10.5% (2×3080, Xeon); 142.8→207.8 (5090) | `91f1e85d`, `0e20d9ae` |
| Bez forków streamów w grafie HIP; liczba utworzonych streamów ma znaczenie | fork off: R9700 43.4→62.9; 2×7900 XTX +12.7%; jeden nieużywany stream ±16–35% prefill | #816, #1386, #2055, P#1240 |
| Checkpointy rozmowy = stan rekurencyjny (KV pozycyjne), na granicach tur i co 16K, przypięty root system-prompt, async copy-out | follow-up 48.6 s→0.35–0.53 s; −370 ms bezczynności GPU na checkpoint | `42810ee8`, #203, `docs/RESEARCH_RUNS.md` |

### 4c. Prefill
| Technika | Zysk | Źródło |
|---|---|---|
| Tabele hipBLASLt per (arch, wersja), bramka poprawności, licznik fallbacków | 7900 XTX: 1.7K +52%, 6.5K +78% (ROCm 10.0); 131K +82%; ukryte 642/642 fallbacków jednego kształtu kosztowały 32% | `7984688e`, `a45783c7`, #745 |
| WMMA prompt attention (int8/q4 kody dokładne w FP16, skala FP32 na lane; układ fragmentów RDNA3 ≠ RDNA4) | kernel 4.05×; prefill +17.9% przy 32K, +22.8% przy 128K (7900 XTX), bo attention było 25.6–26.9% czasu GPU | #786 |
| Globalne loady kafla przed obliczeniami (uwaga na VGPR) | −9.7% czasu kernela; głębszy prefetch (232→248 VGPR) oddał wszystko | #2017 |
| F16 WMMA z dekwantyzacją w LDS zamiast int8 MMQ (K-quanty) | warstwa Q4_K 85.3→53.5 ms (−37%), +15.6% przy 32K (gfx1151; KL 0.0068 vs 0.0031) | #2020 |
| Padding stride’ów będących wielokrotnością 4 KB | GEMM K=6144 19.1→35.0 TFLOPS; +3–7% (gfx1151) | `local://strata-prefill.md` T6 |
| GDN prefill: rekurencja szeregowa w rejestrach, 192 bloki, conv+L2 złączone; **chunked WY na gfx1100 −39%** | 25.4→20.5 ms na warstwę 16K (naprawa klifu VGPR) | #888, #413 |

## 5. Transfer na nasz setup (gęsty 27B hybrid, całość na jednym 7900 XTX)

**Arytmetyka bazowa:**
- Krok 35.7 ms przy 88.5 t/s daje **3.16 tok/krok**.
- **Każda zaoszczędzona 1 ms/krok to ≈ +2.9% t/s** (3.16/34.7 ms = 91.1 t/s).
- Verify trwa ok. 31 ms: matvec ok. 25 ms, przerwy między kernelami ok. 3.2 ms (≈970 kerneli × 3.3 µs), reszta małych opów ok. 2–3 ms [INFERENCE: z roadmap §0 po A3–A6].
- Poza verify zostaje ok. 4.7 ms/krok (draft MTP + host).

**Dlaczego większość Straty nie przenosi się wprost:**
- Jej dźwignie systemowe (cache ekspertów, CPU experts, PCIe share, tail skip, KV streaming, layer split, batch-MTP) wynikają z MoE + offload. U nas wszystko siedzi w VRAM i jest czytane w całości.
- Jej attention jest rzadkie (≤2048 komórek), więc jej „płaski decode z kontekstem” nas nie dotyczy.
- Przenosi się:
  - mechanika okna verify i hosta;
  - latencja małych kerneli na RDNA;
  - rollback GDN, bo **geometria GDN jest identyczna jak nasza: h_v 48, S 128** (`local://strata-kernels.md` nagłówek);
  - koszt draftu MTP;
  - prefill WMMA;
  - metodologia.

**Fakt z naszych plików, którego wcześniej nie liczyliśmy.** Warstwa MTP w UD-Q4_K_XL jest **cała w Q6_K**: q 49.2, o 24.6, gate/up/down 3×69.7, eh_proj 41.0, k/v Q8_0 2×5.3 MiB, razem ≈ 335 MiB.
- Do tego dochodzi draft head 64k wierszy z Q6_K ≈ 256 MiB (995 MiB × 64k/248k).
- Jeden przebieg draftu czyta więc ≈ 590 MiB, a **4 przebiegi ≈ 2.36 GB/krok ≈ 3.4 ms przy 700 GB/s**. Zgadza się to z pomiarem ok. 1.19 ms na przebieg draftu przed złączeniem w jeden graf (`NOTES.md:253`): 590 MiB/1.19 ms ≈ 520 GB/s, czyli draft jest ograniczony odczytem wag MTP.
- W Uncensored Q4_K_M warstwa ma ≈ 251 MiB, czyli ≈ 507 MiB/przebieg i ≈ 2.9 ms/krok.
- Odczyt: gguf-py na obu plikach.

### Ranking (wartość/wysiłek)

| # | Pomysł (źródło w Stracie) | Dlaczego pasuje / nie pasuje | Oczekiwany zysk (arytmetyka) | Wysiłek | Ryzyko | Gdzie w naszym forku | Styk z K1–K5 |
|---|---|---|---|---|---|---|---|
| **1** | **Draft MTP w 4 bitach** (`--mtp-q4`, `e35a061f`: draft −13%, tok/krok 2.64→2.63) | Draft tylko proponuje; verify jest bezstratny, więc wyjście się nie zmienia, ruszyć może się jedynie akceptacja. Nasza warstwa MTP i głowica 64k to Q6_K (6.56 bpw) | Requant Q6_K → Q4_K (4.5 bpw): 590 → ≈405 MiB/przebieg, −740 MB/krok ≈ **−1.0 ms → +3%** (UD). Sama głowica 64k: −0.46 ms → +1.3%. Uncensored: ok. −0.6 ms. Zysk zależy od tego, czy akceptacja zostanie | niski–średni: requant przy ładowaniu (deq → `ggml_quantize_chunk`), zamiana tensorów blk.64 + kopii 64k wierszy | niski; zmierzyć tok/krok na `spec_sweep` | ładowanie modelu (llama-model.cpp, tensory `blk.64.*` / nextn), kod `--spec-draft-vocab` | Łączy się z self-distillation: najpierw destylować, potem kwantyzować. Też VRAM −0.2 GB |
| **2** | **Audyt latencji małych kerneli à la PR #2231** (DPP, multi-block argmax/select, brak bezczynnych grup wierszy, 16 loadów w locie) | Ta sama karta i ten sam ROCm; nasza reszta małych opów to ok. 2–3 ms/verify plus małe opy w grafie draftu (104 kernele) | Odzysk 30–50% czasu małych opów: **−0.6…1.2 ms → +1.7–3.5%**, bitowo (#2231 dał +11.7% na silniku MoE z większą liczbą małych opów) | niski na kernel; rocprofv3: kernele >5 µs na <1 MB danych | niski; DPP może przez FMA-contraction zmienić bity (#2231 `add_nc`), więc pilnować `fp contract(off)` | `norm.cu` (rms_norm fused), `argmax.cu`, norma wyjścia/gating GDN, `ssm-conv.cu`, `getrows.cu`, `unary.cu` | **K2** (rozszerza „fusion” o „latencję”) |
| **3** | **Ścieżka hosta jak w Stracie**: wejścia grafu z pinned mapped memory czytane przez pierwszy kernel, brak syncu między verify → draft, `hipStreamWriteValue32` zamiast host fn, pin wątku hosta | Roadmap A10: `set_tensor` = H2D + sync na każde wejście (≈1.15 ms/krok, ggml-cuda.cu:783-789); ok. 2 ms przerw między grafami | **−0.5…1.0 ms → +1.5–3%** (Strata: +5.6% z usunięcia 0.45 ms syncu) | średni | niski | `ggml-cuda.cu` set_tensor(_async), `llama-graph`/`llama-context` set_input, sekwencja server spec | **K3** wprost |
| **4** | **Pair launch** dla macierzy o wspólnym wejściu (`native_mmvq.cu:2406-2441`): qkv+gate w GDN (UD: oba Q5_K), q/k/v w attention (k,v po 1024 wiersze, latency-bound), gate+up | To **nie** jest nasza nieudana fuzja gate+up (tam były podwójne rejestry). Tutaj kod wątku się nie zmienia, rośnie tylko siatka | 2–3 węzły × 64 warstwy ≈ 130–190 granic × 3.3 µs + lepsze wypełnienie małych macierzy: **−0.4…0.7 ms → +1.2–2%** | średni (matcher w stylu istniejących fuzji; dla różnych typów warp-uniform dispatch po `blockIdx`) | niski, bitowo | `mmvq.cu` multi-col + matcher w `ggml-cuda.cu` | **K2**, też **K1** (lepsze wypełnienie CU dla małych N) |
| **5** | **GDN rollback przez replay zamiast snapshotów**, najlepiej wbudowany w kernel GDN następnego verify | Nasz kernel pisze min(T,K) pełnych stanów 3 MiB na warstwę (`~/wt/k1/.../gated_delta_net.cu:183-195`) | Dziś (T=5): 48 × (3 odczyt + 15 zapis) MiB ≈ 864 MiB/krok. Replay wbudowany: 48 × (3+3) = 288 MiB. **−576 MiB ≈ −0.6…0.7 ms → +1.7–2%** [INFERENCE; najpierw zmierzyć kernel z `keep_rs_t` vs bez przy T=5] | wysoki: semantyka `n_rs_seq`/seq_rm w llama-memory-recurrent i serwerze; trzeba zachować q/k/v/g/β okna (≈41 KB/token/warstwę) | średni | `gated_delta_net.cu`, `llama-memory-recurrent.cpp`, `server-context.cpp` (spec_ckpt) | **K2/K3**; roadmap B11 („snapshot-free rollback”) dostaje konkretny wzór |
| **6** | **Okno atencji MTP** (`--mtp-window`; 8K: +3.5% przy 64K, −0.4% przy 32K, gfx1151) | Przy 94k mamy 77.7 t/s vs 106.9 przy 1.7k (T=0). Draft przechodzi 4× po pełnym KV warstwy MTP | 0 przy krótkim kontekście; przy 94k zależnie od czasu atencji draftu: jeśli 2–4 ms/krok → **+5–10% przy 94k** [INFERENCE; najpierw rocprof grafu draftu przy 94k vs 1.7k] | niski (SWA dla warstwy MTP lub maska KQ) | akceptacja przy cytowaniu długich dokumentów | KV/maska kontekstu draftu MTP (common speculative, llama-kv-cache) | roadmap B6, długi kontekst |
| **7** | **Lookup/n-gram jako okno tylko gdy 1. token = draft MTP 0, plus polityka E[tok]/koszt(T) z kosztem mierzonym online** (`bbe8944e`, `draft_policy.hpp`, `48d2e6ca`) | Nasz „adaptive draft length” zawiódł, bo ignorował koszt szerokości. Ten mechanizm koszt zna, a reguła 1. tokenu chroni czat | czat ≈0 (chronione); kod/agent: +10–40% wg roadmap A9 (u Straty +6–11% przy drogich wierszach MoE; nasze dodatkowe wiersze są tańsze) | średni | niski (bezstratne) | `common/speculative.cpp` (priorytet `--spec-type`), `server-context.cpp` | **K4** (verify 9–16): daje regułę, kiedy szerokie okno się opłaca |
| **8** | **K5 prefill**: (a) GQA FA prefill na WMMA czytający q4_0 wprost (kody dokładne w FP16, skala FP32 na lane, układ fragmentów RDNA3 z #786, loady przed obliczeniami #2017); (b) prototyp F16-WMMA z dekwantyzacją w LDS vs MMQ (#2020); (c) sprawdzenie TFLOPS GEMM-ów K=6144 (padding stride) | Na RDNA3 iu8 WMMA ma ten sam szczyt co f16 (122.8 TOPS/TFLOPS wg specyfikacji AMD; [INFERENCE] nie sprawdzone w tej sesji), więc int8 daje tylko pasmo aktywacji. Nasz MMQ to ok. 43 TFLOPS efektywnie | (a) FA ok. 26% prefillu przy 94k; ×2–4 → **+15–20% prefill przy 94k** (u Straty +18–29% e2e przy 32–128K na gfx1100). (b) niepewne, 0…+30% na matmul. (c) diagnostyka w rocprof, 0…+5% | (a) wysoki, (b) wysoki, (c) niski | (a) niski–średni, (b) numeryka (KL) | `fattn-*` (nowa ścieżka prefill obok fattn-kvq), `mmq.cu`/nowy kernel | **K5** wprost |
| **9** | **Audyt streamów/kolejek**: liczba streamów (2 konteksty: cel + MTP, plus streamy kopii), `GPU_MAX_HW_QUEUES` | U Straty sama liczba utworzonych streamów zmieniała prefill o 16–35% (#2055), a fork w grafie kosztował do −45%. Nasz test „env HIP = szum” nie obejmował układu kolejek | 0…3% [INFERENCE], test bez zmian w kodzie | bardzo niski | niski | env + `ggml_cuda` stream pool | K3 |
| **10** | **Clamp q8_1 (d, sum → ±65504)** (`7a0e3023`) | Nasze Q4_K/Q5_K multi-col liczą człon min z `ds.y`, czyli dokładnie ścieżkę inf·0 = NaN; producenci A6 piszą q8_1 bez clampa (`quantize.cu:100,548`). Strata: po 36k-tokenowym requeście przy 155k każda odpowiedź to jeden powtarzany token (#606) | poprawność, 0 kosztu, bitowo dla skończonych bloków | bardzo niski | brak | `quantize.cu`, wszystkie fused producenty q8_1 (A6) | K1/K2: zrobić od razu |
| **11** | **Metoda tuningu K1 ze Straty**: wybór wierszy/warp i wariantu z rocprofv3 **w realnym decode**, reguła ≥3% na najgorszym kształcie klasy, rotacja wag >96 MB IC w mikrobenchu | Bench IL zawyżał zysk o 20–60%; zła komórka dała −15% decode (#1842) | chroni przed regresją; zysk K1 jest wtedy realny | niski | — | `mmvq-bench/` + rocprof w serwerze | **K1** |
| 12 | Interleaved q8_1 (kopię pisze producent) dla 9–16 kolumn | Na gfx1100 IL wygrywa tylko w klasach ≥4096 wierszy; przy T=5 już współdzielimy unpack wag | <1% przy T=5; może >1% przy 12–16 kolumnach [INFERENCE] | średni | niski | `mmvq.cu` | K4 (dopiero po pomiarze kosztu szerokości) |
| 13 | TSUM (transponowany butterfly na końcu warpa) | Już mamy DPP; zostaje tylko liczba ruchów | <0.5 ms → <1.5% (raczej <1%) | niski | FMA contraction zmienia bity | `mmvq.cu` redukcja | K1 |
| 14 | Persistent kernel z grid barrier dla krótkich łańcuchów (PR #2226) | Po A3–A6 zostało mniej łańcuchów; bariera na gfx1100 ma nieznany koszt | −2.8…4.2% ms/okno u nich (gfx1030); u nas [INFERENCE] 0–2% | wysoki | deadlock przy złym occupancy; walidacja przy starcie z timeoutem | nowe kernele | K2 (później) |

**Nie przenosić (z powodem):**
- Planar repack Q6_K: u nich 0% przy 4 kolumnach; nasz Q6_K już daje 729/695/641 GB/s przy 1/4/8 kolumnach (`NOTES.md:88`).
- Chunked WY GDN prefill: −39% na gfx1100 (#888).
- Drzewa draftów: top-2 trafiał 0/14.
- Bramka p_min / confidence: u nich też płaskie plateau 0.3–0.7 dla gęstych kosztów; zysk +10% był efektem MoE (#744).
- Rejection sampling / coupled / Gumbel: akceptacja rośnie, prędkość płaska na 3060.
- Tensor-core GEMV dla 1–8 kolumn: 1.3–2.2× wolniej.
- Staging aktywacji w LDS dla GEMV: wolniej.
- Wszystko, co dotyczy ekspertów, PCIe i CPU pool.
- Zmiana KV na int8/K8V4: jakość +8–12% PPL przy q4_0 u nich, ale u nas +1.7 GB VRAM przy 204800 ctx (q8_0-K + q4_0-V ≈ 26.6 KB/token vs 18.4 KB). Nie mieści się. Można najwyżej zrobić test jakości na długim dokumencie.

**Łączny potencjał [INFERENCE, zakładając brak nakładania].**
- Pozycje 1–5 to −3.1…4.6 ms/krok, czyli krok 35.7 → ok. 31–32.6 ms i **≈ 97–102 t/s** na krótkim kontekście (dziś 88–90).
- Pozycja 6 dodaje do tego zysk przy długim kontekście, pozycja 7 przy kodzie i agentach, pozycja 8 przy prefillu.

**Kolejność (najtańsze dowody najpierw):**
1. Pozycja 10 (clamp, minuty).
2. Pozycja 9: A/B kolejek, bez kodu.
3. Pomiary rocprof dla pozycji 2 (lista małych kerneli), 5 (`keep_rs_t` on/off) i 6 (graf draftu przy 94k).
4. Implementacja w kolejności 1 → 2 → 3 → 4, potem 5 i 6 zależnie od pomiarów, a pozycje 7/8 w ramach K4/K5.

## 6. Lekcje metodologiczne do przyjęcia

1. **Wyłącznik dla każdej optymalizacji** (`GGML_*_NO_X=1` przywraca starą ścieżkę bajt w bajt) i lista wyłączników jako gotowy plan bisekcji regresji. Odpowiedź Straty na #1373: pary, potem przełączniki po jednym.
2. **Dwie osobne bramki.**
   - Perf: identyczne tokeny greedy (mamy `greedy_check.sh`, trzeba go stosować przy każdym kroku).
   - Numeryka: teacher-forced KL na **realnych oknach verify z MTP**, zawsze obok podłogi (ten sam build uruchomiony dwa razy) i skali (np. UD vs Q4_K_M). My już robimy KLD vs szum batch (`NOTES.md:241`); trzeba to sformalizować.
3. **A/B w przeplatanych parach**, mediana stosunków wewnątrz pary, „k/n par szybszych”.
   - **Ten sam prompt w obu ramionach pary**, bo inaczej zmienia się akceptacja MTP (fałszywe +2.8% w #832).
   - Raz zmierzyć kontrolę A/A i kontrolę pozytywną (np. n=3 vs n=4), żeby znać rozdzielczość harnessu.
   - Nasze ms/krok jest już dobrą miarą (`NOTES.md:184`). Brakuje raportowania liczby par.
4. **Mikrobench nie wybiera konfiguracji.** Tablice tuningu K1 wybierać z rocprofv3 w realnym decode. Mikrobench tylko z rotacją wag >96 MB Infinity Cache (już mamy „na zimno”). Reguła ≥3% na najgorszym kształcie klasy, inaczej zostaje wariant domyślny.
5. **Jedna linia rozkładu kroku na każde żądanie** (`STRATA_DECODE_TIMING`): verify ms, draft ms, przerwy ms, host ms, zaakceptowane/krok, liczba kerneli. Każde A/B pokazuje wtedy, *gdzie* przesunęły się milisekundy, a nie tylko t/s.
6. **Sonda kosztu węzła** (`STRATA_DUMMY_NODES=k`): k pustych kerneli na warstwę daje nasz krańcowy koszt granicy kernela na gfx1100 przy 285 W, zamiast zakładanych 3.3 µs. To rozstrzyga, ile warte są K2 i pozycja 14.
7. **Zmierz okazję przed budową.**
   - Dla K4: rozkład zaakceptowanej długości i koszt verify per szerokość (6/8/9/12/16), potem offline E[tok]/koszt.
   - Dla drzew: top-2 przy odrzuceniach.
   - Dla okna MTP: czas grafu draftu przy 94k.
8. **Wyniki negatywne jako kod i dokumentacja**: opt-in plus liczby w NOTES, mikrobench zapisany w repo („so this does not have to be measured twice”, `43cd140e`). Mamy sekcję negatywów; dobrze byłoby trzymać też gałęzie/patche z liczbami.
9. **Ponownie testować, gdy zmienia się reżim.** Po K1/K2 matvec i przerwy zmieniają proporcje, więc wcześniejsze „szum” (env HIP, `GGML_CUDA_GRAPH_OPT`, hipBLASLt) wolno powtórzyć tylko z nową hipotezą.
10. **Zasada „bezpieczny default nie może kosztować prędkości”** (#2010) i szybkie wycofanie defaultu po pierwszym wiarygodnym pomiarze regresji. Dla nas dotyczy to `run-llm.sh`.
11. **Pułapki toolchainu jako checklisty.**
    - `amdgpu_waves_per_eu` źle kompilowane na clang 22 (#1180);
    - brak `__syncthreads` po double-buffered LDS (#1180);
    - DPP plus FMA contraction zmienia bity (#2231);
    - `__byte_perm` w HIP idzie przez scratch (`600d7307`; u nas `vecdotq.cuh` już używa `__builtin_amdgcn_perm`);
    - sprawdzić ISA (objdump `v_wmma` / `v_perm`), czy szybka ścieżka w ogóle się skompilowała (#786, #260).
12. **Commit = mechanizm + równoważność + wyłącznik + test + liczby (sprzęt, liczba par) + czego nie ruszono.** Ten wzorzec dokumentacji jest tani, a robi z historii gita bazę wiedzy.
