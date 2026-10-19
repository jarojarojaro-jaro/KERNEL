# 20. Build „topka”: Qwen3.8-27B (main + Uncensored) z ogonem lookupu i współdzieleniem cache promptu (szybka ścieżka)

Data: 2026-10-19. Autor: podagent BuildTopka. Sprzęt: RX 7900 XTX (lokalnie, ROCm 10.0). Zakres skrócony decyzją użytkownika („fast track”, ~20–30 min): scalenie, build, kontrola poprawności i bezpieczeństwa, jeden szybki przebieg prędkości na model. Bez ABBA i bez strojenia n_max (patrz §5).

## 0. Najważniejsze
- Build: `~/wt/topka`, gałąź `topka` od `amd-opt` @ `f61994f58`:
  - `6c21a3e9f` = `6e12530cc` (ogon lookupu, `LLAMA_SPEC_LOOKUP`);
  - `22e2b0f55` = `50c3a2f2a` (`LLAMA_SERVER_CACHE_SHARE_MIN`).
  - Kontroler `586f1d596` pominięty na prośbę użytkownika. Konfliktów nie było (auto-merge `common/speculative.cpp`).
- Instalacja: `~/llama-topka` (`bin/` + `lib/`). Launcher: `~/qwen-opt/run-topka.sh qwen|uncensored`. Wywołuje `run-llm.sh` z tymi samymi flagami i portem 8080 i dokłada `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 GGML_HIP_PM4=0 DRAFT_N=4`.
- Poprawność:
  - greedy md5 z wyłączonymi przełącznikami: plain `c4708318`, MTP `6f14e814` = produkcja;
  - profil topka przy T=0 na 4 promptach code-edit (`mvs`): tekst identyczny z MTP-only (4/4 md5).
- Bezpieczeństwo: page faulty w `journalctl -k -b 0`: 31 przed, 31 po (wszystkie z wcześniejszych incydentów, raport 17). PM4 wyłączone.
- Prędkość (jeden przebieg, PM4 wył.):
  - code-edit `mvs` T=0: Qwen 166.1 → **396.9 t/s (×2.39)**, Uncensored **414.8 t/s**;
  - czat `spec_sweep` T=1, 1 seed: Qwen 105.1 t/s, Uncensored 106.9 t/s. Referencja produkcji bez PM4: 103.7 / 109.9 (`NOTES.md:375`). Przy jednym seedzie to szum tekstu T=1 (16b §4.4).

## 1. Polecenia dla użytkownika

```bash
# start (port 8080, jak produkcja; najpierw zatrzymać inny serwer na 8080)
~/qwen-opt/run-topka.sh qwen          # Qwen3.8-27B UD-Q4_K_XL
~/qwen-opt/run-topka.sh uncensored    # Qwen3.8-27B Uncensored Q4_K_M (VISION=1 dodaje mmproj, jak w run-llm.sh)
# w tle z logiem:
LOG=~/qwen-opt/logs/topka-8080.log setsid nohup ~/qwen-opt/run-topka.sh qwen > ~/qwen-opt/logs/topka-8080.launcher.log 2>&1 < /dev/null &

# stop
pkill -f 'llama-topka/bin/llama-server'

# powrót do produkcji (bez zmian, PM4 włączone jak dotąd)
pkill -f 'llama-topka/bin/llama-server'; ~/qwen-opt/run-llm.sh qwen

# wyłączenie pojedynczego przełącznika w topce
LLAMA_SPEC_LOOKUP=0 ~/qwen-opt/run-topka.sh qwen              # bez ogona lookupu
LLAMA_SERVER_CACHE_SHARE_MIN=0 ~/qwen-opt/run-topka.sh qwen   # bez współdzielenia cache promptu
```

