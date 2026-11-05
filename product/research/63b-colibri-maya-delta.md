# 63b. colibri v2.1.0, Project Maya v1.1.27–1.1.54, Delta Inference Engine, RTP-LLM, MNN-LLM: agent i długi kontekst

Data: 2026-11-05. Autor: podagent R63bLocalAgents. Praca wyłącznie na CPU: bez GPU, bez serwera :8080, bez pobierania wag.

Klony (tylko kod):
- `~/src/research63/colibri`: `0a5504a1`, merge #2530, 2026-10-31; tag v2.1.0 = `704a3f68`;
- `~/src/research63/delta`: `307437f`, 2026-11-04;
- `~/qwen-opt/research-src/project-maya`: przestawiony na v1.1.54 `c167004`.

Release notes jako JSON są w `~/src/research63/rel_*.json`. Wycinki: `colibri_rel_top.txt`, `maya_rel_delta.txt`, `mnn_rel.txt`, `rtp_commits.txt`, `mnn_llm.cpp`.

Analiza naszych logów: `/tmp/r63b_logscan.py` i `/tmp/r63b_timeline.py`, czytają tylko pliki `~/qwen-opt/logs/server-*.log`.

Wcześniej badane (rejestr [[ZRODLA]]):
- Maya do v1.1.26 `f26d8ba` (R21g, R32a, R39a, R57f, R60d). Tu opisuję wyłącznie deltę v1.1.27 → v1.1.54.
- Rodzina Strata (R57b).
- colibri, Delta, RTP-LLM i MNN-LLM 3.6.x są badane pierwszy raz. MNN pojawił się tylko na liście silników R03.

Każdy wątek ma własną sekcję z werdyktem i konkretną akcją. Ranking zbiorczy jest na końcu, w „Co z tego dla nas”.

## TL;DR

