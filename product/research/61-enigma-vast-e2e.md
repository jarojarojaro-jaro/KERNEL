# 61 — Enigma E2E na tanich kartach Vast (jak klient)

Data: 2026-10-24, 17:58–20:43 UTC. Aplikacja `app/engine` (binarka `dist/bin/enigma-linux-x64`, Bun `--compile`),
na każdej karcie **czysty kontener `ubuntu:24.04`** (bez CUDA w obrazie, sterownik z hosta), skopiowana tylko binarka +
klucz próbny (`--plan trial --days 3 --sub vast-test`, usuwany z instancji na końcu razem z `~/.enigma/config.json`).
Przebieg: `ENIGMA_NO_BROWSER=1 ./enigma-linux-x64 run --headless --license-file … --model auto --exit-when-ready` —
prawdziwe pobranie modelu z HF i oficjalnego llama.cpp **b11856** (CUDA 12.8 + cudart) z GitHuba. Na 3060 dodatkowo
pełna ścieżka UI przez tunel SSH (lokalny headless Chrome, `--disable-gpu`). Dane: `~/qwen-opt/cloud/results/enigma-<karta>-20261024/`
(`run*/headless.log`, `run*/state.json`, `.enigma/logs`, `.enigma/results`, `smi*.csv` = `nvidia-smi` co 2 s).

## Werdykt

- **Cały przebieg klienta działa na 4 klasach kart NVIDIA** (3060 12 GB, 4060 Ti 16 GB, 5060 Ti 16 GB, 3090 24 GB) w gołym
  Ubuntu 24.04: licencja → skan → rekomendacja (ctx ≥ 131 072) → prawdziwe pobranie modelu z HF i silnika llama.cpp
  b11856 z GitHuba → benchmark startowy → kandydaci → gotowe, `POST /v1/chat/completions` → HTTP 200 w 1.1–1.8 s.
  Ścieżka UI (3060) przeklikana do końca, z czatem na żywo.
