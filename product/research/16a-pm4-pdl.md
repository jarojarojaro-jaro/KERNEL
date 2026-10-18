# 16a — PM4-PDL i prefetch wag na RX 7900 XTX (eksperymenty X1–X3 z 15a)

Data: 2026-10-16…18. Lokalne XTX (gfx1100, ROCm 10.0), $0. Gałąź `pm4-pdl` z `amd-opt` f61994f58, worktree `~/wt/pm4pdl`,
commit `3a008359b` (wszystko za przełącznikami env, domyślnie wyłączone). Surowe wyniki: `~/qwen-opt/pm4pdl/`
(`x1/` mikrobenchmark, `x2/` pomiary w modelu, `x2/frozen/` skrypty).

## TL;DR

1. **X1 (mikrobench PM4-PDL): KILL.** Dla kształtu z hipotezy 15a (matvec 2048×2048 Q5_K, 1024 bloki) najlepszy wariant
   z bezpieczną synchronizacją oszczędza **0.11 µs/kernel** (4.775 → 4.669 µs), próg to 0.5 µs. Samo usunięcie granicy bez
   synchronizacji dałoby 1.73 µs, więc synchronizacja (ticket producenta + poll konsumenta) zjada 94% zysku. Na siatkach
   1536–3072 bloków zostaje 0.6–1.1 µs (29–44% zysku bez synchronizacji). Bez zakleszczeń i bez złych wyników.
2. **X2 (PM4-PDL w taśmie LFM): górna granica +12.0%, oczekiwany realny zysk ≈ +2.9% `[SZACUNEK]` → poniżej progu +3%, KILL.**
   Usunięcie granic bez żadnej synchronizacji (wyniki błędne, tylko czas) przed MoE down: +6.5%, przed zwykłymi MMVQ n=1:
   +6.8%, oba: 289.3 → 324.0 t/s. Po przeliczeniu ułamkiem, który zostaje po synchronizacji w X1 (6–44% zależnie od
   siatki), zostaje ~0.10 ms/token, i to dopiero po przepisaniu MMVQ n=1 / down_reduce na prefetch wag do VGPR (bitowo).
   Usunięcie wszystkich granic naraz zawiesza taśmę (abort po 10 s).
3. **X3 (prefetch wag do L2/MALL dispatchem „touch” bez granicy): KILL.** 1–4 MiB: +0.2…+0.6% (w szumie: produkcja vs
   ta sama taśma różni się o 0.5%, rozrzut rund do 8 t/s), 16 MiB: −2.4%.
4. Qwen MTP nie uruchamiany (żaden eksperyment nie wygrał). Do produkcji nic nie idzie. Koszt: $0 (tylko lokalne XTX).

## 1. X1 — mikrobenchmark PM4-PDL

### Projekt
`~/qwen-opt/pm4pdl/x1/pdl.cpp` + `pdl_kern.hip` (rozszerzenie `~/wt/lfm4-prof/pm4.cpp`). Łańcuch N zależnych syntetycznych
matvec w kształcie MMVQ Q5_K n=1 z LFM (2048 kolumn = 1408 B/wiersz, 2 wiersze na blok jednej fali, 22 dwordy wag na
lane, wagi zimne z puli 1 GiB, wyjście kernela i jest wejściem kernela i+1). Jedna taśma PM4 (vendor AQL packet) na
własnej kolejce ROCr, jak `GGML_HIP_PM4`. Epoka pisana przez CP (`WRITE_DATA`) na starcie każdej taśmy, więc liczniki
i flagi nie wymagają zerowania. Pomiar jak w 15a: (T(1000) − T(200)) / 800, mediana z 25 par, kontrola bitowa wyjścia
względem wariantu z granicą i słowo błędu (bounded spin, 2¹⁶ prób).

Warianty (bez pakietów granicy `CS_PARTIAL_FLUSH` + `ACQUIRE_MEM`, chyba że zaznaczono):

