# 21d. KV cache na dysku: Strata, Mirai S Ada, nasze E5. Czy zabijamy dyski?

Data: 2026-10-19. Agent: ResKvDurability. Zakres: badanie źródeł, arytmetyka i pomiary dysku serwera na CPU i I/O. Na GPU nic nie uruchamiałem. Kodu w forku nie zmieniałem.

## 0. Werdykt w skrócie

1. **Dysk zabija tylko naiwna polityka.** Pełny zapis slotu po każdej turze omp w obecnym formacie E5 (wszystkie checkpointy w pliku) daje ~0.58 TB zapisu na jedną sesję 150k. Dzień ciężkiej pracy agentowej to wtedy ~4.7 TB, a dysk 300 TBW pada w ~2 miesiące (§7). Ten sam ruch w polityce z §10 (najpierw RAM/tmpfs; na dysk tylko append nowych pozycji, jeden stan rekurencyjny i jeden checkpoint na zrzut) daje **~7 GB/dzień typowo i ≤10 GB/dzień pod twardym limitem**. To ≤6% tempa gwarancyjnego dysku 300 TBW i ok. 1/10 tego, co ten serwer już dziś zapisuje w dzień pracy deweloperskiej (~95 GB/dzień, §6).
2. **Odczyty są nieszkodliwe.** Nie zużywają cykli P/E. Restore może robić tyle razy, ile trzeba (§8).
3. **Twierdzenia Mirai S Ada są arytmetycznie spójne, ale niesprawdzalne.** 245k tokenów KV q8_0 Qwena3.8-27B to 8.53 GB (deklarują 8.3 GB). Restore 9.0 s oznacza 0.95 GB/s. „Ponowne czytanie” 524 s oznacza prefill 468 t/s (deklarowane „~9 min” to 8.7 min). W repo nie ma jednak żadnego receiptu dla tych liczb i nie podają stanu page cache. Werdykt: wiarygodne co do rzędu wielkości, niezweryfikowane co do wartości (§3).
4. **Strata 0.2.0 nie istnieje.** Najnowsze wydanie to v0.1.45 z 2026-10-17, a tagi kończą się na v0.1.45 (GitHub API). Mechanizm dyskowy Straty („session files”) jest dobrze zrobiony: tmp + fsync + rename, odciski modelu i konfiguracji, O_DIRECT, tylko najgłębszy checkpoint. Strata uczciwie pisze też, że **nie gwarantuje** identycznych tokenów po restarcie (§4).
5. **„Bajt w bajt te same odpowiedzi” na naszym hybrydzie: wykonalne, ale nie dziś.** Dziś blokują to dwie rzeczy: (a) nasz plik nie zapisuje kontekstu draftu MTP, a restore go czyści (`server-context.cpp:2717-2719`); (b) w trybie domyślnym zamaskowane wiersze KV za pozycją zmieniają wynik WMMA (lekcja z raportu 12). Warunki i test w §9.
6. **Nasz dysk jest wąskim gardłem restore.** Serwer ma Samsung PM9B1 512 GB (OEM, bez DRAM) na łączu PCIe 3.0 x4. `dd` z O_DIRECT zmierzył **1.05–1.60 GB/s**, a E5 restore szedł z 0.95 GB/s. Jesteśmy więc blisko limitu dysku. Warstwa tmpfs pomaga tu podwójnie: zero zużycia i szybszy odczyt (§6, §10).

## 1. Źródła i co jest czym

| ID | Źródło | Uwagi |
|---|---|---|
| S1 | https://github.com/Niko1221/Strata/releases/tag/v0.1.45 | release 17 Oct 06:53, commit `477ac13` |
| S2 | `GET api.github.com/repos/Niko1221/Strata/releases` i `/tags` (2026-10-19) | najnowszy v0.1.45; **brak 0.2.0** (ani tag, ani gałąź: tylko `main`, `rc/0.1.30`); potwierdził niezależnie agent ResEnginesNew (21g) |
| S3 | Strata `docs/DETAILS.md` @ `477ac13` (klon `/tmp/Strata`) | :1041-1056 conversation cache w RAM; :1086-1137 parking; :1232-1362 session files (dysk) |
| S4 | Strata commit `d9cb22d` (2026-10-13, `--conversation-cache-park-gain`) | pomiar kosztu „przepisz cały snapshot co turę” |
| M1 | https://github.com/professorpalmer/mirai-s-ada README, tabela Results (klon `/tmp/mirai-s-ada` @ `b8d7e5b`) | 245k: 10.5 s (restore 9.0 + 1.6), re-read 524 s; 128k: 6.7 s vs 199 s |
| M2 | `mirai-s-ada/RELEASE-NOTES.md:114-231` | bundle-20261017 … 20261018c: tabela 64k/128k/245k, delty, zapis przy bezczynności, 227 s za ~6 GB |
| M3 | `mirai-s-ada/layer/slot_cache.py:17-40,104-156,429-535` | polityka: min 16384 tok., zapis co +8192, budżet 20 GB LRU, łańcuch 8/32 delt, bezczynność 30 s |
| M4 | silnik `professorpalmer/llama.cpp-ada-mirai`, commity `762aafec7d` i `b30f76fdbe` (2026-10-16) | sidecar `.draft`: save/restore kontekstu draftu MTP |
| O1 | `~/KERNEL/product/research/16f-xtx-szybkie.md:192-215`; `~/wt/quickwins/qw/e5.jsonl` | nasze E5 |
| O2 | `~/wt/quickwins/tools/server/server-context.cpp:2602-2671,2717-2719,2933-2956,3745-3790`; `src/llama-context.cpp:3628-3646,3657`; `common/common.h:650-652` | format pliku slotu, checkpointy |
| O3 | metadane GGUF (`~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf`, `~/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf`), lista tensorów `15a-ggufls.py` | wymiary KV i stanu |
| H1 | `lsblk`, `/sys/class/nvme/nvme0/*`, `/sys/block/nvme0n1/stat`, UDisks2 `NVMe.Controller.SmartGetAttributes` (bez sudo), `dd` O_DIRECT (2026-10-19 ~03:10) | dysk serwera |
| T1 | https://www.techpowerup.com/ssd-specs/samsung-pm9b1-512-gb.d1435 | PM9B1: 3500/2500 MB/s, bez DRAM (HMB 64 MB), V6 TLC 128L, TBW „Unknown” |
| T2 | https://semiconductor.samsung.com/consumer-storage/support/warranty | 500GB: 5 lat lub 300 TBW; 1TB: 600; 2TB: 1200; 4TB: 2400; 860 QVO 1TB: 360 |
| T3 | https://www.techpowerup.com/ssd-specs/samsung-990-pro-1-tb.d861 | 990 Pro 1TB: 7450 MB/s, 600 TBW |

