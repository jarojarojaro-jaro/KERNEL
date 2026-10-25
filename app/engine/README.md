# Enigma — aplikacja

Pobierasz Enigmę → podpinasz subskrypcję (klucz licencji) → aplikacja skanuje sprzęt → wybiera najlepszy model
z największym kontekstem (**min. 131 072 tokenów**) → pobiera model i silnik → mierzy benchmark startowy (prefill,
decode, kontekst) na oficjalnym llama.cpp → uruchamia optymalizację → gotowe: lokalny endpoint zgodny z OpenAI
(`http://127.0.0.1:11525/v1`; gdy port zajęty — kolejny wolny z 20 następnych, adres wypisywany i w `ready.endpoint`).

Kontrakt (nazwy, typy, API, układ katalogów): [`CONTRACT.md`](CONTRACT.md). Stos: Bun (backend `Bun.serve`) +
Svelte 5/Vite (UI w przeglądarce na 127.0.0.1), jedna binarka z `bun build --compile`.

## Uruchomienie (dev)

```sh
export PATH=~/KERNEL/app/.tools:$PATH     # bun 1.4.3
bun install
bun run build:ui                          # UI → dist/ui (serwowane pod /)
bun src/server/main.ts                    # UI + API na 127.0.0.1:11525 (lub kolejnym wolnym), otwiera przeglądarkę
```

Bez UI (pełny przebieg, wypisuje postęp; kod wyjścia 0 = gotowe):

```sh
bun src/server/main.ts run --headless --license-file ~/.secrets/enigma-test-license.txt \
    [--model auto|<optionId>] [--min-ctx 131072] [--exit-when-ready]
```

Przy `ready` tryb headless wysyła kontrolne `POST /v1/chat/completions` przez proxy aplikacji i wypisuje
tabelę **baseline → teraz → przyrost %**. Bez `--exit-when-ready` serwer zostaje uruchomiony (Ctrl-C zatrzymuje
łagodnie).

