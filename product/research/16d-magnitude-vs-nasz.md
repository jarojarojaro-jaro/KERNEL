# 16d — Magnitude vs nasz fork vs upstream (eksperyment 15c X1) + KLD Nemotrona, 2026-10-16

Surowe dane: `~/qwen-opt/cloud/results/magnitude-vs-3090-20261016/` i `…/magnitude-vs-5060ti-20261016/` (`x/xbench.jsonl`, `servers.jsonl`, `logs/`, `harness/`, `kld/`). Skrypty: `~/qwen-opt/cloud/runs/magnitude-3090/` (`inst/*`, `analyze.py`); `runs/magnitude-5060ti/` używa tych samych `inst/`.

## 0. Wnioski

1. **Kill criterion X1 nie zadziałał.** Na nie-kopii Magnitude nie jest ≥ fork −5% na obu kartach:
   - LFM2.5-24B-A2B (bez draftera, czyste porównanie kerneli):
     - 3090: fork **291.6** vs Magnitude 209.0 t/s (**+40%**);
     - 5060 Ti: fork **205.1** vs Magnitude 157.8 t/s (**+30%**).
   - Magnitude jest tu na poziomie upstreamu (216.6 i 153.4).
2. **Qwen3.8-27B na 3090, nowe pisanie (T=1): remis.** Magnitude 65.7 t/s (DFlash2), fork 65.7 t/s (MTP n=4), upstream 49.2 t/s.
   - Magnitude dochodzi do remisu drafterem, nie kernelami. Ma lepszą akceptację na kodzie i EN, a dużo gorszą na polskiej prozie (pl-proza 30.1 vs 44.3 t/s).
   - Ten sam drafter DFlash2 w naszym forku daje 49.0 t/s. Magnitude prowadzi DFlash2 dużo taniej niż llama.cpp: 47.6 vs 64.0 ms/krok przy tym samym tok/krok ≈ 3.1.
3. **Kopiowanie i edycja kodu (T=0): na Qwenie wygrywa Magnitude.**
   - copy 64k: 80.2 vs 69.3 t/s; code-edit: 156.1 vs 105.2 t/s (+48%).
   - Powód: DFlash2 daje 7.3–7.8 tok/krok, a nasze MTP n=4 ma sufit 5.
   - Nasz fork z ich drafterem: copy 94.0 / code 121.1. Na copy bije Magnitude, na code-edit przegrywa.
   - Na LFM (bez draftera) code-edit wygrywa nasz fork: 280 vs 217 t/s na 3090, 200 vs 162 na 5060 Ti.
4. **Prefill / TTFT: nasz fork szybszy.** Qwen na 3090: 64k w 72 s vs 86 s, TTFT 2k 1.68 s vs 2.04 s. LFM: pp 2k 7907 vs 5890 t/s.
   - Nasz fork zajmuje mniej VRAM na Qwenie (19.6 vs 22.2 GB). Na LFM jest podobnie (15.5 vs 15.9 GB).
5. **Luki Magnitude (z kodu i błędów):**
   - brak IQ2_S i Q4_1, więc **żaden Qwen3.8-27B GGUF ≤ 16 GB się nie ładuje**;
   - LFM Q4_K_M na 16 GB: OOM przy 64k, działa przy 32k;
   - brak HIP;
   - Q3_K jest importowany do 6-bitowej reprezentacji (bez oszczędności VRAM).
   - Szczegóły w §4.
6. **Nemotron KLD (`TOPK_MOE_NP2`): PASS.** KLD 0.00214 vs szum upstreamu 0.00225. Przy `NP2=0` logity są bit w bit równe upstreamowi. Pełna sekcja w `14-nemotron-3090.md` §13.

## 1. Warunki