## 2. Arytmetyka: bajty na token i stały stan

**Qwen3.8-27B** (O3: `qwen35.attention.head_count_kv 4`, `key_length 256`, 16 warstw `attn_k [5120,1024]`, 48 warstw GDN, `ssm_a [48]`, `ssm_out [6144,5120]`, `ssm_conv1d [4,10240]`, MTP `blk.64.attn_k [5120,1024]`):
- elementy KV na token: 16 warstw × 2 (K,V) × 4 głowy × 256 = 32 768;
- **q4_0** (18 B / 32 el.): **18 432 B/token**; KV warstwy MTP (draft): 2048 × 18/32 = **1152 B/token**;
- **q8_0** (34 B / 32 el.): **34 816 B/token**, draft MTP q8_0 2176 B/token;
- stan GDN na warstwę: S = 48 głów × 128 × 128 × 4 B = 3 145 728 B, conv = 3 × 10 240 × 4 B = 122 880 B; razem 48 warstw = **156.9 MB = 149.6 MiB** (zgadza się z 16f:137);
- checkpoint z MTP: 149.6 + 20.7 MiB = **170.3 MiB = 178.6 MB** (16f:137).

**Rekonstrukcja pliku E5 Qwena** (`n_written` = 2 391 966 216 B dla 53 258 tok., `qw/e5.jsonl`): tokeny 0.21 MB + KV 53 258 × 18 432 = 981.6 MB + stan 156.9 MB = 1138.8 MB. Reszta to 1253.2 MB = **7.02 × 178.6 MB**, czyli 7 checkpointów dopisanych do pliku (O2: `save_slot_checkpoints`, :2639-2671; odstęp `checkpoint_min_step = 8192`, maksimum 32, `common.h:650-652`). Zgodność 0.3%, więc **ponad połowa pliku 53k to checkpointy**. [INFERENCE: rozkład wyliczony; liczby checkpointów nie odczytałem z logu.]

**LFM2.5-24B-A2B** (O3: 10 warstw atencji z `head_count_kv 8`, head dim 2048/32 = 64, KV q8_0): 10 × 2 × 8 × 64 × 34/32 = **10 880 B/token**. Dla 53 030 tokenów to 577.0 MB wobec 580.3 MB w pliku; ~3 MB to stan shortconv i checkpointy.

**Rozmiar pliku Qwena w zależności od długości** (q4_0, GB dziesiętne):

| tokeny | obecny format (wszystkie checkpointy) | 1 checkpoint | + sidecar MTP |
|---|---|---|---|
| 53k | 2.21 | 1.31 | +0.06 |
| 100k | 4.14 | 2.18 | +0.12 |
| 150k | 6.14 | 3.10 | +0.17 |
| 200k | 8.13 | 4.02 | +0.23 |

**„Mirai S 27B”** to ten sam Qwen3.8-27B (README M1: trellis ~2.4 bit/wagę, plik 11.17 GB). KV jest więc identyczny: q8_0 34 816 B/token + `.draft` 2176 B/token.

## 3. Mirai S Ada: weryfikacja twierdzeń

