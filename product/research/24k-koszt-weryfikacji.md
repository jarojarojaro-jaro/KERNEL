# 24k: koszt szerokiej weryfikacji W16 vs MTP4 na XTX. Dekompozycja z istniejących danych, bez poprawki (2026-10-19)

**Werdykt.** Na `mvs` krok W16 kosztuje **35.61 ms** (T=0), a krok MTP4 **29.62 ms**. Różnica to +5.99 ms (+20%). Gdyby krok W16 kosztował tyle co MTP4, XTX dałby 401 → ~482 t/s (+20%), a 3090 +14% (44.35 vs 39.0 ms, 24e).
- Przy tym samym typie kroku poszerzenie z 5 do 16 wierszy kosztuje **≈ 9.4 ms**. Kroki łańcucha pomijają draft MTP (~3.4 ms), stąd mniejsza różnica średnia.
- **Około 70% tej kwoty to graf celu**: llama-bench V16 − V5 = 6.40 ms przy 2k i 7.13 ms przy 8k.
  - Wzrost grafu w profilu T2 (8 → 13 wierszy): matmul 64%, GDN+conv 23%, reszta 14%.
  - **Największa dźwignia to matmul 9–16 kolumn** (≥ 4.2 ms). Sam skok 8 → 9 kolumn (MMVQ → K4 WMMA) kosztuje 1.30 ms (graf T2) / 1.37 ms (E2 przy 2k).
- **Kopia logitów D2H:** 0.99 MB na wiersz (vocab 248320, f32), +0.045 ms/wiersz. Przy 5 → 16 wierszach daje to ~0.5 ms (5%).
- **Około 2.4 ms (26%) jest nierozdzielone** i leży poza llama-bench: głowa LM na 16 zamiast 5 wierszy, replay GDN ~14 zamiast ~4 przyjętych wierszy, catch-up MTP. Do rozdzielenia potrzebny jest profil obecnego buildu.
- **Dwie hipotezy z zadania odpadają:**
  - przebudowa grafu per szerokość: cache grafów per szerokość już działa (`common/speculative.cpp:3586-3588`), a gap hosta nie zmienia się między szerokościami;
  - budowa ogona i łańcucha na CPU: 6.8 µs/krok, czyli 0.02%.
- **Nic nie zostało zaimplementowane ani zmierzone na GPU.** Pauza GPU (Main, ~16:50 UTC) przerwała jedyny blok, profil rocprofv3 off/w16 obecnego buildu, zanim wziął lock. Nie ma commitu kodu i nic nie idzie do Pm4Fix2.

## Tabela 1. Koszt kroku na `mvs` (XTX, 4 pliki × 1024 tok.)
| krok | ms/krok | źródło |
|---|---|---|
| MTP4 (A, 5 wierszy) T=0 / T=1 | **29.62** / 29.62 | `~/qwen-opt/lookup/logs/e3_summary.txt:29-32,36-39` (średnia 4 promptów) |
| W8 sam ogon (C) / W8 + łańcuchy (B), T=0 | 33.25 / 29.96 → draft MTP ≈ 3.29 ms | `e3_summary.txt:29-32` |
| W16 T=0 (84.5% łańcuchów, 10.2% ogonów, 5.3% kroków 5-wierszowych; 283 kroki) | **35.61** | `e4_summary.txt:29-32`; mieszanka z `logs/e4-mvs-W5.lk.jsonl` (żądania 2–5) |
| W16 T=1 (91.8% ogonów, 8.2% kroków 5-wierszowych; 562 kroki) | 38.26 | `e4_summary.txt:36-39`; ten sam log (żądania 6–13) |
| → krok ogona W16 (draft + 16 wierszy) / krok łańcucha W16 (16 wierszy) | ≈ 39.0 / ≈ 35.6 | [INFERENCE] z mieszanek, przy założeniu, że krok 5-wierszowy = A |
| → koszt 5 → 16 wierszy przy tym samym typie kroku | **≈ 9.4** (ogon 39.0 − 29.62; łańcuch 35.6 − (29.62 − 3.46), gdzie draft 3.46 = 39.0 − 35.6) | [INFERENCE] |

