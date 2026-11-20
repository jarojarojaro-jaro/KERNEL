# Własne runtime'y pod AMD: hipfire, Strata, TensorFold, Lemonade (+ HRX od AMD) — delta względem naszych notatek

Stan klonów (`git -C ~/research/engines/<x> log -1 --format='%h %cs'`):
- hipfire `d435a75 2026-11-15` (v0.4.7),
- Strata `3142b66 2026-11-20` (aplikacja 0.2.7, silnik 0.1.49.x),
- TensorFold `124052c 2026-11-20` (po 1.3.0),
- Lemonade `41736cb 2026-11-20`.

Klony są płytkie (1 commit), więc historię zmian czytam z CHANGELOG-ów i release notes. Nic nie było budowane ani uruchamiane.

Czego tu NIE powtarzam, bo jest już w naszych notatkach:
- hipfire do v0.4.2: Redline/PM4, DFlash2 B=16, prefill W4A4, ldsstage/ksplit, X128, liczba magiczna 1,5·2²³ (`~/KERNEL/qwen-opt/research/repos/30-hipfire.md`);
- Strata do v0.1.44: replay GDN, pair launch, interleaved q8_1, PR #2231 i #2226, metodologia (`~/KERNEL/qwen-opt/research/strata/*`);
- TensorFold do 1.0.11: drzewa, rollback przez replay, `qmm_rocm.cu` dla R9700 (`~/KERNEL/qwen-opt/research/tensorfold/*`);
- Lemonade jako produkt i instalator (`~/KERNEL/product/research/03-silniki-i-stack.md` §2).

Punkt odniesienia (z `CONTEXT.md` i `~/praca/enigma-turbo-k/COLLAB.md`):
- Turbo na XTX, Qwen3.8-27B Q4_K_M:
  - dekod 45,9 t/s, 21,7 ms/token, z czego przerwy między kernelami 2,47 ms (541 kerneli, mediana przerwy 3,56 µs, `COLLAB.md:142`);
  - `k_norm_q8` 0,79 ms (131 × 6,0 µs, `COLLAB.md:142`).
- Turbo już ma:
  - wielozadaniowy GEMV na aktywacjach int8 (`k_gemv_q8_multi`, `src/gpu/gpu_forward.hip:309-330`);
  - weryfikację 9–16 kolumn na int8 WMMA w tej samej kolejności sumowania co GEMV (`gpu_forward.hip:332`);
  - siatkę GDN (Hv, dv/32), czyli 192 bloki (`gpu_forward.hip:2352,2408`);
  - flash-decoding dla N ≤ 8 (`COLLAB.md:140`);
  - zredukowany słownik draftu 64k: 66,9 → 71,1 t/s (`src/cli/main.cpp:140`);
  - ogon lookupu W ≤ 8 (`COLLAB.md:288-321`).

---

## A. hipfire (Rust + HIP, tylko AMD) — największa delta

### 1. Co to jest
`d435a75 2026-11-15`, v0.4.7 (bugfix na 0.4.6). Między v0.4.2 a v0.4.7 przybyło ok. 1200 linii CHANGELOG-u (`CHANGELOG.md:1-1217`). Najważniejsze dla nas są trzy PR-y społeczności (@Ben1078) pod gfx1100 i Qwen3.8-27B z MTP oraz to, że retained PM4 stał się domyślny na XTX.

