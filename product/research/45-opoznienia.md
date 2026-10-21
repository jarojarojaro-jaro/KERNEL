# 45 — opóźnienia: rozgrzewka w serwerze, natywny ChatML, budżet TTFT, czas ładowania i przełączania

Branche llama.cpp są lokalne:
- `latency`, commit `d3fde2e65`: rozgrzewka i cache requant MTP;
- `latency-tmpl`, commit `7538632b9`: natywny ChatML.

Oba na bazie `b659634fd`, czyli topka. Konfiguracja produkcyjna `run-topka.sh`: MTP n=4 + lookup 3 W16, coupled, GPU verify, PM4 WA=2 GUARD, ctx 204800. Wszystko szło przez kolejkę (`l45.jobs`, `l45b.jobs`) i obyło się bez faultów.

## 1. Cache konwersji MTP: `LLAMA_MTP_REQUANT_CACHE=DIR` (wdrożone)

**Diagnoza.** Start Qwen trwa 38.5 s, z czego ~34 s zajmuje `init_slots` → `common_speculative_init`. Tam `llama_model_requant_mtp` konwertuje na CPU do iq4_xs głowę draftu (64k × 5120, z q6_K) i blok MTP. Robi to przy każdym starcie (`--spec-draft-head-type/--spec-mtp-type iq4_xs`). LFM tego nie robi i startuje w 4.2 s.

**Zmiana.** Skonwertowane bajty trafiają do pliku w DIR. Klucz to hash bajtów źródła, oba typy i kształt. Plik jest użyty tylko przy zgodnym rozmiarze, a zapis idzie przez tmp + rename. Z cache wychodzą więc te same bajty co z konwersji. Oprócz tego `set_draft_head_vocab` z tymi samymi id jest teraz no-opem. Dzięki temu przebudowa stanu spekulacji nie konwertuje drugi raz i nie zostawia starej kopii w VRAM.

| Qwen topka | ready (start → /health) |
|---|---|
| bez cache (3 starty) | 38569 / 38598 / 38490 ms |
| cache, pierwszy zapis | 41981 ms |
| cache, ciepły (2 starty) | **6553 / 6550 ms (−32.0 s, −83%)** |

**md5.** Prod, pierwsze żądania po starcie: `e0630ccd` z cache i bez. Bramka `greedy.sh` z cache: `c4708318` / `6f14e814` / `894e56e4`.

## 2. Rozgrzewka przed READY: `LLAMA_SERVER_WARMUP_PROMPT=N` (opt-in)

**Jak działa.** Przed READY serwer przepuszcza zwykłą ścieżką slotu jeden prompt z N tokenów plus 8 wygenerowanych (prefill w ubatchach, checkpointy, kroki MTP). Potem przywraca stan świeżego procesu:
- `llama_memory_clear(…, data=true)` na tgt i dft;
- przebudowa slotów i spekulacji (pending_h, lookup, coupled), prompt cache i metryk.

`yield_to_queue` działa też bez pętli kolejki.

**Bramka (wynik: PASS).**
- `greedy.sh`, warm == cold: Qwen plain `c4708318`, MTP `6f14e814`, LFM `894e56e4`. Sprawdzone 2× (z cache i bez).
- Prod, pierwsze żądania: Qwen `e0630ccd`, LFM `7f081041`, w obu ramionach.
- Raport 35 E8 (rozgrzewka po stronie klienta) zmieniał md5. Tutaj md5 się nie zmienia.

**Szybkość, przy N=1100:**

| | bez | z rozgrzewką |
|---|---|---|
| 1. żądanie prod Qwen 2839 tok, prompt_ms | 3465 / 3480 | **3015 / 3043 / 3047 (−437)** |
| 1. żądanie prod LFM 2917 tok, prompt_ms | 780 | **438 (−342)** |
| 1. żądanie 2k wall (ABBA A1 B1 B2 A2) | 2684 / 2688 | **2499 / 2502 (−185)** |
| 1. żądanie 1-tokenowe, Qwen | 244–248 ms | 37 ms |
| ready Qwen (z cache) | 6550 ms | 8902 / 9265 ms (+2.35 s) |
| ready LFM | 4150 ms | 4635 / 4639 ms (+0.49 s) |

Pierwsza wersja resetu kosztowała 15.5 s, bo konwertowała MTP drugi raz. Po no-opie w `set_draft_head_vocab` reset trwa 205–229 ms na Qwen i 13 ms na LFM.

**Werdykt.** Bezstratne, ale czas gotowości rośnie bardziej, niż zyskuje pierwsze żądanie (Qwen: +2.35 s wobec −0.44 s). Przy przełączaniu modeli to regresja. Dlatego zostaje jako opt-in: dla serwera startowanego z wyprzedzeniem, nie domyślnie w `run-topka.sh`.

## 3. Natywny renderer ChatML (wdrożone przez IntegTopka2)

