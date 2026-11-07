# 66b: 1Cat-vLLM v1.5.2 (4× V100) i TokenSpeed (LightSeek): długi kontekst, cache hybrydowy, offload KV

Data: 2026-11-07. Praca tylko na CPU: bez GPU, bez pobierania wag, serwer :8080 nietknięty. Klony kodu: `~/src/research66/1Cat-vLLM` (`c98a8d6`) i `~/src/research66/tokenspeed` (`b941508`). Ścieżki `plik:linia` odnoszą się do korzenia danego klonu (1Cat albo TS). `[SZACUNEK]` oznacza naszą arytmetykę, `[INFERENCE]` wniosek bez pomiaru. Punktem wyjścia była [63-SYNTEZA](63-SYNTEZA.md). Przy każdej pozycji oznaczam, czy jest **NOWA**, czy **ZNANA**.

## 1. TL;DR

1. **„250K tylko 18% wolniej niż 1K” to własność modelu Flash-Next, a nie kernela atencji.** Flash-Next ma 36 warstw GDN i 12 warstw QSA z **natywną rzadką atencją**: indeksator wybiera 512 bloków po 4 tokeny, czyli budżet 2048 tokenów na krok. Do tego historia KV leży w RAM hosta jako FP8, a to jest stratne. Gęsty 27B w tej samej wersji traci **−47%** (501 → 268 t/s), czyli tyle co my (**−45%**, 136.5 → 74.5 t/s przy 199k). **NOWE.**
2. **Efektywne pasmo przyrostu KV jest u nich i u nas takie samo: ~200 GB/s** `[SZACUNEK]`. To ~20–22% szczytu V100/XTX, więc żaden z nas nie stoi na pasmie. Ich droga w dół (Pack-GQA48: 6 głów × 8 tokenów weryfikacji w jednym kaflu, KV czytane raz; podział = liczba SM; 2 CTA/SM) jest bezstratna i pasuje 1:1 do naszego planu #8 (`fattn-kvq`). Zmierzyli: operator **−20…21%** przy 32K–256K, cała runda **−8.6%** przy 128K. **NOWE dowody do znanego planu.**
3. **Liczby 487 / 1224 / 268 t/s z release'u to czas rundy × założone 5.9 tokenu na rundę**, czyli akceptacja 70% przy 7 draftach DFlash2. Zmierzone wyniki zależą od tekstu: HumanEval 84% → 619 t/s, MT-Bench 43% → 386, pisanie po chińsku 22% → 215. NVFP4 i KV FP8 E4M3 są stratne (sekcja 6).
4. **Cache prefiksu dla modeli hybrydowych:** bezstratne pomysły, których nie mamy, to okresowa siatka checkpointów stanu GDN (co 8192 tokeny), „junction learning” (checkpoint w punkcie rozgałęzienia zapisany dla następnych żądań) i dysk jako trzecia warstwa cache przeżywająca restart. **CPU KV offload** dla gęstej atencji jest dla nas bez sensu, bo 3.6 GB na krok przez PCIe to ~150 ms `[SZACUNEK]`; u nich działa tylko dlatego, że QSA jest rzadka.
5. **TokenSpeed nie obsługuje naszej karty** (gfx950/gfx1250/sm90+; gfx1201 tylko przez przenośny Triton; gfx11 brak). ReplaySSM już mamy (`rs_lag` w topce). Nowe są dwie rzeczy: monokernel per warstwa (580 vs 377 t/s na MI350X, ale wpis CI podaje 443) i lekcja „obcinanie po stop-tokenie na GPU przy overlapie”, ważna dla planu #11.

## 2. Co to jest

### 2.1 1Cat-vLLM / 1Cat-LLM v1.5.2

