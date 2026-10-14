# 17 — NVIDIA/TileGym

Klon `--depth 1`, commit c742afc (2026-10-09). Ścieżki plików są względem korzenia repo. Ścieżki naszego forka zaczynają się od `~/llama-master/ggml/src/ggml-cuda/`.

## 1. Co to jest
TileGym to biblioteka przykładowych kerneli NVIDIA w CUDA Tile (cuTile Python, w mniejszym stopniu TileC++, Triton-TileIR i cuTile-rs) oraz łatki podmieniające kernele w modelach HF transformers. Wśród tych modeli są **Qwen3.5** i **LFM2-8B-A1B**, czyli nasze rodziny (`ROADMAP.md:76-92`). Wymaga CUDA 13.1+ i Blackwella albo Ampere'a (`README.md:34`), wszystko testowano na B200 (`ROADMAP.md:82-92`, `tests/benchmark/README.md`). Repo jest aktywne: 423 commity, push 2026-10-14, 826 gwiazdek, licencja MIT (`README.md:227`).

Repo nie publikuje **żadnych** liczb wydajności. Wyniki benchmarków są tylko artefaktami CI (`.github/infra_overview.md:27-28`). Twierdzenia o przyspieszeniach („2–10×”, „78×”) pochodzą z dokumentów dla agentów i porównują z naiwnymi wersjami, a nie z cuBLAS/FlashInfer.

## 2. Kluczowe techniki (z dowodami)
1. **GDN decode, wariant „decode_vstream”** (`src/tilegym/ops/cutile/recurrent_gated_delta_rule.py:233-341`). Działa tylko przy T=1 (`:478-485`).
   - Wyjście liczone jest algebraicznie ze stanu **sprzed** aktualizacji: `out = γ·(Sᵀq) + δ·(k·q)` (`:321-326`). Iloczyn skalarny `k·q` liczony jest raz na token (`:296`). Dzięki temu obie redukcje po stanie (`Sᵀk` i `Sᵀq`) są niezależne i biegną równolegle.
   - W wersji standardowej (`:101-106`, `ops/tilecpp/recurrent_gated_delta_rule.cuh:148-166`) najpierw idzie redukcja `Sᵀk`, potem aktualizacja stanu, a dopiero potem redukcja `S'ᵀq`.
   - Stan jest strumieniowany kaflami 128×16 przez rejestry zamiast trzymania całego kafla.
   - Domyślnie BLOCK_V=32 i STREAM_V_TILE=16 (`:533-542`), czyli dla HV=48 i V=128 jest to 192 bloki.
   - Autotuner celuje w ok. 2× przesubskrybowanie SM (`:344-350`).
   - Brak liczb.
2. **Chunked GDN (prefill)**, port FLA w trzech uruchomieniach: cumsum, intra-chunk (WY), inter-chunk (`chunk_gated_delta_rule.py:399-466`). Repo podaje wnioski o numeryce:
   - Odwrotność metodą Neumanna przez potęgowanie jest używana **tylko gdy ‖A‖∞ < 1**, bo w FP32 powstają człony anulujące się rzędu 1e15 przy skorelowanych kluczach (`:44-68`).
   - Przy kluczach z normą L2 (nasz przypadek, Qwen) zawsze wybierany jest dokładny szeregowy solve, „żeby małe różnice prefillu nie zmieniały dekodowania” (`:154-159`).
   - Bufory pośrednie są w bf16, co połowi ruch między kernelami (`:384-397`).
3. **Flash decode GQA** (`ops/cutile/flash_decode.py`):
   - zamiana operandów `mma(k, q)`, w której KV wypełnia wymiar M, a grupa głów Q wymiar N (≥8) (`:113`, `:315`);
   - suma softmaxu odroczona: `l_i` jest kaflem per element, a redukcja następuje raz na końcu (`:82`, `:128`, `:150`);
   - split-KV = liczba SM / (B·H_kv), z kaflem o rozmiarze potęgi 2 (`:281-289`), plus osobny kernel `splitk_reduce`.