| Twierdzenie (M1/M2) | Arytmetyka | Ocena |
|---|---|---|
| 64k: plik 2.3 GB, restore 0.8 s, re-read 73 s | 65 536 × 34 816 = 2.28 GB ✓; 2.28 / 0.8 = **2.85 GB/s**; prefill 64k/73 s = **877 t/s** | spójne. 2.85 GB/s na Gen4 NVMe jest realne, ale równie dobrze to może być standby cache Windows po restarcie serwera, nie komputera. Nie podają, czy cache był wyczyszczony. |
| 128k: plik 4.5 GB, restore 1.6 s, re-read 195 s | 131 072 × 34 816 = 4.56 GB ✓; 2.85 GB/s; **672 t/s** (zgodne z ich 639 t/s przy 130k w README) | spójne |
| 245k: plik 8.3 GB, restore 9.0 s + 1.6 s tura, re-read 524 s („~9 min”) | 245 000 × 34 816 = **8.53 GB** (−2.7% od deklaracji; „245k” to zapewne zaokrąglenie); 8.3 / 9.0 = **0.92 GB/s**, 3× wolniej niż przy 128k; prefill **468 t/s**; 524 s = **8.7 min** | rząd wielkości wiarygodny. Spadek przepustowości przy 245k nie jest wyjaśniony; możliwe przyczyny: część KV idzie do pinned RAM, plik wypadł z cache albo dysk zwolnił. ×50 wynika głównie z tego, że prefill rośnie nadliniowo, a restore liniowo. |
| 128k dokument po restarcie: 6.7 s vs 199 s cold (restore 2.2 s, 39 nowych tokenów) | 4.56 / 2.2 = 2.07 GB/s; reszta 4.5 s to template, tokenizacja i odpowiedź | spójne |
| „Answers are the same as without the restart” | ma sens przy greedy i pełnym stanie z draftem; dlatego dodali sidecar `.draft` (M4) | wiarygodne przy greedy, niesprawdzalne: w repo **brak receiptu**. `grep` po `receipts/` i `bench/` nie znajduje 524 / 245k / 8.3 GB; README twierdzi, że „receipts for each row are in receipts/”. |
| Pełny zapis ~6 GB (174k) trwał 227 s na wolnym dysku, delta 0.2–0.6 s (M2:142-143) | 6 GB / 227 s = **26 MB/s** | ważny sygnał ostrzegawczy. Dysk bez DRAM albo QLC po wyczerpaniu SLC cache spada do dziesiątek MB/s. |
| Zapis przed żądaniem (domyślny): tura czeka średnio 23 s (delty) / 74 s (pełne) (M2:124-125, sesja Bonsai) | — | **antywzorzec dla UX**: zapis leży na ścieżce krytycznej. My zapisujemy asynchronicznie i tylko przy bezczynności. |

**Polityka Mirai w liczbach zużycia** (M3; symulacja sesji rosnącej po 800 tokenów na turę, rozmiary przeliczone na nasze q4_0, bez checkpointów; ich q8_0 to ~1.9× więcej):
- bundle-20261017b, pełny zapis co +8192 tok. od 16k: **26.9 GB** na sesję 150k i 43.9 GB na 200k;
- bundle-20261018c, delty z pełnym zapisem co 8 delt: **6.9 GB** na 150k i 11.5 GB na 200k. Każda delta niesie cały stan rekurencyjny (~150 MiB, M2:146), a restore „~1 s more per delta” (M2:121).

Co od nich bierzemy: (1) `pos_min` / `append` jako prymityw zapisu przyrostowego; (2) sidecar draftu; (3) klucz pliku = sha256 tokenów i weryfikacja prefiksu tokenów z nagłówka pliku (M3:66-92); (4) budżet LRU usuwający tylko własne pliki `lc-*`. Czego nie bierzemy: zapisu przed żądaniem, okresowego pełnego przepisywania łańcucha i stanu rekurencyjnego w każdej delcie (§10).

## 4. Strata v0.1.45: części dotyczące KV i dysku

- **Release v0.1.45 (S1)** nie wnosi nic do zapisu na dysk. W serwerze jest tylko „conversation-cache copies cost fewer milliseconds per request; no engine change” i przełączniki checkpointów do multi-slot (`STRATA_CKPT_POOL`, `STRATA_CKPT_THREADS`, `STRATA_SLOT_CKPT_MOVE` oznaczony jako „do not use”). Resztę release'u opisuje 21g.
- **Session files (S3:1232-1362)** to dojrzały wzorzec do skopiowania:
  - tmp z unikalną nazwą, fsync, `rename`, potem fsync katalogu; przy błędzie po rename flaga `published`;
  - O_DIRECT w blokach 16 MiB;
  - nagłówek z fingerprintem modelu (rozmiar + pierwszy i ostatni MiB każdego pliku) i konfiguracji (wersja silnika, `--kv`, RoPE, kontekst, przełączniki arytmetyki) plus hash payloadu;
  - **„only the deepest checkpoint is saved”** (:1289); plik zawiera też KV warstwy draftu (:1301);
  - preflight miejsca na dysku (`--session-min-free-mib` 4096); żadnej automatycznej retencji („nothing deletes them”).
