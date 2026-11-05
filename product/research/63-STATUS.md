# Stan prac — stop 2026-11-05 14:2x UTC (na polecenie użytkownika: „zatrzymaj wszystkie testy na GPU”)

**GPU: brak jakichkolwiek testów, benchmarków i kolejek.** Na karcie działa wyłącznie serwer czatu użytkownika (`llama-topka`, Qwen3.8-27B-Uncensored, port 8080, kontekst 204 800) — zostawiony celowo, bo użytkownik z niego korzysta. Nie ruszamy go bez polecenia.

## 1. Research 63 (pakiet linków 2026-11-03)

| Raport | Stan | Co w środku |
|---|---|---|
| 63c-amd-rocm-llamacpp.md | **gotowy** (44 KB) | QSA (`pentaCoxian/Qwen-QSA-llama.cpp`) — 255k: decode 114,7 vs 40,6 t/s na 4090; RDNA-FAST (4 rzeczy, których topka nie ma: f16 WMMA prefill, chunked GDN, dynamiczny słownik draftu, MTP lean reserve); pułapka ROCm 10 (`maxSharedMemoryPerMultiprocessor` 128 KB psuje heurystyki FA); vLLM `ROCM_OCTAVE` 3-bit KV na gfx1100 (−1,1 GiB przy 262k); llama.cpp v0.9.0 = nightly b12110 (254 commity od pinu Enigmy, 582 od bazy topki); audyt KV q5_1 (Enigma bezpieczna); LithosAI „2116 t/s” = 6/czas kroku przy założonej akceptacji 75% |
| 63d-atencja-spec-kwant.md | **gotowy** (47 KB) | LSA nie dla nas (72,4× dotyczy 10M; przy 512k 0,68–1,03×); udział atencji: prefill 34% przy 128k, 51% przy 262k, decode 14–19% przy 128k; Strata KVA = −19…−22% TTFT ≥8k za 3–6 dni; MTP: najlepsze n zależy od karty (5090: 3, 4060: 1), a Enigma ma wpisane `--spec-draft-n-max 4`; Soft-MTP nic nie daje; FLy +5–8% na 27B; LFM2.5-24B-A2B-DSpark wyszedł (664 MB) i topka go obsługuje; Flash-Next NVFP4 nie dla 24 GB; REAP tylko dla klas 12–16 GB |
| 63a-silniki-lokalne.md | **brak** — agent padł na limicie API (429) po 17 min, w trakcie MegaCapybara/YASAKANI | klony i notatki w `~/src/research63` (strata, basalt, elpis, hyperqwen, mc-1.39/1.40, ninfer, tensorfold, ignis, mkyt, lms, tf-v1.*) |
| 63b-colibri-maya-delta.md | **brak** — 429 po 16 min | j.w. (`colibri`, `colibri_rel_top.txt`, `rel_*` JSON-y, `maya_rel_delta.txt`, `delta`) |
| 63e-metodologia-agenci.md | **brak** — agent w toku (5 podagentów), potem 429 | j.w. |

**Wniosek:** 2 z 5 raportów gotowe i to te z największą liczbą konkretów dla naszej karty; 3 do wznowienia (materiał źródłowy już pobrany na dysk, więc wznowienie nie wymaga sieci poza `git fetch`).

## 2. Prace na GPU — wstrzymane, nic nie w toku

- Kolejka nie działa (żaden `run-queue.sh`/`run-jobs.sh`/`flock /tmp/gpu.lock` nie jest uruchomiony).
- Pliki kolejki czekające na zgodę: `~/qwen-opt/queue/i43-int7.jobs` (int6 + pm4-teardown + 1024 rows + IQ4_XS ring), `i43*.jobs`, `x35-*.jobs`, `l45*.jobs`, `p37-*.jobs`, `p40*.jobs`, `q*.jobs`, `uw.jobs`, `next.jobs`.
- `topka-int7` (d5839abfb) zbudowany, **nieinstalowany**; produkcja `~/llama-topka` = f9b84bcfa.
- Ostatnie zmierzone wyniki bez zmian: Qwen3.8-27B UD-Q4_K_XL spec_sweep T=1 ≈ 115 t/s, LFM2.5-24B-A2B tg128 ≈ 296 t/s.

## 3. Aplikacja Enigma

- HEAD `52d1af9` (poprawka APU/iGPU/CPU), testy 129/129, binarki w `app/engine/dist/bin` (2026-10-25 00:04) serwowane z LAN.
- Otwarte: test użytkownika na Windows (czeka na feedback), E2E na XTX (wymaga zgody na GPU).

## Źródła
- 63c: RDNA-FAST `4426ca3`, Qwen-QSA-llama.cpp `fe08b16`, llama.cpp nightly b12110 (`cd959ba`), vLLM v0.33.0 PR #59774, cheaptokens (build 10791).
- 63d: arXiv 2610.42147, Prefrontal-AI/latent-sparse-attention `5ebea73`, Strata `9f7d977` docs/KVA.md, vLLM PR #53987 i #54448, arXiv 2511.22972, 2608.02438.
