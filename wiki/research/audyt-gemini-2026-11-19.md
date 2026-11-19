---
typ: research
tags: [research, audyt, bezpieczenstwo, metodyka, enigma, kolejka]
aktualizacja: 2026-11-19
zrodlo: ~/praca/kernel-gemini/RAPORT.md (Gemini 4 Neon High przez Antigravity CLI, 104 KB, repo @ ab39207; polecenie właściciela 2026-11-19 „przeanalizuj całość kernela, TOP LEVEL”); weryfikacja: 3 agenci scout (sekcje C, D1–13, D14–25 + E/F/G/H) + własne sprawdzenie kodu; commity 9abc3ab, 80112fb, a357444 i następne
status: aktualne
---
# Audyt Gemini całego repo KERNEL (2026-11-19): co było prawdą, co naprawione, co odrzucone

**Bezpieczeństwo karty: oba główne zarzuty prawdziwe i naprawione tego samego dnia.**
- `gpu-guard.sh` przy ostrzeżeniu termicznym robił `exit 4` i przestawał pilnować karty.
- `run-jobs.sh` nie uruchamiał strażnika podczas jobów.

**Pomysły optymalizacji:**
- Dane i cytaty w większości się zgadzają.
- **Szacunki zysków są zwykle 2–10 × za wysokie.**
- Kilka liczb jest zmyślonych, a 8 pomysłów było już testowanych i odrzuconych (raport tego nie zauważył).
- Nowych, wartych kolejki rzeczy jest 6; patrz niżej.

## Naprawione od razu (bez karty, test na makietach albo `bun test`)

| zarzut | prawda? | poprawka |
|---|---|---|
| `gpu-guard.sh:42-44` `exit 4` przy VRAM ≥ 85 / hotspot ≥ 90 °C | tak | ostrzeżenie co 60 s, strażnik działa dalej (makieta: 91 °C → WARN i praca dalej, 101 °C → STOP rc 3) |
| `pgrep -f` w strażniku łapie powłoki agentów | tak | dokładne nazwy procesów (limit 15 znaków `comm`) |
| produkcja chroniona tylko przez `ss :8080` (nie podczas ładowania) | tak | także proces z binarki `~/llama-topka` |
| SIGKILL po 3 s | tak | jeden SIGTERM, do 60 s, potem SIGKILL (makieta: proces ignorujący TERM zabity, powłoka z „llama-bench” w poleceniu nietknięta) |
| `run-jobs.sh` bez strażnika | tak | strażnik na czas kolejki; kolejka staje, gdy strażnik nie żyje |
| `hostguard.sh` `inet_down_cost ≤ 0,003` | tak (decyzja: 0,002) | 0,002 |
| `k114/launch.sh` z pominięciem bramki transferu | tak | `hg_offer_ok`: cena pobierania + czarna lista także dla oferty po id (sprawdzone na żywym API: 0,0088 $/GB odrzucone) |
| `down.sh --all` | tak (sprzeczne z decyzją „tylko po id”) | usunięte |
| `spec_sweep.py` bez md5 i bez wykrywania pętli | tak | md5 wyjścia, flaga pętli (8-gramy), pętle poza medianą (makieta) |
| `k114/summ.py` miesza średnie | tak | czas kroku per prompt, potem mediana (51,1 → 51,5 ms; wnioski bez zmian) |
| `run-llm.sh` `VISION` nadpisuje argumenty, brak jawnego `GGML_HIP_PM4` | tak | `+=`, `GGML_HIP_PM4` domyślnie 0 (run-topka dalej eksportuje produkcyjne 1) |
| `run-topka.sh`: VAR 83 przy KV ≠ q4_0, echo bez VAR/CACHE_HUGE, nagłówek z 21.10 | tak (wpływ VAR 83 na f16 zawyżony: −2,4% tylko przy 131k, +9,6…16% przy 8k/32k) | VAR 83 tylko dla q4_0, echo i nagłówek poprawione |
| Enigma `enigma-rocm-gfx1100` = stara topka bez VAR 83 / CACHE_HUGE | tak | wersja topka-q70 i obie zmienne (`bun test` 208/208) |
| `bench.ts` przy `REPS > 2` powtarza zadania (n-gram cache) | częściowo (był `log.warn`) | błąd zamiast ostrzeżenia |
| `wiki/index.md` i decyzja eco nieaktualne | tak | poprawione |