**Przełączniki.**
- `LLAMA_CHAT_NATIVE=1`: szablony Qwen3.8 i LFM2.5, rozpoznane po hashu źródła, renderują się w C++. Wszystko, czego renderer nie obsługuje, idzie do jinja (obrazy, kwargi szablonu inne niż bool/string).
- `LLAMA_CHAT_LATE_SYSTEM=1`: późna wiadomość system/developer staje się turą `user` w tym samym miejscu. Qwen nie rzuca wtedy „System message must be at the beginning.”, a render wszystkiego przed tą wiadomością się nie zmienia (append-only dla prompt cache). Na LFM ten przełącznik nic nie robi.

**Bramka.** `tests/test-chat-native.cpp` używa ścieżki `oaicompat_chat_params_parse` z `LLAMA_SERVER_SAFE_SPECIAL=1`. Render jest bajt w bajt identyczny z jinja i `prompt_plain_ranges` też się zgadzają. Fallback: 0.

| korpus | Qwen3.8 (5 konfiguracji) | LFM2.5 (2 konfiguracje) |
|---|---|---|
| bodies_w13 | 61/61 | 61/61 |
| bodies_big | 12/12 | 12/12 |
| bodies_huge | 13/13 | 13/13 |
| body_big1 | 1/1 | 1/1 |
| dsdeploy b0 | 1/1 | 1/1 |
| safe-special inj | 6/6 | 6/6 |
| syntetyczne | 32/32 | 32/32 |

**Czas parse.** CPU `taskset -c 2-5`, mediana z 9:

| szablon | body | jinja | native |
|---|---|---|---|
| Qwen | 476 KiB | 108.6 ms | 8.8 ms |
| Qwen | 263 KiB | 60.2 ms | 6.4 ms |
| LFM | 476 KiB | 112.7 ms | 10.0 ms |
| LFM | 263 KiB | 61.7 ms | 6.9 ms |

Typowa tura agenta (body 26 KiB) to ~10 ms → ~1 ms.

## 4. Budżet TTFT tury agenta (Qwen prod, `LLAMA_SERVER_AP_TIMING=1`, replay omp)

Krótka tura `S2-turn2`: 27 nowych tokenów, 7337 w cache. Wall 720–751 ms, prompt_ms 581.

| etap | ms |
|---|---|
| json parse | 0.5 |
| szablon chat (jinja) | 9–11 → ~1 natywnie (pkt 3) |
| tokenizacja całego promptu (7.3k tok) | 15 → ~3 z `LLAMA_TOKENIZE_PAR=8` (raport 42) |
| przywrócenie checkpointu | 38–46 |
| **3 × utworzenie checkpointu (224 MiB, host)** | **3 × 144–150 = ~440** |
| prefill reszty + pierwszy token | ~100 |
| HTTP / reszta wall | ~150 |

Największą pozycją jest kopiowanie checkpointów do pamięci hosta, ~60% TTFT tury. Pokrywa to raport 38: `LLAMA_CKPT_VRAM=1|2` daje ~15 ms na checkpoint, a S2-turn2 spada z 579 do 160–197 ms. IntegTopka2 integruje to teraz z `LLAMA_CKPT_VRAM=2`.

Inne pozycje:
- `prompt_save` przy zmianie rozmowy: 750 ms, w tym 530 ms kopii checkpointów.
- Prefill świeżego promptu: 2k 2.21 s, 8k 8.0 s, 32k 34.1 s.

## 5. Czas ładowania i przełączania Qwen ↔ LFM

Pomiar: start `run-topka.sh` → /health; potem SIGTERM → wyjście procesu → VRAM < 10%.

| | ready | 1. żądanie | wyjście | VRAM wolny |
|---|---|---|---|---|
| Qwen (bez cache) | 38.5 s | 247 ms | 288–309 ms | 78 ms |
| Qwen (cache MTP) | **6.55 s** | 244 ms | 288 ms | 78 ms |
| LFM | 4.15 s | 13 ms | 287 ms | 80 ms |
| Qwen `LLAMA_ARG_LOAD_MODE=none` (bez cache) | 37.4 s | 251 ms | 392 ms | 77 ms |
| LFM `LLAMA_ARG_LOAD_MODE=none` | 2.79 s | 13 ms | 308 ms | 78 ms |

Przełączenie, liczone jako wyjście + zwolnienie VRAM + ready:
- LFM → Qwen: 38.9 s → **6.9 s** z cache MTP;
- Qwen → LFM: ~4.5 s.

`LLAMA_ARG_LOAD_MODE=none` dał LFM −1.36 s i Qwen −1.1 s, ale to po jednym starcie i zależy od page cache. Nie wdrażam bez ABBA.

## Do bazy wiedzy

- **Start Qwen topka to w 83% konwersja MTP do iq4_xs na CPU, nie ładowanie wag.** Cache na dysku skraca ready z 38.5 s do 6.55 s, bez zmiany md5.
- **Rozgrzewka w serwerze jest bezstratna tylko z pełnym resetem:** `llama_memory_clear(data=true)` na tgt i dft oraz przebudowa slotów i spekulacji. Zysk na pierwszym żądaniu (−0.2 do −0.44 s) jest mniejszy niż koszt przed READY.
- **TTFT tury agenta zależy głównie od kopii checkpointów (~440 z ~580 ms), nie od szablonu ani tokenizacji.**