Co się zmienia względem produkcji:
1. Ogon lookupu (16b). Gdy model przepisuje tekst z kontekstu (edycje plików, `str_replace`, cytaty), weryfikacja ma 16 tokenów zamiast 5, a przy T=0 kolejne bloki idą bez draftu MTP. Weryfikacja jest dokładna, więc tekst T=0 na zbadanych promptach się nie zmienia. Na czacie ogon prawie się nie włącza.
2. Współdzielenie cache promptu (16f E4). Nowa sesja agenta po obcym zapytaniu wznawia się z prefiksu promptu systemowego zamiast liczyć go od zera: 8.0 → 1.6 s (pomiar 16f, tu niepowtórzony).
3. PM4 wyłączone (raport 17: resety GPU). Czat jest ~4.7% wolniejszy niż produkcja z PM4 (108.8 → 103.7 t/s wg `NOTES.md:375`). To koszt bezpieczeństwa, nie topki.
4. Biblioteki z `~/llama-topka`. `~/llama-opt` i `run-llm.sh` są nietknięte.

## 2. Build
- `cmake -B build-hip -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DGGML_HIP_GRAPHS=ON -DGGML_HIP_NO_VMM=ON …`, czyli te same opcje co `~/qwen-opt/README.md:46-49`.
- `flock -s /tmp/quiet.lock nice -n 10 cmake --build build-hip -j6`, potem `cmake --install build-hip --prefix ~/llama-topka`.
- test-backend-ops pominięty: łatki zmieniają tylko `common/` i `tools/server/`, ops ggml są bez zmian (jak w 16b §6). Greedy md5 = produkcja potwierdza ścieżkę GPU.

## 3. Poprawność i bezpieczeństwo (`~/qwen-opt/topka/fast.sh`, jeden blok GPU)

| test | wynik | źródło |
|---|---|---|
| `greedy.sh ~/llama-topka`, przełączniki wył., PM4 wył. | plain `c4708318`, MTP `6f14e814` (= produkcja) | `~/qwen-opt/topka/greedy/off.{plain,mtp}.txt` |
| `mvs` T=0: MTP-only (build topka, przełączniki wył.) vs profil topka, Qwen | md5 4/4 identyczne: `d50689c9 530a871b 9f9b429d ea8a5a50` | `~/qwen-opt/topka/logs/copy_bench.jsonl` (`fast-qwen-mtponly`, `fast-qwen-topka`) |
| `mvs` T=0, profil topka, Uncensored | te same 4 md5 co Qwen MTP-only | j.w. (`fast-unc-topka`); osobnego MTP-only dla Uncensored nie robiłem [INFERENCE: tekst = MTP-only] |
| page faulty `journalctl -k -b 0` | 31 przed, 31 po | wyjście `fast.sh` |

Incydent: pierwszy przebieg zatrzymał gpu-guard o 02:39:41 UTC („fan 0 RPM at 93% busy”, hotspot 67 °C). Był to fałszywy alarm: firmware ma tryb zero-RPM. Main poprawił guard. Częściowe wyniki odrzucone, blok powtórzony w całości.

## 4. Szybki pomiar prędkości (jeden przebieg na model; PM4 wył.; świeży serwer przez `run-topka.sh`)

| model | obciążenie | wynik | tok/krok, ms/krok | odniesienie produkcji |
|---|---|---|---|---|
| Qwen | `mvs` code-edit T=0 (4 pliki, 1024 tok.) | **396.9 t/s** (391.1 / 394.0 / 405.8 / 399.8) | 14.03–14.42, 35.5–36.1 ms | MTP-only na tym samym buildzie: 166.1 t/s, 4.9 tok/krok, 29.5 ms (ten blok); 16b: 166.2 |
| Qwen | `spec_sweep` T=1, seed 1 | 105.1 t/s, 29.10 ms/krok | pl-proza 94.8, pl-tech 108.5, pl-kod 110.7, en-chat 88.1, en-tech 106.0, en-code 104.3 | prod. bez PM4 103.7 (`NOTES.md:375`), z PM4 109.0 (`REKORDY.md`) |
| Uncensored | `mvs` T=0 | **414.8 t/s** (406.1 / 414.9 / 421.1 / 414.6) | 14.03–14.42, 34.3–34.8 ms | brak pomiaru MTP-only w tym bloku |
| Uncensored | `spec_sweep` T=1, seed 1 | 106.9 t/s, 28.03 ms/krok | pl-proza 95.8, pl-tech 112.4, pl-kod 125.2, en-chat 88.0, en-tech 121.5, en-code 101.4 | prod. bez PM4 109.9 (`NOTES.md:375`), z PM4 115.5 |

