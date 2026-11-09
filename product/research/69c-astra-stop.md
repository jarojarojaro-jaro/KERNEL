# 69c — Astra-Stop: „łatka 20 KB na jedną macierz i Qwen3.8-27B myśli o 1/3 krócej”

Data: 2026-11-09. Research tylko na CPU (GPU nietknięte, bez buildów). Pobrane wyłącznie pliki łatki z HF (`u.npy` 20 608 B,
`edit.json`, `apply.py`, `README.md`) do `~/src/research69/astra/` oraz `git clone --depth 1` repo replikacji
(`notwitcheer/llm-bench-rig` @ `f732402`) do `~/src/research69/llm-bench-rig/`. **Żadnych wag modelu.** Pomiary
strukturalne zrobiłem na GGUF-ach, które już mamy na dysku (gguf-py + kwantyzator ggml z wdrożonej `~/llama-topka`
przez ctypes, `nice 19`, 1 wątek). Skrypty i wyniki: [`69c-skrypty/`](69c-skrypty/).

**Klasyfikacja: to jest zmiana zachowania (jakości) modelu, NIE bezstratna optymalizacja szybkości.** Edycja zmienia
rozkład wyjściowy, a więc i tokeny. Decyzja o wdrożeniu należy do użytkownika (§7).

## TL;DR

- **Co to jest (NEW):** jedna macierz `layers.63.mlp.down_proj` (ostatnia warstwa trunku), wzór
  `W' = W + u·(uᵀW)` (rank-1, `alpha = −1` w `W − α·u(uᵀW)`), `u` = 5120 liczb float32. Kierunek `u` to
  **odczyt tokena `</think>` przez głowicę LM**: na naszym GGUF cos(u, wiersz `output.weight[</think>]`) = 0.9947,
  a z uwzględnieniem wzmocnienia `output_norm` **0.9998** (pomiar własny). Edycja podwaja więc „głos” ostatniego MLP
  za/przeciw `</think>`; to w praktyce dynamiczny, zależny od kontekstu logit-bias na jeden token, wpisany w wagi.
- **Wyniki dostawcy (NEW):** bf16, pelikan na rowerze, 16 prób/stronę, effort xhigh: mediana myślenia 27 346 → 17 156
  (−37%), średnia −40%; MATH-500 + AIME 2025 + HumanEval (694 zadania): −3% tokenów, trafność 95.2% = 95.2%; przy
  ×3 trafność spada do 44% (karta nie mówi, na czym).
- **Replikacja niezależna (NEW, zweryfikowana w repo):** RTX 5090, Q4_K_M z obu ramion z tego samego bf16, llama.cpp
  `fac3a894f`, **bez MTP** (`--no-nextn`), KV q8_0, T 1.0/top-p 0.95/top-k 20, effort xhigh, 32 vs 32, preregistracja:
  mediana 26 254 → 16 930 (−35.5%, CI95 −74.5…−10.4%), średnia −45.9%, p = 7.5e-6; <5k tokenów 0 → 10/32;
  kompletne SVG 32/32 → 31/32; mediana czasu próby 753.7 → 529.7 s (−30%). **W 11/32 odpowiedziach po edycji
  pojawia się dosłowne `</think>` w widocznej odpowiedzi (0/32 bez edycji); jedyny niekompletny SVG to ten, w który
  wpadło `</think>`.** Matematyka (24 zadania): 22/24 = 22/24.
- **Czy pasuje do naszego Uncensored? Tak (NEW, pomiar):** w naszym Q4_K_M tensor `blk.63.ffn_down.weight` to **Q6_K**
  (73 113 600 B); cos(u, kierunek Orca r) = 0.014 (≈ losowy 1/√5120), ‖uᵀW‖ = 1.5660 vs 1.5664 u replikatora
  na Main – obie edycje są praktycznie ortogonalne i składają się bez interakcji.
- **Da się nałożyć lokalnie bez pobierania modelu (NEW, zrobione):** (a) **LoRA rank-1 90 KB** (`lora_b = u`,
  `lora_a = uᵀW_served`, alpha = 1 → skala serwera = siła edycji, per żądanie); (b) **splice** w kopię GGUF:
  naiwna re-kwantyzacja Q6_K zachowuje tylko **1.76×** zamiast 2× (delta 1.4% normy jest poniżej kroku Q6_K), wariant
  z error-feedbackiem wzdłuż u daje **2.005×** (cos 0.99998). Nawet `u.npy` nie jest potrzebne: `u` odtwarzamy
  z GGUF (`output_norm ⊙ output.weight[</think>]`, cos 0.9998).