| | RTX 3090 | RTX 5060 Ti 16 GB |
|---|---|---|
| instancja Vast | 56264196 (i5-14400, kwota 15.36 CPU → `-t 15`, sterownik 595.84, 280 W) | 56262949 (EPYC 7502, cgroup v1 7.68 CPU → `-t 8`, sterownik 580.173.02, 180 W) |
| fork | `cuda-3090-opt` @ `3da7a02ec` (profil Ampere w defaultach) | `cuda-v070-5060ti` @ `0488cba76` + `GGML_HIP_GATE_UP_Q8=0 GGML_HIP_Q8_IDS=0` |
| upstream | v0.7.0 (`620d222`) | v0.7.0 |
| Magnitude | `magnitude-engine` z `954d677d` (źródło wydania cli@0.2.9), zbudowany lokalnie (`cargo build --release --locked`, rustc 1.91.1), NVRTC 12.9 z paczki release | to samo |

- **Modele (te same pliki GGUF dla wszystkich silników, sha256 w `inst/models.tsv`):**
  - Qwen3.8-27B UD-Q4_K_XL (17.56 GB, rev. `27af057e` = katalog Magnitude, plik identyczny z naszym `4ca72078`);
  - LFM2.5-24B-A2B Q4_K_M (14.53 GB).
  - Drafter Magnitude: `magnitudedev/Qwen3.8-27B-DFlash2-GGUF` Q8_0 (2.06 GB).
  - Magnitude nie ma własnego formatu. Przepakowuje wagi GGUF przy ładowaniu i nie zmienia bitów na wagę, z wyjątkiem Q3_K/IQ3_S → q6k.
- **Flagi (tuned per silnik):**
  - llama.cpp: `-fit off -ngl 999 -fa on -np 1 -c 67584`.
  - Qwen: KV q4_0, `--spec-type draft-mtp --spec-draft-n-max 4`; fork dodatkowo `--spec-draft-vocab … -n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs`.
  - LFM: KV q8_0, `-b 2048 -ub 2048`.
  - Magnitude: domyślne (KV K8V4, metoda z katalogu: Qwen `dflash2` + drafter, LFM `plain`), `--context-tokens 67584`.
  - 5060 Ti LFM: wszystkie silniki przy `-c 33792` i copy 32k (Magnitude nie mieści 64k).
- **Autotune Magnitude:** pełny budżet 60 s przy pierwszym starcie na pustym cache. Czas do gotowości: Qwen 51.5 s, LFM 62.5 s; ze strojeniem z cache 5–10 s. Ślad: `logs/*.mag.first.tuning.jsonl` (746 wpisów dla Qwena). Pomiary szły na cache, tak jak w zainstalowanej aplikacji.
- **Klasy obciążenia** (klient `inst/xbench.py`, metryki z `timings` serwera, oba silniki zwracają format llama.cpp; zegar klienta zgadza się z nimi):
  - **(a) sweep:** 6 promptów spec_sweep × 3 seedy, T=1, 400 tok, thinking off.
  - **(b1) copy:** fixture `prose-repeat` Magnitude (linie 0 i 1, docięte do 64k ich regułą `Fixture.sized` z szablonem i tokenizerem llama-server), T=0, 256 tok.
  - **(b2) code-edit:** 4 pliki llama.cpp v0.7.0 (`pad.cu`, `ngram-cache.h`, `sampling.h`, `lazy.py`) + polecenie rename/komentarz → „cały plik”, T=0, 1024 tok.
  - Do tego TTFT 2k (×3) i 16k, VRAM peak (nvidia-smi).
- **Kolejność:** ABBA `mag fork base base fork mag`, każda runda na świeżym serwerze.
  - Dla Qwena na 3090 runda mag#1 przepadła (błąd klienta: Magnitude wymaga pola `model`), a dodatkowa mag#7 padła na „MemoryPressure HostRam” (31 GB RAM hosta). **Magnitude Qwen 3090 = 1 runda.**
  - LFM: pełne 2 rundy na silnik.
  - `forkdf` (fork + drafter DFlash2, n=15): 2 rundy po ABBA.

## 2. Tabela główna (mediana rund; t/s dekodu)

