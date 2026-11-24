---
typ: ekosystem
tags: [ekosystem, spekulacja, moe, metodologia]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/strata/README.md:1-34,194; ~/KERNEL/qwen-opt/research/strata/issues.md:1-20; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:82; ~/KERNEL/product/research/21d-kv-na-dysku.md:76-88; ~/KERNEL/product/research/21g-nowe-silniki.md:218-272,291-297; ~/KERNEL/product/research/21n-strata-020-gyro.md:7-10; ~/KERNEL/product/research/63a-silniki-lokalne.md:29-32,69-169; ~/KERNEL/product/research/66a-strata-maya.md:23-116,141-204,273-298,355-365
status: aktualne
---
# Strata (Niko1221/Strata)

**Silnik C++/CUDA/HIP pod jeden model MoE z offloadem (HEAD `a0116b27`, 2026-10-12, tag v0.1.43.1), studiowany jako wzór metodologii autora.**

Repo: 1892 commity w 19 dni, 49 tagów. Model docelowy: Qwen3.8-Flash-Next (125B MoE, ok. 6B aktywnych, 48 warstw: 36 GDN + 12 sparse attention, 512 ekspertów top-10, tablica n-gram 28.8 GB, głowica MTP). Otwarty PR #2231: bitowo identyczne poprawki decode na RX 7900 XTX, +11.7% chat / +14.3% agent decode, KL 0.0000. Standard autora: zmiana domyślnej ścieżki musi dać bajtowo identyczne wyjście na czterech modelach i przejść A/B prędkości; wszystko, co zmienia bity, jest opt-in. Dla nas: chunked GDN (WY) dał −39% na gfx1100 (#888, odrzucone) oraz odkrycie, że warstwa MTP w UD-Q4_K_XL jest cała w Q6_K (≈ 335 MiB). Raporty cząstkowe: `timeline`, `kernels`, `spec-host`, `prefill`, `method`, `issues`, `update-v0.1.44`.

Session files (v0.1.45, 21d): tmp + fsync + rename, fingerprint modelu i konfiguracji, O_DIRECT, tylko najgłębszy checkpoint; „0.2.0” nie istnieje ([[raport-21d-kv-na-dysku]]).

