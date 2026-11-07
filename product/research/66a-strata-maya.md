# 66a. Strata v0.2.12 (dostrojony drafter DFlash2, Strix Halo, Mac) i Project Maya v1.1.55–v1.1.56

Data: 2026-11-07. Autor: podagent R66a_StrataMaya. Praca tylko na CPU: bez GPU, bez serwera :8080, bez pobierania wag.

Klony (tylko kod, `git clone --depth 1`):
- `~/src/research66/Strata`: HEAD `146df3c4` (2026-11-07 01:29). Tag v0.2.12 = `123bad4a`, v0.2.11 = `4a416016`.
- `~/src/research66/project-maya`: HEAD `7645ddd5` (2026-11-07 09:41). v1.1.55 = `c4effee6`, v1.1.56 = `22fc101f`.

Release notes jako tekst: `/tmp/strata_v0.2.12.txt`, `/tmp/maya_v1.1.5{4,5,6}.txt`, lista commitów Mai `/tmp/maya_cmp.txt` (pliki tymczasowe, poza repo).

**Punkt wyjścia (co już wiemy, żeby nie powtarzać):**
- Strata do v0.2.11 (`9f7d977d`): [63a §2–5](63a-silniki-lokalne.md), [[strata]] w wiki.
  - DFlash2 jest domyślny od 0.2.10 i wygrywa na greedy kodzie, nie przy T=1.
  - KVA jest stratne.
  - Dla gfx1100 i gęstego 27B nic.
- Project Maya do **v1.1.54 `c167004`**: [63b §2](63b-colibri-maya-delta.md), [[project-maya]]. Wiersz v1.1.54 jest już w tabeli 63b. **Deltą jest więc v1.1.55 + v1.1.56** (+6 commitów po tagu do `7645ddd5`).
- DFlash/DFlash2 na naszym 27B jest już zmierzony:
  - [15b §3](15b-spekulacja-frontier.md): DFlash2 n=15 przy T=1 daje 97.9 t/s, MTP 108.8;
  - `qwen-opt/NOTES.md:148-158`: przy T=0 ~równo z MTP, przy T=1 gorzej (sample-and-match);
  - [10-post-training](10-post-training.md): fine-tune DFlash2 w TensorFold dał 0.
- Adaptacyjna głębokość draftu (reguła „iloczyn pewności”) to klasa odrzucona w [24q](24q-adaptacyjna-spekulacja.md): zmienia greedy md5, bo weryfikacja zależy od szerokości. Lekcja: [[lekcja-glebokosc-zmienia-tekst]].

## 0. Qwen3.8-Flash-Next na naszym sprzęcie (XTX 24 GB + 64 GB DDR4, Ryzen 7 5700X): Strata 0.2.12 czy upstream llama.cpp?

Pytanie użytkownika (przez Main, 2026-11-07). Model: Qwen3.8-Flash-Next (125B MoE, ~6B aktywnych, tablica n-gram/PLE „engram” ~51B parametrów = 28.8 GB w IQ4_NL), GGUF Unsloth Dynamic v3.1.

### 0.1 Czy Strata 0.2.12 obsługuje Flash-Next i DFlash2 na Linuksie z dGPU ROCm albo Vulkan?

- **ROCm/HIP: tak.**
  - Gotowy pakiet `rx7900` (Linux, gfx1100/1101/1102) zawiera własny ROCm 7.10.0a20251120 (koła TheRock `gfx110X-dgpu`); wystarczy sterownik amdgpu z jądra (`docs/AMD_HIP.md:8-17,55-61`).
  - RX 7900 XT/XTX ma status „Maintainer-tested” (`AMD_HIP.md:32`). Ze źródeł: `./setup.sh --backend hip`, kompilacja 10–20 min; użyje systemowego ROCm 7 z `/opt/rocm`, jeśli jest (`AMD_HIP.md:98-108`).
  - **Zastrzeżenie:** pliki wydania 0.2.12 nie były uruchomione na RX 7900 („Not run on a matching card: … RX 7900”, release notes). W 0.2.11 paczka RX 7900 też była tylko zbudowana (63a).
- **Vulkan: nie.** Silnik ma backendy CUDA, HIP, Metal, SYCL i CPU (`CMakeLists.txt:14,80,93`). Vulkan występuje tylko przy budowie generatora obrazów `sd-cli` (`setup.py:5382-5393`).
- **Zestawy Unsloth v3.1 są w katalogu** (rewizja `d9620119`, 2026-11-04, silnik ≥ 0.1.57; `setup.py:429-509`). Rozmiar ekspertów („arena”) i pobranie:
  - UD-IQ1_M: 34.8 GB / 68.0 GB;
  - UD-Q2_0: 37.4 / 70.5;
  - UD-IQ2_XS: 42.3 / 75.8;
  - UD-Q2_K_XL: 46.0 / 79.6;
  - UD-IQ3_XXS: 50.3 / 83.6;
  - UD-Q3_K_XL: 56.2 / 89.5;
  - UD-IQ4_XS-v31: 60.4 / 93.7.
  - Ostatni shard każdego zestawu to tablica n-gram (28.8 GB, osobny plik).
- **DFlash2 na gfx1100: kod jest, ale nikt go nie mierzył.**
  - HIP jest w `DFLASH2_BACKENDS` (`strata_control/drafting.py:41`), a gfx1100 nie należy do `_TESTED` (`:98`), więc poziom to „untested” (`:192`).
  - Auto i tak wybiera DFlash2 dla Flash-Next i zestawów Unsloth (`drafting.py:16`), ale ze **standardowym** packiem. Dostrojony pack 0.2.12 dla HIP włącza się tylko na gfx1151 (`:329-332,425-426`).
  - Próg pewności wynika z liczby slotów ekspertów na karcie (`CONF_STEPS`, `:267`). Przy 24 GB to prawdopodobnie 0.5–0.7 `[INFERENCE]`.
  - Powrót do MTP: `strata launch --drafting mtp`.

### 0.2 Opcje pamięci w Stracie

- **Tablica n-gram (engram/PLE) na SSD:** czytana po kilka wierszy na token przez cache systemu, nie ładowana do RAM ani VRAM (`docs/HOW_IT_WORKS.md:31`, `docs/MODELS.md:121-123`).
- **Offload MoE (trzy poziomy):**
  - VRAM: gęsta część, atencja/GDN, router, shared experts, głowica, warstwa MTP, KV (od 64K tylko najczęściej czytana część), a resztę wypełnia **adaptacyjny cache ekspertów**, ~700 ekspertów na GB;
  - RAM: wszystkie eksperty, przypięte; CPU liczy chybienia w miejscu, równolegle z GPU (AVX2 / AVX-512);
  - (`HOW_IT_WORKS.md:22-30`).
- **64 GB RAM to tryb „budżetu RAM”** dla zestawów Unsloth: budżet = RAM − 24 GB, czyli **40 GB** (`--resident-budget-gib 40`).
  - Najgorętsze eksperty trzymane w RAM, reszta czytana z GGUF na SSD.
  - Prefetch z routera następnej warstwy: `STRATA_LOOKAHEAD`, bez wpływu na wynik.
  - Od ctx 64K KV idzie do RAM i jest odejmowany od budżetu (`docs/UNSLOTH_Q4.md:26-32,201-206`).
- **Co się mieści przy 40 GB budżetu:** w całości tylko UD-IQ1_M (34.8 GB) i UD-Q2_0 (37.4 GB). Przy UD-IQ2_XS…UD-IQ4_XS-v31 część ekspertów (2…20 GB) pochodzi z SSD `[INFERENCE: zakładam, że cache VRAM nie zmniejsza zapotrzebowania na RAM; dokument mówi to tylko o rodzinie ISTA w trybie low-RAM, `MODELS.md:133-142`]`.
  - Dla porównania rodzina ISTA (oryginalne GSQ-RCO): IQ3_S 50 GB ekspertów „mieści się przy 64 GB z niewielką ilością innych programów” (`MODELS.md:125-134`).
- **Drafting:**
  - DFlash2 (standardowy pack 0.52 GB, pobierany raz, ~0.9 GB VRAM) albo MTP (pobranie ~6 GB warstwy MTP, `MODELS.md:144-145`);
  - lookup z kontekstu przy edycjach kodu.