| karta | model | klasa | Magnitude | nasz fork | upstream | uwagi |
|---|---|---|---|---|---|---|
| 3090 | Qwen3.8-27B Q4_K_XL | sweep T=1 | 65.7 (3.13 tok/krok) | **65.7** (2.98) | 49.2 | fork+DFlash2: 49.0; Magnitude 1 runda |
| 3090 | Qwen3.8-27B | copy 64k | **80.2** (7.31 tok/krok) | 69.3 (4.49) | 58.6 | fork+DFlash2: **94.0** (7.43) |
| 3090 | Qwen3.8-27B | code-edit | **156.1** (7.82) | 105.2 (4.91) | 78.7 | fork+DFlash2: 121.1 |
| 3090 | Qwen3.8-27B | prefill 64k / TTFT 2k | 744 t/s / 2.04 s | **888 / 1.68 s** | 887 / 1.64 s | |
| 3090 | Qwen3.8-27B | VRAM peak | 22.2 GB | 19.6 GB | 19.3 GB | |
| 3090 | LFM2.5-24B Q4_K_M | sweep T=1 | 209.0 | **291.6** | 216.6 | bez draftera wszędzie |
| 3090 | LFM2.5-24B | copy 64k | **163.5** | 132.5 | 127.8 | patrz uwaga o LFM niżej |
| 3090 | LFM2.5-24B | code-edit | 216.9 | **280.4** | 212.7 | |
| 3090 | LFM2.5-24B | pp 2k / 16k, VRAM | 5890 / 5840, 15.9 GB | **7907 / 7995**, 15.5 GB | 7789 / 7894, 15.5 GB | |
| 5060 Ti | Qwen3.8-27B UD-Q3_K_XL | wszystkie | **nie ładuje się** (IQ2_S) | sweep 58.0, copy 52.0, code 98.2 | 43.5 / 44.7 / 70.8 | Q4_K_XL nie mieści się w 16 GB |
| 5060 Ti | LFM2.5-24B Q4_K_M, ctx 32k | sweep T=1 | 157.8 | **205.1** | 153.4 | |
| 5060 Ti | LFM, ctx 32k | copy 32k | 125.4 | **149.9** | 123.0 | |
| 5060 Ti | LFM, ctx 32k | code-edit | 161.6 | **199.9** | 150.4 | |
| 5060 Ti | LFM, ctx 32k | pp 2k, VRAM | 4728, 14.9 GB | **6055**, 14.9 GB | 6081, 14.9 GB | |

- Rozrzut rund ≤ 2.4% wszędzie (`analyze.py`).
- Per prompt Qwen 3090 (t/s, tok/krok):

  | silnik | pl-proza | pl-tech | pl-kod | en-chat | en-tech | en-code |
  |---|---|---|---|---|---|---|
  | Magnitude | 30.1 / 1.32 | 52.9 / 2.48 | 109.2 / 5.29 | 60.6 / 2.87 | 70.7 / 3.39 | 86.5 / 4.18 |
  | fork | 44.3 / 1.97 | 66.6 / 2.99 | 77.8 / 3.52 | 57.2 / 2.61 | 64.8 / 2.97 | 70.5 / 3.24 |

  DFlash2 wygrywa na kodzie, a na polskiej prozie traci 32%.
- **Harness Magnitude** (`magnitude-bench job --mode prose-repeat --context 64k --section context --passes 2`). Nasz llama-server szedł przez wrapper z flagami tuned.
  - Qwen 3090, dekod: Magnitude 121.3, fork 71.5, upstream 58.5 t/s.
  - Prefill: 763 / 896 / 893 t/s.
  - Akceptacja: 100% / 94.8% / 95.7% (`harness/qwen-*/report.md`).
  - Ich „decode tok/s” liczy (tokeny)/(completion − TTFT) ze strumienia. Dla Magnitude daje to więcej niż `timings.predicted_ms` samego serwera (80 t/s). Dla llama.cpp obie miary się zgadzają. `[INFERENCE]`: Magnitude wlicza w `decode_ms` część pracy, którą ich harness uznaje za TTFT.
  - Harness dla LFM nie przeszedł: LFM generuje tekst rozumowania mimo `enable_thinking: false`, a harness to odrzuca.
