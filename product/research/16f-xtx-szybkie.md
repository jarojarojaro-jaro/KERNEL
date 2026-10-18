# 16f. Szybkie zyski na XTX: LFM ubatch, typ bloku MTP, hak MTP w prefillu, cache promptu agenta, cache sesji na SSD

Data: 2026-10-18. Autor: agent XtxQuickWins. Sprzęt: RX 7900 XTX (gfx1100), ROCm 10.0.
Kod: worktree `~/wt/quickwins`, gałąź `quickwins` od `amd-opt` @ `f61994f58`. Commity: `50c3a2f2a`, `fc89bc486`, `7f908b4dd` (cofnięty w `caefe1800`), `7369380bf`.
Skrypty i surowe wyniki: `~/wt/quickwins/qw/` (`srv.sh` = linia poleceń `run-llm.sh`, `block.sh`/`seq.sh` = blok GPU pod `flock`, `ttft.py`, `replay.py`, `capture_proxy.py`, `*.jsonl`, `e1-*.txt`, `greedy/`).
Wszystkie pomiary to świeże serwery i ABBA (mediany), chyba że zaznaczono inaczej. Wyniki zebrane w czasie kolizji blokad (23:18–23:30 UTC) odrzucone.

## TL;DR i zalecane flagi produkcyjne

| # | Eksperyment | Werdykt | Liczby |
|---|---|---|---|
| E1 | LFM `-b 2048 -ub 2048` | **wygrywa** | pp4096 6108 → 7148 t/s (+17%), pp16384 5654 → 6680 (+18%); TTFT 8k 1471 → 1254 ms, 32k 6668 → 5692 ms (−15%); VRAM +498 MiB przy ctx 131072 |
| E2 | blok MTP: Q6_K (natywny) / IQ4_XS / Q8_0 | **IQ4_XS zostaje** (Q6_K i Q8_0 przegrywają) | 5 seedów: IQ4_XS 113.2 t/s, 3.063 tok/krok, 28.14 ms/krok; Q6_K 109.4 t/s, 3.012, 28.76 |
| E3 | złożenie haka MTP w graf prefillu | **przegrywa, nie wdrażać** (maks. zysk ~2.5%) | sam hak: 65 / 186 / 768 ms przy 2k / 8k / 32k; reszta różnicy MTP vs bez spekulacji to checkpointy i synchronizacja |
| E4 | cache promptu agenta | **przyczyna znaleziona, łatka wygrywa** | nowa sesja omp po obcym zapytaniu: Qwen 8019 → 1612 ms, LFM 1357 → 230 ms (`LLAMA_SERVER_CACHE_SHARE_MIN=1024`) |
| E5 | cache sesji na SSD | **wykonalny już dziś przez slot save/restore** | sesja 53k: Qwen odczyt 2.51 s zamiast ~61.5 s prefillu; LFM 0.53 s zamiast ~12.2 s |
| dod. | kopie stanu przez pinned host (`LLAMA_STATE_PINNED`) | **przegrywa** (cofnięte) | checkpoint ~94–104 ms bez zmian; replay omp: 1981 → 1982 ms |

Proponowana zmiana `~/qwen-opt/run-llm.sh` (pliku produkcyjnego nie zmieniałem). Linia z `LLAMA_SERVER_CACHE_SHARE_MIN` działa dopiero po przeniesieniu commita `50c3a2f2a` do `amd-opt` i przebudowaniu `~/llama-opt`. Bez łatki zmienna jest ignorowana, więc linia nic nie psuje.

