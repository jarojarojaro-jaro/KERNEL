# TensorFold (ashhart/TensorFold): jak autor myśli i iteruje, i co z tego przenieść na Qwen3.8-27B na jednym 7900 XTX

Stan: klon z pełną historią w `~/research/TensorFold`, HEAD `0efbd447` (2026-10-12, = tag `v1.0.8`). Repo ma 1560 commitów na `main` (1903 na wszystkich gałęziach), 32 tagi w 18 dni, 552 PR-y i 235 issues. Gałęzie: `python-0.6` (zamrożony silnik Python/MLX 0.2–0.6.6), `zig-preview`, `zig-flashnext` (= main). Nic nie było budowane ani uruchamiane. Ścieżki `plik:linia` są względem korzenia repo przy HEAD, chyba że podano tag lub commit. `#N` oznacza https://github.com/ashhart/TensorFold/issues/N (PR-y mają tę samą numerację). Liczby z naszego setupu pochodzą z `~/qwen-opt/NOTES.md`, `research/v2/roadmap.md` i studium Straty (`research/strata/README.md`). Szacunki oznaczam [INFERENCE].

Raporty cząstkowe z pełnymi cytatami:
- `local://tensorfold-timeline.md`: każdy tag, fazy, przepisania historii, trajektorie 27B i Nemotrona.
- `local://tensorfold-qwen27.md`: silnik dla **naszego modelu** (Qwen3.8-27B): drzewa DFlash2 nad GDN, liczby, wyniki negatywne.
- `local://tensorfold-spec-host.md`: polityka głębokości draftu, rollback stanu, host, prompt cache.
- `local://tensorfold-kernels.md`: kernele (Metal, CUDA, HIP), PR #100 (R9700), trellis, numeryka, dispatch.
- `local://tensorfold-method.md`: metodologia, porównanie punkt po punkcie ze Stratą, 16 lekcji.
- `local://tensorfold-issues.md`: ok. 75 wątków issues/PR z liczbami i wynikiem.

