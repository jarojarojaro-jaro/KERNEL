# 21n. Strata 0.2.0-beta i Gyro-S (Qwen3.8-Flash-Next) na naszym XTX

Data: 2026-10-19. Tylko CPU (bez GPU i chmury). Klon: `~/qwen-opt/research-src/strata-020` (tag `v0.2.0-beta` = `3d1fb480`), `agention-llama.cpp` @ `9aa51ce4`. Notatki i surowe dane: `21n-notatki/`.

## Werdykt

1. **Gyro-S to zły plik dla naszej maszyny.** Sama Strata przypisuje go progowi **32 GB RAM+VRAM** (README:155-170). Przy naszych 86 GB (24 + 62) Strata poleca **IQ3_S**. Gyro-S zyskuje prędkość, bo przy tym samym VRAM mieści ~2× więcej ekspertów (trafienia ≈96% wobec ≈75%). Płaci za to jakością: KLD 0.27–0.40, czyli gorzej niż IQ2_XS według pomiaru Straty, a LiveCodeBench spada do 67% przy limicie 64k.
2. **Szacowana prędkość Gyro-S na XTX: ~50–75 t/s bez MTP i ~60–100 t/s z MTP** `[INFERENCE]` (rachunek w §3). Nasz 27B robi 100 t/s (sweep T=1) i 170 t/s (code-edit). Flash-Next byłby u nas wolniejszy. Przy jakości Gyro-S przewaga Flash-Next nad 27B na benchmarkach (+1…+17 pkt w BF16) jest niepewna.
3. **„Nie mieści się” było nieaktualne.** Tabela n-gramów (PLE, 28.8 GB) leży na SSD, więc IQ3_S potrzebuje ~50 GB RAM na ekspertów + VRAM. To mieści się w 62 GB „przy prawie niczym innym otwartym” (MODELS.md:88-92). Liczba 94–111 GB obejmowała PLE.
4. **Strata 0.2.0 to głównie aplikacja, nie silnik.** Silnik ma wersję 0.1.45.3. Zmiany: 55% to aplikacja, 6% silnik. **Nic nowego w prędkości dla gfx1100.** Przyspieszenia dotyczą NVIDIA sm_86/sm_60/sm_120, gfx12 (Linux), Intel Arc i warstwy plików na Linuksie. RX 7000 ma build AppImage, ale „no RX 7000 card ran them” (release notes:81).
5. **Test:** Gyro-S nie teraz. Jeśli wracamy do Flash-Next, najpierw IQ3_S w naszym forku. Gyro-S ma sens tylko jako test progu produktowego „32 GB PC”. Kryteria zatrzymania są w §4.

## 1. Strata 0.2.0-beta vs v0.1.45

Git: 667 commitów bez merge'y (Niko1221 608, Laurent Zuijdwijk 35), 1 275 plików, +219 290/−3 168. Podział: aplikacja `apps/` +121 308 (55%), CLI/control/serve/harness/packaging +41 936 (19%), testy +22 125, **silnik** (`src include cmake sycl metal third_party`) 118 commitów, **+13 580/−781 (6%)**.

| Zmiana silnika (domyślna) | Liczby z release notes | Arytmetyka | Dla nas |
|---|---|---|---|
| Tabele przełączników sm_86/sm_60 (bitowo) | 3060 60.36→66.52, A4000 51.16→57.82, P100 36.56→41.76 | ×1.102 / 1.130 / 1.142 ✓ | nie (NVIDIA) |
| gfx12: WMMA w uwadze promptu + Q2_0 fused experts (zmienia bity, KL 0.0003/0.0015) | R9700 Q2_0 4K 1 151→2 286, 20K 1 384→2 751 | ×1.986 / 1.988 ✓ („1.99×”) | nie: gfx1100 tylko opt-in (`STRATA_HIP_WMMA=1`) |
| Linux: eksperci z page cache bez kopii, prefetch I/O, cgroup liczy czysty page cache | 12 GB emul., 32 GB RAM: dekod ×1.70–2.88 | — | wzorzec dla trybu low-RAM |
| Chunk promptu wyceniany po RAM/SSD | 3060 + emulowany SATA: 20K 334→822, 29K 419→910; odczyt 29.5→0.6 GB | ×2.46 / 2.17 ✓ | wzorzec |
| Wątki CPU = rdzenie fizyczne (limit 32) | wątki = logiczne → dekod 0.65–0.73× | — | **do sprawdzenia u nas** |
| Rozgrzewka hipBLAS na wątku przy ładowaniu | pierwszy prompt 154→673 t/s (R9700) | ×4.4 | **do sprawdzenia TTFT** |
| HIP VMM (`hipMemAddressReserve/Map`, 2 MiB) dla `--kv-grow` | — | — | pomysł: rosnący KV |
| Port Gyro (APR): trellis + Hadamard, CPU AVX2/AVX-512 | R9700 Gyro-S 85.3→89.6 vs rc2 | ×1.050 ✓ | §2 |