| wariant | producent | konsument |
|---|---|---|
| B | — (granica, dziś) | — |
| BC | granica + `fetch_add` release na liczniku | — |
| P0 | `fetch_add` na jednym liczniku | wagi → VGPR, potem poll licznika (= epoka × liczba bloków) |
| T0c16 | ticket: ostatni blok pisze epokę do 16 kopii flagi (po linii 128 B) | wagi → VGPR, poll swojej kopii flagi (`s_sleep 1` lub 8) |
| T1c16 / T2c16 | jw. | bez prefetchu / „touch” po 1 dword na linię wag przed czekaniem |
| W0c16 | licznik | blok 0 polluje licznik i rozsyła epokę do 16 flag („relay”), reszta wagi → VGPR → poll flagi |
| S0 | licznik rozłożony na 16 linii | suma 16 liczników |
| R0 | CP: `RELEASE_MEM` (EOP) po dispatchu pisze flagę | wagi → VGPR → poll flagi |
| O | nic (złe wyniki) | nic — dolna granica |

### Wyniki (czysty przebieg, `x1/bench4.log`, 2 powtórzenia całego zestawu, µs/kernel)

| siatka (bloki) | MB/matvec | B (dziś) | BC | najlepszy PDL | Δ vs B | O (bez sync) | Δ O vs B |
|---|---|---|---|---|---|---|---|
| 1024 (= LFM 2048², out_proj/attn) | 2.88 | 4.775 | 5.341 | W0c16 4.669 | **−0.11** | 3.046 | −1.73 |
| 1536 (in_proj+conv) | 4.33 | 6.674 | 7.396 | T0c16s8 6.081 | −0.59 | 4.643 | −2.03 |
| 2560 | 7.21 | 10.316 | 11.327 | T0c16s1 9.229 | −1.09 | 7.838 | −2.48 |
| 3072 | 8.65 | 12.201 | 19.843 | T0c16s8 11.257 | −0.95 | 9.401 | −2.80 |

Pozostałe obserwacje:
- **Jeden licznik/flaga, którą polluje cały grid, jest wolniejszy od granicy** (P0 1024: 7.07 vs 5.01, T0c1 6.32; `x1/bench2.log`). Dopiero 16 kopii flagi (po linii 128 B) albo relay daje wynik ≤ B. To ten sam problem, który MonoKernel rozwiązuje `pre_poll` (15a §2.2).
- **Prefetch wag do VGPR przed czekaniem pomaga tylko na dużych siatkach** (2560: T0 9.23 vs T1 bez prefetchu 10.23; 1024: bez różnicy). Touch do L2 (T2) jest gorszy od prefetchu do VGPR wszędzie.
- **Sam atomik producenta kosztuje:** BC = granica + `fetch_add` release na bloku: +0.57 µs (1024), +7.6 µs (3072; jeden adres, 3072 atomiki).
- Liczniki rozłożone na 16 linii (S0) są gorsze od B (1024: 11.3 µs przy obciążonym GPU, `x1/bench3.log`).
- `RELEASE_MEM` z CP jako flaga: przy 1024/1536/2560 blokach czekanie wygasa (flaga nie przychodzi w 2¹⁶ próbach), przy 3072/6144 działa, ale jest wolniejsze od B. Moje kodowanie pakietu dla gfx11 może być złe `[NIEZWERYFIKOWANE]`; porzucone.
- **Bez zakleszczenia:** siatka 6144 bloków (2× pojemność GPU) we wszystkich wariantach bez wygaśnięć (`x1/bench2.log`), zgodnie z założeniem 15a §4.1, że dispatcher wydaje grupy kolejnych dispatchy po kolei.
- Poprawność: 0 niezgodności bitowych i 0 wygaśnięć we wszystkich wariantach z protokołem (smoke n = 1/2/10/100 i każdy pomiar). Soak 10⁵ replayów nie był uruchamiany (X1 i tak odpada na kryterium zysku).

**Werdykt X1 (kryterium 15a §6: oszczędność < 0.5 µs/parę → kill): dla kształtu z hipotezy (2048², 1024 bloki) −0.11 µs → KILL.**
Zysk istnieje tylko dla siatek ≥1536 bloków (0.6–1.1 µs). Synchronizacja zjada 94% (1024) do 56–66% (2560/3072) tego, co daje usunięcie granicy.