- **Jakość:**
  - md5 greedy nie jest porównywalny między silnikami.
  - Magnitude nie wystawia logitów w API, więc KLD jego wyjścia nie zmierzyłem.
  - Proxy: zgodność z oczekiwanym tekstem.
    - Qwen copy: prefiks 100% i ratio 0.91/0.90 identycznie dla wszystkich silników.
    - code-edit: ratio 0.969 identycznie.
  - LFM na prose-repeat zaczyna od rozumowania („We need to output the passage…”), więc copy na LFM nie jest prawdziwym kopiowaniem (prefiks 0 u wszystkich). Jakościowo silniki się nie różnią.

## 3. Uzupełnienie: Qwen3.5-9B na 5060 Ti (nie jest modelem produktu)

- Dodane, bo to jedyny Qwen z drafterem, który Magnitude ładuje na 16 GB (katalog `qwen3.5-9b`: UD-Q4_K_XL, drafter DFlash Q8_0).
- Po 1 rundzie, nie ABBA. Upstream nie skończony (instancję zniszczono na polecenie).

| | Magnitude + DFlash | fork MTP n=4 |
|---|---|---|
| sweep T=1 | 68.2 t/s | **121.0** |
| tok/krok pl-proza / pl-tech / pl-kod / en-chat / en-tech / en-code | 1.00 / 1.41 / 1.25 / 2.00 / 2.45 / 3.06 | 1.71 / 2.43 / 2.56 / 2.61 / 2.46 / 2.91 |
| copy 64k | **175.8** (8.29 tok/krok) | 128.1 (4.53) |
| code-edit | **376.7** (13.4 tok/krok) | 239.0 (4.80) |
| prefill 64k | 2053 t/s | **2343** |
| VRAM | 8.9 GB | 8.3 GB |

Drafter DFlash dla 9B na polskim tekście jest prawie bezużyteczny (1.0–1.4 tok/krok). Na kopiowaniu dominuje.

## 4. Luki Magnitude (dowody)

- `source_element()` (`engine/executor/src/planning/weights.rs:2085`) obsługuje: F32, F16, BF16, Q8_0, Q3_K, Q4_K, Q5_K, Q6_K, IQ2_XS, IQ3_XXS, IQ3_S, IQ4_NL, IQ4_XS, Q4_0, Q5_0, Q5_1, MXFP4, NVFP4. **Brak IQ2_S, IQ2_XXS, Q4_1, Q2_K.**
  - Błąd na UD-Q3_K_XL: `LoadFailed(Unsupported(Representation { reason: "unsupported source encoding Iq2S" }))` (`logs/fail64k/qwen.mag.first.log`, 5060 Ti).
  - Każdy unsloth Qwen3.8-27B ≤ 16 GB ma IQ2_S (UD-Q3_K_XL, UD-IQ4_XS, UD-Q4_K_S) albo Q4_1 (Q4_0). Odczyt nagłówków przez HTTP range.
  - Na 16 GB nie ma więc 27B (katalog i tak oferuje tylko Q4/Q6/Q8 UD).