**Do zrobienia na jaroserverai po włączeniu:** skopiować poprawione `tools/gpu-guard.sh`, `queue/run-jobs.sh`, `run-llm.sh`, `run-topka.sh` do `~/qwen-opt` (diff przed kopią).

**Harness fabryki:** `spec_sweep.py` jest w hashu harnessu (`factory/fk/paths.py:25`). Harness był już odblokowany wcześniej (25 zmienionych plików od locka, m.in. reguły R36/R37 z commitu RSI-F). Locka nie robiłem, bo zatwierdziłbym cudze zmiany; to decyzja właściciela.

## Fałszywe, zawyżone albo już odrzucone

- **`LLAMA_SPEC_COUPLED=1` w profilu Enigmy CUDA (C.1.4a, D1):**
  - samo dopisanie nic nie da, bo wydany fork nie ma tej ścieżki (`67-nvidia-vast-kampania.md:85`);
  - „7–13%” to spadek T=0 → T=1, a zmierzone sprzężone na CUDA daje +5,3…5,5%.
  - Wątek przechodzi do K-004 z poprawionym planem.
- **K-114 metodyka (C.3.1):** krytyka trafna (różnica krok − cel zawiera V5 − V1), ale liczby 51,52 / 20,19 ms są zmyślone. Zastrzeżenie dopisane do notatki K-114, a pomiar trafia do K-116.
- **Wcześniej odrzucone, czego raport nie zauważył:**
  - „single-pass KV” (D3) = K-087: liczby 400 GB/s i 43% zmyślone, kernel jest ograniczony obliczeniami;
  - fuzja QKV/gate-up (D11): PAIR2 +0,4%, liczba „340 → 185 launchy” zmyślona;
  - taśma delt GDN (D16) = K-092;
  - douczanie MTP na PL (D23) = K-098;
  - drafter DFlash2 (E3) = K-097;
  - kompresja entropijna wag (E5) = K-099: „3,1–3,4 bit” przeczy pomiarowi 3,865/4;
  - `-np` na XTX (D17) = K-086;
  - cięcie barier PM4 (D10) = K-093.
- **Zawyżone zyski:** dynamiczne `-ub` (źródło mówi × 1,004), epilog `kvq` (0,2–0,4%, nie 0,5–1,5%), adaptacyjny draft na NVIDIA (zmierzone +3,2%, nie +8…20%). Cele w planie G („4090 125–140 t/s” itp.) nie mają pokrycia.
- **Poza zasadami:**
  - natywne W4 / NVFP4 (E2) to zmiana kwantu;
  - tor „numeric-KLD” (C.5.3) jest sprzeczny z decyzją 2026-11-05;
  - CDNA, Tenstorrent, Intel i Apple bez sprzętu; zostają w notatkach skill-io.
- **Propozycje rewizji decyzji (C.5):** bramka dla zmiennej długości draftu to dokładnie istniejąca K-007 i czeka na decyzję właściciela. `-c 8192` do mikroprofilowania jest technicznie słuszne, ale profil musi mieć punkty ≥ 32k i ≥ 131k.

## Do kolejki (nowe albo poprawione)

| K | co | priorytet |
|---|---|---|
| K-004 (poprawiony) | build forka CUDA + sprzężone próbkowanie `7cdc0121b`, ABBA na 5060 Ti; zmierzone gdzie indziej +5,3…5,5% | wysoki |
| K-116 (poprawiony) | najpierw V(5) − V(1), potem `nsys` draftu | wysoki |
| K-125 | KLD ścieżki `kvq` dla Qwena na XTX (nigdy niezmierzone) | średni |
| K-126 | Enigma Windows: CUDA 13.4 dla Blackwell (dziś 12.4 → JIT przy pierwszym starcie) | średni |
| K-128 | czy omp obcina `<think>` i psuje trafienia cache (logi, bez karty) | średni |
| K-118 (poprawiony) | ramię ≥ 131k | średni |
| K-127 | AVX2 vs bez AVX2 w forku CUDA | niski |

## Powiązane
- [[gpu-guard]]
- [[KOLEJKA-TESTOW]]
- [[2026-11-17-k114-nvidia-sufit]]
- [[lekcja-vast-tylko-pelna-moc]]
- [[skill-io-metodyka]]