```diff
--- a/run-llm.sh
+++ b/run-llm.sh
@@
-#   lfm         none ~294 t/s LiquidAI LFM2.5-24B-A2B Q5_K_M (MoE, ~2B active, no MTP head), ctx 131072, KV q8_0
+#   lfm         none ~294 t/s LiquidAI LFM2.5-24B-A2B Q5_K_M (MoE, ~2B active, no MTP head), ctx 131072, KV q8_0,
+#                    -b/-ub 2048 (prefill +17%, TTFT -15% at >=8k, +0.5 GB VRAM; 16f E1)
@@
 case $model in lfm|lfm-uncensored) kv_default=q8_0 ;; esac
 kv=${KV:-$kv_default}
+# LFM: one 2048-token ubatch per MoE pass (pp4096 6108 -> 7148 t/s on the XTX); UB=512 restores the old setting
+ub_args=()
+case $model in lfm|lfm-uncensored) ub_args=(-b 2048 -ub "${UB:-2048}") ;; esac
@@
 export LLAMA_SERVER_REASONING_CONTROL=${REASONING_CONTROL:-0}
+# a new agent session (same system prompt + tools) resumes from a cached long session's checkpoint even when an
+# unrelated request took the slot in between (16f E4: Qwen 8.0 -> 1.6 s, LFM 1.36 -> 0.23 s); needs the quickwins patch
+export LLAMA_SERVER_CACHE_SHARE_MIN=${CACHE_SHARE_MIN:-1024}
 
 "$bin" -m "$gguf" -ngl 999 -fa on -ctk "$kv" -ctv "$kv" -c "$ctx" -np 1 --jinja --cache-ram 16384 \
-    "${think_args[@]}" --host "$host" --port "$port" --log-file "$log" "${spec_args[@]}" "${extra_args[@]}"
+    "${think_args[@]}" --host "$host" --port "$port" --log-file "$log" "${spec_args[@]}" "${ub_args[@]}" "${extra_args[@]}"
```

`MTP_TYPE=iq4_xs` zostaje bez zmian (E2).

---

## E1. LFM `-b 2048 -ub 2048`

Teza z 5060 Ti: +56% pp4096 (4217 → 6587). Na XTX zysk jest mniejszy, bo nasz prefill LFM przy ub 512 już ma ~6100 t/s.

**llama-bench** (`-fa 1 -ctk q8_0 -ctv q8_0 -b 2048 -r 3`, kolejność ub 512→1024→2048, potem 2048→1024→512; `qw/e1-bench.md` w logu przebiegu):

| ub | pp4096 (A / B) | pp16384 (A / B) |
|---|---|---|
| 512 | 6134 / 6083 | 5663 / 5644 |
| 1024 | 6858 / 6852 (+12%) | 6320 / 6306 (+12%) |
| 2048 | 7142 / 7153 (**+17%**) | 6682 / 6679 (**+18%**) |

pp512 ma rozrzut ±1100–1400 t/s (rozgrzewka pierwszego powtórzenia), więc go nie interpretuję.

**TTFT serwera** (ustawienia z `run-llm.sh lfm`, ctx 131072, KV q8_0, świeże prompty bez cache, mediana z 2 powtórzeń; dwie serie: 512→1024→2048 i 2048→1024→512; `qw/e1-ttft.jsonl`):

| ub | 512 tok. | 2k | 8k | 32k | VRAM po pomiarach |
|---|---|---|---|---|---|
| 512 | 143 / 142 ms | 366 / 365 | 1473 / 1470 | 6676 / 6660 | 18591 MiB |
| 1024 | 144 / 144 | 337 / 338 | 1316 / 1316 | 6007 / 6005 | 18765 MiB |
| 2048 | 157* / 144 | 331 / 331 | 1258 / 1251 | 5690 / 5693 | 19089 MiB |

\* jedno powtórzenie 170 ms (rozgrzewka), drugie 144 ms.

VRAM rośnie o +498 MiB (bufor obliczeń). Przy ctx 131072 KV q8_0 to 19.1 z 24 GB, więc mieści się.

**Numeryka (KLD).** `llama-perplexity`, korpus = notatki wiki (`qw/kld.txt`), `-c 2048 --chunks 12 -b 2048`, baza = ub 2048 (`qw/e1-kld3.txt`):

| porównanie | KV q8_0: KLD / same top | KV f16: KLD / same top | PPL (q8_0) |
|---|---|---|---|
| ub 2048 (baza) | — | — | 14.111 ± 0.445 |
| ub 1024 | 0.0672 / 88.6% | 0.0670 / 88.8% | 14.108 |
| ub 512 | 0.0682 / 88.7% | 0.0659 / 88.5% | 14.300 |
| ub 256 | 0.0552 / 89.4% | 0.0594 / 89.5% | 14.090 |
| ub 128 | 0.0666 / 89.1% | 0.0677 / 88.8% | 14.164 |
| ub 512 vs ub 512 (A/A) | 0.0000 / 100% | — | — |

