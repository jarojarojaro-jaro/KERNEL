# 66c — Hyperkernel (Hyperstition): rezydentny megakernel na B300 i co z tego dla gfx1100

Data: 2026-11-07. Tylko CPU: bez GPU, bez pobierania modeli i wag. Klony (`--depth 1`) w `~/src/research66/`:
- `Hyperkernel` @ `7048c586ab6b1f82fa11f348ae89be2aa7d4dd33` (2026-11-06, jedyny commit „hyperserve demos”);
- `mirage-mpk-amd` (gałąź `mpk-amd-mi355x` z PR #820 MPK) @ `b6ef312bd8ad21dd0aed9095cadfd5c85db4f862` (2026-11-02).

Artefakty Hyperkernela rozpakowałem do `/tmp/hk/` (`zstd -d`; `c1_entry.sass` to 31 MB tekstu SASS, `c1_reference.json` to metadane pakietu). Odnośniki `entry.sass:N` dotyczą pliku rozpakowanego z `kernels/b300/c1/entry.sass.zst`.

Oznaczenia: `[INFERENCE]` = wniosek bez pomiaru; `[SZACUNEK]` = rachunek z naszych liczb; **V** = twierdzenie producenta (marketing); **F** = fakt sprawdzony w kodzie albo w danych.

## 1. TL;DR

1. **Hyperkernel nie publikuje kodu generatora ani źródeł kerneli.** Repo zawiera tylko gotowe pakiety dla B300 (`sm_103a`: SASS + cubin w zstd), host w Ruście (`cudarc`) i skrypty. Ścieżki AMD nie ma żadnej: w całym repo 0 trafień `hip|rocm|amd|gfx`, a twierdzenie „extends to AMD” pochodzi tylko z wątku na X.
2. **Konstrukcja (F, z nazw symboli w SASS):** jeden kooperacyjny kernel `mega_main` na GPU, 148 CTA × 384 wątki, klaster 16, 227 KB SMEM, **rezydentny przez cały czas pracy serwera**. Ma statyczny harmonogram per SM (tablice `ST_N`/`ST_AT`), 140 funkcji etapów `spine_body*`, a zależności idą przez monotoniczne liczniki (`REDG.ADD.64` bez odpowiedzi + poll wątku 0 z unieważnieniem L1). Host komunikuje się przez pierścienie w zmapowanej pamięci hosta. Na GPU dzieje się też próbkowanie, akceptacja draftu (blok 6 = 1 + 5) i stronicowanie KV. Host przyznaje „horyzont” 2 kroków naprzód.
3. **Nagłówek +36.7% (V):** 1129.6 vs 826.5 tok/s/użytkownika p90 przy C1, 4×B300 TP4, harness AgentX. Bazą jest wynik vLLM opublikowany przez NVIDIA, nie powtórzony przez autorów. Hyperkernel używa prawdziwego draftera, a nie podaje akceptacji. Pozostałe dwa słupki porównują 2 użytkowników z 1 oraz C4 ze „standard decode” (słabszą bazą). Jakość sprawdza 7 pytań z podanymi odpowiedziami, bez KL i GSM8K.
4. **Dla Qwen3.8-27B na XTX megakernel dałby realnie +3…+6% decode przy krótkim kontekście** `[SZACUNEK]` (sufit +12% przy 78% pasma, tak jak Hazy). Przy 199k byłoby to +2…+4%, a zegar sesji agentowej skróciłby się o 1–2%. NOWE dane lokalne: fuzje z raportu 54 (−126 dispatchy na krok, 13%) zmierzone w ABBA dały prozę **+0.24% (szum)** i `mvs` **0.0%**. Same granice nie są więc kosztem: płaci się za ogony i rampy w łańcuchach MMVQ → norma → MMVQ (górna granica −2.17 ms na krok).
5. **Rekomendacja:** nie portujemy (nie ma czego). Do zrobienia jest tylko tani PoC-A (1–1.5 dnia): mikrobench hand-offu w **trwałej** siatce 96–192 WG z ≤ 1 atomikiem na WG na etap, czyli wzorcem Hyperkernela i Hazy. Nasz koszt hand-offu z 16a mierzyliśmy na siatkach 1024–3072 bloków. Pełny megakernel Qwena to 40–70 osobodni `[SZACUNEK]`, opłacalny tylko wtedy, gdy PoC-A i PoC-B przejdą progi.

## 2. Co to jest

### 2.1 Hyperkernel / hyperserve (Hyperstition)

| pole | wartość | źródło |
|---|---|---|
| repo | `Hyperstitioncc/Hyperkernel`, MIT, utworzone 2026-11-05, 1 commit, 173 gwiazdki / 20 forków (2026-11-07) | GitHub API |
| zawartość | binarny `hyperserve` 0.2.0 (Rust 2024, `cudarc` 0.19.10, CUDA 13, sterownik ≥ R580) + pakiety `kernels/b300/*` (SASS/cubin/blobs/JSON w zstd, 96 MB) | `Cargo.toml:1-25`, `README.md:5-17` |
| generator „Hyperkernel” | **nieopublikowany**; zapowiedź „over the next couple weeks we will release the entire Hyperkernel stack” | wątek X (1/9) |
| sprzęt | tylko NVIDIA B300 (`sm_103a`); skrypt odmawia innych GPU | `scripts/dsv41/dsv41:70` |
| modele | DeepSeek-V4.1-Flash (TP4, presety c1…c8, kontekst 1M, tablice Engram ~203 GB w RAM hosta), openpilot, Evo 2 7B, Matrix-Game 3.0, ACT, π₀-FAST, ESMFold, trening Qwen 30B MoE | `README.md:7-115`, pakiety |
| AMD | **brak w kodzie**; „our kernel generation extends to other hardware (B200s, AMD, TPUs)” to tylko zdanie z wątku | grep repo: 0 trafień |

**Twierdzenia producenta (V)** z wątku (mirror `r.jina.ai`, oryginał na X nieczytelny bez logowania) i wykresu `HWYitJxasAAayvc`:

| teza | warunki | baza | co sprawdziłem | ocena |
|---|---|---|---|---|
| C1 +36.7%: 1129.6 vs 826.5 tok/s/user (p90) | 4×B300 TP4, AgentX (`agentx-harness==1.0.11`, `--public-dataset semianalysis_cc_traces_weka_062126`, 3600 s), drafter wbudowany (blok 6) | „NVIDIA·vLLM low latency specialized kernels, Oct 20” – liczba opublikowana przez NVIDIA, nie zmierzona przez autorów | harness: `scripts/dsv41/dsv41:93-107`; metryka `1000/p90 ITL`: `agentic_summary.py:110`. AgentX przy spekulacji wymusza AL w silnikach bazowych (R21f), a Hyperkernel nie ma przełącznika wymuszonej AL, więc liczy na prawdziwej akceptacji na syntetycznej treści. Akceptacji nie podaje | **nieporównywalne 1:1**; kierunek wiarygodny, bo osobny pomiar NVIDIA mega daje +40–56% (§5.4) |
| 2 users 1059.6 vs 1 user NVIDIA (+28.2%), 4 users 948.4 vs 1 user (+15%) | jw. | jw. | porównanie różnych współbieżności | chwyt prezentacyjny |
| C4 +90.6%: 948.4 vs 497.5 | jw. | „Standard decode, Oct 2”, nie wariant low-latency | baza słabsza od dostępnej | **zawyżone** |
| C8 +28.5%: 734.5 vs 571.4 | jw. | low-latency Oct 20 | — | jak C1 |
| Evo 2: 9.0 vs 27.3 ms/bp (3×), MG3 37.4 vs 11.6 FPS, ESMFold 195 vs 677 ms, openpilot 2570 vs 1590 aut, Moshi 6.8 vs 9.45 ms/ramkę, trening Qwen 30B MoE 31% MFU (+11%) | 1×B300 itd. | PyTorch + CUDA graph, TensorRT, stack Arc | bazy to zwykle PyTorch: słabe; nie dotyczy nas | nieistotne dla nas |
| „60–100 linii na megakernel”, „wygenerowane w < 50 min”, „generator zbudowany w 20 dni” | — | — | generatora brak; w SASS c1 jest 535 funkcji i 247 152 instrukcje | nieweryfikowalne |

Jakość (F): `scripts/dsv41/known_answers.py:14-23` to 7 promptów (stolica, passkey 30–90k znaków, ciąg liczb) przy T=0 plus `check` „Paris” (`dsv41:80-86`). **Nie ma KL, GSM8K ani porównania z referencją.** Dla odmiany NVIDIA mega przy porcie na B200 raportuje KL 0.0044 i GSM8K 98.2% (§5.4).

### 2.2 Pakiet LLM c1 (F, `c1_reference.json`)

- `point`: `layers=dsv41 batches=1 context=1048576 drafter=true moe_image=single window_keep=2048 prefill_attention=rows`.
- `kernel`: `entries [["mega_main",148]]`, `threads 384`, `cluster 16`, `cooperative true`, `smem 232448`, `stack 8944`, 9 loaderów (`pt_codes`, `pt_mx_codes`, `pt_mx_scales`, `hd_pretile`, `tma_map_at`…) do przepakowania wag z safetensors przy starcie.
- `model`: `block 6` (1 token + 5 draftów), `vocab 129280`, `chunks [2048]` (kawałek prefillu), `ranks 4`.
- obraz pamięci: 6934 „domów” (6712 HBM, 218 peer, 4 host = **202.8 GB w RAM hosta**, tablice Engram), 625 deskryptorów TMA (`map`), 1931 wywołań loaderów.
- presety c2/c4/c5/c8 to ten sam kernel z innymi szerokościami (`batches 1,2[,4[,8]]`), wszędzie blok 6.

## 3. Technika: jak to działa (kod i SASS)

### 3.1 Uruchomienie i życie kernela (host, F)
- `gpu/load.rs:19-35` `boot`: ładuje moduły, buduje arenę i obraz (zapisy, łatki adresów, mapy TMA, loadery), wpisuje adresy pierścieni do globali kernela (`ht_rings`, `ht_ctl`), robi barierę między rankami i **raz** uruchamia kernel. Odtąd kernel działa bez końca.
- `gpu/load.rs:314-337`: start kooperacyjny (`CU_LAUNCH_ATTRIBUTE_COOPERATIVE`) z klastrem 16. Wariant „split” to 7 klastrów × 16 = 112 CTA plus pary w drugim launchu z `PROGRAMMATIC_STREAM_SERIALIZATION`, czyli PDL (`SPLIT_CLUSTERS`, `:17`, `:318-323`). Do tego opcjonalne okno L2 persisting (`cuda.rs:283-291`).
- `gpu/ring.rs:1-69`: pierścień zleceń i pierścień odpowiedzi w pamięci przypiętej hosta, zmapowanej dla GPU (`cuda.rs:105-115`, `cuMemHostAlloc DEVICEMAP`). Liczniki head/tail mają osobne linie 64 B, zapis z `Release`.
- `gpu/feed.rs:110-127`: host wysyła komendy (`seat`, `prompt`, `pages`, `start`, `end`), a potem jednym zapisem `ctl.word(8)` ustawia **grant** = (liczba komend, horyzont kroków). `engine/clock.rs:3,20-29`: `LEAD = 2`, więc GPU może wykonać 2 kroki decode przed następnym grantem. Host nie czeka na żaden krok synchronicznie: GPU sam próbkuje, akceptuje drafty i zapisuje `commits` i logprob'y do pierścienia odpowiedzi.
- `engine/mod.rs:26-49`: pętla hosta to `schedule → push → drain` z `yield_now`. Stronicowanie KV (`pages`) i wywłaszczanie robi host. Detekcja końca (EOS, limit) też jest po stronie hosta, z opóźnieniem ≤ 2 kroków.

### 3.2 Wnętrze `mega_main` (F z symboli SASS, interpretacja `[INFERENCE]`)
- **Rdzeń harmonogramu „spine”:** `spine_main_0`, `spine_main_0_c0/_c1` (role w klastrze), `spine_body0…139` (140 ciał etapów, część parametryzowana warstwą: `SPINE_L0…L17`), `spine_wait`, `spine_done`, `spine_land`. Tablice `ST_N`/`ST_AT`/`ST_RAT`/`ST_INIT` w `.nv.constant3` (`entry.sass:114064-114260`). `ST_N` ma 296 = 2 × 148 wpisów: pierwsza połowa to 185–228 pozycji na SM, druga 816–874. `[INFERENCE]` To dwa statyczne programy per SM (krok decode i krok prefillu), czyli interpreter list instrukcji per SM jak u Hazy. `MEGA_SMID_PERM4` i `MEGA_CL_POS` mapują SM na pozycję w klastrze.
- **Synchronizacja między etapami (F):**
  - `spine_done` (`entry.sass:208675`): `BAR.SYNC` bloku, potem wątek 0 robi `MEMBAR.GPU` i `REDG.E.ADD.64.STRONG.GPU` (atomik bez zwracanej wartości) na licznik etapu. Liczniki leżą co 128 B, a fence jest pomijany, gdy dane poszły przez TMA/bulk.
  - `spine_wait` (`entry.sass:209092`): wątek 0 pętli `LDG.E.64.STRONG.GPU` + `CCTL.IVALL` + `YIELD`, aż licznik ≥ epoka × liczba producentów; potem `BAR.SYNC`. Liczniki są monotoniczne (bez resetu), jak nasze tickety z epoką w 16a.
  - `spine_land` (`entry.sass:208787`): opcjonalny znacznik `SR_GLOBALTIMERLO` per SM i etap (`STG`) plus `REDG.MAX` – **wbudowane profilowanie**.
  - Funkcje `mega_stalled`, `landed_stalled`, `where_wait`, `tg_trap` i globalne `tg_fault` służą do diagnostyki zawieszeń. Pętla w `spine_wait` nie ma limitu prób.
- **Etapy obliczeń (F, nazwy):**
  - GEMV/GEMM na tcgen05: `DenseOne/DenseBody/DenseStream<…6…>` (6 wierszy = szerokość weryfikacji), role warpów `role_mma/role_copy/role_init/role_fini`, 84 `UTCQMMA` (FP8/FP4), 116 `UTCHMMA`, 70 `LDTM` (TMEM);
  - MoE: `moe_body`, `RouteCore`, `RouteCoreDraft`, `GroupedStage`, `SelectRowsStage`;
  - atencja DeepSeek (rzadka, z indeksami): `att::run`, `WideStage` / `attn_wide`, `spine::topk_run`, `scan_run<ScanIdx…>`, `compress_run`;
  - mHC: `HcStatsCore`, `AinArMhc`, `SeamCore`;
  - Engram / embeddingi: `EmbedStage`, `EgkvCore`, `KrRowsStage`;
  - próbkowanie: `SpineSample::accept_top` (akceptacja spekulacji), `SpineNucleusOf` (top-p), `SpineDraw::noise` (szum próbkowania).
- **Mieszanka instrukcji c1 (F):** 247 152 instrukcje; 1634 `SYNCS.EXCH.64` i 296 `SYNCS.PHASECHK…TRYWAIT` (mbarriery), 124 `UBLKCP` (kopie bulk), 12 `UTMALDG` (TMA), 4 pary `UCGABAR` (bariera klastra), 22 `NANOSLEEP`, 4138 `LDL` / 2931 `STL` (spill na stos 8944 B).

### 3.3 Jak radzą sobie z decode ograniczonym pamięcią
- Bez granic kerneli: etap startuje, gdy licznik producenta dojdzie do progu. Warpy `role_copy` ładują wagi przez TMA/bulk do SMEM niezależnie od czekania na aktywacje, więc **prefetch wag przed czekaniem** jest wbudowany w konstrukcję. To ta sama lekcja co nasza [[lekcja-megakernel-prefetch-nie-granica]].
- Spekulacja z blokiem 6 zamienia GEMV na GEMM M=6 na tensor core'ach. Przy TP4 i 8 TB/s na GPU krok jest w reżimie latencji, nie pasma. `[SZACUNEK]` 1129.6 tok/s przy AL ≈ 3–4 daje krok ≈ 2.7–3.5 ms, a NVIDIA szacuje podłogę pasma tego kroku na ~1 ms (§5.4).
- Brak hosta na ścieżce krytycznej: grant z horyzontem 2 kroków, próbkowanie i akceptacja na GPU.

### 3.4 Ścieżka AMD/HIP: czego by wymagała
Nic z repo nie przenosi się bez generatora:
1. **Kod urządzenia:** 100% to SASS `sm_103a` z instrukcjami bez odpowiedników na RDNA3: tcgen05/TMEM, TMA, mbarriery, klastry/DSMEM, `REDG` do pamięci multicast NVLink. Na gfx1100 trzeba by napisać wszystkie etapy od nowa, a do tego Qwen3.8 (GDN + FA + MTP, K-quanty GGUF) to inny graf niż DeepSeek.
2. **Host:** `cudarc` (Driver API, `cuTensorMapEncode*`, `cuMulticast*`, `cuMemExportToShareableHandle`). Port na HIP jest wykonalny: `hipModuleLaunchCooperativeKernel`, `hipHostMalloc` z mapowaniem, bez map TMA i bez multicastu. Format pakietu (`hyperserve-bundle-2`: zapisy, łatki, loadery, porty) nie zależy od producenta, poza rekordami `map` (TMA).
3. **Generator:** jedyna realna droga to wydanie stosu z backendem AMDGPU. Wątek obiecuje wydanie „w kilka tygodni”, ale wymienia „AMD” bez architektury. `[INFERENCE]` Jeśli backend AMD powstanie, to najpierw dla CDNA (MI3xx, wave64, MFMA), tak jak u Mirage (§5.2), nie dla RDNA3.

## 4. Co megakernel dałby na naszym stosie (gfx1100, Qwen3.8-27B Q4, MTP)

### 4.1 Liczby, które już mamy
| wielkość | wartość | źródło |
|---|---|---|
| dispatchy na krok MTP (PM4=0) | **946** (draft ×4: 109, weryfikacja n=5: 824, update MTP ~13) | [54 §1](54-mniej-granic.md) |
| granice w taśmie weryfikacji | 919 | [37 §4](37-proza-100.md) |
| koszt granicy PM4 (mikrobench) | 0.46–0.86 µs; bez PM4 ~2.75 µs | wiki `pm4-replay` |
| PM4 vs graf HIP (Qwen MTP) | 29.16 → 27.80 ms/krok (−1.36 ms) | wiki `pm4-replay` |
| górna granica „bez granic” (wynik błędny, tylko czas) | partia pp5 24.74 ms: −0.78 (340 granic MMVQ), −0.73 (208 przed normą), **−2.17 ms (548 granic razem, nadaddytywnie)** | [37 §4](37-proza-100.md) |
| luki hosta | GPU stoi **410 µs/krok** między taśmami | [37 §2](37-proza-100.md) |
| bajty wag na krok | 18.42 GB → 19.19 ms przy 960 GB/s, 19.89 ms przy 926 GB/s; „lost vs roofline” 7.00 ms (PM4=0) | [47](47-kernel-lab.md) |
| krok produkcyjny | spec_sweep T=1 114.8 t/s przy 27.4–27.7 ms/krok → efektywnie 18.42/27.6 = **667 GB/s = 69% z 960** | [63-SYNTEZA](63-SYNTEZA.md), [63e](63e-metodologia-agenci.md) |
| małe kernele | GDN 0.72, rms_norm 0.67 (praca ~4.5 µs/wywołanie, nie czekanie), FA kvq 0.56 (stałe ~18–20 µs), gdn_conv 0.26, unary 0.22, set_rows 0.18, rope 0.18 ms/krok | [47](47-kernel-lab.md), [51](51-male-kernele.md) |
| hand-off przez pamięć na RDNA3 | zjada 56–94% zysku z usunięcia granicy na siatkach 1024–3072 bloków | [16a](16a-pm4-pdl.md), [[lekcja-handoff-rdna3]] |
| **NOWE: fuzje z raportu 54 zmierzone** | ABBA x54 + x54r (`~/qwen-opt/launchcut/logs/prose.jsonl`, `copy_bench.jsonl`, 2026-10-21): proza A 78.54/78.65/78.01/78.97 vs B (`ATTN_PREP_MT=1 KVQ_FWHT_GATE=1`) 78.63/78.69/78.91/78.68 t/s → **+0.24%**, w szumie; `mvs` 428.49 vs 428.55 → **0.0%**. Akceptacja 0.293 w obu. Env ramion potwierdzony w logu kolejki (`arm x54r-Ba … XENV=…`); że matcher fuzji faktycznie zadziałał, log nie pokazuje `[INFERENCE]` | ten raport (dane z dysku; wiki `raport-54` mówi jeszcze „niezmierzone”) |

**Narzut na token (odpowiedź na pytanie z zadania):** to nie „~600 launchy na krok”, tylko **946 dispatchy na krok**, czyli ~320 na token przy ~2.9 tok/krok (greedy 106 t/s). Same pakiety granic PM4 to 946 × 0.46–0.86 µs ≈ 0.43–0.81 ms/krok (1.6–2.9% kroku). Gdyby zamiast PM4 był zwykły graf HIP, wyszłoby ~2.6 ms. Większy jest koszt ukryty: ogon jednego MMVQ i rampa następnego. Górna granica dla łańcuchów MMVQ → norma → MMVQ to 2.17 ms/krok (8.8%). Pomiar x54 potwierdza, że usunięcie 126 granic poza tymi łańcuchami nie daje nic mierzalnego.

### 4.2 Szacunek zysku (bezstratny, `[SZACUNEK]`)
Pula, którą megakernel może odzyskać, na krok ~27.6 ms:

| składnik | sufit | realnie na RDNA3 | uzasadnienie |
|---|---|---|---|
| luki hosta (rezydentna pętla MTP z próbkowaniem na GPU, jak grant Hyperkernela) | 0.41 ms | 0.3–0.4 ms | = plan #11 z 63-SYNTEZA (+1…2%) |
| ogony/rampy w łańcuchach MMVQ → norma → MMVQ | 2.17 ms | 0.5–1.0 ms | 16a: po synchronizacji zostaje 6–44% zysku; R37 szacuje ~0.5 ms |
| małe operacje nałożone na strumień wag (norma, conv GDN, RoPE, set_rows; ~2.8 ms pracy) | ~1.5 ms | 0.3–1.0 ms | są na ścieżce krytycznej; nakładanie możliwe tylko z prefetchem wag następnego MMVQ do VGPR `[INFERENCE]` |
| sprawność MMVQ (738–787 GB/s → ~900) | ~1.0–1.5 ms | 0 | megakernel tego sam nie naprawia; to strojenie kerneli (47/50x) |
| **razem** | **~4 ms (sufit Hazy 78%: 24.6 ms → +12%)** | **1.1–2.4 ms → +4…+9.5%, środek +5–6%** | zgodne z 15a (+3–6%) |

- **Długi kontekst:** oszczędność w ms jest podobna, ale krok rośnie (199k: 74.5 t/s), więc względnie +2…+4%. Przyrost ~18 ms/krok między 1.7k a 199k to FA i maska ([63d E7](63d-atencja-spec-kwant.md)), czego megakernel nie naprawia. Tam lepsze są plany #3 i #8 z 63.
- **Sesja agentowa:** decode to ~32% zegara ([[lekcja-agent-prefill-nie-decode]]), więc +5% decode daje ≈ −1.5% zegara.
- **Bezstratność:** możliwa bitowo, jeśli każdy etap zachowa matematykę i kolejność redukcji obecnych kerneli (MMVQ z kwantem q8_1, drzewo `rms_norm_mul_f32_unrolled<5>`, `kvq`). Bramka md5 (c4708318 / 6f14e814) + KLD jak zawsze.

### 4.3 Koszt portu na gfx1100 `[SZACUNEK]`
- **Port Hyperkernela:** niemożliwy dziś (brak generatora i źródeł, tylko SASS).
- **Własny megakernel Qwena (dataflow, trwała siatka):** 40–70 osobodni. Wchodzi w to weryfikacja n=5 dla 64 warstw (48 GDN + 16 FA kvq), łańcuch draftu MTP ×4, próbkowanie i akceptacja na GPU, KV q4_0 z FWHT, checkpointy stanu GDN i cache sesji. 15a liczyło 25–35 osobodni na warstwę LFM, a Qwen ma dwa typy warstw, MTP i dłuższy kontekst. Do tego stałe utrzymanie przy rebase'ach upstream.
- **Ryzyka:** zawieszenia (trwała pętla bez limitu u Hyperkernela; NVIDIA mega zawiesił produkcję 2× w 12.5 h, §5.4). Ewikcja kolejki KFD / CWSR przy rezydentnym kernelu to ta sama klasa co nasze page faulty PM4 (raport 17) `[INFERENCE]`. Co-residency: 96 CU, przy 1–2 WG/CU wszystkie WG muszą być rezydentne. Windows (Enigma) ma TDR, więc kernel rezydentny „na zawsze” nie wchodzi w grę.

## 5. Prior art: co znamy i co jest nowe

| projekt | stan w naszej wiedzy | co nowego (2026-11) |
|---|---|---|
| **Hazy Megakernels** (Llama-1B BF16, H100 78% pasma; interpreter per SM, stronicowany SMEM, liczniki `atomicAdd`) | znane: [[megakernele-prior-art]], R15a §2.6 | brak zmian; repo `HazyResearch/Megakernels` HEAD `7309cec801` (2025-06-02). Hyperkernel to w praktyce ta sama architektura, wygenerowana automatycznie i rozszerzona o serwowanie |
| **MPK / Mirage** (OSDI ’26, Qwen3-8B A100 14.5 → 12.5 ms) | znane | **NOWE: PR #820 (2026-11-02, otwarty) – backend HIP dla gfx950 (MI355X, CDNA4)**: „static megakernel” na typ warstwy i batch (nie jeden rezydentny kernel), Kimi K3 TP8 w SGLang ROCm: **2.02× przy bs1**, 1.24–1.28× przy bs64; GSM8K 0.954 vs 0.958. Kod: `include/mirage/static_megakernel_hip/core.cuh:2-7` („no PDL: HIP starts a kernel after the previous one ended”), `:153` (store z `sc0 sc1`, bity CDNA), `:514` (`s_sleep` w pollu). Pierwszy otwarty runtime megakernela w HIP z protokołami hand-off/reset/start i notatkami negatywnymi (`amd/notes/batch_decode_bs1_64.md:219`: `POLL_SLEEP`, `COOP_LAST_NOWAIT` itd. „ties”). Na RDNA3 trzeba przepisać asm (sc0/sc1 → glc/dlc), wave64 → wave32 i MFMA → WMMA/dot |
| **vLLM MonoKernel** (ROCm, „tagged pairs”) | znane: [[vllm-monokernel]], 63c (gfx942 #60731) | — |
| **NVIDIA `sgl-nvidia-mega`** („SGLang low-latency mode”) | znane tylko z bloga (63e §4, liczba przy symulowanej AL 5.4) | **NOWE: port na B200 i produkcja** (`caiovicentino/deepseek-v4.1-flash-megakernel-4x-b200` @ `8315e89094`): per-user decode **+40…+56% przy 1–8 równoległych**, remis przy 9–32; KL 0.0044, GSM8K 98.2%; **2 zawieszenia w 12.5 h**, produkcja wróciła na zwykłą ścieżkę; krok DSpark ~6.1 ms vs podłoga pasma ~1 ms; NVIDIA naliczyła ~1600 kerneli na krok na stock vLLM GB300. Repo pluginu `sgl-project/sgl-nvidia-mega` HEAD `7b6ff0e2c5` (2026-11-07) |
| **Fleet** (AMD Research, arXiv 2604.15379) | **NOWE** | trwały runtime z zadaniami per chiplet (wspólne L2 die'a); MI350 Qwen3-8B 1.3–1.5× vs vLLM przy bs 1–8; L2 hit 12 → 54% przy bs32. Dla RDNA3 (jeden die, brak L2 per chiplet) przenosi się tylko idea zadań z lokalnością cache |
| **Ada-MK** (arXiv 2605.11581) | **NOWE** | megakernel na Ada (L20) z harmonogramem wyliczonym offline (bez rozgałęzień w runtime), wtyczka do TRT-LLM: +23.6% vs TRT-LLM, +50.2% vs vLLM przy bs1; launch overhead 14.6% e2e. Potwierdza, że statyczny harmonogram (jak `ST_N` w Hyperkernelu) wystarcza przy stałej konfiguracji |
| Kimi K3 specialized decode, Lucebox (3090 1.55×), TensorFold (M5: bariera siatki przegrywa), TKCC (AMD +0.22%), Flapping Airplanes, Fraser (DSv4.1 500+ t/s, megakernel WIP) | znane: R21f, R15a, R63e, R60b, R60c | bez zmian |
| Event Tensor (MLSys 2026, dynamiczne megakernele) | **NOWE** (tylko tytuł z programu MLSys, nieczytane) | — |

## 6. Macierz przydatności

| platforma | co z Hyperkernela | werdykt |
|---|---|---|
| **AMD gfx1100, topka** | nic do uruchomienia. Wzorce: trwała siatka z ≤ 1 atomikiem na WG na etap, monotoniczne liczniki co 128 B, prefetch wag przed czekaniem, grant z horyzontem dla pętli MTP, znaczniki czasu per etap | PoC-A/B (§7); realnie +3…+6% decode po 40–70 osobodniach; nie przed planami #1–#8 z 63 |
| **Enigma, NVIDIA CUDA** (upstream llama.cpp) | binaria tylko `sm_103a`, na kartach konsumenckich nic nie ruszy. Upstream ma grafy CUDA, a PDL (#22522) tylko dla CC ≥ 9.0, więc sm_120 tak, sm_86/89 nie. Na 3090/4090 megakernel miałby względnie więcej do wzięcia (granica grafu 0.8–1.3 µs × ~950), ale Qwen 27B jest tam już na 77% pasma (15a §3.3) | nic do zrobienia; śledzić, czy generator obsłuży sm_86/89/120 |
| **Apple Metal** | Metal nie gwarantuje postępu między threadgroupami, więc czekanie w pętli na inny threadgroup grozi zakleszczeniem; TensorFold M5 z barierą siatki przegrał | nie dotyczy |
| **Intel (Arc B580/B60, Xe2)** | brak backendu; SYCL bez gwarancji postępu poza rozszerzeniami `[INFERENCE]` | nie dotyczy |
| **Strix Halo (gfx1151)** | ta sama rodzina ISA co gfx1100, więc PoC z gfx1100 byłby przenośny. Przy 256 GB/s krok 27B to ~70 ms, a stały narzut ~3 ms, więc ≤ +3% `[SZACUNEK]` | niski priorytet |

## 7. Pomysły do przetestowania (tylko bezstratne)

| # | pomysł | bezstratny? | oczekiwany zysk i dlaczego | wysiłek | jak testować na naszej maszynie | ryzyko |
|---|---|---|---|---|---|---|
| A | **PoC-A: hand-off w trwałej siatce** (wzorzec Hyperkernela/Hazy): 96 lub 192 WG × 256 wątków, łańcuch N=200 syntetycznych matvec w kształcie Q5_K n=5, r5120. Producent: wątek 0 każdego WG robi `__hip_atomic_fetch_add` (relaxed, scope agent) po `__threadfence()` na licznik etapu co 128 B. Konsument: najpierw wagi następnego etapu do VGPR, potem wątek 0 polluje (`__builtin_amdgcn_s_sleep(1)` + load z bypassem L0/L1), potem `__syncthreads` | tak (bitowo z definicji; kontrola bitowa wyjścia jak w X1) | brak zysku bezpośrednio; rozstrzyga, czy megakernel na XTX ma sens. Hipoteza: przy 96–192 producentach zamiast 1024–3072 hand-off kosztuje ≤ 0.25 µs i zostawia ≥ 50% zysku z „bez granicy” (16a mierzył 6–44% na dużych siatkach) | 1–1.5 d | rozszerzenie `~/qwen-opt/pm4pdl/x1/pdl.cpp` + `pdl_kern.hip`; metryka (T(1000) − T(200)) / 800, mediana z 25 par; trzy ramiona: taśma PM4, PM4 bez granic (UB), trwała siatka. **Kill:** hand-off > 0.3 µs albo < 30% zysku UB | zawieszenie: bounded spin + słowo błędu (jak 16a), test w kolejce z `GUARD=1` |
| B | **PoC-B: jedna warstwa GDN i jedna FA jako trwały kernel** (n=5, lista etapów skopiowana z taśmy PM4: norma → qkv MMVQ → conv → GDN → gated norm → out → add → norma → gate/up → silu·mul → down → add), matematyka 1:1 z kerneli topki | tak, jeśli kolejność redukcji identyczna; bramka md5 warstwy | warstwa −8…−15% → po rozszerzeniu na model **+3…+6% decode** | 4–6 d (po A) | harness warstwy na prawdziwych wagach z lokalnego GGUF (bez pobierania); porównanie z czasem tej warstwy w taśmie (`klab profile` + `ub_bench.sh`, `llama-bench -p 5 -n 0`). **Kill:** < 8% czasu warstwy albo md5 ≠ | jak A + spill VGPR (Hyperkernel ma stos 8944 B na wątek; u nas Q6_K n5 już ma 251 VGPR) |
| C | **Rezydentna pętla MTP z grantem horyzontu** (host daje „wolno do kroku t+2”; draft → weryfikacja → akceptacja → następny draft bez hosta) | tak (rozkład bez zmian; greedy bitowo) | luki hosta 410 µs/krok → **+1…+1.5%**; Hyperkernel to potwierdza, ale pomysł jest już planem #11 z 63 | 5–10 d | `spec_sweep` + proza E0 ABBA (`p100_arm.sh`), bramka md5 `p100_md5.sh` | zmiany w API decode i próbkowaniu llama.cpp; `--grammar` i stopy po stronie hosta |
| D | **Znaczniki czasu per dispatch w taśmie PM4** (jak `spine_land`: `s_memrealtime` w prologu/epilogu za przełącznikiem albo pakiet CP z timestampem `[INFERENCE]`) | tak (tylko narzędzie) | 0% t/s; daje atrybucję 7 ms „lost vs roofline” w trybie PM4, którego rocprofv3 nie widzi | 1 d | `GGML_HIP_PM4_DEBUG` + nowy tryb; zgodność z `klab profile` przy PM4=0 | narzut pomiaru; poza produkcją |
| E | **Zamknąć wiedzę z x54** (bez GPU): fuzje A+B z raportu 54 ≈ 0%; pozycje C/F z 54 („mniej dispatchy” poza łańcuchem MMVQ) obniżyć w kolejce | — | oszczędza dni pracy | 0.5 h (wiki) | dane już są: `~/qwen-opt/launchcut/logs/` | — |

Kolejność: E → A → (jeśli A przejdzie) B → decyzja o pełnym megakernelu. C jest niezależne (plan #11).

## 8. Zaparkowane (stratne)

| pomysł | dlaczego stratny | liczby informacyjnie |
|---|---|---|
| KV FP8 (`--kv-cache-dtype fp8_e4m3` u NVIDIA mega) | inny kwant KV | wymagany przez plugin; KL 0.0044 |
| aktywacje MXFP8 w kernelach (MonoKernel gfx942, 63c) | kwantyzacja aktywacji inna niż q8_1 | — |
| opt-in FP8 attention (MonoKernel GLM, 15a) | dodatkowa kwantyzacja | 4.80 ms vs 5.92 ms |
| numeryka Hyperkernela (własne GEMM tcgen05 FP8/FP4, własne próbkowanie) | wyniki nie bitowe względem referencji; KL/GSM8K nieopublikowane | — |
| wagi NVFP4/MXFP4 | inny kwant wag | — |

## 9. Źródła

- Hyperkernel: https://github.com/Hyperstitioncc/Hyperkernel (commit `7048c586ab6b1f82fa11f348ae89be2aa7d4dd33`, 2026-11-06); pliki: `README.md`, `Cargo.toml`, `src/bundle.rs:94-179`, `src/gpu/load.rs:17-35,297-337`, `src/gpu/cuda.rs:105-115,261-305`, `src/gpu/ring.rs:1-69`, `src/gpu/feed.rs:110-127`, `src/engine/clock.rs:1-30`, `src/engine/mod.rs:26-49`, `scripts/dsv41/dsv41:34,70,93-107`, `scripts/dsv41/agentic_summary.py`, `scripts/dsv41/known_answers.py:14-23`; SASS `kernels/b300/c1/entry.sass.zst` (po `zstd -d`: linie 114064-114260, 208675, 208787, 209092); metadane `kernels/b300/c{1,2,4,5,8}/reference.json.zst`.
- Wątek: https://x.com/hyperstition_cc/status/2118432349352595528 (2026-11-05; X bez logowania nieczytelny, treść 1/9…11/11 z mirrora https://r.jina.ai/https://x.com/hyperstition_cc/status/2118432349352595528); wykres https://pbs.twimg.com/media/HWYitJxasAAayvc?format=jpg&name=large.
- Wtórne: https://applycoding.com/news/2026-11-06-hyperstition-open-sources-hyperkernel-for-faster-gpu-inference ; https://agihunt.info/en/p/1a1ad8957c15861964fb305f69b (oba 2026-11-06, bez nowych faktów).
- Mirage MPK HIP: https://github.com/mirage-project/mirage/pull/820 (gałąź `mpk-amd-mi355x` @ `b6ef312bd8ad21dd0aed9095cadfd5c85db4f862`); MPK: https://arxiv.org/abs/2512.22219.
- NVIDIA mega na B200: https://github.com/caiovicentino/deepseek-v4.1-flash-megakernel-4x-b200 (`8315e89094`, 2026-10-21); https://github.com/sgl-project/sgl-nvidia-mega (`7b6ff0e2c5`); https://www.lmsys.org/blog/2026-10-18-sglang-low-latency-mode/.
- Fleet: https://arxiv.org/abs/2604.15379 ; Ada-MK: https://arxiv.org/abs/2605.11581 ; Hazy: https://github.com/HazyResearch/Megakernels (`7309cec801`); Event Tensor: https://mlsys.org/virtual/2026/session/3718.
- Nasze: [15a](15a-monokernel.md) §2.6, §3.2; [16a](16a-pm4-pdl.md); [37](37-proza-100.md) §2–4; [47](47-kernel-lab.md); [51](51-male-kernele.md); [54](54-mniej-granic.md); [63-SYNTEZA](63-SYNTEZA.md); [21f](21f-inferencex.md); wiki `pm4-replay`, `lekcja-handoff-rdna3`, `lekcja-megakernel-prefetch-nie-granica`, `megakernele-prior-art`; pomiar x54: `~/qwen-opt/launchcut/logs/{prose,copy_bench}.jsonl`, `~/qwen-opt/queue/logs/` (linie `arm x54…`).
