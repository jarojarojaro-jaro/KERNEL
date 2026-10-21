# 24p. Sprzężone próbkowanie draftu (LLAMA_SPEC_COUPLED) na topce — pomiar T=1

Data: 2026-10-20. Autor: podagent OptCoupledT1. Kontynuacja raportu [16k](16k-sprzezone-probkowanie.md), w którym A/B przerwały resety PM4.
Kod: `~/wt/coupled2`, gałąź `coupled-topka` = topka `f2217bac7` + cherry-pick `760ee6990`, `3f25fc204` z `opt-coupled` (bez konfliktów; binarki z `3a0f3ada3`, HEAD `7cdc0121b` = pusty commit z liczbami). Binarki: `~/qwen-opt/coupled2/inst` (rbuild). Skrypty i wiersze per żądanie: `~/qwen-opt/coupled2/` (`c2_arm.sh`, `c2_gate.sh`, `csweep.py`, `analyze.py`, `logs/rows.jsonl`).

## 0. Werdykt

**Wygrana, mała: +3.5% t/s przy T=1 (CI95 +1.8…+5.3%), bezstratnie.** To porównanie z wyłącznikiem off w tej samej binarce, przy konfiguracji topki. Wobec zainstalowanej topki wychodzi ≈ +2.5…+3.5%, bo build off mógł być o 0.5–1% wolniejszy, a nie zostało to rozstrzygnięte (§3). Próg kill z 16k (+2%) przekroczony średnią; dolna granica CI leży tuż pod nim.
- Czysty efekt sprzężenia draftu (tryb 1 vs kontrola 2, ten sam rozkład tekstów, ten sam cel): **tok/krok +3.7% [+2.1, +5.3]**, koszt opu Gumbel **+0.66% ms/krok** → netto t/s +3.0% [+1.4, +4.7].
- T=0 bez zmian (sampler greedy, sprzężenie się nie włącza): md5 identyczne przy wyłączniku off i on.
- **Zgodność z LLAMA_GPU_VERIFY (top-128 na GPU): pełna, bez fallbacku.** Sampler sprzężony zależy tylko od zbioru (id, logit) po łańcuchu filtrów, a nie od kolejności kandydatów; szybka ścieżka top-k z kandydatów top-m daje ten sam zbiór co pełny wiersz (24m). Potwierdzone: tryb 1 przy T=1 z GV=0 i GV=1 daje **12/12 identycznych tekstów**. Ogon lookup (tryb 3, W16) działa bez zmian: tokeny lookup są weryfikowane dopasowaniem prefiksu jak każdy draft.
- T=0.7 nie zmierzone: limit użytkownika ≤ 30 min GPU na pomiar szybkości (zostało T=1). 16k: przy T=0.7 tok/krok +2.6% (1 vs 2).

## 1. Bramka poprawności (`~/qwen-opt/queue/logs/c2-gate.log`, `c2-gv0.log`, `c2-gv1.log`)

| test | wynik |
|---|---|
| `test-backend-ops -o GUMBEL_MAX -b ROCm0` | 152/152 |
| `test-coupled-sampling 200000` (test 16k: chi² rozkładu, niezależność, spekulacja == plain token w token, op CPU == łańcuch) | all passed; 0/20000 różnic w każdej parze; op 0/2000 |
| greedy md5 (PM4 WA=2, GV=1), off / `LLAMA_SPEC_COUPLED=1` | Qwen plain `c4708318` / `c4708318`, MTP `6f14e814` / `6f14e814`, LFM `894e56e4` / `894e56e4` |
| T=1, tryb 1, GV=0 vs GV=1 (6 promptów × seedy 1,2, 400 tok.) | 12/12 identycznych tekstów, tok/krok 3.170 = 3.170 |

Bezstratność = ten sam rozkład wyjścia co zwykłe próbkowanie (dowód 16k §2; test chi² powyżej). Przy T=1 tekst nie może być md5-identyczny z samplerem `dist` (inny strumień losowy przy tym samym seedzie).

## 2. Pomiar T=1 (`~/qwen-opt/queue/logs/c2-t1*.log`, `analyze.py`)

Konfiguracja topki (MTP n=4, lookup 3 W16, PM4 WA=2 + GUARD, HSA_USE_SVM=0, GV=1), świeży serwer na ramię, spec_sweep 6 promptów × 400 tok. Kolejność 0 1 2 (seedy 1–8) | 2 1 0 (seedy 9–16): ABBA, nowe seedy w drugim przejściu (lekcja: stały seed = ten sam tekst). 96 żądań na tryb. Tryby: 0 off, 1 cel + draft MTP sprzężone, 2 cel sprzężony + draft greedy (kontrola).

| tryb | t/s (pula) | tok/krok | ms/krok | mediana promptów t/s (przejście 1 / 2) |
|---|---|---|---|---|
| 0 off (topka) | 107.6 | 3.037 | 28.23 | 113.4 / 110.6 |
| 1 sprzężone | **111.4** | **3.111** | 27.94 | 115.6 / 118.0 |
| 2 kontrola | 108.1 | 3.001 | 27.76 | 112.9 / 116.7 |

Porównania sparowane po (prompt, seed), bootstrap 95%:

| para | t/s | tok/krok | ms/krok |
|---|---|---|---|
| 1 vs 0 | **+3.50% [+1.80, +5.28]** | +2.43% [+0.68, +4.25] | −1.03% [−1.46, −0.66] |
| 1 vs 2 | +2.99% [+1.41, +4.68] | **+3.66% [+2.07, +5.31]** | +0.66% [+0.49, +0.83] |
| 2 vs 0 | +0.50% [−1.24, +2.22] | −1.19% [−3.01, +0.59] | −1.68% [−2.08, −1.31] |