### 2. Architektura: co się zmieniło
- **Spekulacja MTP na XTX przeskoczyła o ~30%** dzięki trzem zmianom, wszystkie domyślnie włączone na gfx1100 i wszystkie „NUMERIC, not byte-identical” (bramka KLD, nie bitowa) (`README.md:115-130`):
  1. GEMV na aktywacjach int8 dla weryfikacji 2–5 wierszy (#987). Wcześniej szły przez kafel WMMA f16, w którym 12 z 16 kolumn to padding (`CHANGELOG.md:1140`).
  2. Atencja weryfikacji na WMMA z podziałem K dla 1–8 wierszy (#989, `CHANGELOG.md:1145`).
  3. Draft MTP po podzbiorze 65 536 tokenów wyciętym z lm_head (#998, `CHANGELOG.md:1107`).
- **Retained PM4 jest domyślny na gfx1100** dla `.mq4r` i od v0.4.5 także dla dense `.mq3-xt`, w trybie AR bez draftu (`CHANGELOG.md:486`). Wcześniej blokowały go kernele ze scratch, a teraz jest jeden `COMPUTE_TMPRING_SIZE` na trasę plus ring pamięci na kolejkę (`CHANGELOG.md:475`).
- **Polityka spekulacji:**
  - `speculation.mtp=auto` dla Qwen3.5/3.6/3.8 **zostawia zwykły AR**, dopóki producent nie zadeklaruje zmierzonej „podłogi AR” (`CHANGELOG.md:1410`). MTP na 27B jest więc u nich opt-in.
  - DFlash odchodzi do AR, gdy cykl przestaje się opłacać. Próg: `base + per_row × verified_rows + per_1k_ctx × pos/1024`, a pierwsze 8 cykli oceniane jest wcześniej (`CHANGELOG.md:782,1497`).
- **Lookup wewnątrz okna DFlash2** (domyślnie, `CHANGELOG.md:1361`):
  - okno „Copy” zastępuje drafty kandydatami z lookupu;
  - okno „Tail” to K draftów + L z lookupu, K+L ≤ 15;
  - kontroler wybiera okno lookup tylko wtedy, gdy zmierzona akceptacja żądania na zmierzoną cenę okna bije okno bazowe.
- **gfx1201 TP4:** cały token jako jeden graf, kolektyw jako jeden kernel `push-reduce` (`CHANGELOG.md:1023`). Dla nas bez znaczenia (jedna karta), ale pokazuje skalę kosztu launchy: 1650 kerneli/token/rank i ~40% czasu tokenu w bezczynności.
- **Railgun** (cały token jako certyfikowany program PM4) na gfx1100 jest wstrzymany: port transportu tylko na CPU, „never run on a device”, szacunek 5–10 dni pracy (`STATE.md:1-35`).

### 3. Techniki z liczbami (7900 XTX, Qwen3.8-27B `mq4-xts` 15 GB, KV Q8)

| Technika | Mechanizm | Liczba | Źródło | Bitowo? |
|---|---|---|---|---|
| Int8 GEMV dla weryfikacji 2–5 wierszy | aktywacje kwantyzowane raz na grupę projekcji (int8, skala na 32); `v_dot4_i32_iu8`; wariant v4 to trwała siatka, całe K w LDS, 3-poziomowy ring wag non-temporal dwordx4; bliźniak `_multi` obsługuje do 4 wag na jednym wejściu | MTP K=3: code-1k 104,7 → 127,4 (×1,217), prose-1k 106,7 → 131,1, code-32k 81,8 → 95,5, prose-32k 51,7 → 58,9; KLD WT2 0,041142 → 0,041110 (w CI) | `CHANGELOG.md:1140`; `kernels/src/gemv_mq4g256v2_q8x.hip:1-38` | nie (bramka KLD) |
| Atencja weryfikacji WMMA, split-K | blok = (głowa kv, zakres kluczy); kafle 32 kluczy z przeplotem między blokami; K i Vᵀ dekwantyzowane Q8→f16 do LDS; S=K·Qᵀ i O=Vᵀ·Pᵀ na WMMA dla 6 głów q × wierszy; leniwy rescale (próg 8 w log2); redukcja zakresów osobnym kernelem | sam: 9K 64,8 → 69,6 (+7%), 39K 51,8 → 64,3 (+24%), 101K 43,6 → 68,5 (+57%); razem z #987: code-32K 95,7 → 121,2, prose-32K 59,0 → 73,3; 1K bez zmian | `CHANGELOG.md:1145`; `kernels/src/attention_verify_wmma.gfx1100.hip:1-33` | nie |
| Bariera tylko na LDS | `s_waitcnt lgkmcnt(0); s_barrier` między `sched_barrier(0)`; `__syncthreads()` w trybie WGP czeka na vmcnt(0) i unieważnia L0, więc serializuje prefetch rejestrów | część wyniku #989 (bez osobnej liczby) | `attention_verify_wmma.gfx1100.hip:50-58` | tak |
| Draft po 65 536 tokenach | wiersze podzbioru kopiowane z lm_head (178 MiB); weryfikacja bez zmian | +7,5% przy 9K, +1,7% przy 39K, +3% na krótkich | `CHANGELOG.md:1107` | rozkład tak, tekst nie |
| Wynik łączny MTP na XTX | #987 + #989 + #998 | code-1K 136,5–136,8; prose-1K 141,1; code-32K 129,5–129,9; prose-32K 79,7–80,1 t/s | `README.md:219` | nie |
| Retained PM4 (Redline) w AR | ten sam kod obiektowy co graf HIP, wysyłany jako zatrzymany bufor PM4 | 27B `.mq3-xt`, XTX: story 53,4 → 62,5 t/s (×1,170), po prompcie 4,5K 50,6 → 58,7 (×1,161); bench 53,73 → 62,81; soak 1923 s bez zawieszeń; identyczne id tokenów | `CHANGELOG.md:477,484-488` | **tak** |
| Lookup w oknie DFlash2 | Copy/Tail, wycena per żądanie | R9700: zadania z kopiowaniem 199,7 → 279,1 t/s (+39,8%), cytaty 2K/8K/25K +111,6%; edycja kodu −1,0%, tool edit −8,5% | `CHANGELOG.md:1361-1362` | nie (zmienia wiersze weryfikacji) |
| FA2 split-KV dla weryfikacji DFlash na długim kontekście | domyślnie na gfx1100 przy kontekście > 4096 | W7900, 21,6K tokenów: 43,5 → 49,4 t/s (+13,6%), AR 36,2 | `CHANGELOG.md:1655` | nie |

Deklarowane a sprawdzalne:
- Wszystkie liczby z tabeli to ABBA na świeżych procesach, z receipts na maszynie „hipx” (nie w repo).
- Wiersze #987/#989 częściowo mierzył autor PR-a, a bramkę maintainera opisano osobno (`README.md:107-113`).
- Repo samo zastrzega, że to pomiary na jednym promptcie i jednej karcie, a nie ogólne twierdzenia (`README.md:107-110`).
- **Model ma 15 GB i KV Q8, a numeryka nie jest bitowa.** Z naszymi 16,5 GB i regułą „spec == plain bit w bit” nie da się tego porównać 1:1.

**Porównanie z Turbo:**
- MTP u hipfire 136–141 t/s przy 1K i 80–130 przy 32K. U nas spec na długich promptach 95–99 (2k/8k), a produkcja 140–159.
- **hipfire przegonił nasz poprzedni wniosek z `30-hipfire.md`, że „MTP na XTX nie dobije do 100”**, i to przy 32K kontekstu.
- Główne źródła ich przewagi przy 32K to atencja weryfikacji (+24…57%) i ogólnie tańsza weryfikacja `[INFERENCE: z rozbicia #987/#989]`.

### 4. Co bierzemy do Turbo
Zbiorczy ranking jest na końcu notatki. Z hipfire są tam punkty 1, 2, 4 i 5.

### 5. Werdykt
hipfire to dziś najszybsza na XTX publiczna ścieżka dla Qwen3.8-27B z MTP przy długim kontekście. Kosztuje to jednak numerykę nie-bitową i własny format wag. Dla nas najcenniejsze są: projekt kernela atencji weryfikacji (WMMA, 6 głów q na blok, LDS-only barrier) i liczby z retained PM4 (+16–17% AR, bitowo).

---

## B. Strata (C++/CUDA/HIP/SYCL/Metal, silnik pod Qwen3.8-Flash-Next MoE i DeepSeek V4.1)

### 1. Co to jest
`3142b66 2026-11-20`. Od v0.1.44.1 (nasza ostatnia notatka) Strata stała się aplikacją 0.2.x z Terminalem i paczkami silnika per karta (`docs/release-notes-0.2.0.md:1-25`). Doszedł DeepSeek V4.1-Flash z ekspertami na SSD (`docs/release-notes-0.2.4.md:3`). **Gęstego 27B nadal nie obsługuje** (README, sekcja Models: Flash-Next i Qwen3.6-35B-A3B).

### 2. Architektura: delta
- Pakiety `hip-rdna3` (gfx1100/1101/1102/1151) są budowane, ale „The maintainers have not run them on an RX 7000 or a Strix Halo card” (`release-notes-0.2.0.md`, Known limits). Wszystkie twarde liczby AMD pochodzą z R9700 (gfx1201).
- Domyślne ustawienia zmieniające bity włączają się tylko po bramce KL (0,0003 / 0,0015 przy prompt attention WMMA na gfx12, `release-notes-0.2.0.md`, New defaults). Bez zmian względem metodologii z naszych notatek.
- DFlash2 jest opt-in. „Auto means MTP, because no card has shown DFlash2 winning everywhere yet” (`release-notes-0.2.3.md:7`).
- Opcjonalne „przybliżone czytanie ostatnich 12 warstw” długiego promptu (`STRATA_KVA=1`) jest stratne: +11% przy 14K i +18% przy 30K na RTX 5070. Domyślnie wyłączone, bo psuło zadania agentowe (`release-notes-0.2.7.md:39`). **Nie dla nas.**

### 3. Techniki z liczbami (nowe od 0.1.44)

| Technika | Liczba | Źródło | Dotyczy nas? |
|---|---|---|---|
| **Kolejność otwierania kolejek HW (queue priming).** Dwa strumienie tworzone na głównym wątku przed startem innych, żeby MES nie posadził dwóch najgorętszych kolejek na jednym compute pipe | R9700, prompt 4K: 10 z 32 świeżych startów wolnych (1980 vs 2290 t/s), po poprawce 0 z 32; 5 kolejek kosztuje dekod −2…−3,6% | `engine/src/program/generate.cpp:3406-3467`; `release-notes-0.2.1.md`, New defaults | tak, jeśli używamy >1 strumienia (prefill/kopie); tani test na „bimodalność” pomiarów |
| `hipStreamWriteValue32/WaitValue32` vs jednowątkowy kernel flagi | natywne 13 µs, ale „not reliable in the engine's multi-stream use”: 3 różne wyjścia na 5 przy 26K; kernel z `__threadfence_system` 20 µs, deterministyczny | `engine/src/split/src/hip/cuda.h:17-53` | ostrzeżenie: nie używać natywnych memops HIP do synchronizacji z hostem |
| Persistent kernel z grid barrier na gfx11/12 | gfx11/12 nie mają `s_memrealtime`, więc nie ma timeoutu bariery i ścieżka jest wyłączona; R9700 „neutral to 1% slower” (#2226) | `engine/src/kernels/cuda/fused_gr.cu:3340-3367` | dowód przeciw megakernelom na barierze siatki na RDNA3/4 |
| Zawieszenie pierwszego okna weryfikacji na HIP | kernel czekał na flagę, którą host podnosił dopiero po powrocie z launcha; 8 na 41 przebiegów na Strix Halo, po poprawce 0 na 46 | `release-notes-0.2.2.md:47` | lekcja dla mapowanej pamięci i flag w grafie |
| Słownik draftu tylko EN (`--mtp-draft-vocab draft_vocab_en.bin`) | +2,7…+3,1% dekodu na tekście EN | `release-notes-0.2.7.md:43` | już mamy 64k |
| Bezczynność GPU na 1 karcie | dekod zostawia 5% czasu karty bezczynne (2 karty: 47–49%) | `release-notes-0.2.2.md:28` | punkt odniesienia: u nas przerwy = 11% (2,47/21,7 ms) |

### 4. Co bierzemy
Queue priming jako test: godziny pracy, zysk tylko przy wielu strumieniach. Do tego dwie lekcje negatywne: natywne memops HIP i bariera siatki na gfx11.

### 5. Werdykt
Strata od października rozwija produkt i MoE/SSD. Dla gęstego 27B na XTX nowych kerneli nie ma, a XTX nie jest testowany przez autorów.

---

## C. TensorFold (Zig + Metal/CUDA, od 1.1.x także natywny HIP)

### 1. Co to jest
`124052c 2026-11-20`, po wersji 1.3.0 (`CHANGELOG.md:182`). Od 1.0.12 ma opt-in natywny silnik HIP dla Qwen3.5/3.6/3.8 i Flash-Next: lane rounds, MTP, radix prompt cache, TP przez RCCL (`CHANGELOG.md:2957-2969`).

### 2. Architektura: delta
- Pracę HIP robi społeczność, prawie wyłącznie na gfx1151 (Strix Halo) i gfx1201. **gfx1100 tylko kompiluje się**: „It has not run on a gfx1100 GPU yet” (`CHANGELOG.md:2246`). Maintainer nie ma karty AMD (`CHANGELOG.md:1613`).
- Kontrakt bitowy zostaje: drafted == serial, każda zmiana HIP opisana jest jako „same bytes”.
- Prompt cache przez radix pool i snapshoty GDN na granicach chunków. Bez zmian względem `tensorfold/qwen27.md` §1.7.

### 3. Techniki z liczbami (HIP, gfx1151, Qwen3.8-27B MLX 4-bit, chyba że podano inaczej)

| Technika | Liczba | Źródło | Bitowo? |
|---|---|---|---|
| Rekurencja GDN w prefillu: pół value-head na blok | prompt −5…6% czasu (27B) | `CHANGELOG.md:1040` | tak (u nas siatka dv/32 już jest) |
| Score atencji dekodu: 4 klucze na warp przy długich zakresach, 2 przy krótkich | dekod +7,5…+18,9% przy 32K i 64K | `CHANGELOG.md:1842` | tak |
| Lane round > 4 wierszy: wagi z cache zamiast z DRAM dla każdego bloku wierszy | 27B przy 16 strumieniach 51 → 75 t/s (code) | `CHANGELOG.md:1613` | tak |
| Zaokrąglenie do typu aktywacji w kaflu zamiast osobnego castu | cold prompt +2…3% | `CHANGELOG.md:2014` | tak |
| Kafel prompt attention: P w rejestrach, 6 fal/SIMD | TTFT +1…5% (2K–64K) | `CHANGELOG.md:2036` | tak |
| Wycena okien kopiowania z własnych zmierzonych rund; kopia droższa niż zysk jest przycinana | brak liczby | `CHANGELOG.md:245` | tak |
| **Wynik negatywny: „rows together”** (3–4 wiersze w jednym strumieniu dot) | launche 3…16% szybsze, 1 strumień +3,4…5,9%, ale 2 strumienie greedy −3,2% i −2,3%, bo tańsze wąskie okna sprawiły, że polityka draftowała płycej | `docs/optimization-ledger.md:544-551` | — |
| Wynik negatywny: fuzja małych kerneli (Flash-Next HIP) | przerwa między dispatchami: mediana 2,0 µs; najtańszy kernel 1,3 µs; fuzja szacowana na 2,4–4,0% rundy, poniżej progu | `docs/optimization-ledger.md:514-520` | — |
| Wynik negatywny: prefetch i podwójne buforowanie kafli strumieniowych | 0 zysku | `docs/optimization-ledger.md:522-528` | — |

### 4. Co bierzemy
Lekcję z „rows together”: polityka głębokości draftu oparta na zmierzonych kosztach może zjeść zysk z szybszego kernela. Każdą zmianę kosztu weryfikacji mierzyć end-to-end z polityką, nie samym kernelem. Dodatkowo dane, że przerwa ~2 µs na gfx1151 to rząd wielkości naszych 3,56 µs.

### 5. Werdykt
HIP w TensorFold to dziś port społecznościowy pod Strix Halo, bez pomiarów na XTX. Nie ma od nich kernela do wzięcia na gfx1100.

---

## D. Lemonade (C++, router/serwer AMD) i HRX (nowy runtime AMD)

### 1. Co to jest
`41736cb 2026-11-20`. Sam Lemonade nie ma kerneli. Uruchamia llama.cpp (ROCm/Vulkan/CPU), FLM i RyzenAI (NPU), vLLM (gfx1151) oraz od niedawna **`llamacpp-hrx`** (`README.md:190-195`; `docs/dev/backends-reference.md:57`: „experimental, linux, amd_gpu (gfx1100, gfx1151)”).

### 2. Architektura: co nowego
- **HRX** („HIP Runtime Extended”, https://github.com/ROCm/hrx-system) to lekki runtime AMD:
  - `libhrx` ok. 2 MiB, z jawnymi command bufferami;
  - JIT kernela (Loom) w ~1–15 ms;
  - bez ROCr i bez prekompilowanych bibliotek;
  - opcjonalna warstwa zgodności z HIP (88% API).
- Do llama.cpp jest backend `ggml-hrx` (RFC: https://github.com/ggml-org/llama.cpp/discussions/27219, PR #27218). Projekt (https://github.com/user-attachments/files/31165074/hrx-backend-architecture.md):
  - cały `ggml_cgraph` importowany i dopasowywany lokalnymi „przepisami” fuzji (root = matmul/atencja);
  - z tego powstaje `CommandProgram` ze specjalizowanymi kernelami, arena tymczasowych buforów i nagrany graf HRX;
  - na gorącej ścieżce tylko podmiana wejść i replay.
- AMD deklaruje „lower per-dispatch overhead to similar levels as is seen in the graphics pipelines”, a wobec lepszego z HIP/Vulkan „30-50% prefill, parity to 15% non-MTP decode”. Bez liczb bezwzględnych (RFC).
- Lemonade ma nocny dashboard regresji forków llama.cpp: https://bench.lemonade-server.ai/regressions, API `/api/regressions/<sha>`. Rejestr forków: `src/cpp/resources/benchmark_forks.json:1-120`. Wszystkie runnery to Strix Halo.

### 3. Liczby (zewnętrzne)

| Pomiar | Liczba | Źródło |
|---|---|---|
| HRX vs HIP, Qwen3-30B-A3B Q4_K_M, gfx1151 | tg128 85,1 vs 68,0 (+25,1%); pp128 +123%; pp16 −28% (HIP lepszy poniżej ~32 tokenów) | komentarz w dyskusji #27219 (https://github.com/ggml-org/llama.cpp/discussions/27219) |
| Kolejność siatki split-KV decode (kv_block, kv_head) → (kv_head, kv_block) | powyżej ~8K kluczy zbiór roboczy wypada z 32 MB MALL: 250 µs → 97,5 µs na warstwę (67 → ~170 GB/s), bitowo to samo | jw., komentarz z 2026-09-19 (fix 4) |
| Lemonade nightly, **Qwen3.8-27B**, gfx1151, kontekst 4k | tg: HRX 8,45 (Q4_K_M); ROCm nightly 17,43; Vulkan 16,79; AMD gfx11 fork 17,14 (Q4_K_XL) | `https://bench.lemonade-server.ai/api/regressions/e938896995db426e675e1a592740e6254eafe6b4` (pobrane 2026-11-20) |
| Lemonade nightly, Qwen3-30B-A3B, gfx1151, 4k | tg: Vulkan 54,6 vs ROCm stable 41,7 | jw. |

Deklarowane a sprawdzalne:
- „+15% decode” HRX to deklaracja AMD bez liczb.
- Jedyny niezależny pomiar (+25% tg) dotyczy MoE 30B-A3B na gfx1151.
- **Na Qwen3.8-27B ścieżka HRX jest dziś 2× wolniejsza od HIP** (8,45 vs 17,4 t/s w nocnym benchu), więc pokrycie hybrydy GDN jest jeszcze niedojrzałe `[INFERENCE: z jednego punktu dashboardu]`.

### 4. Co bierzemy
- Na dziś nic do kodu. Obserwować HRX jako przyszłą tanią drogę do niskiego kosztu dispatchu na AMD, alternatywę dla własnego PM4.
- Teraz bierzemy tylko trik z kolejnością siatki split-KV (punkt 6 rankingu).

### 5. Werdykt
Lemonade to orkiestrator. Ciekawy jest HRX: AMD samo przyznaje, że koszt dispatchu przez ROCm/HIP jest problemem na kartach klienckich, i buduje własny runtime z command bufferami i replayem całego grafu.

---

## E. Ranking trików do wzięcia do Turbo

Liczby Turbo: dekod 21,7 ms/token, z czego przerwy 2,47 ms. 1 ms/token ≈ +4,8% plain.

| # | Trik (skąd) | Gdzie w Turbo | Szacowany zysk | Koszt | Ryzyko dla bezstratności |
|---|---|---|---|---|---|
| 1 | **Atencja weryfikacji/dekodu na WMMA dla długiego kontekstu** (hipfire #989): blok = (głowa kv, zakres kluczy z przeplotem kafli po 32), K i Vᵀ f16 w LDS, S i O na WMMA dla 6 głów q × N wierszy, leniwy rescale, osobny reduce zakresów | zastąpić `k_attn_w`/`k_attn_comb` (flash-decoding VALU, `COLLAB.md:140`) jednym kernelem dla N = 1..8 | hipfire: +24% przy 39K, +57% przy 101K, 1K bez zmian. U nas zysk tylko przy ≥16–32K: przy 32K atencja czyta 16 warstw × 64 KB × 32K ≈ 2 GB na krok, więc przy ~300 GB/s ok. 7 ms, a przy ~800 GB/s ok. 2,6 ms `[INFERENCE: przepustowości naszego kernela nie znam; zmierzyć rocprofv3 przy 32K]` | 4–6 dni | **bezstratne, jeśli** ten sam kernel liczy N=1 i weryfikację, a podział zakresów zależy tylko od długości kontekstu. Wiersze WMMA są od siebie niezależne. Wymaga bramki vs llama.cpp (inna kolejność sumowania niż obecna) |
| 2 | **Retained PM4 zamiast `hipGraphLaunch`** (hipfire Redline; kernargi w VRAM, CS_PARTIAL_FLUSH + ACQUIRE_MEM między zależnymi) | grafy dekodu/MTP/weryfikacji (`gpu_forward.hip:1907-1960,2437-2446`) | hipfire na XTX, 27B, AR: ×1,16–1,17 bitowo (`CHANGELOG.md:488`). U nas sufit to przerwy 2,47 ms. Przy −1…2,4 µs/dispatch × 541: −0,5…−1,3 ms → **+2,5…6,5% plain**, podobny ms-zysk na krok spec `[INFERENCE]` | 2–4 tyg. | bitowe (te same kernele). Ryzyko: zawieszenia GPU i utrzymanie. Najpierw tani test: `HIP_FORCE_DEV_KERNARG=1` (domyślnie 1 w aktualnym HIP, „2-3 µs for some kernels”, https://rocm.docs.amd.com/projects/HIP/en/latest/reference/env_variables.html) i etap 0 z `30-hipfire.md` §4 |
| 3 | **Norma+q8 w producencie przez „ostatni blok”** (Strata #2231 „producer writes q8_1”; hipfire fused RMSNorm/rotate/quant; TF last-arriving block) | GEMV `down`/`out` z `accumulate`: licznik atomowy, ostatni blok liczy sumę kwadratów i q8 całego wektora (5120 wartości) w tej samej kolejności co `k_norm_q8` | do −131 launchy i przerw: 0,79 ms pracy + ~0,45 ms przerw (131 × 3,56 µs) → ok. −0,5…0,8 ms → **+2…4%** `[INFERENCE]`. Uwaga: prolog w GEMV dał −43%, epilog −7% (`COLLAB.md:142`), więc to inny wzorzec (jeden blok, nie każdy) | 2–3 dni | bitowe, jeśli redukcja w tej samej kolejności co `k_norm_q8` |
| 4 | **Polityka spec z ceną per cykl i odejściem do AR** (hipfire `base + per_row·rows + per_1k_ctx`, TF wycena okien kopiowania z własnych rund) | `src/runtime/spec_engine.cpp` | tam, gdzie spec przegrywa z plain (proza przy T>0, długi kontekst): unika strat; przy kodzie ~0 `[INFERENCE]`. Przy okazji: mierzyć politykę end-to-end, bo „rows together” w TF pokazał, że szybszy kernel potrafi obniżyć tok/s przez płytsze drafty | 1–2 dni | bezstratne (wybór okna nie zmienia tekstu przy naszym bitowym verify) |
| 5 | **Ogon lookupu do W = 16** (hipfire Copy/Tail: +39,8% na kopiowaniu, +111% cytaty; produkcja W=16 do 400 t/s) | `gpu_generate.h`, `lookup_max_w` 8 → 16; weryfikacja 9–16 już jest (`gpu_forward.hip:332`) | na `--bench-copy` od ~222 t/s w stronę 350–400 (`COLLAB.md:317`). Potwierdzenie z zewnątrz, nie nowy pomysł | 1–2 dni | bezstratne |
| 6 | **Kolejność siatki split-KV: (kv_head, kv_block)** (HRX, dyskusja #27219) | siatka `k_attn_w` (`gridDim.z = S`): sprawdzić, czy bloki jednej głowy kv idą po sobie | na gfx1151 2,6× szybszy producer powyżej 8K. XTX ma 96 MB Infinity Cache, więc próg wyżej (≈24K+) `[INFERENCE]` | godziny | bitowe (zmiana tylko kolejności bloków) |
| 7 | **Bariera tylko na LDS** (`s_waitcnt lgkmcnt(0); s_barrier` + `sched_barrier`) | kernele z prefetchem do rejestrów: MMQ prefill, `k_attn_gqa`, wide-verify WMMA | kilka % w tych kernelach `[INFERENCE]`; prefill 80% GEMM | 1 dzień + audyt ISA | bitowe |
| 8 | **Queue priming** (Strata) | start serwera, jeśli >1 strumień | usuwa bimodalne starty (u nich 10/32 → 0/32, −13% przy złym starcie) | godziny | bitowe |

Nie bierzemy:
- **Int8 GEMV dla weryfikacji (hipfire #987).** Już mamy (`k_gemv_q8_multi`) i to bitowo. Ich +22% to nadrobienie złej ścieżki f16 WMMA.
- **Draft 65k.** Mamy (+6% u nas).
- **Persistent kernel na barierze siatki.** R9700 neutralnie, a gfx11 nie ma timera do bezpiecznej bariery.
- **KVA Straty** (stratne).
- **Kernele TensorFold HIP** (gfx1151, brak danych z XTX).
- **HRX dziś** (27B 2× wolniej od HIP na nocnym benchu).

Wymóg „bez zmiany formatu wag” wyklucza też formaty MQ4/MQ3 z FWHT i W4A4 hipfire (bez zmian względem `30-hipfire.md`).

## F. Werdykt jednym zdaniem
Z czterech projektów tylko hipfire ma świeże, zmierzone na XTX i 27B kernele: atencję weryfikacji WMMA (do +57% przy 101K) i retained PM4 (+17% AR bitowo). Do Turbo bierzemy więc kolejno: atencję WMMA dla długiego kontekstu, PM4 (albo HRX, gdy dojrzeje) i przeniesienie normy+q8 do producenta. Strata, TensorFold i Lemonade dają głównie lekcje negatywne i pomiarowe.
