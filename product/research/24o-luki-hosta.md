# 24o: luki hosta w kroku spekulacji MTP (XTX, topka), 2026-10-20

**Werdykt: trzy bezstratne przełączniki gotowe, bramka md5 zaliczona; pomiar prędkości ABBA w kolejce, jeszcze nieuruchomiony.**
- Gałąź `host-gap` (`~/wt/hostgap`, commit `49bc932a8` na topce `f2217bac7`), build `~/llama-hostgap`. Wszystko domyślnie wyłączone.
- „~4 ms bezczynności na krok” z rocprofv3 to w ~80% artefakt profilowania z `GGML_HIP_PM4=0`. W prawdziwej luce hosta (tryb PM4=1) koszt jest gdzie indziej, niż zakładało zadanie.
- Oczekiwany zysk trzech przełączników na czacie: **≈ −0.3 ms/krok (~+1.1%)**. To szacunek z trace'u: [INFERENCE] do czasu ABBA.

## Gdzie host traci czas
**Ślad PM4=0** (24k/24m, `vcost/prof-gv1/off`, `hostgap/gapclass.py`, 65 regularnych kroków mvs):
- wall 30.60 ms, busy 26.97 ms;
- granice kerneli w grafach: **959 × 3.41 µs = 3.27 ms**, czyli koszt AQL. PM4 robi z tego ~0.5–0.9 µs/granicę i nie jest to czas hosta;
- prawdziwe luki hosta: weryfikacja→catch-up **161 µs**, catch-up→draft **40 µs**, draft→weryfikacja **158 µs**;
- przekroczenie n_kv co 256 tokenów (rebuild + warmup + capture): **~19.5 ms na zdarzenie**, ≈0.26 ms/krok na mvs.

**Ślad produkcyjny PM4=1**: `LLAMA_HOSTGAP_TRACE`, job `hg-trace`, MTP-only, czat T=1 seed 1, 778 kroków. Średnie zawierają outliery granic requestów.

| pozycja | A (off) | B (wszystko on) | uwagi |
|---|---|---|---|
| koniec yield (handshake z workerem kolejki) | 46 + 31 + 23 = **~100 µs/krok** | **3.8 µs** | 3 yieldy/krok; wake z C2 |
| taśma catch-up: stream sync + latencja CP + GPU | 38 + 21 + 85 µs, synchronicznie | async HIP graph, 11–16 µs hosta | PM4 launch czeka na koniec taśmy |
| re-capture weryfikacji przy n_kv: instantiate/ExecUpdate | 2.9 ms średnio, **13.5 ms max** | 0 | mvs: 194 µs/krok |
| stream sync przed taśmą draft / catch-up | 35–49 µs | bez zmian | weryfikacja 4–6 µs; hipoteza: SDMA dla 80–100 KB wejść |
| host llama decode na graf (balloc…set_inputs…flush) | 160–240 µs × 3 grafy | bez zmian | największy pozostały koszt |
| GUARD: memcmp IB weryfikacji | 8–16 µs | bez zmian | decyzja bezpieczeństwa |

## Zmiany (bezstratne, env, domyślnie off)
1. `LLAMA_SERVER_YIELD_FAST=2`:
   - koniec yield nie budzi uśpionego workera;
   - catch-up MTP i draft idą bez yield;
   - serwer i kolejka, bez zmian numeryki.
2. `GGML_HIP_PM4_MIN_DISPATCH=16`: graf < 16 kerneli (catch-up, 12 kerneli) idzie asynchronicznym HIP graph zamiast taśmy. Host liczy próbkowanie i przygotowanie draftu, gdy GPU robi catch-up. Kolejność zapewnia stream sync przed taśmą draftu.
3. `GGML_HIP_PM4_LAZY_EXEC=1`: po capture z udaną taśmą bez `hipGraphInstantiate`/`ExecUpdate`. Instancja powstaje dopiero przy fallbacku (GUARD cooldown).
4. `LLAMA_HOSTGAP_TRACE=1|N` (diagnostyka): znaczniki server/MTP/llama/CUDA/PM4 i znaczniki czasu GPU taśm; parser `~/qwen-opt/hostgap/hg_parse.py`.