Wniosek: **każda** zmiana podziału na ubatche zmienia logity LFM o KLD ≈ 0.06 (88–89% tego samego top-1). Dzieje się tak niezależnie od typu KV. Upstream `e60eff95f` daje bit w bit te same liczby co nasz fork (`-c 512`: KLD 0.0766 dla ub 2048 i 0.0737 dla ub 1024 w obu buildach; `qw/e1-kld.txt`, `qw/e1-kld2.txt`). ub 2048 nie jest gorsze od ub 512: PPL 14.11 vs 14.30, różnica w granicach ±0.45. To cecha modelu albo ścieżki ggml dla LFM, nie zmiana jakości wywołana przez ub 2048. `[INFERENCE]` najpewniej remisy w routingu top-k MoE wzmacniane przez 40 warstw.

Uwagi:
- Checkpoint „n − 4 − ub” leży przy ub 2048 o 2052 tokeny przed końcem promptu. Regeneracja albo edycja ostatniej wiadomości przelicza do ~2k tokenów, czyli ~0.3 s na LFM.
- Greedy md5 krótkich promptów (`greedy.sh`) nie zależy od ub: prompt < 512 tokenów mieści się w jednym ubatchu.

**Werdykt: wygrywa.** +17–18% prefillu, −15% TTFT od 8k wzwyż, −10% przy 2k, bez zmian przy 512. Kosztuje +0.5 GB VRAM. Numeryka jest na poziomie każdej innej zmiany podziału batcha.

## E2. Typ bloku MTP (`--spec-mtp-type`), głowa draftu `iq4_xs` jak w produkcji

`spec_sweep` (6 promptów EN/PL, T=1, 400 tokenów), produkcyjny `~/llama-opt`, linia poleceń `run-llm.sh qwen`. Przebiegi przy stałym seedzie są deterministyczne: powtórzenia A/A dały identyczne tok/krok, a t/s różniły się o ±0.2.

**Runda 1:** 2 seedy, kolejność A-B-C / C-B-A / A-B-C. Mediany:

| typ bloku MTP | t/s (mediana promptów) | ms/krok |
|---|---|---|
| iq4_xs (produkcja) | 106.5 / 106.3 / 106.5 | 28.27 / 28.33 / 28.29 |
| natywny Q6_K | 108.7 / 108.5 / 108.5 | 28.91 / 29.00 / 28.96 |
| q8_0 | 103.1 / 102.9 / 103.2 | 29.19 / 29.31 / 29.20 |

**Runda 2:** 5 seedów, kolejność A-B-B-A, `qw/spec_sweep.jsonl`, etykiety `e2s5-*`:

| typ | t/s (mediana) | śr. t/s | tok/krok | ms/krok |
|---|---|---|---|---|
| iq4_xs | 113.3 / 113.2 | 108.9 | **3.063** | **28.14** |
| natywny Q6_K | 109.5 / 109.3 | 104.7 | 3.012 | 28.76 |

Przy 2 seedach Q6_K „wygrywał”, bo pl-kod dał 3.67 vs 3.25 tok/krok. Przy 5 seedach jest odwrotnie (3.32 vs 3.45). Z 2 seedami rozrzut per prompt jest większy niż efekt. Offline pilot (11) przewidywał +0.45% tok/krok dla Q6_K, a na żywo przy T=1 wyszło −1.7%, czyli efekt w szumie. Do tego Q6_K kosztuje +0.62 ms/krok (+2.2%), a q8_0 +0.9 ms/krok.

**Werdykt: Q6_K i q8_0 przegrywają; IQ4_XS zostaje** (−3.4% t/s dla Q6_K przy 5 seedach).

## E3. Hak MTP na prompt w prefillu (15d L4: „TTFT −5–7%”)

Zanim cokolwiek składać, zmierzyłem, ile kosztuje sam hak. Dodałem dwa przełączniki diagnostyczne:
- `LLAMA_MTP_HOOK_TIMING=1`: rozbicie `process()` na czas czekania na cel, dekod MTP i kopię;
- `LLAMA_MTP_HOOK_SKIP=N`: pomija dekod MTP dla batchy ≥ N tokenów. Drafty się psują, ale TTFT da się zmierzyć.

TTFT, Qwen3.8-27B, linia poleceń produkcyjna, świeże prompty, mediana 4 pomiarów (A-B-C-C-B-A + powtórka A; `qw/e3d.jsonl`):