v0.1.44.1–0.1.45 (21g, 2026-10-19): ścieżka Qwen3.6-35B-A3B, dekod R9700 83.2 → 117.8 t/s (llama.cpp 82), bitowo; fuzje = nasze 0049/0051/0053/0056; `--parallel` vs `llama-server -np` ×1.14 / 1.61 / 1.53 / 1.56 dla N = 1 / 2 / 4 / 8; domyślny chunk 4096 zmienia bity (KL 0.004); Flash-Next 125B na XTX + 96 GB RAM ≈ 80 t/s, prefill 1810 t/s przy 98K (#2938); PR #3064 [[bariera-lds-rdna3]].

0.2.0-beta (`3d1fb480`, 21n): 55% zmian to aplikacja, silnik 6%; dla gfx1100 nic nowego; Gyro-S to plik dla 32 GB ([[raport-21n-strata-gyro]]).

0.2.1–0.2.2 (`011c9e60`, 10-21, silnik 0.1.47; R57b): Gyro na Arc/Mac, trellis NVIDIA +17% (3060) / P100 +30%, pula CPU per NUMA, role kart Main/Helper/Off; silnik ~11% zmian od 0.2.0-beta, dla gfx1100 nic do prędkości. Lekcja `86d10ed8`: flaga hosta podnoszona po `graphLaunch` = deadlock na HIP (8/41 → 0/46). Domyślne wagi = ISTA-DASLab GSQ-RCO GGUF. XTX (społeczność): IQ3_S 62.3 t/s, prefill 128K 926 → 1687 z tabelą hipBLASLt. „Qwen3.8-Flash” = hostowane API, lokalnie tylko Flash-Next ([R57b](../../product/research/57b-strata-qwen38-flash.md)).

0.2.3–0.2.11 (klon `9f7d977d`, 2026-11-05, silnik 0.1.48 → 0.1.57; R63a): dla gfx1100 i gęstego 27B nic; paczka „Linux RX 7900” tylko zbudowana, nieuruchomiona. KVA (0.2.7) to stratny prefill przez stan późnych warstw ([[strata-kva]], odrzucony). PR #4366: ogłoszone +39% prefillu to ciepły vs zimny przebieg, realnie +2–6%. 0.2.10: DFlash2 domyślny (wygrywa na greedy kodzie, nie przy T=1), silnik TP „wszystkie karty”; „128K na 8 GB” = drabina degradacji mierzona na dużej karcie ograniczonej do 8 GB (wzór UX dla Enigmy). Synteza: [[raport-63-synteza]].

0.2.12 (tag `123bad4a`, 2026-11-07, silnik 0.1.58; R66a): „newly trained DFlash2 drafter” to fine-tune drafteru Inco AI dla Flash-Next (603 M, na wyjściach kwantów UD-Q4_K_XL i UD-IQ4_XS-v31): +11.4% przyjętych draftów, +2.1…5.0% t/s; z 27B nieużywalny (inne tapy i format `.pack`). Tweet vs release notes: Mac +10.3…12.7%, nie +31%; Strix Halo ×1.77–2.12 to prefill 4K z fuzowanych kerneli F16 WMMA (stratne, tylko Windows), „prawie 3× na Linuksie” nie było mierzone; „3× low RAM” to poprawka błędu liczenia wolnej pamięci. Pułapka UMA: kopie z niezarejestrowanej areny hosta szły ~0.5 GB/s. Dla Enigmy: próg draftu rośnie z kosztem wiersza weryfikacji ([[prog-draftu-od-kosztu-wiersza]]). Flash-Next na XTX: tylko HIP (bez Vulkana), DFlash2 na gfx1100 niezmierzony, reguły RAM ISTA vs Unsloth w [[qwen38-flash-next]]. Synteza: [[raport-66-synteza]].

## Aktualizacja 2026-11-19 (v0.2.16, silniki 0.1.62; Telegram „gpu”)

- **Własny kod silnika na wszystkich platformach** (NVIDIA, AMD, Intel Arc, Mac, DGX Spark), bez ggml i bez kerneli macierzowych llama.cpp. Te same tokeny co w 0.2.15 na 10 promptach: R9700 10/10, P100 10/10, M5 Max 10/10, Arc A750 9/9. Nowych liczb prędkości dla gfx1100 i gęstego 27B brak.
- **Lekcja (wszystkie firmy):** w 0.2.15 na Apple M1–M4 z UD-Q4_K_XL liczyła się tylko ćwiartka kolumn w części warstw (160 z 640), **a tekst dalej brzmiał płynnie**. KL pierwszego tokena 0,303 → 0,0068 po poprawce; top-1 różny w 3/6 → 1/6 promptów. Krótka odpowiedź tego nie pokazuje. Potrzebna jest bramka KL/md5 na każdej architekturze, nie „czy brzmi dobrze”. Dla nas: Enigma na nowych kartach zawsze z bramką KLD.
- **Blackwell, CUDA 12:** pierwsza odpowiedź 173,0 s → 0,34 s po dodaniu natywnego kodu dla karty (wcześniej kompilacja JIT z PTX). Enigma ma natywne `sm_120` (CUDA 12.8), ale to warto sprawdzić przy każdym nowym wydaniu.
- Prefill starszych NVIDIA: V100 26k tokenów 17 464 → 15 068 ms (−13,7%), 2080 Ti ×1,088 vs 0.1.58.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Wiersz o 0.2.12–0.2.13 zamknęliśmy zdaniem „3060 prefill 3×, DFlash2 per karta; nic dla XTX”. Strata to jednak bezpośredni konkurent aplikacji Enigma: aplikacja desktopowa (Tauri, `app/desktop`), serwer hosta (`app/host`), aktualizacja z ustawień albo `strata update`, konfiguracja modelu na Intel Arc (Control v0.1.59.1, notatki v0.2.13 w `product/research/watch/2026-11-14.md:213-217`). Klon `~/research/engines/Strata` @ `3142b66`:
- **Domyślne ustawienia per architektura (`docs/DETAILS.md:1399-1412`, `engine/include/strata/core/nv_defaults.hpp`):** dla sm_86, sm_60, sm_120, sm_121 osobny zestaw przełączników, każdy bitowo zgodny (bramka 10 promptów + exact_pp 4K/20K), ustawiany przed odczytem przełączników; przełącznik ustawiony przez użytkownika wygrywa; cały zestaw wyłącza jedna zmienna (`STRATA_SM86_PERF=0`). Przełączniki, które nie dały zysku albo dały mieszany, są wypisane z nazwy.
- **U nas:** Enigma ma tylko `mtp.nMaxByArch` dla długości draftu (`app/engine/data/engines.json:600`, K-129). Nasze bezstratne przełączniki XTX żyją w `run-topka.sh` i nie trafiają do użytkowników: silnik `enigma-rocm-gfx1100` ma `distribution: local` (`engines.json:264-272`). Strata dowozi swoje usprawnienia każdemu posiadaczowi danej karty, my tylko sobie.
- **Telemetria (`docs/DEVELOPER_INTEGRATION_HANDOFF.md:214-216`):** brakujący sygnał to „unavailable”, nigdy zero ani zgadnięta wartość; scenariusz akceptacji: mieszane krótkie i długie żądania, anulowanie w trakcie, restart, a liczniki muszą się zgadzać (żadne żądanie nie znika między stanami). To samo, czego brakuje Enigmie po `ready` ([[inference-stack]], [[superfluid]]).
- **12 GB:** prefill 3060 2k 87 → 264 t/s to wynik dla karty, którą Enigma obsługuje dziś tylko Bonsai; jeśli Strata stanie się domyślnym wyborem posiadaczy 12 GB, to przez takie liczby.
- Co bierzemy: (1) w `engines.json` zestaw bezstratnych przełączników per architektura z jednym wyłącznikiem i bramką md5, zaczynając od tego, co już zmierzyliśmy na 3090/5060 Ti; (2) wysłać silnik gfx1100 do użytkowników (punkt 6 w [[inference-stack]]); (3) zasada „brak sygnału = niedostępny” w UI Enigmy.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): warstwa aplikacji
Wiersze rejestru o 0.2.0 („55% to aplikacja, dla gfx1100 nic”) czytały aplikację jako szum. To dokładnie warstwa, w której Enigma przegrywa ([[inference-stack]]). Klon `~/research/engines/Strata` @ `3142b66`:
- **Skala:** serwer hosta to 103 moduły, ~14,2 tys. linii (`app/host/server/*.mjs`) i 386 plików testów (`app/host/tests`); Enigma `app/engine/src/server` to ~2,7 tys. linii i 12 plików testów.
- **Powrót do poprzedniego silnika:** aktualizacja zostawia poprzednią wersję, a „rollback” to jedna operacja w aplikacji (`app/host/server/native-control.mjs:101-102,624,684`: „The previous engine is back. Your models and settings are unchanged.”). Enigma nie ma ani aktualizacji silnika, ani powrotu.
- **Kontrola konfiguracji przed startem:** plik `strata-<model>.json` sprawdzany przed uruchomieniem, błąd z numerem linii i podpowiedzią najbliższej nazwy przy literówce (`run-config-check.mjs:1-10`); „literówka nigdy nie jest startem, który po prostu pada”.
- **Kolejka zapytań z anulowaniem** (`request-queue.mjs:1-20`) i jeden automat stanów dla monitora: faza, t/s, pamięć, temperatury, energia (`monitor.mjs:1-15`).
- **Zapis odporny na awarię:** rozmowa zapisywana przez plik tymczasowy, flush i rename; testy symulują pełny dysk i awarię w połowie zapisu (`chat-store.mjs:8-9,31`).
- **Rozdział aplikacji i silnika:** supervisor już nie uruchamia llama-server, tylko czyta stan, log i metryki Prometheus silnika (`supervisor.mjs:1-6`).
- **`strata connect`:** konfiguracja omp, Claude Code, Codex i innych klientów ze sprawdzeniem `--check --output json` (R21n:28-36). Enigma pokazuje adres endpointu i gotowe fragmenty kodu (`ready.endpoint`, `app/engine/CONTRACT.md`), ale sama niczego nie konfiguruje ani nie sprawdza.
- Enigma ma już: wątki CPU = rdzenie fizyczne (`app/engine/src/server/engine.ts:483-495`, akcja (b) z R21n), pobieranie z wznowieniem i sha256 (`download.ts:1,130-169`), strażnik Host/Origin (`api.ts:30-41`).
- Lekcja: Strata najpierw miała działający i mierzony silnik (zgodność bajtowa, A/B), a potem włożyła 55% zmian w aplikację. My najpierw włożyliśmy pracę w stronę i własny silnik, a aplikacja nie przeżywa awarii silnika.
- Bierzemy do Enigmy: (1) poprzednia wersja silnika + powrót, (2) kontrola konfiguracji przed startem, (3) `enigma connect` dla omp i Claude Code, (4) testy nazwane od awarii (pełny dysk, przerwany zapis).