**Najważniejsze w jednym akapicie.** TensorFold i Strata mają podobny cel: szybki, bezstratny decode ze spekulacją. Strata jest silnikiem pod jeden model MoE z offloadem. TensorFold jest kontraktem dokładności („drafted == plain, resumed == fresh, concurrent == solo, chunking nie zmienia bitów”), realizowanym dla 7 rodzin modeli na Metal, CUDA i (przez społeczność) na ROCm. Dla nas są w nim cztery nowe rzeczy:
1. **Weryfikacja na macierzach (WMMA/tensor units), dla której dodatkowe wiersze są prawie darmowe.** Na RDNA4 (R9700) przejście z 12 do 16 wierszy kosztuje +1.2 ms. U nas jedna dodatkowa kolumna kosztuje ok. 1.4 ms.
2. **Drzewa draftów nad Gated DeltaNet działają w produkcji.** Stan węzła drzewa trzyma się w rejestrach, a commit to replay zaakceptowanej ścieżki. To obala wpis „tree drafts: GDN rollback is chain-only” w `roadmap.md:243`.
3. **Rollback GDN przez „lagged state”.** Replay zaakceptowanych wierszy odbywa się w kernelu następnego okna. Działa na trzech backendach, w tym w silniku HIP na gfx1100 (#490).
4. **Głębokość draftu wyceniana kosztem mierzonym przy starcie**, z kalibracją pewności głowicy. Daje +6–7%, a do tego jest udokumentowane, dlaczego tańsze polityki przegrywają.

Na samym modelu 27B TensorFold jest na naszym typie sprzętu wolniejszy od nas:
- natywny HIP na W7800 (gfx1100): 25.8–27.2 tok/s plain (#490);
- R9700 (RDNA4, 640 GB/s) z DFlash2 i drzewami: 95.7 chat / 126 code tok/s przy T=1 (#100).

Ten drugi wynik osiąga karta wolniejsza od naszej o 1/3 pamięciowo, mając ok. 96 tok/s na czacie wobec naszych 88–90. Różnicę robi właśnie płaska szerokość verify.

---

## 1. Czym jest TensorFold: architektura, komponenty, modele, sprzęt

- **Produkt.** Serwer OpenAI/Anthropic (`tensorfold serve`) jako jedna binarka Zig, która sama czyta checkpointy (MLX affine 2–8 bit, NVFP4, EXL3, EXLR8), tokenizuje i odpala kernele Metal lub CUDA. Python i MLX nie są potrzebne w ścieżce decode (`README.md:3-5`, `ZIG-PREVIEW.md:3`). Linia 0.x (Python + MLX + własne kernele Metal; torch/Triton/.cu na CUDA) jest zamrożona na gałęzi `python-0.6`.
- **Rdzeń: „lanes”.** Jeden forward weryfikuje wszystko naraz: drafty MTP, drzewa DFlash2 i kopie z kontekstu (n-gram). Zostają tylko tokeny, które model wyprodukowałby sam (`ZIG-PREVIEW.md:5`). Wspólny „lane core” obsługuje rundy, drafty, „keep” i współbieżne strumienie. Rodzina modelu dostarcza tylko operatory i wagi (`CONTRIBUTING.md:29-31`).
- **Kontrakt dokładności** (`CONTRIBUTING.md:33-46`), weryfikowany narzędziami:
  - wynik z draftami = wynik z `"draft": false`;
  - wznowienie = świeże wykonanie;
  - strumień współbieżny = ten sam strumień solo;
  - wiersze promptu niezależne od podziału na chunki.

  Kernele są „row-invariant”: wiersz ma te same bity niezależnie od tego, ilu wierszy dotyczy wywołanie (1–128). Służą temu split-K ustalony kształtem wagi, sumowanie w stałym porządku i `-ffp-contract=off` (`local://tensorfold-kernels.md` §5).
- **Modele i sprzęt (1.0.8, `README.md:61-69`):**

  | Model | Backend / sprzęt |
  |---|---|
  | Nemotron 3.5 Lightning 30B-A3B (hybryda Mamba-MoE + MTP) | M1–M5; CUDA: GB10, RTX 3090, RTX PRO 6000 |
  | Qwen3.8 Flash Next (GDN-MoE) | M5 Ultra |
  | GLM-5.3-Flash i GLM-5.3 (EXLR8) | dwa M5 Ultra po MCDMA |
  | Qwen3.5-2B | M5 Max |
  | **Qwen3.8-27B** (MLX 4-bit g64 + DFlash2 `z-lab/Qwen3.8-27B-DFlash2`) | Metal: M5 Max i M3 Ultra. W linii Python także GB10, RTX 4090, RTX PRO 6000 i R9700 (PR #100) |

- **27B: geometria jak u nas** (`zig/src/families/qwen27/round_plan.zig:96`):
  - 48 warstw GDN (nk 16, nv 48, dk = dv 128, stan fp32 3 MiB/warstwę);
  - 16 warstw attention 24/4 (GQA 6), head 256;
  - vocab 248,320;
  - MLX 4-bit to 14.4 GB czytane na forward, wobec 17.6 GB w naszym UD-Q4_K_XL.
- **AMD.** W `main` jest tylko szkielet runtime HIP (#463, `zig/kernels/hip/affine.hip` naiwny). Pełny silnik HIP społeczności (#490/#617/#621/#631, gfx1030/gfx1100/gfx1151) jest otwarty. Port PyTorch-ROCm na R9700 (#100) zamknięto bez merge’a, ale jest w nim najciekawszy dla nas kernel (`qmm_rocm.cu`).
- **Funkcje poboczne** (bez wpływu na prędkość):
  - Living Weights / `--slide`: model uczy się faktów do wag checkpointu (`docs/living-weights.md`);
  - kompakcja kontekstu (`--compact-at`);
  - `--learn`: prefiksy promptów na dysku, tylko Mac;
  - „speed-up mode”: jeden model na dwóch Macach.

## 2. Ewolucja wersja po wersji

Pełna tabela 32 tagów jest w `local://tensorfold-timeline.md` §2. Tutaj fazy z liczbami.

| Faza | Tagi (daty) | Co się działo | Zmierzone efekty / uzasadnienie |
|---|---|---|---|
| P0. Prehistoria | do 09-24 | Runtime MoE stronicujący wagi z dysku (`--resident-budget`), wymazany | #1, #2. Notka v0.2.0: „This release is a rewrite”. Nowy root `094f5e4d` |
| P1. Dokładne „lanes” w Pythonie | 0.2.0–0.3.4.1 (09-25..27) | Kontrakt drafted == serial od pierwszego dnia. 27B z DFlash2 i drzewami na M5. CUDA na DGX Spark (0.3.0). Lanes na M1–M4 (0.3.3). Wszystkie modele na lanes, własny `simd_qmm`, zredukowany draft vocab (0.3.4) | 27B na M5 Max: 120–124 short, 189 code (0.2.0). Na Spark 2.7–3.1× vLLM MTP=3 (0.3.0). M3 Ultra 63.9 → 141.3 code (0.3.4). **Odwrót w 0.3.4.1:** prefill „row-exact” był kilka razy wolniejszy (27B 2k 542 → 867 tok/s po powrocie do forwardu MLX na siatce 2048) |
| P2. Szerokość | 0.3.5–0.6.5 (09-27..10-03) | Współbieżność, 6 nowych rodzin, formaty (EXL3, NVFP4, oQ), RTX 40/50, fala PR-ów społeczności | 27B Spark przy 128k: 18.4 → 38.9 tok/s, bo attention czyta chunk kluczy raz na rundę (0.5.0). bf16 zamiast FP8 jako domyślny prompt: KL 0.0031 vs 0.0624 (0.6.0). GDN tree kernel −8…35% (0.6.2). **Głębokość MTP wyceniana kosztem: +6–7%** (0.6.5, `bcb8f01c`) |
| P2′. Port Zig (równolegle) | 09-27..30 | `feat/zig` S. Christiansena na bazie Zig z mlx-serve | 91 commitów, później dołączonych do historii (`f24b5c8f`) |
| P3. Prywatny sprint Zig → preview | 10-03..06 | Jeden command buffer na rundę, GPU-side rounds, test megakernela, speed-up mode | Flash Next 117.8 → 123.2 (`c6d5fd35`), −99 launchy +6% (`3673a760`), GPU-side rounds 142.4 → 144.8 (`4495f918`), **megakernel z grid barrier przegrywa: 4.6–18 µs/fazę vs 4.01 µs relaunch** (`1fbd9ba7`), **adaptacyjna głębokość „landed+1” przegrywa ze stałą 3** (`11ecb46b`) |
| P4. Cutover | 1.0.0 (10-07) | Zig staje się main, Python zamrożony | **27B wykluczony: „paired served decode and cold-prefill measurements remain slower than Python 0.6.6”** (`CHANGELOG.md:203`) |
| P5. Natywna szerokość | 1.0.1–1.0.8 (10-07..12) | 27B natywnie (1.0.3, `34c44245`), Ampere sm_86, stany promptu w dowolnym wierszu, współbieżny 27B i drafty przy T>0 (1.0.6), EXLR8 GLM-5.3 (1.0.8) | 27B na M5 Max: 64–77 proza / 151 code, plain 18–19.5 (1.0.3). Edycja/regeneracja: 10.9 → 1.7 s (1.0.5). Pamięć 27B 44.2 → 26.5 GiB przy tej samej prędkości (1.0.8). Prefill 27B wciąż ok. połowy mlx_lm (252 vs 441 tok/s przy 8k, M3 Ultra) |

**Trajektoria 27B (nasz model), od najlepszych wyników w górę:**
- R9700 (#100): 98 tok/s (pierwsze WMMA) → 128 tok/s (persistent WMMA decode, fused gate/up, cięcia launchy) przy 4k. Pierwsza działająca wersja (Triton) miała 44 tok/s.
- M5 Ultra (#578): greedy code 199–215, chat 142–144 tok/s.
- GB10 (240 GB/s): 49.6 / 45.8 → 57.8 / 50.0 tok/s.

Akceptacja: na czacie ląduje 3.5–3.95 tokenu na rundę, przy suficie 5.6–6.1 wynikającym z top-16 kandydatów DFlash2 (v0.3.4). Autor sam pisze, że ograniczeniem jest drafter, nie verify.

**Odwroty i regresje** (`local://tensorfold-timeline.md` §5):
- row-exact prefill (0.3.4 → 0.3.4.1);
- FP8 jako domyślny prompt (do 0.6.0);
- polityka eksmisji cofnięta za brak „no-slower gate” (`a5f518b4`);
- „copies zamiast drzew” dla samotnego strumienia 27B (1.0.6 → 1.0.7: 138 → 146 tok/s, M3 Ultra);
- −4.5% na greedy code M1–M4 naprawiane przez dwie wersje;
- pierwszy projekt Living Weights zastąpiony w 1.0.7.

W 1560 commitach są tylko 2 reverty.

**Rytm pracy:**
- ok. 87 commitów dziennie; ashhart jest autorem 70% i committerem 91%;
- 201 z 744 kolejnych commitów dzieli mniej niż minuta;
- w repo jest runbook dla agentów AI;
- reguła usuwania trailerów co-author;
- 144 wątki wprost deklarują Claude/Claude Code.

PR-y społeczności są rebase’owane na „kandydata” wydania i odnotowywane pustym merge’em („Merge #N's head: the same change”, 35 razy). [INFERENCE] Jak u Straty, to workflow wielu agentów. Tempo jest możliwe dzięki bramce bitowej: każda zmiana albo daje te same tokeny, albo nie wchodzi.

## 3. Metodologia autora i porównanie ze Stratą

Szczegóły i cytaty są w `local://tensorfold-method.md`. Poniżej to, czym TensorFold różni się od Straty. Wspólne wnioski (bramka bitowa, przeplatane A/B, „mikrobench nie wybiera konfiguracji”, negatywy jako dokumentacja) pomijam.

1. **Kontrakt zamiast tolerancji.** Strata dopuszcza zmianę numeryki, gdy teacher-forced KL nie przekracza podłogi szumu. TensorFold praktycznie nie dopuszcza żadnej:
   - odrzucone int8 KV, mimo −6% / −13% czasu rundy przy 90k / 242k (#247);
   - odrzucona ścieżka Q8_1 dla promptu (#144);
   - odrzucone fp16 P·V (#457);
   - FP8 prompt tylko opt-in, bo PPL +4.1% vs +0.03% dla bf16 (#100).

   Przy zmianie kolejności redukcji wymagana jest referencja FP64 per klasa projekcji, z raportem **najgorszej kolumny**, bo „średnia nie może ukryć gorszej kolumny” (`CONTRIBUTING.md:41-44`). W #457 zmiana była lepsza w L2, ale pogarszała 1.8–5.8% elementów, więc odpadła. Porównanie robi się względem podłogi „dokładny wynik zaokrąglony do bf16”.
2. **Cztery osie poprawności, każda z narzędziem:**
   - `bench_concurrent.py --alone --serial`;
   - `tf-cuda-test resume`: stany w wierszach 1, 7, 1500, 2047, 2048, 2049;
   - test chunk-invariance: 17 wzorców cięcia, bajt w bajt (#670);
   - klasyfikator near-tie (`tools/zig/qwen27_margins.py:13-26`). Rozbieżność jest remisem tylko wtedy, gdy wygrywa ta sama para tokenów i oba marginesy są ≤ 1 odstęp bf16. W każdym innym przypadku to bug.
3. **Bramka wydania ABBA z regułą ilorazów krzyżowych** (`tools/zig/gate_cells.py:17-18`, `gate_judge.py:127-148`).
   - „Wolniej” tylko wtedy, gdy każdy iloraz krzyżowy jest < 1, a średnia < 0.98.
   - Jeśli własne wizyty jednego ramienia różnią się o > 5%, komórka **nie dostaje werdyktu**.
   - Sama bramka jest testowana „podłożonym błędem”: binarka z jednym zmienionym tokenem albo spowolniona musi przez nią nie przejść (`gate_plant.py:1`).
   - Strata miała kontrolę pozytywną i A/A, ale nie miała reguły braku werdyktu ani podkładania błędów.
4. **Hipotezy przez kernele „celowo błędne”** (#527, M5 Ultra, 27B). Najpierw rozkład kroku: GPU, kodowanie na CPU i **czas hosta po zakończeniu command buffera**, który okazał się 2.3 ms kopii stanu GDN. Potem trzy ablacje:
   - te same loady bez matematyki: 1080 GB/s wobec 700 realnych;
   - skale zastąpione stałymi: −3%;
   - MMA zastąpione zwykłym fma: 65.9 → 31.6 µs.

   Wniosek: kernel jest ograniczony jednostką tensorową, więc przestawianie pętli nic nie da. Strata miała spis bajtów i rozkład okna, ale nie miała ablacji typu speed-of-light.
5. **Polityka oparta na zmierzonych kosztach, z diagnozą porażek** (#250, #136):
   - tabele kosztów: najszybszy z 7 pomiarów, ponowny pomiar przy spadkach > 3% i dryfie > 15%, cache per build/GPU/driver;
   - uzasadnienie min: „Noise only adds time” (`49dad8b9`);
   - jeden start 3090 zapisał 0.61 ms dla kroku, który ma 0.34 ms (`CHANGELOG.md:159`).

   Ważne, bo zgodne z naszym nieudanym p-cum: polityki wyceniane kosztem przegrały na Flash Next, ponieważ żywa runda kosztowała 5.0 ms/draft wobec 3.55 ms w tabeli (+40%). Iloczyn pewności głowicy zawyżał akceptację ok. 2.5×.
6. **Pułapki pomiarowe, których Strata nie miała** (`local://tensorfold-method.md` §3):
   - regresja „−24%” była w rzeczywistości ponownym przechwytywaniem grafów, widocznym dopiero przy liczbie różnych promptów większej niż liczba slotów (#317);
   - tempo serwera vs wall clock klienta (#317);
   - `seconds` zawierało prefill (#588);
   - rampa zegara GPU po kompilacji na CPU (#527);
   - wyścig widoczny tylko pod obciążeniem GPU: 5/10 różnych odpowiedzi na gfx1150 (#490);
   - biblioteka wybierająca kernel po liczbie wierszy (#437);
   - „procent akceptacji” mylący, gdy silnik sam zmienia liczbę draftów (#280);
   - harness, który porównywał brakujące hashe jako równe (#485).
7. **Gdzie lądują liczby.**
   - Strata trzyma pomiary w komentarzach kodu.
   - TensorFold zabrania tego (`CONTRIBUTING.md:79-80`: pliki ≤ 600 linii, komentarze jednoliniowe). Liczby trafiają do „receipts” w PR-ach, do recept i do CHANGELOG, gdzie każdy wpis jest akapitem pomiarowym z sekcją „Known issues”.
   - Liczba od kontrybutora jest cytowana jako jego, dopóki autor sam jej nie powtórzy („We have not re-run them”, 14 razy).
8. **Profil myślenia.**
   - **Strata:** najpierw system, potem kernele; jeden model; zmiany zawężane do architektury przez tabele per-arch.
   - **TensorFold:** najpierw kontrakt, potem szerokość (rodziny i sprzęt), na końcu prędkość. Cel jest jawny: „każda komórka co najmniej 2× standardu” (mlx_lm/vLLM; v0.3.4), potem „3×” (0.3.6).
   - Zmiana jest zawężana do sprzętu, na którym ją zmierzono: szersze okna kopii tylko na GB10, „bo szersze okno trzeba opłacić zmierzonym kosztem verify na każdej innej karcie” (#115).
   - Jedna ścieżka na model. Szybsze duplikaty silnika są zamykane, a ich pomysł przenoszony do ścieżki kanonicznej (#520/#528/#568).

## 4. Katalog technik (mechanizm → zmierzony zysk → przenośność)

### 4a. Weryfikacja i matmul (szczegóły: `local://tensorfold-kernels.md` §1, §3, §4)
| Technika | Mechanizm | Zysk (sprzęt) | Przenośne? | Źródło |
|---|---|---|---|---|
| **Verify matmul na macierzach dla 1–32 wierszy** | Wagi z globalnej pamięci prosto do fragmentów (bez LDS), aktywacje ≤16/32 wierszy w LDS, jeden odczyt wagi na wszystkie wiersze. 1 wiersz idzie tą samą drogą (row-invariance) | R9700: 12 wierszy, matmule 29 z 37 ms przy ok. 80% z 639 GB/s; 12 → 16 wierszy **+1.2 ms**. M5 Ultra: 1 → 16 wierszy 21.08 → 23.40 ms (#661). GB10 EXL3: 1 → 16 wierszy ≤ 5% | **Tak (WMMA gfx11)**, z zastrzeżeniami z §5 | `refs/pr/100:.../qmm_rocm.cu:139-366`, #100, #661 |
| Persistent split-K bez launchu redukcji | Split ustalony kształtem wagi, ostatni blok (atomic counter + fence) sumuje plasterki w kolejności | Część drogi 98 → 128 tok/s (R9700) | Tak | `qmm_rocm.cu:284-309,355-366` |
| Prefetch „slab ahead” plus non-temporal load wag | Następny slab ładowany przed bieżącymi MMA, także na granicy itemów | M5 Ultra: projekcje 3.32 → 2.70 ms, **96% streamingu**. GB10 +10–40% | Tak | `244989a3`, `38235a9c` |
| Reguła occupancy kafla streamującego | Kolumny na lane: najszersze z `cols·bits ≤ 32` przy ≥ 3000 wave’ach | **W7800 gfx1100:** gate_up 9B 8-bit 514 → ok. 681 GB/s, bez zmiany bitów | Tak (K1) | `286840ac` (#490) |
| Wąskie macierze: wiersz na simdgroup, split-K „sets” | Gdy jobów jest mniej niż rdzeni | router 0.146 → 0.069 ms; gate/up 1.24–1.84× | Tak | `22f41e22`, `9b1aab43`, `5e449c7b` |
| Stacked projekcje jako widoki | `[qkv\|z\|b\|a]`, `[q\|k\|v]`, `[gate\|up]` jako jeden matmul, członkowie jako strided views, glue bierze row-stride zamiast kopii | −176 launchy na rundę, łącznie 1007 → 943; matmule 30.3 → 29.2 ms (R9700) | Tak (≈ pair launch Straty) | #100 |
| Etapy pipeline’u od linii 128 B | Wyrównanie stage’y FP8 lane matmula | verify 12 wierszy 103 → 85 ms (GB10) | Ogólna zasada | `docs/recipes/qwen3.8-27b.md:94-95` |
| Bias × suma grupy w fp32 | Zamiast bf16 | błąd prompt-GEMM 3.8e-3 → 1.1e-6 rms | Tak (S1) | `db78ea7b` |

### 4b. GDN / stan rekurencyjny (`local://tensorfold-qwen27.md` §1.4, `local://tensorfold-spec-host.md` §3)
| Technika | Mechanizm | Zysk | Przenośne? | Źródło |
|---|---|---|---|---|
| **Drzewo nad GDN, stany węzłów w rejestrach** | ≤ 16 węzłów × float4 na lane (dk 128 = 32 lane × 4); węzeł bierze stan rodzica przez jednolity `switch(parents[i])` i nic nie pisze poza wyjściem; powyżej 16 węzłów jest slab snapshotów | Drzewa 16-wierszowe kosztują tyle co łańcuch; drzewo vs łańcuch **+21–34% tok/s** (M5 Max, Python 0.2), offline code 4.35 → 5.57 tok/przebieg | Tak (64 VGPR więcej na lane) | `zig/kernels/metal/core/deltanet.metal:139-191` |
| Drzewo na CUDA: harmonogram DFS/poziomami | Tryplety `(node, source, dest)`, ≤ 32 sloty w shared memory, zwalniane po ostatnim dziecku | „GDN tree kernel −8…35%” (0.6.2) | Tak | `py:.../cuda/kernels/gdn.py:23-74`, `zig/kernels/cuda/gdn.cu:133-304` |
| **„Lagged state”: replay w następnym oknie** | Kernel okna najpierw odtwarza `pk` zaakceptowanych wierszy poprzedniego okna z buforów per-wiersz (double-buffered „parity”), zapisuje stan raz (w wierszu pk−1), potem liczy nowe wiersze w rejestrach. Commit na hoście to `pos += keep; prev_keep = keep` | Baza całego Nemotrona CUDA; Flash Next `FZ_GDN=2` 166.4 → 174.5 tok/s (M5 Ultra, z fz_lane); **HIP gfx1100: „te same bity za ok. 2% pamięci”** | **Tak (nasze S4)** | `nemotron_mamba.cu:20-155`, `cuda_engine.zig:488-492`, `244989a3`, `170df51e` |
| Commit ścieżki jednym launchem dla wszystkich warstw | Tablica wskaźników | 3.6 → 2.3 ms na rundę (dwa Sparki) | Tak | `gdn.cu:266-304` |
| Jeden butterfly dla dwóch redukcji | `q·S(i)` i `k·S(i+1)` w jednym `spread_sum<2R>`; wejścia węzła i+1 ładowane w trakcie i | Część z −8…35% | Tak (≈ TSUM Straty) | `gdn.cu:187-248` |
| Scan in-place przy pełnej akceptacji | Brak kopii 288 MiB/token stanu „publish” | **+4.0% (2k), +2.6% (16k)** plain, M5 Max, 27B | Tak (już mamy #30139/A4) | #711 |
| Conv tail z indeksów przodków | Bez okna conv per węzeł | — | Tak | `deltanet.metal:368-389` |
| Stan w dowolnym wierszu bez dodatkowego przebiegu promptu | Scan zapisuje stan w oznaczonym wierszu z rejestrów (druga instancja kernela, ≤ 16 wierszy zapisu) | Tury 2–5 startują 1.7–2.8× szybciej (Nemotron) | Tak | `3f4850c0`, #670 |

### 4c. Spekulacja, host, sampling (`local://tensorfold-spec-host.md` §2, §4)
| Technika | Mechanizm | Zysk | Źródło |
|---|---|---|---|
| **Głębokość MTP wyceniana kosztem, w trakcie rundy** | `keep(k)`: `run² ≥ rate·row(k)`; `more(k)`: `run² ≥ rate·(row(k+1)+level)`; `run` = iloczyn top-1 pewności; potęga 2 koryguje nadmierną pewność głowicy; `rate` = EMA tokenów na **modelowane** ms; koszty z tabeli startowej (PAVA, wklęsłe) | **+6% (1 i 2 Sparki), +7% (RTX PRO 6000)** vs cap 3 / pewność 0.2 | `zig/src/core/draft_depth.zig:14-91`, `bcb8f01c` |
| Porażki tańszych polityk | EMA między rundami −4…7% na czacie; look-ahead 0.964; koszt bez kalibracji „przedraftowuje”; „landed+1” 137.6–139.9 vs 143.1 przy stałej 3 | dokumentacja | #250, #136, `11ecb46b` |
| Drzewo DFlash2 i wybór szerokości | Best-first 15 węzłów, ≤ 4 dzieci, top-16 na głębokość plus niskorangowy „edge” rodzic→dziecko; szansa węzła z online kubełków log-prob (0.5 nat) z priorytetem e^own; szerokość maksymalizuje `E[tok]/(cost(w)+overhead)` | 4.0–5.2 tok/rundę przy 12 wierszach (GB10); R9700 chat 95.7 / code 126 przy T=1 | `selector.zig:6,43-111`, `qwen27_landing.zig:4-24`, `allocate.zig:8-47` |
| Drzewa MTP: zmierzone i odrzucone | Runner-up na poziomie 1 trafia w **56–88%** pudeł (Strata: 0/14), ale łańcuchy wygrywają: proza 333 vs top-2×2 295 vs top-4×8 154 tok/s (3090) | negatyw | `cacde04e` |
| MTP jako druga opinia dla DFlash2 | Zależne wywołanie przed verify | akceptacja +3–12%, ale tok/s **−6…9%** | #113 |
| **Keyed Gumbel jako domyślny sampler** | `argmax(logit/T − log(−log u(seed,pos,id)))`; drafter dodaje ten sam szum (DFlash2 ×0.7; Nemotron τ = 0.6·T) | Sampled ≈ greedy: R9700 code 126.1 (T=1) vs 117.9 (greedy); 3090 352.5 vs 372.5 | `lanes/gpu_rule.zig:83-92`, `selector.zig:56` |
| Akceptacja i commit na urządzeniu, commit za następnym draftem | Matcher kernel → keep → replay GDN → kompakcja KV → taps → wiersz głowicy w jednym command bufferze, jeden readback; commit po picks, czekanie dopiero przed następnym verify | **+3.7% short, +12.0% przy 16k** (M5 Max CLI, 5/5 par) | `generation.zig:84-109`, `4f5f387b`, #713 |
| Dedykowana pętla dla jednego strumienia | Zamiast ogólnego schedulera | +3.5–7% (GB10) | `efcf970e` |
| Rundy w całości na GPU (Metal) | Host „czyta z tyłu”, rundy kolejkowane 2 do przodu, zatrzymanie draftu zerowaniem liczników indirect dispatch | GPU-side rounds 142.4 → 144.8 | `4495f918`, `gpu_round.zig:48-62` |
| Grafy dla okien maskowanych (grammar) | Przechwycenie przy pierwszym użyciu per liczba wierszy, bity maski pod stałym adresem | `"draft": false` +4.4% | #660 |
| Budżet hosta (3090) | Runda Nemotrona: 7.1 ms verify + 1.0 ms MTP + **0.3 ms host** | punkt odniesienia | `3cda8800` |

### 4d. Prompt cache, prefill, attention
| Technika | Zysk | Źródło |
|---|---|---|
| Stan zapisywany przy starcie wiadomości użytkownika oraz **512/2048 tokenów przed końcem długiego system promptu**; stan zawiera K/V tylko do długości promptu, w stronach 2 MiB | 62 MiB vs 543.7 MiB na stan; 258 stanów zamiast 30 w 16 GiB | `CHANGELOG.md:7-8` |
| **Background warm pass** po odpowiedzi (prefill historii plus otwarcia następnej tury, ustępuje nowym żądaniom) | TTFT **−48…57%** przy przerwie ≥ 0.15 s | #723, `924104e2` |
| Stan „rewind” tuż przed ostatnią wiadomością użytkownika | edycja/regeneracja 10.9 → 1.7 s (M3 Ultra, 27B) | `CHANGELOG.md:118` |
| Głowica MTP chłonie wiersze promptu **tylko jako K/V** (embed + normy + eh_proj + QKV, bez attention/o_proj/MLP/head) | brak izolowanej liczby | `cuda_mtp.zig:270-293` |
| Attention: chunk kluczy czytany raz na wszystkie wiersze rundy, loady 16 B | 27B Spark 128k: 18.4 → 38.9 tok/s | `CHANGELOG.md:379-381` |
| WMMA tree/prompt attention (R9700): blok na chunk 512 kluczy × głowę KV; `S^T = K·Q^T`, więc P jest od razu operandem A dla P·V | 120k: 1908 → 1324 µs/warstwę; prompt attention 78 vs 48.9 TFLOPS | #100 |
| Higiena kerneli hipcc: 32-bitowa arytmetyka indeksów, presja rejestrów, kolejność loadów | −6.6% ms/rundę przy 61k, −10.5% przy 123k (R9700) | #406 |

### 4e. Specyficzne dla Metal/MLX (nie przenosić)
- Tensor units M5 i ich ograniczenie liczbą instrukcji (8×8 MMA w 7/8 puste przy 1 wierszu, #527).
- ANE dzieli MLP promptu (`qwen27/mlp_ane.metal`).
- Serial encoders, ICB z jobami pisanymi przez GPU.
- Keep-warm residency sets.
- Obejścia kompilacji Metal 4.1.
- MCDMA i QoS wątków dla dwóch Maców.
- Trellis EXL3/EXLR8: kernele tylko CUDA/Metal. Na GB10 3.0 bpw daje −30% bajtów przy tylko −11% czasu rundy, a akceptacja czatu spada z 4.2 do 3.0–3.3, więc **czat jest wolniejszy** (`docs/recipes/qwen3.8-27b.md:118-133`).

## 5. Transfer na nasz setup (gęsty 27B hybrid, cały na jednym 7900 XTX, llama.cpp HIP)

**Arytmetyka bazowa** (jak w studium Straty):
- Krok 35.7 ms przy 3.16 tok/krok, więc **1 ms/krok ≈ +2.9% t/s**.
- Verify trwa ok. 31 ms: matvec ok. 25 ms przy ok. 700 GB/s i 5 kolumnach, przerwy ok. 3.2 ms (972 kernele).
- Poza verify zostaje ok. 4.7 ms. Według arytmetyki Straty składa się na to:
  - łańcuch draftu MTP: 4 przebiegi × ok. 590 MiB wag Q6_K, czyli ok. 2.4 GB/krok i **ok. 3–3.5 ms**;
  - host, sampling i catch-up: **ok. 1–1.5 ms** [INFERENCE].
- Koszt dodatkowej kolumny verify to ok. 1.4 ms (hipoteza roadmap B1, niezmierzona). Klif MMQ zaczyna się od 9 kolumn (`NOTES.md:159`).

**Sprawdzone w naszym forku na potrzeby tej analizy:**
- `ggml/src/ggml-cuda/gated_delta_net.cu:183-195`: przy `keep_rs_t` kernel GDN zapisuje snapshot stanu 3 MiB na token okna i na warstwę. Przy T=5 to 48 × 5 × 3 MiB = 720 MiB zapisu na verify.
- `src/models/qwen35.cpp:568-657`: przebieg MTP bez trybu chain (prompt i catch-up) liczy pełną warstwę (attention, `wo`, FFN) dla wszystkich wierszy. Przycinana jest tylko głowica (`inp_out_ids`, :752).

### Pomiary decyzyjne przed implementacją (zero kodu albo minimalny kod; GPU należy do Main)
1. **Krzywa szerokości verify:** ms/krok przy 5/6/8/9/12/16 kolumnach, min z ≥ 7 pomiarów, z ponownym pomiarem outlierów (lekcja `CHANGELOG.md:159`). Rozstrzyga #2 i #5–#7.
2. **Timeline rocprofv3 między grafami:** koniec verify → start draftu → start verify. Daje kubełek „host po zakończeniu GPU” (#527), który rozstrzyga #3.
3. **`keep_rs_t` on/off przy T=5:** ile kosztują zapisy snapshotów. Rozstrzyga #1.
4. **Offline z logów MTP:** P(cel = 2. kandydat MTP | pierwsze pudło). Strata: 0/14, Nemotron: 56–88%. Rozstrzyga #8.
5. **Mikrobench prototypu WMMA-iu8:** Q4_K 17408×5120 przy 1/5/8/16 kolumnach, z rotacją kopii wag > 96 MB IC, a potem weryfikacja w silniku przez rocprofv3. Go, jeśli 16 kolumn ≥ 650 GB/s.

### Ranking (wartość/wysiłek)

| # | Pomysł (źródło w TensorFold) | Dlaczego pasuje / nie pasuje | Oczekiwany zysk (arytmetyka) | Wysiłek | Ryzyko | Gdzie w naszym forku | Styk z planem; zmiana priorytetu |
|---|---|---|---|---|---|---|---|
| **1** | **S4 w formie „lagged state”**: replay `pk` zaakceptowanych wierszy na początku kernela GDN następnego verify, z buforów per-wiersz (q/k/v/g/β po conv i wejście conv, ok. 20 KB/wiersz/warstwę), indeksowany **ścieżką `kept_rows`**, nie licznikiem (`nemotron_mamba.cu:83-155`, `gdn.cu:159-180`, `170df51e`) | Ta sama geometria GDN (16/48/128). Działa już na gfx1100 w HIP (#490). Usuwa nasze 720 MiB zapisów snapshotów na verify. Host-commit staje się dwiema liczbami, więc nie ma rollbacku na hoście | Zapis 720 → 144 MiB, czyli −576 MiB ≈ **−0.6…0.75 ms → +1.7–2.2%** (część może pochłonąć IC). Ważniejsze, że to warunek wstępny dla #3, #5, #8 i #9 | wysoki: `n_rs_seq` / seq_rm / checkpointy w llama-memory-recurrent, „pending window” zamiast snapshotów; checkpoint promptu musi go spłukać | średnie | `gated_delta_net.cu`, `ssm-conv.cu`, `llama-memory-recurrent.cpp`/`-hybrid.cpp`, builder qwen35, `server-context.cpp` (spec_ckpt) | **S4 / B11: podnieść priorytet.** Strata podała pomysł, TensorFold pokazuje go w produkcji na 3 backendach i uzależnia od niego drzewa i szerokie okna |
| **2** | **K4 przeformułowane: „płaska szerokość”.** Kernel WMMA-iu8 dla 6–16 kolumn: wave ma 16 wierszy wyjścia; wagi globalnie → VGPR → fragment int8 (bez LDS dla wag); q8_1 ≤ 16 kolumn w LDS; persistent grid; split-K ustalony kształtem i składany przez ostatni blok; prefetch slabu; loady non-temporal (`slc`) (`qmm_rocm.cu:139-366`) | Na RDNA4 12 → 16 wierszy kosztuje 0.3 ms/wiersz. U nas ok. 1.4 ms/kolumnę plus klif MMQ. Zastrzeżenia [INFERENCE]: na RDNA3 iu8 WMMA ma ten sam szczyt co `v_dot4` (ok. 123 TOPS), więc zysk to oszczędność rejestrów (akumulator 16×16 = 8 VGPR) i liczby instrukcji, nie przepustowość. Operandy gfx11 są replikowane w połowach wave’a. **Brak dodatniego dowodu na gfx1100**: w #490 macierze on/off dają < 5% w wolnym silniku | Przy 5 kolumnach, jeśli dojdzie do ok. 80% z 960: 25 → 22.9 ms, **−2.1 ms (+6%)** [INFERENCE]. Główna wartość: nachylenie 1.4 → ok. 0.3–0.5 ms/kolumnę, co odblokowuje #5, #8 i #9 (R9700 16 vs 12 wierszy: code +13–19%, proza −9% bez reguły #5) | bardzo wysoki: szablon na każdy typ (Q4_K, Q5_K, Q6_K, IQ4_XS, Q8_0) plus dispatcher | średnie (VGPR, unpack Q6_K/IQ4_XS) | nowy `mmvq-wmma.cu` albo specjalizacja small-N w `mmq.cuh`, dispatch w `ggml_cuda_mul_mat` dla `ne11 ∈ [6,16]` | **K4 + K1.** K4 powinno najpierw obniżyć nachylenie (pomiar 1 i 5), a dopiero potem poszerzać okno |
| **3** | **Pętla spekulacji bez synchronizacji hosta, etapami:** (a) rozbić host gap (pomiar 2); (b) przy T=0 argmax/porównanie draftów i `n_accept` na GPU, graf łańcucha MTP czyta `n_accept` i wiersz h z pamięci urządzenia (`get_rows` z indeksem na GPU), host czyta wynik z opóźnieniem; (c) przy T>0 keyed Gumbel (`gpu_rule.zig:83-92`) jako deterministyczny sampler na GPU, który daje to samo przy T>0; (d) z #1 rollback też jest wartością na urządzeniu (`generation.zig:84-109`, `4f5f387b`, `efcf970e`) | Benchmark TensorFold: host Nemotrona na 3090 to 0.3 ms/rundę; samotna pętla +3.5–7%; commit za draftem +3.7% (short) / +12% (16k). U nas host plus sampling ok. 1–1.5 ms/krok [INFERENCE]. `-bs` (sampling na GPU) samo nic nie dało (`NOTES.md:232`), bo nie usuwa round-tripu. HIP nie ma węzłów warunkowych (roadmap B3), więc indeksy muszą być danymi, nie sterowaniem | **−0.7…1.3 ms → +2–4%** [INFERENCE]; więcej przy długim kontekście, gdzie host buduje maskę KQ (roadmap A10.2: 1–3 ms przy 94k), o ile maska powstaje na GPU z `pos` | wysoki (etap b: średni) | niskie dla T=0, średnie dla T>0 (kary/grammar) | `server-context.cpp` (pętla spec), `common/speculative.cpp`, `qwen35.cpp` graph_mtp (wejście `n_accept`), `llama-kv-cache.cpp` (maska) | **K3 / A10:** konkretny cel „host ≤ 0.5 ms/krok” |
| **4** | **S2 ma dodatkowe wsparcie:** drafter w 4 bitach przy „tej samej akceptacji” (DFlash2: Mac 12.5 → 7.5 ms/blok, GB10 19.5 → 9.6 ms/rundę; `v0.3.3` recipe). TensorFold domyślnie trzyma głowice MTP w 4 bitach (Nemotron `mtp-4bit.safetensors`, NVFP4 → affine-4 przy ładowaniu `5f971417`) | Nasz draft to ok. 10% kroku (ok. 3–3.5 ms, ograniczony odczytem wag Q6_K). Zastrzeżenie: TensorFold **nie publikuje A/B akceptacji 4-bit vs bf16 dla MTP** | Jak u Straty: 590 → ok. 405 MiB/przebieg, **−1.0 ms → +3%** | niski–średni | niskie | ładowanie `blk.64.*` i `draft_head` | **S2: zostaje wysoko**, z niezależnym potwierdzeniem |
| **5** | **Reguła głębokości wyceniana kosztem**: `keep(k)`/`more(k)` z `run²` (`draft_depth.zig:53-91`), tabela kosztów kolumna/poziom przy starcie (min z 7, PAVA, dryf 15%, cache per build), `rate` z modelowanych ms | Wyjaśnia nasz nieudany p-cum (`NOTES.md:179`): bez potęgi 2 i bez cen. Przy naszych cenach (kolumna 1.4 ms + poziom ok. 0.85 ms) i rate = 3.16/35.7 = 0.0885 tok/ms kolejna głębokość wymaga Πp ≥ ok. 0.45; łańcuch idzie głęboko tylko na kodzie | Teraz: mieszanka 0…+2% (zbiera ok. +1.4% z n=5 na kodzie bez strat na czacie; `NOTES.md:249`: n=3/4/5 = 85.2/86.4/87.6). Po #2 i #4 (kolumna ok. 0.4, poziom ok. 0.6) próg spada do Πp ≥ 0.3, code/edycje **+10–20%** [INFERENCE] | niski (ok. 100 LOC + tabela) | niskie (bezstratne); średnie ryzyko złej wyceny: sprawdzać tabelę na żywych rundach (#250: +40%) | `common/speculative.cpp`, graf łańcucha MTP (n_max 6–7, wynik obcinany per krok) | **K4:** to włącznik, który usuwa stratę −9% na prozie przy szerokich oknach |
| **6** | **Prompt cache, polityka:** (a) background warm pass po odpowiedzi (#723: TTFT −48…57%); (b) stan „rewind” przed ostatnią wiadomością użytkownika (10.9 → 1.7 s przy edycji/regeneracji); (c) marki 512/2048 przed końcem długiego system promptu; (d) stan o rozmiarze promptu, nie okna | Nasz A1 już działa (`NOTES.md:222-229`: follow-up 0.7 s). Nowe są (a) i (b). Szablony Qwen usuwają `<think>` z historii, więc po każdej odpowiedzi z myśleniem następna tura re-prefilluje odpowiedź. (a) chowa ten koszt w czasie czytania przez użytkownika | Agent/czat z thinking: TTFT −0.5…4 s na turę (2–4k tokenów przy 660–910 t/s) [INFERENCE]; decode 0 | średni (zadanie w tle w idle slocie, ustępuje nowemu żądaniu) | niskie | `server-context.cpp` (checkpointy, idle task) | A1 / A10.3 |
| **7** | **MTP chłonie prompt jako K/V** (`cuda_mtp.zig:270-293`): dla wierszy promptu tylko embed + normy + eh_proj + attn_norm + QKV + zapis KV; pełna warstwa tylko dla ostatniego wiersza | Sprawdzone: u nas `build_pass` liczy attention, `wo` i FFN dla wszystkich wierszy promptu (`qwen35.cpp:568-657`). Przy decode nic to nie da, bo odczyt wag jest i tak dla ostatniego wiersza | Prefill: FFN + `wo` warstwy MTP to ok. 1.2% FLOP-ów matmul trunku; attention MTP przy 94k to ok. 1/17 z 26% udziału FA, czyli ok. 1.5%. Razem **+1…3% prefillu** (więcej przy długim kontekście) [INFERENCE] | niski–średni (wariant grafu z `n_outputs`-zależnym przycięciem przed attention) | niskie (wyjście bez zmian) | `qwen35.cpp` graph_mtp, hook promptu w `speculative.cpp` | K5 / A10.3b |
| **8** | **Drzewa nad GDN** (po #1 i #2): stany węzłów w rejestrach (`deltanet.metal:139-191`), maska drzewa w FA, commit przez replay ścieżki. Warianty: (a) boczne liście MTP (2. kandydat na każdej głębokości, bez dodatkowych przebiegów MTP, SLOTS ≤ 1); (b) drzewo DFlash2 tylko dla EN/code | Obala nasz wpis „GDN chain-only”. **Ale dziś się nie opłaca:** 16-wierszowe drzewo to +11 kolumn × 1.4 = +15.4 ms (+43%), wymaga ≥ 1.43× tokenów, a TensorFold ma 1.28×. Dowody dla MTP są sprzeczne (Strata 0/14, Nemotron 56–88% i mimo to łańcuchy wygrywają) | Po #2 (0.4 ms/kolumnę): (a) **+2–3%** przy P(2. = cel \| pudło) > 0.3; (b) EN code **+15–27%** [INFERENCE], PL strata, potrzebny routing | bardzo wysoki | wysokie | `gated_delta_net.cu` (wariant drzewa), `fattn-kvq` (maska drzewa), speculative/server | Nowy pomysł (B/K4 faza 2); poprawić `roadmap.md:243` |
| **9** | **Okna kopii rosnące 16 → 128 przy pełnych trafieniach** (n-gram, warunek ≥ 8 zgodnych tokenów) | Nasz A9 odrzucił długie n-gramy przez checkpointy hosta (`roadmap.md:244`, ok. 151 MB). #1 je usuwa, #2 tanio je weryfikuje | Edycje kodu i cytaty: TensorFold GB10 144 → 489–501 tok/s (3.4×, #115), Flash Next 92 → 341 (#319). U nas kilkukrotnie na turach „kopiujących”, czat 0 | średni (po #1/#2) | niskie | `common/ngram-*`, `speculative.cpp` | A9 |
| **10** | **Drobne kernele (K2):** (a) bramka wyjściowa attention w combine FA (−16 kerneli/krok); (b) wspólny butterfly q·S/k·S i prefetch wejść w GDN (`gdn.cu:187-248`); (c) wąskie macierze: wiersz na wave / split-K „sets” (k/v 1024 wiersze, małe projekcje MTP); (d) 32-bitowe indeksy i audyt VGPR w `fattn-kvq` (#406) | Te same wzorce co nasza fuzja; (d) jest nowe dla długiego kontekstu | (a) ok. 0.1 ms; (b) −0.2…0.4 ms; (c) −0.1…0.3 ms; razem **+1–2%** krótki kontekst; (d) **+1.5–3% przy 94k** [INFERENCE: R9700 −6.6/−10.5% rundy przy 61k/123k] | niski każde | niskie | `fattn-kvq`, `gated_delta_net.cu`, `mmvq.cu` | K2 |
| **11** | **K1: metoda i dwie techniki:** (a) kernele ablacyjne „speed-of-light” (#527); (b) mianownik = zmierzony streaming read, nie 960; (c) explicit double-buffer wag w MMVQ; (d) reguła occupancy `cols·bits ≤ 32`, ≥ ok. 4100 wave’ów na 96 CU (`286840ac`) | TensorFold: M5 96% streamingu, W7800 514 → 681 GB/s. Nasze 5 kolumn przy ok. 700 GB/s to [INFERENCE] ok. 80–85% streamingu | +50 GB/s przy 5 kolumnach daje **−1.7 ms (+5%)**; ablacje mówią, czy to w ogóle możliwe | niski (a, b), średni (c, d) | niskie | `mmvq.cu`, `mmvq-bench/` | **K1** |
| 12 | Keyed Gumbel przy T>0 jako sampler (poza #3c) | Teoretycznie sprzężenie Gumbela nie przebija optymalnego rejection samplingu dla pojedynczego tokenu [INFERENCE]. Nasz „probabilistic” nic nie dał; Strata miała płasko na 3060. Wartość leży głównie w deterministyczności i w #3 | 0…+3% przy T=1 (T=1 vs T=0: 81.1 vs 86.3, `NOTES.md:170-171`) | niski–średni | niskie (kary/grammar) | `common/sampling.cpp`, sampler draftu | — |
| 13 | Loop guard w bloku think (okres ≤ 8, 256 powtórzeń, start ≥ 64; 1.3 µs/commit) | Wygoda, nie prędkość: przerywa wielominutowe pętle myślenia (#204: 28k tokenów) | 0 | niski | niskie | `server-context.cpp` | — |

**Czego nie przenosić (z powodem):**
- **Bitowa row-invariance jako kontrakt.** Kosztuje TensorFold 20–29% przy 1 wierszu na M5 (#527, ścieżka FP32-ALU zaparkowana). My bramkujemy przez greedy_check i KLD. Warto natomiast przejąć klasyfikator near-tie jako detektor bugów (§6).
- **Trellis EXL3/EXLR8:** nie ma kernela HIP, dekodowanie jest ciężkie dla ALU, zmienia trunk, a akceptacja czatu spada (4.2 → 3.0–3.3).
- **FP8 prompt i FP8 KV:** tylko gfx12, a FP8 prompt daje PPL +4.1%.
- **Własne kernele HIP TensorFold:** W7800 ma 25.8–27.2 tok/s plain, ok. 49% pasma end-to-end (#490). Z #490 bierzemy wyłącznie regułę occupancy, „GQA raz na głowę KV” (to już mamy) i bucketowanie grafów.
- **Megakernel z grid barrier:** przegrał też na M5 Ultra (`1fbd9ba7`), co zgadza się z naszym „Avoid”.
- **Druga opinia MTP dla DFlash2:** −6…9%.
- **„Copies zamiast drzew” dla samotnego strumienia:** cofnięte w 1.0.7.
- **Rozszerzanie draft vocab skryptami:** `draft_vocab_extend.py` nie ma Latin-Extended. U nas 3.5% polskich tokenów leży poza 64k (`NOTES.md:161`) i jest to już w roadmap C.
- **Współbieżność i lanes dla wielu strumieni, dwa Maki, Living Weights, kompakcja.** Użytkownik jest jeden.

**Delta względem studium Straty (co się zmienia w planie):**
- **K4** zmienia się najbardziej. Strata dała tylko IL q8_1 i regułę ≥ 3%; TensorFold pokazuje, że właściwym celem jest nachylenie kosztu kolumny (#2) plus reguła wyceny (#5). Bez tego szerokie okna to strata, z tym kod +13–19% (#100).
- **S4:** z „pomysłu” (Strata ranking #5) do warunku wstępnego dla #3/#8/#9, z gotowym wzorcem (lagged state, `kept_rows`) i dowodem na gfx1100 (#490).
- **K3:** od „wejścia z pinned mapped + brak syncu” (Strata) do pętli, w której akceptacja i rollback są danymi na GPU (#3), z celem 0.3–0.5 ms hosta na rundę.
- **Drzewa:** w Stracie „nie budować” (top-2 0/14), w roadmap „niemożliwe dla GDN”. TensorFold pokazuje, że są możliwe i opłacalne przy płaskiej szerokości oraz dobrym drafterze (DFlash2), a nieopłacalne dla MTP nawet przy 56–88% trafień runner-upa. Odłożone za #1 i #2, z pomiarem 4.
- **S2:** dodatkowe, niezależne potwierdzenie, że 4-bitowy drafter trzyma akceptację.
- **S3:** TensorFold nie ma okna atencji MTP, więc brak dowodów w żadną stronę.
- **Self-distillation MTP:** TensorFold pokazuje, że drafter trenowany na niekwantyzowanym modelu traci akceptację na kwantyzowanym trunku (EXL3: 4.2 → 3.0–3.3; #280). To wspiera destylację na **naszym** trunku Q4. Pomysł „recordera” (#620: zapis tapów i top-k celu z ruchu serwera) to tani sposób zbierania polskich danych.
- **K5:** #7 (MTP jako K/V), trik `S^T = K·Q^T` dla WMMA prompt attention (B4), higiena indeksów (#10d). Nasz prefill 660–910 t/s jest już szybszy od każdej ścieżki AMD TensorFold poza FP8 na RDNA4.

**Łączny potencjał [INFERENCE, bez nakładania].**
- Krótki kontekst, czat:
  - #1 + #3 + #4 + #10 + #11 dają −4…6 ms/krok, czyli 35.7 → ok. 30–31.5 ms, **≈ 100–105 t/s**;
  - z #2 i #5 dochodzi do tego +0–3% na czacie i +10–20% na kodzie.
- Kod i agent: #5 + #9 (po #1/#2) dają kilkukrotny zysk na edycjach.
- Długi kontekst: #3 (maska na GPU) i #10d.

**Kolejność:**
1. Pomiary decyzyjne 1–5 (ok. 1 dzień GPU).
2. #4 (S2) i #5 (tania reguła; od razu daje dane o kosztach).
3. #1 (S4 lagged).
4. #3 etapami (b) → (c).
5. #10 i #11 jako część K1/K2.
6. #2 tylko po pozytywnym pomiarze 5.
7. Potem #9, #8.
8. #6 i #7 niezależnie (prefill/TTFT).

## 6. Lekcje metodologiczne do przyjęcia

Tylko nowe względem listy ze studium Straty (`strata/README.md` §6). Pełna lista L1–L16 jest w `local://tensorfold-method.md` §8.

1. **ABBA z regułą ilorazów krzyżowych i „brakiem werdyktu”.**
   - `spec_sweep.sh` liczy ms/krok w kolejności A B B A.
   - „Wolniej/szybciej” tylko wtedy, gdy wszystkie ilorazy krzyżowe mają ten sam znak, a średnia przekracza 2%.
   - Jeśli dwie wizyty tego samego ramienia różnią się o > 2% (nasza powtarzalność to ok. 0.3 ms ≈ 0.8%, `NOTES.md:182`), wynik to „brak werdyktu”.
   - Wzór: `gate_judge.py:127-148`.
2. **Harness testowany podłożonym błędem.** Raz na zmianę harnessu uruchomić build z jednym zmienionym tokenem (env debug) albo z `usleep(300)` na krok. Harness musi zgłosić „różne” lub „wolniej”. Do tego testy parsera na uciętym wyjściu serwera (#432, #485: „missing is not zero”).
3. **Drafted == plain jako detektor bugów, z klasyfikatorem near-tie** (`qwen27_margins.py`).
   - Greedy z MTP off vs on. Przy pierwszej rozbieżności zrzucić top-2 z obu ścieżek.
   - „Remis” tylko wtedy, gdy ta sama para wygrywa i oba marginesy są ≤ epsilon (np. 1 odstęp bf16).
   - W każdym innym przypadku to bug ścieżki spec (rollback GDN/KV, pozycje). Obowiązkowe przed i po #1, #3 i #8, bo KLD na prefillu tych bugów nie widzi.
4. **Determinizm pod obciążeniem GPU.** `greedy_check.sh --stress`: 10× w spoczynku i 10× z równoległym procesem HIP (GEMM w pętli). Na gfx1150 dopiero obciążenie ujawniło brak bariery: 5/10 różnych odpowiedzi (#490). Dotyczy naszych nowych kerneli: fattn-kvq WMMA, fuzje, graf MTP.
5. **Ablacje speed-of-light przed strojeniem K1** (#527):
   - te same loady bez dp4a;
   - dp4a bez loadów;
   - skale stałe.

   Do tego mianownik ze zmierzonego streamingu. To mówi, czy 700 GB/s jest ograniczone wzorcem dostępu, latencją czy ALU. Bez tego grozi tydzień przestawiania pętli, które nie mogą pomóc.
6. **Kubełek „host po zakończeniu GPU”** jako osobna linia rozkładu kroku, obok przerw wewnątrz grafu: 2.3 ms z 27.5 ms w #527 było kopią na hoście. To uzupełnia jedną linię rozkładu kroku ze Straty.
7. **Tabele kosztów:** minimum z ≥ 7 pomiarów, ponowny pomiar spadków > 3% i dryfu > 15%, cache per build/GPU. Do tego **porównanie tabeli z żywymi rundami**, bo na Flash Next różnica +40% zabiła politykę (#250). Dotyczy pomiaru 1 i reguły #5.
8. **FP64 per klasa projekcji, z najgorszą kolumną i „% elementów gorszych”** dla każdej zmiany niebitowej (S1, S2, #2), obok KLD. Średnia ukryła 1.8–5.8% pogorszonych elementów w #457.
9. **Inwariant A/B:** ten sam hash tokenów, ta sama liczba kroków i akceptacji, więc różni się tylko czas kroku (#317, #406). Jeśli inwariant nie zachodzi, raportować tylko ms/krok; t/s jest wtedy nieporównywalne (zgodne z `NOTES.md:184`).
10. **Więcej różnych promptów niż slotów i licznik rekapturowania grafów HIP** (#317: fałszywe „−24%” z 1.25 s rekapturowania na żądanie, widoczne dopiero od 6. promptu). Raportować też czas wall klienta dla krótkich odpowiedzi.
11. **Zmierz sufit draftera, zanim zbudujesz szersze okno.** TensorFold policzył, że prawda leży w top-16 dla 6.5–7 tokenów na rundę, a żaden scorer nie trafia > 75% za głębokością 1, więc drzewa mają twardy sufit. U nas odpowiednik to pomiar 4 (P(2. kandydat | pudło)) i rozkład głębokości akceptacji przed K4.
12. **Zmiana zawężona do sprzętu, na którym ją zmierzono, i reguła „no-slower na każdej długości”.** Nowy default w `run-llm.sh` wchodzi tylko wtedy, gdy nie jest wolniejszy przy 1.7k, 30k i 94k (cofnięcie `a5f518b4` miało dokładnie taki powód).
13. **Format wpisu negatywnego** (#527): nagłówek „Findings … (parked)”, gałąź, flaga env, jedno zdanie decyzji i reguła, która ją wymusiła. Lista „exact but no faster” w NOTES ma oszczędzić następnej osobie dzień pracy (#502).