- **Liczby Straty (S3:1354-1362; RTX 4070 Ti, NVMe ext4, Flash-Next IQ3_XXS, 63 025 tok.):** plik 1.20 GB (19.0 kB/token, inny model, nieporównywalne z Qwenem 1:1); save 0.65 s z fsync = **1.84 GB/s**; restore 1.05 s = **1.14 GB/s**; cold 25.5 s. Każdy pomiar to pojedynczy przebieg.
- **Uczciwe zastrzeżenie (S3:1347-1352):** „Exact future token replay across restarts is not guaranteed”. Pierwsza 32-tokenowa kontynuacja była zgodna z procesem, który działał dalej. Następna rozjechała się od 28. tokenu, przy czym trzy procesy po restore były zgodne między sobą. Przyczyny nie wyizolowali. U nich realne źródła to rezydencja ekspertów i zaokrąglenia CPU/GPU w MoE. My mamy wszystko na GPU, ale mamy własne źródła numeryki (§9).
- **Patologia „przepisz cały snapshot co turę” zmierzona (S4, RAM, nie dysk):** 1 418 parkowań jednej długiej rozmowy dało **2 251.9 GB** kopii hosta. Bramka `park-gain` zmniejszyła to do 3.26 GB. Gdyby to szło na SSD, byłoby to 2.25 TB, czyli 0.75% dysku 300 TBW w jednym przebiegu benchmarku.

## 5. Porównanie z naszym E5

| | nasze E5 (XTX, Qwen q4_0 + MTP) | Mirai (4070, q8_0) | Strata (4070 Ti) |
|---|---|---|---|
| kontekst | 53 258 | 64k / 128k / 245k | 63 025 |
| plik | 2.39 GB (z 7 checkpointami) | 2.3 / 4.5 / 8.3 GB | 1.20 GB |
| save | 1.99 s (1.20 GB/s, **bez fsync**, `llama-context.cpp:3629` otwiera `"wb"` w miejscu) | brak danych (delta 0.2–0.6 s) | 0.65 s z fsync |
| restore | 2.51 s (0.95 GB/s, page cache zrzucony) | 0.8 / 1.6 / 9.0 s | 1.05 s |
| prefill zamiast tego | ~61.5 s (×24.5) | 73 / 195 / 524 s | 25.5 s |
| draft MTP w pliku | **nie**: restore czyści pamięć draftu (O2:2717-2719) | tak (`.draft`) | tak |
| ochrona przed złym modelem | tylko magic/wersja/rozmiary; `TODO: add more model-specific info` (`llama-context.cpp:3657`) | sha tokenów | fingerprint modelu i konfiguracji |
| atomowość | brak (zapis w miejscu, bez tmp/rename/fsync) | `os.replace` z tmp (M3:368) | pełna |

Wnioski dla nas: (1) przy tej samej długości plik jest ~2× za duży z powodu checkpointów; (2) brak MTP po restore (wpływ na acceptance niezmierzony); (3) brak atomowości i odcisku modelu. Przy 46 „unsafe shutdowns” w SMART (§6) to realne ryzyko podania uszkodzonego albo obcego stanu. Przykład: Qwen Uncensored ma tę samą architekturę i kształty, więc wczytanie jego pliku nie skończy się błędem rozmiaru.

## 6. Dysk serwera (pomiar bez sudo)

- **Model:** `SAMSUNG MZVL4512HBLU-00BH1`, FW `HPS3NHAV`, 476.9 GiB (lsblk, `/sys/class/nvme/nvme0/model`), czyli **Samsung PM9B1 512 GB**: OEM, kontroler Marvell 88SS1322, **bez DRAM** (HMB 64 MB), V-NAND V6 TLC 128L, spec 3500/2500 MB/s, **TBW nieopublikowane** (T1).
- **Łącze:** `current_link_speed 8.0 GT/s`, `width 4`, czyli **PCIe 3.0 x4** (~3.9 GB/s surowo), mimo że dysk jest Gen4.
- **SMART** (UDisks2 `SmartGetAttributes`, bez sudo):
  - `percent_used 0`, `avail_spare 100%` (próg 5%), `media_errors 0`;
  - `total_data_written 1 875 484 672 000 B` = **1.875 TB**, `total_data_read` 3.22 TB;
  - `power_cycles 169`, **`unsafe_shutdowns 46`**;
  - temperatura 311 K = 38 °C, WCTEMP 356 K = 83 °C, CCTEMP 358 K = 85 °C;
  - `SmartPowerOnHours: 89` wygląda na nieaktualną wartość, nie opieram się na niej.
- **Bieżące tempo zapisu:** `/sys/block/nvme0n1/stat` pokazuje 52 830 818 sektorów × 512 = **27.05 GB w 6.81 h** uptime'u, czyli ~4.0 GB/h, **~95 GB/dzień** przy obecnej pracy deweloperskiej (buildy, logi, modele).
- **Endurance (proxy):** detaliczne Samsungi klasy 500 GB mają **300 TBW / 5 lat** (T2). To 164 GB/dzień przez 5 lat, czyli 0.33 DWPD. Dla 1 TB 600 TBW (T2, T3). NAND V6 ma do 3000 P/E (T1), więc 300 TBW jest szacunkiem konserwatywnym. Zapisane dotąd 1.875 TB to 0.6% z 300 TBW.
- **Odczyt sekwencyjny zmierzony** (`dd iflag=direct` po pliku GGUF Qwena, pod `flock /tmp/quiet.lock`, load avg 8–11 przez inne zadania):
  - 16 MiB QD1: 4.29 GB w 4.09 s = **1.05 GB/s**;
  - 1 MiB QD1: 2.15 GB w 1.34 s = **1.60 GB/s**;
  - 4 równoległe strumienie 16 MiB: 4.29 GB w 3.86 s = **1.11 GB/s** (licznik sektorów potwierdził, że w tym czasie nikt inny nie czytał).
  - Wynik to ~30–45% specyfikacji. To pojedyncze pomiary na obciążonej maszynie, przyczyny nie badałem [INFERENCE: DRAM-less + łącze Gen3 + stare dane]. **Wniosek: restore E5 (0.95 GB/s) już teraz jest prawie na limicie tego dysku.**
