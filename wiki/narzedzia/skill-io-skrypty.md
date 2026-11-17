---
typ: narzedzie
tags: [narzedzia, bench, sufit, kolejka, pamiec, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — scripts/bench.py:1-262, scripts/ceiling.py:1-51, scripts/queue.sh:1-14, scripts/mem.sh:1-31, examples/*.json; kopia ceiling.py i nasze wejście: ~/KERNEL/qwen-opt/skill-io/
status: aktualne
---
# Skrypty skill-io (bench.py, ceiling.py, queue.sh, mem.sh): co robią linia po linii i co bierzemy

**Cztery małe skrypty (Python stdlib + bash). Bierzemy wprost `ceiling.py` (już policzony nasz sufit) i z `bench.py` trzy pomysły: test igieł, flagę pętli i ledger. Kolejka i pomiar pamięci są u nas mocniejsze (`run-jobs.sh`, xtxbench), więc ich wersji nie przyjmujemy.**

**`bench.py`** (`:1-262`, dowolny serwer OpenAI):
- **Pomiar** (`:64-97`): `chat()` streamuje z `stream_options.include_usage`. TTFT = pierwszy kawałek treści lub rozumowania. Dekod = (completion_tokens − 1) ÷ (koniec − pierwszy token), czyli zegar klienta, ale tokeny z usage serwera.
- **Panel** (`:34-41`): 6 stałych promptów (kod LRU, TCP, opowiadanie 600 słów, B-tree vs LSM, bash backup, krach 1929).
- **Przebieg** (`:183-213`):
  - rozgrzewka;
  - TTFT krótkiego promptu (`max_tokens` 8);
  - c1: 6 × 512 tok., mediana (`:187-196`);
  - cN: N wątków naraz, suma tokenów ÷ ściana (`:198-206`);
  - prefill: unikalny dokument, `max_tokens` 1, prompt_tokens ÷ TTFT (`:208-213`).
- **`document()`** (`:107-119`): słowa z listy 20, 3 kody `[A-Z0-9]{8}` na głębokościach 1/4, 2/4, 3/4, nagłówek z `time_ns` (bez trafień w cache), pytanie o wszystkie kody.
- **Test długiego kontekstu** (`--long N`, `:215-222`): retrieval „k/3” = ile kodów jest w odpowiedzi.
- **`looping()`** (`:100-104`): > 50% powtórzonych 8-gramów słów → flaga LOOP.
- **`MemWatch`** (`:133-149`): co 3 s sonda zwracająca bajty, przy przekroczeniu limitu zatrzymuje serwer.
- **`on_ac`** (`:122-130`): odmawia pracy na baterii.
- **Zapis** (`:229-241`): każdy run jako linia `ledger.jsonl`; `show` drukuje tabelę.

**`ceiling.py`** (`:1-51`):
- `decode_ceiling` (`:20-25`):
  - eksperci jako suma po (k+1)·n wierszach;
  - weryfikacja = dense + głowica + eksperci + n·KV·ctx (× (k+1) z `kv_per_verify_row`);
  - draft = k·n·(warstwa + głowica);
  - wynik = pasmo ÷ ((weryfikacja + draft) ÷ (a·n)) · n.
- `prefill_ceiling` (`:28-31`): MFU · szczyt ÷ (2·aktywne + 4·warstwy·głowy·head_dim·L/2).
- **Braki:** stan rekurencyjny (dodajemy do `dense_gb`), drugie przejście KV przy N=5 (flaga). Nasz wynik: [[skill-io-sufity]].

**`queue.sh`** (`:1-14`): `flock` na `/tmp/inference-hillclimb.lock`, kolejno `bench.py run configs/<n>.json`, log `runs-<n>.log`; wzorzec `ctl cand ctl`.
- U nas mocniej: `run-jobs.sh` ma tickety FIFO, PM4 safety, sprawdza dziennik jądra po każdym jobie i zatrzymuje :8080.

**`mem.sh`** (`:1-31`): pamięć kontenera.
- NVIDIA: `nvidia-smi` per PID + cgroup anon.
- Pamięć zunifikowana: suma `drm-resident-*` z `/proc/<pid>/fdinfo`, deduplikowana po `drm-client-id`.
- U nas: XTX dyskretny, `mem_info_vram_used`; idea fdinfo przydatna w K-011 (ewikcja do GTT).

**Decyzje** (testy w [[KOLEJKA-TESTOW]]):
1. `ceiling.py` + JSON w `qwen-opt/skill-io/` przyjęte. Kolumna „sufit” w raportach.
2. `bench.py` bez zmian na XTX (port testowy) daje liczby 1:1 z ich kartami (3090 Qwen3.8-27B EXL3 3 bpw: 96,2 proza / 141,1 kod) → K-110.
3. Test igieł z `document()` → bramka długiego kontekstu w deployu (K-109).
4. `looping()` → flaga w `spec_sweep` i jakość-mini (zmiana harnessu, nie modelu).

## Wszystkie firmy (2026-11-17)

- **`ceiling.py` jest niezależny od firmy.** Nasz `karty.py` (`qwen-opt/skill-io/`) liczy go dla 34 kart: AMD, NVIDIA, Apple, Intel i Tenstorrent. Dane pochodzą ze specyfikacji producentów, a źródła są w `karty.json → _zrodla` ([[skill-io-sufity]]). Pamięć Apple i iGPU wpisana jako użyteczna (~75% / ~50–70% RAM).
- **`mem.sh` w trybie `unified`** (suma `drm-resident-*`) jest właściwy dla iGPU Intela pod Linuksem. Na Apple zamiast niego `vm_stat`/`ioreg` (`SKILL.md:94`). Tenstorrent: `tt-smi`.
- **`bench.py`** mówi tylko OpenAI API, więc ten sam plik działa na XTX i na 3090/5060 Ti w Vast. To podstawa porównań między firmami (K-110, K-113).
- **`mem.sh`** ma gałąź NVIDIA (`nvidia-smi` per PID). Na AMD dyskretnym `drm-resident` w fdinfo działa tak samo jak na iGPU, tylko liczy VRAM.

## Powiązane
- [[skill-io-przeglad]]
- [[skill-io-sufity]]
- [[spec-sweep]]
- [[xtxbench-szybki-ab]]