4. **Paged decode (suite FlashInfer)**, `suites/flashinfer/cutile/fmha_decode_bsr.py`. To jedyne miejsce z twardymi danymi per architektura (pomiary NVIDIA):
   - Zamiana operandów QK (TRANS_QK) pomaga na B200. Na konsumenckim sm120 w MLA **spowalnia o 6–80%** (`:38-46`), ale dla GQA wyłączenie jej na sm120 daje ~3× spowolnienie (`:1360-1363`).
   - Gather wielu stron jest szybszy o 10–74% na sm100, a na sm120 wolniejszy o 29–83% (`:66-69`).
   - Redukcja 4 głów na CTA działa ~2.5× wolniej na A100 (`:206-209`).
   - Na mniejszych SM V jest ładowane dopiero **po** QK, żeby kafel V nie żył w rejestrach podczas QK (`:1009-1011`, `:1111-1113`).
   - Bufory scratch dla splitów nie są zerowane: wiersze poza liczbą splitów są maskowane przez select, bo mnożenie przez 0 przenosi NaN (`:150-152`, `:1640-1643`). Pojedynczy split pisze prosto do wyjścia (`:1628-1633`).
   - Split wymiaru `head_dim` V na dodatkowe CTA, gdy siatka jest mała (`:1676-1686`).
5. **Wiki technik** (`wiki/cutile-knowledge-wiki/`). Każdy wpis ma pole `basis: measured, N=…` i opisany zakres, w którym technika nie działa. Wszystkie pomiary NVIDIA pochodzą z B200.
   - **Wave exact cover**: grid o jedną CTA za granicą fali płaci całą falę. Efekt jest realny dla pętli po wierszach i split-K, ale **nie występuje** w siatkach MMA, które same się pipelinują (`techniques/tech-wave-exact-cover.md:17-21, 55-59, 69-76`).
   - **Usuwanie maksimum softmaxu przy udowodnionym zakresie** (`tech-softmax-max-elision.md:23-30, 43-46`). Wejścia z ciężkimi ogonami wymagają pełnego online max (`:62-64`).
   - **Odwrócenie scatter na gather** w MoE combine: 1.9×+ względem atomowego scattera (`tech-scatter-to-gather-inversion.md`, Evidence).
   - `num_ctas=2` na cienkim kaflu decode: 1.76× wolniej (`index.md:55`).
   - Persistent GEMM z jednym akumulatorem: 0.87× wersji płaskiej (`tech-persistent-grid.md`, Evidence).
6. **Integracje Qwen3.5 i LFM2** (`src/tilegym/transformers/qwen3_5/`, `lfm2_moe/`). To wyłącznie proste fuzje elementwise:
   - sigmoid/softplus bramek GDN (`kernels/gdr_preprocess.py:31-34`);
   - conv1d update + SiLU tylko dla B=1, T=1 (`causal_conv1d_update_silu.py:36-44, 56-57`);
   - residual + RMSNorm, gated RMSNorm, sigmoid·mul.

   MoE w LFM to batchowy `fused_moe` w stylu vLLM (`modeling_lfm2_moe.py:13-18`, `ops/cutile/moe.py:20-50`). Nie ma ścieżki decode dla batch 1.
7. **Proces**: `kernel_inventory` w formacie FlashInfer-Bench, czyli definicja, workload JSONL z prawdziwymi kształtami i tolerancją oraz rozwiązanie (`src/tilegym/kernel_inventory/__init__.py:5-17`). Skille dla agentów mają własną ewaluację na 5 zadaniach, z których tylko 1 jest pozytywne (`skills/tilegym-improve-cutile-kernel-perf/BENCHMARK.md:12-14, 45`).