| prompt | bez spekulacji | MTP | MTP, hak pominięty | MTP − bez | **sam hak** (MTP − skip) | reszta (skip − bez) |
|---|---|---|---|---|---|---|
| 2k | 2235 ms | 2534 | 2469 | +299 (+13.4%) | **65 ms (2.6%)** | 234 ms |
| 8k | 7876 | 8375 | 8189 | +499 (+6.3%) | **186 ms (2.2%)** | 313 ms |
| 32k | 33619 | 35050 | 34282 | +1431 (+4.3%) | **768 ms (2.2%)** | 663 ms |

`LLAMA_MTP_HOOK_TIMING` dla 2k (`qw/e3-timing.server.log`): dekod MTP 26–34 ms plus kopia 4 ms na batch 2048 tokenów (na zimno 69 + 17 ms). Wypełnienie batcha to 0.03 ms.

Złożenie haka w graf celu oszczędza tylko narzut wokół obliczeń warstwy MTP (kopie, synchronizacja, osobny launch). Same obliczenia (1 warstwa z 65) zostają. **Górna granica zysku to 2.2–2.6% TTFT**, realnie ~1%. To mniej niż 15d zakładał (5–7%). Na 3090 część różnicy A0 → A1 mogła mieć inne źródło.

Skąd jest „reszta” (234 ms przy 2k)? `LLAMA_CKPT_TIMING=1` (`7369380bf`) pokazuje:
- każdy prompt robi 2 checkpointy (n − 4 − ub i n − 4);
- odczyt stanu rekurencyjnego celu trwa **~94 ms** (149.6 MiB, bez spekulacji) i **~104 ms** (170.3 MiB z MTP: +20.7 MiB oczekujących wierszy GDN z S4);
- część draftu to 0.2 ms, stan spekulacji 0 B.

Przy 2k checkpointy to ~190–210 ms TTFT w obu trybach. Z MTP dochodzą większy stan (+2 × 10 ms), synchronizacja w haku przed każdym batchem (`llama_get_embeddings_nextn`, tracimy nakładanie CPU/GPU) i wyjście h_nextn dla wszystkich wierszy. `[INFERENCE]` dokładny podział reszty na te składniki niezmierzony.

Próba naprawy: kopie stanu przez wspólny pinned bufor hosta (`LLAMA_STATE_PINNED`, `7f908b4dd`). **Bez efektu.** Replay omp, Qwen:
- obce zapytanie: 1981 → 1982 ms;
- start sesji: 1564 → 1671 ms;
- tura 2: 613 → 649 ms.

Odczyt nie jest ograniczony pasmem. `[INFERENCE]` ogranicza go opóźnienie: ~150 synchronicznych `ggml_backend_tensor_get` (48 warstw GDN × r/s/oczekujące wiersze). Kod cofnięty (`caefe1800`). Następny krok, który ma sens: jedna seria `tensor_get_async` z jedną synchronizacją. Zgadza się z tym `TODO` w `llama_io_write_host`. Potencjalnie −150…−200 ms na każdy prompt i każdą turę Qwena, z MTP i bez. Niezmierzone: GPU zatrzymane na prośbę użytkownika.

**Werdykt: złożenie haka przegrywa** (≤2.6%, nie implementowałem). Większy, tani cel: koszt checkpointów ~200 ms na prompt.

## E4. Audyt cache promptu agenta: skąd 7–10k przeliczenia na starcie sesji

**Co wysyła omp** (omp 18.10.4 przechwycony atrapą serwera `qw/capture_proxy.py`, CPU, `/v1/responses`):
- prompt systemowy jest **stały**: md5 `f3b2fed4`, 10 194 znaków, 11 narzędzi. Identyczny w różnych sesjach, katalogach i dniach (16.10 i 18.10);
- data i cwd siedzą w `<system-reminder>` w pierwszej wiadomości usera, więc nie psują prefiksu;
- w trybie `-p` (z sesją i z `-c` kontynuacją) omp nie wysyła do llama.cpp żadnych zapytań pobocznych (tytuł, streszczenie): jedno POST na turę;
- `prompt_cache_key` = id sesji; llama-server go ignoruje.

**Logi serwera** (`~/qwen-opt/logs/server-2026-10-15_*.log`): pełne przeliczenie 7290 tokenów występuje po `selected slot by LRU`. Wcześniej slot zajęło krótkie, obce zapytanie (np. `f_sim_best = 0.250, f_keep = 0.000`, 16 tokenów), a długa sesja trafiła do `--cache-ram`.