- Test zapisu (2 GiB O_DIRECT z fsync) się nie odbył: `quiet.lock` był zajęty, po 60 s timeout. Nie powtarzałem go ze względu na prośbę o oszczędzanie CPU i I/O.
- **TRIM:** `fstrim.timer` włączony (cotygodniowy), mount `rw,relatime` bez `discard`, `discard_max_bytes` > 0. Usunięte pliki cache wracają do puli raz w tygodniu, co wystarcza. Zajętość / to 55% (243 z 466 G).

## 7. Zużycie: zapis na operację i na dzień

**Na operację zapisu (Qwen, q4_0):**
- pełny zapis w obecnym formacie: 53k 2.39 GB (zmierzone), 150k ~6.1 GB, 200k ~8.1 GB;
- pełny zapis z 1 checkpointem: 150k 3.1 GB, 200k 4.0 GB;
- zapis przyrostowy (projekt §10): nowe pozycje × 18 432 B + stan i 1 checkpoint (0.336 GB). Tura omp z 2k nowych tokenów: 37 MB KV + 336 MB stanu. **Stały stan GDN dominuje w małych zapisach**, więc nie zapisujemy co turę.
- LFM: 10.9 kB/token, 53k = 0.58 GB, stan znikomy.

**Scenariusz „ciężki dzień agentowy”:** 8 głównych sesji omp rosnących do 150k (~180 tur po ~800 tok.) i 30 subagentów po 30k. Ten profil to [INFERENCE]; z capture omp mamy tylko start sesji 7–10k (16f E4), ale model jest parametryczny.

| polityka | GB / sesja 150k | GB / dzień | 300 TBW wystarcza na |
|---|---|---|---|
| P0: pełny zapis po każdej turze, obecny format | 582 | **~4 660** | **~64 dni** |
| P0': j.w., 1 checkpoint | 321 | ~2 570 | ~117 dni |
| P1: Mirai 17b (pełny co +8k, ≥16k; q4_0, bez ckpt) | 26.9 | ~215 | ~3.8 roku (ich q8_0: ~2 lata) |
| P2: Mirai 18c (delty + pełny co 8) | 6.9 | ~55 | ~15 lat |
| P3: nasz projekt bez warstwy RAM (append KV raz + 2 zrzuty stanu) | 3.6 | ~29 | ~28 lat |
| **P4: nasz projekt (tmpfs; na dysk tylko przy shutdown/presji RAM, top-2 sesje)** | — | **~7 (limit 10)** | **>100 lat dla samej tej funkcji** |

Arytmetyka P4: przy jednym wyłączeniu albo restarcie dziennie zrzucamy 2 najnowsze sesje × (150k × 19 584 B z MTP + 0.336 GB) = 2 × 3.27 = 6.5 GB. Subagenci nie trafiają na dysk (reguła z §10). Dla porównania: obecne tło deweloperskie to ~95 GB/dzień (§6).

Uwagi o WAF: duże sekwencyjne pliki kasowane w całości i TRIM-owane to najbardziej przyjazny wzorzec (WAF bliski 1). Rating TBW zakłada mieszankę klienta JEDEC z drobnymi losowymi zapisami, więc porównanie jest konserwatywne. Ryzyko rośnie przy dysku zapełnionym powyżej ~80%: SLC cache maleje, a WAF i czasy zapisu rosną (por. 26 MB/s u Mirai, §3).

## 8. Czy odczyty są nieszkodliwe? Termika i stabilność

- **Odczyt nie zużywa NAND:** nie ma programowania ani kasowania, więc nie ma cykli P/E. Read disturb kontroler obsługuje relokacją bloku dopiero po bardzo wielu odczytach tego samego bloku. Jeden restore to jeden odczyt pliku, więc to pomijalne [INFERENCE: ogólna wiedza o NAND, bez źródła w tym raporcie]. `total_data_read` 3.22 TB nie wpływa na `percent_used`.
- **Termika:** zrzut 4 GB to kilka sekund pracy. Dysk ma 38 °C przy progach 83/85 °C. Ryzyka nie ma, chyba że ktoś robi zapis ciągły (P0).
- **Stabilność:** 46 niebezpiecznych wyłączeń w historii. Zapis musi być atomowy (tmp, fsync, rename, fsync katalogu), a odczyt weryfikowany hashem. Uszkodzony plik oznacza ponowny prefill, nigdy dekodowanie z częściowego stanu (wzorzec Straty S3:1337-1338).
- **RAM/tmpfs:** zero zużycia. Serwer ma 62 GB RAM, z czego 47 GB to buff/cache, a `/dev/shm` ma 32 GB. Limit warstwy RAM musi zostawić page cache na mmap wag (Qwen 17.6 GB + LFM).