## 2. X2 — PM4-PDL w taśmie LFM: górna granica

Zanim przepisuje się kernele produkcyjne (ticket/flaga w MMVQ n=1, down_reduce, conv), zmierzyłem **górną granicę**:
`GGML_HIP_PM4_UB=<klasy>` usuwa pakiety granicy przed wszystkimi dispatchami danej klasy **bez żadnej synchronizacji**
(wyniki błędne, tylko czas). Każdy PDL ma koszt synchronizacji ≥ 0, więc zysk PDL ≤ zysk UB. Klasy: `conv`
(in_proj+conv, 29/token), `down` (MoE down+reduce, 38), `mmvq1` (zwykłe MMVQ n=1 bez ids: out_proj, attn q/k/v/o, gęste
FFN, głowa), `router` (norm+router+top-k), `norm` (rms_norm). LFM2.5-24B-A2B Q5_K_M, KV q8_0, llama-bench tg128 -r 5,
`ab.sh` przeplatane.

Wyniki ważne: `x2/ab4.log` (2 rundy, wszystkie konfiguracje w każdej rundzie, po restarcie z nową krzywą wentylatora) i
`x2/ab2.log` (1 runda, przed pauzą). `x2/ab3.log` biegł w czasie pauzy — tylko orientacyjnie, zgodny z ab4.

| konfiguracja | granic usuniętych / token | ab4 runda 1 / 2 (t/s) | średnia | ms/token | Δ vs `-` | ab2 (1 runda) |
|---|---|---|---|---|---|---|
| produkcja `~/llama-opt` | 0 | 288.79 / 292.67 | 290.73 | 3.440 | +0.5% | 294.84 |
| `-` (ta gałąź, przełączniki wył.) | 0 | 289.49 / 289.15 | 289.32 | 3.456 | 0 | 294.07 |
| UB conv | 29 | 293.93 / 292.48 | 293.21 | 3.411 | +1.3% | 288.88 |
| UB down | 38 | 307.83 / 308.55 | 308.19 | 3.245 | **+6.5%** | 306.06 |
| UB mmvq1 | 75 | 308.64 / 309.07 | 308.86 | 3.238 | **+6.8%** | 303.25 |
| UB router | 38 | 295.46 / 298.74 | 297.10 | 3.366 | +2.7% | 297.08 |
| UB norm | 43 | 296.61 / 300.77 | 298.69 | 3.348 | +3.2% | 297.19 |
| **UB down,mmvq1** | 113 | 326.04 / 321.90 | **323.97** | **3.087** | **+12.0%** | — |
| UB conv,down,mmvq1,router,norm | 196 | taśma wisi (abort 10 s) | — | — | — | — |

Na jedną usuniętą granicę w modelu: down 0.211 ms / 38 = **5.6 µs**, mmvq1 0.218 ms / 75 = **2.9 µs**. To więcej niż
1.7–2.8 µs z X1 bez synchronizacji, bo w modelu konsument nachodzi też na ogon producenta (np. down na ogon gate+up 3072
bloków).

- `UB=conv,down,mmvq1,router,norm` (196 z 389 granic): **taśma wisi**, abort po 10 s (`x2/comb.err`); błędne dane w
  kernelach z ticketami/indeksami. „all” też nie mierzone. Każda klasa osobno i `down,mmvq1` działają.

**Ile z tego zostaje po prawdziwej synchronizacji** `[SZACUNEK]`: przyjmuję ułamek z X1 (oszczędność PDL / oszczędność
bez synchronizacji dla podobnej siatki): down (2048 bloków, między 1536: 29% a 2560: 44%) ~35% → 0.074 ms; mmvq1
(głównie siatki 1024 i 256 bloków) ~6–10% → ~0.015 ms; conv (1536 bloków) 29% × 0.045 ms → 0.013 ms. Razem ≈ 0.10 ms z
3.456 ms = **+2.9%**, przy czym:
- wymaga to prefetchu wag do VGPR w kernelach produkcyjnych przed czekaniem (bez prefetchu, wariant T1, PDL w X1 nie daje
  nic: 2560 bl. −0.09 µs). MMVQ n=1 i down_reduce czytają wagi przez `vec_dot_q_cuda` w pętli; ścieżka „xraw” z
  wielokolumnowego MMVQ liczy człon min Q5_K inaczej (nie bitowo). Bitowy prefetch = przepisanie pętli każdego typu
  (15a: 6–9 osobodni);