**Mechanizm** (`server-task.cpp:1824`): przy wyborze wpisu z `--cache-ram` wpis jest pomijany, jeśli `f_keep < 0.25`, czyli gdy nowy prompt współdzieli < 25% długości wpisu. Nowa sesja dzieli z długą sesją (np. 53k) tylko prompt systemowy (~7.3k = 14%), więc wpis jest pomijany i serwer liczy od zera. Bez obcego zapytania problemu nie ma: slot sam wybiera się przez LCP, a checkpoint z początku pierwszej wiadomości usera ratuje prefiks.

Replay (`qw/replay.py`: prawdziwy prompt systemowy i narzędzia omp, sesja S1 rośnie do 53k, potem obce zapytanie X, potem nowa sesja S2; `qw/e4.jsonl`):

| scenariusz | LFM: przeliczone tok. / wall | Qwen MTP: przeliczone tok. / wall |
|---|---|---|
| S2 bez obcego zapytania (stan dzisiejszy) | 502 / 554 ms | — |
| S2 po obcym zapytaniu, bez łatki | **7276 / 1357 ms** | **7341 / 8019 ms** |
| po obcym, `LLAMA_SERVER_CACHE_SHARE_MIN=1024` | 502 / 230 ms | 63 / 1612 ms |
| j.w. + `LLAMA_LFM2_MSG_SPANS=1` | 60 / 166 ms | (Qwen ma granice wiadomości natywnie) |

Łatka (`50c3a2f2a`, domyślnie wyłączona):
- **`LLAMA_SERVER_CACHE_SHARE_MIN=N`**: wpis pominięty regułą 25%, który ma ≥ N wspólnych tokenów prefiksu, jest przywracany jako **kopia**. Oryginał zostaje w cache, więc długa sesja nie ginie. Kopia jest używana tylko wtedy, gdy daje większe `f_sim` niż zwykły wybór. Serwer przywraca stan i wraca do checkpointu na wspólnym prefiksie.
- **`LLAMA_LFM2_MSG_SPANS=1`**: granice wiadomości dla szablonu LFM2 (jak `qwen3-coder`). Checkpoint powstaje na początku wiadomości usera, a nie tylko n − 4 − ub, więc nowa sesja przelicza 60 zamiast 502 tokenów.

Greedy md5 (świeże serwery, `qw/greedy/`):
- przełączniki wyłączone: c4708318 / 6f14e814 / 894e56e4 = bazy;
- `CACHE_SHARE_MIN=1024`: bez zmian (Qwen c4708318 / 6f14e814, LFM 894e56e4);
- `LFM2_MSG_SPANS=1`: LFM **407b8411**. Prompt jest teraz dzielony na batche na granicy wiadomości usera, a LFM reaguje na każdą zmianę podziału (E1: KLD ~0.06). To nie błąd, ale zmiana bitowa, więc przełącznik zostaje opcjonalny (zysk 64 ms).

Pozostały koszt Qwena po łatce (1612 ms wall przy 63 przeliczonych tokenach): ~1.1 s to przywrócenie kopii 2.3 GB stanu z RAM, a ~200 ms to checkpointy (E3).

Inne flagi:
- `--cache-ram 16384` wystarcza: wpis 53k Qwena to 2.3 GB, LFM 0.55 GB;
- `-cms` / `--ctx-checkpoints` nie są przyczyną;
- `--slot-prompt-similarity` (0.1) działa poprawnie.

Kto w praktyce zajmuje slot: inny klient (web UI, curl, benchmarki), druga sesja omp albo subagenci omp z innym promptem systemowym na tym samym serwerze `[INFERENCE: subagenci niesprawdzeni na lokalnym modelu]`.

**Werdykt: przyczyna = obce zapytanie + reguła `f_keep < 0.25`, nie zmienny prompt i nie checkpointy. Łatka wygrywa:** Qwen −80% (8.0 → 1.6 s), LFM −83% (1.36 → 0.23 s).

## E5. Cache sesji na SSD: projekt