### 0.3 Upstream llama.cpp

- **Architektura `qwen4exp`:**
  - w master od [#27742](https://github.com/ggml-org/llama.cpp/pull/27742) (scalony 2026-08-27, `6c84c7d5d`);
  - **MTP w master od [#29761](https://github.com/ggml-org/llama.cpp/pull/29761)** („Qwen4Exp: add MTP”, `c061df198`, 2026-10-01, pierwszy tag **b11330**).
  - Gałąź `danielhanchen:qwen4exp/mtp` ([PR #28243](https://github.com/ggml-org/llama.cpp/pull/28243)) jest **zamknięta bez scalenia**, HEAD `6fcaa16f` z 2026-09-21 (GitHub API). Konkurencyjny [PR #27836](https://github.com/ggml-org/llama.cpp/pull/27836) jest nadal otwarty.
  - Wniosek: zamiast tej gałęzi bierzemy master ≥ b11330 z `--spec-type draft-mtp` `[INFERENCE: #29761 zastąpił obie gałęzie; różnic funkcjonalnych nie porównywałem]`.
- **Tablica PLE/engram:** `TENSOR_READ_LAZY`, czyli wiersze czytane na żądanie z mmap (`src/models/qwen4exp.cpp:213-214`, `src/llama-model-loader.h:72`). To odpowiednik „n-gram na SSD” w Stracie.
- **Offload MoE:** `--n-cpu-moe N` / `-ot exps=CPU` (statyczny podział warstw) plus **`--moe-cache-mib`** (LRU ekspertów z RAM na GPU, [#29887](https://github.com/ggml-org/llama.cpp/pull/29887), scalony 2026-10-07; 4090 Flash-Next Q4_0 25.0 → 40.7 t/s, 5090 30.8 → 67.8; R21g). Jest też w topce: `common/arg.cpp:2795`.
- **DFlash2 dla Flash-Next w llama.cpp: niezweryfikowane.**
  - Ogólny DFlash2 jest od b10658, a `qwen4exp` wystawia wejścia warstw dla tapów (`qwen4exp.cpp:450`, strumienie hyper-connection).
  - Drafter Straty uśrednia 4 strumienie (`dflash2.hpp:3-4`). Czy konwerter llama.cpp robi to samo, nie sprawdzałem.
  - GGUF społeczności: [nazeshinjite/Qwen3.8-Flash-Next-DFlash2-GGUF](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-DFlash2-GGUF) `[INFERENCE]`.

### 0.4 Co będzie lepsze na tym sprzęcie

| | Strata 0.2.12 (HIP `rx7900`) | upstream llama.cpp master ≥ b11330 (ROCm lub Vulkan) |
|---|---|---|
| Backend na XTX | tylko HIP (własny ROCm 7.10) | ROCm albo Vulkan |
| Engram/PLE | SSD, przez cache systemu | mmap leniwie (`TENSOR_READ_LAZY`) |
| Eksperci na GPU | **adaptacyjny cache** najczęściej używanych + CPU liczy chybienia równolegle | statyczne `--n-cpu-moe` + LRU `--moe-cache-mib` |
| Drafter | DFlash2 (Auto, nieprzetestowany na gfx1100) albo MTP; lookup | MTP (`draft-mtp`); DFlash2 niezweryfikowany; ngram/lookup |
| Prefill na XTX | tabela hipBLASLt dla gfx1100 (opt-in na dGPU, bo zmienia zaokrąglenia; `AMD_HIP.md:85-93`): 0.1.38, IQ3_S, 7900X + 96 GB: prompt 1K 760 / 4K 1275 / 32K 1641 / 128K 1494 t/s (`docs/DETAILS.md:1435`) | brak pomiaru na XTX |
| Dekod na XTX (zmierzony) | **60–65 t/s** IQ3_S, MTP, 7900X + 96 GB DDR5 (`DETAILS.md:1435`); społeczność 62.3 t/s (R57b); #2938 82.5 t/s zawyżone | brak; 4090 + RAM: 40.7 t/s Q4_0 z `--moe-cache-mib` |
| Ryzyka | wydanie 0.2.12 nieuruchomione na RX 7900; tryb budżetu RAM czyta z SSD przy 64 GB; osobny stos ROCm | eksperci z CPU na 8 rdzeniach i DDR4; statyczny podział |

**Werdykt `[INFERENCE]`:** na XTX + 64 GB DDR4 Strata ma przewagę konstrukcyjną nad upstream llama.cpp:
- adaptacyjny cache ekspertów w VRAM;
- CPU i GPU pracują jednocześnie;
- strojony prefill HIP;
- jedyne liczby z XTX (60–65 t/s) pochodzą ze Straty, a najlepsza znana liczba upstream (40.7 t/s) jest z RTX 4090.

Dwie rzeczy obniżą wynik Straty u nas względem 60–65 t/s:
- (a) **DDR4 i 8 rdzeni (5700X)** zamiast DDR5 i 12–16 rdzeni: chybione eksperty liczy CPU, a przepustowość DDR4 jest niższa (~45–50 vs ~75–90 GB/s);
- (b) **64 GB RAM:** przy zestawach ≥ UD-IQ2_XS część ekspertów pochodzi z SSD.

Realistycznie, dla UD-IQ3_XXS / UD-Q2_K_XL, spodziewam się ~35–55 t/s dekodu `[INFERENCE, niezmierzone]`. To mniej niż nasz Qwen3.8-27B w topce (greedy ~106 t/s, sesje 95–217 t/s). Ten sam wniosek co w R57b i R21n: Flash-Next na tej maszynie ma sens dla jakości, nie dla szybkości.

Mniejsze zestawy (UD-IQ1_M, UD-Q2_0) mieszczą się w całości w RAM, ale mają niższą jakość. Zmiana kwantu to decyzja użytkownika, poza naszą regułą bezstratności (inny model).

**Test A/B (wymaga zgody: zatrzymanie :8080 i pobranie 70–94 GB):**
- **Wspólne warunki:**
  - ten sam GGUF w obu silnikach, np. UD-IQ3_XXS v3.1 (83.6 GB) albo UD-Q2_K_XL (79.6 GB);
  - ten sam zestaw promptów (`spec_sweep` 48 promptów, T=0 i T=1, 300 tokenów);
  - 2 rundy ABBA, świeży start silnika na ramię, dziennik `free`/`iostat` (odczyty z SSD).
- **Ramię A:** Strata `./setup.sh --backend hip`:
  - wariant 1: `strata launch --family unsloth --model UD-IQ3_XXS`, Auto = DFlash2;
  - wariant 2: to samo z `--drafting mtp`.
- **Ramię B:** llama.cpp master ≥ b11330 (ROCm i Vulkan osobno), `-ngl 99 --n-cpu-moe N` (N dobrane tak, żeby VRAM był pełny), `--moe-cache-mib` z resztą VRAM, `--spec-type draft-mtp --spec-draft-n-max 2/3`, ctx 32k.
- **Mierzyć:** dekod t/s, prefill 4K/32K, TTFT, szczytowy RAM i odczyty SSD.
- **Kill:** dekod Straty < 1.2× llama.cpp na tym samym GGUF przy T=1, a więc nie warto utrzymywać drugiego stosu ROCm.

## 1. TL;DR

1. **„Newly trained DFlash2 drafter” to fine-tune drafterów Inco AI dla Qwen3.8-Flash-Next (125B MoE), nie dla 27B.**
   - Waga 603 M, plik `.pack` Straty (Q4_0 + selektor Q4_0), 0.34 GB.
   - Dostrojony na wyjściach kwantów UD-Q4_K_XL i UD-IQ4_XS-v31: +11.4% przyjętych draftów, +2.1…5.0% t/s na CUDA/Strix/Arc, +3.4…4.5% na Macu.
   - **Z Qwen3.8-27B w llama.cpp nieużywalny:** inny cel (taps z 5 warstw Flash-Next, hidden 2560 vs nasz drafter 27B hidden 5120 / 1.9 B), inny format.
   - DFlash2 dla 27B (z-lab/Inco AI, GGUF) już mamy, a llama.cpp go obsługuje od b10658.
2. **Nagłówki z tweeta nie zgadzają się z release notes.**
   - Mac: wyjście **+10.3…12.7%**, nie +31%.
   - Strix Halo Windows: ×1.24…×2.14 to **prefill**. „Prawie 3× na Linuksie” nie ma pokrycia: Linux Strix nie był uruchomiony, a przełączniki są tylko na Windows.
   - „3× low RAM” to prefill RTX 3060 87 → 264 t/s z **poprawki błędu** liczenia wolnej pamięci.
3. **Strix Halo przyspieszył dzięki kernelom prefillu, nie dzięki drafterowi i nie dzięki UMA.**
   - Fuzowane kernele ekspertów na WMMA w F16 (K-quanty UD-Q4_K_XL i warstwy Q5_0 down UD-IQ4_XS-v31) zastąpiły „gather + dekwant FP16 + hipBLASLt”, które brały 24–29% prefillu.
   - Zmieniają bity (bramka KL), więc u nas trafiają do „stratnych”.
   - Dekod: +3…24% z dostrojonego draftera i grupowanych kerneli ekspertów MoE.
4. **Maya v1.1.55–56: dla dekodu i prefillu gfx1100 z gęstym 27B nic do bezpośredniego portu.** Najcenniejsza jest lekcja z #864 (RX 7900 XTX: −39% czasu kerneli WMMA przez lepsze „karmienie” WMMA, bitowo).
   - Nasz audyt ISA tej lekcji (NOWE, §3.4): w topce MMQ **Q6_K** na gfx1100 czyta skale bajt po bajcie (`ds_load_i8` ×16, zero `ds_load_b128`), podczas gdy Q4_K/Q5_K/IQ4_XS/IQ4_NL ładują 128-bitowo.
   - Q6_K to 13.4% elementów macierzy UD-Q4_K_XL i 21.2% Q4_K_M. Kandydat na +1.5…5% pp, bitowo `[INFERENCE]`.
5. **Dla Enigmy (NOWE):**
   - Strata zmierzyła, że próg pewności draftu musi rosnąć z kosztem wiersza weryfikacji (eksperci strumieniowani: 0.8; rezydentni: 0.35). Na kartach 12 GB z MoE w RAM MTP bije DFlash2 o 12–44%. → kandydaci `--spec-draft-p-min` i n=1…4 w optymalizatorze.
   - DFlash2 jest jedynym drafterem, który na Macu wygrał z MTP (+9.2…14.3% na Flash-Next).
   - `LLAMA_SERVER_TOK_CACHE` jest w produkcji topki **martwy**: ścieżka `SAFE_SPECIAL` go omija (Maya właśnie włączyła odpowiednik domyślnie).

## 2. Co to jest

### 2.1 Strata v0.2.12 (Niko1221/Strata, @coldniko, MIT; drafter Apache-2.0)

[Release v0.2.12](https://github.com/Niko1221/Strata/releases/tag/v0.2.12), 2026-11-07 08:54 UTC. App/Terminal 0.2.12, silnik i Control 0.1.58, feed 122. Model docelowy bez zmian: **Qwen3.8-Flash-Next** (125B MoE, ~6B aktywnych) plus osobny silnik DeepSeek-V4.1-Flash.

**Tweet autora** ([x.com/coldniko/status/2118994582054559808](https://x.com/coldniko/status/2118994582054559808), czytany przez snippet web_search, X nieczytelny bez logowania): „newly trained DFlash2 drafter for Strix Halo and Mac; 31% tokens/s increase on Macs; Strix Halo 2x faster on Windows and almost 3x faster on Linux; 3x improvement on low ram setups; tool call fixes”.

**Fakty z release notes** (pomiar autora: 0.2.11 i 0.2.12 obok siebie, 2–3 rundy, świeży start silnika na przebieg, kolejność ramion zamieniana co rundę, greedy 300 tokenów; każda wersja z ustawieniami, które sama zapisuje dla danej maszyny, więc kolumna 0.2.12 zawiera już nowy wybór draftera):

| Maszyna, kwant | Prompt (t/s) | Wyjście | Uwagi |
|---|---|---|---|
| Mac M5 Max, UD-Q4_K_XL | 4K 1406 → 1605; 32K 1350 → 1524 | **+12.7%** (każdy rodzaj w górę) | DFlash2 domyślny na Macu, conf 0.7 |
| Mac M5 Max, UD-IQ4_XS-v31 | 4K 1440 → 1649; 32K 1373 → 1543 | **+10.3%** (agent −0.9%) | |
| Strix Halo (Win), UD-IQ4_XS-v31 | **4K 690 → 1220 (×1.77)**; 32K 1107 → 1377 | kod +10%, czat +3%, **tool call −9.5%** | strata tool-call przypisana drafterowi |
| Strix Halo (Win), UD-Q4_K_XL | **4K 597 → 1267 (×2.12)**; 32K 1034 → 1370 | kod +24%, czat +6%, tool call −5.8%, agent −2.5% | |
| RTX 3060 12 GB, UD-IQ4_XS-v31 | **2K 87 → 264 (×3.0)**; 32K 361 → 981 | kod +37%, agent +34%, **JSON −18.9%** | poprawka file tier |
| RTX PRO 5000, IQ3_S | 8K ×1.002 | +2.4% (agent −1.5%, czat −1.0%) | |
| DGX Spark, IQ3_S / UD-IQ4_XS-v31 | – | +3.1% / +5.0% | |
| R9700, IQ3_S / UD-IQ4_XS-v31 (Auto → MTP) | 32K 3076 → 3304 / 2817 → 3015 | **kod −10.5% / −8.5%** | DFlash2 wyłączony, bo prompt stall 11/50 |
| 2× A6000 | poziom | ±0.4% | |

Weryfikacja tweeta:
- „+31% na Macu”: w release notes i w repo (`grep` po `docs/`, `strata_control/drafting.py`) **nie występuje**.
  - Najbliższe liczby: DFlash2 vs MTP na Macu +12.7% / +9.2% oraz dostrojony pack vs stock +4.5% / +3.4% (`strata_control/drafting.py:311-313`).
  - Po złożeniu daje to ~+13…18% względem MTP `[INFERENCE]`.
- „Strix 2× na Windows”: zgodne tylko dla **prefillu 4K** (×1.77–2.12). Przy 32K jest ×1.24–1.32, a dekod rośnie o +3…24%.
- „Prawie 3× na Linuksie”: **brak pomiaru**. Release notes w „What we ran” piszą: „Not run on a matching card: … Strix Halo on Linux”.
  - Przełączniki prefillu są w kodzie tylko dla Windows: `kq_on()` wymaga `_WIN32` (`src/prefill/moe_fused_iq.cu:1880-1891`), a `q50_on()` na Linuksie zwraca false (`:1949-1954`).
- „3× low RAM”: zgodne dla **prefillu RTX 3060 przy 2K** (×3.0). Przyczyna to poprawka błędu, nie technika:
  - drugi test startowy liczył własną pamięć silnika jako wolną i przełączał eksperty na wolny file cache (0.2.11: 3/3 startów, 0.2.12: 0/3);
  - wyłącznik `STRATA_FILE_TIER_HONEST=0`.

**Zmiany 0.2.12:**
- **Dostrojony drafter DFlash2** (`data/dflash2-tuned/NOTICE.md`):
  - kopia [incoai/Qwen3.8-Flash-Next-DFlash2](https://huggingface.co/incoai/Qwen3.8-Flash-Next-DFlash2) @ `a22a1744`;
  - **wszystkie 603 M parametrów dostrojone na tekście, który kwanty UD-Q4_K_XL i UD-IQ4_XS-v31 napisały dla promptów Straty** (repozytoria, dokumenty, syntetyczne rekordy, bez danych użytkowników);
  - spakowane jako Q4_0 + selektor Q4_0, 339 694 592 B, SHA-256 `4df2e5ab…`;
  - drugi plik z selektorem bf16 (522 458 112 B) dla SYCL/Arc.
  - Wynik autora: **+11.4% przyjętych draftów** (`strata_control/drafting.py:225-229`).
  - Per platforma vs stock pack, 3 rundy, 3/3 (`drafting.py:315-319`):
    - CUDA rezydentna: PRO 5000 IQ3_S ×1.021;
    - DGX Spark: ×1.032 / ×1.048 (IQ3_S), ×1.050 (UD-IQ4_XS-v31);
    - Strix Halo: IQ3_S ×1.037, UD-Q4_K_XL ×1.043, UD-IQ4_XS ×1.045, UD-IQ4_XS-v31 ×1.046;
    - Arc A750 (bf16sel): ×1.054 przy conf 0.6, ×1.063 przy 0.5;
    - Mac (conf 0.7 vs stock przy 0.5): +4.5% / +3.4%.
  - Greedy identyczne z niedostrojonym drafterem na Metal i CUDA (120/120); na HIP tekst różni się długością okna (NOTICE.md).
- **R9700 / gfx1201:** Auto startuje MTP, bo 11 z 50 silników DFlash2 na 0.2.11 zawisło na prompcie (`drafting.py:351`).
- **Strix Halo Windows:** fuzowane kernele prefillu dla UD-Q4_K_XL i warstw Q5_0 UD-IQ4_XS-v31 oraz grupowane kernele dekodu włączone domyślnie (`STRATA_GFX1151_DEFAULTS=0` wyłącza).
- **Mac:** ścieżka promptu nakłada pracę hosta na GPU, bity te same (`STRATA_METAL_PROMPT_HOSTPIPE`, `metal/src/engine/prompt_chain.inc` +160, `window.cpp` +212).
- **RDNA4, prompty ≥30k:** chunked GDN scan, 32K +6.1%, 64K +6.7% (R9700).
- **Opt-in:**
  - `STRATA_PF_FUSED_Q50=1` (gfx12, prompt +40–44%);
  - `STRATA_IQ4_W4A8` (NVIDIA, „same output as MMQ”);
  - `STRATA_SELECT_TWO_PASS=1` (dokładna dwuprzebiegowa selekcja QSA, 128K +1.65%);
  - `STRATA_ADAPT_FETCH`, peer overlap, VNNI tier.
- **Tool calle** (`serve/frontend.py`, `serve/server.py`):
  - #5409: `<function=tools NAME>` i gołe `<function=tools>` (`frontend.py:783,1624`);
  - #5276: otwieracze `<toolcall>` / `<tool-call>` (`:788,1656`);
  - #5281: narzędzie MCP pisane samym ostatnim segmentem, gdy pasuje dokładnie jedno (`:1210`);
  - #4828: wymuszony `tool_choice` przy kilku narzędziach, 24/24 vs 0/24;
  - #4832: wyniki Anthropic po `tool_use_id`;
  - #4622: `undeclared_tool_calls` (`server.py:9853-9861`, domyślnie „text”).
- **Diff v0.2.11 → v0.2.12:** 98 commitów, 161 plików. Kod silnika: m.in. `qsa_select.cu` +767, `moe_iq4_w4a8.cu` +495, `generate.cpp` +397, `prefill.cpp` +263, `window_rule.hpp` +55 (GitHub compare API).

### 2.2 Project Maya v1.1.55 (2026-11-05 17:18) i v1.1.56 (2026-11-06 12:21)

[v1.1.55](https://github.com/mw00/project-maya/releases/tag/v1.1.55), [v1.1.56](https://github.com/mw00/project-maya/releases/tag/v1.1.56). 48 commitów v1.1.54 → v1.1.56, 64 pliki. Modele bez zmian: GLM-5.3-Flash, DeepSeek-V4.1-Flash, MiniMax-M3.1-Flash, Qwen3.8-Flash-Next. **Gęstego 27B nadal brak.**

| Zmiana | Liczby (warunki) | Bitowo? | Werdykt dla nas |
|---|---|---|---|
| v1.1.55: Codex CLI na `/v1/responses` (#726): narzędzia z `namespace`, pomijanie wbudowanych `web_search`/`local_shell`, `reasoning.summary`, `encrypted_content` w obie strony | e2e z Codex CLI 0.160.0 na 3 modelach | n/d | **Enigma:** test zgodności Codex CLI z upstream `llama-server` (`/v1/responses` jest: `tools/server/server.cpp:376-377`) |
| v1.1.55: odpowiedź web-chatu biegnie do końca bez czytelnika, trzymana dobę na dysku, przeżywa restart (`c6884c38`, `9ecfb4e7`) | – | n/d | **Enigma UX** (telefon/zamknięte okno); bez wpływu na t/s |
| v1.1.55: `MAYA_PROMPT_MEMO` domyślnie on (`d862d019`): przyrostowe przygotowanie promptu, te same id | follow-up po historii 115K **−6% czasu** (GLM, 3× V100); bez MEMO ~1.8 s/turę przy 150–350K (`docs/SETTINGS.md:942-947`) | tak (tryb `verify`) | nasz odpowiednik `LLAMA_SERVER_TOK_CACHE` jest **nieaktywny w produkcji** (§3.5) |
| v1.1.55: DeepSeek `DS4_AI_RUN` (bufory indeksera z długości promptu), `MAYA_DS4_AR2` (pipelined all-reduce 2 GPU), `LOAD_INTERLEAVE` | +1.3/3/4% prefill (3× V100), ładowanie −31% (Gorgon Halo) | tak | nie dotyczy (DeepSeek, wiele GPU) |
| v1.1.55: GLM KV INT8 domyślnie | VRAM cache 1.78 → 1.13 GB @128K | **nie** | 🚫 parked (stratne) |
| v1.1.56: załączniki (PDF/Office/EPUB/RTF/wideo) przez OpenAI `file`, Responses `input_file`, Anthropic `document` (#837, #842) | – | n/d | Enigma: funkcja produktowa |
| v1.1.56: **#864** gfx11 WMMA: kernele ekspertów EXL3 −39%, **te same bity** (pepuscz, RX 7900 XTX, ROCm 7.2.4) | bench-set 128–512 wierszy/eksperta: −38.9…−39.7%; 1–37 wierszy: −6.9…−13.9%; 108/108 wyjść bitowo | tak | **lekcja kernelowa → audyt MMQ topki (§3.4)** |
| v1.1.56: #834 GEMV dekodu EXL3 zinline'owany | Gorgon Halo DS 2.25 bpw: dekod 32.3 → 33.6 (+4%) razem z #864 | tak | nie dotyczy (EXL3) |
| v1.1.56: #875 `DS4_CHUNK_GFX11` (doc `d1818c65`) | dyskretny XTX ze strumieniowaniem ekspertów: prompt +15–45% przy większym chunku (`0`) | **nie** (zmienia odpowiedzi) | potwierdzenie znanego: duży `-ub` przy MoE z offloadem (Enigma) |
| v1.1.56: #840 GLM: przy nieudanym wczytaniu slotu próbuje następnego slotu, potem checkpointu | – | tak | wzór dla topki: łańcuch fallbacku przy restore z `--cache-ram`/SSD |
| v1.1.56: #845 seed: żądanie bez `seed` dostaje losowy | – | – | nie dotyczy (llama-server losuje) |
| v1.1.56: #844 loop guard łapie powtarzane tool calle DeepSeeka | – | – | nie dotyczy |
| v1.1.56: #869/#870 RDNA2 prompt F16 / IQ1_S MMQ | +18–33% (2× RX 6900 XT) | **nie** | 🚫 parked |
| v1.1.56: #853 P2P na więcej kart, #851 helper overlap (+11% dekodu), #865/#866 EXL3 helper GPU (~2× prompt na 2× XTX + iGPU) | – | tak | nie dotyczy (wiele GPU, EXL3) |
| po tagu (6 commitów): `78c450a2` SIGTERM nie zawiesza serwera; `7645ddd5` Ollama `"think": false` | – | – | Enigma: sprawdzić `think:false` w API Ollamy, jeśli Enigma je wystawia |

## 3. Technika w szczegółach

### 3.1 DFlash2 vs DFlash vs MTP vs EAGLE

| | MTP (Qwen nextn) | EAGLE-3 | DFlash | DFlash2 |
|---|---|---|---|---|
| Co to | warstwa(y) next-token w checkpoincie modelu | osobna lekka głowica na cechach z 3 poziomów celu | **blokowy drafter dyfuzyjny**: 5 warstw, non-causal | DFlash + lokalna konwolucja + selektor kandydatów |
| Wejście | ostatni stan ukryty celu + embedding tokenu | cechy low/mid/high celu | cechy z 5 warstw celu **wstrzyknięte w K/V każdej warstwy** draftera ([15b §3](15b-spekulacja-frontier.md)) | jak DFlash |
| Generacja | szeregowo, 1 przebieg na token | szeregowo / drzewo | **jeden przebieg na blok** (anchor + maski), pozycje niezależnie (argmax) | jeden przebieg na blok 8 (7 draftów), potem **ścieżka przez selektor** |
| Spójność między pozycjami | pełna (autoregresja) | pełna | brak (każda pozycja osobno) | selektor: top-16 głowicy na pozycję, biliniowy score rank-256 (poprzedni wybór × kandydat), przejście od lewej do prawej |
| Koszt draftu przy n | ∝ n przebiegów warstwy | ∝ głębokość | stały (1 przebieg) | stały (1 przebieg + selektor) |
| Długi kontekst | pełna atencja | – | traci powyżej 4k (gov_report 4.53 → 2.09 przy 32k) | SWA 2048 (ring) |

Kod:
- Strata `include/strata/core/dflash2.hpp:1-17` (architektura: taps = średnia 4 strumieni hyper-connection po warstwach 5/15/25/35/45, fc 12800 → 2560, 5 warstw, dynamiczny 2-tap conv „prepare/finish” wokół atencji i MLP, ring K/V 2048 + 16 zapasu, ring trzyma tylko zatwierdzone wiersze, więc odrzucenie nie wymaga cofania).
- llama.cpp (topka `c0576e3e8`): `common/speculative.cpp:1056-1057` (DFlash2 = `selector_top_k > 0`), `:1298-1320` (spacer selektora: `scores = row + top_k + predecessor·top_k`, argmax, opcjonalne `p_min` na softmaksie w argmaksie), konwersja `conversion/qwen.py:734-787,929-930`.
- Upstream: DFlash `d1b34251b` (#22105, 2026-06-28), DFlash2 `b10f9ca58` (#27342/#27816, 2026-08-27, pierwszy tag **b10658**). Pin Enigmy b11856 już to zawiera.

**Bezstratność:** we wszystkich czterech przypadkach weryfikuje model docelowy.
- llama.cpp przy T>0 robi sample-and-match: rozkład zachowany, akceptacja niższa niż przy rejection sampling.
- Strata stosuje „prawo propozycji” MTP tylko do kandydatów, które sama MTP wylosowała (`include/strata/spec/window_rule.hpp:35-38`). Drafty DFlash2 są punktowe, więc to również sample-and-match.

**Okno draftu w Stracie (`--draft-conf`):** okno kończy się, gdy **iloczyn** prawdopodobieństw selektora spada poniżej progu (`window_rule.hpp:26,65-68`). llama.cpp ucina na **pojedynczym** tokenie (`speculative.cpp:1309-1317`).
- Opt-in `STRATA_DF2_GATE` (`window_rule.hpp:73-77`) kalibruje przeżywalność per pozycja i przedział pewności na żądanie i wydłuża okno, gdy `survival × ms/token ≥ koszt wiersza`.
- To jest dokładnie klasa „adaptacyjna głębokość” z 24q: **znana**. U nas zmienia md5 (szerokość weryfikacji); Strata pisze to samo dla HIP (NOTICE.md).
- `skip_draft_for_lookup` (`window_rule.hpp:40-46`): przy długim dopasowaniu lookupu runda draftera jest pomijana.
  - Nasz `LLAMA_SPEC_LOOKUP=3` robi to dopiero po pełnym przyjętym bloku (`speculative.cpp:2829-2830`).
  - Różnica to jedna runda MTP na początek łańcucha kopii; zysk ≤ ułamka procenta `[INFERENCE]`. 15-synteza odrzuciła „lookup nadpisujący MTP”.

### 3.2 Czy dostrojony drafter Straty zadziała z Qwen3.8-27B w llama.cpp?

**Nie.**
1. **Inny cel.**
   - Drafter Straty czyta stany Flash-Next (48 warstw, taps 5/15/25/35/45, uśrednione 4 strumienie hyper-connection; `dflash2.hpp:3-7`), hidden 2560, 603 M.
   - Drafter 27B, który mamy (`~/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`, metadane GGUF): `general.size_label 1.9B`, `dflash.embedding_length 5120`, `block_count 5`, `block_size 8`, `target_layers [6,20,34,48,62]`, `selector_rank 256`, `selector_top_k 16`, `conv_kernel_size 2`, `sliding_window 2048`, źródło z-lab/Inco AI.
2. **Inny format.**
   - `.pack` Straty (`tools/dflash2_pack.py --q4_0-selector`) to własny układ.
   - llama.cpp czyta GGUF `dflash` (konwersja z HF `DFlash2DraftModel`).
   - Społecznościowy GGUF drafter Flash-Next istnieje ([nazeshinjite/Qwen3.8-Flash-Next-DFlash2-GGUF](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-DFlash2-GGUF)), ale też tylko dla Flash-Next.
3. **Wartość przenośna to metoda, nie plik:** fine-tune draftera na wyjściach **kwantyzowanego** celu.
   - Strata: +11.4% przyjętych draftów → +2…6% t/s.
   - TensorFold (372k tokenów) dostał 0 (`10-post-training.md:36`).
   - Wielkość korpusu Straty jest nieznana (`phaseA-tests/round0215/RESULTS-DF2WS.md` nie jest w publicznym repo).
   - U nas DFlash2 27B przegrywa z MTP przy T=1 o ~10% (97.9 vs 108.8), więc +11% akceptacji co najwyżej wyrówna `[INFERENCE]`. Ten sam pomysł dla głowicy MTP to plan #19 z 63 (on-policy), gdzie nasza samodestylacja KL dała ±0.2–2%.

### 3.3 Dlaczego Strix Halo ×1.24…×2.12 (backend, UMA, kernel?)

Odpowiedź: **kernel prefillu MoE (fuzja ekspertów na WMMA w F16) plus domyślne przełączniki gfx1151; nie zjawisko UMA.**

1. **Prefill.** Do 0.2.11 warstwy ekspertów K-quant (UD-Q4_K_XL: Q4_K/Q5_K gate/up, Q5_1/Q8_0 down) i Q5_0 down (UD-IQ4_XS-v31: 33 z 48 warstw) wypadały ze ścieżki fuzowanej. Szły przez gather → dekwant FP16 → hipBLASLt, co brało **24–29% promptu** (`src/prefill/moe_fused_iq.cu:1936-1939`). 0.2.12 na Windows gfx1151 kieruje je do `native_f16_kernel`:
   - kody int8 (q − 16) razy skala bloku, iloczyny F16, wiersze down w FP16 do combine;
   - `kq_on()` `:1874-1895`, `q8d_f16_default()` `:1919-1935`, `q50_on()` `:1943-1959`.
   - Wyjście różni się „at rounding level; KL-gated” (`:1874-1875`).
   - Wcześniejszy, tej samej klasy krok (0.2.8) przy prompt secie WMMA dał 688.8 → 1192.8 t/s przy 4K i KL pierwszego tokenu 0.0014 (`docs/STRIX_HALO_WINDOWS.md:88-95`).
2. **Duży chunk i własne bufory promptu** (wcześniejsze wersje, w tle liczb):
   - eksperci czytani raz na chunk, więc większy chunk = mniej odczytów (`STRIX_HALO_WINDOWS.md:100-104`);
   - **pułapka UMA:** „pożyczony” slot eksperta wracał z arenay hosta z ~0.5 GB/s, bo arena nie jest zarejestrowana w sterowniku w trybie UMA. 823 sloty zajęły 2.75 s z 3.3 s promptu 4K, a własne bufory dały +8.5–8.9% (`:96-100`).
   - To jedyny element „unified memory” i dotyczy kopiowania, nie arytmetyki.
3. **Dekod (+3…24% na kod/czat).**
   - Dostrojony pack: ×1.037–1.046 (`drafting.py:317`).
   - Domyślna tabela 18–19 dokładnych przełączników gfx1151 (`src/core/arch_defaults.cpp:63-105`), m.in.:
     - `STRATA_EXPERT_V2` (grupowane eksperty dekodu IQ3_S/IQ4_NL);
     - `Q8_PACKED` +2.3%;
     - `ATTN_LANECELL`, `TSUM` (wiele sum warpów jako jeden transponowany butterfly);
     - `GDN_SPLIT`, `QFUSE`, `LFUSE`.
   - Na Windows także `SMALL_UNR`, `GR_Q8_PFS` (−0.25% czasu okna, `:98-104`). `STRATA_SH_STREAM` na Windows wyłączony (−6.9%).
4. **Linux gfx1151** zostaje przy starych ścieżkach (`#if defined(_WIN32)` w `kq_on`/`q50_on`), więc „prawie 3× na Linuksie” nie wynika z kodu 0.2.12 `[INFERENCE]`.

**Dla nas:**
- (1) jest stratne, ta sama klasa co „f16 WMMA GEMM w prefillu” (RDNA-FAST) w sekcji 4 raportu 63 → parked.
- (3) to głównie kernele MoE Flash-Next. Pokrewne nasze: TSUM/LANECELL jako idee mamy (63c, R21b), a `ATTN_LANECELL` to wariant atencji dekodu przy MoE.

### 3.4 Maya #864: „karmienie” WMMA na gfx1100 i audyt MMQ topki (NOWE)

**Diagnoza autora #864** ([PR #864](https://github.com/mw00/project-maya/pull/864), commit `4da0b6cc`):
- kernel WMMA 3× wolniejszy na kafel niż IQ2;
- koszt w podawaniu operandów, nie w iloczynach:
  - 197–214 VGPR (7 fal/SIMD);
  - kafel i aktywacje czytane z LDS po słowie;
  - słowa kafla „stage'owane” przez LDS w każdym plasterku;
  - ~57 KB LDS na blok 32 wierszy (4 fale/SIMD).

**Poprawki:**
1. operandy WMMA jako 2× `ds_load_b128` zamiast 8 słów (pitch 9 → 12);
2. słowa kafla przez `v_permlane16`/`v_permlanex16` lub `ds_bpermute` zamiast LDS;
3. kształt bloku z liczby wierszy na eksperta (16/32/64);
4. `out` dzieli LDS z `xb` (jedna bariera więcej), gate w rejestrach: 57 → 24 KB LDS, 216 → 148 VGPR.

Wynik: −39% przy ≥128 wierszach na eksperta, 108/108 wyjść bitowo.

**Co z tego mamy w topce:**
- Kształt kafla z wierszy na eksperta na RDNA3: **jest** (`ggml/src/ggml-cuda/mmq.cu:198-202`: `ncols_opt = ne12·n_expert_used/ne02`), plus dobór J dla gęstych, gdy kafli < CU (`:226-247`).
- Audyt ISA zrobiłem tutaj, na CPU, z `~/llama-topka/bin/libggml-hip.so.0.26.0`:
  - `llvm-objdump --offloading`, code objecty gfx1100 w `/tmp/r66a/`;
  - metadane `llvm-readelf --notes`, liczniki instrukcji z `llvm-objdump -d` po symbolu;
  - wariant `fallback=0`, statyczne liczby w ciele kernela.

| typ MMQ, J | VGPR | `ds_load_b128` | `ds_load_i8` | `ds_load_2addr_b64` | `v_wmma_i32_16x16x16_iu8` | instrukcji |
|---|---|---|---|---|---|---|
| Q4_K, 128 | 239 | 36 | 0 | 0 | 32 | 1461 |
| Q5_K, 128 | 244 | 36 | 0 | 0 | 32 | 1597 |
| IQ4_XS, 128 | 242 | 36 | 0 | 0 | 32 | 1426 |
| IQ4_NL, 128 | 229 | 36 | 0 | 0 | 32 | 1395 |
| **Q6_K, 128** | 222 | **0** | **16** | 18 | **16** | 1555 |
| **Q6_K, 64** | 172 | **0** | **16** | 10 | 8 | 1131 |

- Wniosek: Q4_K/Q5_K/IQ4 już ładują operandy 128-bitowo (lekcja #864 pkt 1 zastosowana). **Q6_K na ścieżce AMD WMMA jest wyjątkiem.**
- W `mmq-vec-dot.cuh:1154-1182` skala `sc[k01/4]` jest czytana jako `int8` z LDS **w najgłębszej pętli** (po `l` i `n`), a `x_df[i*sram_stride]` też per element.
  - Pętla `k01` nie ma `#pragma unroll`.
  - Ścieżka Turing tego samego typu (`:1219-1234`) ładuje skale raz jako `int` i rozpakowuje.
- Udział Q6_K w elementach macierzy (bez embeddingu i MTP; `15a-ggufls.py` na nagłówkach lokalnych GGUF, CPU):
  - **UD-Q4_K_XL (produkcja): Q6_K 13.4%** (ssm_out ×13, attn_k ×12, attn_output ×9, ffn_down ×6, ffn_gate ×5, output);
  - **Q4_K_M: 21.2%** (ffn_down ×33, attn_qkv ×24, attn_v ×9, output).
- Szacunek: jeśli kernel Q6_K jest ograniczony podawaniem LDS i spadnie o 15–30%, prefill zyska ~+1.5…3% (UD-Q4_K_XL) / +2.5…5% (Q4_K_M) `[INFERENCE: zakłada udział czasu ≈ udział elementów; do potwierdzenia profilem]`.
- Bitowość jest osiągalna: ten sam iloczyn `C.x[l]·sc·x_df·dB` w tej samej kolejności, zmienia się tylko sposób ładowania (tak jak 0070 [[mmq-epilog]] dla Q4_K/Q5_K, +2.2% pp4096 bitowo).
- To jest cel „T1: epilog dla Q6_K” z planu RSI (21h, wiki `2026-10-19-plan-retro-rsr-0070`), którego nie wykonano. **Nowe jest konkretne miejsce i dowód ISA.**

### 3.5 `MAYA_PROMPT_MEMO` vs nasz `LLAMA_SERVER_TOK_CACHE` (NOWE: u nas martwy w produkcji)

- Maya: przyrostowe przygotowanie promptu po stringu, te same id, tryb `verify`. Domyślnie od v1.1.55. Bez tego ~1.8 s/turę przy 150–350K (`project-maya/docs/SETTINGS.md:942-947`).
- Topka: `LLAMA_SERVER_TOK_CACHE` (`tools/server/server-common.cpp:951-1072`) działa tylko w `server_tokenize_cached`, wywoływanym z `tokenize_mixed` przy `parse_special` (`:943`).
  - Produkcja ma `LLAMA_SERVER_SAFE_SPECIAL=1` (`qwen-opt/run-topka.sh:98`), więc czat idzie ścieżką `tokenize_prompt_plain_ranges` → `common_tokenize_plain_ranges` (`server-context.cpp:5110-5115`, `server-common.cpp:1306-1316`), **bez cache'u**.
  - `TOK_CACHE` nie jest też ustawiany w `run-topka.sh`.
  - Działa za to `LLAMA_TOKENIZE_PAR=8` (`src/llama-vocab.cpp:3586-3604`).
- Koszt bazowy wg 24i: tokenizacja + szablon 137.3 ms przy 91k. Z PAR=8 część tokenizacji spada kilkukrotnie `[INFERENCE]`, a przy 262k rośnie liniowo.
- Zysk rzędu kilkudziesięciu ms na turę agenta przy 100k+: mały, ale bitowy i tani. Dla Enigmy (upstream, bez PAR) większy, ale wymaga łatki upstream.

### 3.6 Strata: próg draftu zależny od kosztu wiersza weryfikacji (NOWE dla Enigmy)

`strata_control/drafting.py:257-276`: DFlash2 vs MTP przy równym VRAM, IQ3_S, czat 6 tur + 4 zimne prompty, 3 rundy. Zysk według progu (0.35 / 0.5 / 0.65 / 0.8 / 0.9) i liczby slotów ekspertów na karcie:
- 1383 sloty: −4.2 / +3.1 / +7.1 / **+9.3** / +8.7%;
- 15 766 slotów: **+4.9** / +5.6 / +3.5 / −0.6 / −6.5%.

Reguła wdrożona w `CONF_STEPS = ((12000, 0.35), (7500, 0.5), (3000, 0.7), (0, 0.8))` (`:267`): im więcej ekspertów jedzie przez PCIe, tym droższy wiersz i tym krótsze powinno być okno. Do tego:
- `BACKEND_CONF` sycl 0.6, metal 0.5 (`:276`);
- dla klasy „streaming” (12 GB) przy IQ3_S Auto = **MTP**, bo „MTP beats DFlash2 by 12-44%” (`:334-347`).

**Enigma dziś:** jeden kandydat `--spec-type draft-mtp --spec-draft-n-max 4` (`app/engine/src/server/optimize.ts:108-111`), bez `p_min`, bez DFlash2. Plan #4 z 63 (n=1…4) dostaje dodatkowy, zmierzony wymiar: próg `p_min` zależny od klasy offloadu MoE.

## 4. Macierz istotności

| Element | AMD gfx1100 topka | Enigma NVIDIA CUDA | Apple Metal | Intel (Arc/SYCL, Vulkan) | Strix Halo (gfx1151) |
|---|---|---|---|---|---|
| Dostrojony pack DFlash2 Straty | ✗ (Flash-Next, format .pack) | ✗ (jw.) | ✗ (jw.) | ✗ | ✗ |
| Metoda „drafter dostrojony na wyjściach kwantu” | plan #19 (MTP) / DFlash2 27B: niski priorytet ($) | jw. | jw. | jw. | jw. |
| DFlash2 27B jako kandydat w optymalizatorze | ✗ (zmierzone: < MTP przy T=1) | ? (3090: DFlash2 n=7 +22.6% vs MTP n=2 +59.8%, `02-autotuning:257`) → raczej ✗ | **✓ do zmierzenia** (Strata: Mac DFlash2 > MTP +9.2…14.3% na MoE) | ? (Arc: DFlash2 −2.6% vs MTP w 0.2.10) | ? (Strata: DFlash2 > MTP +8.8…12% w 0.2.10) |
| Próg `p_min` / n zależny od kosztu wiersza | mały (XTX rezydentny, 24q) | **✓** (MoE z `--n-cpu-moe`, 8–16 GB) | ✓ (unified, conf 0.5–0.7) | ✓ (Arc 0.6) | ✓ |
| Fuzowane eksperty F16 WMMA w prefillu | 🚫 stratne | 🚫 | 🚫 | 🚫 | 🚫 (główne źródło ×2) |
| Pułapka UMA: kopie host→„device” 0.5 GB/s | n/d | n/d | n/d | iGPU: możliwe `[INFERENCE]` | **✓ lekcja**: nie kopiować wag w obrębie UMA |
| Maya #864: karmienie WMMA (b128, permlane, LDS) → Q6_K MMQ | **✓** (prefill, bitowo) | n/d (MMA Turing już pakuje skale) | n/d | n/d | ✓ (RDNA3.5 ten sam kod) |
| `TOK_CACHE` dla ścieżki SAFE_SPECIAL | **✓** (mały) | Enigma = upstream, wymaga łatki | jw. | jw. | jw. |
| Odporny parser tool-calli (`<toolcall>`, `<function=tools NAME>`, ostatni segment MCP) | ✓ (`SAFE_TOOLS` do przeglądu) | ✓ (upstream parser) | ✓ | ✓ | ✓ |
| Uczciwe liczenie wolnej pamięci po starcie silnika | n/d | **✓** (planer Enigmy) | ✓ | ✓ | ✓ |
| Odpowiedź do końca + trwałość (Maya v1.1.55) | n/d | ✓ UX | ✓ | ✓ | ✓ |
| Codex CLI `/v1/responses` (Maya #726) | test | ✓ test | ✓ | ✓ | ✓ |

## 5. Pomysły do testu (tylko bezstratne)

| # | Pomysł | Bezstratny? | Oczekiwany zysk i dlaczego | Wysiłek | Jak przetestować na naszej maszynie | Ryzyko |
|---|---|---|---|---|---|---|
| A1 | **Q6_K MMQ na AMD WMMA: skale ładowane raz jako `int` (jak ścieżka Turing), `x_df` wyciągnięte przed pętlę `l`, `#pragma unroll` dla `k01`**, tylko gfx11 | **tak, bitowo** (ta sama kolejność iloczynów, zmienia się ładowanie) | pp4096 UD-Q4_K_XL +1.5…3%, Q4_K_M +2.5…5% `[INFERENCE]`: Q6_K = 13.4% / 21.2% elementów, w ISA 16× `ds_load_i8` i 0× `ds_load_b128` (§3.4) | 0.5–1 d | (1) `rocprofv3 --kernel-trace` na `llama-bench -m Qwen3.8-27B-UD-Q4_K_XL -p 4096 -n 0 -ub 2048 -r 3`: udział `mul_mat_q<14,…>`; kill, jeśli < 5% czasu prefillu. (2) `test-backend-ops -o MUL_MAT` (+ `MUL_MAT_ID`) i bramka bitowa logitów prefillu 2048 tok. przy ub 512/64 jak w 0070. (3) ABBA `llama-bench -p 512,4096` ×3 rundy; kill < +1% pp4096. (4) greedy md5 c4708318 / 6f14e814 bez zmian | mały: VGPR może przekroczyć próg fal (222 → ?), sprawdzić `klab isadiff` |
| A2 | **Enigma: kandydaci progu draftu per klasa** – dla MoE z `--n-cpu-moe` i kart ≤16 GB: `--spec-draft-p-min ∈ {0, 0.5, 0.8}` × `--spec-draft-n-max ∈ {1,2,4}` (rozszerzenie planu #4) | tak (rozkład bez zmian; md5 może się zmienić przez szerokość) | 0…+15% na MoE z offloadem `[INFERENCE z Strata: próg zmienia wynik o −4…+9%, MTP vs DFlash2 do 44% na 12 GB]`; XTX rezydentny ~0 | 0.5–1 d TS | XTX emuluje klasę „streaming”: Qwen3.6-35B-A3B-UD-IQ4_XS (lokalnie, `~/models/q36`) z `--n-cpu-moe 20/30/40`, upstream build Enigmy, `spec_sweep` T=0 i T=1 (zestaw 48 promptów), siatka p_min × n; ABBA 2 rundy | czas optymalizatora rośnie ×3–9 → przycinać siatkę po klasie |
| A3 | **`TOK_CACHE` dla ścieżki `SAFE_SPECIAL`** (przyrostowo do ostatniej granicy specjalnej poza `plain_ranges`), tryb `=2` porównuje z pełną tokenizacją | tak (te same id, weryfikowane) | kilkadziesiąt ms/turę przy 90–262k (24i: 137 ms @91k bez PAR) | 0.5 d | CPU: `LLAMA_SERVER_AP_TIMING=1`, replay `agent_bench.py` / `replay interf` 2 wątki 75–120k na testowym serwerze (nie :8080), `ap tokenize … ms` przed/po; `=2` musi dać 0 rozbieżności | niskie; obciążenie RAM cache'u tekstu |
| A4 | **DFlash2 jako kandydat Enigmy na Apple Metal** (GGUF z-lab 27B / drafter dla modelu z katalogu) | tak (sample-and-match) | Mac: Strata +9.2…14.3% nad MTP na Flash-Next; dla 27B gęstego nieznane | 0.5 d + pobranie po stronie aplikacji | nie na XTX: Mac (użytkownik albo $ chmura), `llama-server --spec-type draft-dflash -md …` vs `draft-mtp n=2/4`, ten sam workload Enigmy | DFlash słabo zna polski (NOTES:50: PL 65 vs 78 t/s) → per język |
| A5 | **Parser tool-calli odporny na `<toolcall>`, `<tool-call>`, `<function=tools NAME>`, ostatni segment MCP** (Strata #5276/#5409/#5281) – przegląd `SAFE_TOOLS` w topce i parsera upstream w Enigmie | tak (tylko parsowanie wyjścia) | 0 t/s; mniej zepsutych tur agenta (0.2.8: 92.9 → 98.3% odzysku) | 0.5 d | test jednostkowy parsera z 6 przypadkami z `serve/test_server.py` Straty; potem `spec_sweep` z promptami tool-call (plan #13) | fałszywe wywołania z cytowanego tekstu (u nas `SAFE_TOOLS` tego pilnuje) |
| A6 | **Enigma: planer pamięci nie liczy pamięci własnego silnika jako wolnej** (Strata `STRATA_FILE_TIER_HONEST`) | tak | uniknięcie złej degradacji (Strata: prefill ×3 na 3060) | 2 h przeglądu | CPU: przegląd `app/engine` (MemBar/plan), czy drugi pomiar po starcie `llama-server` odejmuje jego RSS/VRAM | – |
| A7 | **Topka: łańcuch fallbacku przy nieudanym restore** (Maya #840: następny wpis → checkpoint → pełny odczyt) | tak | brak „zimnych” tur po błędzie wczytania | 0.5 d | CPU: przegląd `server-context.cpp` (prompt_load / `--cache-ram`), test z uszkodzonym plikiem slotu na serwerze testowym | rzadki przypadek |

Ranking zysk/wysiłek: **A1 > A2 > A3**, potem A5, A6, A4, A7.

Czego ten pakiet **nie** daje: dekodu przy długim kontekście (odczyt KV przy 199k: 74.5 t/s). Nic w Stracie 0.2.12 ani w Mai 1.1.55–56 nie dotyczy atencji gęstej przy długim ctx w sposób bezstratny. Selekcja QSA Straty to rzadka atencja Flash-Next (natywna w modelu), u nas zaparkowana.

## 6. Odłożone (stratne)

| Pomysł | Dlaczego odpada | Liczby (informacyjnie) |
|---|---|---|
| Strata: fuzowane eksperty F16 WMMA w prefillu (K-quanty, Q5_0 down, Q8_0 down) na gfx1151 | iloczyny F16 zamiast int8/MMQ; „KL-gated” (`moe_fused_iq.cu:1874-1875,1919-1925`) | Strix 4K ×1.77–2.12; wcześniej 688.8 → 1192.8 (KL 0.0014) |
| Strata `STRATA_HC_Q8=1` (domyślne na gfx1151) | „near-tie tokens can differ” | dekod ~+9% |
| Strata `STRATA_PF_FUSED_Q50=1` (gfx12, opt-in) | zmienia arytmetykę warstw | R9700 prompt +40–44% |
| Strata route prior / route-tail-skip / „Faster” 5 z 6 ekspertów | pomijanie/zmiana ekspertów | (0.2.7–0.2.11) |
| Maya GLM KV INT8 domyślnie | inny kwant KV | VRAM 1.78 → 1.13 GB @128K |
| Maya `DS4_INDEX_TC` (v1.1.54, WMMA indeksera na gfx11) | „changes the answers slightly” | +3/6/10% przy 8/32/64K |
| Maya `MAYA_DS4_PROMPT_F16`, `MAYA_DS4_EXPERT_MMQ` (#869/#870) | zmienia odpowiedzi | +18–33% prompt na 2× RX 6900 XT |
| Maya `DS4_CHUNK_GFX11=0` | większy chunk zmienia odpowiedzi | XTX ze strumieniowaniem +15–45% prompt |
| Maya `MAYA_DS4_RING_FAST_LINK`, `DRAFT_SPREAD` (v1.1.54) | zmienia rozmieszczenie ekspertów, „answers change slightly” | +4–14% prefill (3× V100) |

## 7. Źródła

- Strata v0.2.12: https://github.com/Niko1221/Strata/releases/tag/v0.2.12 (2026-11-07). Tag `123bad4a`, v0.2.11 `4a416016`, klon HEAD `146df3c468739147f520ac3816de806f71232571`.
  - Pliki: `data/dflash2-tuned/NOTICE.md`; `strata_control/drafting.py:60-110,200-351`; `include/strata/core/dflash2.hpp:1-17`; `include/strata/spec/window_rule.hpp:26-77`; `src/core/arch_defaults.cpp:27-136`; `src/prefill/moe_fused_iq.cu:1874-1966`; `docs/STRIX_HALO_WINDOWS.md:81-111`; `docs/MAC.md:98-104`; `serve/frontend.py:783-790,1210,1624,1656`; `serve/server.py:9853-9861`.
  - Compare API: `repos/Niko1221/Strata/compare/v0.2.11...v0.2.12` (98 commitów, 161 plików).
- Tweet: https://x.com/coldniko/status/2118994582054559808 (snippet z web_search; strona X nieczytelna).
- Drafter bazowy: https://huggingface.co/incoai/Qwen3.8-Flash-Next-DFlash2 (rev `a22a1744e85c17364dcc54a6a420af7135d4c7f6`). GGUF społeczności: https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-DFlash2-GGUF. Drafter 27B (lokalny GGUF, metadane): https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2.
- Project Maya:
  - https://github.com/mw00/project-maya/releases/tag/v1.1.55 (`c4effee6`, 2026-11-05), https://github.com/mw00/project-maya/releases/tag/v1.1.56 (`22fc101f`, 2026-11-06); baza v1.1.54 `c167004` (63b); klon HEAD `7645ddd536f4b6e3074f0bc4fba94d029c3fbfe6`.
  - Commity: `4da0b6cc` (#864), `61ec6593` (#834), `d862d019` (defaults/MEMO), `d1818c65` (#875), `68451cf1` (#840). PR: https://github.com/mw00/project-maya/pull/864. `docs/SETTINGS.md:942-958`.
- llama.cpp / topka (`~/wt/topka-q63` @ `c0576e3e8`):
  - DFlash: `common/speculative.cpp:995-1125,1255-1326,2824-2856`; `conversion/qwen.py:734-787,929-930`; upstream commity `d1b34251b` (#22105), `b10f9ca58` (#27342/#27816, tag b10658);
  - MMQ: `ggml/src/ggml-cuda/mmq.cu:190-247`, `mmq-vec-dot.cuh:1132-1234`;
  - serwer: `tools/server/server-common.cpp:943,951-1072,1234-1316`, `server-context.cpp:5105-5126`, `server.cpp:376-377`; `src/llama-vocab.cpp:3586-3604`.
- ISA: `~/llama-topka/bin/libggml-hip.so.0.26.0` (build 2026-11-05), wyciąg code objectów gfx1100 w `/tmp/r66a/` (`llvm-objdump --offloading`, `llvm-readelf --notes`, `llvm-objdump -d`).
- Udział typów wag: `product/research/15a-ggufls.py` na `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf` i `~/models/*/Qwen3.8-27B-Uncensored-Q4_K_M.gguf` (tylko nagłówki).
- Enigma: `app/engine/src/server/optimize.ts:108-111`. Produkcja: `qwen-opt/run-topka.sh:78-103`.
- §0 Flash-Next na XTX:
  - Strata: `docs/AMD_HIP.md:8-108`, `docs/HOW_IT_WORKS.md:22-31`, `docs/MODELS.md:119-145`, `docs/UNSLOTH_Q4.md:26-32,201-230`, `docs/DETAILS.md:1435`, `setup.py:429-509,705-725`, `CMakeLists.txt:14,80,93`, `strata_control/drafting.py:16,41,98,192,267,329-332,425-426`.
  - llama.cpp: [#27742](https://github.com/ggml-org/llama.cpp/pull/27742) (qwen4exp, 2026-08-27), [#29761](https://github.com/ggml-org/llama.cpp/pull/29761) (MTP, `c061df198`, b11330), [#28243](https://github.com/ggml-org/llama.cpp/pull/28243) (gałąź `danielhanchen:qwen4exp/mtp`, zamknięty bez scalenia, HEAD `6fcaa16f`), [#27836](https://github.com/ggml-org/llama.cpp/pull/27836) (otwarty), [#29887](https://github.com/ggml-org/llama.cpp/pull/29887) (`--moe-cache-mib`).
  - Topka: `src/models/qwen4exp.cpp:196-215,450`, `src/llama-model-loader.h:72`. Wcześniejsze: R21g, R21n, R57b.
- Wcześniejsze raporty: 63-SYNTEZA, 63a §2–5, 63b §2, 15b §3, 24q, 24i, 10-post-training, wiki [[mmq-epilog]], [[strata]], [[project-maya]].