Statystyki lookupu (`mvs`, Qwen): 1043 kroki, ogony 31 (314/337 tokenów przyjętych), łańcuchy 239 (3320/3562), host 2.5 ms łącznie.

VRAM po załadowaniu (ctx 204800): ~23.5 GiB (Qwen), ~22.9 GiB (Uncensored) wg `amd-smi`. Odczyt przed kolejnym ramieniem pokazywał jeszcze pamięć poprzedniego serwera, więc to liczby przybliżone. Porównania ABBA VRAM z produkcją nie robiłem.

Czat przy 1 seedzie nie rozstrzyga regresji. 16b §4.4 pokazało, że koszt kroku jest w szumie (±0.2%), a t/s przy T=1 skacze ±1% przez zmianę tekstu.

## 5. Nie zrobione w szybkiej ścieżce (kolejne kroki)
1. ABBA vs produkcja na świeżych serwerach (PM4 wył. w obu ramionach + jedno ramię produkcji z PM4), ≥5 seedów czatu T=1 i T=0, `copy`, `long` ~30k, TTFT nowej sesji (replay `interf`), pp4096, VRAM. Harness gotowy: `~/qwen-opt/topka/arm.sh` (ramiona `prod|prodpm4|topka|topkaoff`, benche `ttft,sweep,sweep0,mvs,mvs0,copy,long`).
2. Strojenie `DRAFT_N` 4/5/6 z ogonem (`DRAFT_N=5 ~/qwen-opt/run-topka.sh …`). Bez zmiany domyślnego 4 przed pomiarem.
3. Pomiar TTFT nowej sesji (`LLAMA_SERVER_CACHE_SHARE_MIN`) na tym buildzie. Dziś liczba pochodzi z 16f.
4. PM4 dopiero po zwalidowanej poprawce (Pm4Fix).

## Rekordy (nowe najlepsze)
- Uncensored, code-edit `mvs` T=0: **414.8 t/s** (2026-10-19, `run-topka.sh uncensored`, PM4 wył., `topka` @ `22e2b0f55`, `~/qwen-opt/topka/logs/copy_bench.jsonl` label `fast-unc-topka`). Nowa para (karta, model, obciążenie) w `REKORDY.md`.
- Qwen `mvs` T=0: 396.9 t/s przy PM4 wył. To nie bije rekordu 400.9 (16b, PM4 wł.), ale jest pierwszym pomiarem tej klasy bez PM4.

## Do bazy wiedzy

| folder | tytuł | treść | liczby (źródło) |
|---|---|---|---|
| `eksperymenty/` | 2026-10-19 build topka (`2026-10-19-build-topka.md`) | amd-opt + ogon lookupu (W16, tryb 3) + `CACHE_SHARE_MIN=1024`, PM4 wył.; launcher `run-topka.sh`; greedy = produkcja; tekst T=0 code-edit identyczny | mvs T=0 Qwen 166.1 → 396.9, Uncensored 414.8 t/s; md5 c4708318/6f14e814; page faulty 31 → 31 (`~/qwen-opt/topka/logs/copy_bench.jsonl`, `greedy/`) |
| `meta/` | `REKORDY.md`: wiersz Uncensored code-edit | nowy rekord 414.8 t/s (prod. nie, topka) | j.w. |
| `lekcje/` | aktualizacja guardu GPU (zero-RPM) | firmware XTX trzyma 0 RPM do ~70 °C; licznik „fan stoi przy obciążeniu” tylko przy hotspot ≥ 80 °C lub VRAM ≥ 82 °C | `~/qwen-opt/tools/gpu-guard.log` 02:39:41 |
| `repo/` | hub raportu 20 | gałąź `topka` (`6c21a3e9f`, `22e2b0f55`), `~/llama-topka`, `~/qwen-opt/run-topka.sh`, instrukcje start/stop/rollback | §1 tego raportu |
