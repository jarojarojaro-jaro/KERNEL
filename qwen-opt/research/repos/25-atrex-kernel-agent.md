# 25 — Atrex Kernel Agent (AKA, Alibaba)

Repo: https://github.com/alibaba/atrex-kernel-agent (HEAD `5ad94ff`, 2026-10-14, v0.3.0). Przeczytałem też artykuł
https://arxiv.org/abs/2607.14541 („Are LLM-Generated GPU Kernels Production-Ready?”, wersja HTML v1). Artykuł na
WeChacie o operatorach Qwen3.8-Max (README:46, „do 1.55×”) jest za captchą, więc tej liczby nie dało się sprawdzić.

## 1. Co to jest

AKA to orkiestrator agentów kodujących (Claude/Codex/Qoder/Pi) dla **jednego operatora naraz**. Ma pętlę
profil → wiedza → plan → edycja → weryfikacja, mechaniczny nadzorca (to on promuje kandydata, nie agent), izolację w
git worktree i bazę wiedzy „GPU Wiki” (961 plików JSON). Licencja Apache‑2.0. Projekt jest aktywny: v0.1 w czerwcu,
v0.3 we wrześniu, ostatni commit z dzisiaj. Sprzęt: NVIDIA Hopper/Blackwell, **AMD tylko CDNA3/CDNA4**
(MI300X/MI308X/MI355X) i T‑Head PPU. Na AMD obsługuje wyłącznie Triton/FlyDSL/TileLang, bez HIP C++
(`orchestrator/constants.py:54`). Kernel jest zawsze plikiem `kernel.py`. RDNA nie ma nigdzie: ani w hardware_wiki,
ani w narzędziach. Jedyne 2 karty „RDNA4” mają błędne gfx (niżej, §5).

## 2. Kluczowe techniki (z dowodami)

### 2a. Pętla i kontrola
| # | Technika | Dowód |
|---|---|---|
| A1 | **Nadzorca mechaniczny.** O akceptacji i zakończeniu decyduje kod, nie samoocena agenta. HEAD = zawsze najlepszy zaakceptowany kandydat. Agent edytuje tylko swój worktree i oddaje `candidate_ready`/`pivot`/`blocked` | `docs/design.md:24-27`, `:84-87`, `:145-146` |
| A2 | **Tryb szybki → pełny.** Epizody 1–2 to 5 prób „plan → implementacja → jeden pełny ewaluator” **bez profilowania i bez ABBA**, wygrywa najszybsza poprawna. Dopiero od epizodu 3: profil → research → plan → edycja → poprawność → bench | `design.md:433-453`, `constants.py:35-37` |
| A3 | **Weryfikacja ABBA w jednej alokacji GPU**: inkumbent/kandydat naprzemiennie, sprawdzenie, że wykonano dokładnie ten harmonogram, wszystkie przebiegi muszą przejść. Domyślnie **2 pary i próg 0%** | `long_horizon/verifier.py:40-51`, `:285-295`, `:332-371`; `constants.py:37`; `orchestrator/campaign.py:201` |
| A4 | **Wynik przypięty do hasha**: rekord ewaluatora musi mieć hash dokładnie tego `kernel.py`, który jest zacommitowany | `design.md:378-383`, `:438-445` |
| A5 | **Jedna kategoria optymalizacji na edycję**, z zapisem „evidence → inference → action”. Delta > ~30% wymaga powtórzenia pomiaru | `skills/gpu-kernel-episode-loop/SKILL.md:197-200`, `:218-221` |
| A6 | **„Optimization dropout”**: po zastoju maskuje się część rekordów pamięci (`masked: true`), ale nie kod ani zaakceptowane pomiary. Świeży agent ocenia kernel bez kotwicy w starych porażkach. Tryb „goal” startuje po ≥50 epizodach i >3 epizodach bez promocji | artykuł §5.2 pkt 6; `tools/memory_manager.py:298-308`; `long_horizon/campaign.py:49-50`, `:545-549` |
| A7 | **Plan recenzowany przez niezależnych recenzentów.** Zamrożona propozycja + ten sam pakiet dowodów trafia współbieżnie do Codexa i Qodera, żaden nie widzi odpowiedzi drugiego. Domyślnie wyłączone | `skills/gen-plan/SKILL.md:79-84`, `:102-126` |
| A8 | **Dodatkowe sondy numeryczne.** Osobny agent czyta kod kandydata i referencję, po czym zleca ≤3 celowane rozkłady wejść (constant, near_constant, log_uniform, sparse, alternating, ramp, packed_bytes) z cytatem linii kodu. Nadzorca je uruchamia, a błąd wraca do agenta do naprawy. Agent nie ustala tolerancji (rel‑L2 ≤ 1e‑3 jest stała) | `orchestrator/prompts/numerical_review.md:14-36`, `docs/releases/v0.3.0.md` („Correctness and measurement”) |
| A9 | **Specyfikacje sprzętu tylko ze źródłem.** Liczba szczytowa bez cytatu unieważnia przebieg. Roofline liczony przed pierwszym kernelem | `design.md:523`; artykuł §5.2 pkt 3 |