## Wyniki
- **Bramka (`hg-gate-qwen`, `hg-gate-lfm`):**
  - A: Qwen plain c4708318, MTP 6f14e814, LFM 894e56e4, czyli tyle co topka;
  - B (wszystkie przełączniki + trace): wyjście identyczne.
- **rocprofv3 PM4=0 (`hg-prof`):** nie rozstrzyga.
  - Ślady tej sesji mają nakładające się znaczniki czasu (ujemne luki, busy > span), więc klasyfikacja luk się nie udała.
  - Ms/krok klienta A 31.52 vs B 31.68 (1 przebieg, szum). Przy PM4=0 działa tylko przełącznik 1.
  - Kryterium „ślad pokazuje zmniejszenie bezczynności” spełnia ślad PM4=1 (tabela wyżej), nie rocprofv3.
- **ABBA:** w kolejce, nieuruchomione do końca sesji. Joby:
  - `hg-mvs` (mvs ABBA);
  - `hg-sweep1/2` (spec_sweep 5 seedów ABBA);
  - `hg-copy` (T=0/T=1, md5 per seed).
- Podsumowanie: `python3 ~/qwen-opt/hostgap/hg_summary.py`.

## Akcje
1. Odczytać `hg_summary.py` po jobach hg2. Wygrana = B szybsze w każdym ramieniu sweep/mvs i md5 copy 6/6.
2. Wtedy wdrożyć w topce:
   - `cd ~/wt/topka && git merge --ff-only host-gap`;
   - podmienić `~/llama-topka/bin` na `~/llama-hostgap/bin` (jak gv-install);
   - w `run-topka.sh` wyeksportować `LLAMA_SERVER_YIELD_FAST=2 GGML_HIP_PM4_MIN_DISPATCH=16 GGML_HIP_PM4_LAZY_EXEC=1`.
3. Następny krok (cel ≥100 t/s na prozie):
   - **host llama decode 0.5–0.7 ms/krok**. Potrzebny trace z medianami (wersja z medianami + `LLAMA_SYNC_SKIP` napisane i wycofane, niezbudowane; `synchronize` woła się 26–37×/krok).
   - Test env `GPU_FORCE_BLIT_COPY_SIZE=1024` (SDMA → blit dla wejść 80–100 KB i D2H h_nextn), szac. −60 µs/krok.
4. GUARD=1 kosztuje 8–16 µs/krok (memcmp IB). Zostaje, bo to decyzja użytkownika.

## Do bazy wiedzy
- `lekcje/` „Bezczynność z rocprofv3 przy PM4=0 to w 80% granice AQL”:
  - 959 × 3.4 µs = 3.3 ms z 3.9 ms;
  - realne luki hosta to ~0.36 ms (161/40/158 µs);
  - mierzyć w trybie PM4=1 przez `LLAMA_HOSTGAP_TRACE`.
- `lekcje/` „Synchroniczny launch taśmy PM4 zabija overlap”: catch-up (12 kerneli) jako taśma blokuje host. Krótkie grafy lepiej puścić jako async HIP graph.
- `metody/` „Koszt re-capture przy n_kv”: capture ~1–2 ms, instantiate/ExecUpdate do 13.5 ms, budowa taśmy ~3 ms, co 256 tokenów. Przy taśmie instancja HIP nie jest potrzebna (`GGML_HIP_PM4_LAZY_EXEC`).
- `lekcje/` „Handshake `yield_to_queue` kosztuje ~30–45 µs na yield” (wake workera z C2), 3× na krok.
- `eksperymenty/` 2026-10-20 „24o luki hosta”: gałąź `host-gap` `49bc932a8`, skrypty `~/qwen-opt/hostgap/` (`hg_md5.sh`, `hg_arm.sh`, `hg_ab.sh`, `hg_trace.sh`, `hg_prof.sh`, `hg_parse.py`, `hg_summary.py`, `gapclass.py`).