## Przegląd 2026-11-24: rodzina Straty (Basalt, Sync-Strata, v0.2.18)
- **Basalt** (jesdga95/basalt, 1948 gwiazdek 2026-11-24, tylko sm_120 i Flash-Next): wpis z 20.11 nazwał go „nowym”, a studiowaliśmy go już w R63a §6 (`dc047a7`, 11-04): dokładna dwustopniowa głowica Q8_0 w płaszczyznach bitowych (−20% czasu głowicy, bitowo dla greedy; dla Q6_K nie działa), środek warstwy GDN w jednym trwałym launchu. Reklamowane „6950/273 vs 5250/164” nie występuje w repo (`63-SYNTEZA.md:45`). Plan #23 (sito Q8_0 dla LFM) nadal czeka.
- **Sync-Strata** (hiruhiru2005, utworzone 2026-11-16, 99 gwiazdek): aplikacja „jednym kliknięciem” dla Windows i Linux na forku Straty z własnymi kwantami Sync-XS/S/M. To dokładnie kształt Enigmy zrobiony przez jedną osobę w tydzień. Co mają, a my nie: tabela wsparcia z jawnym „nie sprawdzone na prawdziwym sprzęcie” przy każdej rodzinie GPU, setup pobiera tylko silnik pasujący do karty (także HIP dla RX 6000/7000/9000), port API przesuwa się na wolny, gdy 8080 zajęty (`sync api` pokazuje faktyczny), parowanie telefonu kodem QR ważnym 3 min (klucz nie opuszcza PC), wybór modelu po ilości RAM ([README](https://github.com/hiruhiru2005/sync-strata)). Ich kwanty są niezgodne z llama.cpp i stratne dla nas — ale lekcje produktowe są niezależne od kwantów.
- **v0.2.18 (2026-11-21, silnik `strata-hy4` 0.1.64):** nowy model obsłużony w osobnym silniku w ciągu dni, z gotową paczką `hip-rx7900`; eksperci w RAM i na SSD dla 220B/12B aktywnych; deklaracje R9700 62 t/s, 5090 90–111. Dwa dni później `strata-inkling` 0.1.66 z paczką hip-rx7900 uruchomił się u nas z naszym plikiem (K-134: kopie 100,6 / 109,6 t/s, T=0,7 60,6 t/s), ale przy długich promptach dał page fault GPU — szybkie wydania bez testu na naszej karcie.
- **Lekcja:** Strata stała się platformą (forki Basalt, Sync-Strata, PolyStrata) bo dowozi gotowe paczki per karta i per model; Enigma ma lepszą bramkę poprawności, ale silnik ROCm wciąż `distribution: local`. Wydanie paczki gfx110X z bramką md5/KLD jest ważniejsze niż kolejny kernel.

## Przegląd 2026-11-24, wiersz 0.2.2 (proporcje pracy i własny silnik)

- Uzupełnienie powyższego o rejestrowy wiersz 0.2.2, który zamknęliśmy zdaniem „dla gfx1100 nic”. Od 0.2.0-beta do 0.2.2 było 337 commitów w 2 dni, a silnik to tylko ~11% zmienionych linii; reszta to aplikacja, Terminal (`strata launch/connect/update/bench`), testy i dokumentacja (`product/research/57b-strata-qwen38-flash.md`, §2). U nas proporcja była odwrotna i w złą stronę: 97 commitów landingu wobec 28 aplikacji ([[inference-stack]]).
- Własny silnik bez ggml (0.2.16) Stracie się udał, a nasz Enigma Turbo nie. Różnica to bramka: Strata sprawdza te same tokeny na 10 promptach na każdej architekturze, Turbo testował się na syntetycznym modelu ([[enigma-turbo-gemini-2026-11-20]]).
- Popyt: 29 639 gwiazdek w 4 tygodnie dla „jeden model, każdy sprzęt, instalacja jednym kliknięciem” — to jest produkt, który chcemy zrobić.
- Lekcja HIP z 0.2.2 zostaje: flaga hosta podnoszona po `graphLaunch` daje zakleszczenie (8/41 → 0/46).
- Co bierzemy: liczyć udział silnika, aplikacji, testów i dokumentacji w naszych commitach co tydzień, tak jak tu, i trzymać aplikację na równi z silnikiem.

## Przegląd 2026-11-24, wiersze 0.2.3–0.2.11 i basalt v0.5.0 (serwer, pomiar, sprzęt klienta)

- **0.2.3–0.2.11** zamknęliśmy zdaniem „dla gfx1100 i gęstego 27B nic; KVA stratny”. Kernelowo to prawda, ale raport `product/research/63a-silniki-lokalne.md` (§2, §4, §5) zapisał lekcje serwera, które w werdykcie zginęły:
  - **Cache rozmów liczony z wolnej pamięci** (0.2.3: 40% ponad podłogę, ≤ 8 GiB): drugi agent ma 91% reużycia, tura 11 → 3 s. U nas limit jest stały. Topka ma `--cache-ram` ([[lekcja-cache-ram-za-maly]]), profile `enigma-rocm-gfx1100` mają na sztywno 16384 MiB (`app/engine/data/engines.json:321,372,402`), a pozostałe silniki Enigmy nie przekazują flagi wcale (`engine.ts:570-577`). Żaden z tych limitów nie zależy od RAM użytkownika.
  - **Odzysk zepsutych wywołań narzędzi 92,9 → 98,3%** (0.2.8). Od R63a czeka jako „pomysł do serwera”. Fork [[speedy]] zrobił z tego cały produkt.
  - **Drabina degradacji zamiast mniejszego kontekstu** (0.2.10, „128K na 8 GB”): okno KV, potem bez MTP, potem głowica w RAM, każdy krok jedną linią w logu. W `app/engine/src` nie ma drabiny, planer obcina kontekst.
  - **Prywatność przy replikach** (0.2.11, #2892): odpowiedź trafiała do złego żądania. Każdy tryb wielu slotów w Enigmie albo topce potrzebuje testu „każda odpowiedź wraca do swojego żądania” pod współbieżnością.
  - **Pomiar:** ogłoszone +39% prefillu (PR #4366) to ciepły przebieg wobec zimnego, realnie +2–6%. Ścieżka promptu wybierana z pomiaru czasu zmieniała odpowiedzi (0.2.5), więc teraz wybiera ją długość promptu. Wybór wariantu z czasu musi zachować bity albo być jawnie oznaczony.
- **basalt v0.5.0** (nowy model Hy4-flash, nie nasz). Dwie lekcje produktu z wersji 0.2.1 (R63a §6):
  - **`--idle-sleep`:** bezczynny serwer oddaje VRAM, a powrót trwa 4 s zamiast 40,6 s zimnego startu. Upstream llama-server ma odpowiednik `--sleep-idle-seconds`, który zwalnia model i ładuje go przy żądaniu (`~/praca/llama-duo/common/arg.cpp:3845`, `tools/server/server-context.cpp:1090-1102`). Enigma go nie przekazuje (brak w `app/engine/src/server/engine.ts`). Klient Enigmy to często PC do gier, a model trzymający 20 GB VRAM bez przerwy blokuje mu grę.
  - **Bramka jakości wobec BF16, nie wobec siebie:** na tych samych wagach Q8_0 basalt ma KLD 0,0200, a llama.cpp 0,0325. Mierzą swój silnik względem modelu źródłowego, nie tylko „bitowo jak poprzednia wersja” ([[lekcja-bit-exact-wobec-siebie]]).

## Powiązane
- [[tensorfold]]
- [[lucebox]]
- [[zgodnosc-bitowa-md5]]
- [[wylacznik-w-kazdej-latce]]
