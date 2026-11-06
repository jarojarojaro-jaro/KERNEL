# 65 — Jak odzyskaliśmy 1 GiB VRAM i dostaliśmy pełny kontekst 262 144 (2026-11-05/06)

Źródła: `~/qwen-opt/q63/NOTES.md` §2, `~/qwen-opt/q63/logs/summary.txt`, `~/qwen-opt/q63/logs-dep/mem.txt`, `~/qwen-opt/queue/logs/ctx-262144.log`, łatka `qwen-opt/patches/topka-q63/0002-mtp-lean-reserve-*.patch`. Wiki: [[2026-11-05-q63-topka]], [[lekcja-rezerwa-mtp-kopia-f16]], [[2026-11-06-ctx-262k-fit]], [[2026-11-06-final-mode]].

## 1. W skrócie

| | przed (topka f9b84bcfa) | po (topka-q63) | zmiana |
|---|---|---|---|
| bufor compute kontekstu draftu MTP (ROCm0) | 1081,23 MiB | 40,28 MiB | −1041 MiB |
| VRAM po załadowaniu, ctx 204 800 | 23 360 MB | 22 319 MB | **−1,0 GiB** |
| kontekst czatu (Uncensored) | 204 800 | **262 144** | **+28%** |
| zapas VRAM w najgorszym przypadku | 1201 MiB (przy 204 800) | 1193 MiB (przy 255k wypełnionych) | ten sam |
| prędkość / odpowiedzi | 120,51 t/s, md5 20bfd0bb | 120,54 t/s, md5 20bfd0bb | 0%, bit w bit |

Kontekst wzrósł o 28% bez zmiany kwantyzacji, modelu, jakości i prędkości. Zysk pochodzi wyłącznie z bufora, który był rezerwowany na graf nigdy niewykonywany.

## 2. Skąd się brała strata

llama.cpp przy starcie robi „rezerwę grafu” (`sched_reserve`) dla każdego kontekstu. Buduje najgorszy możliwy graf i alokuje pod niego bufor compute raz, żeby w trakcie pracy nie alokować pamięci.

Kontekst draftu MTP (głowica, która zgaduje następne tokeny) dostawał tę samą rezerwę co zwykły model: `n_ubatch` (512) tokenów z pełną atencją nad całym KV draftu. Na XTX taka atencja idzie kernelem MMA, który potrzebuje kopii KV w f16. Rezerwa była więc liczona tak:

| składnik (ctx 204 800, KV draftu q4_0, ub 512) | MiB |
|---|---|
| kopia f16 całego KV draftu (K+V: 2 × 204 800 × 1024 × 2 B) | 800 |
| maska f16 512 × 204 800 | 200 |
| aktywacje | ~68 |
| **razem** | **~1068** (zmierzone 1081,23) |

Tymczasem kontekst draftu w topce wykonuje tylko dwa rodzaje grafów:
1. **catch-up:** zapis K/V dla tokenów promptu i weryfikacji, bez atencji, FFN i głowicy (wszystkie wiersze `output=false`);
2. **krok draftu 1 tokenu:** atencja przez kernel `kvq` (≤ 16 tokenów), który czyta KV q4_0 bezpośrednio, bez kopii f16.

Graf „512 tokenów z pełną atencją” nigdy się nie wykonywał, a zabierał ~1 GiB VRAM i 220 MiB pamięci hosta.

## 3. Poprawka (bezstratna)

Port pomysłu z RDNA-FAST (`TAG_MTP_LEAN_RESERVE`, raport 63c E6): `llama_context::mtp_lean_reserve` rezerwuje tylko grafy, które naprawdę się wykonują (catch-up K/V-only + krok 1 tokenu). Gdyby kiedyś pojawił się większy graf, scheduler raz powiększy bufor (z ostrzeżeniem w logu), czyli tak samo jak upstream przy grafie większym od rezerwy. `LLAMA_MTP_LEAN_RESERVE=0` przywraca stare zachowanie.

Walidacja (2026-11-05):
- md5 greedy Qwen i LFM: PASS;
- ABBA z produkcją: 120,51/120,58 → 120,54/120,57 t/s, md5 przy 32k identyczny;
- przy okazji: ub 2048 mieści się teraz w VRAM, ale prefill jest o 0,6–0,9% wolniejszy, więc zostaje ub 512.

## 4. Przeliczenie na kontekst

KV przy q4_0 (z logu serwera): model 3600 MiB / 204 800 tokenów = 18,0 KiB/token + draft 225 MiB / 204 800 = 1,1 KiB/token, razem **~19,1 KiB/token**. Tylko 16 z 64 warstw Qwen3.8-27B ma pełne KV (48 to GDN ze stałym stanem), dlatego kontekst jest tak tani.

- 262 144 − 204 800 = 57 344 tokenów × 19,1 KiB ≈ **1,07 GiB**, czyli dokładnie tyle, ile zwolniliśmy.
- Test (2026-11-06, 17:29): prompt 254 977 tokenów, szczyt VRAM 23 367 / 24 560 MiB, zapas 1193 MiB, prefill 465 t/s, decode na końcu 78,7 t/s, bez OOM i błędów amdgpu.
- UD-Q4_K_XL (profil `qwen`) przy 262 144: szczyt 24 224 MiB, zapas tylko 336 MiB, więc niewdrożony.

## 5. Co z tego dalej

1. **Aplikacja Enigma / karty NVIDIA:** ta sama rezerwa istnieje w upstream llama.cpp (silnik bazowy Enigmy). Na CUDA FA dla KV q4_0 też używa kopii f16, więc na 3090/4060 Ti z MTP to również ~0,8–1 GiB przy dużym kontekście. Na 16 GB to +25–35% kontekstu. Do sprawdzenia na Vast (`-lv 4`, linie `sched_reserve`) i ewentualnie jako PR do upstream.
2. **Nadmiar KV ~10 KiB/token (63a):** zmierzone wcześniej 29,1 KiB/token wobec 19,1 z buforów. Reszta to prawdopodobnie checkpointy GDN i cache. Kolejny kandydat na zapas pamięci.
3. **Reguła ogólna (lekcja):** rozmiar bufora rezerwy to koszt najgorszego grafu, który scheduler sobie wyobraża, a nie koszt modelu. Przy każdym dodatkowym kontekście (draft, sidecar) sprawdzaj `sched_reserve` z `-lv 4` i pytaj, czy ten graf w ogóle się wykonuje.
