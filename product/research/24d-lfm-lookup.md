# 24d. Lookup bez draftera dla LFM2.5 (LLAMA_SPEC_LOOKUP, bez MTP)

**Werdykt: NIE adoptować.** Zysk na copy/code-edit wynosi +17% (W8) zamiast oczekiwanych ×2.3–2.8. Tekst przy T=0 różni się od plain, również na buildzie CPU niezależnym od batcha, więc dokładności rollbacku nie udowodniłem. Kod jest w commicie `54d382932` (gałąź `~/wt/lfm-lookup`), opt-in, a wyłączony daje bez zmian md5 `894e56e4`. Profil LFM dla `run-topka.sh` z `-b/-ub 2048` i lookupem wyłączonym poszedł do Pm4Fix2.

## Co zbudowano
- `LLAMA_SPEC_LOOKUP=2|3`, gdy model nie ma typu spekulacji (LFM): lookup kontekstowy sam jest drafterem. Każdy krok z dopasowaniem ≥ `MMIN` weryfikuje do W−1 tokenów (pierwszy blok ma szerokość `LLAMA_SPEC_LOOKUP_W0`). Cel trzyma `n_rs_seq = W` snapshotów stanu conv (`lfm2.cpp`: slot s = stan s tokenów wstecz). Jest też graf weryfikacji per szerokość.
- **Naprawiony crash:** dla LFM2 przy `n_rs_seq > 0` rezerwacja grafu kończyła się `GGML_ASSERT(obj_new)`, bo budżet `graph_max_nodes` nie liczył zapisów snapshotów. Teraz dolicza `3·n_layer·n_rs_seq` węzłów (`src/llama-context.cpp`). To był powód, dla którego przerwane ramiona `c1-lk16`/`c1-lk8` padały.

## Wyniki (XTX, LFM2.5-24B-A2B Q5_K_M, KV q8_0, ub 2048, ABBA na świeżych serwerach)
Zestaw copy: 6 promptów × 512 tok., T=0 i T=1 × 3 seedy. Kolejność ramion: A W16 W8 W8 W16 A (`~/qwen-opt/lookup/lfm/logs/s1.out`).

| ramię | copy T=0 mediana t/s | copy T=1 mediana t/s | tok/krok (edit-2k / refactor, T=0) | ms/krok |
|---|---|---|---|---|
| A (wyłączony) | 288.2 / 285.9 | 288.1 / 284.6 | 1.00 / 1.00 | 3.43–3.55 |
| W16 | 312.4 / 313.8 (**+9%**) | 283.4 / 286.4 (−0.5%) | 1.97 / 6.32 | 4.8–11.9 |
| W8 | 334.7 / 341.8 (**+17%**) | 317.6 / 317.8 (**+11%**) | 1.73 / 1.55 | 4.0–5.1 |

- **Dlaczego nie ×2.4 jak na Qwenie:** LFM2.5 zawsze myśli, a `enable_thinking:false` nie działa w jego szablonie. Wszystkie 512 tokenów to reasoning (content pusty, md5 `d41d8cd9` we wszystkich ramionach), a nie kopia. Jedyny prompt, w którym reasoning cytuje kod (refactor-en), daje 6.32 tok/krok i 532.7 t/s (**×1.85**).
- **Weryfikacja jest droga:** krok W16 z 6.3 tok. trwa 11.9 ms wobec 3.5 ms plain (MoE ładuje więcej ekspertów). Akceptacja tokenów: W16 4459/7616 (59%), W8 3850/5101 (75%), więc W8 > W16 na LFM.