- **Bez poprawek klient by nie przeszedł**: na pierwszej karcie silnik nie wstał (brak `libgomp`, exit 127 po pobraniu
  7 GB), a gdyby wstał — CUDA runtime leżał poza ścieżką bibliotek i ggml liczyłby po cichu na CPU (#1, #2). Poza tym
  fantomowe karty i zły RAM w kontenerach (#3, #4) oraz dwa błędy benchmarku, które zawyżały wynik spekulacji (#5, #6).
- **Pamięć z katalogu jest bezpieczna**: realne szczyty `nvidia-smi` 10.70 / 14.93 / 14.93 / 19.03 GiB przy planie
  10.74 / 15.38 / 15.31 / 23.19 GiB; żaden OOM. Na 3090 plan przeszacowany o ~4.2 GiB (przekazane do EngineCatalog).
- **Optymalizacja na oficjalnym silniku daje mało** (bez silnika Enigma dla CUDA): lookup n-gram +1.5% … +5.2% decode
  po uczciwym pomiarze; MTP na 3090 **+40.5% decode / +102% deep**, ale odrzucony regułą „prefill ≤ −5%” (−11.3%).
- **Wąskie gardło dla klienta = łącze**: model 6.9–16.4 GiB pobierał się 3–23 min (8–95 MB/s, zależnie od hosta),
  GitHub (silnik) 4–26 MB/s; benchmark + optymalizacja 6–9 min.
- **Koszt: $0.52** z limitu $3.00 (szczegóły niżej); na koniec 0 instancji (API).

## Błędy znalezione i naprawione

Commity `40a915d`, `703e965`, `7aa26d7` (+ `a7bf452` EngineCatalog: punkty pomiarowe z tych przebiegów w
`test/catalog.measured.json`, kod `mtp_no_memory`). Po każdej poprawce `bun test` (100 testów), `bun run check`,
`bun run build`, ponowny przebieg na karcie.

| # | Objaw na karcie | Przyczyna | Poprawka |
|---|---|---|---|
| 1 | **llama-server exit 127** po pobraniu 7 GB modelu (3060): `libgomp.so.1: cannot open shared object file` | oficjalne buildy Linux linkują OpenMP; minimalny Ubuntu (serwer, kontener) nie ma `libgomp1` | po instalacji silnika `ldd` po `llama-server` + `libggml*.so`; brakujący `libgomp.so.1` pobierany do katalogu silnika (przypięty conda-forge `libgomp-14.4.0`, sha256, ~0.6 MB, bez roota); inne braki = czytelny błąd z nazwą pakietu (`libvulkan1`, sterownik NVIDIA…). Sprawdzane **przed** pobraniem modelu (silnik idzie pierwszy) |
| 2 | `ldd libggml-cuda.so`: `libcudart.so.12`, `libcublas.so.12` not found | dwa archiwa (llama + cudart) rozpakowują się do sąsiednich katalogów; cudart poza ścieżką bibliotek → ggml **po cichu** ładuje tylko CPU | biblioteki `.so` z sąsiednich katalogów przenoszone obok `llama-server`; przed startem `llama-server --list-devices` (raz na binarkę) — brak urządzenia GPU dla backendu GPU = błąd zamiast cichego biegu na CPU |
| 3 | skan: 4 karty NVIDIA (1× RTX 3060 12 GB + 3× „PCI 10de:2487 0 GiB”) | sysfs w kontenerze pokazuje wszystkie karty hosta, `nvidia-smi` tylko naszą; parowanie po kolejności | `nvidia-smi --query-gpu=…,pci.bus_id`, parowanie po adresie PCI; karty, których sterownik nie widzi, pominięte |
| 4 | RAM 125.8 GiB przy limicie kontenera 60.4 GiB | `MemTotal` hosta | RAM = min(MemTotal, cgroup `memory.max` / v1 `limit_in_bytes`) |
| 5 | decode baseline→kandydat zawyżony (z XTX: 180 t/s na 27B) | decode = surowa kontynuacja korpusu z `ignore_eos` (model kopiuje/zapętla, lookup/MTP przyjmują wszystko) | decode = zadania czatu przez `/apply-template` (oryginalne opowiadanie PL + EN), deep = dokument 32k + pytanie, bez `ignore_eos`, liczone faktyczne tokeny, akceptacja draftów w logu; prefill dalej na surowym korpusie (zgłosił Main) |
| 6 | 4060 Ti, lookup: deep decode **17.2 → 64.5 t/s**, akceptacja 115/115 (100%) | llama-server trzyma cache n-gramów **między żądaniami**; powtórzenie 2× tego samego żądania odtwarza poprzednią odpowiedź (zmierzone ręcznie: to samo żądanie drugi raz 21 → 80 t/s, 204/256) | każde powtórzenie ma własne zadania (3 pary PL/EN, 3 pytania deep); test: żaden prompt decode się nie powtarza |
| 7 | ponowny `run --headless` używał starego skanu z `state.json` | `if (!state.hw) scan()` | skan i rekomendacja od nowa, gdy stan nie pochodzi z tego uruchomienia |
| 8 | Ctrl-C w headless → kod wyjścia 0 („gotowe”) | `process.exit(0)` w obsłudze sygnału | headless 130/143, aplikacja UI dalej 0 |
| 9 | pierwszy postęp: `1 KiB/s ETA 315949 s` (też przy wznowieniu: `ETA 627950832 s`) | pierwsza próbka liczy czas połączenia/haszowania prefiksu | pierwsza próbka tylko ustawia punkt odniesienia |
| 10 | wznowienie po błędzie haszowało 7 GB modelu od nowa (46 s) | sha256 z pobierania nie trafiał do `hashes.json` | digest zapisywany po zweryfikowanym pobraniu (testy pobierania mają własny `ENIGMA_HOME`) |
| 11 | UI: pod „Pobieranie” pasek `scan 100%` | `start()` nie czyścił postępu skanu | `progress: null` przy starcie |

Przetestowane przy okazji i działa: przerwanie pobierania modelu (SIGINT) i wznowienie od 14% przez `Range`
(3060, run1 → run2); weryfikacja sha256 w trakcie pobierania; ponowne użycie silnika i modelu.

## RTX 3060 12 GB (Vast 19911149, Nowy Jork)

Host: 4 karty (2× 3060 + 2× 4060 Ti; kontener widzi jedną), Xeon E5-2682 v4, limit kontenera 60.4 GiB RAM / ~15 vCPU,
sterownik 570.133.07, PCIe 3.0 x16, limit mocy 170 W, ~318 GB/s. $0.102/h, ruch $1.3/TB. Łącze w praktyce ~8–12 MB/s
(test `curl`: 8 równoległych zakresów ≈ 9 MB/s łącznie — host, nie aplikacja).

|faza|wynik|czas|
|---|---|---|
|licencja|`trial`, ważna do 2026-10-27|< 1 s|
|skan|RTX 3060 12 GiB sm_86 CUDA+Vulkan; RAM 60.4 GiB (po poprawce #3/#4; wcześniej 4 karty i 125.8 GiB)|0.1 s|
|rekomendacja|Gemma 4 12B UD-Q4_K_XL, ctx 262 144, KV q8_0, ub 1024, CUDA (2 alternatywy, 25 odrzuconych)|< 1 s|
|pobranie silnika|b11856 CUDA 12.8 + cudart, 0.72 GiB z GitHuba|2 min 36 s (~4.9 MB/s)|
|pobranie modelu|6.86 GiB z HF, sha256 OK; przerwane SIGINT przy 14% i wznowione (`Range`)|15 min (~8.2 MB/s)|
|benchmark startowy|**pierwszy przebieg: exit 127 (libgomp, #1)**; po poprawce OK, `ctxOk`|2 min 5 s|
|optymalizacja|ub-512 odrzucony (−1%), ub-2048 nie mieści się, MTP brak głowicy, enigma brak silnika sm_86, **lookup zostaje**|4 min 7 s|
|ready + `/v1`|`POST /v1/chat/completions` przez proxy → HTTP 200|1.4 s|
|UI (cały przebieg)|licencja → sprzęt → rekomendacja → pobieranie → baseline → optymalizacja → gotowe + czat na żywo|9 min 41 s (model z dysku, silnik pobrany od nowa)|

Pamięć: plan wagi 6.86 + KV 2.46 + compute 1.18 + narzut 0.24 = **10.74 GiB** z 11.78; `nvidia-smi` szczyt
**10 954 MiB = 10.70 GiB** (−0.04 GiB vs plan).

| | baseline (b11856) | najlepszy (lookup) | przyrost |
|---|---|---|---|
|prefill 4096|1187.3 t/s|1152.8 t/s|−2.9%|
|decode 256|33.4 t/s|38.9 t/s|+16.7% ⚠|
|deep 32 599 tok: prefill / decode|1003.6 / 27.4 t/s|997.4 / 28.5 t/s|−0.6% / +4.0%|

⚠ 3060 mierzona **przed** poprawką #6 (powtórzenia z tym samym żądaniem → odtwarzanie z cache n-gramów): przyrost
lookup jest zawyżony (akceptacja 271/384 = 71%). Baseline i ub-512 (bez spekulacji) są poprawne. Przebieg UI: 34.0 → 38.1
(+12.2%), ten sam błąd. Uczciwy pomiar tej samej metody na 4060 Ti/5060 Ti: +5.2% / +1.5%.

Zrzuty: `app/engine/screens/vast-3060-*.png` (01 licencja, 02 klucz OK, 03 sprzęt z prawdziwą kartą, 04 rekomendacja,
05-1…4 rosnący pasek pobierania silnika 20% → 82% → weryfikacja sha256 modelu, 06 benchmark startowy, 07 optymalizacja,
08 gotowe z tabelą baseline → teraz → %, 09 czat na żywo przez `/v1`). Oś czasu: `vast-3060-timeline.txt`.

## RTX 4060 Ti 16 GB (Vast 47543119, Nowy Jork)

EPYC 7532, limit 45.2 GiB RAM, sterownik 570.169, **PCIe gen4 x4**, 165 W, ~236 GB/s. $0.188/h, ruch $2.6/TB
(`--allow-paid-traffic`: koszt ruchu ~$0.035; tańszych hostów 4060 Ti z ruchem ≤ $2/TB nie było).

|faza|wynik|czas|
|---|---|---|
|licencja|OK|< 1 s|
|skan|RTX 4060 Ti 16 GiB sm_89, RAM 45.2 GiB|0.1 s|
|rekomendacja|Qwen3.8-27B UD-Q3_K_XL, ctx 131 072, KV q4_0, ub 1024 (3 alternatywy: Gemma 4 26B-A4B IQ4_XS 225k, LFM2.5-24B, gpt-oss-20b)|< 1 s|
|pobranie silnika|0.72 GiB + `libgomp` z conda-forge (poprawka #1 zadziałała: 5 s)|3 min 6 s|
|pobranie modelu|12.2 GiB z HF|22 min 45 s (~9.6 MB/s)|
|benchmark startowy|`engine devices: CUDA0: NVIDIA GeForce RTX 4060 Ti`, OK|2 min 51 s|
|optymalizacja|ub-512 0%, ub-2048 nie mieści się, MTP `no_mtp_head`→ teraz `mtp_no_memory` (głowica jest, kontekst draftu nie mieści się w 16 GB), **lookup zostaje** (inne md5)|5 min 40 s|
|ready + `/v1`|HTTP 200|1.8 s|

Pamięć: plan 11.73 + 2.40 + 0.98 + 0.27 = **15.38 GiB** z 15.71; szczyt **15 290 MiB = 14.93 GiB** (plan +0.45 GiB, bezpieczna
strona; EngineCatalog przeliczył narzut CUDA na tych punktach).

| | baseline | najlepszy (lookup) | przyrost |
|---|---|---|---|
|prefill 4096|938.6 t/s|936.7 t/s|−0.2%|
|decode 256|19.7 t/s|20.7 t/s|+5.2%|
|deep 32 642 tok: prefill / decode|798.6 / 17.1 t/s|801.2 / 17.0 t/s|+0.3% / −0.6%|

Pierwszy przebieg (run1, przed #6) pokazał deep decode 17.2 → **64.5 t/s** przy akceptacji 115/115 — stąd znaleziony
błąd #6; liczby wyżej to run2 po poprawce (ten sam model i silnik z dysku, skan od nowa).

## RTX 5060 Ti 16 GB (Vast 40594843, Tajwan)

EPYC 7402, limit 42.6 GiB RAM, sterownik 595.58.03, PCIe gen3 x8, 160 W, ~368 GB/s. $0.217/h, ruch darmowy.

|faza|wynik|czas|
|---|---|---|
|licencja|OK|< 1 s|
|skan|RTX 5060 Ti 15.9 GiB sm_120, RAM 42.6 GiB|0.1 s|
|rekomendacja|Qwen3.8-27B UD-Q3_K_XL, ctx 131 072, KV q4_0, ub 1024 (alternatywy: Gemma 4 26B-A4B 221k, Gemma 4 12B 262k f16, Qwen3.5-9B)|< 1 s|
|pobranie silnika|0.72 GiB + `libgomp`|28 s (~26 MB/s)|
|pobranie modelu|12.2 GiB z HF|6 min 44 s (~32 MB/s)|
|benchmark startowy|CUDA0 RTX 5060 Ti (Blackwell, build CUDA 12.8 działa), OK|2 min 26 s|
|optymalizacja|ub-512 −0.1%, ub-2048 nie mieści się, MTP `mtp_no_memory`, enigma brak silnika sm_120, **lookup zostaje** (+1.5%, inne md5)|4 min 51 s|
|ready + `/v1`|HTTP 200|1.4 s|

Pamięć: plan 11.73 + 2.40 + 0.98 + 0.20 = **15.31 GiB** z 15.61; szczyt **15 285 MiB = 14.93 GiB**.

| | baseline | najlepszy (lookup) | przyrost |
|---|---|---|---|
|prefill 4096|1010.8 t/s|1010.0 t/s|−0.1%|
|decode 256|27.9 t/s|28.3 t/s|+1.5%|
|deep 32 642 tok: prefill / decode|892.9 / 15.2 t/s|892.9 / 15.2 t/s|0% / −0.2%|

## RTX 3090 24 GB (Vast 56254418, Polska)

Threadripper PRO 5945WX, limit 53.9 GiB RAM, sterownik 580.173.02, PCIe gen4 x16, 350 W. $0.228/h, ruch ~darmowy.
Dwa wcześniejsze hosty 3090 (Ontario 57560109, Illinois 57560615) odrzucały klucz SSH (`Permission denied (publickey)`
mimo klucza przypiętego do instancji) — zniszczone po ~5 min każdy; `cloud/up.sh` dopisuje teraz w onstart nasz klucz
do `authorized_keys` i poprawia prawa (lekcja-vast-authorized-keys), trzeci host wpuścił od razu.

|faza|wynik|czas|
|---|---|---|
|licencja|OK|< 1 s|
|skan|RTX 3090 24 GiB sm_86, RAM 53.9 GiB|0.1 s|
|rekomendacja|Qwen3.8-27B UD-Q4_K_XL, ctx 131 072, KV q4_0, ub 1024 (alternatywy: Flint 40B-A2.5B NVFP4 204 800, Qwen3.6-35B-A3B 262 144, Gemma 4 26B-A4B Q6_K Vulkan)|< 1 s|
|pobranie silnika|0.72 GiB + `libgomp`|16 s|
|pobranie modelu|16.4 GiB z HF|2 min 58 s (~95 MB/s)|
|benchmark startowy|CUDA0 RTX 3090, OK|1 min 34 s|
|optymalizacja|ub-512 −0.5% (prefill −4.5%), ub-2048 nie mieści się, **MTP +40.5% decode, odrzucony: prefill −11.3%**, **lookup zostaje** (+2.4%)|4 min 38 s|
|ready + `/v1`|HTTP 200|1.1 s|

Pamięć: plan 15.69 + 2.64 + 4.54 + 0.32 = **23.19 GiB** z 23.57; szczyt baseline **19 486 MiB = 19.03 GiB**, MTP
21 348 MiB. Plan za wysoki o ~4.2 GiB (prawdopodobnie compute) — ten sam GGUF zmieściłby większy kontekst.

| | baseline | najlepszy (lookup) | przyrost | MTP (odrzucony) |
|---|---|---|---|---|
|prefill 4096|1523.9 t/s|1488.2 t/s|−2.3%|1352.4 (−11.3%)|
|decode 256|41.2 t/s|42.2 t/s|+2.4%|57.8 (+40.5%), akceptacja 627/1555|
|deep 32 642 tok: prefill / decode|1325.5 / 33.7 t/s|1324.3 / 35.5 t/s|−0.1% / +5.2%|1247.4 / 68.0 (+102%)|

## Koszt

| karta | instancja | czas | koszt |
|---|---|---|---|
|RTX 3060|57546121|17:58–18:56|$0.11|
|RTX 4060 Ti|57551755|18:58–19:57|$0.23|
|RTX 5060 Ti|57557617|20:03–20:21|$0.07|
|RTX 3090 (2 hosty bez SSH)|57560109, 57560615|~5 min każdy|$0.06|
|RTX 3090|57561120|20:30–20:43|$0.05|
|**razem**| | |**$0.52** (kredyt $11.07 → $10.56, po rozliczeniu)|

## Wnioski / do zrobienia (poza zakresem tej rundy)

- Reguła optymalizacji: MTP na 3090 (+40% decode, +102% deep) przegrywa z lookup +2.4% przez prefill −11.3%. Dla
  czatu prefill 1350 t/s to wciąż ~3 s na 4k promptu — warto rozważyć regułę ważoną (np. czas typowej odpowiedzi).
- Lookup „zostaje” przy +1.5% (5060 Ti) z innym md5 — w granicach szumu; próg minimalnego zysku (np. ≥ 3%) dla
  kandydatów zmieniających tekst uchroniłby przed przełączaniem dla zera.
- Pobieranie jednym połączeniem: na wolnych hostach (3060/4060 Ti) równoległe zakresy `curl` nie przyspieszały (łącze
  hosta ~100 Mb/s), więc nie zmieniane.
- 3060: przyrost lookup do powtórzenia po poprawce #6 (baseline poprawny).