Wielu żądań i KV nic nowego nie dotyczy, poza `kv_q8` gather (+11% w mikrobenchu) i telemetrią batcha. **Aplikacja i Terminal** to bezpośrednia konkurencja dla UX Podkręta:
- agent oparty na przypiętym, przyciętym **DeepSeek Harness** (`dsh`, MIT), z trybami Manual/Bypass, web search i `/loop`;
- `strata launch`: kreator plus monitor z 7 widokami (hit rate ekspertów, PCIe, RAM, dysk);
- `strata connect`: pisze i sprawdza konfigurację **omp**, Claude Code, Codex, OpenCode, pi, Hermes i OpenClaw (`--check --output json`);
- podpisany kanał aktualizacji silnika (Ed25519): próbne uruchomienie przed przełączeniem, rollback;
- pobieranie po 8 połączeniach (40→77 MB/s) z przypiętym SHA-256 i rozmiarem;
- obrazki na GPU od 24 GB VRAM, niżej na CPU.

Ograniczenia: instalatory na Windows są niepodpisane, a `BENCHMARK_PROTOCOL.md` to dopiero szkic.

## 2. Gyro-S: format, jakość, gdzie działa

**Nagłówek GGUF** (zakresy HTTP, `gguf-S-TQ1_0.txt`, parser `gguf_header_parse.py`): arch `qwen4exp`, 48 warstw (36 GDN + 12 pełnej uwagi z indexerem top-k 2048), hidden 2560, **512 ekspertów, top-10**, FF 640, 1 ekspert współdzielony, hyper-connections ×4.

| Część | Typ | bpw | Rozmiar |
|---|---|---:|---:|
| Eksperci gate/up | TQK6 (typ 145) | 1.625 | 2×7.62 GiB |
| Eksperci down | TQK7 (typ 146) | 1.875 | 8.79 GiB |
| **Eksperci razem** | — | **1.708** | **24.02 GiB = 25.79 GB** |
| Gęste (Q5_K attn/SSM, Q8_0/Q6_K HC, router BF16, embed/output Q6_K) | — | — | 3.62 GiB |
| Tabela PLE (3-gramy, 16×20M wierszy × 160) | IQ4_NL | 4.5 | 26.82 GiB (na SSD) |
| **Plik** | — | — | **54.46 GiB = 58.48 GB** ✓ (HF: 58 487 015 808 B) |

- **Nic nie jest wycięte.** Wszystkie tensory ekspertów mają wymiar `[…, 512]`, czyli 48 × 512 = 24 576 ekspertów. Wagi bez PLE: 54.46 − 26.82 = **27.64 GiB** ✓ (zgadza się z kartą modelu).
- **Format:** trellis z rodziny QTIP. Stan 15-bitowy, K = 6/7 bitów na krok 4 wag. Indeks z hasha `×0x9e3779b1` wybiera 2 punkty z 2048-punktowego codebooka par fp16. Skala fp16 na 128 wag. Do tego obrót Hadamarda (Sylvester, blok 128, jawne znaki dla 640/2560). Źródła: `ggml-common-tq.h:6-16` i klucze `prism.hadamard.*`.
- **Enkoder i kalibracja są niepublikowane.** Gyro-M ma TQ2_T 2.125 bpw i PLE w Q8_0. Gyro-L ma typy 147–149, których Strata nie obsługuje.
- **Bajty/token:** gęste 3.36 GB (bez `token_embd`) plus 10 × 48 × 1 049 600 B = 0.50 GB ekspertów, razem **3.86 GB**. Aktywnych parametrów jest 6.67 B ✓. Sufit XTX to 960 / 3.86 = 249 t/s. Zmierzone wykorzystanie pasma u innych: 5090 113 t/s = 24% szczytu, R9700 (Vulkan) 57.8 t/s = 35%. Dekod jest ograniczony liczbą kerneli i obliczeniami trellisa, nie pasmem.