## 9. „Bajt w bajt te same odpowiedzi” na hybrydzie GDN + atencja

Punkt odniesienia ma znaczenie:
- **(A) restore == serwer, który nie był restartowany.** To osiągalne, bo restore jest kopią bajtów: KV q4_0 tak, jak leży w pamięci, stan GDN i conv w f32, checkpointy. Kolejne tury liczą się z identycznego stanu. Warunki:
  1. ten sam binarny build, GPU, flagi (`-fa`, `-ub`, `-b`, typy KV, ctx, MTP n, słownik draftu) i model; dlatego fingerprint w nagłówku;
  2. **stan draftu MTP musi wrócić.** W trybie domyślnym tokeny z MTP i bez niego mają różne md5 (raport 12: `c4708318` vs `6f14e814`), bo rozmiar okna weryfikacji N zależy od draftów. Bez sidecara drafty po restore są inne niż w procesie żywym, więc zmienia się numeryka i przy remisach także tokeny. Dziś nasz restore czyści pamięć draftu (O2:2717-2719), a stan `data_spec` wraca tylko z checkpointu;
  3. **zamaskowane wiersze KV za końcem sekwencji.** W żywym procesie leżą tam stare wiersze odrzuconych draftów, po restore zera albo śmieci. Na RDNA3 WMMA reaguje na nie o 1–2 ulp (lekcja `lekcja-bit-exact-attention`). Neutralizuje to `GGML_HIP_BITEXACT_FA_ZERO_MASKED=1` / `LLAMA_SPEC_BITEXACT=1` (gałąź `batch-invariant`);
  4. **ten sam checkpoint przy rozjeździe promptu.** omp/szablon może zrzucić reasoning poprzedniej odpowiedzi. Wtedy żywy serwer cofa się do najnowszego pasującego checkpointu (O2:3745-3783), a restore musi mieć ten sam. Wystarczy zapisać checkpoint z końca ostatniego promptu. Starsze checkpointy (edycja historii daleko wstecz) dają poprawny, ale nie bitowo identyczny wynik, bo inaczej dzielą ponowne przeliczenie na ubatche;
  5. sampling: identyczność bajtowa ma sens przy greedy albo jawnym seedzie. Przy T=1 bez seeda identyczny jest tylko rozkład.
- **(B) restore == zimny prefill tego samego tekstu: NIE, i nie trzeba.** Stan zbudowany turami ma inne granice ubatchy niż prefill jednym ciągiem. Dla LFM różne rozmiary ubatcha dają KLD 0.055–0.068 i 88–89% zgodności top-1 (`modele/lfm-czulosc-na-podzial-batcha.md`). Dla Qwena GDN chunked prefill też zależy od podziału (raport 12, lista źródeł). Restore jest tu wręcz **wierniejszy**: odtwarza dokładnie ten stan, którego model używał.
- **Deduplikacja między sesjami nie może psuć (A).** Wspólny prefiks tokenów (system prompt i narzędzia omp) nie gwarantuje identycznych bajtów KV, bo zależą one od podziału na ubatche w danej sesji. Rozwiązanie: segmenty adresowane hashem **bajtów** (BLAKE3), a indeks tokenów wskazuje na hashe bajtów. Deduplikacja zachodzi tylko przy identycznych bajtach, więc ryzyko dla exactness jest zerowe.

**Werdykt:** (A) jest wykonalne przy greedy i trybie BITEXACT po dodaniu sidecara MTP i zapisu checkpointu z końca promptu. W trybie domyślnym spodziewam się rzadkich rozjazdów numerycznych [INFERENCE, do zmierzenia w §11]. W produkcie obiecujemy „ten sam stan, poprawna kontynuacja”. „Bajt w bajt” obiecujemy tylko w trybie BITEXACT.

## 10. Projekt dla silnika i Podkręta (z budżetem zużycia)

**Warstwy:**
1. **L0: VRAM** (slot żywy) i **L1: RAM w procesie** (`--cache-ram 16384`, istniejący `server_prompt_cache`).
2. **L2: tmpfs** (`/dev/shm/podkret-kv/<model-fp>/`, limit domyślnie min(12 GiB, 20% RAM), LRU). Przeżywa restart serwera i zmianę modelu Qwen ↔ LFM (16f E5: główny zysk), nie przeżywa restartu komputera. Zużycie zerowe.
3. **L3: SSD** (`~/.cache/podkret/kv/<model-fp>/`). Zapis tylko w sytuacjach: (a) wyłączenie lub restart systemu (systemd `ExecStop` albo sygnał do `appd`) dla top-K=2 najnowszych sesji; (b) presja RAM wypychająca wpis z L2, który był wznawiany co najmniej raz; (c) jawne „przypnij sesję” w UI. **Nigdy na ścieżce żądania.**

**Kiedy zapisywać z L0/L1 do L2:** przy bezczynności slotu ≥60 s, przy zmianie modelu i przy wypchnięciu z L1. Tylko dla sesji ≥16k tokenów (krótsze prefill odtworzy w <20 s). Subagentów zapisujemy dopiero, gdy któryś wróci drugi raz (reguła „wznowiony ≥1×”).