- producent musi zrobić atomik na blok: w X1 sam ten atomik (BC) kosztuje +0.57 µs przy 1024 i +7.6 µs przy 3072
  blokach (jeden adres); ticket z 16 kopiami flagi to ukrywa, ale nie zawsze;
- 15a zakładało +5…+15% (S1/S1'); pomiar daje górną granicę +12% bez synchronizacji, a realnie ~3%.

**Werdykt X2: kill (oczekiwany zysk ≤ +3% przy koszcie 6–9 osobodni i ryzyku zawieszeń; kryterium briefu < +3%).**
Greedy md5 nie był potrzebny (nic nie trafia do produkcji; UB daje złe wyniki z definicji). Jedyny kandydat, gdyby wracać:
sam down_reduce (górna granica +6.5%, siatka 2048, ~35% → ~+2.2%).

## 3. X3 — prefetch wag do L2/Infinity Cache

`GGML_HIP_PM4_TOUCH=<KiB>`: w taśmie po każdym małym dispatchu (≤ 64 bloki: norm, router, attn_prep, FA, combine) i przed
matvec, którego wagi zostały zapisane przy uruchomieniu (`ggml_hip_pm4_note_weights`, MMVQ n=1 bez ids i in_proj+conv),
wstawiany jest dispatch `ggml_hip_pm4_touch` (≤ 64 × 256 wątków, 1 dword na linię 128 B pierwszych <KiB> wag) **bez
pakietów granicy**: czyta wagi do L2/MALL równolegle z małym kernelem. Następna granica czeka na oba. 54 dispatche touch
na taśmę (smoke `x2/smoke.log`). API `hipLaunchAttributeExtDynDataPrefetch` nie wchodzi w grę na gfx1100 (ROCr: 0 regionów,
15a §7). Wyniki bitowo te same z definicji (ten sam łańcuch kerneli + kernel tylko do odczytu).

| konfiguracja | ab4 runda 1 / 2 (t/s) | średnia | Δ vs `-` | ab3 (orientacyjnie) |
|---|---|---|---|---|
| `-` | 289.49 / 289.15 | 289.32 | 0 | 290.29 |
| TOUCH 1024 KiB | 293.89 / 285.93 | 289.91 | +0.2% | 293.98 |
| TOUCH 2048 KiB | 292.59 / 289.48 | 291.03 | +0.6% | 289.88 |
| TOUCH 4096 KiB | 292.36 / 289.87 | 291.12 | +0.6% | 289.99 |
| TOUCH 16384 KiB | 282.27 / — (runda 2 nie wykonana: serwer użytkownika) | 282.27 | −2.4% | 283.87 |

**Werdykt X3: kill (kryterium 15a: < 1% taśmy).** +0.2…+0.6% mieści się w szumie (produkcja i ta sama taśma z tej gałęzi
różnią się o 0.5%, rozrzut jednej konfiguracji między rundami do 8 t/s), a większy prefetch (16 MiB) spowalnia: touch
konkuruje o pasmo z bieżącym kernelem. W X1 analogiczny „touch” przed czekaniem (T2) też przegrywał z prefetchem do VGPR.
Nie mierzyłem czasów per klasa (`GGML_HIP_PM4_DEBUG=3`), bo t/s nie pokazało efektu.

## 4. Qwen MTP
Nie uruchamiane: brief każe sprawdzać Qwena tylko, gdy któryś z X1–X3 wygra.

## 5. Kod (commit `3a008359b`, gałąź `pm4-pdl`)
- `hip-pm4.cu`: `GGML_HIP_PM4_UB` (diagnostyka, NIEBEZPIECZNE — złe wyniki, możliwe zawieszenie taśmy), `GGML_HIP_PM4_TOUCH`, licznik pominiętych granic w `GGML_HIP_PM4_DEBUG=1`.
- `mmvq.cu`: rejestracja wag (`ggml_hip_pm4_note_weights`) w MMVQ n=1 i in_proj+conv (no-op, gdy TOUCH=0).
- Domyślna ścieżka bez zmian: `-` vs produkcja w tabeli §2 (ta sama taśma, 304 dispatche).
- Do produkcji nic nie idzie.

## 6. Co dalej
- PM4-PDL i prefetch MALL na XTX: zamknięte. Zysk z granic jest prawdziwy (górna granica +12%), ale tanio go nie wziąć:
  synchronizacja przez pamięć na RDNA3 kosztuje prawie tyle, co granica PM4 (0.46–0.86 µs), przy małych siatkach więcej.
- Jeśli wracać do tematu, to tylko jako kernel dataflow (15a pomysł C/D: trwały blok MoE), gdzie hand-off nie wymaga
  atomika na każdy blok producenta, albo jako fuzja gate+up → down w jednym kernelu.
- `GGML_HIP_PM4_UB` zostaje na gałęzi jako narzędzie: szybka górna granica dla każdego pomysłu „mniej granic”.

## Do bazy wiedzy

| folder | tytuł (plik) | streszczenie | kluczowe liczby (źródło) |
|---|---|---|---|
| eksperymenty | PM4-PDL na XTX: synchronizacja zjada zysk (`2026-10-18-pm4-pdl-x1.md`) | Usunięcie granicy PM4 między zależnymi matvec i zastąpienie jej ticketem/flagą z prefetchem wag do VGPR | 1024 bl.: 4.775 → 4.669 µs (−0.11, próg 0.5), bez sync −1.73; 2560 bl. −1.09 z −2.48; 16 kopii flagi konieczne (1 licznik: 7.07, 1 flaga: 6.32 vs granica 5.01 µs); atomik producenta +0.57…+7.6 µs (`16a-pm4-pdl.md` §1, `~/qwen-opt/pm4pdl/x1/bench4.log`) |
| eksperymenty | Górna granica „mniej granic” w taśmie LFM (`2026-10-18-pm4-ub-lfm.md`) | `GGML_HIP_PM4_UB` usuwa granice bez synchronizacji (złe wyniki, tylko czas) | down +6.5%, mmvq1 +6.8%, oba +12.0% (289.3 → 324.0 t/s), 5.6 µs/granicę down, 2.9 µs mmvq1; wszystkie klasy naraz: zawieszenie taśmy (`16a` §2, `x2/ab4.log`) |
| lekcje | Wynik negatywny: prefetch wag do MALL dispatchem bez granicy (`prefetch-mall-xtx.md`) | Touch 1–4 MiB wag następnego matvec w trakcie małych kerneli nie przyspiesza, 16 MiB spowalnia | +0.2…+0.6% (szum), 16 MiB −2.4% (`16a` §3, `x2/ab4.log`) |
| lekcje | RDNA3: hand-off przez pamięć ≈ koszt granicy PM4 (`handoff-rdna3.md`) | Każdy protokół flag/ticketów kosztuje ~to samo co CS_PARTIAL_FLUSH+ACQUIRE_MEM; zysk tylko na siatkach ≥1536 bloków i tylko z prefetchem do VGPR | patrz X1; RELEASE_MEM z CP jako flaga: czekanie wygasa (`16a` §1) |
| research | Raport 16a (`raport-16a-pm4-pdl.md`) | X1 kill, X2 kill (górna granica +12%, realnie ~+3%), X3 kill; Qwen nie testowany | `16a-pm4-pdl.md` TL;DR |
| research | Aktualizacja raportu 15a | Szacunek S1 (+9–15%) za wysoki: realny PM4-PDL ≈ +3% | `16a` §2 |