## 3. Przeniesienie na AMD/HIP/RDNA3
| # | Technika | Da się? | Jak / dlaczego nie |
|---|---|---|---|
| 1 | Równoległe redukcje GDN | **Tak** | Nasz kernel ma po dwie szeregowe redukcje DPP na token: `kv` (`gated_delta_net.cu:205-210`), potem aktualizacja stanu i `attn` (`:217-224`). Na RDNA3 obie redukcje przeplatamy w jednym motylku DPP (2 wartości, te same 3 kroki przy 8 lane'ach na kolumnę). Wariant bitowy: zob. P1. |
| 1b | Strumieniowanie stanu kaflami (T=1) | Nieistotne | My trzymamy 16 floatów stanu na lane (`gated_delta_net.cu:85-92`) przy 384 blokach. Problemem jest łańcuch zależności, a nie VGPR. |
| 2 | Chunked GDN | Technicznie tak (WMMA f16 16×16) | Wynik negatywny na gfx1100: Strata #888, a GDN to ~15 ms z 554 ms ubatcha (`repos/14-auto-gpu-kernel.md:71`, `10-tilelang.md:58`). Z TileGym bierzemy tylko **reguły numeryki** na wypadek przyszłej próby: dokładny solve przy L2-norm i bramkę ‖A‖∞ < 1. |
| 3 | Swap operandów, odroczona suma, split-KV | Już mamy | `fattn-kvq.cu`: KV jako M WMMA, suma per lane (`:383-389`) łączona na końcu (`:434`), a leniwy rescale z progiem (`:377-396`) jest lepszy niż pełny online max z cuTile. |
| 4 | V ładowane po QK na „małych SM” | Do sprawdzenia | Zasada przenośna (VGPR→obłożenie). Nasz kvq prefetchuje następny kafel w rejestrach, a „prefetch w FA” był już negatywny (NOTES:324), więc nie proponuję nic nowego. |
| 4b | Lekcja per architektura (sm100 vs sm120) | Tak, jako zasada | Te same optymalizacje dają ±80% zależnie od szerokości MMA. Nasze tabele per (typ, n) w `mmvq.cu` robią to samo. Potwierdza regułę „decyzje z rocprofv3 w modelu”. |
| 5a | Wave exact cover | **Tak, diagnostycznie** | RDNA3: fala = 192 SIMD × waves/SIMD bloków jednowave'owych. Zob. P2. |
| 5b | Usuwanie max softmaxu | Raczej nie | Dowód zakresu dla Qwen/LFM (qk-norm + RoPE/FWHT zachowują normę): \|s\| ≤ scale·d·max\|w_q\|·max\|w_k\| [WNIOSEK]. Przy d=256 i wagach normy rzędu kilku przekracza to zakres exp2 dla f16 P. Nasz próg leniwego rescale i tak usuwa prawie wszystkie rescale; zostaje tylko max per kafel. |
| 5c | Scatter na gather w MoE | Już mamy | `mul_mat_vec_q_moe_down_reduce`: blok liczy wiersze wszystkich użytych ekspertów i redukuje w rejestrach (`mmvq.cu:3223-3230`). |
| 6 | Fuzje Qwen3.5/LFM2 | Już mamy, i to więcej | A4/A5/A6, NORM_GATE, GDN_CONV_AB, INPROJ_CONV, NORM_ROUTER. TileGym jest tu daleko za nami. |
| 7 | cuTile, TMA, `num_ctas`, TMEM | Nie | Brak kompilatora Tile IR na AMD, a do TMA/CGA nie ma odpowiednika na RDNA3 (zob. raport 13). |

## 4. Pomysły dla nas

### P1. GDN: jedna przeplatana redukcja na token zamiast dwóch szeregowych (Qwen, decode/weryfikacja i prefill)
- **Co zmienić** (`gated_delta_net.cu`, pętla `:161-258` i replay `:125-151`):
  - Wariant bitowy (forma TensorFold #10b, ułożona tak, żeby nie zmieniać bitów): po aktualizacji stanu dla tokenu t liczyć w jednym przebiegu po `s_shard` dwie sumy częściowe: `attn_t = Σ S'·q_t` i `kv_{t+1} = Σ S'·k_{t+1}`. Obie redukować jednym przeplatanym motylkiem DPP. `delta_{t+1}` liczy się wtedy bez osobnej redukcji na początku tokenu t+1.
  - Normy L2 `q_{t+1}`, `k_{t+1}` i ładowania ich wierszy nie zależą od stanu, więc liczymy je w cieniu tokenu t. Kolejność sum per wartość zostaje ta sama, więc wynik jest bitowo identyczny.
  - Tam, gdzie nie ma następnego tokenu (pierwszy token wywołania), kv liczymy jak dziś.
  - Alternatywa z TileGym (`out = γSᵀq + δ(k·q)`) skraca łańcuch także dla pierwszego tokenu, ale **zmienia bity**. Lepiej zostać przy wariancie bitowym.
- **Dlaczego to nie powtórka wyniku negatywnego „prefetch w GDN”** (NOTES:324): skracamy łańcuch zależności redukcji (3 kroki DPP plus czekania na token), a nie ukrywamy latencji pamięci.
- **Zysk [SZACUNEK]**:
  - GDN to 638 µs na weryfikację (NOTES:292), ok. 8–9 szeregowych kroków tokenów na wywołanie (T=5 plus replay). Bajty stanu (2×3 MB × 48 warstw ≈ 0.3 ms przy ~900 GB/s) to dolna granica, a resztę zajmuje łańcuch. Usunięcie jednej z 2–3 szeregowych redukcji na token daje 15–30% kernela, czyli **0.1–0.2 ms/krok (0.3–0.7%)**.
  - Prefill: GDN ~15 ms z 554 ms ubatcha, więc 0.4–0.8%.
- **Koszt**: 1 dzień. **Ryzyko**: niskie, a ze względu na FMA-contraction trzeba pilnować jawnych łańcuchów `fmaf` (NOTES:261). **Pomiar**: rocprofv3 `gated_delta_net_cuda` w weryfikacji, `lh.sh` (hash logitów), greedy md5, `test-backend-ops -o GATED_DELTA_NET`.

### P2. Audyt fal MMVQ („wave exact cover” na 192 SIMD), bez GPU na start
- **Co**:
  - Z `--save-temps` (ISA, VGPR/LDS na wariant) wyliczyć dla każdej klasy launchu w obu modelach rezydencję R = 192 × min(waves_per_eu, limit z VGPR) / nwarps bloków.
  - Dla każdej klasy policzyć nblocks/R. Przykład: Qwen n=5 Q4_K/Q5_K ma cap 10 fal (`mmvq.cu:1419-1421`) i nwarps 1, RPB 4 (`mmvq.cu:10-23`). Wtedy 17408 wierszy daje 4352 bloki ≈ 2.27 R, a 5120 wierszy daje 1280 bloków ≈ 0.67 R (6–7 bloków na SIMD, nierówno).
  - Klasy z ułamkiem 0.1–0.4 ostatniej fali wziąć do A/B. Możliwe ruchy: RPB, który ląduje na wielokrotności R, waves_per_eu dobrany tak, by R dzieliło nblocks, albo wariant grid-stride z 192·k blokami.
  - Wariant grid-stride przy okazji umożliwia prefetch następnego slabu wag w tym samym bloku, czyli TensorFold #11c. Tamten raport ma priorytet; TileGym dodaje tylko arytmetykę, kiedy w ogóle warto.
- **Zysk [SZACUNEK]**: 0–3% czasu MMVQ w dotkniętych klasach. Wiki samo zastrzega, że dla ciał, które same się pipelinują (MMVQ jest memory-bound), efekt może zniknąć (`tech-wave-exact-cover.md:55-59`). Dlatego najpierw jeden A/B „o falę obok”, potem reszta.
- **Koszt**: pół dnia analizy plus 1 dzień A/B. **Ryzyko**: brak, bitowo identyczne (ta sama kolejność sum per wiersz). **Pomiar**: `verify_mmvq.py` / rocprofv3 w modelu (NOTES:247-248: mikrobench myli się).

### P3. (zasady, nie kod) Numeryka chunked GDN na wypadek kolejnej próby prefillu
Jeśli K5 wróci do chunked GDN (Strata #2299 dała +1.4–2.1% na gfx1151, #888 −39% na gfx1100):
- przy kluczach z normą L2 trzeba robić dokładny szeregowy solve lub blokowy solve WMMA ze sprawdzeniem ‖A‖∞ < 1 (`chunk_gated_delta_rule.py:44-68, 154-159`);
- pośrednie W/U w f16/bf16 połowią ruch (`:384-397`);
- bramka jakości to KLD na długim dokumencie, a nie tolerancja per kernel.

Zysk wprost 0. Chroni przed „szybkim, ale złym” prefillem, który zmienia dekodowanie.

### Czego świadomie nie proponuję
- Fuzje Qwen3.5/LFM2 z TileGym: wszystkie są podzbiorem naszych.
- `fused_moe`/`moe_align` dla LFM decode: to architektura batchowa. Przy 1 tokenie nasze MMVQ-ids i fuzja down+reduce+residual są lepsze. TileGym **nie ma niczego** na nasz główny problem LFM (koszt uruchomień, 416 kerneli/token).
- Przepisywanie aktywacji na exp2 bez dzielenia (`tech-exp2-activation-forms.md`): nasze ogony są ograniczone latencją pamięci i synchronizacji, a nie VALU. Do tego zmienia to bity.
- Split `head_dim` V w FA decode: przy długim kontekście split-KV daje więcej, a przy krótkim kernel FA LFM trwa ~5–8 µs i dominuje granica uruchomienia.

## 5. Krytyka
- **Brak liczb.** Status „✅ Available = performance optimized” (`ROADMAP.md:122`) nie ma pokrycia w opublikowanych pomiarach. Twierdzenia „2–10×”, „78× wolniej” i „+50–300%” w `skills/**` porównują z naiwną wersją (`optimizing-reference.md:307-309`, `cutile-api-reference.md:150-162`). To dokumentacja dla agentów, a nie benchmark względem FlashInfer/cuBLAS.
- **Ewaluacja skilli to marketing**: 5 zadań, 1 próba, 1 zadanie pozytywne, próg 50% (`BENCHMARK.md:12-14, 45`).
- **„Wsparcie” Qwen3.5 i LFM2** oznacza monkey-patch HF z kilkoma kernelami elementwise, testowany na B200. Nie ma pomiaru end-to-end, grafów ani spekulacji. Dla nas to nieistotne.
- **GDN decode** jest poprawny, ale naiwny względem naszego: brak lagged state/replay, brak MTP. Jedyny ciekawy element to forma algebraiczna (P1), która zmienia bity.
- **Wiki jest uczciwsza od reszty repo**: podaje zakres, w którym technika nie działa, i liczbę kerneli (N). Dane są jednak tylko z B200 i cuda-tile 1.2.
- **Dane sm100/sm120** w `fmha_decode_bsr.py` to najcenniejszy fragment metodologicznie: dowodzi, że optymalizacje decode nie przenoszą się nawet między dwiema generacjami NVIDIA. Na RDNA3 trzeba mierzyć, a nie kopiować.

## 6. Werdykt
**Niska.** To biblioteka dydaktyczna pod Blackwell i HF, bez liczb, a jej kernele decode, MoE i fuzje są w tyle za naszymi. Wartość ma jedno małe, tanie, bitowe skrócenie łańcucha redukcji w GDN (P1), arytmetyka fal dla audytu MMVQ (P2) i reguły numeryki chunked GDN (P3).