**Pomiar istniejącego mechanizmu** (`--slot-save-path`, `POST /slots/0?action=save|restore`, checkpointy w pliku od #26004; page cache pliku zrzucony przed odczytem; `qw/e5.jsonl`):

| model | sesja | plik | zapis | odczyt | potem S2 (nowa sesja) | dla porównania: prefill 53k |
|---|---|---|---|---|---|---|
| LFM | 53 030 tok. | 553 MiB | 0.37 s | 0.53 s | 502 tok., 836 ms | ~12.2 s |
| Qwen MTP | 53 258 tok. | 2.28 GiB | 1.99 s | 2.51 s | 63 tok., 2224 ms | ~61.5 s |

Wariant A, **wrapper** (≈1 dzień, bez zmian w llama-server):
- proces obok serwera (albo `run-llm.sh`) robi `save` przy zmianie modelu, zatrzymaniu serwera i bezczynności > N min;
- nazwa pliku = hash (ścieżka + rozmiar + mtime modelu, typy KV, typ/rozmiar draftu MTP, szablon, pierwsze 4096 tokenów);
- przy starcie serwera albo przy nowym żądaniu wrapper tokenizuje prompt (`/apply-template` + `/tokenize`), szuka pliku z najdłuższym wspólnym prefiksem (indeks hashy bloków co 256 tokenów) i robi `restore` przed przekazaniem żądania;
- wady: jeden slot, ręczne zarządzanie budżetem dysku, restore blokuje serwer (2.5 s dla Qwena).

Wariant B, **natywny** (≈3–5 dni albo przejęcie upstreamu #28092 / wersji ngxsona):
- w `server_prompt_cache::update()` wpis usuwany z RAM jest zapisywany asynchronicznie (tmp + fdatasync + rename) do `~/.cache/llama/prompts/<model-id>/`;
- w `load()`, gdy w RAM nie ma wpisu z `f_sim` > progu, serwer szuka w indeksie dyskowym (łańcuch hashy bloków tokenów → plik) i czyta stan razem z checkpointami;
- budżet dysku i TTL jak w Lucebox (128 GB, 72 h);
- identyfikacja jak w wariancie A.

Zalecenie: najpierw wariant A, bo daje 95% zysku przy przełączaniu Qwen ↔ LFM (2.5 s zamiast ~60 s). Wariant B dopiero, gdy upstream się zdecyduje.

**Werdykt: wykonalne, bezstratne.** Mechanizm save/restore działa z checkpointami. Odczyt (2.5 s Qwen, 0.5 s LFM) jest 23–24× szybszy od prefillu. Wrappera nie implementowałem (zakres „design only”).

## Wyniki negatywne (do zapisania)
- Q6_K i Q8_0 bloku MTP zamiast IQ4_XS: −3.4% / −3% t/s (E2). Wynik z 2 seedów był mylący.
- Złożenie haka MTP w graf: maks. 2.2–2.6% TTFT, nie implementowane (E3).
- Pinned staging dla kopii stanu: 0% (E3; commit i revert).
- `LLAMA_LFM2_MSG_SPANS`: działa (−64 ms), ale zmienia greedy md5 LFM.

## Kontrola jakości
- Greedy md5 na świeżych serwerach: patrz E4. Przełączniki domyślnie wyłączone dają bazy.
- `test-backend-ops` nie dotyczy: żadna zmiana nie dotyka kerneli ani grafu (zmiany w serwerze, parserze szablonu i diagnostyce).
- KLD: E1, ubatch LFM.
- Zasady GPU: każdy blok pod `flock /tmp/gpu.lock flock /tmp/quiet.lock` (serwer start → pomiar → kill w jednym trzymaniu). Przebieg z 23:18–23:25 (LFM replay z pinned) odrzucony: ktoś odtworzył pliki blokad i dwa zadania szły równolegle.

## Do bazy wiedzy

1. **eksperymenty/2026-10-18-lfm-ubatch-2048.md** (nowa): pp4096 6108 → 7148 t/s (+17%), pp16384 5654 → 6680 (+18%), TTFT 8k 1471 → 1254 ms, 32k 6668 → 5692 ms, 512 bez zmian, VRAM +498 MiB (18591 → 19089 MiB przy ctx 131072 q8_0); 5060 Ti miało +56%. zrodlo: `~/wt/quickwins/qw/e1-ttft.jsonl`, log przebiegu llama-bench w tym raporcie.
2. **wiedza/lfm-czulosc-na-podzial-batcha.md** (nowa, status: do-sprawdzenia przyczyny): dowolne dwa rozmiary ubatcha dają KLD 0.055–0.068 (same top 88–89%), także KV f16 i upstream e60eff95f (bit w bit to samo); PPL 14.09–14.30 ± 0.45. Konsekwencje: zmiana `-ub`, granic batcha i checkpointów (np. `LLAMA_LFM2_MSG_SPANS`) zmienia greedy LFM. zrodlo: `qw/e1-kld*.txt`.
3. **latki/latki-spekulacji.md** (aktualizacja przy 0032/S2): IQ4_XS bloku MTP potwierdzony na żywo; natywny Q6_K 109.4 vs 113.2 t/s, 3.012 vs 3.063 tok/krok, 28.76 vs 28.14 ms/krok (5 seedów, ABBA); q8_0 103.1 vs 106.4 t/s (2 seedy); offline +0.45% z pilota 11 nie przenosi się. zrodlo: `qw/spec_sweep.jsonl` (e2s5-*), raport 16f E2.
4. **eksperymenty/2026-10-12-cache-promptu-i-a7.md** (aktualizacja) albo nowa **eksperymenty/2026-10-18-cache-promptu-agenta.md**: przyczyna przeliczeń 7.3k = obce zapytanie + `f_keep < 0.25` (`server-task.cpp:1824`); prompt systemowy omp stały (md5 f3b2fed4, data/cwd w wiadomości usera, brak zapytań pobocznych w `-p`); łatka `LLAMA_SERVER_CACHE_SHARE_MIN=1024`: Qwen 8019 → 1612 ms, LFM 1357 → 230 ms; `LLAMA_LFM2_MSG_SPANS=1` 166 ms, ale zmienia md5 LFM (407b8411). zrodlo: `qw/e4.jsonl`, commit `50c3a2f2a`.
5. **latki/wylaczniki-env.md** (aktualizacja, gałąź `quickwins`, poza `amd-opt`): `LLAMA_SERVER_CACHE_SHARE_MIN`, `LLAMA_LFM2_MSG_SPANS`, `LLAMA_MTP_HOOK_TIMING`, `LLAMA_MTP_HOOK_SKIP` (diagnostyka, psuje drafty), `LLAMA_CKPT_TIMING`.
6. **eksperymenty/2026-10-18-hak-mtp-i-checkpointy.md** (nowa): TTFT bez/MTP/MTP-skip 2235/2534/2469 (2k), 7876/8375/8189 (8k), 33619/35050/34282 (32k); hak 2.2–2.6%, więc 15d L4 („−5–7%”) zawyżone dla XTX; checkpoint stanu Qwena ~94 ms (149.6 MiB) / ~104 ms (170.3 MiB z MTP), 2 na prompt; pinned staging bez efektu (opóźnienie, nie pasmo); następny kandydat: wsadowe `tensor_get_async`. zrodlo: `qw/e3d.jsonl`, `qw/e3-timing.server.log`, commity `7369380bf`, `7f908b4dd`/`caefe1800`.
7. **produkt/cache-sesji-na-dysku.md** (nowa albo dopisek do 15d L3): slot save/restore z checkpointami działa: LFM 53k 553 MiB zapis 0.37 s / odczyt 0.53 s; Qwen 2.28 GiB 1.99 s / 2.51 s, potem start sesji 2.2 s zamiast ~61.5 s prefillu; projekt wrappera (A) vs natywny (B). zrodlo: `qw/e5.jsonl`.
8. **decyzje/** (do decyzji użytkownika): przyjąć do `run-llm.sh` `-b 2048 -ub 2048` dla LFM i `LLAMA_SERVER_CACHE_SHARE_MIN=1024` (po scaleniu `50c3a2f2a` do `amd-opt`); `MTP_TYPE` bez zmian.
9. **lekcje/**: (a) spec_sweep z 2 seedami potrafi odwrócić znak efektu ±3%, więc dla decyzji o typach kwantów co najmniej 5 seedów; (b) skrypt `sweep.sh` pisze `spec_sweep.jsonl` w cwd, a kopiowanie pliku z `~/qwen-opt` nadpisało wyniki rundy 1 E2 (liczby zachowane w logu przebiegu); (c) nigdy nie usuwać ani nie odtwarzać `/tmp/*.lock`: nowy inode łamie wzajemne wykluczanie.
