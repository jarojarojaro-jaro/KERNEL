---
typ: eksperyment
tags: [eksperymenty, kontekst, rx-7900-xtx, eco, telemetria]
aktualizacja: 2026-11-07
zrodlo: ~/qwen-opt/logs/server-2026-11-06_175345.log (print_timing, stop processing; 145 zadań, 17:53–18:58)
status: aktualne
---
# Prawdziwa sesja użytkownika w final mode: 120,8 t/s średnio do 139k kontekstu (2026-11-06)

**W prawdziwej pracy agentowej (omp, 145 zadań, 125 658 wygenerowanych tokenów, kontekst do 139 160) czat w final mode (eco 2200, ctx 262 144) pisał średnio 120,8 t/s, ważone tokenami. Do 128k utrzymywał 117–127 t/s, przy 128–160k spadał do 95,8 t/s.**

Pomiar bierze tylko liczby z logu serwera (czas generowania, tokeny, akceptacja MTP), bez treści rozmów. Zadania z mniej niż 32 wygenerowanymi tokenami są pominięte.

| Kontekst | Zadania | Tokeny | Decode ważone | Mediana | Maks. | Średnia akceptacja MTP |
|---|---:|---:|---:|---:|---:|---:|
| 0–32k | 57 | 47 163 | **127,2** | 123,6 | 171,8 | 0,57 |
| 32–64k | 27 | 21 038 | **121,6** | 121,5 | 216,7 | 0,58 |
| 64–96k | 29 | 26 559 | **116,6** | 125,3 | 205,1 | 0,65 |
| 96–128k | 19 | 23 178 | **123,1** | 128,9 | 219,5 | 0,66 |
| 128–160k | 11 | 7 720 | **95,8** | 98,3 | 120,8 | 0,56 |
| **Całość** | 143 | 125 658 | **120,8** | 122,7 | 219,5 | – |

Prefill w tej sesji, prompty ≥ 4000 tokenów:
- 795–929 t/s przy kontekście do 30k;
- 498,6 t/s dla 4 242 tokenów dopisanych przy 103k.

Z pomiaru syntetycznego (`ctx-262144.log`, [[2026-11-06-final-mode]]), przy 255k w kontekście:
- prefill **465,1 t/s**;
- decode **78,7 t/s**.

**Wnioski:**
- Długość kontekstu do ~128k waży mniej niż akceptacja MTP. Pasmo 96–128k ma wyższą akceptację (0,66) niż 0–32k (0,57) i porównywalną prędkość.
- Wyraźny spadek zaczyna się powyżej 128k, gdzie odczyt KV dominuje krok. Tam celuje pomysł „KV raz na weryfikację” ([[kv-raz-na-weryfikacje]], 66-SYNTEZA poz. 2).
- W porównaniu ze spec_sweep (118,3 t/s, syntetyczny zestaw 6 promptów) prawdziwa praca agentowa wychodzi średnio o 2% szybciej.

**Uwaga operacyjna (2026-11-07):**
- Serwer czatu nie wstał sam po restarcie maszyny (06.11 18:58 → 07.11 13:20). `run-llm.sh` nie ma usługi startowej.
- Eco 2200 wróciło z crontaba.
- Serwer uruchomiony ręcznie 07.11 ~16:40.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[2026-11-06-final-mode]]
- [[2026-11-06-profil-eco-2200]]
- [[REKORDY]]
- [[kv-raz-na-weryfikacje]]
- [[reactor-monitor]]