**Format (natywny, zamiast obecnego pliku slotu):**
- **segmenty KV** `[pos_a, pos_b)` po 8192 pozycji, warstwa po warstwie, typ jak w pamięci (q4_0/q8_0); adres = BLAKE3(bajtów), zapisywane **raz** (append-only). Prymityw serwera: `save{pos_min}` / `restore{append}` jak u Mirai (M2:134-146), ale **bez stanu rekurencyjnego w segmencie**;
- **punkt stanu**: stan GDN i conv (156.9 MB) + `data_spec` + KV draftu MTP (sidecar, 1152 B/token) + **jeden checkpoint z końca ostatniego promptu** (178.6 MB). Przy kolejnym zrzucie poprzedni punkt jest kasowany;
- **manifest** (JSON): łańcuch hashy tokenów co 256 tok. (indeks prefiksów z 16f), lista segmentów, punkt stanu, fingerprint (rozmiar + BLAKE3 pierwszego i ostatniego MiB GGUF, commit buildu, wersja ROCm/CUDA, `-ctk/-ctv/-ctkd`, ctx, ub, b, MTP n, słownik, tryb BITEXACT), hash payloadu;
- zapis przez tmp, `fdatasync`, `rename` i fsync katalogu; odczyt z O_DIRECT w blokach 16 MiB i walidacją przed pierwszym zapisem na GPU (wzorzec S3).

**Odtwarzanie:** najdłuższy prefiks z L1, potem L2, potem L3, wybierany po indeksie tokenów. Odczytujemy segmenty do pozycji punktu stanu i sam punkt stanu. Próg opłacalności: oszczędność ≥2048 tokenów prefillu (M3 `min_gain`).

**Kompresja: domyślnie wyłączona.** q4_0 to skale f16 i nibble, czyli dane prawie losowe; stan f32 może zyskać 5–15% [INFERENCE, niezmierzone; nie było pliku stanu do testu, bo pliki E5 nie przetrwały]. CPU serwera jest teraz przeciążony, więc zysk nie uzasadnia kosztu. Do ewentualnego sprawdzenia w §11.

**Budżet zużycia (twarde reguły w `appd`):**
- limit dzienny zapisu L3 = **2% pojemności dysku/dzień** (512 GB → 10 GB, 1 TB → 20 GB). Przy TBW ≈ 600× pojemność (TLC, T2) to ≤6% endurance w 5 lat, przy QLC (np. 360 TBW / 1 TB, T2) ≤10%. Po przekroczeniu L3 jest wyłączone do północy, L2 działa dalej;
- limit miejsca L3 = min(32 GB, 10% pojemności), a zajętość systemu plików musi zostać ≤80%; TTL 72 h (jak Lucebox w 16f), LRU kasuje całe łańcuchy;
- strażnik SMART (UDisks, bez roota): `percent_used ≥ 80`, `avail_spare ≤ spare_thresh + 10`, `critical_warning ≠ 0` albo `media_errors` rośnie: L3 wyłączone, komunikat w UI;
- licznik w UI: „KV cache zapisał X GB w tym miesiącu (Y% limitu)”, liczony z `total_data_written` z SMART i własnego licznika bajtów;
- dysk wolny przy zapisie (<200 MB/s w ostatnim zrzucie albo zrzut >30 s): L3 zmienia się w „tylko przy shutdown, top-1” (lekcja z 227 s u Mirai).

## 11. Plan wdrożenia, oczekiwany zysk, minimalny eksperyment

**Etapy i nakład:**
1. *Higiena obecnego mechanizmu* (~0.5 dnia): tmp, fsync, rename; fingerprint w wrapperze (16f wariant A); zapis tylko ostatniego checkpointu, co tnie plik 53k z 2.39 do ~1.31 GB, a 200k z 8.1 do 4.0 GB.
2. *Sidecar MTP* (~0.5 dnia): `llama_state_seq_get_data_ext(ctx_dft, …, FLAGS_NONE)` do pliku obok, zamiast `seq_rm` w O2:2719; +4.7% bajtów pliku z jednym checkpointem.
3. *Warstwa tmpfs i polityka w wrapperze/`appd`* (~1–2 dni): L2, triggery bezczynności, zmiany modelu i shutdown, limity z §10.
4. *Natywne segmenty `pos_min` / `append` i punkt stanu* (~2–3 dni, serwer): append-only, deduplikacja po bajtach.

**Oczekiwany zysk** (prefill z dopasowania t = 0.943·n + 0.00389·n² [s, n w tys.] do 29.5k = 31.2 s i 94k = 123 s, `BENCHMARKI…:30-31`, [INFERENCE: ekstrapolacja z 2 punktów]):

| sesja | prefill (szac.) | restore z SSD przy 1.05 GB/s (1 ckpt + MTP) | ×|
|---|---|---|---|
| 53k | 61.5 s (zmierzone, 16f) | 1.37 GB, ~1.3 s (dziś 2.51 s z 7 ckpt) | ×47 |
| 150k | ~229 s | 3.27 GB, ~3.1 s | ×74 |
| 200k | ~344 s (5.7 min) | 4.25 GB, ~4.0 s | ×86 |

