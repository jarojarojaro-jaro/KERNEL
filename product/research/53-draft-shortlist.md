# 53. Shortlist w głowicy draftu MTP (E52b): low-rank po pełnym słowniku + dokładne przeliczenie

Data: 2026-10-21. Autor: podagent DraftShortlist. Branch `draft-shortlist` (`~/wt/draft-shortlist`, od `topka` 03f7fc7e1), skrypty w `53-skrypty/`, dane w `~/qwen-opt/draft-shortlist/`.
Stan: **kod gotowy i zbudowany, bramka recall NIE przeszła, GPU przerwane decyzją użytkownika (stop wszystkich jobów GPU) przed ABBA.** `[INFERENCE]` = wniosek bez pomiaru.

## TL;DR

1. **Implementacja (HIP, bez nowych kerneli):** `LLAMA_DRAFT_SHORTLIST=1` (domyślnie off), commit `ca7d71228`. W grafie łańcucha MTP (`qwen35.cpp`) każdy przebieg robi:
   - z̃ = A(B·hn), gdzie A to Q8_0 [128 × 248320] (33.8 MiB), a B to F32;
   - `ggml_top_k` (K = `LLAMA_DRAFT_SHORTLIST_K`, domyślnie 128);
   - `get_rows` K wierszy `output.weight` (Q6_K, już w VRAM), potem mul_mat, czyli dokładne logity;
   - `gumbel_max` z `ids` = tokeny shortlisty (szum kluczowany id tokenu, czyli ta sama semantyka co pełna głowica, gdy top-k 20 draftu leży w C);
   - embed następnego tokenu z kopii `token_embd` na GPU (682 MiB, zamiast 180 MiB wierszy 64k).
   VRAM netto ≈ +536 MiB `[INFERENCE z rozmiarów]`. Czynniki z pliku `LLAMA_DRAFT_SHORTLIST_FACTORS` (format `DSL1`, `sl_head.py export`).
2. **Bezstratność:** q′ = softmax po C (po filtrach) jest poprawnym rozkładem, a weryfikacja sprzężona (Gumbel celu, token = argmax celu) nie używa q, więc rozkład wyjścia się nie zmienia. GPU, s53b, PM4 produkcyjne:
   - **plain md5 `c4708318` OK przy on i off**;
   - **MTP T=0 off `6f14e814` OK, on `5f5b378f`**. To ta sama klasa zmian co głębokość/głowica draftu: weryfikacja nie jest bitexact względem wzoru akceptacji (raport 40 §3.3, 24q, 32b). Tekst jest spójny, rozjazd zaczyna się w znaku 725 (tabela markdown).
   - Akceptacja na 2 promptach bramki: off 0.558 / 0.280, on 0.551 / 0.285.
   - Uwaga: przy tym biegu `best.bin` podmieniałem w trakcie bramki, więc nie wiem, czy ramię on miało czynniki SVD, czy ridge λ=300 (K=1024). Do powtórzenia rano.
3. **Bramka CPU recall top-20 ≥ 99%: NIE.** Najlepsze czynniki r=128 w formie zamkniętej (bez SGD) na odłożonych stanach E0 (8000 stanów łańcucha, głębokości 1–4):

| czynniki | K | top-1 ∈ C | top-5 ⊂ C | top-20 ⊂ C | udział top-20 w C |
|---|---|---|---|---|---|
| SVD(W Σ^½) | 128 | 81.8% | 33.8% | 1.9% | 60.7% |
| SVD(W Σ^½) | 1024 | 96.8% | 77.7% | 30.4% | 89.0% |
| SVD(W Σ^½) | 2048 | 98.7% | 88.1% | 50.7% | 93.9% |
| ridge λ=300 (top-32) | 128 | 87.5% | 46.2% | 2.5% | 65.6% |
| ridge λ=300 | 1024 | **97.6%** | 82.7% | 40.8% | 91.1% |
| ridge λ=3000 | 1024 | 97.1% | 81.1% | 36.3% | 90.0% |

   EAGLE-4 podaje top-1 91.5% z SVD i 98.2% po treningu przy K=128. My mamy 81.8% z SVD (inna głowica i dane), więc retrieval r=128 bez treningu SGD jest daleko od bramki. Trening SGD (`sl_head.py fit`, forward KL + hinge) jest napisany, ale nie poszedł: `cpuheavy` daje 2 rdzenie, a 3000 kroków po 248k logitów to ~1 h+ przy wolnym quiet.lock.
4. **Nie zmierzone:** czas kroku draftu i ABBA E0/mvs/czat. Ryzyko `[INFERENCE]`: `ggml_top_k` po 248k idzie na HIP ścieżką radix (11 kerneli na przebieg, ×4). Może zjeść większość z −0.5 ms/krok. Jeśli ABBA pokaże koszt, następny krok to własny kernel GEMV+top-k (lokalne top-K w bloku + scalanie).

## 1. Co zrobione