- **Wersja:** release v1.5.2 z 2026-11-06. Wheel zbudowany z main `9f970d628`, tag na `2bb8c2b9`; 128 PR, 1805 commitów ([release](https://github.com/1CatAI/1Cat-vLLM/releases/tag/v1.5.2)). Repo to fork vLLM, w którym V100/SM70 jest głównym celem („Make Volta Fast Again”, `README.md:9-60`). Jest w trakcie zmiany nazwy na 1Cat-LLM i dostał obsługę GGUF.
- **Sprzęt pomiarów:** 4× V100-SXM2-32GB z NVLink, TP4. Pamięć 1107 MHz, rdzeń ≤1530 MHz, limit 350 W, ECC włączone, host 62 GB RAM.
- **Modele:**
  - **27B:** Unsloth Qwen3.8-27B-NVFP4 + `incoai/Qwen3.8-27B-DFlash2` (7 draftów, próbkowanie probabilistyczne), docelowe KV `fp8_e4m3`, KV draftu FP16 (`docker/sm70_release/serve.sh:33-40`).
  - **Flash-Next:** Qwen3.8-Flash-Next-NVFP4 + MTP4 (draft greedy), `kv-cache-dtype float16`, ale `qsa_host_kv` z historią **FP8 E4M3 w RAM hosta** i 32 768 „gorącymi” tokenami na GPU (`serve.sh:42-51`).

**Liczby z release'u v1.5.2 (warunki: jedno żądanie, T=0, czysty decode bez prefillu, przeliczone na akceptację 70%):**

| | 1K | 8K | 32K | 64K | 128K | 250K | 250K vs 1K |
|---|---|---|---|---|---|---|---|
| 27B t/s | 501 | 487 | 452 | 409 | 346 | 268 | −47% |
| ms/runda przy 5.9 tok/rundę `[SZACUNEK]` | 11.8 | 12.1 | 13.1 | 14.4 | 17.1 | 22.0 | +10.2 ms |
| Flash-Next t/s | 260 | 253 | 250 | 234 | 221 | 213 | −18% |
| ms/runda przy 3.8 tok/rundę `[SZACUNEK]` | 14.6 | 15.0 | 15.2 | 16.2 | 17.2 | 17.8 | +3.2 ms |

- **Zastrzeżenie producenta:** wiersze „1 / 8 współbieżnych” są „按接受率 70% 折算” (przeliczone na akceptację 70%). 27B daje 5.9 tokenu na rundę, Flash-Next 3.8. Zmierzony jest czas rundy, a liczba tokenów na rundę jest założona.
- **Sześć zbiorów danych, T=0, naturalny koniec:**

| Zbiór | Akceptacja 27B | t/s 27B | Akceptacja Flash-Next | t/s Flash-Next |
|---|---|---|---|---|
| HumanEval | 84% | 619 | 91% | 311 |
| MBPP | 81% | 552 | — | — |
| MATH500 | 76% | 543 | — | — |
| GSM8K | 77% | 529 | — | — |
| MT-Bench | 43% | 386 | 60% | 258 |
| chiński tekst | 22% | 215 | 46% | 195 |

- **Prefill i cache (27B):**
  - pierwsze wypełnienie 250K: 101.6 s (~2.5k t/s);
  - 8K: 1.72 s (~4.6k t/s), czyli ~1.2k t/s na jedną V100, mniej więcej tyle co nasze ~860–1000 t/s na XTX;
  - pełne trafienie przy 250K: 1.59 s; tura z dopisaną wiadomością: 1.70 s.
- **Znane ograniczenia** z release'u:
  1. zmiana ostatnich 10% promptu 32–64K oznacza pełne przeliczenie;
  2. przy jednym żądaniu próbkowanie Flash-Next kosztuje +3.3 ms na rundę;
  3. maksimum 8 żądań przy 256K.

### 2.2 TokenSpeed (LightSeek Foundation)

- **Repo i licencja:** [lightseekorg/tokenspeed](https://github.com/lightseekorg/tokenspeed), MIT, założone 2026-05-06, HEAD `b941508` z 2026-11-07.
- **Architektura:** silnik pod obciążenie agentowe.
  - Pętla zdarzeń w Rust (`ts-host`) hostuje harmonogram C++ jako maszynę stanów. Bezpieczeństwo KV jest wymuszane typami w czasie kompilacji.
  - Jeden wątek Pythona wydaje całą pracę GPU (TS `docs/design/event-loop.md:3-18,107-131`).
  - Frontend SMG/Dynamo przez msgpack, bez Pythona na ścieżce żądania (TS `README.md:9-16`).
- **Sprzęt:** NVIDIA sm90/sm100/sm103/sm107. AMD gfx950 i gfx1250 (Gluon). gfx1201 (RDNA4, R9700) tylko z przenośnymi kernelami Triton, BF16, `--enforce-eager` (TS `AGENTS.md:143-149`, `docs/guides/getting-started.md:155-176`). **Brak gfx11xx, Apple i Intela.** NPU: tylko Ascend (TS `tokenspeed-kernel-npu/README.md:1-17`).
- **Qwen3.8-27B:** jest przepis na jedną kartę (FP8, KV `fp8_e4m3`, MTP 3 kroki, `--attention-backend trtllm`, czyli tylko NVIDIA) (TS `docs/recipes/models.md:1066-1084`).
- **Liczby producenta:**

| Twierdzenie | Producent | Wpis CI w repo | Warunki z CI |
|---|---|---|---|
| Flash-Next na GB300 | „685 t/s na użytkownika” | 691.82 t/s/użytk. przy C=1 (TS `test/ci/perf/qwen3.8-flash-next-nvfp4-tp4ep4-evalscope-agentic.yaml:35-46`) | 4× GB300, NVFP4, MTP3, KV BF16; SWE-Smith, 500 tokenów z `ignore_eos`; metryka 1000/TPOT |
| Qwen3.5-397B | „580 TPS” | 530 przy C=1 na 4× GB200 | KV fp8 |
| monokernel na MI350X | „580 vs 377 t/s” (komentarz) | 443 t/s (mediana z 3 przebiegów na runnerze) | TS `test/ci/perf/qwen3.8-flash-next-mxfp4-monokernel-gsm8k-single-request-mi35x.yaml:14-17,70-79` |

Twierdzenie o monokernelu nie zgadza się z własnym wpisem CI.

## 3. Technika w szczegółach

### 3.1 Skąd „−18%” Flash-Next: architektura modelu + stratny host KV (NOWE)

- **Model** (1Cat `docs/design/sm70_qwen38_flash_next_nvfp4.md:91-94`): 48 warstw, 36 GDN + 12 QSA w układzie 3:1. QSA ma 24 głowy Q, 2 KV, D=256, indeksator o wymiarze 128, kompresję ×4 i **rzadki budżet 2048 tokenów**.
- **QSA jest natywne w checkpoincie.** Konfiguracja HF zawiera pola `indexer_*`, a warstwy mają typ `qwen_sparse_attention` (1Cat `vllm/models/qwen4_exp/config.py:14-20,67-76,144-167`). `block_topk ∈ {512, 2048}` (`:162-167`). Dla Flash-Next rzadkość jest więc definicją modelu, a nie aproksymacją silnika.
- **Selekcja:** indeksator liczy wyniki na skompresowanych kluczach (n/4) w FP32 przez cuBLAS, potem dokładny top-k 512 bloków, rozwinięcie do 2048 tokenów i ogon przyczynowy (1Cat `vllm/models/qwen4_exp/nvidia/ops/qsa.py:1316-1319,1385-1456`). Kroki draftu MTP 1+ używają indeksów z kroku 0 (`sm70_qwen38_flash_next_nvfp4.md:484-488`). To dotyczy tylko draftu, więc wyjście się nie zmienia.
- **Koszt z kontekstem rośnie tylko w indeksatorze:** O(n/4) przy 1 głowie KV i wymiarze 128. Atencja ma stały koszt 2048 tokenów. Stąd +3.2 ms na rundę między 1K a 250K `[SZACUNEK]`.
- **Host KV** (1Cat `docs/design/flashnext_host_fp8_kv.md`, `vllm/config/kernel.py:934-990`):
  - Autorytatywna historia leży w pamięci hosta przypiętej (pinned) jako E4M3 ze skalą FP32 na token × głowę × K/V.
  - Na GPU zostaje cache stron „hot”, mapowany strona → slot z wymianą zegarową (clock sweep). To nie jest okno ostatnich tokenów.
  - Chybienia kernel czyta przez UVA prosto z hosta do ~64 MiB wspólnego bufora roboczego FP16.
  - Koszt umieszczenia na hoście: +0.47 ms (C1) i +2.15 ms (C4, +5.1%) na rundę.
  - Jakość: E4M3 vs FP16 daje KL 0.0017–0.0021, top-1 62–63/64 i akceptację draftu −2.3 pp (CI [−3.04, −1.54]). Sam autor odrzucił to jako domyślne („rejects default promotion”, `flashnext_host_fp8_kv.md`, sekcja „Same-format placement diagnostic”), a mimo to release 1.5.2 włącza `qsa_host_kv` z FP8 (`serve.sh:50`). **Stratne.**
- **Wniosek:** tej techniki nie da się przenieść na Qwen3.8-27B, który ma gęstą atencję, bez doklejenia wyuczonego indeksatora. To jest zaparkowane QSA (#28 w 63-SYNTEZA, sekcja 4).

### 3.2 Gęsty 27B: kernele decode i weryfikacji (bezstratne poza FP8)

Wszystkie kernele są w 1Cat `flash-attention-v100/kernel/flash_decode_paged.cu`.

- **Decode q=1 (XQA split-KV):**
  - Kernel `flash_attention_decode_xqa_tc_partition_kernel_256_wide`, `:1257-1330`. Jedna CTA na (batch, głowa KV, partycja).
  - 6 głów Q tej samej głowy KV to wiersze kafla WMMA, więc KV czytane jest raz na partycję.
  - Wynik partycji: max, suma exp i nienormalizowane O w FP32. Combine `:2787-2880` (wagi `exp_sum·exp(m_i−M)`, FMA w rosnącej kolejności).
  - Rozmiar partycji zależy od długości: E4M3 p64 <12 288 ≤ p256 <49 152 ≤ p512 <98 304 ≤ p896 <196 608 ≤ p1664 (1Cat `include/flash_v100_policy.h:249-276`). W jednym CUDA graph siedzi kilka węzłów, a każdy wychodzi wcześnie, jeśli `seq_lens` z urządzenia jest poza jego zakresem (`:535-556`). Cel: nie zostawiać niepełnej ostatniej fali.
- **„P1024 dual-CTA” (#206):** `__launch_bounds__(192,2)`, rejestry 188 → 168, DRAM 260 → 371 GB/s. Przy 128K 40.82 → 48.54 t/s, wyjście bitowo równe (1Cat `docs/design/sm70_tp4_nomtp_long_context_decode.md:998-1117`).
  - Ten sam dokument mierzy dla decode p256 tylko **23% pasma DRAM** przy 12.5% occupancy. Kernel jest ograniczony latencją, nie HBM.
- **Weryfikator grupowy q8 (Pack-GQA48), czyli najważniejsza część dla nas:**
  - Stałe `:1819-1880`: 48 wierszy na CTA = 8 tokenów weryfikacji × 6 głów. q16 = 16 × 3 głowy w 2 CTA.
  - Kafel KV ma 32 tokeny, CTA 512 wątków, **80 podziałów = liczba SM V100**.
  - Liczba podziałów: `min(80, ceil(L/64))`, a 1 podział przy L ≤ 128 (`:1906-1918`). Kafle są rozłożone równo, z resztą rozdzieloną po podziałach.
  - Przyczynowość per wiersz w kernelu (`prefix_kv_len = L − q`, `:2125`). Combine LSE w FP32 (`:2676-2784`).
  - Wariant E4M3 dla release'u: `:4446-4562`.
  - Historia optymalizacji (1Cat `docs/design/sm70_dflash2_long_verify_decay.md`):
    1. **Atrybucja z trace'u:** atencja grupowa wyjaśnia 99.2% wzrostu fazy celu między 32K a 128K. Draft, selektor, próbkowanie i TP nie mają znaczenia.
    2. **Podziały 40 → 80** (1 → 2 CTA na SM): operator −18…−22% przy ≥32K i +16% przy 1K. Cała runda przy 128K **40.78 → 36.68 ms (−10.0%)**.
    3. **Kafle balansowane do pełnych 32-tokenowych kafli WMMA i specjalizacja strony w czasie kompilacji:** dalsze −1.7% operatora przy 128K.
    4. **Pack-GQA48:** jedna 48-wierszowa CTA zamiast dwóch (grupa 4 głów + ogon 2 głów), z których każda czytała i dekodowała tę samą stronę KV. Operator −19.6 / −19.9 / −20.6 / −21.2% przy 1K/32K/128K/256K. Runda −1.5% przy 1K, **−3.4% przy 32K, −8.6% przy 128K**. Nachylenie 32K → 128K spadło 11.24 → 8.94 ms. PPL bitowo równe poprzedniemu wariantowi.
    5. **Proxy roofline:** 8.7–9.3 „logicznych” TFLOP/s i 136–145 GB/s, płasko w funkcji kontekstu. Autorzy piszą wprost, że to nie jest nasycone HBM.
  - **Porażki** (do `wyniki-negatywne`):
    - split-K po wymiarze D w QK: ±0.4%, brak zysku;
    - adres liczony przez pół warpa i rozgłaszany przez shuffle: −2.4…−3.5%;
    - zwarte mapowanie ogona 2 głów: −6.3…−7.0%;
    - FP8 dekodowane inline w pętli atencji przy host KV: 196 vs 107 µs;
    - PV rozbite na 3 iloczyny tensor-core: wolniejsze.
- **DFlash2: atencja draftu z przesuwnym oknem (#328).** Pętla startuje od pierwszego kafla osiągalnego przez okno (1Cat `flash-attention-v100/kernel/fused_mha_forward_paged.cu:447-450,736-741`). Przy 256K 0.423 → 0.247 ms na warstwę, krzywa płaska od 32K. Bezstratne, ale u nas nie ma zastosowania: głowica MTP ma pełną atencję, a okno MTP W=8192 już testowaliśmy z wynikiem negatywnym (105 → 90 t/s, [07 łatka 0046](07-nasze-metody-uogolnienie.md), [15b](15b-spekulacja-frontier.md)).

### 3.3 Normalizacja: ich 27B vs nasz 27B (NOWE)

| | 1Cat 27B (4× V100, TP4) | topka (1× XTX) |
|---|---|---|
| KV na token na GPU | 16 warstw × 1 głowa KV × 256 × 2 × 1 B (E4M3) = **8 KiB** | 16 × 4 głowy × 256 × 2 × 0.5625 B (q4_0) = **18 KiB** |
| Przyrost czasu kroku/rundy | +10.2 ms (1K → 250K, ~249k tokenów) | ~+18 ms (1.7k → 199k, ~197k tokenów; [63d E7](63d-atencja-spec-kwant.md)) |
| Odczyt KV w przyroście | 249k × 8 KiB ≈ 2.0 GB na GPU | 197k × 18 KiB ≈ 3.6 GB |
| Efektywne pasmo przyrostu `[SZACUNEK]` | **~200 GB/s** (~22% z ~900) | **~200 GB/s** (~21% z 960) |
| Spadek t/s | −47% (1K → 250K) | −45% (1.7k → 199k) |

Wniosek: na gęstym modelu 1Cat nie jest lepszy od nas. Ich nachylenie da się zejść jeszcze o ~20% tymi samymi bezstratnymi środkami, które mamy w planie #8. U nas weryfikacja MTP4 to 5 tokenów × 6 głów = 30 kolumn. `fattn-kvq` ma `fattn_kvq_ncols = 16` (topka `ggml/src/ggml-cuda/fattn-kvq.cu:31`), więc `ntiles_x = ceil(30/16) = 2` (`:620-622`): **KV q4_0 jest czytane i dekodowane dwa razy na krok.** O tym, czy drugi odczyt trafia w 96 MB Infinity Cache, decyduje dopiero profil `[INFERENCE]`. Dobór podziałów to 2 bloki na WGP dla q4_0 i 1 dla q8_0 (`:625-635`), strojony na LFM2 (D=64), a nie na Qwen przy D=256 i 199k.

### 3.4 Szybszy prefill długiego kontekstu (1Cat 1.5.x)

- **Natywny prefill Q4096/Q8192 D256:** sześć głów GQA spakowanych w szersze GEMM-y Tensor Core, QK/PV w FP32.
  - Postęp: 17.9 → 47 → 60.8 → 71 TFLOP/s; 79 TFLOP/s przy Q4096 (#1287).
  - E4M3 jest jednorazowo przepisywane do bufora FP16 przez „bridge” (1Cat `csrc/attention/sm70_v37/bridge.cu:16-60`); sama konwersja jest dokładna.
- **Split-KV dla krótkich kawałków po długim prefiksie** (#1298). Prefill i rezydentny decode idą razem w pełnych blokach (#1295).
- **Siatka stanu Mamby rozprzężona z blokiem KV** (#645): prefill 100K +12.9%.
- **Dla nas:** w llama.cpp FA mma już ma `parallel_blocks` i stream-K z fixupem ([63d E7](63d-atencja-spec-kwant.md)). Nowy jest pomiar „tura z dopisaną wiadomością przy 250K = 1.7 s”, który możemy porównać 1:1 (T7).

### 3.5 Cache prefiksu dla hybryd (GDN + atencja) vs nasze cache-ram i checkpointy (część NOWA)

Pliki: 1Cat `vllm/v1/core/*`, release'owe flagi `--partial-prefix-cache --block-size 2048 --mamba-block-size 2048 --mamba-cache-mode align --prefix-cache-retention-interval 8192` (`docker/sm70_release/serve.sh:25-37`).

- **Stan GDN** zapisywany jest tylko na granicach bloku 2048, przy końcu kawałka harmonogramu (`vllm/v1/core/sched/scheduler.py:479-582`). Jedna migawka to jedna strona bloku na grupę Mamby; strona atencji jest dopasowana rozmiarem do strony stanu (`vllm/platforms/interface.py:739-777`).
- **Retencja** (`single_type_kv_cache_manager.py:1550-1630`, `kv_cache_coordinator.py:121-140`):
  - `0` (domyślnie): granice powtórki plus wykryte „junctions”;
  - `N`: dodatkowo checkpoint co N tokenów;
  - `None`: każda granica.
  - Koszt dla Flash-Next TP4: 29.7 MB stanu vs 10.24 MB atencji na blok. Przy gęstej retencji 74% RAM poszłoby na migawki (`docs/design/grouped_cpu_offload.md:10-15`).
- **Junction learning:** gdy prefiks atencji sięga dalej niż jakikolwiek zapisany stan, żądanie zapisuje `shared_prefix_boundary`. Harmonogram tnie tam kawałek, maska zatrzymuje stan i **kolejne** żądanie trafia (`kv_cache_coordinator.py:690-760`, `scheduler.py:565`). Pierwsze rozwidlenie wciąż wymaga przeliczenia (`docs/features/automatic_prefix_caching.md:52-59`). Stąd ich ograniczenie nr 1 („ostatnie 10% promptu”).
- **Partial prefix cache** (`vllm/v1/core/partial_prefix_cache.py:1-164`): migawka w dokładnej pozycji wewnątrz bloku (koniec ostatniej wiadomości i koniec system promptu).
  - Granice wylicza serwer z sond szablonu czatu i zaokrągla w dół do 64 tokenów, czyli do kawałka kernela GDN. Wznowiony prefill tnie się wtedy tak samo jak zimny (`vllm/entrypoints/openai/chat_completion/serving.py:93-200`, `vllm/v1/request.py:59-60,160-173`). Celem jest bitowa zgodność trafienia z zimnym przebiegiem.
  - Z MTP lookup cofa się o jeden blok, czyli traci do 2048 tokenów (`single_type_kv_cache_manager.py:1300-1309`).
- **Wyjście modelu, także rozumowanie, trafia do cache** (#1338). Stan na granicy bloku odtwarzany jest z pośrednich stanów MTP (`vllm/v1/worker/mamba_utils.py:1033-1132`).
- **Porównanie z topką:**
  - Nasze checkpointy powstają przy wiadomościach użytkownika plus `checkpoint_min_step` (topka `tools/server/server-context.cpp:4253-4258,4328-4332`) oraz w ogonie promptu. `--cache-ram 40960` trzyma całe wpisy slotu.
  - Brakuje nam: (a) okresowej siatki dla długich pojedynczych wiadomości (wklejony dokument albo wynik narzędzia), (b) checkpointu w punkcie rozwidlenia dla następnego rodzeństwa, (c) warstwy dyskowej przeżywającej restart.
  - Mamy: kopię całego slotu (prościej), rollback GDN przez powtórkę (`rs_lag`, topka `src/llama-memory-recurrent.h:82-103`) oraz plan „chudych checkpointów” (#6) i „wspólnego początku” (#7).

### 3.6 CPU KV offload

- **1Cat ogólny** (`vllm/v1/kv_offload/cpu/*`, `vllm/distributed/kv_transfer/kv_connector/v1/offloading/scheduler.py:862-940,1038-1180`):
  - natywny `OffloadingConnector` vLLM świadomy grup;
  - zapis write-through w trakcie liczenia (nie przy eksmisji) na osobnych strumieniach do pamięci przypiętej, surowe bajty w dtype KV GPU, z **osobną pulą slotów na stan GDN**;
  - eksmisja LRU/ARC z degradacją starszych checkpointów;
  - opcjonalna warstwa FS przeżywająca restart (`vllm/v1/kv_offload/tiering/fs/manager.py`).
  - **Bezstratny** (kopia bajtów). Funkcjonalnie to nasze `--cache-ram` plus dysk.
- **Flash-Next `qsa_host_kv`** (sekcja 3.1): historia atencji czytana przez PCIe w czasie decode. Ma sens tylko przy rzadkiej atencji z 2048 tokenami na krok.
- **Dla gęstego 27B:** 3.6 GB KV na krok przez PCIe 4.0 x16 (~25 GB/s) daje ~145 ms na krok `[SZACUNEK]`. Odpada dla XTX i dla Enigmy.
- **„Shared host arena” (#1404)** to memfd dla ekspertów GGUF i KV DeepSeek-V4.1, a nie cache prefiksu (1Cat `vllm/utils/shared_host.py:38-75`).

### 3.7 NVFP4 na V100 (stratne, zaparkowane)

- **Metoda:** W4A16. Nibble E2M1 ze skalami E4M3 na 16 wag i globalną skalą FP32 są rozpakowywane do FP16 w rejestrach. GEMM HMMA884 z akumulacją FP32 (TurboMind W4A16 dla M>1, QPN2/QPN8 dla małych M). Część projekcji to kanałowe FP8 W8A16 (1Cat `docs/design/sm70_qwen38_nvfp4_decode.md:5-60`, `docs/design/sm70_dflash2_shared_nvfp4.md:20-40`). Volta nie ma sprzętowego FP4/FP8, więc to czysta dekompresja wag.
- **Jakość według producenta:**

| Test | BF16 | NVFP4 27B |
|---|---|---|
| GSM8K (300 zadań) | 285 | 289 |
| MMLU (400) | 336 | 332 |
| HumanEval (20) | 19 | 20 |

  W 100 wyjściach przy rozbieżności z BF16 mediana przewagi logprob wynosi 0.2. Próbki są małe. Z [63a §13](63a-silniki-lokalne.md): pełne NVFP4 psuje równoległe tool-calle (BFCL 79 → 65.5%).
- **Werdykt:** zmiana kwantu wag, więc sekcja 6.

### 3.8 TokenSpeed: techniki

1. **ReplaySSM.** Weryfikacja czyta zatwierdzony stan GDN i nic nie zapisuje. Zapisuje tylko lekki payload `[k|v|a|b]` na każdy token draftu. Po akceptacji jedno uruchomienie odtwarza zaakceptowany prefiks dla wszystkich warstw, ze stanem w FP32 do końcowego zapisu (TS `tokenspeed-kernel/python/tokenspeed_kernel/ops/attention/gdn/README.md:199-281`, `docs/design/tree-speculation.md:105-121`). **ZNANE:** topka ma to samo jako `GATED_DELTA_NET_LAG`/`rs_lag` (`src/llama-memory-recurrent.h:82-103`, `src/llama-model.cpp:2393-2399,2843-2844`).
2. **Weryfikacja łańcucha w formie chunked** (macierze Grama na tensor-core zamiast sekwencyjnej rekurencji). Zmienia kolejność działań i nie jest bitowa („Outputs round differently”, `gdn/README.md:226-229`). Częściowo pokrywa się z naszym planem #21.
3. **Zbalansowany split-KV liczony raz na krok na GPU** i używany przez każdą warstwę (TS `tokenspeed-kernel-amd/.../gfx950/attention/mha/decode.py:1559-1673`). Wiersze bloku (tokeny weryfikacji × grupa GQA) dzielą jeden przejazd po sumie kluczy (`:273-280`), czyli to samo co Pack-GQA. Ścieżka zbalansowana wygrywa przy wielofalowych work-groupach (weryfikacja), a przy jednofalowym decode traciła do ~20% (`:2350-2363`). Bezstratne (tylko kolejność scalania softmaxu).
4. **Overlap głębokości 1 z drenażem zależności w jednym miejscu** (TS `docs/design/event-loop.md:510-551`). Lekcja z błędu: przy spekulacji i overlapie CPU obcinało wynik na stop-tokenie, a GPU zatwierdzało wszystkie zaakceptowane tokeny. To psuło opublikowany checkpoint GDN. Poprawka: obcinanie długości na GPU (TS `docs/spec-finish-checkpoint.md:5-14`, `docs/design/cache-concepts.md:331-345`). **NOWE dla planu #11.**
5. **Monokernel dekodu:** jedno trwałe uruchomienie na warstwę. Etapy przekazują dane przez otagowane 64-bitowe skrzynki, wagi kolejnych etapów są prefetchowane. Wymaga ≤1 CTA na CU. „Same math, not the same bits” (TS `docs/design/monokernel.md:1-80`). Dziś tylko Qwen4Exp na gfx950. Wcześniejszy megakernel TKCC dał na AMD +0.22% ([63e §3](63e-metodologia-agenci.md)).
6. **Próbkowanie Gumbel-max i weryfikacja na GPU, gramatyka przechwytywalna w grafie** (TS `python/tokenspeed/runtime/grammar/host_grammar.py:73-110`). Bezstratne.
7. **Opcje stratne** (wszystkie opt-in): KV fp8/mxfp8, stan SSM w bf16, BLASST skip-softmax, QSA (sekcja 6).

## 4. Macierz przydatności

| Technika | AMD gfx1100 (topka) | Enigma NVIDIA CUDA | Apple Metal | Intel | Strix Halo |
|---|---|---|---|---|---|
| Pack-GQA: (draft+1) × G wierszy w jednym kaflu, KV raz | **tak**, plan #8 w `fattn-kvq` | tak, upstream `fattn-mma` z `ncols2` dla GQA 6 grupuje tylko po 2 `[INFERENCE]`, a pin Enigmy to upstream | tak (Metal FA w llama.cpp, ta sama logika) `[INFERENCE]` | tak (SYCL/Vulkan) `[INFERENCE]` | tak, i ważniejsze: 256 GB/s LPDDR5X, więc podwójny odczyt KV boli bardziej |
| Podziały = liczba CU × k, ≥64 tokeny na podział, kafle balansowane | tak (strojenie `fattn-kvq.cu:625-635`) | upstream ma już dobór fal i stream-K | — | — | tak (40 CU) |
| Okresowe checkpointy GDN i junction learning | tak (serwer topki) | tak (patch do pinu Enigmy) | tak | tak | tak |
| Dyskowa warstwa cache / save przy wyjściu | średnio (serwer 24/7) | **tak** (aplikacja desktopowa restartuje się) | tak | tak | tak |
| CPU KV offload dla gęstej atencji | nie (PCIe) | nie | n/d (pamięć wspólna) | nie | n/d (pamięć wspólna) |
| ReplaySSM | mamy | upstream ma rollback przez snapshoty | — | — | — |
| Monokernel per warstwa | badawczo; najpierw zmierzyć przerwy w profilu (#3) | badawczo | — | — | — |
| Silnik TokenSpeed jako całość | nie (brak gfx11) | tylko sm90+ (H100/B200); konsumenckie karty NVIDIA nieobsługiwane | nie | nie | nie (gfx1151 brak) |
| 1Cat jako silnik | nie (tylko SM70/72/75) | nisza: V100/T4 przez GGUF w 1Cat-LLM | nie | nie | nie |

## 5. Pomysły do przetestowania (tylko bezstratne)

Baseline: long_ctx 94k 105.6, 199k 74.5 t/s (T=0, MTP4 + W16); spec_sweep T=1 114.8 t/s; prefill 860–1000 t/s; TTFT 94k 123 s.

| # | Pomysł | Bezstratny? | Oczekiwany zysk i dlaczego | Wysiłek | Jak testować na XTX | Ryzyko |
|---|---|---|---|---|---|---|
| T1 | **Pack-GQA w `fattn-kvq`**: kafel 32 kolumn (5 tokenów × 6 głów = 30) zamiast 2 × 16, KV q4_0 dekodowane raz na krok; LSE combine w FP32 bez zmian (= plan #8, nowe dowody) | tak (kolejność sum, bramka md5/KLD) | FA przy ≥32k −15…20% (1Cat: operator −20…21%, runda −3.4% przy 32K i −8.6% przy 128K); u nas 94k 105.6 → 109–113, 199k 74.5 → 78–83 (+5…11%) `[SZACUNEK]`, pod warunkiem że FA to ≥ połowa nachylenia 18 ms | 3–5 d | `test-backend-ops perf -o FLASH_ATTN_EXT` (hs 256, nh 24/4, nb 5, KV q4_0 98 304 i 196 608) A/B, potem `long_ctx_bench` 94k/199k ABBA i bramka md5 c4708318/6f14e814/894e56e4, a przy różnicy KLD | LDS na 32 kolumny × (256+8) × 2 B Q + bufory VT, spadek occupancy; trzeba podwoić `nsplit`, żeby utrzymać 2 bloki/WGP; zysk znika, jeśli drugi odczyt i tak trafia w Infinity Cache |
| T2 | **Przegląd podziałów `fattn-kvq` dla q4_0 D=256**: `blocks_per_sm` {1,2,3,4} × minimum tokenów na podział {64,128,256}, przełącznik env | tak (inne granice podziału, bramka KLD) | 1Cat: 1 → 2 CTA/SM dało −21% operatora przy ≥32K; nasz dobór był strojony na LFM2 D=64 (`fattn-kvq.cu:625-628`); FA przy 199k 0…−10% `[SZACUNEK]` | 0.5 d | ta sama komenda perf przy n_kv 32k/98k/196k, potem `long_ctx_bench` 199k dla zwycięzcy | szum < próg; zmiana md5 |
| T3 | **Profil kroku przy 199k metodą 1Cat** (plan #3): suma partial i combine ÷ liczba kroków, rozbicie FA celu, FA draftu, maski i combine, do tego „logiczne” GB/s i TFLOP/s | n/d (pomiar) | bramka dla T1/T2: 1Cat przypisał 99% nachylenia jednemu kernelowi; jeśli u nas FA < 50% z 18 ms, T1 schodzi z priorytetu | 30 min GPU + 0.5 d | rocprofv3 (PM4 wyłączony), 1.7k vs 199k | żadne |
| T4 | **Okresowa siatka checkpointów GDN** (np. co 8192 tokeny w długich wiadomościach) **+ checkpoint w punkcie rozwidlenia** (junction) przy następnym prefillu | tak (kopie stanu) | edycja ostatnich 10% promptu 60k: przeliczenie ~60k → ≤8k tokenów, TTFT ~65 s → ~8–10 s `[SZACUNEK przy ~900 t/s]`; koszt ~150 MiB RAM na checkpoint `[INFERENCE: 48 warstw GDN × 48 głów × 128² × fp32]`, rzeczywistą liczbę odczytać z logu „created context checkpoint” | 1–1.5 d | skrypt replay: prompt 60k (jedna wiadomość) → ten sam ze zmienionym końcem → trzecie żądanie rodzeństwo; mierzyć `prompt_n`, TTFT i md5 odpowiedzi vs zimny start | RAM w `--cache-ram 40960`; liczbę checkpointów ogranicza `n_ctx_checkpoints`; kolizja z planem #6 (chude checkpointy), więc projektować razem |
| T5 | **Cache przeżywający restart w Enigmie**: zapis slotu (`/slots?action=save`) przy bezczynności lub zamknięciu i odczyt przy starcie, z checksumą (CRC32C jak RTP z 63b) i stanem draftu MTP (#30574) | tak (bajty) | pierwsza tura po restarcie aplikacji przy rozmowie 50k: ~55 s → ~2–4 s (NVMe ~2–3 GB/s, wpis kilka GB) `[SZACUNEK]` | 1–2 d (TS + flagi serwera) | e2e Enigmy: rozmowa 50k, restart, następna tura; TTFT i md5 vs ciągła sesja; osobno akceptacja MTP po odczycie | bez stanu draftu akceptacja spada 49 → 37% (#30574); miejsce na dysku; wersjonowanie przy zmianie buildu |
| T6 | **Pomiar „tura dopisana przy długiej historii”** (1Cat: 1.70 s przy 250K na 4× V100) | n/d (pomiar) | jeśli u nas > 3 s przy 94k/199k: profil ścieżki „krótki kawałek po długim prefiksie” (1Cat #1298 split-KV) i konwersji KV q4_0 → f16 w prefillu | 15 min GPU | fill test: 94k i 199k w cache, potem wiadomość 300 tokenów; TTFT z timings serwera | żadne |
| T7 | **Overlap głębokości 1 (plan #11) z obcinaniem po stop-tokenie na GPU** (lekcja TokenSpeed) | tak | Qwen +1…2%, LFM +4…6% (jak plan #11); lekcja chroni checkpoint GDN przed zepsuciem | średni–wysoki | bramka md5 plus test: stop-token w środku zaakceptowanego okna, potem trafienie w cache następnej tury | cicha korupcja stanu GDN, jeśli obcinanie zostanie na CPU |
| T8 | **Monokernel per warstwa** (TokenSpeed) | fp-reorder (KLD) | nieznany dla gęstego 27B na XTX; TKCC dał +0.22% na AMD; wart rozważenia tylko, jeśli T3 pokaże > 2 ms przerw między kernelami na krok | wysoki (tygodnie) | najpierw T3 (przerwy z trace) | koszt utrzymania; ≤1 CTA/CU kłóci się z occupancy GEMV |

Ranking zysku do wysiłku: **T3 → T2 → T1** (blok kernelowy długiego kontekstu, decyzja o T1 po T3), **T4** razem z planem #6, **T5** dla Enigmy. Pomysły znane i niepowtarzane: DFlash2 z probabilistycznymi draftami (decyzja 16i, sprzężone próbkowanie w topce), ReplaySSM (mamy `rs_lag`), okno atencji MTP (negatywne, łatka 0046).

## 6. Zaparkowane (stratne)

| Pomysł | Dlaczego odpada | Liczby (informacyjnie) |
|---|---|---|
| NVFP4 W4A16 (1Cat na V100, Unsloth/QUASAR) | inny kwant wag | parytet na małych próbkach (GSM8K 289 vs 285/300, MMLU 332 vs 336/400); BFCL −13.5 pp przy pełnym NVFP4 (63a §13) |
| KV FP8 E4M3 (domyślne dla 27B w 1Cat i w przepisie TokenSpeed) | inny kwant KV; skala skalarna na warstwę z checkpointu, domyślnie 1.0 (1Cat `vllm/model_executor/layers/attention/attention.py:113-116`) | dla host KV Flash-Next: KL 0.0017–0.0021, akceptacja −2.3 pp |
| QSA / rzadka atencja (Flash-Next natywnie; dla 27B tylko przez doklejony indeksator, #28 w 63) | rzadka atencja, w 27B nie jest definicją modelu | Flash-Next 250K −18% vs 1K |
| Host KV FP8 z oknem „hot” (`qsa_host_kv`) | FP8 i zależność od rzadkiej selekcji | +0.47 ms (C1) i +2.15 ms (C4) na rundę |
| TokenSpeed: KV mxfp8, stan SSM bf16, BLASST skip-softmax | zmiana numeryki lub pomijanie atencji | — |
| Lookup q16 z adaptacyjnym poszerzaniem (1Cat #366) | bezstratne (weryfikacja), ale to specjalny kontrakt „powtarzany kontekst”, nie zysk ogólny; pokrywa się z naszym lookupem | 316 t/s tylko na powtórzonym kontekście |

## 7. Źródła

**Repozytoria (klony `--depth 1` w `~/src/research66/`):**
- 1Cat-vLLM: https://github.com/1CatAI/1Cat-vLLM, commit `c98a8d66482333eb8d8b87be72e8856445ac99ec` (2026-11-06).
- TokenSpeed: https://github.com/lightseekorg/tokenspeed, commit `b9415081e503a7e378b3aba1ce6e2ceb6054686f` (2026-11-07).

**Release'y i notatki:**
- 1Cat v1.5.2: https://github.com/1CatAI/1Cat-vLLM/releases/tag/v1.5.2 (2026-11-06; wheel z main `9f970d628`, tag `2bb8c2b9`). Strona demo z release'u celowo pominięta (adres IP).
- 1Cat v1.5.1: https://github.com/1CatAI/1Cat-vLLM/releases/tag/v1.5.1 (2026-10-03).
- 1Cat v1.5.0 i v1.2.2: https://github.com/1CatAI/1Cat-vLLM/releases.

**Kluczowe pliki 1Cat:**
- `README.md:60-120`;
- `docker/sm70_release/serve.sh:20-55`;
- `flash-attention-v100/kernel/flash_decode_paged.cu:1257-1330,1819-1918,2043-2125,2676-2880,4446-4562`;
- `include/flash_v100_policy.h:249-276`;
- `docs/design/sm70_dflash2_long_verify_decay.md`;
- `docs/design/sm70_tp4_nomtp_long_context_decode.md`;
- `docs/design/flashnext_host_fp8_kv.md`;
- `docs/design/flashnext_device_qsa_history.md`;
- `docs/design/flashnext_qsa_router_structure.md`;
- `docs/design/sm70_qwen38_flash_next_nvfp4.md:91-94,484-488`;
- `docs/design/grouped_cpu_offload.md`;
- `docs/features/automatic_prefix_caching.md:25-60`;
- `docs/design/sm70_qwen38_nvfp4_decode.md`;
- `docs/design/sm70_dflash2_shared_nvfp4.md`;
- `vllm/models/qwen4_exp/config.py:14-180`;
- `vllm/v1/core/{single_type_kv_cache_manager.py,kv_cache_coordinator.py,partial_prefix_cache.py,kv_cache_manager.py}`;
- `vllm/v1/kv_offload/`.

**Kluczowe pliki TokenSpeed:**
- `README.md`, `AGENTS.md:143-149`;
- `docs/design/{event-loop.md,monokernel.md,tree-speculation.md,cache-concepts.md}`, `docs/spec-finish-checkpoint.md`;
- `docs/recipes/models.md:943-1169`;
- `tokenspeed-kernel/python/tokenspeed_kernel/ops/attention/gdn/README.md`;
- `tokenspeed-kernel-amd/python/tokenspeed_kernel_amd/ops/gfx950/attention/mha/decode.py:273-280,1559-1673,2350-2363`;
- `test/ci/perf/*.yaml`.

**Blogi TokenSpeed** (cytowane w README, nieczytane, liczby wzięte z CI w repo):
- https://lightseek.org/blog/tokenspeed-qwen3-8-flash-next.html
- https://pytorch.org/blog/lightseek-tokenspeed-kernel/

**Nasz kod i dane:**
- topka `~/wt/topka-q63`: `ggml/src/ggml-cuda/fattn-kvq.cu:31,615-636`, `src/llama-memory-recurrent.h:82-103`, `tools/server/server-context.cpp:4253-4258`;
- [63-SYNTEZA](63-SYNTEZA.md), [63d E7](63d-atencja-spec-kwant.md);
- `wiki/REKORDY.md:108`.

**X/Twitter:** nie był potrzebny. Wszystkie twierdzenia pochodzą z GitHuba (release'y, kod, dokumenty w repo).