Z tmpfs restore powinien być ≤1 s dla 53k [INFERENCE: ograniczać będzie ścieżka `state_read` i H2D, nie pamięć].

**Minimalny eksperyment** (wymaga GPU pod `flock /tmp/gpu.lock flock /tmp/quiet.lock`; uruchamia Main, harness `qw/e5`):
1. Qwen 53k: save do `/dev/shm` i do SSD (z wyczyszczonym page cache); zmierzyć restore i TTFT następnej tury.
2. Ta sama sesja: następna tura greedy (≥256 tok.) w procesie żywym i po restore (nowy proces), w trybie domyślnym i w `LLAMA_SPEC_BITEXACT=1` + `GGML_HIP_BITEXACT_FA_ZERO_MASKED=1`; porównać md5 i acceptance MTP z sidecarem i bez.
3. Replay jednego dnia omp (`qw/replay.py`, capture omp) z polityką P4; licznik zapisu z `/sys/block/nvme0n1/stat` przed i po.

**Kryteria kill:**
- restore z tmpfs ≥80% czasu restore z SSD: L2 nie daje szybkości (zostaje tylko jako ochrona przed zużyciem), uprościć do L1 + L3;
- acceptance MTP po restore bez sidecara spada o <3% względnie: sidecar opcjonalny tylko dla trybu BITEXACT;
- md5 różne w trybie BITEXACT: błąd w zapisie lub odczycie, blokuje obietnicę „bajt w bajt”;
- replay dnia zapisuje >10 GB na SSD: poprawić politykę przed wydaniem;
- restore ≥10% czasu prefillu przy 53k: projekt nieopłacalny (dziś 4%).

**Zgodność z forkiem:** lookup tail i PM4 nie dotyczą stanu. kvq czyta KV q4_0/q8_0 w miejscu, więc segmenty mają ten sam typ. BITEXACT patrz §9. Bezstratne: tak, to kopia stanu, nie zmiana numeryki.

## Do bazy wiedzy

- **folder `produkt/`, tytuł „Cache sesji na dysku: polityka i budżet zużycia”** (nowa albo rozszerzenie proponowanej w 16f `produkt/cache-sesji-na-dysku.md`):
  - P0 (pełny zapis co turę, format E5) ~582 GB/sesja 150k, ~4.7 TB/dzień, 300 TBW w ~64 dni; P4 (tmpfs + zrzut top-2 przy shutdown) ~7 GB/dzień, limit 10 GB/dzień (2% pojemności); źródło: ten raport §7, `~/KERNEL/product/research/21d-kv-na-dysku.md`;
  - Qwen q4_0 18 432 B/token + MTP 1152; stan GDN 156.9 MB; checkpoint 178.6 MB; plik E5 53k = 1138.8 MB stanu + 7 × 178.6 MB checkpointów; źródło: GGUF metadane, `qw/e5.jsonl`, `server-context.cpp:2639-2671`, `common.h:650-652`.
- **folder `sprzet/` (albo `serwer/`), tytuł „Dysk serwera: Samsung PM9B1 512 GB”**:
  - `MZVL4512HBLU-00BH1`, DRAM-less, PCIe 3.0 x4 (8 GT/s × 4), O_DIRECT 1.05–1.60 GB/s (spec 3.5), SMART: 1.875 TB zapisane, 0% used, 46 unsafe shutdowns, 38 °C; zapis ~95 GB/dzień przy pracy deweloperskiej; TBW nieopublikowane, proxy 300 TBW; źródło: lsblk, `/sys/class/nvme/nvme0`, UDisks2 SmartGetAttributes, dd 2026-10-19, T1, T2.
- **folder `research/`, tytuł „Raport 21d: KV na dysku (Strata, Mirai S Ada)”**:
  - Mirai 245k: 8.53 GB wyliczone vs 8.3 deklarowane, restore 0.92 GB/s, prefill 468 t/s, brak receiptów; delty z ~150 MiB stanu każda; zapis przed żądaniem kosztuje 23–74 s na turę; 227 s za ~6 GB (26 MB/s); źródło: M1, M2:114-231, M3;
  - Strata 0.2.0 nie istnieje (najnowsze v0.1.45, 2026-10-17); session files: tmp + fsync + rename, fingerprint, O_DIRECT 16 MiB, najgłębszy checkpoint; 63k = 1.20 GB, save 0.65 s, restore 1.05 s; brak gwarancji identycznych tokenów (rozjazd od 28. tokenu); park-gain 2 251.9 GB → 3.26 GB; źródło: S2, S3:1232-1362, S4.
- **folder `lekcje/`, tytuł „Restore stanu ≠ zimny prefill; exactness wymaga draftu MTP i zerowania zamaskowanych wierszy”**:
  - nasz restore czyści kontekst draftu (`server-context.cpp:2717-2719`); plik slotu bez fsync, tmp i fingerprintu (`llama-context.cpp:3629,3657`); exactness (A) tylko w BITEXACT z sidecarem; źródło: ten raport §9, raport 12, `lekcja-bit-exact-attention`.