| element | gdzie | stan |
|---|---|---|
| ładowanie czynników + kopia embd | `src/llama-model.cpp` `llama_model::setup_draft_shortlist()` (wołane z `set_draft_head_vocab`, idempotentne) | zbudowane |
| graf łańcucha | `src/models/qwen35.cpp` (gałąź `dsl`), `llama-context.cpp` (łańcuch dozwolony z `dsl_a` zamiast `draft_embd`) | zbudowane, działa na GPU (s53b) |
| ścieżka nie-łańcuchowa MTP | bez zmian (głowica 64k zostaje dla catch-up) | – |
| ekstrakcja stanów MTP | `sl_head.py dump-eval` (e0x, łańcuch K=5 po ścieżce zrealizowanej, jak `ext_head.py`), `dump-train` (ext_p1, teacher-forcing, 73k stanów, inne prompty niż E0) | zrobione |
| dokładne cele | `sl_head.py targets`: top-256 + logsumexp z pełnego `output.weight` (dequant Q6_K → f16, cache `mtp-train/cache/*.output_full.f16.npy`) | zrobione |
| czynniki | `init` (SVD W Σ^½, `fit --steps 0`), `ridge` (ważone LS per wiersz A przy stałym B; top-32 z wagą λ), `fit` (SGD, nie puszczony) | init + ridge zrobione |
| recall | `sl_head.py ksweep` | tabela wyżej |
| lustro sprzężone | `sl_head.py eval` → `ext_full/`, `ext_sl_*` → `40-skrypty/pa_offline.py` | **w toku** (`cpu4.sh`, wyniki w `~/qwen-opt/draft-shortlist/off_*.json`) |

Logika sprzężenia (sprawdzona w kodzie, `gumbel-max.cu`): remisy rozstrzyga klucz = id tokenu, nie kolumna, więc nieuporządkowany wynik `top_k` niczego nie zmienia. Filtry top-k/top-p/min-p liczone są po C. Gdy top-20 draftu ⊂ C, wynik jest identyczny z pełnym słownikiem. W przeciwnym razie zmienia się tylko propozycja.

## 2. Rano (dokładne kroki)

1. `~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/draft-shortlist/s53m.jobs`. Jeden plik:
   - `s53m-chk` (`s53d.sh`): (2) MTP on ×2 md5, (3) `LLAMA_GPU_VERIFY=0` z shortlistą, (4) `nt_gap.py`, czyli luka top-2 logitów celu w pierwszym różnym tokenie (off vs on);
   - ABBA A1 B1 B2 A2 (A = off, B = on; `p100_arm.sh` prose, mvs, prosethink, seedy 1,2; logi `~/qwen-opt/draft-shortlist/logs/`).
   Czynniki: `best.bin` = ridge λ=300, `best.k` = 1024 (czytane w chwili startu joba).
2. Podsumowanie: `prose_sum.py` na `logs/prose.jsonl`, `copy_bench.jsonl` (mvs).
3. **Reguła przyjęcia (Main, jako zmiana KONFIGU):**
   - plain md5 bez zmian (już OK);
   - nowe MTP md5 deterministyczne w 2 biegach; zapisać je tu jako nową referencję;
   - GV=0 == GV=1;
   - pierwszy różny token to near-tie (luka top-2 z `nt_gap.py`);
   - wyraźny zysk ABBA na prozie bez regresji mvs/czat.
   Dopiero wtedy wysłać do IntegTopka3.
4. Oczekiwanie `[INFERENCE]`: przy top-1 ∈ C 97.6% strata akceptacji draftu na tokenach w 64k może zjeść zysk z OOV (PL 6.7% tokenów). Sprawdzi to lustro (`off_ext_sl_ridge_l300_t32_K1024.json` vs `off_ext_full.json` vs `off_base64k.json`). Jeśli lustro pokaże tok/krok ≤ baza 64k, ABBA nie ma sensu przed treningiem SGD.
5. Jeśli recall jest za słaby: `cpuheavy --quiet … sl_head.py fit --steps 3000` (SGD od `init_r128.pt`, ~1–2 h na 2 rdzeniach) albo r=256 (A Q8_0 68 MiB, nadal ≪ 178 MiB głowicy 64k), potem `ksweep` i `export`.

## 3. Nie zrobione

- E52a (drafter EAGLE-4): nie zaczęte, zabrakło czasu i GPU.
- Pomiar czasu kroku draftu: brak, GPU zatrzymane.

## Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| metody | Shortlist draftu MTP na topce: `LLAMA_DRAFT_SHORTLIST=1` | Low-rank A(Bh) Q8_0 r=128 po 248k → `ggml_top_k` K → `get_rows` Q6_K `output.weight` → dokładne logity → `gumbel_max(ids=C)`. Embed z kopii `token_embd` na GPU (+536 MiB netto). Branch `draft-shortlist` ca7d71228 (raport 53) |
| wyniki-negatywne | Retrieval r=128 bez treningu nie trzyma top-20 | SVD(W Σ^½) K=128: top-1 81.8%, top-20 ⊂ C 1.9%. Ridge ważone top-32: K=1024 top-1 97.6%, top-20 40.8%. Bramka 99% wymaga SGD (forward KL) albo większego r (raport 53) |
| lekcje | Każda zmiana draftu zmienia md5 MTP T=0 na topce | Plain `c4708318` stały, MTP `6f14e814` → `5f5b378f` przy shortliście. Weryfikacja nie jest bitexact względem wzoru akceptacji (jak głębokość, 24q/40). Przyjęcie jako zmiana konfigu: deterministyczne ×2, GV0 == GV1, near-tie w pierwszej różnicy, ABBA (raport 53) |
| lekcje | `cpuheavy` = 2 rdzenie i quiet.lock | Długi łańcuch CPU pod jednym `cpuheavy --quiet` blokuje całą kolejkę GPU. Każdy krok osobno (`cpu4.sh`), ewaluacja w częściach `--part i/n` (raport 53) |