**Jakość:**
- **Karta modelu** (vs unsloth Q8_0, korpus 2026 tech+kod, c=2048 × 60):
  - KLD: Gyro-S 0.401 (top-1 75.3%; na kodzie 0.109), ISTA IQ2_XS 0.420, IQ3_XXS 0.311, AP-Q4_K_XL 0.107.
  - MMLU-Pro na 70 pytaniach: Gyro-S 78.1, Q4 81.4. Błąd standardowy ≈ 4.8 pkt, więc to nierozróżnialne. Autorzy sami piszą „within noise”.
  - LCB v6, 30 zadań, 1 seed: **Gyro-S 67% przy 64k**, 83% przy 128k; Gyro-M 90%/100%.
  - Pętle: 2/20 (pagoda), 0/45 w teście obciążeniowym.
- **Niezależny pomiar Straty** (GYRO.md:20-23): Gyro-S KL **0.268 vs IQ2_XS 0.236**, czyli 13.6% gorzej przy 24.3% mniejszej liczbie bajtów ✓. Na korpusie autorów kolejność jest odwrotna. Gyro-M 0.159 ≈ IQ3_XXS 0.157, ale zestaw rozumowania wypadł gorzej niż Q2_0 (49/60 vs 57/60).
- **Odniesienie:** nasz 27B UD-Q4_K_XL ma KLD-wiki 0.0153 do BF16 (16e). Protokoły są inne, ale różnica rzędu wielkości jest wyraźna `[INFERENCE]`. Najmocniej skwantowane formaty tracą dodatkowo na polskim: KLD-PL/wiki 1.24–1.44 (16e).

**Gdzie działa:**
- **Stock llama.cpp: nie.** Nasz `llama-master` zna `qwen4exp`, ale typy ggml kończą się na 42 (`ggml.h:433`), a Gyro używa 144–146.
- **agentionai/llama.cpp (GitLab):** CUDA, Vulkan, CPU. HIP kompiluje się z `ggml-cuda` (glob `mmq*.cu`), ale nie jest testowany `[INFERENCE]`.
- **Strata ≥ 0.1.45.1:** CUDA. HIP jest eksperymentalny, zwalidowany na gfx1151, uruchomiony na gfx1201. Na gfx1100 silnik tylko ostrzega „not yet validated” (`generate.cpp:3318-3320`).
- **Kernele CPU zmierzone u nas** (5700X, 2 przypięte rdzenie, `tq-cpu-bench-5700x.txt`):
  - parity daje **0 failures**;
  - TQK6/TQK7 AVX2: **565–570 µs na eksperta** (1.8–2.0 GB/s na rdzeń), czyli ×2.1 szybciej niż `vec_dot` z ggml (1 183 µs);
  - w grupie 3 tokenów 241 µs/token;
  - Q2_0 dla porównania 207 µs (6.7 GB/s): trellis na CPU jest ~3.3× droższy na bajt.

## 3. Czy zmieści się i jak szybko pójdzie na XTX

- **Pamięć:** XTX 24 GiB ≈ 3090 24 GiB. Na 3090 przy 128k kontekstu `auto` dał **15 756 slotów** (GYRO.md:217). U nas przy 32k szacuję ~16 500 `[INFERENCE]`.
- **RAM:** 25.8 GB ekspertów (mmap) + PLE na SSD, łącznie 54.6 GB z page cache przy 62 GB RAM. Mieści się.
- **Kontekst jest tani:** 64k to +1.16 GiB, bo pełną uwagę ma tylko 12 warstw, a KV ma 2 głowice. 1 GiB KV to ≈1 000 slotów, czyli −1.5 pkt proc. trafień.
- **Krzywa pokrycia** zmierzona przez Stratę dla routingu Flash-Next: **H(f) = 1 − (1 − f)³**. Punkty kontrolne: f 0.59 → 92.2%, f 0.81 → 99.4% (`generate.cpp:4445-4465`).