## Tabela 2. Z czego składa się ≈ 9.4 ms i co z tym zrobić (ranking wg udziału)
| # | składnik | udział | dowód | poprawka bezstratna | status |
|---|---|---|---|---|---|
| 1 | matmul wag 9–16 kolumn (K4 WMMA small-N; poza llama-bench także głowa LM Q6_K 995 MiB na 16 wierszach) | **≥ 4.2 ms (≥ 45%)** + część pozycji 4 | T2 8 → 13 wierszy: matmul +1.633 z +2.566 ms grafu; Q5_K +0.94, IQ4_XS +0.35, Q4_K +0.31; skok 8 → 9 kolumn +0.87 matmul / +1.30 graf (`~/qwen-opt/vcost/t2_width.txt`); E2: 8 → 9 = 1.4 ms, dalej 0.37–0.8 ms/kol. | kernel 9–16 kolumn z tą samą kolejnością akumulacji per kolumna co K4, więc tekst = topka; cel: V16 ≈ V8 | nie zrobione (kernel, dni) |
| 2 | GDN + ssm_conv rosnące z wierszami, w tym replay przyjętych wierszy (`n_rs_seq` 15 vs 4) | ≥ 1.5 ms (≥ 16%) + część pozycji 4 | T2: gdn +0.34, conv +0.24 ms przy 8 → 13 wierszach; llama-bench nie ma replay (`n_rs_seq` = 0) | replay jako same aktualizacje rzędu 1, bez S·k i wyjścia (TensorFold update-v1.0.11 #7); kolejność operacji na stanie ta sama | nie zrobione; najpierw `LLAMA_GDN_REPLAY=0` vs 1 przy W16 |
| 3 | kopia logitów D2H (11 wierszy × 0.99 MB) | ~0.5 ms (5%) | T2: gap hosta po głowie 0.438 / 0.489 / 0.663 ms przy 8 / 9 / 13 wierszach = 0.045 ms/wiersz ≈ 22 GB/s | argmax na GPU dla greedy weryfikacji, wtedy kopiowane są tylko id; bitowo, o ile remisy rozstrzyga się tak jak CPU. Ścieżka `backend_sampling` istnieje, ale wyłącza się przy budżecie rozumowania (`common/sampling.cpp:585`) | nie zrobione |
| 4 | nierozdzielone poza llama-bench: głowa LM 5 → 16 wierszy, replay GDN, catch-up MTP (T2: +0.009 ms/wiersz) | ~2.4 ms (26%) | różnica 9.4 − 6.5 − 0.5 | – | wymaga profilu obecnego buildu |
| 5 | elementwise (rms_norm, GLU, FA, quantize) | ~0.9 ms (~10%) | T2: +0.35 ms przy 8 → 13 wierszach | fuzje | poza zakresem |
| 6 | przebudowa grafu per szerokość | 0 | cache per szerokość włączony przy lookupie; w T2 przerwy między kernelami w grafie celu (span − busy 2.75–2.80 ms) i gap hosta nie rosną z szerokością | – | nie dotyczy |
| 7 | budowa ogona/łańcucha na CPU | 6.8 µs/krok | `print_stats` w `e4-mvs-W5.server.log`: host 1.941 ms na 285 kroków | – | nie dotyczy |

Zastrzeżenie: proporcje 1/2/5 pochodzą z profilu T2 (`~/qwen-opt/t2/prof/new-n{7,8,12}`, build z 2026-10-13, MTP n = 7/8/12). Od tamtej pory doszły fuzje, kvq i replay GDN. Kierunek się zgadza, liczby trzeba potwierdzić profilem topki.

## CUDA (3090)
Analogia dotyczy pozycji 2 i 3 bez zmian (ten sam op GDN, ta sama kopia logitów po PCIe). Pozycja 1 jest na CUDA inna: weryfikacja powyżej 8 kolumn idzie przez MMQ, bo szerokie MMVQ działa tylko na RDNA3 (`~/wt/cuda-topka/ggml/src/ggml-cuda/mmvq.cu:1124-1128`). Wariant CUDA nie powstał, bo nie ma zmierzonej poprawki.

Sesja 3090 powinna zmierzyć:
1. `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 1,5,8,9,16 -n 0 -d 2048,8192` – krzywa V(w), czyli 16i E-C1, wciąż niezrobione;
2. `nsys` serwera off vs W16 na `mvs` (klasy: mmq vs mmvq, GDN, FA, gap po głowie);
3. udział gapu D2H przy 16 wierszach.

## Akcje
1. Po wznowieniu GPU (blok ≤ 15 min): `flock /tmp/gpu.lock flock /tmp/quiet.lock timeout 900 taskset -c 2-5 ~/qwen-opt/vcost/prof_block.sh off w16`, potem `~/qwen-opt/vcost/vc_trace.py ~/qwen-opt/vcost/prof/{off,w16}`.
   - Wynik: rozbicie kroku obecnego buildu i rozdzielenie pozycji 4.
   - Skrypt analizy sprawdziłem na śladzie T2. Skrypt GPU nie był uruchomiony.
2. Drugi blok: `EXTRA_ENV=LLAMA_GDN_REPLAY=0 OUT=prof-snap … prof_block.sh w16`, czyli replay vs snapshoty przy 16 wierszach.
3. Decyzja: jeśli matmul ≥ 50% kroku W16 ponad MTP4, zlecić kernel 9–16 kolumn bitowo zgodny z K4 (to nie OptMmvq2: ich zakres to n=1).
4. Pozycja 3 (argmax GPU, ~0.5 ms) to tania i bitowa poprawka, ale zysk wynosi ≤ 1.4% kroku, więc jest na końcu kolejki.

**Nie zrobione (pauza GPU):** profil obecnego buildu, wszystkie poprawki z env, ABBA mvs/copy/spec_sweep, md5, test-backend-ops, KLD, wariant CUDA. Worktree `~/wt/vcost` (gałąź `verify-cost`) został usunięty, bo nie zawierał zmian.

## Do bazy wiedzy
- `metody/koszt-szerokosci-weryfikacji.md` (aktualizacja):
  - w serwerze 5 → 16 wierszy kosztuje ≈ 9.4 ms/krok na `mvs`, więcej niż llama-bench V16 − V5 = 6.4 ms;
  - llama-bench wylicza głowę LM tylko dla ostatniego wiersza i nie ma replay GDN (`n_rs_seq` = 0), a nie liczy kopii logitów (0.99 MB/wiersz, 0.045 ms/wiersz na XTX);
  - krok W16 na `mvs` T=0 = 35.61 ms wobec MTP4 29.62 ms (+20%).
- `lekcje/` (nowa) „Koszt szerokiej weryfikacji to matmul, nie host”:
  - w profilu 8 → 13 wierszy matmul daje 64% wzrostu grafu, GDN+conv 23%;
  - budowa ogona lookupu kosztuje 6.8 µs/krok, cache grafów per szerokość już jest;
  - skok 8 → 9 kolumn (MMVQ → K4 WMMA) kosztuje 1.3–1.4 ms.
- `eksperymenty/` 2026-10-19 „24k koszt weryfikacji”: dekompozycja z danych e3/e4/E2/T2, poprawki niezmierzone (pauza GPU), skrypty `~/qwen-opt/vcost/` (`prof_block.sh`, `vc_client.py`, `vc_trace.py`, `t2_width.py` + `t2_width.txt`).