- Q3_K i IQ3_S są importowane do reprezentacji q6k (komentarz `weights.rs:2110-2119`), więc mniejsze kwanty nie oszczędzają VRAM.
- LFM Q4_K_M na 16 GB przy 64k: `allocation requires 165675008 bytes; 89577882 bytes available` (`logs/fail64k/lfm.mag.first.log`). Działa przy 32k. Nasz fork mieści 64k (15.4 GB).
- Brak offloadu do RAM (#194). Import wag wymaga RAM hosta: na 31 GB padło „MemoryPressure HostRam” przy kolejnym starcie 27B (`logs/qwen.mag.7.log`).
- Brak HIP (tylko CUDA sm_80+, Metal, Vulkan; `docs/compatibility.md`). KV domyślnie K8V4.
- API: `model` wymagane (400 bez niego). Brak `/tokenize`; jest `/api/v1/chat/templates/apply`.

## 5. Ocena dla PLAN-u

- Przewaga kerneli na NVIDIA istnieje i jest duża w dekodzie bez draftera: +30–40% nad Magnitude, który jest na poziomie upstreamu. Także w prefillu: +18–35%.
- Słabością naszego stosu są drafty o dużej głębokości:
  - MTP n=4 ma sufit 5 tok/krok, a DFlash2 w llama.cpp jest drogi (64 ms/krok vs 47.6 u Magnitude).
  - Kandydaci: tańsza ścieżka DFlash (verify 16 tokenów), adaptacyjna głębokość według klasy (15c pkt 3), spec-copy/n-gram dla tur kopiujących (15c pkt 2).
- Na polskim tekście tuned MTP wygrywa z DFlash2 (pl-proza +47%).
- Raporty publiczne muszą zawsze rozdzielać obie klasy (potwierdza lekcję o benchmarkach na kopii).

## 6. Koszt

| pozycja | koszt |
|---|---|
| 3090 #1 (56262831, SSH nie działał, zniszczona po ~12 min) | ≈ $0.06 |
| 3090 56264196 ~3.0 h × $0.205 + ~60 GB × $6/TB | ≈ $0.62 + $0.36 |
| 5060 Ti 56262949 ~2.6 h × $0.188 (transfer $0) | ≈ $0.49 |
| **razem** | **≈ $1.5** `[SZACUNEK z cen/h]` (limit $2.30) |

Kredyt Vast 6.90 → 4.01. Spadek obejmuje też równoległe instancje innych agentów. Obie instancje zniszczone (`show instances`: 0 naszych).

## 7. Czego nie zrobiłem

- Druga runda Magnitude dla Qwena na 3090 (OOM RAM hosta przy restarcie).
- KLD wyjścia Magnitude (brak logitów w API).
- Harness Magnitude dla LFM (reasoning mimo thinking off).
- Upstream dla 9B.
- MTP n>4 i n-gram w forku na klasie copy.

## Do bazy wiedzy

- `eksperymenty/` (nowy): **X1 Magnitude vs fork vs upstream (3090, 5060 Ti)** (`2026-10-16-magnitude-vs-fork.md`):
  - LFM sweep 3090: 291.6 / 209.0 / 216.6; 5060 Ti 32k: 205.1 / 157.8 / 153.4 (§2 tabela);
  - Qwen27B 3090: sweep 65.7 = 65.7 (mag 1 runda), copy 80.2 vs 69.3, code 156.1 vs 105.2, fork+DFlash2 49.0 / 94.0 / 121.1;
  - kill criterion nietrafiony. Źródło: `results/magnitude-vs-*-20261016/x/xbench.jsonl`, `analyze.py`.
- `repo/magnitude.md` (aktualizacja):
  - brak IQ2_S/IQ2_XXS/Q4_1/Q2_K (`weights.rs:2085`), więc brak 27B na 16 GB;
  - Q3_K → q6k;
  - LFM 64k OOM na 16 GB;
  - autotune 60 s → gotowość 51–62 s, potem 5–10 s;
  - DFlash2 47.6 ms/krok vs llama.cpp 64.0 (3090, `xbench.jsonl`);
  - harness: decode 121 t/s vs ich własne `timings` 80 (§2).
- `lekcje/` (nowa) **„Drafter głęboki vs MTP: kopia vs polski”**: Magnitude DFlash2 7.3–7.8 tok/krok na copy/code, a 1.32 na pl-proza; MTP n=4 ma sufit 5 (§2, §3).
- `lekcje/lekcja-limit-cpu-kontenera` (aktualizacja): hosty z cgroup v1 nie mają `cpu.max`. Kwota jest w `cpu/cpu.cfs_quota_us` (5060 Ti: 768000/100000 = 7.68 przy `nproc` 64). Bootstrap ma teraz fallback (`inst/bootstrap.sh:55-58`).
- `lekcje/` (nowa) **„pkill -f przez ssh zabija własną sesję”**: wzorzec pasuje do linii `bash -c` z tym samym tekstem; trzeba kotwiczyć `^bash ./main.sh` (sesja 16d).
- `metody/zgodnosc-bitowa-md5.md` (aktualizacja): KLD Nemotrona `TOPK_MOE_NP2` 0.00214 vs szum ub256 0.00225, NP2=0 bit w bit (`14-nemotron-3090.md` §13; `results/magnitude-vs-3090-20261016/kld/summary.txt`).
- `ludzie-firmy/magnitude` / research 01: „strojenie u konsumenta” Magnitude nie daje przewagi kerneli na NVIDIA. Wygrywa drafterem na kopii.