### 2b. Narzędzia pomiarowe (AMD)
| # | Technika | Dowód |
|---|---|---|
| T1 | **rocprofv3 ATT (thread trace) + automatyczne streszczenie**: top‑15 instrukcji wg latency, top‑10 wg stall, wykrycie `ds_bpermute` i `scratch`. Działające flagi dla ROCm 7.2: jawna geometria (`--att-target-cu 1 --att-shader-engine-mask 0xf --att-simd-select 0xf --att-buffer-size 0x6000000`), `--output-format csv json` (bez tego jest tylko `results.db`), **bez** `--att-activity`, iteracja `[1]` z pominięciem rozgrzewki, wybór największego `stats_*.csv` | `tools/profile_kernel.sh:220-290`; `reference/profile_guide.md:64-154` |
| T2 | Tabela „wzorzec ISA × stall/idle → akcja” (np. `buffer_load_*` + wysoki stall → pipelining, wysoki idle → za długi łańcuch zależności) | `profile_guide.md:212-231` |
| T3 | **Sufit pasma dla danego rozmiaru danych**: memcpy o tej samej liczbie bajtów jako mianownik wykorzystania, bo małe transfery nie nasycają HBM | `tools/measure_bandwidth_ceiling.py:16-35` |
| T4 | **Linia czasu wewnątrz kernela**: rekorder per właściciel (CTA/warp) w buforze z nagłówkiem ABI. Wykrywa overflow, zdublowanego właściciela i zły SM; znaczniki `globaltimer`+`smid`. Pomiar perturbacji ABBA+BAAB w świeżych procesach, cel narzutu ≤10%. Snapshot z sondami nigdy nie jest kandydatem | `skills/autonomous-gpu-kernel-timeline/backends/cuda_backend/atrex_timeline.cuh:108-217`; `SKILL.md:48-62`, `:75-76` |

### 2c. Wiedza z GPU Wiki (MI300X/MI308X, pomiary autorów)
- **Persistent kernel w FA**: −3.1% (87.4 → 84.7 TFLOPS), bo grid 512 WG i tak amortyzuje start, a stan kafla
  (Q, max/sum, O) trzeba zapisywać i przywracać (`anti-strategy/.../flash-attn-pitfalls.25-...json`).
- **Stosunek `SQ_LDS_BANK_CONFLICT/SQ_INSTS_LDS` wprowadza w błąd**: 72.7% na instrukcję przy 3.7% czasu GPU w
  stallu. Decyzję podejmować na metryce „% czasu w stallu” (`...flash-attn-pitfalls.33-...json`).
- **MoE M=1 (decode)**: średnia ze zdarzeń skacze 622 ↔ 526 µs przy czystym trace’ie. Kolejność diagnozy: trace →
  suma kerneli → minimum e2e → dopiero średnia (`...fused-moe-fp8-ptpc-pitfalls.11-...json`). Wydajność odczytywać
  tylko z `rocprofv3 --kernel-trace` z jawną listą sumowanych dispatchy (`...chunk-gdn-...pitfalls.3-...json`).
- **„Mniej VGPR/LDS statycznie” nie oznacza szybciej**: o akceptacji decyduje rocprofv3 (`...chunk-gdn-...pitfalls.5-...json`).
- **Zigzag na poziomie SE** dla causal attention na MI300X: +15–20% (`technique-card/amd/cdna3/gluon/.../se_level_zigzag.*`).
- **Chunk‑GDN na MI308X**: megakernel z 8 falami, 4 liczącymi i 4 producentami, `h_acc` fp32 w rejestrach. W bazie
  zostały tylko streszczenia, bo pełny markdown usunięto przy migracji do JSON (`doc/amd/cdna3/flydsl/...megakernel...json`).