## Dokładność (T=0)
| test | wynik |
|---|---|
| `greedy.sh` LFM, lookup wyłączony | **894e56e4** = baza |
| `greedy.sh` LFM, `=3 W16` (GPU) | 2237ad17 ≠ baza |
| CPU z llamafile (batch-wariantny), domyślny `repeat_penalty` 1.05 z GGUF | 4/4 prompty różne, rozjazd przy tokenie 50–131 |
| jw., `repeat_penalty` 1.0 | refactor: 128/128 identycznych tokenów; strrep: rozjazd przy tokenie 66, gdzie przerwa top1/top2 plain = **0.024 nat** (2. najmniejsza ze 128) |
| logproby plain vs lookup (llamafile) | przed pierwszym batchem weryfikacji 0.000 (bit w bit); po nim 0.00–0.13. Sam prefill tego samego prefiksu różni się od plain o tyle samo (0.017/0.052) |
| CPU **bez** llamafile (`build-cpu-exact`, założenie: kolumny niezależne) | plain 9 promptów; W16: 2/2 zmierzone prompty **różne** (edit-2k-en, hashline-pl, rozjazd ~90 tok.). Bieg przerwany przez pauzę |
| `test-recurrent-state-rollback` na LFM (CPU) | split-replay: nmse 0.0077, max diff 2.68 na 1. pozycji po rollbacku. Nie rozstrzyga, bo kontekst referencyjny ma inny podział ubatchy, a LFM ma KLD ~0.06 przy każdej zmianie podziału (16f E1) |

Wniosek: na buildzie z llamafile wszystkie rozjazdy da się wytłumaczyć numeryką batcha. Kara 1.05 z GGUF dzieli logit ~25 na 1.05, czyli przesuwa go o ~1.2 nat, co zamienia przerwy rzędu 1 nat w remisy. Na buildzie niezależnym od batcha różnica nie powinna wystąpić. Albo ten build nie jest w pełni niezależny od batcha (niezweryfikowane), albo w ścieżce rollback/weryfikacji jest błąd. **Rozstrzygnięcie jest otwarte.**

## Adopcja / odrzucenie
- **Odrzucone dla topki:** lookup-alone dla LFM (`LLAMA_SPEC_LOOKUP=0` w profilu LFM). Kod zostaje jako opt-in.
- **Do integracji (Pm4Fix2):** profil `run-topka.sh lfm|lfm-uncensored` (`~/qwen-opt/lookup/lfm/run-topka-lfm.diff`): `none`, `-b/-ub 2048`, `CACHE_SHARE_MIN=1024`, `PM4=0`. Uzasadnienie ub 2048 (16f E1): pp +17%, TTFT −15%. KLD 2048 vs 512 = 0.068, tyle samo co między dowolnymi ub (1024: 0.067, 256: 0.055; A/A 0), PPL 14.11 vs 14.30 ±0.45. Działa na obecnym buildzie topki, bez nowego kodu.

## Nie zrobione (GPU wstrzymane przez użytkownika)
- ABBA mvs (1024 tok.) i czat `spec_sweep` ≥5 seedów (ms/krok) dla W8. Sesja `mvs:A,L8,L8,A sweep:A,L8,L8,A` została zabita w kolejce.
- lfm-uncensored; prompty z odpowiedzią poza reasoningiem (dłuższe `max_tokens`).
- Rozstrzygający test dokładności: plain z wymuszonym `n_rs_seq=16`, bez draftów, na `build-cpu-exact`. Oddziela to podział prefillu i niezależność od batcha od rollbacku. Do tego logproby W16 vs plain na tym buildzie.
- test-backend-ops: nie dotyczy, bo żaden op nie był zmieniany (tylko budżet węzłów grafu).

## Do bazy wiedzy
- LFM2 przy `n_rs_seq > 0` wymaga większego `graph_max_nodes`: snapshoty conv to 3 węzły × `n_rs_seq` na warstwę. Bez tego jest assert `obj_new` w `graph_reserve` (naprawione w `54d382932`).
- GGUF LFM2.5 ustawia `general.sampling.penalty_repeat = 1.05`, `temp 0.1`, `top_k 50`. „T=0” w serwerze wciąż stosuje karę 1.05, więc greedy LFM nie jest argmaxem logitów (21–33 z 256 tokenów to nie top-1). Porównania tekstu robić z `repeat_penalty: 1.0` albo pamiętać, że kara wzmacnia szum numeryczny.
- LFM2.5 zawsze myśli: copy-bench z 512 tok. mierzy reasoning, a nie kopię (content pusty).
- Lookup-alone na LFM: W8 > W16 (akceptacja 75% vs 59%; krok W16 to 11.9 ms vs 3.5 ms). Przyspieszenie: copy +17% (T=0), +11% (T=1); refactor ×1.85.
- Narzędzia: `~/qwen-opt/lookup/lfm/` (`gpu_ab.sh`, `arm_lfm.sh`, `cpu_exact*.sh`, `prefix_probe.sh`, `gap.py`, logi).