Inne polecenia: `enigma license --key K | --file F`, `enigma scan [--raw]` (`--raw` = surowe dane skanu, do
nagrywania fixture'ów), `enigma --help`.

### Ścieżka deweloperska CPU (bez GPU)

`ENIGMA_DEV_CPU=1` to prawdziwa ścieżka CPU: skan raportuje `gpus=[]`, katalog planuje pod RAM, silnik = build CPU
llama.cpp. W labie (bez pobierania modeli):

```sh
ENIGMA_HOME=/tmp/enigma-e2e/home ENIGMA_MODELS_DIR=~/models \
ENIGMA_ENGINE_DIR_UPSTREAM_CPU=~/wt/upstream/build-cpu ENIGMA_DEV_CPU=1 ENIGMA_PORT=11540 \
ENIGMA_BENCH_PREFILL=512 ENIGMA_BENCH_DECODE=64 ENIGMA_BENCH_DEEP=2048 \
cpuheavy --quiet bun src/server/main.ts run --headless --license-file ~/.secrets/enigma-test-license.txt \
    --model qwen36-35b-a3b/UD-IQ4_XS/cpu --exit-when-ready
```

Na CPU katalog wybiera MoE z małą liczbą aktywnych parametrów (patrz niżej); w labie (62 GB DDR4-3200) czwórka to
Flint 40B-A2.5B, Qwen3.6-35B-A3B UD-IQ4_XS, LFM2.5-24B-A2B, Gemma 4 26B-A4B, a `--model` musi być jedną z nich (Qwen3.6
leży w `~/models/q36`). Przebieg skompilowaną binarką (`dist/bin/enigma-linux-x64`, `ENIGMA_BENCH_REPS=1`, ~8 min,
exit 0, 262 144 ctx, decode 9,1 t/s na 2 rdzeniach `cpuheavy`): [`test/e2e/cpu-dev-transcript.txt`](test/e2e/cpu-dev-transcript.txt).

Build CPU llama.cpp (raz): `cd ~/wt/upstream && cpuheavy --quiet cmake -S . -B build-cpu -DCMAKE_BUILD_TYPE=Release
-DGGML_HIP=OFF -DGGML_CUDA=OFF -DLLAMA_CURL=OFF -DLLAMA_USE_PREBUILT_UI=OFF && cpuheavy --quiet cmake --build
build-cpu -j2 --target llama-server llama-bench`.

### Komputery bez osobnej karty graficznej (APU, iGPU, sam CPU)

Skan rozróżnia `gpus[].kind`: `discrete` / `integrated` / `apple`. Grafika zintegrowana (AMD APU „Radeon(TM) Graphics”,
780M…, Intel UHD/Iris Xe/Arc Graphics) to nie karta: `vramGiB` = część RAM wydzielona przez BIOS (zwykle 0,5–2 GB),
`sharedGiB` = RAM, który może zmapować (Windows: ½ RAM, Linux: GTT z sysfs). `Hw.memory` = typ, szybkość i kanały RAM
(Windows `Win32_PhysicalMemory`, Linux `/run/udev/data/+dmi:id`, bez roota; potem EDAC; inaczej ostrożny domyślny dla
generacji CPU, oznaczony `source: 'default'`) i przepustowość = MT/s × 8 B × kanały.

Bez karty z własną pamięcią model żyje w RAM: budżet = RAM − zapas na system i programy (Windows ≥ 8 GB lub 25%,
Linux ≥ 6 GB lub 20%); grafika zintegrowana (Vulkan) dostaje najwyżej to, co może zmapować, procesor (CPU) — cały
budżet; ten sam model × kwant woli grafikę zintegrowaną. Prędkość pisania = η × przepustowość RAM / bajty na token
(aktywne wagi + KV), skalibrowana pomiarami na naszym CPU (Ryzen 7 5700X, DDR4-3200 ×2, `ramMeasured` w katalogu:
Qwen3.6-35B-A3B IQ4_XS 13,1 t/s, LFM2.5-24B Q5_K_M 23,0, Qwen3.8-27B Q4_K_XL 2,3); pokazywana jako zakres. Opcje
poniżej 8 t/s są odrzucane (`too_slow_on_this_hw`). W rankingu prędkość zmierzona na tej klasie sprzętu wygrywa z
szacowaną, chyba że szacowana opcja ma wynik wyższy o > 20%; plan z < 3% wolnego budżetu RAM jest obniżany
(`tight_memory`). Przykład: APU z 31 GB DDR4-3200 → Qwen3.6-35B-A3B UD-IQ4_XS, 262 144 ctx, CPU, 11–14 t/s.

## Build binarek

```sh
bun run build      # vite build → dist/ui, potem tools/build.ts
```

`tools/build.ts` generuje `src/server/enigma.gen.ts` (nie w repo: osadza pliki `dist/ui` i woła CLI) i kompiluje
`bun build --compile` dla `bun-linux-x64`, `bun-windows-x64`, `bun-darwin-arm64` do `dist/bin/enigma-<os>-<arch>`.
Jedna platforma: `bun tools/build.ts --target bun-linux-x64`.

## Testy

```sh
bun test           # hw (fixture'y z naszej maszyny + przykłady Windows/macOS/NVIDIA), licencja, pobieranie
                   # (lokalny Bun.serve, przerwane transfery, wznowienie), silniki (profile topki, zip), optymalizacja,
                   # API (Host/Origin), katalog
bun run check      # tsc --strict (backend)
bun run check:ui   # svelte-check (UI)
```

## Licencje (klucze subskrypcji)

Klucz `ENIGMA-<base64url(JSON)>.<base64url(podpis Ed25519)>`, weryfikacja offline kluczem publicznym wbudowanym
w `src/server/license.ts`. Klucz prywatny: `~/.secrets/enigma-license-ed25519.pem` (mode 600), **nigdy w repo**.

```sh
bun tools/license-issue.ts                       # pierwszy raz: tworzy parę kluczy, wypisuje klucz publiczny
bun tools/license-issue.ts --sub <konto> --plan pro|team|trial --days 30 --out ~/.secrets/<plik>.txt
```

Testowy klucz labu (30 dni): `~/.secrets/enigma-test-license.txt`. Bez ważnego klucza działa skan i rekomendacja;
pobieranie, benchmark i optymalizacja są zablokowane (API 403 z komunikatem).

## Silniki (`data/engines.json`)

- **Baseline** = oficjalne binarki llama.cpp, przypięte: `bun tools/engines-pin.ts [--release vX.Y.Z | --tag bNNNNN]`
  (tylko JSON z GitHub API; binarki są publikowane wyłącznie jako buildy `b*`, wydanie `v*` wskazuje swój build
  w `nightly-tag.txt`, np. v0.7.0 = b11669). Obecnie **b11856** (2026-10-24, najnowszy; od b11803 obsługuje Flint
  NVFP4, którego v0.7.0 jeszcze nie ma): Linux CPU/Vulkan/ROCm 10.0/CUDA 12.8 (+cudart), Windows CPU/Vulkan/CUDA 12.4
  (+cudart)/HIP (ROCm 10.0), macOS arm64 Metal; sha256 każdego pliku z API (gdy brak — liczony przy pierwszym
  pobraniu i zapisywany w `engines/<id>/digests.json`).
- **Enigma** = `enigma-rocm-gfx1100` (topka, RX 7900 XTX). Adres dystrybucji jeszcze nie istnieje → tylko lokalnie
  (`ENIGMA_ENGINE_DIR_ENIGMA_ROCM=~/llama-topka`); bez tego UI i log mówią wprost, że zoptymalizowanego silnika dla tej
  platformy nie ma, a przebieg idzie dalej na oficjalnym. Profile w `engines.json` odwzorowują
  `~/qwen-opt/run-topka.sh` + `run-llm.sh`: Qwen3.8 (MTP n=4 + słownik draft 64k, iq4_xs, `LLAMA_MTP_REQUANT_CACHE`,
  lookup 3/16, PM4 + guard, coupled, host-gap, ckpt/chat/safety, `--reasoning-effort low`, `--cache-ram 16384`),
  LFM2.5-24B (`-b/-ub 2048`, KV q8_0, lookup 0, bez coupled/host-gap). Nie odwzorowane: `--log-file` (log idzie
  ze stdout/stderr do `~/.enigma/logs`) i keep-awake BACO (na serwerze robi to `gpu-powercap.service`).
- Serwer modelu: `llama-server` na 127.0.0.1, losowy port, losowy `--api-key`; aplikacja wystawia go jako `/v1`
  (proxy ze streamingiem, bez klucza po stronie klienta). Zatrzymanie: czekanie na wolne `/slots`, **jeden** SIGTERM,
  45 s, dopiero potem SIGKILL.

## Benchmark i optymalizacja

Protokół z `CONTRACT.md`: prefill = prompt ~4096 tokenów ze stałego korpusu (`data/corpus.txt`, PL+EN, napisany na
potrzeby projektu, domena publiczna; generator `bun tools/corpus-gen.ts`), dokładna liczba tokenów przez `/tokenize`
serwera, `cache_prompt:false`; decode = 256 tokenów greedy (seed 1, bez `ignore_eos`; przy wcześniejszym końcu liczone
faktyczne tokeny) na zadaniach czatu (szablon modelu przez `/apply-template`: oryginalne opowiadanie PL + EN, md5
wszystkich tekstów); deep = korpus ~32k jako dokument + pytanie o własny tekst, 128 tokenów; 2× mediana. Każde
powtórzenie ma **własne** zadania: llama-server trzyma cache n-gramów między żądaniami, więc identyczne drugie żądanie
odtwarza poprzednią odpowiedź (zmierzone na 4060 Ti: 21 → 80 t/s, 204/256 draftów przyjętych). Ciągnięcie surowego
korpusu też zawyżało decode spekulacji (model kopiował tekst). Akceptacja draftów (`draft_n_accepted/draft_n`) idzie
do logu, gdy serwer ją podaje.
Kandydaci: silnik Enigma (jeśli jest), `-ub 512/1024/2048` (gdy mieści się w pamięci wg katalogu), MTP (model z głowicą
MTP), lookup n-gram (`--spec-default`). Zostaje najszybszy decode ze stratą prefill ≤ 5%; `sameOutput` = md5 decode
równe baseline. Wyniki: `~/.enigma/results/*.json`.

## Katalog danych i nadpisania

| | |
|---|---|
| `ENIGMA_HOME` | dane (domyślnie `~/.enigma`, Windows `%LOCALAPPDATA%\Enigma`): `config.json` (klucz licencji, 600), `state.json` (faza, wznawialna po restarcie), `models/`, `engines/`, `downloads/`, `logs/` (`enigma.log`, `server-*.log`), `results/`, `hashes.json` (cache sha256) |
| `ENIGMA_MODELS_DIR` | dodatkowy katalog z GGUF (2 poziomy w głąb): ta sama nazwa i rozmiar = bez pobierania; sha256 sprawdzane (na wątku roboczym, z postępem), gdy katalog je zna |
| `ENIGMA_ENGINE_DIR_<KEY>` | lokalny silnik zamiast pobierania: `UPSTREAM_CPU`, `UPSTREAM_VULKAN`, `UPSTREAM_ROCM`, `UPSTREAM_CUDA`, `UPSTREAM_METAL`, `ENIGMA_ROCM` |
| `ENIGMA_PORT` | preferowany port UI/API (domyślnie 11525, bo 11500 zajmuje omp); zajęty → kolejne 20 portów, faktyczny adres w logu i w `ready.endpoint` |
| `ENIGMA_NO_BROWSER=1` | nie otwieraj przeglądarki |
| `ENIGMA_DEV_CPU=1` | planuj tylko pod CPU (skan zwraca `gpus=[]`) |
| `ENIGMA_BENCH_PREFILL`, `_DECODE`, `_DEEP`, `_REPS` | rozmiary benchmarku (domyślnie 4096 / 256 / 32768 / 2) |
| `HF_ENDPOINT` | mirror Hugging Face (domyślnie `https://huggingface.co`; pliki z `/<repo>/resolve/main/<ścieżka>`) |

Pobieranie: wznawiane (`Range`), z postępem (prędkość, ETA), weryfikacją sha256, plikiem tymczasowym `.part`
i atomowym `rename`; anulowanie zostawia `.part` do wznowienia.