- **Werdykt:** tanie do sprawdzenia (0 pobrań, adapter gotowy), ale korzyść jest głównie przy **effort xhigh i
  zadaniach otwartych**; na matematyce/kodzie −3%, a przy naszym produkcyjnym `--reasoning-effort low` efekt
  niezmierzony. Ryzyko `</think>` w treści (11/32) jest dla agentów z wywołaniami narzędzi w formacie XML groźne
  (§5). Rekomendacja: test T1–T6 (§6) gdy GPU wolne; ewentualne wdrożenie tylko jako **opcja opt-in per żądanie**
  (LoRA, domyślnie wyłączona) + strażnik „drugie `</think>` zabronione”.

## 1. Fakty o edycji (źródła pierwotne)

| fakt | źródło | NEW/KNOWN |
|---|---|---|
| Repo HF `jarrodwatts/Qwen3.8-27B-Astra-Stop`, rev `27c08370`, 2026-11-04 06:15Z, Apache-2.0, pliki `apply.py`, `edit.json`, `u.npy` (20 608 B, sha256 `4b68782a…448c`), 0 dyskusji, 0 pobrań w API | [HF API](https://huggingface.co/api/models/jarrodwatts/Qwen3.8-27B-Astra-Stop), [commits](https://huggingface.co/api/models/jarrodwatts/Qwen3.8-27B-Astra-Stop/commits/main) | NEW |
| Tensor: `model.language_model.layers.63.mlp.down_proj.weight`, shard `model-00017-of-00018.safetensors` (2 108 759 344 B, sha256 `beb51f01…a8`), baza `Qwen/Qwen3.8-27B` rev `1d4bf0f2` | [`edit.json`](https://huggingface.co/jarrodwatts/Qwen3.8-27B-Astra-Stop/blob/main/edit.json), [drzewo bazy](https://huggingface.co/api/models/Qwen/Qwen3.8-27B/tree/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0) | NEW |
| Wzór `W' = W − α·outer(u, u@W)`, α = −1, u znormalizowane; `apply.py` liczy w float64, zapis bf16; wynik sha256 `44ad2e65…89af`; model z testów liczony w float32 (1 812 wag różni się o 1 ulp bf16) | `edit.json`; [`README.md:19-23,61`](https://huggingface.co/jarrodwatts/Qwen3.8-27B-Astra-Stop/blob/main/README.md); `apply.py:62-66` | NEW |
| Rodzaj edycji: **rank-1, wzmocnienie** (nie ablacja) składowej wyjścia MLP warstwy 63 wzdłuż u: `W' = (I + u uᵀ)W`. To nie jest bias, nie wektor dodany do `output.weight` ani wiersze lm_head; `output.weight` nietknięte | `apply.py:62-66` | NEW |
| Względna zmiana macierzy 1.4% (karta), u nas 1.426% na Q6_K Uncensored | karta `README.md:19`; [`analyze_unc.json`](69c-skrypty/analyze_unc.json) | NEW (pomiar) |
| Jak znaleziono: GPT-6 Astra w Codex „robiąc własne eksperymenty na wagach”, ~$100 GPU (post autora); inspiracja: Weight-Space Programming | [X autora 2026-11-04](https://x.com/jarrodwatts/status/2117808859691811216) (108 826 wyświetleń przy odczycie), `README.md:15` | NEW (koszt i narzędzie); WSP KNOWN ([R62](62-weight-space-programming.md)) |
| Log odkrycia (prompty, kod, przebiegi) **nieopublikowany** – w odróżnieniu od eksperymentu 8 WSP | brak plików w repo HF; [R62](62-weight-space-programming.md) opisuje pełne logi exp8 | NEW |

### 1.1 Czym jest u – pomiar na naszym GGUF (NEW)

`69c-skrypty/analyze.py` na `~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf` (wynik: [`analyze_unc.json`](69c-skrypty/analyze_unc.json)):

| porównanie | cos |
|---|---|
| u vs `output.weight[</think>]` (id 248069), surowy wiersz | 0.9947 (karta: 0.995) |
| u vs `output_norm ⊙ output.weight[</think>]` (efektywny kierunek odczytu w strumieniu) | **0.9998** |
| u vs `<think>` / `<\|im_end\|>` / `Wait` / `\n` | 0.143 / 0.257 / 0.083 / −0.144 |
| u vs 512 losowych wierszy: średnio \|cos\| / max | 0.062 / 0.258 |
| u vs kierunek Uncensored r (Orca, `21e-skrypty/r_qwen.npy`) | **0.014** |

[INFERENCE] u to po prostu znormalizowany wektor „logit-lens” tokena `</think>` liczony z bf16; resztkowa różnica 2e-4
to szum Q6_K w naszym `output.weight`. Wniosek praktyczny: przepis jest odtwarzalny z dowolnego GGUF bez `u.npy`
(`make_lora.py … local`, cos adaptera z u.npy vs lokalnego 0.9998).

Przesłuch na inne tokeny (`crosstalk.txt`, cały słownik 248 320): względne pchnięcie logitu `(g⊙w_t)·u / (g⊙w_</think>)·u`
– `</think>` 1.000, następne **0.27** (`-------------</`, `**>>`, `----</`, `</tool_response>` 0.247, `<\/` 0.241,
`<|box_end|>` 0.236); poza `</think>` tylko 10 tokenów ma > 0.25; najczęstsze tokeny lekko w dół (`Ġ` −0.22, `(` −0.17, `,` −0.15,
`.` −0.15, `\n` −0.14); odchylenie standardowe 0.03. Edycja jest więc bardzo selektywna na `</think>`.

[INFERENCE] Mechanizm przecieku `</think>` do odpowiedzi: ostatnie MLP „głosuje” za tokenami zamykającymi (`</…`),
a podwojenie jego składowej wzdłuż u podnosi też `</think>` w miejscach zamykania tagów – zgodne z tym, że jedyny
zepsuty SVG w replikacji to ten z `</think>` wewnątrz SVG. Dla nas istotne: Qwen3.8 woła narzędzia w XML
(`</parameter>`, `</function>`, `</tool_call>`), a kod agentów to często HTML/JSX.

## 2. Liczby i warunki (dostawca vs zweryfikowane)

| | autor (bf16) | replikacja witcheer (Q4_K_M) |
|---|---|---|
| status | **deklaracja dostawcy**; brak surowych danych, brak samplera, brak dokładnego promptu | **zweryfikowane w repo** (`PREREG.md`, `summary.json`), surowych śladów brak w repo |
| sprzęt | nie podano (post: „~$100 w GPU”) | 1× RTX 5090, 4 sloty po 65 536, KV q8_0 |
| silnik | Transformers/vLLM/SGLang? nie podano | llama.cpp `fac3a894f`, `--reasoning-format deepseek`, **bez MTP** |
| prompt | „pelican riding a bicycle” (dokładne brzmienie nieznane) | `Generate an SVG of a pelican riding a bicycle`, bez promptu systemowego |
| sampler | nie podano | T 1.0, top-p 0.95, top-k 20, min-p 0, seedy 1–32, cap 60 000 (nikt nie dobił) |
| effort | xhigh | xhigh (`chat_template_kwargs`), smoke: xhigh 65 vs low 53 tokeny promptu |
| mediana myślenia | 27 346 → 17 156 (−37%), n = 16 | 26 254 → 16 930 (**−35.5%**, CI95 −74.5…−10.4), n = 32, p = 7.5e-6 |
| średnia | 28 474 → 17 201 (−40%) | 26 809 → 14 509 (**−45.9%**, CI95 −60.3…−31.4) |
| rozkład po edycji | – | **dwumodalny**: Q1 2 614, Q3 23 483, min **151** tokenów |
| < 5 000 tokenów | 0/16 → 5/16 | 0/32 → 10/32 |
| kompletny SVG | 16/16 → 16/16 | 32/32 → **31/32** (Fisher p = 1.0); „kompletny” = parsuje się i renderuje (≥ 4 kolory, ≥ 3% pikseli), jakość rysunku nieoceniana |
| `</think>` w treści | – | **0/32 → 11/32** |
| matematyka | 694 zadania: 95.2% = 95.2%, tokeny −3% | 24 z MATH-500: 22/24 = 22/24, mediana myślenia 792.5 → 706.5, średnia 2 197 → 2 198 |
| ×3 | trafność 44% (zbiór nieznany), ×5+ „przestaje myśleć” | nie testowano |
| t/s | – | 38.4 → 39.5 t/s/slot (4 sloty równolegle) – bez wpływu na szybkość |

Źródła: [karta `README.md:29-36`](https://huggingface.co/jarrodwatts/Qwen3.8-27B-Astra-Stop/blob/main/README.md);
[`astra-stop/README.md:9`](https://github.com/notwitcheer/llm-bench-rig/blob/main/astra-stop/README.md),
[`PREREG.md:17-25`](https://github.com/notwitcheer/llm-bench-rig/blob/main/astra-stop/PREREG.md),
[`data/astra-stop/summary.json`](https://github.com/notwitcheer/llm-bench-rig/blob/main/data/astra-stop/summary.json);
post replikatora [x.com/witcheer/status/2119392237125501252](https://x.com/witcheer/status/2119392237125501252)
(2026-11-08 11:31 UTC; link do repo w wątku [2119392238186713562](https://x.com/witcheer/status/2119392238186713562)).

**Uwagi metodyczne:**
- Jeden prompt kreatywny. Na zadaniach z odpowiedzią efekt jest bliski zeru (−3%), więc „myśli o 1/3 mniej” to
  wynik dla jednego typu zadań, nie ogólny.
- Różnica 31/32 vs 32/32 nie jest istotna (Fisher p = 1.0), ale jej przyczyna (przeciek `</think>`, 11/32) to
  systematyczny efekt uboczny, nie szum.
- Nikt nie porównał z tańszą alternatywą: effort `medium`/`low` albo budżet myślenia przy tej samej trafności.
  To kluczowe porównanie (patrz T4).
- Obie liczby są bez MTP; my mamy MTP n = 4 + lookup + weryfikację GPU.
- Szersza krytyka „Weight-Space Programming” (agent pisał kod Pythona i uruchamiał model, a nie „czytał wagi”):
  [honnibal.dev 2026-11-03](https://honnibal.dev/blog/astra-read-write-misleading) (NEW); kontrola mechaniczna
  OpenWSP i audyt Honesty.Tools są KNOWN z [R62](62-weight-space-programming.md).

## 3. NEW vs KNOWN

| teza | status | gdzie |
|---|---|---|
| WSP/Astra na Qwen3.5-0.8B (pętle, rank-1 na 2× `down_proj`), krytyka, kontrole | KNOWN | [R62 §1–3](62-weight-space-programming.md) |
| Edycja kierunku = LoRA rank-1, `build_lora_mm` na `ffn_down`, `lora` per żądanie, splice zamiast `export-lora` | KNOWN | R62 §4.1 (u nas: `llama-graph.cpp:1607-1641`, `:2039`, `server-context.cpp:1976-1986`) |
| Bramka KLD ≤ 2× podłoga Q8, ryzyko MTP przy edycji trunku | KNOWN | R62 §4.3 |
| Uncensored = rank-1 projekcja writerów (I − r rᵀ) | KNOWN | [[uncensored-ablacja-kierunku]] |
| Swift 1.5: RL na krótsze myślenie, E1: −19% tokenów zadań przez rzadsze pętle, mediana bez zmian | KNOWN | [[swift-1-5]] |
| Sampler budżetu myślenia (twarde cięcie: FORCING `</think>` + opcjonalna wiadomość), `--reasoning-budget`, per żądanie `thinking_budget_tokens` | KNOWN | łatka 0066 (R08:178), `qwen-opt/samp_ab.py:21`; kod: `common/reasoning-budget.h`, `server-common.cpp:1836-1846` |
| Astra-Stop: tensor, wzór, α = −1, liczby autora i replikacji, przeciek `</think>` 11/32 | **NEW** | §1–2 |
| u ≈ `output_norm ⊙ W_U[</think>]` (cos 0.9998), przesłuch ≤ 0.27, mechanizm przecieku przez tokeny `</…` | **NEW** (pomiar + [INFERENCE]) | §1.1 |
| Na naszym Q4_K_M: Q6_K, ortogonalne do r (0.014), ‖uᵀW‖ 1.5660 | **NEW** (pomiar) | §1.1, §4 |
| Re-kwantyzacja Q6_K→Q6_K gubi 24% edycji; error-feedback 2.005×; Q8_0 1.9985× | **NEW** (pomiar) | §4.2 |
| Gotowy adapter LoRA 90 KB dla naszego pliku | **NEW** (zrobione) | §4.1 |
| W llama.cpp nie ma „miękkiego” budżetu (bias rosnący z liczbą tokenów); jest tylko twardy | **NEW** (sprawdzone w kodzie: `reasoning-budget.cpp:170-183` – passthrough albo −inf poza wymuszanym tokenem) | §5 |
| Edycja w ostatniej warstwie nie zmienia KV/stanu GDN żadnej warstwy trunku (jedynie logity i wejście głowicy MTP) | **NEW** [INFERENCE z architektury: warstwa 63 jest ostatnia] | §4.1 |

## 4. Zastosowanie do naszego modelu i kwantyzacji

| plik | `blk.63.ffn_down.weight` | ‖uᵀW‖ | `output.weight` |
|---|---|---|---|
| nasz `Qwen3.8-27B-Uncensored-Q4_K_M.gguf` (Orca, 16 810 714 496 B) | **Q6_K**, 73 113 600 B, offset danych 16 373 996 928 | 1.5660 | Q6_K |
| `Qwen3.8-27B-UD-Q4_K_XL.gguf` (Main, Unsloth; NVIDIA Enigma) | Q6_K, 73 113 600 B | 1.5632 | Q6_K |
| Q4_K_M witcheera z bf16 Maina (z `PREREG.md:18`) | Q6_K | 1.5664 → 3.1312 po edycji (1.999×) | – |

- Orca zrzutowała r także z tej macierzy (‖rᵀW‖ = 0.079 wobec ~1.53 oczekiwanego dla losowego kierunku), ale r ⟂ u,
  więc `(I + u uᵀ)(I − r rᵀ)W ≈ (I − r rᵀ)(I + u uᵀ)W` – Astra na Uncensored ≈ Astra na Main (NEW, pomiar).
- `--no-nextn` u replikatora: nie testowali głowicy MTP. U nas MTP (blk.64) dostaje stan ukryty z warstwy 63, czyli
  edytowany; jego własny `output.weight` jest nietknięty. [INFERENCE] Głowica nie „wie” o wzmocnieniu `</think>`,
  więc akceptacja może minimalnie spaść na granicy myślenia (rzadkie pozycje).

### 4.1 Droga A: LoRA rank-1 w runtime (zalecana do testów)

- `make_lora.py BASE.gguf OUT.gguf [u.npy|local]` → `blk.63.ffn_down.weight.lora_a` F32 ne=[17408,1] (= uᵀW
  zdekwantyzowanego tensora, który serwujemy), `.lora_b` F32 ne=[1,5120] (= u), `adapter.lora.alpha = 1`.
  Kształty zgodne z walidacją `llama-adapter.cpp:364-370`; skala `alpha/rank = 1`, więc **skala adaptera = siła
  edycji** (1.0 = ×2 autora, 0.5 = ×1.5, 0 = wyłączone).
- Zbudowane: `~/src/research69/astra/astra-stop-lora-unc.gguf` (90 496 B, sha256 `f75fbfb3…b729`) i wariant z
  lokalnym u. Nie ładowałem go w serwerze (GPU zajęte).
- Uruchomienie: `EXTRA_ARGS="--lora,<ścieżka>,--lora-init-without-apply" ~/qwen-opt/run-topka.sh uncensored`
  i w żądaniu `"lora":[{"id":0,"scale":1.0}]`. Zmiana adaptera czyści cache slotu (`server-context.cpp:1978-1981`);
  [INFERENCE] dla warstwy 63 jest to w zasadzie zbędne (KV trunku się nie zmienia), ale KV warstwy MTP już tak.
- Koszt wg V(w, ctx) ([[koszt-szerokosci-weryfikacji]]): +4 węzły grafu w jednej warstwie (2× `mul_mat` rank-1,
  `scale`, `add`) na krok weryfikacji, ~90 KB odczytu → ~8–10 µs przy V5 = 24.1–27.2 ms (2k–64k) ≈ **0.03–0.04%**
  `[SZACUNEK: ~2 µs podłogi pakietu na XTX, R21b]`. Niewiadoma: zgodność z PM4 replay i fuzjami topki (R62 §4.3).

### 4.2 Droga B: splice do kopii GGUF (zero kosztu runtime)

Pomiar `splice_variants.py` (kwantyzator `ggml_quantize_chunk` z `~/llama-topka/bin/libggml-base.so`, bez imatrixa):

| wariant | ‖uᵀWq‖ / ‖uᵀW‖ (cel 2.0) | cos(uᵀWq, 2uᵀW) | szum poza u (‖·‖/‖W‖) |
|---|---|---|---|
| re-kwantyzacja bez edycji (kontrola) | 1.0 (97.7% bajtów identycznych) | – | 0.02% |
| Q6_K, edycja wprost | **1.759** | 0.9927 | 0.94% |
| Q6_K, nadsterowanie k = 1.15 | 1.933 | 0.9936 | 1.04% |
| **Q6_K, error-feedback wzdłuż u, 4 iteracje** | **2.005** | **0.99998** | 1.17% |
| Q8_0 (zmiana typu, +21.6 MB, wymaga przepisania pliku) | 1.9985 | 0.99998 | 0.56% |

- Przyczyna (NEW): delta 1.4% normy to ~0.1 kroku Q6_K na element; ponowna kwantyzacja już skwantyzowanego tensora
  w większości wraca na stary punkt siatki. Replikator kwantyzował z bf16, stąd jego 1.999×.
- Blob error-feedback (`blk63_ffn_down_astra_unc_errfb.q6k`, 73 113 600 B, sha256 `f6eff25f…7074`) i
  `splice_gguf.sh` (kopia 16.8 GB + `dd` w offset, kontrola `cmp`, że nic poza tensorem się nie zmieniło) są gotowe;
  **nie uruchamiałem** kopii (16.8 GB zapisu na dysk, wolne 101 GB).
- Szum re-kwantyzacji 1.17% normy jednej macierzy to dodatkowa (niezamierzona) zmiana; LoRA jej nie ma.

## 5. Na tle znanych metod skracania myślenia

| metoda | mechanizm | zmienia wagi? | kontrola użytkownika | dowód jakości | u nas |
|---|---|---|---|---|---|
| **Astra-Stop** | ×2 składowej MLP63 wzdłuż odczytu `</think>` (miękki, kontekstowy bias) | tak (albo LoRA runtime) | LoRA: skala per żądanie | 1 prompt kreatywny + 694/24 zadania; przeciek `</think>` 11/32 | niezmierzone |
| Swift 1.5 (RL/OPD) | fine-tune całego trunku | tak, cały model | brak (inny model) | E1: −19% tokenów zadań przez mniej pętli, mediana bez zmian, W4 pass 1.00 | KNOWN [[swift-1-5]]; licencja < $1M |
| `--reasoning-effort low/medium/xhigh` | linia w prompcie systemowym (szablon Qwen3.8) | nie | per żądanie (`chat_template_kwargs`) | produkcja na `low` | KNOWN, `run-llm.sh:46-55` |
| budżet myślenia (`--reasoning-budget`, `thinking_budget_tokens`, `--reasoning-budget-message`) | twarde wymuszenie `</think>` po N tokenach | nie | per żądanie | Qwen3: budżet z wiadomością ([2505.09388](https://arxiv.org/abs/2505.09388)); s1 „budget forcing” ([2501.19393](https://arxiv.org/abs/2501.19393)) | KNOWN, w kodzie topki |
| „miękki” budżet: bias na `</think>` rosnący po N tokenach | sampler | nie | per żądanie | brak gotowej implementacji w llama.cpp (sprawdzone) | NEW pomysł (I6) |
| tłumienie tokenów refleksji („Wait”, „Hmm”) | logit-bias/ban | nie | per żądanie (`logit_bias`) | NoWait −27…−51% długości ([2506.08343](https://arxiv.org/abs/2506.08343)) | do rozważenia, niezmierzone |
| ThinkEdit / SEAL | edycja głów atencji / wektor sterujący | tak / nie | – | KNOWN (R62 §3) | – |

Uwaga: zwykły statyczny `logit_bias` na `</think>` jest gorszy od Astry – działa także w odpowiedzi i bez
kontekstu; Astra jest ~„biasem równym własnemu głosowi ostatniego MLP”, a mimo to i tak przecieka (11/32).

## 6. Testowalne pomysły (na NASZYM pudle)

Wszystko na Uncensored Q4_K_M, topka-q63 z produkcyjnymi flagami (MTP n=4, lookup W16, GPU verify, PM4). Ramiona
w blokach ABBA na świeżych serwerach. Narzędzia: `69c-skrypty/pelican_ab.py` (pelikan/dowolny prompt, skala LoRA per
żądanie, skan przecieku), `~/qwen-opt/quantkld/tasks.py` (20 zadań: 8 math, 6 kod, 6 PL), `spec_sweep`,
`llama-perplexity --kl-divergence` z `--lora`.

| # | pomysł | oczekiwany zysk (V(w,ctx) + tokeny) | dokładny test | kryterium odrzucenia | do pobrania |
|---|---|---|---|---|---|
| T1 | LoRA ładuje się w topce, skala 0 = bez zmian | 0 (bramka) | serwer z `--lora …,--lora-init-without-apply`; greedy md5 na `spec_sweep` vs bez `--lora` | crash, błąd adaptera, inny md5 przy skali 0 | 0 (adapter 90 KB gotowy) |
| T2 | koszt LoRA przy skali 1 | −0.03…−0.04% t/s `[SZACUNEK]` | `spec_sweep` T=1 ABBA, skala 0 vs 1; akceptacja MTP z logów | t/s < −1% albo akceptacja MTP < −1 pp | 0 |
| T3 | replikacja na naszym stosie (xhigh, MTP) | mediana myślenia −30…−36%, czas do odpowiedzi −30% (wg replikacji) | `pelican_ab.py run --effort xhigh --seeds 1-16` ×2 ramiona (~1.6 h XTX `[SZACUNEK: 16×(26k+17k)/118 t/s]`) | mediana < −20% albo p ≥ 0.05; svg_ok spada o > 2/16 | 0 |
| T4 | **czy to w ogóle coś daje przy `low`/`medium`** i czy `medium` bez edycji nie daje tego samego | `low`: 0…−10% `[SZACUNEK]` | `tasks.py run --seeds 1,2` (20 zadań) dla 4 ramion: {low, xhigh} × {skala 0, 1} + pelikan `--effort medium` skala 0 | przy `low` mediana tokenów > −5% → brak wartości dla produkcji; pass spada o ≥ 2/40 | 0 |
| T5 | KLD na tekście bez myślenia | ~0 (u ⟂ zwykłym tokenom, przesłuch ≤ 0.27) | `llama-perplexity --kl-divergence-base` z bazy vs `--lora` skala 1 na korpusach 16e (wiki, PL proza, kod, czat) | KLD > 2× podłoga Q8 (0.0038 / 0.0006) | 0 |
| T6 | **przeciek `</think>` w agentach** | – (ryzyko) | `pelican_ab.py scan` na T3/T4 + 50 zadań agentowych z narzędziami (replay sesji omp) i prompt HTML/JSX; licz `</think>` w treści i w `<tool_call>` | ≥ 1 zepsute wywołanie narzędzia albo przeciek > 2% odpowiedzi | 0 |
| T7 | strażnik: `</think>` dozwolone tylko wewnątrz otwartego bloku myślenia (stan DONE samplera budżetu → −inf) | usuwa przeciek; koszt ~0 (host) | zmiana w `common/reasoning-budget.cpp` (stan DONE) + T3/T6 ponownie | przeciek > 0 albo zmiana md5 bazowego modelu przy zerowym przecieku | 0; wymaga buildu (później) |
| T8 | siła 0.5 (×1.5) | mniejszy przeciek przy części zysku | T3 + T6 ze skalą 0.5 | jak T3/T6 | 0 |
| T9 | splice (error-feedback) zamiast LoRA, tylko gdy T1 padnie na fuzjach | 0 kosztu runtime | `splice_gguf.sh`, potem T1–T6 na nowym pliku; KLD splice vs LoRA | KLD(splice‖LoRA) > podłoga Q8 | 0 (16.8 GB miejsca na kopię) |
| T10 | NVIDIA (Enigma) | jak T3/T4, LoRA identyczna w CUDA | `make_lora.py <UD-Q4_K_XL lub UD-Q6_K> … local`, T2–T6 na wynajętej 4090 przy okazji innych testów | jak wyżej | 0 dodatkowo (te same GGUF co w recepturach) |

Czego **nie** trzeba pobierać: modelu bf16 (55.56 GB) ani shardu 17 (2.11 GB). Shard 17 przydałby się tylko do
dokładnej kopii przepisu autora na Mainie (kwantyzacja z bf16 zamiast error-feedbacku); dla Uncensored i tak trzeba by
dołożyć projekcję Orki (mamy `r_qwen.npy`). Nie zalecam.

Czas GPU całości T1–T6: ~4–5 h XTX `[SZACUNEK]`, albo ~$3–5 na Vast (R62 §5.2: ewaluacja ramienia $2–3).

## 7. Decyzja dla użytkownika (zmiana zachowania, nie optymalizacja)

| opcja | co | zysk | ryzyko | rekomendacja |
|---|---|---|---|---|
| A | nic nie zmieniać; zostać przy `--reasoning-effort low` | – | – | domyślna, dopóki T3–T6 nie przejdą |
| B | **opt-in per żądanie**: przełącznik „krótsze myślenie” = LoRA skala 1 (albo 0.5), domyślnie wyłączony | −30…−36% tokenów myślenia przy xhigh/otwartych zadaniach (wg replikacji) | przeciek `</think>`, nieznana jakość poza 1 promptem i małymi zbiorami | **tak, ale dopiero po T1–T6 i najlepiej z T7** |
| C | wpiec na stałe (splice) do modelu domyślnego | jak B, bez kontroli użytkownika | jak B, dla wszystkich | nie |
| D | sam strażnik `</think>` (T7), niezależnie od Astry | brak zysku szybkości; poprawność formatu | minimalna zmiana wyjścia tylko przy niepoprawnym tokenie sterującym | do rozważenia osobno |

## 8. Ryzyka

1. **Przeciek `</think>` do treści** (11/32 u replikatora) – dla agentów z XML tool calls i kodu HTML/JSX może psuć
   parsowanie; nasz `LLAMA_SERVER_SAFE_TOOLS` traktuje markery jako prawdziwe tokeny specjalne (R42), a ten przeciek
   jest prawdziwym tokenem specjalnym [INFERENCE: parser może uznać drugie zamknięcie myślenia].
2. **Wczesne ucinanie myślenia:** minimum 151 tokenów i dwumodalny rozkład po edycji; autor: ×3 → trafność 44%.
   Jakość krótkich pelikanów nieoceniona (tylko „renderuje się”).
3. **Uogólnienie:** dowody to 1 prompt kreatywny + 694 zadania autora (bez CI, bez rozbicia) + 24 zadania replikatora.
   Brak PL, brak agentów, brak długiego kontekstu, brak effort `low`.
4. **Zgodność z topką:** LoRA w grafie z PM4 replay / fuzjami / łańcuchem MTP niesprawdzona; MTP nieobjęte replikacją.
5. **Kwantyzacja:** naiwny splice daje 1.76× zamiast 2× – kto „wypiecze” edycję w już skwantyzowany plik, dostanie
   słabszą edycję niż autor (dotyczy też cudzych GGUF-ów z tą łatką).
6. **Licencja:** Apache-2.0 (łatka i baza) – czysto; Orca Uncensored też Apache-2.0.

## 9. Źródła

- Łatka: [huggingface.co/jarrodwatts/Qwen3.8-27B-Astra-Stop](https://huggingface.co/jarrodwatts/Qwen3.8-27B-Astra-Stop) (rev `27c08370`; `README.md`, `edit.json`, `apply.py`, `u.npy`); post autora [x.com/jarrodwatts/status/2117808859691811216](https://x.com/jarrodwatts/status/2117808859691811216).
- Replikacja: [github.com/notwitcheer/llm-bench-rig/tree/main/astra-stop](https://github.com/notwitcheer/llm-bench-rig/tree/main/astra-stop) (HEAD `f732402`, 2026-11-08), [`data/astra-stop/summary.json`](https://github.com/notwitcheer/llm-bench-rig/blob/main/data/astra-stop/summary.json); post [x.com/witcheer/status/2119392237125501252](https://x.com/witcheer/status/2119392237125501252).
- Tło: [rikiyat.github.io/blog/weight-space-programming](https://rikiyat.github.io/blog/weight-space-programming/); [honnibal.dev/blog/astra-read-write-misleading](https://honnibal.dev/blog/astra-read-write-misleading); [R62](62-weight-space-programming.md).
- Skracanie myślenia: [Qwen3 Technical Report 2505.09388](https://arxiv.org/abs/2505.09388); [s1 2501.19393](https://arxiv.org/abs/2501.19393); [NoWait 2506.08343](https://arxiv.org/abs/2506.08343).
- Nasz kod (`~/wt/topka-q63` @ `c0576e3e8`): `src/llama-graph.cpp:1607-1641` (`build_lora_mm`), `:2039` (down w `build_ffn`), `src/models/qwen35.cpp:495-498`, `src/llama-adapter.cpp:205-221,358-370`, `tools/server/server-context.cpp:1961-1990`, `tools/server/server-common.cpp:1836-1846`, `common/reasoning-budget.h`, `common/reasoning-budget.cpp:170-183`, `common/arg.cpp:3755-3767`.
- Nasza baza: [[uncensored-ablacja-kierunku]], [[swift-1-5]], [[koszt-szerokosci-weryfikacji]], [R62](62-weight-space-programming.md), `~/qwen-opt/run-topka.sh`, `~/qwen-opt/run-llm.sh:46-55`.
- Pomiary własne: [`69c-skrypty/`](69c-skrypty/) – `analyze.py` → `analyze_unc.json`, `splice_variants.py` → `splice_variants.json`, przesłuch → `crosstalk.txt`, `make_lora.py`, `splice_gguf.sh`, `pelican_ab.py`.

### Proponowane wiersze ZRODLA

| Astra-Stop (HF jarrodwatts/Qwen3.8-27B-Astra-Stop) | rev `27c08370` (11-04) | R69c | Rank-1 ×2 na `blk.63.ffn_down` wzdłuż odczytu `</think>`; zmiana zachowania, nie bezstratna; LoRA 90 KB gotowa. | −37% mediany (bf16, n=16, autor); 694 zadania −3% tokenów | wyniki przy effort low, przeciek `</think>` |
| llm-bench-rig/astra-stop (witcheer) | `f732402` (11-08) | R69c | Preregistrowana replikacja Q4_K_M na 5090 bez MTP: potwierdza −35.5%, ale `</think>` w treści 11/32. | 26 254 → 16 930; SVG 32→31/32 | surowe ślady, test z MTP |
| honnibal.dev „Astra read/write misleading” | 11-03 | R69c | Krytyka WSP: eksperymenty z LLM używały Pythona i przebiegów modelu. | – | – |