### 2d. Wyniki (artykuł, XPU‑A)
- „XPU‑A” jest zanonimizowany. `[WNIOSEK]` To MI308X: case study wspomina „80‑CU occupancy limit”, a ścieżki to
  AITER/FlyDSL.
- Vanilla agenci: najlepszy S_agg = 0.107 dachu. Żaden nie dorównuje kernelowi produkcyjnemu (Tab. 4).
- AKA, Tab. 8: **3 operatory × 1 kształt × pojedynczy pomiar** (§5.4: „Performance is a single timed run per
  (op, shape)”), wynik względem kernela produkcyjnego:
  - chunk_gated_delta: 0.03× → 1.20× (Qwen3.7‑Max) i 0.04× → 1.31× (Opus 4.7);
  - attention_forward: 0.17× → 1.11× i 0.78× → 1.17× (S 0.28 → 0.42);
  - mla_decode: 0.10× → 1.06× i 0.71× → 1.27×.
- Dla operatorów „dispatch‑bound” S zostaje na podłodze (0.03 i 0.004).

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Przenośność | Jak u nas / dlaczego nie |
|---|---|---|
| A1/A3/A4 nadzorca + ABBA + hash | tak, w większości już mamy | Przeplatane A/B, przełączniki `GGML_HIP_*`, greedy md5/logit hash. AKA nie daje nic ponad 04/06/21 poza jednym szczegółem: **pomiar przypięty do hasha binarium**. Ich próg 0% przy 2 parach jest słabszy niż nasze 2 rundy × 6 promptów × 3 seedy. |
| A2 tryb szybki bez profilu | tak | Pasuje do strojenia parametrów (NI/RPB/waves_per_eu), gdzie profil niczego nie wyjaśnia. Robimy to już w praktyce (K1). |
| A6 dropout pamięci | tak, jako eksperyment procesu | Kłóci się z naszą regułą „Wyniki negatywne – nie wracać”. Patrz P4: filtr negatywów dopiero **po** propozycjach, nie przed. |
| A8 sondy numeryczne | tak | Odpowiednikiem są dodatkowe przypadki w `test-backend-ops` z celowanymi rozkładami wejść (P3). Nasza bramka bitowa nic nie mówi o zmianach niebitowych (q8_0 kvq, stan GDN fp16). |
| T1 ATT | **tak, inne flagi** | rocprofv3 ATT na gfx1100 jest „Trace‑only” (instrukcje i czasy działają, `--att-perfcounters`/`--att-activity` nie; dokumentacja ROCprofiler‑SDK, „Using thread trace”, tabela urządzeń). Flagi AKA są pod gfx9: na Navi `--att-simd-select` to **ID SIMD 0–3**, nie maska (domyślnie 3, zalecane `0x0`), a `--att-target-cu` to **WGP**. Navi31 ma 6 SE → maska `0x3f` `[WNIOSEK]`. „Latency = Stall + Execute” na gfx10+. Strata używał thread trace na gfx1151 (`research/strata/issues.md:72`), więc ścieżka działa na RDNA3.x. Ważne, bo nasze PMC zwracają 0 (`NOTES.md:256`). |
| T2 tabela ISA→akcja | częściowo | `v_mfma` → `v_wmma`, `ds_bpermute` → u nas DPP/`ds_swizzle`. Reszta (szerokość `buffer_load_dwordx4`, `scratch`, `s_waitcnt`) obowiązuje 1:1. |
| T3 sufit dla rozmiaru | tak | Kernel czytający te same bajty tym samym gridem w łańcuchu grafu HIP, z wagami „na zimno” > 96 MB MALL (P2). |
| T4 linia czasu w kernelu | tak | `globaltimer` → `wall_clock64()` (100 MHz na gfx11, ×10 = ns, jak u Strata `research/strata/kernels.md:69`) albo `s_memrealtime`. `%smid` → `s_getreg_b32(HW_REG_HW_ID1)` z polami SE/SA/WGP/SIMD `[WNIOSEK, sprawdzić bity dla gfx11]`. Rekorder per blok w buforze globalnym, tylko w buildzie diagnostycznym. |
| Persistent FA −3.1% | tak, jako ostrzeżenie | Zgodne z naszym pomiarem: łańcuch dużych faz w kernelu trwałym kosztuje 8–11 µs/fazę (`NOTES.md:358`). Persistent ma sens tylko przy małych gridach. |
| Zigzag SE | słabiej | MI300X ma 8 XCD z osobnymi L2, Navi31 ma 6 SE i **wspólne** L2/MALL. Zostaje tylko efekt ogona fal przy nierównej pracy bloków (causal FA w prefillu), patrz P6. |
| Megakernel chunk‑GDN (fale producent/konsument) | nie teraz | Chunked GDN na gfx1100 to już udokumentowany negatyw (Strata #888, −39%; `repos/10-tilelang.md:58`, `17-tilegym.md:52`). Rozdział fal producent/konsument bez async‑copy na RDNA3 daje mniej niż na CDNA z `buffer_load ... lds`. |
| Sandbox/Bubblewrap/recovery, PPU, Gluon, FlyDSL | nie | Infrastruktura flot GPU (`tools/sandbox.py` ma 4900 linii, monitor 1331). U nas jedna karta i HIP C++. |

## 4. Pomysły dla nas

Pomijam to, co już jest w 04/06/21 i NOTES: przeplatane A/B, ledger, archiwum TRAPS, retrospektywa, LOO ablacja,
świeży agent z ramowaniem, dedup ISA, red‑team łatek, chunked GDN.

**P1. ATT thread trace dla gorących kerneli decode (Qwen + LFM).** Źródło: T1, T2.
- Co: skrypt `prof/att.sh` z flagami pod Navi:
  - `rocprofv3 --att --att-library-path <decoder> --att-target-cu <WGP> --att-shader-engine-mask 0x3f
    --att-simd-select 0 --att-buffer-size 0x6000000 --output-format csv json`;
  - `--kernel-include-regex 'mul_mat_vec_q'`, `--kernel-iteration-range` poza rozgrzewką, `llama-bench -n 8`;
  - jeśli trace nie łapie kerneli z grafu, `GGML_CUDA_DISABLE_GRAPHS=1` (ISA jest ten sam).
- Parser jak w AKA (`profile_kernel.sh:259-289`), plus udział `s_waitcnt vmcnt` w latency i liczba
  `buffer_load_dwordx4` między kolejnymi `s_waitcnt`.
- Cel: odpowiedzieć z ISA, dlaczego MMVQ n=1 ma ~700–780 GB/s, a nie ~900, i dlaczego NI=8 przegrało
  (`NOTES.md:103`). Do rozróżnienia: za mało bajtów w locie na falę, stall na adresowaniu SALU/VALU czy ogon redukcji.
  Te same pytania dla `fattn-kvq` przy 94k i `norm_router_topk`.
- Zysk: pośredni. `[SZACUNEK]` Zamienia zgadywanie wariantów NI/RPB na 1–2 celowane zmiany. Pokrywa się z 02 P3
  („sprawdzić, czy ATT działa”). Nowe są konkretne flagi Navi i gotowy parser.
- Koszt: 2–4 h. Ryzyko: dekoder nie ładuje się na ROCm 10.0 albo trace ma 0 bajtów (AKA opisuje ten objaw przy złej
  geometrii, `profile_guide.md:96`). Pomiar: czy `stats_*.csv` ma >0 wierszy dla `mul_mat_vec_q`.

**P2. Sufit pasma dopasowany do rozmiaru i gridu każdego gorącego wywołania.** Źródło: T3.
- Co: mikrokernel „tylko odczyt” (dwordx4, GLC|DLC jak K1, suma do jednego rejestru) wołany z dokładnie tą liczbą
  bajtów i tym samym gridem co dane wywołanie MMVQ. Klasy wywołań:
  - LFM: gate+up ekspertów ~8.7 MB w 12.5 µs, in_proj, out_proj, down+reduce (`lfm-decode-round2.md:50-53`);
  - Qwen: ffn up/gate/down, qkv, n=1 i n=5.
- Uruchamiany w łańcuchu grafu HIP między innymi kernelami, z rotacją kopii > 96 MB.
- Wynik to tabela „GB/s kernela / GB/s sufitu tego rozmiaru”. Dla wywołania ~10 µs rozbieg i wygaszanie grida to
  istotny ułamek, więc sufit może wyjść ~750–850 GB/s, a nie 960 `[SZACUNEK]`.
- Zysk: decyzyjny. Jeśli gate+up LFM ma ≥90% sufitu dla swojego rozmiaru, dalsza praca nad pasmem MMVQ w LFM nie ma
  sensu i zostają tylko granice kerneli. Jeśli <80%, wiadomo, gdzie kopać.
- Koszt: 0.5–1 dnia. Ryzyko: mikrokernel jest lepszy niż realny dach, bo nie dekoduje. Wtedy dodać wariant z kosztem
  ALU dekodu Q5_K jako drugi punkt. Pomiar: rocprofv3 `--kernel-trace`, mediana z ≥50 wywołań.

**P3. Celowane sondy numeryczne dla nowych kerneli (zwłaszcza niebitowych).** Źródło: A8.
- Co: przy każdej łatce agent kernelowy dopisuje ≤3 przypadki do `test-backend-ops` z nietypową inicjalizacją, każdy z
  cytatem linii kodu, który może zawieść. Kandydaci:
  - (a) **remisy logitów routera** (identyczne wartości) w `norm_router_topk` i `topk_moe`: porządek ekspertów
    deterministyczny i zgodny z CPU;
  - (b) aktywacje blisko ±65504 i „massive activations” w producentach q8_1 (to samo ryzyko, które wykrył S1,
    `NOTES.md:259`);
  - (c) `fattn-kvq` przy długim KV z prawie równymi logitami i skrajnymi skalami bloków q4_0/q8_0 (przed planowaną
    instancją q8_0, `lfm-decode-round2.md:95-101`);
  - (d) GDN z β≈1 i bramką → 0 (kasowanie stanu) w ścieżce lag/replay S4.
- Zasada z AKA: próg ustala Main, agent nie widzi marginesu. Spójne z 21 P6(f).
- Zysk: 0 t/s, ochrona przed cichym błędem w zmianach niebitowych. Koszt: ~0.5 dnia na zestaw, potem ~30 min na
  łatkę. Pomiar: liczba złapanych defektów, PASS/FAIL na CPU‑referencji.

**P4. „Dropout” na plateau: ślepa ocena i filtr negatywów po fakcie.** Źródło: A6.
- Co: dla dwóch kerneli na plateau (MMVQ n=1 Qwen ~780 GB/s; ścieżka warstwy MoE LFM, 416 kerneli/token) świeży
  agent dostaje **tylko** kod, roofline z P2, ATT z P1 i twarde ograniczenia (bitowo, HIP, bez GPU). Nie dostaje sekcji
  „Wyniki negatywne” ani historii. Oddaje top‑5 propozycji z mechanizmem i szacunkiem.
- Main **po fakcie** odsiewa propozycje pokrywające się z negatywami. Do testu idą tylko nowe albo te, które podają
  nowy argument przeciw negatywowi.
- Różnica względem 21 P6(e): tam ograniczenia przechodzą dosłownie, a negatywy jako „ramka”. Tu negatywy celowo
  maskujemy, żeby zmierzyć, czy kotwiczą.
- Zysk: `[SZACUNEK]` 0–2 nowe kierunki. Koszt: 1 sesja agenta, bez GPU. Ryzyko: strata czasu na duplikaty, ale
  filtrowanie jest tanie. Pomiar: ile propozycji przeszło filtr i jaki dały wynik.

**P5. Linia czasu wewnątrz kerneli z ogonem „ostatni blok” i diagnoza „slow mode”.** Źródło: T4.
- Co: port `atrex_timeline.cuh` na HIP (`wall_clock64`, HW_ID1, bufor per blok, flagi overflow i duplikatu) pod
  `GGML_HIP_TIMELINE=1`. Kernele: `norm_router_topk`, `mul_mat_vec_q_conv` (tickety grup), `moe_down_reduce` oraz
  gate+up ekspertów LFM.
- Pytania:
  - (a) ile trwa ogon ticketu i czekanie na ostatni blok (mamy tylko mikrobench ~1 µs, `NOTES.md:358`);
  - (b) rozkład końców bloków per SE/WGP;
  - (c) **czy „slow mode” gate+up (24.3 → 27.2 µs w części procesów, przyczyna nieznana,
    `lfm-decode-round2.md:78-81`) dotyczy wszystkich bloków, czy tylko jednego SE/WGP**. `[WNIOSEK]` Jeśli jednego, to
    raczej rozmieszczenie zasobów lub zegar niż kod.
- Narzut sprawdzać jak w AKA: ABBA+BAAB ze sondami i bez, ≤10%.
- Zysk: pośredni. Wyjaśnienie (c) jest warte ~0.11 ms/token (2.7%) w tych procesach, w których slow mode występuje.
  Koszt: ~1 dzień. Ryzyko: sondy zmieniają zachowanie kernela. Dlatego sonda na blok tylko z lane 0, 2–4 znaczniki na blok.

**P6. (tani test) Kolejność kafli Q w causal FA prefillu: najcięższe pierwsze.** Źródło: zigzag SE (§2c).
- Co: sprawdzić w naszym kernelu FA prefillu (K5, „Q w SRAM”), w jakiej kolejności dispatchowane są kafle Q przy
  masce causal. Jeśli ostatnie dostają najwięcej KV, odwrócić kolejność (LPT) albo przeplatać ciężkie z lekkimi.
- Zysk: `[SZACUNEK]` 0–3% czasu FA przy 30–94k, czyli ≤1–2% prefillu. Na wspólnym L2 Navi31 efekt jest mniejszy niż
  ich +15–20% na MI300X. Koszt: 1–2 h. Ryzyko: kolejność redukcji się nie zmienia (każdy kafel liczy swoje Q), więc
  powinno być bitowo identycznie. Pomiar: llama-bench pp4096 przy d32768/d98304, przeplatane.

**Outside the box.** AKA pokazuje, że po samym agencie nie należy się spodziewać przełomu przy kernelach
„dispatch‑bound”: S zostaje ~0.03, a liczy się tylko różnica wobec produkcji. Nasz główny koszt (granice kerneli w LFM)
jest problemem **między operatorami**, a AKA z założenia optymalizuje jeden operator naraz. Warto więc przenosić z nich
narzędzia pomiaru (P1, P2, P5), a nie pętlę agenta. Granicą optymalizacji powinna być u nas cała warstwa (np. „warstwa
MoE LFM = 1–2 kernele”), z sufitem z P2 jako kryterium stopu.

## 5. Krytyka

- **Brak RDNA.** AMD = CDNA3/CDNA4. Tryb OpenSSH obsługuje tylko „one assigned physical NVIDIA GPU”
  (`design.md:192`). Lista PMC i flagi ATT są pod gfx9 (`profile_kernel.sh:235-245`, `:311-330`), więc na Navi
  część jest błędna (simd‑select) albo nieobsługiwana (`--att-activity`).
- **Wiki niskiej jakości tam, gdzie dotyka RDNA.** Karta „RDNA4 WMMA” podaje gfx1250 (RDNA4 to gfx1200/1201), a
  „treść” to sama ścieżka źródła (`technique-card/amd/rdna4/.../pattern-wmma-wave32-...json`). W kartach z migracji
  `what` == `when`, karty symptomów mają techniki o nazwach „examples” i „caveats”, a wszystkie liczniki `worth.track`
  są zerowe. Ranking „knowledge flywheel” nie jest więc jeszcze napędzany sprzężeniem zwrotnym. Pełne playbooki (np.
  chunk‑GDN) usunięto przy migracji, zostały tylko streszczenia.
- **Słaba statystyka akceptacji.** 2 pary ABBA i próg 0% (`constants.py:37`, `orchestrator/campaign.py:201`)
  promują szum. Wynik to **średnia arytmetyczna przyspieszeń per kształt** (`reference/test_kernel.py:166-170`,
  release notes v0.3.0), która przecenia duże wygrane na małych kształtach. Domyślne `rtol=0.05` w ewaluatorze
  Atrex‑Bench (`reference/atrex_bench_test_kernel.py:375`) jest luźne.
- **Wyniki artykułu to case study**, nie benchmark: 3 operatory × 1 kształt × 1 pomiar (§5.4). Sami autorzy pokazują,
  że wygrana 1.11× z AITER wynika z kształtu niekorzystnego dla AITER (head_dim 72, AITER ma S≈0.36). Liczba „1.55×”
  z README jest niesprawdzalna.
- **Koszt.** Przykład w README zakłada `max-iters 300`. Vanilla Opus zużył 5.67M tokenów wyjścia na 30 operatorów
  (Tab. 6). Ciężka infrastruktura odtwarzania po awarii jest bez znaczenia przy jednej lokalnej karcie.
- **Niezgodne z naszymi regułami**: agent może zmieniać framework w trybie leaderboard, a „production” dopuszcza tylko
  Python DSL. HIP C++ i integracji z ggml nie ma.

## 6. Werdykt

**Średnia (tylko narzędzia pomiarowe).** Kerneli ani wiedzy o RDNA3 brak, a pętla agenta dubluje to, co już opisały
04/06/21. Warte przejęcia są trzy rzeczy:
- działający przepis i parser rocprofv3 ATT (po poprawce flag pod Navi) jako zamiennik martwych PMC;
- sufit pasma dopasowany do rozmiaru wywołania;
- sondy numeryczne i linia czasu wewnątrz kernela.