- Oba przejścia osobno dają ten sam znak: 1 vs 0 t/s +2.8% i +4.2%, 1 vs 2 tok/krok +4.1% i +3.2%.
- **ms/krok:** sam sprzężony cel (2 vs 0, ten sam drafter greedy) jest o 1.7% tańszy na krok. [INFERENCE: inne teksty (inny strumień RNG) → inna mieszanka szerokości weryfikacji/ogonów lookup; albo tańszy sampler celu niż `dist`; nie rozdzielone.] Op Gumbel w łańcuchu MTP kosztuje +0.66% (1 vs 2; 16k: +0.4%).
- Tryb 1 vs 2: identyczne teksty 1/96 (400 tok., w 16k 30/80 przy 96 tok.) — rozjazd numeryczny batcha weryfikacji, jak przy T=0; rozkład ten sam, więc porównanie nieobciążone.

## 3. Regresja przebudowy (wyłącznik off vs zainstalowana topka)

`c2-reg.jobs` (`~/qwen-opt/queue/logs/c2x-*.log`): T=1, seedy 1–8, tryb 0, zainstalowana topka, a potem coupled2 z wyłącznikiem off. **Teksty identyczne 48/48** (ta sama numeryka; także z ramieniem `c2-t1a-m0`).

| build | t/s (pula) | tok/krok | ms/krok |
|---|---|---|---|
| `~/llama-topka` | 108.6 | 3.055 | 28.14 |
| coupled2, off (c2x) | 107.5 | 3.055 | 28.41 (+0.96%) |
| coupled2, off (c2-t1a-m0, 2 h wcześniej) | 108.0 | 3.055 | 28.29 (+0.53%) |

- Przy wyłączniku off graf MTP jest bitowo ten sam co w topce (`smpl_prm` = nullptr → `ggml_argmax`). Na hoście dochodzi tylko sprawdzenie końca łańcucha samplera.
- Różnica +0.5…+1% pochodzi więc albo z innego binarium (rbuild vs build topki), albo z szumu jednej pary A-B bez odwrócenia kolejności. [INFERENCE] Nie rozstrzygnięte w limicie 10 min.
- Nawet w najgorszym przypadku, gdyby cały +1% był kosztem, zysk netto wobec dzisiejszej topki wynosi ≈ +2.5% przy T=1.

## 4. Działania

- **Zalecenie: zainstalować i włączyć `LLAMA_SPEC_COUPLED=1` w topce** (tylko T>0, czyli czat; T=0 i edycje kodu bez zmian).
- Uwaga produktowa: przy tym samym seedzie teksty T>0 będą inne niż dziś. Rozkład jest ten sam. Seed daje odtąd ten sam tekst ze spekulacją i bez niej (z dokładnością do numeryki batcha).
- Instalacja (kolejka GPU, wzór `gv-install`). Jeśli topka poszła w międzyczasie do przodu, zamiast `--ff-only` trzeba zrobić `git merge coupled-topka` i przebudować:
  `c2-install|120|~|cd ~/wt/topka && git merge --ff-only coupled-topka && rm -rf ~/llama-topka.f2217bac7 && mv ~/llama-topka ~/llama-topka.f2217bac7 && mkdir -p ~/llama-topka/lib && cp -a ~/qwen-opt/coupled2/inst/bin ~/llama-topka/bin && git log --oneline -1`
- `run-topka.sh`: dopisać `export LLAMA_SPEC_COUPLED=${LLAMA_SPEC_COUPLED:-1}`, tylko w gałęzi qwen/uncensored. Dla LFM nic nie zmienia, bo nie ma MTP; sampler sprzężony i tak daje ten sam rozkład.
- Po instalacji jedna kontrola (≤ 10 min): greedy md5 (`c4708318`/`6f14e814`) oraz spec_sweep T=1 na seedach 1–8, porównany z `c2-t1a-m1` (111.0 t/s, 3.108 tok/krok).
- Niezrobione (limit GPU): T=0.7 na topce i ABBA build-vs-build z §3. `LLAMA_SPEC_COUPLED_DT` rozstrzygnięty offline przez OptProseTree (raport 24s, lustro MTP, 17.7k startów prozy, T=1, chain-4; względem DT=1.0): DT 0.7 +0.26% tok/krok (szum), 1.3 −0.6%, 1.6 −1.5%. **Zostaje DT=1.** Tamże sprzężony vs greedy +4.2% tok/krok offline, zgodnie z naszym +3.7% na GPU.

## 5. Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| `eksperymenty/` | `2026-10-20-sprzezone-t1-topka.md` | E-X4 domknięte na topce: 16 seedów × 6 promptów/tryb, ABBA; T=1 sprzężone vs off **+3.5% t/s [+1.8, +5.3]**, tok/krok 3.037 → 3.111; czysty efekt draftu (1 vs 2) tok/krok +3.7% [+2.1, +5.3], op Gumbel +0.66% ms/krok. md5 T=0 bez zmian (`c4708318`/`6f14e814`/`894e56e4`), test 16k all passed, GV=0 == GV=1 12/12 przy T=1. Źródło: raport 24p, `~/qwen-opt/coupled2/logs/rows.jsonl`. |
| `metody/` | aktualizacja `sprzezone-probkowanie-draftu.md` | Status: zmierzone na topce, +3.5% przy T=1; zgodne z GPU verify top-m (sampler zależy od zbioru kandydatów, nie od kolejności) i ogonem lookup; T=0.7 niezmierzone na topce. |
| `lekcje/` | aktualizacja `lekcja-ustalony-seed-to-nie-powtorzenie.md` | Działający schemat: ABBA z NOWYMI seedami w drugim przejściu + ramię kontrolne + bootstrap po (prompt, seed) dało CI ±1.7% przy 96 żądaniach/tryb w ~26 min GPU. |