1. **Najważniejsze odkrycie nie pochodzi od konkurencji, tylko z naszych logów.** Cudze poprawki agentowe (colibri #2517, Maya #607/#639) kazały mi sprawdzić, ile nasz serwer traci na ponownym czytaniu długich promptów.
   - Wynik: z 4753 s prefillu zapisanych w `~/qwen-opt/logs/server-*.log` aż **3536 s (74%) to 38 żądań**, w których prompt ≥20k tokenów był czytany od zera albo od ≤8k. Najgorsze tury trwały 150–200 s.
   - Przyczyna: wpis `--cache-ram` Qwena przy 75–120k tokenów ma **7–14 GB**, a limit to **16 384 MiB**. Mieści się więc jeden długi wątek. Drugi wątek (subagent, druga sesja omp) go wyrzuca: „making room … removing oldest entry (size = 9554 MiB)”, 22 z 38 przypadków.
   - To jest dokładnie problem, który colibri i Maya łatały u siebie. U nas jest większy, bo nasz stan GDN plus 32 checkpointy na wpis jest ciężki.
2. **colibri „256k w szybkości 64k” nie jest techniką dekodu długiego kontekstu.** To poprawka planera pamięci w ich silniku MoE: planer wyceniał cały kontekst jako bufor jednego forwardu, a KV było w f32. Po przejściu na f16 karcie zostaje 7 GB na eksperty zamiast 0.65 GB. Dla gęstego 27B z KV q4_0 nic nie wynika.
3. **colibri „tura agenta 86 → 4.9 s” to dwie poprawki ich serwera:**
   - snapshot był przesunięty o jeden token;
   - funkcja „park” przy krótkim zapytaniu bocznym.

   llama-server ma już odpowiednik pierwszej (checkpointy n−4−ub i n−4, PR #20288) i zgrubny odpowiednik drugiej (`prompt_save` przy LRU). Brakuje nam pojemności i chudych wpisów, nie mechanizmu.
4. **Maya v1.1.39 „19× TTFT”** to osobny, mały wpis „wspólny początek” (system prompt + narzędzia) w RAM, niezależny od rozmów. Nasz `CACHE_SHARE_MIN` robi to samo, tylko kopiując **cały** wpis długiej sesji: do 14 GB zamiast ~0.4 GB. To bezpośredni port na topkę.

   Dobre i tanie pomysły z innych wydań Mai:
   - punkty przywracania (#639);
   - stała kolejność narzędzi (#625);
   - pętla-strażnik, który nie psuje prefiksu (#704);
   - **`tools/agent_bench.py`** (#406): benchmark agentowy, stdlib, dowolny serwer OpenAI. Możemy go użyć bez zmian.
5. **Maya „SSD +22%”** (#570) to strumieniowanie eksperta z NVMe na GPU kawałkami. Nie dotyczy gęstego 27B ani LFM w VRAM. Dla aplikacji Enigma ma sens dopiero przy MoE większym niż RAM.
6. **Delta, RTP-LLM i MNN:** żadnego przełomu dla XTX.
   - Delta: `REWIND_GAP` dla przerwanej tury oraz ustawienia Windows dające +12% (do aplikacji Enigma).
   - RTP-LLM: polityka „stan liniowy tylko na ogonie promptu” (`reuse_cache_tail_blocks`) potwierdza kierunek chudych checkpointów; CRC32C cache'u na dysku schowane w oknie kopii.
   - MNN 3.6.2: DFlash 2.09× na Metal i draft dzielący `lm_head`.
7. **Prawdziwego przełomu w dekodzie przy batch 1 tu nie ma.** Największy realny zysk to **latencja tur agenta na długich sesjach: rząd −90…−97% TTFT dla przeplatanych wątków ≥75k**, przy zmianie konfiguracji i ~1–2 dniach kodu.

## 0. Nasz stan (punkt odniesienia)

- Rekordy ([[REKORDY]]):
  - start nowej sesji po obcym zapytaniu: 1612 ms przy 53k z `CACHE_SHARE_MIN=1024` (`16f-xtx-szybkie.md:168-169`);
  - tura S2-turn2: 197 ms przy `CKPT_VRAM=2` (`38-checkpointy-vram.md:16`);
  - wznowienie 53k z SSD: 2.51 s (`16f:199`);
  - prefill ~930–1015 t/s przy 5–30k (logi z 2026-11-05).
- Konfiguracja produkcyjna:
  - `run-llm.sh:109`: `-np 1 --cache-ram 16384`, KV q4_0, ctx 204800;
  - `run-topka.sh`: MTP n=4, lookup W16, `CACHE_SHARE_MIN=1024`, `CKPT_VRAM=2`.
- Rozmiar stanu Qwen3.8-27B (metadane GGUF: `qwen35.block_count 65`, `ssm.state_size 128`, `ssm.time_step_rank 48`, `ssm.inner_size 6144`, `head_count_kv 4`, `key_length 256`, `full_attention_interval 4`):
  - stan GDN: 48 warstw × 48 głów × 128 × 128 × 4 B ≈ **151 MB**, plus konwolucja ~6 MB, razem ≈ 157 MB (zgodne z 24i);
  - KV: 16 warstw × 2 × 4 × 256 × 0.5625 B ≈ **18 KB/token** (q4_0).

  Wpis 118k powinien więc mieć ~2.2 GB KV plus maksymalnie 32 checkpointy × 157 MB ≈ 5 GB. **Zmierzone: 14.2 GB.** `[INFERENCE]` Nadwyżka to najpewniej stan draftu zapisywany przy każdym checkpoincie (`spec_ckpt`/`data_dft`, `server-context.cpp:2614`). Do potwierdzenia przez `LLAMA_SERVER_AP_TIMING=1`, który loguje „ckpt N / MiB” (`server-context.cpp:343`).

### 0.1 Analiza logów serwera (wszystkie `server-*.log`, 704 żądania; 560 to Qwen Uncensored)

| klasa żądania | żądań | tokenów prefillu | czas prefillu |
|---|---|---|---|
| slot wybrany przez LRU (LCP < 0.1) | 237 | 2 897 327 | 3644 s |
| LCP, f_keep ≥ 0.5 | 335 | 371 839 | 511 s |
| LCP, f_keep < 0.5 | 129 | 426 590 | 491 s |
| **w tym: prompt ≥20k przeczytany od ≤8k** | **38** | **2 788 708** | **3536 s** |

Przykład z 2026-11-05 (`server-2026-11-05_135730.log`, oś czasu z `/tmp/r63b_timeline.py`). Dwa wątki ~75k i ~90k przeplatają się, za każdym razem wraca „reused=4375” (wspólny system prompt), a resztę serwer czyta od nowa:

```
 8.22.047 LRU held= 52852 prompt= 74262 reused=  4375 proc= 69887 pp= 85.0s  (evict 4946 MiB)
10.53.890 LRU held= 75333 prompt= 76979 reused=  4375 proc= 72604 pp= 89.2s  (evict 3500 MiB)
```

W `server-2026-11-03_123725.log` takich tur 100–200 s jest 22, z wyrzuceniami wpisów 7–14 GB.

**Wniosek:** dziś przy pracy agentowej na topce większość czasu czekania to nie dekod i nie kernele, tylko pojemność i kształt prompt cache'u. Cudze projekty pokazują, jak to rozwiązać.

---

## 1. colibri v2.1.0 (JustVugg/colibri)

Źródła:
- [release v2.1.0](https://github.com/JustVugg/colibri/releases/tag/v2.1.0) (2026-10-31; 387 PR, 35 kontrybutorów);
- kod `0a5504a1`, [docs/qwen38.md](https://github.com/JustVugg/colibri/blob/v2.1.0/docs/qwen38.md), [docs/speculative.md](https://github.com/JustVugg/colibri/blob/v2.1.0/docs/speculative.md), [docs/api.md](https://github.com/JustVugg/colibri/blob/v2.1.0/docs/api.md).

**Co to jest.** Silnik w czystym C, „jeden plik na rodzinę modeli”. Backendy: CPU, Vulkan (dense chain `vk_chain.c` i expert tier `vk_tier.c`), CUDA (`cuda_chain`, `cu_tier`) oraz Metal. Cel: duże MoE na zwykłym PC, z ekspertami w VRAM, RAM i na NVMe. Od v2.1.0 czyta GGUF natywnie (`coli import`).
- Sprzęt testowy autora: RTX PRO 4000 Blackwell SFF (24 GB, 70 W) + i5-13500 + 62 GB RAM.
- Qwen3.8-27B jest obsługiwany (silnik `qwen36`), ale bez liczb na GPU. README podaje tylko 3.45 t/s int4 na CPU ([README](https://github.com/JustVugg/colibri/blob/v2.1.0/README.md)).
- Na XTX jedyny pomiar społeczności to 0.77 t/s z warstwą ekspertów HIP (DeepSeek z dysku, `docs/benchmarks.md:170`). Na RX 9070 XT Vulkan był 19–24% szybszy od ich ścieżki HIP (`docs/benchmarks.md:237`).

**Jak pracuje autor.** Każdy commit ma pomiar przed → po na tym samym PC (ABBA „alternated twice”) i kontrolę bitową. Przykłady:
- „a verify's rows keep a decode step's bits”, sprawdzane `tests/test_vk_chain.c` na Lavapipe, RADV i RTX;
- mikro-benche pojedynczych dispatchy, np. „a dispatch costs 1.4 µs, RMSNorm 2048 5.5 µs”, `COLI_VK_CHAIN_BENCH=small`.

Dużo commitów nosi „Co-Authored-By: Claude Opus”, więc pracuje agentowo, podobnie jak my. Ich nawyk wart skopiowania: **przy każdym chybieniu cache'u log mówi, w którym tokenie i na jakim tekście prompt rozjechał się ze stanem** (`COLI_PREFIX_LOG`, opis niżej).

### 1.1 „256k w szybkości 64k” (#2517, commit `d4f61222`)

- **Twierdzenie:** Qwen3.8-Flash-Next IQ2_XS przy `--ctx 262144`: prompt 15.6 → 149 t/s, decode 9.6 → 45.7 t/s ([docs/qwen38.md, „A long context”](https://github.com/JustVugg/colibri/blob/v2.1.0/docs/qwen38.md)).
- **Mechanizm (kod):** dwie zmiany, żadna nie dotyczy atencji.
  1. Planer RAM (`family_registry.py`, `_qwen38_prompt_rows`) wyceniał cały kontekst jako bufory wierszy jednego forwardu: 38 GB przy 262k. Prompt jest jednak czytany w segmentach 8192/2048. Po zmianie planer wycenia jeden segment, a cache ekspertów w RAM rośnie z 10 do 490 slotów na warstwę.
  2. KV z f32 na f16 (`Q38_KV`): rezerwa łańcucha CUDA spada z 19.23 do 12.86 GiB, a budżet ekspertów na karcie rośnie z 0.65 do 7.03 GB. Jakość: 2.5566 vs 2.5555 nat/token na 1000 tokenach teacher-forced.
- **Wiarygodność:** pomiary wewnętrzne, prompt 452 tokeny + 128 wyjścia. To **nie** jest dekod przy 256k zapełnionego kontekstu, tylko dekod przy *zaalokowanym* oknie 256k. „64k” znaczy tu „jak przy alokacji 64k”. Hasło w releasie jest mylące.
- **Werdykt: nie dotyczy topki ani gęstego 27B.** Nasze KV to q4_0, a alokacja 262k na 24 GB jest już policzona: 16 warstw z pełną atencją × 18 KB/token ≈ 4.7 GB przy 262k.
- **Akcja dla nas:** jedna lekcja do aplikacji Enigma (planer pamięci): **nie wyceniać bufora prefillu jako `ctx` wierszy, tylko jako `n_ubatch`/segment.** Sprawdzić `app/engine` (MemBar/plan) przy MoE z offloadem ekspertów (`--n-cpu-moe`). Jeśli planer rezerwuje bufor obliczeń proporcjonalny do ctx, to zabiera miejsce ekspertom. Koszt: 1 h przeglądu kodu planera.

### 1.2 „Tura agenta 86 s → 4.9 s” (#2517/#2521, commit `d175038c`)

- **Twierdzenie:** Hermes Agent, prompt 14 785 tokenów, Qwen3.8-Flash-Next na łańcuchu CUDA. Druga tura 86 s → 4.9 s (14 783 tokenów z reużytku, 27 przeczytanych); na CPU Qwen3.6-35B 51.6 → 3.3 s ([release](https://github.com/JustVugg/colibri/releases/tag/v2.1.0), [docs/qwen38.md „An agent's turns”](https://github.com/JustVugg/colibri/blob/v2.1.0/docs/qwen38.md)).
- **Mechanizm, krok po kroku (z diffu `c/qwen38.c` +178 linii):**
  1. *Snapshot o token za daleko.* Hermes odsyła odpowiedź bez rozumowania. Model napisał `<think>\n`, a szablon renderuje `<think>\n\n</think>`. Snapshot końca promptu był brany *po* `<think>`, więc wypadał o 1 token za daleko (14 809 z 14 810) i każda tura czytała wszystko od nowa. Poprawka: `q38_serve_prefill_at` czyta prompt w dwóch odcinkach i bierze snapshot tuż za ostatnim `<|im_start|>assistant\n` (`q38_answer_start` szuka sekwencji w ostatnich ≤8 tokenach).
  2. *Park.* Krótkie zapytanie boczne (tytuł rozmowy, 133 tokeny) zajmowało jedyny stan. Teraz rozmowa (≥ `COLI_PARK_MIN` = 1024 tokeny) jest „parkowana”: zapisywana jest kopia stanu rekurencyjnego oraz **tylko tych wierszy K/V i indeksu, które krótkie zapytanie może nadpisać**, czyli `np + min(max_tok, 4096) + SPEC_ROWS`. Po zakończeniu zapytania wszystko wraca (`q38_unpark`, „however it ends”). Jeśli zapytanie wyszło poza zachowane wiersze, rozmowa jest czytana od nowa, a w logu pojawia się komunikat.
  3. *Diagnostyka.* `COLI_PREFIX_LOG=1` przy chybieniu wypisuje, ile tokenów zgadza się ze stanem żywym i ze snapshotem, oraz 16 tokenów tekstu po obu stronach miejsca rozjazdu.
  4. Wcześniej (#2113/#2114, 2026-10-16): tura kontynuuje ze **stanu żywego** (prompt + wygenerowana odpowiedź), a nie ze snapshotu końca promptu (27.2 → 2.6 s). `preserve_thinking` jest domyślnie włączane, gdy klient odsyła `reasoning_content` (`c/openai_server.py:3345`).
- **Wiarygodność:** jeden przebieg na turę. Liczba 86 s to ich własny błąd plus wolny prefill (~170 t/s przy MoE z RAM). Test regresji `tests/test_qwen38_prefix_serve.py` sprawdza, że reużycie daje to samo co zimny silnik.
- **Co z tego mamy już w llama-server/topce:**
  - (1) Checkpointy przy n−4−ub i n−4 (`server-context.cpp:4065-4084`, PR #20288) leżą *przed* promptem generacji. Pułapki „o 1 token” u nas nie ma.
  - (4) llama-server kontynuuje ze stanu żywego i domyślnie zachowuje rozumowanie (`server-context.cpp:1663`, `common/jinja/caps.cpp:22`). Szablon Qwen3.8 przy `preserve_thinking` undefined zostawia `<think>` (sprawdzone w GGUF).
  - (2) Zamiast parku llama-server robi `prompt_save` całego slotu do `--cache-ram` (`server-context.cpp:1799-1808`). To jest poprawne, ale kosztowne (D2H całego stanu i wszystkich checkpointów) i ograniczone limitem 16 GB (§0.1).
- **Werdykt: pomysł „park tylko tego, co nadpisze krótkie zapytanie” jest wartościowy, ale u nas ważniejsza jest pojemność cache'u (§0.1).** Port parku do llama.cpp przy `-np 1` wymagałby zapisu zakresu komórek KV i stanu GDN, bez API `seq_rm`/`seq_cp` dla hybrydy. To 2–3 dni pracy z ryzykiem. Ten sam efekt dają taniej E1+E2.
- **Akcja dla nas:**
  - (a) **`LLAMA_SERVER_PREFIX_LOG`** na wzór `COLI_PREFIX_LOG`: przy `n_past < 0.5·n_prompt` loguje LCP ze slotem i najlepszym wpisem cache'u oraz 16 tokenów tekstu po obu stronach. Koszt 0.5 dnia, zero ryzyka. Daje odpowiedź, który klient psuje prefiks.
  - (b) Aplikacja Enigma (`app/engine/src/ui/components/Chat.svelte:40`): historia jest wysyłana bez `reasoning_content`, więc każda tura czyta od nowa treść poprzedniej odpowiedzi. Odsyłanie `reasoning_content` daje dokładny reużytek stanu żywego. Zysk szacuję na 0.3–1 s na turę przy odpowiedziach 300–1000 tokenów `[INFERENCE]`. Koszt: 3 linie.

### 1.3 MTP Qwen3.6 do 120 t/s (#2250/#2251/#2256, #2376/#2407)

- **Twierdzenie:** Qwen3.6-35B-A3B int4-g64 na RTX PRO 4000: decode 99.7–104.5 → 115.8–120.1 t/s (CUDA), 83.2–83.8 → 99.9–109.3 (Vulkan) ([docs/speculative.md](https://github.com/JustVugg/colibri/blob/v2.1.0/docs/speculative.md)).
- **Mechanizm:**
  1. Najlepszy jest **1 draft**. 2 drafty: 94.6–108.6; 3 drafty: 88.6–95.2.
  2. Bramka `spec_draft.h`: `value(k) = E(k)/cost(k)`, gdzie `E(k) = 1 + a1 + a1a2 + …`, a `cost(k) = (T(k+1) + (k−1)d)/T(1)` z **mierzonego** T(n). Co 16 wyborów sonduje głębokość +1. Co 64 forwardy wymusza krok plain, żeby T(1) było aktualne.
  3. Głębokość per krok z prawdopodobieństwa draftu (`spec_gate_pick_p`, 10 przedziałów p), domyślnie włączona dla Qwen3.6.
  4. **Wiersze weryfikacji dzielą odczyt wag GEMV** (kernel szablonowy NR=4, CUDA i Vulkan). `lm_head` int8 przy 2/3/4 wierszach: 2.50/3.74/4.97 → 1.32/1.42/1.65 ms. Bity wiersza = bity kroku dekodu.
  5. Dynamiczny słownik draftu: 16k najczęstszych tokenów, plus te o liczności ≥ ¾ ostatniego, plus tokeny bieżącej rozmowy. Liczniki są połowione co 1024 tokeny i zapisywane na dysk przy wyjściu.
- **Wiarygodność:** dobra. Dwie rundy po 3 prompty, ABBA, tekst porównany z wersją bez głowicy, prompt po prompcie. Model to MoE A3B, więc koszt weryfikacji to głównie routowanie ekspertów. Inna fizyka niż u nas.
- **Werdykt: nic nowego dla topki.**
  - (2)/(3) to nasze 24q (głębokość adaptacyjna). Odrzuciliśmy ją, bo zmienna szerokość weryfikacji zmienia greedy md5. colibri ma to samo zastrzeżenie (dopuszcza zmianę bitów przy dynamicznym tier).
  - (4) mamy w MMVQ wielokolumnowym (HIP), a w Vulkanie upstreamu jest `mul_mat_vec_max_cols` (`ggml-vulkan.cpp:2936,5524`).
  - (5): nasz słownik to stałe 64k, a 24b pokazało, że OOV to 2–5% tokenów. Mniejszy dynamiczny słownik (16k + tokeny rozmowy) obniżyłby koszt głowicy, który jest rzędu ~2% kroku `[INFERENCE: 24b, +5.6% za 248k vs 64k]`. Sufit ≤ +1–1.5%.
- **Akcja:** brak dla XTX. Dla aplikacji na słabszych kartach (4060/3060, gdzie MTP n=3 bywa wolniejsze, jak w D w wejściu): rozważyć **pomiar T(n) przy starcie i dobór n_max** (bramka colibri bez zmiany głębokości per krok). W Enigma Optimize to już robimy kandydatami. Zostaje przegląd, czy kandydaci obejmują n=1/2.

### 1.4 KV f16 (#2326/#2327, #2440–#2442)

- **Twierdzenie:** GLM-5.3 przy 131 072 tokenach: 11.9 GB zamiast 23.9 GB ([release](https://github.com/JustVugg/colibri/releases/tag/v2.1.0)).
- **Mechanizm:** domyślny KV colibri był f32. Przejście na f16 połowi pamięć. Dodatkowo shadery atencji Vulkan mają bliźniaki KV16. Decode atencji jednej warstwy po 18k: 241 → 181 µs (`01777895`). „Decode attention by KV head”: 4 pozycje V w locie (`e71aa6f5`).
- **Werdykt: dogonili standard.** llama.cpp ma f16/q8_0/q4_0 od dawna, my używamy q4_0 (Qwen) i q8_0 (LFM). Nic do wzięcia.
- **Akcja:** brak. Lekcja dla aplikacji Enigma: przy kwantyzowanym KV na Vulkanie/CUDA trzymać się typów, dla których FA ma kernele. Wejście B (cheaptokens): q5_1 + FA spada po cichu na CPU.

### 1.5 Eksperty z NVMe dla modeli 1T (#2198/#2280, `docs/multidisk.md`)

- **Twierdzenie:**
  - Kimi K3 UD-IQ1_S (594 GB): 0.349 t/s;
  - Mistral-Large-4 233 GB: 1.34 t/s;
  - DeepSeek V4.1 IQ1_S 233 GB: 5.0–5.3 t/s.

  Odczyt ekspertów bez readahead daje Kimi +30%.
- **Werdykt: nie dotyczy** gęstego 27B ani LFM (całe w VRAM). Dla aplikacji Enigma to inna klasa produktu: liczby są użyteczne tylko jako „da się uruchomić”.
- **Akcja:** brak. Ewentualnie do mapy konkurencji: colibri i Maya pokrywają segment „model większy niż RAM”, którego nie obsługujemy.

---

## 2. Project Maya (mw00/project-maya), delta v1.1.27 → v1.1.54

Źródła: [releases](https://github.com/mw00/project-maya/releases), kod v1.1.54 `c167004`, 511 commitów od v1.1.26. Silnik ma teraz cztery modele: GLM-5.3-Flash, DeepSeek-V4.1-Flash, MiniMax-M3.1-Flash, Qwen3.8-Flash-Next „CYBER-FROST”. **Gęstego 27B nadal brak.**

Ocena każdego wydania (tylko punkty istotne dla nas, reszta to modele, UI, Windows i poprawki):

| wydanie (data) | co istotne | werdykt / akcja dla nas |
|---|---|---|
| [v1.1.27](https://github.com/mw00/project-maya/releases/tag/v1.1.27) (10-24) | DeepSeek: eksperty z GGUF kopiowane do RAM zamiast czytania z plików, gdy się mieszczą: +22–100% | nie dotyczy (gęsty model w VRAM) |
| [v1.1.28](https://github.com/mw00/project-maya/releases/tag/v1.1.28) (10-25) | DeepSeek 1-GPU: lepsze podawanie ekspertów (do ~2× na 3090); opcje AMD dla GLM | nie dotyczy |
| [v1.1.29](https://github.com/mw00/project-maya/releases/tag/v1.1.29) (10-26) | MiniMax-M3.1 (osobny silnik `maya-mm3`); KV INT8 domyślnie; `reasoning_effort: auto` | nie dotyczy |
| [v1.1.30](https://github.com/mw00/project-maya/releases/tag/v1.1.30) (10-27) | kwanty MiniMax Maya-XS/S; **loop guard** dla każdego modelu; kalibracja chunku prefillu per PC (1.4–1.75× na Gorgon Halo) | kalibracja chunku już jest w Enigma Optimize (ub); loop guard opisany przy v1.1.43 |
| [v1.1.31](https://github.com/mw00/project-maya/releases/tag/v1.1.31) (10-27) | DeepSeek „suffix draft” (#540/#543): weryfikacja tokenów, które w kontekście szły po powtórzonym tekście, do 1.6× na edycjach | **to nasz lookup W16** (16b, ×2.41 na mvs); potwierdzenie kierunku, nic nowego |
| [v1.1.32](https://github.com/mw00/project-maya/releases/tag/v1.1.32)/[v1.1.33](https://github.com/mw00/project-maya/releases/tag/v1.1.33) (10-27) | poprawki UI i setupu | nie dotyczy |
| [v1.1.34](https://github.com/mw00/project-maya/releases/tag/v1.1.34) (10-27) | `--parallel` dla DeepSeek/MiniMax: 2 rozmowy dają ~1.6× tok/s; Qwen-3.8-Flash-Next w setupie | u nas -np>1 to KILL (24c); nie wracamy |
| [v1.1.35](https://github.com/mw00/project-maya/releases/tag/v1.1.35) (10-28) | GLM: edycja ostatniej wiadomości po przełączeniu czatu nie czyta wszystkiego (~10× na 2K); MiniMax: krótkie pytanie nie wypycha długiej rozmowy z obrazem (2.9×) | **ten sam problem co §0.1** (obce krótkie żądanie wypycha długie); patrz E1–E3 |
| [v1.1.36](https://github.com/mw00/project-maya/releases/tag/v1.1.36) (10-28) | DeepSeek: okna weryfikacji 9–16 i 1–8 miały inne ścieżki zaokrągleń, więc tekst T=0 zależał od historii; ujednolicone (#608) | ta sama lekcja co nasze 24c/24q (szerokość weryfikacji a md5); nic nowego |
| [v1.1.37](https://github.com/mw00/project-maya/releases/tag/v1.1.37) (10-29) | **#639 punkty przywracania**: start ostatniej wiadomości usera, punkt przy ogonie, koniec system prompt + narzędzia; edycja końca czatu 20K: 18 s → 0.3 s. **#625 stała kolejność narzędzi** (15.7 → 0.3 s). #587 harmonogram „po kawałku” przy --parallel | punkty przywracania = nasze checkpointy na `is_user_start` i n−4; **stała kolejność narzędzi do proxy aplikacji Enigma (E6)** |
| [v1.1.38](https://github.com/mw00/project-maya/releases/tag/v1.1.38) (10-29) | CYBER-FROST: eksperty spoza RAM czytane O_DIRECT, +26% na PC z małym RAM | nie dotyczy |
| [**v1.1.39**](https://github.com/mw00/project-maya/releases/tag/v1.1.39) (10-29) | **#607 wspólny początek** (system + narzędzia) trzymany w RAM osobno od rozmów: nowa rozmowa 19× szybciej, 25× przy `--parallel 2`. **#570 GLM SSD stream fetch**: ekspert jedzie na GPU kawałkami w trakcie odczytu, +22% | #607: **port do topki (E3)**; #570: nie dotyczy gęstego 27B |
| [v1.1.40](https://github.com/mw00/project-maya/releases/tag/v1.1.40) (10-30) | #668: punkt przy ogonie promptu włączany tylko wtedy, gdy wg zmierzonego czasu/token kosztuje mniej niż ponowny odczyt; Mac eksperymentalnie | lekcja dla nas: n−4−ub i n−4 kosztują 2 checkpointy na prompt (~15 ms każdy przy `CKPT_VRAM=2`, 38), więc bez zmian |
| [v1.1.41](https://github.com/mw00/project-maya/releases/tag/v1.1.41) (10-30) | loop guard między turami (#640); **GLM: przerwany odczyt promptu zostawia ostatni checkpoint** (#573), snapshot przed promptem generacji (#572); `/models/load` | #573 sprawdzić u nas (E7) |
| [v1.1.42](https://github.com/mw00/project-maya/releases/tag/v1.1.42) (10-30) | obrazy wszędzie; DeepSeek: punkty przy ogonie w jednym odczycie (+16–24% na 20–30K) | nie dotyczy |
| [v1.1.43](https://github.com/mw00/project-maya/releases/tag/v1.1.43) (10-31) | **#704: loop guard przepisywał prefiks** długiej rozmowy, więc cache chybiał; po poprawce następna tura na 150K ~15× szybciej. Liczba równoległych odczytów z NVMe mierzona per dysk | zasada: **żadna warstwa pośrednia (proxy, strażnik, safe-tools) nie może zmieniać tekstu przed końcem prefiksu**. Sprawdzić nasze `LLAMA_SERVER_SAFE_TOOLS` (topka `098ce134d`) |
| [v1.1.44](https://github.com/mw00/project-maya/releases/tag/v1.1.44)–[v1.1.46](https://github.com/mw00/project-maya/releases/tag/v1.1.46) (10-31…11-01) | kwanty unsloth DeepSeek, poprawka IMA na 1 GPU, Halo +5% | nie dotyczy |
| [v1.1.47](https://github.com/mw00/project-maya/releases/tag/v1.1.47) (11-01) | DeepSeek Maya-XS v2: KLD 0.284 → 0.251, +20% szybciej | nie dotyczy |
| [v1.1.48](https://github.com/mw00/project-maya/releases/tag/v1.1.48) (11-01) | **#746: budżet myślenia zamyka rozumowanie tak, że stan zostaje prefiksem następnego promptu** (wcześniej 59 s przy 32K) | dotyczy aplikacji Enigma, jeśli dodamy budżet myślenia: zamknięcie `</think>` musi trafić do stanu tak samo, jak wyrenderuje je szablon |
| [v1.1.49](https://github.com/mw00/project-maya/releases/tag/v1.1.49) (11-02) | poprawki | nie dotyczy |
| [v1.1.50](https://github.com/mw00/project-maya/releases/tag/v1.1.50) (11-02) | API w stylu Ollama, przycisk Turbo (stratne: pomijanie ekspertów, greedy, bez myślenia), GLM Maya-XS 73 GB | Turbo jako UX ciekawe, ale stratne; nie kopiujemy |
| [v1.1.51](https://github.com/mw00/project-maya/releases/tag/v1.1.51) (11-03) | DeepSeek TP wypełnia GPU (+10% dekodu); Qwen: porzucony odczyt promptu nie psuje kolejnych żądań (#703) | nie dotyczy |
| [v1.1.52](https://github.com/mw00/project-maya/releases/tag/v1.1.52) (11-03) | GLM: FFN warstw DSA w CUDA graphs, +8–9% dekodu; `DS4_INDEX_TC` (WMMA na RDNA3) | CUDA graphs mamy; nic nowego |
| [v1.1.53](https://github.com/mw00/project-maya/releases/tag/v1.1.53) (11-04) | **#813 `MAYA_PROMPT_MEMO`: tokenizacja tury przyrostowo, te same id** (testy na szablonach GLM/DS/MiniMax/Qwen); **#406 `tools/agent_bench.py`** | MEMO = nasze `LLAMA_SERVER_TOK_CACHE` (24i, 61/61 identycznych); **agent_bench.py używamy (E0)** |
| [v1.1.54](https://github.com/mw00/project-maya/releases/tag/v1.1.54) (11-05) | DeepSeek prefill na Halo +178–250% (eksperci czytani tylko dla tokenów chunku); WMMA indeksera domyślnie na gfx11; „Fix, Qwen chats: follow-up czytał całą rozmowę” | ostatni punkt to ten sam błąd klasy co colibri #2517, u innego autora. Wzorzec: **silniki hybrydowe (GDN) zawsze najpierw psują reużytek przy rozmowach** |

### 2.1 Mechanizm #607 (kod `src/ds4/ds4_main.cpp`, commit `b2d4c30`)

- Gdy prompt czytany od tokenu 0 dochodzi do znacznika `shared` (koniec system promptu i narzędzi), stan jest kopiowany do osobnej struktury `Prefix{tokens, data}` przez `m.slot_save`.
- Limity: `MAYA_DS4_PREFIX_KEEP` = 2 wpisy, `PREFIX_GB` = 2 GB, `PREFIX_MIN` = 1024 tokeny; usuwany jest najdawniej użyty.
- Nowy prompt bierze najdłuższy pasujący `Prefix`, ale tylko wtedy, gdy pokrywa więcej niż punkty przywracania samego modelu (`prefix_find`/`prefix_take`).
- Rozmiar: u nich ~20 MB na 11.3K tokenów, bo KV DeepSeeka jest skompresowane. U nas to byłoby KV 0..p plus jeden stan GDN: przy 14k tokenów ≈ 14k × 18 KB + 157 MB ≈ **0.42 GB**.
- Pomiar Mai: 1× V100, Maya-XS, 11 307 tokenów odzyskanych, 19 przeczytanych, TTFT 19× krótszy.
- **Werdykt:** to jest dokładnie brakujący element obok naszego `CACHE_SHARE_MIN`. Ten dziś przywraca *kopię całego wpisu* długiej sesji (`server-task.cpp:1821-1845`): 2.3 GB przy 53k (1.1 s, 16f) i do 9–14 GB przy 100k+ `[INFERENCE: ~5–7 s przy 2.3 GB/1.1 s]`, i to tylko wtedy, gdy wpis jeszcze żyje w cache'u. Po wyrzuceniu (§0.1) nowa sesja czyta system prompt od zera.
- **Akcja:** E3.

### 2.2 Ogólny werdykt Maya

Dla prędkości dekodu i prefillu na gfx1100 przy gęstym 27B nadal **nic** (jak w R60d). Dla ścieżki agenta trzy rzeczy do wzięcia:
- wspólny początek (#607);
- stała kolejność narzędzi (#625);
- `agent_bench.py` (#406) jako benchmark.

Plus dwie zasady:
- nic nie przepisuje prefiksu (#704);
- przerwanie nie gubi stanu (#573, #746).

---

## 3. Delta Inference Engine (musicurgy/delta-inference-engine)

Źródła: [repo](https://github.com/musicurgy/delta-inference-engine), kod `307437f` (2026-11-04), release [0.9](https://github.com/musicurgy/delta-inference-engine/releases/tag/0.9), [0.91](https://github.com/musicurgy/delta-inference-engine/releases/tag/0.91), [0.92](https://github.com/musicurgy/delta-inference-engine/releases/tag/0.92) (10-26…27). Kod ma 50 commitów.

**Co to jest.** Port na Windows silnika [Xolotl](https://github.com/Indras-Mirror/Xolotl) (fork Straty) dla **DeepSeek-V4.1-Flash-1017** (552B, eksperty 2-bit) na jednej karcie NVIDIA ≥12 GB plus ≥128 GB RAM i NVMe. Instalator `.bat`, OpenAI i Anthropic API. Autor (musicurgy) pracuje z Claude (Co-Authored-By). To produkt-opakowanie, nie nowe kernele.

**Liczby (README, RTX 3090):**
- pisanie: 41 t/s przy 192 GB RAM, 33 t/s przy 128 GB;
- długi prompt 25–64k: 610 / 410 t/s;
- UD-IQ1_S przy 128 GB: 37.5 t/s.

Zgodność top-1 z API DeepSeeka: 91.4% (dokładne routowanie) i 90.2% z „route bias 0.28”. Route bias faworyzuje eksperty już siedzące na GPU i daje ~20% szybciej, ale jest **stratny** ([README „Quality”](https://github.com/musicurgy/delta-inference-engine/blob/main/README.md)).

**Agent i cache (z kodu):**
- **Cache 8 rozmów w RAM**, ~20 MB na 10k tokenów (skompresowane KV DeepSeeka). Przełączenie między rozmowami: 16–18 s → 1–3 s; sesja 9 tur z dwiema przeplatanymi rozmowami ~8k: 95 → 49 s.
- **`STRATA_SERVE_REWIND_GAP`** (domyślnie 16, commit `a25b8df`, z Xolotl `961d390`), `tools/v41/engine/ds41_generate.cpp:1549-1557,1786-1798`. Agent przerywa turę i wyrzuca częściową odpowiedź, więc nowy prompt jest o kilka tokenów krótszy od stanu żywego. Bez poprawki silnik czytał wszystko od nowa. Teraz stan cofa się o ≤16 pozycji, a ogon jest przeczytany ponownie: rozmowa 9566 tokenów 16.8 s → 0.48 s. Działa, bo u nich okno SWA ma zapas 16 pozycji (`RAW = SWA + 16`).
- „Follow-up 200–2000 tokenów zachowuje większość cache'u ekspertów na GPU” (0.6–0.9 s na turę).

**Werdykt:**
- Pułapkę przerwanej tury u nas łapie checkpoint n−4 poprzedniego promptu. Przerwana odpowiedź ma dłuższy stan niż nowy prompt, a LCP kończy się przed promptem generacji.
- Dla hybrydy GDN cofnięcie stanu żywego o N tokenów jest niemożliwe bez checkpointu. Robimy to już mechanizmem checkpointów, więc nic do portu.
- 8 rozmów w RAM działa u nich tylko dlatego, że stan DeepSeeka to ~2 KB/token. Nasz Qwen to 18 KB/token plus 157 MB na każdy checkpoint. Wniosek: **trzeba odchudzić checkpointy w cache'u (E2)**, inaczej nie zmieścimy wielu rozmów.

**Akcja (aplikacja Enigma, Windows):**
- „Windows settings for speed”: plan zasilania High performance + HAGS + Lock pages in memory dają razem +12% pisania (21.7 → 24.3 t/s), RAM na deklarowanej szybkości +3%.
- Dla nas plan zasilania i HAGS mają znaczenie przy offloadzie MoE na CPU i przy pętli hosta. `[INFERENCE]` przy pełnym VRAM zysk mniejszy.
- Do aplikacji: **ekran diagnostyki, który sprawdza te ustawienia i nazywa wyłączone** (jak `Start DeepSeek.bat`). Koszt 0.5–1 dnia, zysk do zmierzenia na Windows (E8).

---

## 4. Alibaba RTP-LLM (alibaba/rtp-llm)

Źródła: [repo](https://github.com/alibaba/rtp-llm). Ostatni release na GitHubie to v0.2.0 (2025-10-31), więc wydania nie odzwierciedlają stanu. Badałem commity: HEAD `26711bad2` / `f81f777a1` (2026-11-03/04), lista w `~/src/research63/rtp_commits.txt`, oraz PR-y [#1574](https://github.com/alibaba/rtp-llm/pull/1574), [#1460](https://github.com/alibaba/rtp-llm/pull/1460), [#1423](https://github.com/alibaba/rtp-llm/pull/1423).

**Co to jest.** Produkcyjny silnik serwujący Alibaby (Taobao/Qwen API): CUDA, ROCm (AITER, Triton 3.8, #1421), PPU, disaggregated prefill/decode, RDMA, wielopoziomowy KV cache (HBM, host, dysk, zdalny „KVCM”), DeepSeek V4/V4.1 z MegaKernel decode (#1371). Skala datacenter, nie konsumencka.

**Co ważne dla konsumenckiego GPU i hybrydy GDN:**
1. **#1574 „reusable tail retention”.** Dla grup liniowej atencji (GDN i Next/Kimi linear) stan jest materializowany tylko dla **ostatnich N bloków** promptu (`reuse_cache_tail_blocks`), a wcześniejsze są zwalniane. Zastąpiło to stary `LINEAR_STEP`, czyli checkpoint co k bloków. Osobne pule bloków dla Linear i SWA (`linear_pool_blocks`, `swa_pool_blocks`).
   - **To niezależne potwierdzenie E2:** w produkcji Alibaba przy hybrydach nie trzyma checkpointów stanu liniowego wzdłuż całego promptu, tylko przy ogonie (plus prefiksy z puli).
2. **#1460 chunked prefill dla hybrydy:** kontynuacja stanu konwolucji i SSM GatedDeltaNet na granicach chunków, MTP w chunkach. „Exact token equivalence is not guaranteed across existing attention kernel paths”, czyli ten sam problem bitowy co u nas (16f E1: LFM reaguje na podział ubatcha).
3. **#1476/#1527: CRC32C dla host i disk KV cache, schowane w oknie kopii KV.** Wzorzec do naszego projektu cache'u sesji na SSD (16f E5, wariant B): suma kontrolna liczona w trakcie D2H, zero dodatkowej latencji.

**Werdykt:** silnik nie dla nas (brak gfx1100, skala klastra). Wzorce cache'u są przydatne.

**Akcja:**
- (a) E2 projektować jak #1574: chude checkpointy, „ogon + punkty wiadomości”;
- (b) przy cache'u sesji na SSD dodać CRC32C liczone w czasie zapisu.

---

## 5. Alibaba MNN-LLM (alibaba/MNN 3.6.2)

Źródła: [release 3.6.2](https://github.com/alibaba/MNN/releases/tag/3.6.2) (2026-10-29, tag `498882a27`), kod `transformers/llm/engine/src/llm.cpp` (pobrany przez API, `~/src/research63/mnn_llm.cpp`).

**Co to jest.** Silnik on-device (telefony, iPad, RISC-V; backendy CPU, Metal, OpenCL, Vulkan, CUDA, Hexagon/QNN, RKNN).

**Liczby:** Qwen3.5-2B na iPad Pro M5 (Metal): prefill 3542.9 t/s; **DFlash** decode 111.9 → 234.0 t/s (2.09×).

**Mechanizmy:**
- DFlash: projekcja cech, konkatenacja i argmax na urządzeniu; przyrostowy KV draftu; **draft dzieli `lm_head` z modelem docelowym** (mniej pamięci i dysku; stare drafty trzeba przeeksportować).
- Gated delta rule fused + chunked prefill na Metal i Hexagon.
- Grupowanie tokenów po ekspertach w MoE (CPU, Metal, OpenCL, CUDA, Vulkan).
- Vulkan coopmat dla INT4.
- `setPrefixCacheFile`: prefiks KV zapisywany do pliku na dysku (wymaga `kvcache_mmap`, `llm.cpp:1455-1475`).
- Opcjonalna „token compression”: wybór zdań pod budżet tokenów, stratne, domyślnie wyłączone.

**Werdykt dla topki:** nic.
- DFlash na 27B już badaliśmy (57e, „splash-dflash”). Nasz MTP + lookup ma 114–118 t/s.
- Wspólny `lm_head` mamy w sensie głowicy MTP Qwena (wbudowana).

**Dla aplikacji Enigma:** MNN to inny segment (mobile/NPU). Jedyne, co da się przenieść, to **prefiks KV jako plik** (odpowiednik naszego slot save/restore, 16f E5) i potwierdzenie, że plikowy cache prefiksu jest standardem w silnikach on-device.

**Akcja:** brak. Wrócić przy Androidzie lub iPadzie w produkcie.

---

## 6. Co z tego dla nas (ranking: oczekiwany zysk / wysiłek)

Format: baseline → teraz (oczekiwane) → przyrost. Wszystkie eksperymenty GPU idą przez kolejkę (`flock /tmp/gpu.lock`), na świeżym serwerze testowym na innym porcie (nie :8080), z bramką greedy md5 `c4708318`/`6f14e814`/`894e56e4`.

| # | eksperyment | baseline → oczekiwane | przyrost | wysiłek | ryzyko |
|---|---|---|---|---|---|
| **E0** | **Benchmark agentowy**: `tools/agent_bench.py` z Mai (stdlib, OpenAI API, seed, „cold bursts”, „checks”) + nasze `replay.py interf` rozszerzone o 2 przeplatane sesje ~75–120k | dziś nie mierzymy przeplatanych długich wątków | narzędzie do E1–E3 | 0.5 dnia | zero |
| **E1** | `--cache-ram 16384 → 40960` (RAM 62 GB, 58 GB dostępne; model w VRAM) w `run-llm.sh:109` | tura po przełączeniu wątku 75–120k: **85–200 s** (logi §0.1) → ~4–8 s (przywrócenie wpisu 9–14 GB z RAM `[INFERENCE: 2.3 GB/1.1 s z 16f]`) | **−90…−97% TTFT** takich tur; w logach ~3.5 tys. s z 4.75 tys. s prefillu | 1 linia + pomiar | presja RAM przy przełączaniu modeli (LFM) i page cache; sprawdzić `free` w szczycie |
| **E2** | **Chude checkpointy w cache'u**: przy `prompt_save`/`alloc` (`server-task.cpp:1722-1804`) kopiować tylko checkpointy na początku 1. i ostatnich 2 wiadomości usera oraz n−4−ub i n−4 (jak Maya #639, RTP #1574); najpierw zmierzyć udział `data_dft` (`LLAMA_SERVER_AP_TIMING=1`) | wpis 118k: 14.2 GB → ~3–4 GB `[INFERENCE]`; w 16 GB mieszczą się 3–4 długie wątki zamiast 1; save/restore ~3× szybsze | razem z E1: wiele wątków bez wyrzucania; E1 bez E2 zjada RAM | 1 dzień | md5 bez zmian z konstrukcji (restore bierze najnowszy checkpoint ≤ LCP); przy edycji starej wiadomości dłuższy prefill (poprawny) |
| **E3** | **Wspólny początek (Maya #607)**: przy prefillu od 0, gdy `is_user_start` pierwszej wiadomości usera i pos ≥1024, zapisać mały wpis (KV 0..p + 1 stan GDN + draft) jako osobną pozycję cache'u (2 wpisy, LRU); `CACHE_SHARE_MIN` wybiera go zamiast kopii całego wpisu | nowa sesja po obcej: 1612 ms przy 53k (16f); przy 100k+ ~5–7 s `[INFERENCE]`; po wyrzuceniu: pełny prefill system promptu (4.4k → 4.4 s w logu 11-05) → **~0.3–0.5 s** | −70…−95% startu sesji (subagenci omp, nowe czaty aplikacji) | 1–1.5 dnia | ~0.2–0.4 s D2H przy pierwszym odczycie nowego system promptu (jednorazowo) |
| E4 | `LLAMA_SERVER_PREFIX_LOG` (jak `COLI_PREFIX_LOG`): przy chybieniu loguje LCP ze slotem i z najlepszym wpisem oraz 16 tokenów tekstu po obu stronach | dziś wiemy „ile”, nie „dlaczego” | diagnostyka każdego przyszłego chybienia | 0.5 dnia | zero |
| E5 | Aplikacja Enigma `Chat.svelte:40`: odsyłać `reasoning_content` w historii | tura czyta ponownie treść poprzedniej odpowiedzi → 0 | ~0.3–1 s na turę `[INFERENCE]` | 0.5 h | kontekst rośnie o rozumowanie (szablon Qwena i tak je zachowuje) |
| E6 | Proxy aplikacji Enigma: **stała kolejność narzędzi** (Maya #625: zbiór nazw → pierwsza widziana kolejność) oraz zasada „proxy nie zmienia prefiksu” (#704); sprawdzić `LLAMA_SERVER_SAFE_TOOLS` | przetasowane narzędzia MCP: pełny prefill (Maya 15.7 s → 0.3 s) | przypadki brzegowe → 0 | 0.5 dnia | zero |
| E7 | Przerwany odczyt promptu (Maya #573): czy llama-server po `cancel` w trakcie prefillu zachowuje przetworzone tokeny i stan do ponowienia; test `replay.py` z przerwaniem w 50% | nieznane | jeśli gubi: do 50% prefillu na ponowienie | 0.5 dnia testu | zero |
| E8 | Aplikacja Enigma na Windows: diagnostyka planu zasilania, HAGS i large pages (Delta: +12% przy offloadzie) | – | 0…+12% przy MoE z CPU `[INFERENCE]` | 0.5–1 dzień | zero |
| E9 | Planer pamięci aplikacji (lekcja colibri 1.1): bufor obliczeń wyceniany na ubatch, nie na ctx | – | więcej warstw lub ekspertów w VRAM na małych kartach, jeśli jest błąd | 1 h przeglądu | zero |
| – | MTP: bramka głębokości, dynamiczny słownik 16k (colibri 1.3) | – | ≤ +1–1.5%, md5 się zmienia | – | odrzucone (24q, 24b) |
| – | park colibri (KV tylko dla nadpisanych wierszy) | E1+E2 dają to samo taniej | – | 2–3 dni | – |

**Kolejność:** E0 → E1 (zmiana konfiguracji) → E2 → E3; E4, E5, E6 równolegle (tanie).

**Kryterium sukcesu:** w agent_bench z 2 przeplatanymi wątkami ≥75k mediana TTFT tury ≤10 s (dziś 85–90 s), p95 ≤20 s; greedy md5 bez zmian; RSS serwera ≤45 GB.

## 7. Jak myślą autorzy (wnioski metodyczne)

- **colibri:** każdy problem agentowy zaczynają od pytania, *w którym tokenie i na jakim tekście* prompt rozjechał się ze stanem (`COLI_PREFIX_LOG`). Dopiero potem patrzą na czas. Off-by-one przy `<think>` znaleźli tylko dzięki temu logowi. My mierzyliśmy „ile tokenów przeliczono” (16f), ale nie „gdzie i dlaczego”.
- **Maya:** pętla społeczności przyniosła 4 niezależne zgłoszenia „cała rozmowa czytana od nowa”: #704, #746, #573, v1.1.54 Qwen. Każde miało inną przyczynę (strażnik, budżet myślenia, anulowanie, szablon). Lekcja: **każda warstwa nad silnikiem jest potencjalnym zabójcą prefiksu**, więc potrzebny jest test regresji na poziomie prefiksu („następny prompt zaczyna się od poprzedniego + odpowiedzi”, jak colibri `tests/test_chat_history_reuse.py`).
- **Delta:** produkt to 80% instalatora i diagnostyki (PASS/FAIL, zip debugowy bez promptów i z zanonimizowaną nazwą użytkownika). Kernel się nie zmienia. To wzorzec dla UX aplikacji Enigma.
- **RTP-LLM:** pamięć dla hybryd projektują jako „pule per typ warstwy + retencja ogona”, a nie „kopia całego stanu”. To kierunek, w którym powinien pójść nasz cache.

## 8. Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| `eksperymenty/` | 2026-11-05 audyt logów prompt cache | 3536 s z 4753 s prefillu (74%) to 38 długich (≥20k) ponownych odczytów; wpisy Qwena 7–14 GB przy limicie 16 GB (`/tmp/r63b_logscan.py`) |
| `lekcje/` | colibri „256k w szybkości 64k” to planer pamięci + KV f16, nie technika atencji | – |
| `lekcje/` | park / wspólny początek / punkty przywracania: trzy formy tego samego (mały stan na granicach wiadomości) | Maya #607/#639, colibri #2517, RTP #1574 |
| `repo/` | colibri, Delta, RTP-LLM, MNN: nowe karty repo | sekcje 1, 3, 4, 5 |
| `repo/project-maya` | aktualizacja v1.1.27–1.1.54 | tabela z §2 |

## 9. Źródła (wersje do [[ZRODLA]])

- colibri: [JustVugg/colibri](https://github.com/JustVugg/colibri), release [v2.1.0](https://github.com/JustVugg/colibri/releases/tag/v2.1.0) (2026-10-31, tag `704a3f68`), kod `0a5504a1`; commity `d175038c`, `d4f61222`, `95f7fb76`, `b1523f51`, `fda8c025`, `c4f35b2b`/`9289286a`, `78add8e9`; docs `qwen38.md`, `speculative.md`, `api.md`, `benchmarks.md`.
- Project Maya: [mw00/project-maya](https://github.com/mw00/project-maya/releases), v1.1.27 `f027308` … v1.1.54 `c167004` (2026-10-24…11-05); commity `b2d4c30` (#607), `22db5cc` (#625), `50a3313` (#639), `fb0c351` (#704), `73bd0fe`/`50d7efd` (#573/#572), `bd84e18` (#746), `e64dbd3` (#813); `tools/agent_bench.py`, `serve/frontend.py:548`.
- Delta Inference Engine: [musicurgy/delta-inference-engine](https://github.com/musicurgy/delta-inference-engine), kod `307437f` (2026-11-04), release 0.9/0.91/0.92 (2026-10-26…27); commit `a25b8df` (`REWIND_GAP`); upstream [Xolotl](https://github.com/Indras-Mirror/Xolotl) → [Strata](https://github.com/Niko1221/Strata).
- RTP-LLM: [alibaba/rtp-llm](https://github.com/alibaba/rtp-llm), HEAD `26711bad2`/`f81f777a1` (2026-11-03/04); PR [#1574](https://github.com/alibaba/rtp-llm/pull/1574), [#1460](https://github.com/alibaba/rtp-llm/pull/1460), [#1423](https://github.com/alibaba/rtp-llm/pull/1423), #1476/#1527 (CRC32C).
- MNN: [alibaba/MNN 3.6.2](https://github.com/alibaba/MNN/releases/tag/3.6.2) (2026-10-29, tag `498882a27`); `transformers/llm/engine/src/llm.cpp` (`setPrefixCacheFile`).
- Nasze: `~/wt/topka` `098ce134d` (`tools/server/server-context.cpp:1754-1820,3944-4141`; `server-task.cpp:1722-1845`); `~/KERNEL/qwen-opt/run-llm.sh:109`; logi `~/qwen-opt/logs/server-*.log` (do 2026-11-05 13:57).
