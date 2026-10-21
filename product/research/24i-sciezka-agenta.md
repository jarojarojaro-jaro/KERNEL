# 24i. Ścieżka agenta: testy z InferenceX §11.5 na Qwen3.8-27B (XTX)

Data: 2026-10-19. Gałąź `agentpath` (~/wt/agentpath, od topka 2821e1303), commit `caf2b8e14`. Narzędzia: `~/qwen-opt/agentpath/`.

## Werdykt

- **(2) Tokenizacja + szablon: koszt jest realny i rośnie liniowo. Tokenizację naprawiłem bezstratnie** (`LLAMA_SERVER_TOK_CACHE=1`): przy kolejnych turach tej samej rozmowy spada z ~0.8 ms/1k tokenów do 0.5–2.5 ms na całą turę. 61/61 promptów daje tokeny identyczne z pełną tokenizacją. Render szablonu (63 ms przy 91k) zostaje.
- **(5) Audyt grafu decode (ślad mtp4): żadna pojedyncza operacja spoza matvec/FA/GDN nie przekracza 2% czasu kroku**, więc kryterium kill jest spełnione. Największy kandydat to ścieżka stanu konwolucji GDN (get_rows + concat + cpy): ~1 ms/krok (~3% decode, ~1% zegara sesji). To na granicy progu, więc bez implementacji.
- **(1) zapis przyrostowy, (3) MTP po restore, (4) odstęp checkpointów: nie zrobione (GPU wstrzymane).** Build z pomiarami i replay są gotowe, ale żaden bieg GPU nie ruszył: kolejka, a potem wstrzymanie GPU przez użytkownika.

## Liczby

### (2) Tokenizacja i szablon, CPU (`tmplbench`, ten sam kod co serwer: `oaicompat_chat_params_parse` + `tokenize_input_prompts`, vocab-only, `--jinja --reasoning-effort low`, prawdziwe sesje omp z fan-outu 13/15, best of 3)

| prompt (tokeny) | parse JSON | szablon | tokenizacja | razem |
|---|---|---|---|---|
| 14 017 | 0.4 ms | 10.7 ms | 14.4 ms | 25.5 ms |
| 38 811 | 0.9 ms | 29.4 ms | 32.5 ms | 62.7 ms |
| 75 341 | 1.7 ms | 49.1 ms | 57.7 ms | 108.5 ms |
| 91 005 | 1.9 ms | 62.9 ms | 72.5 ms | 137.3 ms |
| 158 287 (2 sesje sklejone) | 3.8 ms | 114.1 ms | 136.1 ms | 254.0 ms |

Próg z §11.5 (30 ms) jest przekroczony od ~15k tokenów.

**Zmiana:** `LLAMA_SERVER_TOK_CACHE=1` (`server-common.cpp`, `server_tokenize_cached`).
- Tokenizer najpierw tnie tekst na tokenach specjalnych, a potem tokenizuje każdy fragment osobno. Dla tokenu specjalnego X, którego żaden inny token specjalny nie może nakryć (zawierać go ani zaczynać się lub kończyć w jego środku), tokeny na lewo od X nie zależą od tekstu na prawo.
- Serwer trzyma 8 ostatnich promptów z tokenami. Bierze wpis z najdłuższym wspólnym prefiksem bajtów, kopiuje jego tokeny do ostatniego takiego X w tym prefiksie i tokenizuje tylko resztę.
- Wymagania: tylko słowniki BPE bez dodawanych BOS/EOS. Qwen ma 27 tokenów granicznych.
- `=2` dodatkowo tokenizuje całość i loguje rozbieżność (tryb testowy).

Weryfikacja: `bodies_w13.jsonl` (61 kolejnych tur 4 sesji, 8–56k tokenów), `TB_VERIFY=1`: **0 rozbieżności**. Czas tokenizacji tury po pierwszej: 0.5–2.5 ms, a bez cache 11–50 ms przy tych długościach.
- Zysk przy 91k ≈ 70 ms na turę, przy 158k ≈ 130 ms (tokenizacja pełna minus sufiks).
- Skutek dla TTFT na GPU: nie zmierzony, bo GPU było wstrzymane.

Szablon: render jinja odbywa się 3× na żądanie (prompt + 2 rendery w `common_chat_template_generation_prompt`). Prototyp pomijający jeden render dał w `tmplbench` 62.3 vs 62.9 ms przy 91k, czyli bez efektu. **Kill**, zmiany wycofane. Nie wiem, czy biblioteka w tym biegu zawierała zmianę (lokalny build przerwany), więc wynik jest niepewny.

### (5) Graf decode, ślad rocprof `~/qwen-opt/prof/{mtp4,rocm-mtp4-now}` (llama-master z 9.10, MTP4, 154/159 przejść celu)