| na token, bez MTP | Gyro-S (16 500 slotów) | IQ3_S (9 048 slotów, jak #2938) |
|---|---:|---:|
| f / trafienia H | 0.671 / **96.5%** | 0.368 / **74.8%** |
| chybione eksperty × rozmiar | 17 × 1.05 MB = 18 MB | 121 × 2.04 MB = 253 MB |
| koszt chybień | CPU (8 rdz. × 1.85 GB/s ≈ 14.8 GB/s, ograniczenie obliczeniowe): **1.2 ms**; PCIe 4.0 ×16 (25 GB/s): 0.7 ms | DDR4 (~40 GB/s, pasmo): 6.3 ms; CPU+PCIe razem: ~3.9 ms |
| GPU przy pełnej rezydencji | 11.5–17.3 ms (R9700 57.8 t/s × 1.0–1.5 pasma) | podobnie |
| **dekod** | **~51–79 t/s** | **~43–65 t/s** |

- **Z MTP:** prose ×~1.24, kod ×~1.85 (proporcje z 5090: 140/113 i 209/113). Okno weryfikacji zwiększa liczbę chybień, ale CPU dekoduje blok raz na całe okno (241 vs 565 µs). Wynik: Gyro-S ~60–100 t/s `[INFERENCE]`.
- **Sprawdzenie modelu na 3090** (Zen 2, stare kernele `vec_dot`): prose 31.8 t/s. To ~17 ms chybień na token wyjściowy, co zgadza się z 110 ocenami ekspert×token na okno × 1.18 ms / ~6 rdzeni.
- **Liczba z #2938** (XTX + 9950X DDR5, IQ3_S, 82.5 t/s) pochodzi z powtarzanego akapitu przy T=0 i 70% akceptacji draftów. Jest zawyżona względem realnej pracy.

## 4. Działania

1. **Gyro-S na naszym boxie: nie testujemy teraz.** Gdyby wrócić do Flash-Next, test minimalny wygląda tak:
   - **(T1)** IQ3_S (84 GB, standardowe typy) w **naszym forku** (`qwen4exp` + `--moe-cache-mib`) albo w Stracie (build HIP gfx1100).
   - Pomiar: sweep T=1, code-edit, czat PL na xbench, 3 przebiegi naprzemiennie, plus nasz zestaw 20 zadań PL i 5 agentowych vs 27B.
   - **Kill:** sweep T=1 < 50 t/s albo pass rate < 27B.
   - **(T2, opcjonalnie, próg produktowy)** Gyro-S w Stracie z HIP gfx1100:
     - najpierw `native_expert_parity --load-check` (musi dać 0 failures) i 8 pytań greedy. **Kill:** jakakolwiek porażka albo śmieciowy tekst;
     - potem emulacja karty 16 GB przez `--expert-cache N` (np. 9 000 / 3 000 slotów). **Kill:** prose z MTP < 30 t/s przy 9 000 slotów.
2. **Do przejęcia (S, tanie):**
   - **(a)** krzywa H(f) = 1 − (1 − f)³ w doradcy sprzętu Podkręta: przewidywanie t/s dużych MoE z VRAM/RAM;
   - **(b)** sprawdzić domyślne `-t` w naszym launcherze: rdzenie fizyczne, nie logiczne;
   - **(c)** zmierzyć TTFT pierwszego żądania po starcie (leniwe ładowanie rocBLAS/hipBLASLt?). Jeśli płacimy, rozgrzewać na wątku przy ładowaniu;
   - **(d)** UX: odpowiednik `strata connect` z `--check --output json` dla omp/Claude Code, podpisany kanał aktualizacji z rollbackiem, przypięte SHA-256 i wielowątkowe pobieranie.
3. **Do rozważenia (M):** HIP VMM dla rosnącego KV (`3980a5ce`), żeby nie rezerwować pełnego kontekstu z góry.
4. **Nie przejmujemy:** kerneli trellis (nasz 27B jest gęsty, a enkoder jest zamknięty) ani `STRATA_ROUTE_PRIOR` (KL ×10).

## Źródła

- Release: https://github.com/Niko1221/Strata/releases/tag/v0.2.0-beta (2026-10-19 13:52 UTC; `21n-notatki/release-notes-0.2.0-beta.md`); `git diff v0.1.45 v0.2.0-beta`.
- Strata @ `3d1fb480`: `docs/GYRO.md`, `docs/MODELS.md:74-101`, `docs/AMD_HIP.md`, `README.md:151-175`, `src/program/generate.cpp:3305-3320, 4445-4485`, `third_party/ggml/ggml-common-tq.h`, `strata_cli/launch/harness.py:219`, `apps/desktop/scripts/stage-harness.mjs:3`.
- Karta i API HF: https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-GGUF (sha `aa0a0c3e`, 2026-10-16); nagłówki GGUF (pierwsze 32 MiB plików S/M/L/MTP).
- agentionai/llama.cpp: https://gitlab.com/agentionai-group/llama.cpp @ `9aa51ce4`.
- Issue #2938 (XTX IQ3_S): https://github.com/Niko1221/Strata/issues/2938.
- Karta Qwen3.8-Flash-Next (benchmarki vs 27B): https://huggingface.co/Qwen/Qwen3.8-Flash-Next.
- Nasze: 16e (KLD 27B), REKORDY.md (27B 100/170 t/s), 21g, `hardware/rx-7900-xtx.md`.

## Do bazy wiedzy

| Folder | Tytuł | Treść |
|---|---|---|
| `repo/strata.md` (aktualizacja) | Strata 0.2.0-beta | 0.2.0 = aplikacja + Terminal + silnik 0.1.45.3. Silnik to 6% zmian (+13 580/−781 z +219 290). Dla gfx1100 nic nowego w prędkości (build RX 7000 nieuruchomiony). gfx12: prompt ×1.99. sm_86/sm_60: ×1.10–1.14. Linux: zero-copy page cache, dekod ×1.16–2.88 (emul.). Wątki = rdzenie fizyczne. `strata connect` obsługuje omp. Agent na DeepSeek Harness. |
| `modele/` (nowa) | Qwen3.8-Flash-Next Gyro (APR) | Gyro-S: eksperci TQK6/TQK7, 1.708 bpw, 24.02 GiB; wszystkie 512 × 48 ekspertów; PLE IQ4_NL 26.82 GiB na SSD; plik 58.48 GB; wagi 27.64 GiB. Działa tylko w agentionai/llama.cpp i Stracie (typy 144–146), na AMD zwalidowany tylko gfx1151. KL wg Straty 0.268 vs IQ2_XS 0.236; LCB 67% przy 64k. |
| `kernele/` lub `lekcje/` | Krzywa pokrycia cache ekspertów Flash-Next | H(f) = 1 − (1 − f)³ (Strata, zmierzone: f 0.236 → 69.2%, 0.59 → 92.2%, 0.81 → 99.4%). Zależy od routingu modelu, nie od kwantu. |
| `eksperymenty/` | 2026-10-19 trellis CPU na 5700X | `tq_cpu_parity` 0 failures; TQK6/TQK7 AVX2 565–570 µs na eksperta (1.8–2.0 GB/s na rdzeń), ×2.1 vs ggml `vec_dot`; Q2_0 207 µs (6.7 GB/s). |
| `research/` | Raport 21n | Werdykt: Gyro-S to próg 32 GB, nie nasz. U nas IQ3_S (~50 GB RAM). Szac. XTX Gyro-S 51–79 t/s bez MTP vs IQ3_S 43–65 `[INFERENCE]`. Kill-kryteria T1/T2. Do przejęcia: krzywa H(f), wątki fizyczne, rozgrzewka BLAS, connect/aktualizacje. |