| kategoria | us/krok | % czasu kerneli |
|---|---|---|
| matmul (mmvq/mmq + quantize_q8_1) | 29 240 | 84.5 |
| kopie / get_rows / set_rows | 1 325 | 3.8 |
| rms_norm | 1 037 | 3.0 |
| eltwise (add/mul/silu/...) | 816 | 2.4 |
| concat (stan konwolucji GDN) | 581 | 1.7 |
| GDN | 519 | 1.5 |
| FA | 322 | 0.9 |

Pojedyncze kernele poza matvec/FA/GDN, wszystkie < 2%:
- `rms_norm_f32<1024>` 1.81% (153 wywołania/krok × 4.1 µs);
- `cpy_scalar` 1.67% (261/krok × 2.2 µs);
- `concat_non_cont` 1.65% (48/krok × 12.0 µs);
- `k_get_rows_float_vec` 0.98% (48/krok × 7.1 µs).

Ścieżka stanu konwolucji GDN (`build_conv_state_lag`: get_rows → transpose → concat → cpy historii) kosztuje ~1.0–1.15 ms/krok. Concat niekontiguowy osiąga ~27 GB/s.
- Fuzja w jeden kernel conv-z-historią dałaby ≤ ~0.9 ms/krok, czyli ~2.7% decode.
- Przy udziale decode ~32% zegara sesji (21f §5) to ~0.9% zegara, a więc poniżej progu 1%. **Stop.**

Zastrzeżenie: ślad pochodzi z llama-master, nie z topki (topka ma te same `build_conv_state_lag`/concat w `delta-net-base.cpp`).

## Adopt / kill

| zmiana | decyzja |
|---|---|
| `LLAMA_SERVER_TOK_CACHE=1` | **adopt po smoke-teście na serwerze** (CPU: identyczne tokeny 61/61). Na GPU nie uruchomione |
| `LLAMA_SERVER_AP_TIMING=1` (logi kosztów: zapis/odczyt `--cache-ram`, checkpointy, szablon/tokenizacja, akceptacja draftu w 8 pierwszych krokach) | narzędzie, domyślnie wyłączone, zostaje |
| pominięcie renderu szablonu | kill (brak efektu, wycofane) |
| fuzja stanu konwolucji GDN | kill na teraz (< 1% zegara) |

## Nie zrobione (GPU wstrzymane)

- **(1) koszt zapisu do `--cache-ram`.** Brak pomiaru. Z wcześniejszych danych (16f E4) przywrócenie 2.3 GB przy 53k trwa ~1.1 s.
  - Z kodu: zapis = `vector::resize` (zerowanie) + D2H do pamięci stronicowanej + **głęboka kopia wszystkich checkpointów** (`prompt.checkpoints` kopiowane w `alloc`, każdy ~157 MB stanu GDN) przy każdej zmianie toru.
  - Przy `-np 1` i równoległych subagentach omp zmiana toru następuje przy każdym żądaniu.
  - Gotowe do pomiaru: `arm.sh` / `block2.sh`, workloady `w6.json` (4 tory × 6 tur, rr) i `w2big.json` (2 tory ~60k).
  - Kolejność poprawek do sprawdzenia: przeniesienie checkpointów zamiast kopii, bufor bez zerowania, pamięć przypięta, a delta dopiero jeśli D2H dominuje.
- **(3) akceptacja MTP po restore.** Licznik „first 8 steps accepted” jest w buildzie. Porównanie rr vs serial (`--order serial`) nie zostało uruchomione.
- **(4) koszt checkpointów.** Logi `ap ckpt create/restore` (czas, przeliczone tokeny) są w buildzie, ale bez biegu.
- Greedy md5 nowego buildu (c4708318/6f14e814) nie został sprawdzony, bo GPU było wstrzymane. Zmiany są domyślnie wyłączone, a włączony cache daje identyczne tokeny.

## Do bazy wiedzy

| folder | tytuł (plik) | streszczenie 1 linia | kluczowe liczby (źródło) |
|---|---|---|---|
| research | Raport 24i: ścieżka agenta (`raport-24i-sciezka-agenta.md`) | Tokenizacja i szablon kosztują ~1.5 ms/1k tokenów na turę. Cache tokenizacji to usuwa bezstratnie. Graf decode nie ma pojedynczego fallbacku > 2% | 91k: szablon 63 + tokenizacja 73 ms → tokenizacja ~1–2 ms; 0/61 rozbieżności (`agentpath/tmplbench`) |
| metody | Bezstratna tokenizacja przyrostowa (`tokenizacja-przyrostowa.md`) | Podział na tokenach specjalnych, których nic nie nakrywa, pozwala użyć tokenów poprzedniego promptu do ostatniej takiej granicy we wspólnym prefiksie | Qwen: 27 tokenów granicznych; BPE bez BOS/EOS (`server-common.cpp`) |
| lekcje | Glue w decode Qwen to ~15% kroku, ale rozproszone (`lekcja-glue-decode.md`) | Największy pojedynczy kawałek (stan konwolucji GDN) to ~1 ms/krok, czyli < 1% zegara sesji agenta | matmul 84.5%, concat 12 µs × 48/krok (`prof/rocm-mtp4-now`) |
