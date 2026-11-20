---
typ: research
tags: [research, gemini, agenci, silnik, weryfikacja]
aktualizacja: 2026-11-20
zrodlo: ~/praca/kernel-gemini/src/enigma-turbo (napisany przez Gemini 4 Neon w agy, rozmowa właściciela 19–20.11, ~7,2 tys. linii); test na Qwen3.5-0.8B Q4_K_M (unsloth, md5 54e125d5…); referencja llama-completion topki z -ngl 0 na jaroserverai
status: aktualne
---
# „Enigma Turbo” od Gemini 4 Neon: README obiecuje silnik CUDA/HIP, a działa tylko wolny CPU i odpowiada bełkotem

**Test 2026-11-20 na prawdziwym modelu Qwen3.5-0.8B Q4_K_M (ta sama architektura hybrydowa co nasz 27B): na pytanie „What is the capital of France?” Enigma Turbo odpowiada bełkotem z surowymi tokenami (`èĬ±ĠfaĠfaĠf… IMEIMEIME`, wykrywacz pętli zgłasza pętlę) w tempie 0,7 t/s. llama.cpp na tym samym pliku (CPU, 4 wątki): „Paris is the capital of France.” przy 60,9 t/s. Na karcie niczego nie uruchamiałem: jego kod GPU nie jest nigdzie wywoływany.**

## Co faktycznie jest w kodzie (przegląd 2026-11-20)

| obietnica w README | stan w kodzie |
|---|---|
| „Dual CUDA/HIP”, MMVQ SoA, FA kvq 1-pass, GDN, MTP persistent (`src/kernels/cuda_hip/*.cu`, ~1 tys. linii) | **Żaden kernel GPU nie jest wywoływany.** `engine.cpp` liczy wszystko przez `kernels::*_cpu` (`forward_layer`, `forward_batch`, `propose_drafts`). Build HIP/CUDA najwyżej skompiluje martwy kod. |
| szybki silnik | jednowątkowe pętle skalarne na CPU: 0,7 t/s na modelu 0,8B (llama.cpp 60,9 t/s, ~87 × szybciej) |
| tokenizer BPE z GGUF | brak mapowania bajtów GPT-2 (`bytes_to_unicode`): spacje nie stają się `Ġ`, więc tokeny są złe (29 tokenów promptu zamiast 24), a dekodowanie wypisuje surowe `Ġ`/`âĢĵ` |
| głowica MTP `blk.64` | ładuje tylko `enorm`/`hnorm`/`eh_proj`/`shared_head.norm`. Pomija całą warstwę transformera MTP, więc drafty nie są drafterem Qwena. |
| bezstratność | gdy brakuje tensora, ładowanie po cichu podstawia stałe (`ssm_conv1d` = 0,25, `ssm_a` = −1, normy = 1,0) zamiast błędu. Zły plik daje bełkot bez ostrzeżenia. |
| „ALL PASS”, „LOSSLESS SPECULATION BIT-FOR-BIT”, „Anti-K-001” | testy (`tests/test_turbo.cpp`) działają tylko na **syntetycznym** modelu 256 × 4 warstwy z losowymi wagami. Sprawdzają spójność silnika z samym sobą, nigdy wyniku względem llama.cpp ani prawdziwego GGUF. Przechodzą, choć silnik na prawdziwym modelu nie działa. |

Elementy, które mogą być wartościowe jako pomysły (niezweryfikowane na GPU, bo nic ich nie woła):
- repack wag do 128-bitowych strumieni SoA, bitowo zgodny w teście CPU dla Q4_K, Q6_K i IQ4_XS;
- sklejenie gate+up i Q+K+V w jeden GEMV;
- maska przyczynowa liczona z `pos` zamiast maski z hosta.

Wszystkie trzy mamy już w wiki jako znane dźwignie: K-013, K-111 i fuzje z R24.

## Lekcje

- **Agent bez prawdziwej bramki buduje „zielone” testy na własnych założeniach.** Bramka silnika to zawsze: prawdziwy GGUF → ten sam prompt → porównanie tekstu i logitów z llama.cpp (md5 T=0, KLD), a dopiero potem t/s. Tak jak u nas: [[bramka-kld-kanarki]], [[kernelbench]] („mocna bramka albo nic”).
- **README i nazwy testów to nie dowód.** „100% BIT-EXACT”, „Dual CUDA/HIP” i „ALL PASS” padły przy silniku, który nie odpowiada na pytanie o stolicę Francji.
- Na kartę nie idzie kod, który nie przeszedł bramki na CPU. Zasada bezpieczeństwa karty plus szybkie iteracje: 0,8B na CPU w 2 min odsiało całość.

## Co dalej (propozycja)

Jeśli właściciel chce dalej rozwijać ten silnik z Gemini, warunek wejścia na kartę to kolejno:
1. tokenizer zgodny z llama.cpp (te same id na 100 tekstach);
2. Qwen3.5-0.8B: md5 T=0 = llama.cpp na 6 promptach;
3. wywołanie kerneli GPU z silnika i `test-backend-ops`-podobne porównanie z CPU;
4. dopiero wtedy XTX i 27B.

Realnie to tygodnie pracy, a nasz fork llama.cpp już ma te dźwignie z pomiarami.

## Praca w parze Kernel + Gemini 4 Argon High (od 2026-11-20 04:50, decyzja właściciela)

Repo `~/praca/enigma-turbo` (git, poza KERNEL), zasady w `COLLAB.md`: jedna miara prawdy `gate/gate.py`, czyli referencja llama.cpp na tym samym GGUF (Qwen3.5-0.8B Q4_K_M), 26 tekstów tokenizera i 6 promptów (top-5 logprob + 16 tokenów greedy). Nikt nie zmienia gate bez zgody drugiej strony. Gemini działa przez `agy` (`--model gemini-4-argon-high --mode accept-edits`) jako unit `systemd --user`. Gdy kończy turę, `notify.sh` wrzuca wiadomość do skrzynki Kernela, który robi przegląd i zleca następną rundę.

Runda 1:
- **Gemini: tokenizer** (byte-level BPE + pretokenizacja Qwena), stan wyjściowy 1/26 identycznych.
- **Kernel: forward.** Znalezione rozbieżności z `llama.cpp src/models/qwen35.cpp`:
  - bramka `z` to osobny tensor `attn_gate`;
  - `ssm_a` w GGUF ma już postać −exp(A_log);
  - brakowało SiLU po conv1d, L2-normy q/k i skali q;
  - `attn_q` niesie Q i bramkę sigmoid przeplecione per głowica;
  - RoPE działa tylko na 64 z 256 wymiarów.
- Nowy `forward_ref.cpp` (referencyjny forward FP32, wyrocznia dla szybkich ścieżek). Gate gen, przed → po:

| miara | przed | po (319bdb7) |
|---|---|---|
| top-1 pierwszego kroku zgodny z llama.cpp | 0/1 | 5/6 |
| tokeny greedy identyczne | 0/8 | 51/88 (2 prompty 16/16, 1 prompt 8/8) |
| max |Δlogp| top-5 | – | 0,09–0,46 nat |

Rozjazdy pojawiają się tam, gdzie model się waha (top-1 −1,2…−1,5). Otwarte: szum llama.cpp (aktywacje q8_K na CPU, KV f16) czy jeszcze jeden błąd. Najpierw pomiar podłogi szumu, dopiero potem tolerancja gate.

### Runda 1b: forward HIP na XTX i model 27B (2026-11-20 rano)

- `src/gpu/gpu_forward.hip`: ta sama matematyka co `forward_ref`.
  - Wagi zostają w formacie bloków GGUF na karcie (Q4_K/Q5_K/Q6_K/Q8_0/IQ4_XS), czyli tyle samo bajtów co w llama.cpp. Aktywacje, KV i stan GDN są w FP32.
  - Stary kod GPU od Gemini 4 Neon w ogóle się nie kompilował: `__builtin_nontemporal_load` na `uint4`.
- Poprawki loadera: `n_layer` bez bloków `nextn` (27B: 65 → 64). `gate --gpu` nie ładuje już modelu do RAM.
- **Gate na prawdziwym modelu produkcyjnym** (Qwen3.8-27B-Uncensored Q4_K_M, referencja llama.cpp na XTX): **PASS 6/6**, |Δlogp top-1| ≤ 0,056, greedy 16/16 na 3 promptach. Na 0.8B też PASS.

| tempo dekodu (XTX, ten sam plik GGUF) | Enigma Turbo | llama.cpp topka (bez spekulacji) |
|---|---|---|
| Qwen3.5-0.8B: per-element GEMV → GEMV K-quant → GDN w LDS | 81,3 → 162,0 → 187,0 t/s | 436,9 t/s |
| Qwen3.8-27B: per-element GEMV → GEMV K-quant → GDN w LDS → graf HIP → GEMV int8 + `sudot4` | 3,96 → 26,61 → 28,20 → 28,76 → **35,35 t/s** (+793%, 84% llama.cpp) | 42,16 t/s |

Profil 27B (`rocprofv3`, na token):
- GEMV Q4_K 21 ms, czyli ~585 GB/s (61% pasma);
- GEMV Q6_K 6,3 ms;
- GDN 3,0 ms → 0,83 ms po przeniesieniu stanu do LDS (wersja z rejestrami miała 348 VGPR spill);
- RMSNorm 1,9 ms (208 wywołań);
- atencja 0,5 ms.

Do odzyskania do poziomu llama.cpp (23,7 ms/token) jest ~9,5 ms. Dźwignie po kolei:
1. GEMV: ładowania 16-bajtowe, potem aktywacje int8 i `dot4`;
2. narzut ~1000 uruchomień kerneli na token: graf HIP z pozycją w pamięci karty;
3. GDN ze stanem w rejestrach;
4. fuzja norm.

**Incydent 2026-11-20 04:29–04:41 (serwer czasu UTC):** `rsync --delete` katalogu `~/turbo` skasował plik zadań kolejki w trakcie. `run-jobs.sh` przeczytał 0 zadań, a mimo to zatrzymał produkcję :8080 bez zadania przywrócenia, więc czat nie działał ~12 min. Przywrócony ręcznie: health ok, n_ctx 262144.
- Poprawka: `run-jobs.sh` odmawia pustej albo brakującej listy przed zatrzymaniem :8080 (sprawdzone na `/nonexistent.jobs`).
- Pliki zadań trzymamy w `~/turbo-jobs/`, poza synchronizowanym katalogiem.

### Pętla optymalizacji (od 2026-11-20 05:56, polecenie właściciela „loopuj aż F1”)

Każdy krok to profil `rocprofv3`, jedna dźwignia, gate 0.8B + 27B (zawsze PASS) i 2 pomiary.

| krok (27B, XTX, dekod) | t/s | profil |
|---|---|---|
| start pętli (GEMV int8) | 35,35 | GEMV 20,1 ms/token |
| fuzja: norm+int8 w jednym bloku, wiele GEMV w jednym launchu, swiglu+int8 | 39,93 | multi-GEMV 18,75 ms |
| fuzja 2: q/k prep, atencja+int8, conv+SiLU+L2, gated norm+int8 (656 kerneli/token) | 40,73 | – |
| Q4_K: nagłówek bloku jednym ładowaniem 16 B, aktywacje int4, unroll 2 | 42,50 | multi-GEMV 17,74 ms |
| Q6_K przepakowany do 224 B (wyrównane ładowania) | 41,92 | **odrzucone**: +6,7% bajtów kosztuje więcej, niż daje wyrównanie |
| norm w rejestrach + redukcja shuffle; GDN 4 grupy wierszy × 32 kolumny | **43,55** | kernele 20,47 ms; przerwy ~2,5 ms |

**Wynik: Enigma Turbo bez spekulacji = 43,55 t/s wobec llama.cpp topka bez spekulacji 42,16 (+3,3%) na tym samym pliku i karcie.**

Dalej:
1. spekulacja MTP (produkcja ma ~120 t/s z MTP + lookup), czyli GEMV wielokolumnowy do weryfikacji i cofanie stanu GDN;
2. prefill batchem (Gemini);
3. atencja flash-decoding;
4. mniej przerw między kernelami.

### Pętla, iteracje 2–4 (2026-11-20 rano): partie tokenów, serwer, MTP

| krok (27B, XTX) | wynik |
|---|---|
| GEMV wielokolumnowy (N ≤ 8, wagi dekodowane raz), R wierszy na falę | prefill 44,8 → 219 t/s; dekod 43,79 t/s; weryfikacja N=5 27,8 ms (V(5)/V(1) = 1,24) |
| `forward_all` (weryfikacja) + `accept` (cofanie) | bitowo równe krokom pojedynczym (max \|Δlogit\| 0) |
| serwer `serve --gpu` (Gemini r2) | test 3/3 („Paris”, strumień == bez strumienia), 48–50 t/s na krótkich odpowiedziach |
| głowica MTP na karcie, cofanie przez ponowne liczenie | K=1 +10%, K≥3 wolniej (koszt powtórki ~23 ms) |
| **cofanie z taśmy rekurencji (bez GEMV)** | **K=2: 43,91 → 66,99 t/s (+52,6%)**, 128/128 tokenów identycznych z dekodem bez spekulacji; akceptacja 0,55, 2,06 tok/krok |

Lekcja: przy weryfikacji spekulacji w hybrydzie GDN najdroższe nie jest samo sprawdzanie draftów, tylko cofanie stanu po odrzuceniu. Powtórzenie kroku kosztowało 23 ms, a taśma (wejście conv, q|k|v, beta|alpha na warstwę, 31 MB) zbija to do ułamka ms. To ta sama idea co „delta tape” z projektu Gemini 4 Neon, tylko tym razem zmierzona i sprawdzona bramką.

### Serwer ze spekulacją lookup + MTP (T=0), 27B na XTX, 2026-11-20 ~07:10

`tests/test_serve.py --compare-spec`: 5/5 zadań identycznych bit w bit (ze spekulacją == bez == strumień SSE).

| zadanie | bez spekulacji t/s | ze spekulacją t/s | × |
|---|---|---|---|
| krótkie odpowiedzi (3 pytania, 8–13 tok.) | 48–50 | 74–86 | 1,48–1,79 |
| kopia/edycja kodu Python 40 linii | 41,17 | 163,84 | 3,98 |
| kopia/edycja kodu C++ 40 linii | 41,18 | **188,12** | **4,57** |

Gemini 4 Argon High wyczerpał limit w rundzie 3 (lookup + pętla w serwerze; reset za ~164 h). Jego niezacommitowaną pracę przejrzał, poprawił (usunięty syntetyczny test oczekiwanej szybkości) i scalił Kernel. Od rundy 4 partnerem jest Gemini 4 Neon High: spekulacja przy T>0 bezstratnie (rejection sampling z draftem jednopunktowym).

### Pętla optymalizacji 2026-11-20 07:10–07:55 (27B, XTX, T=0, draft vocab 64k, p_min 0,5)

| krok | przed | po | Δ |
|---|---|---|---|
| T>0 bezstratnie (Gemini r4, test χ² na 200 tys. próbek) | 42,8 t/s (T=0,7 bez spekulacji) | 64,5–66,4 t/s | +52% |
| graf HIP dla przebiegu MTP | 72,18 t/s | 72,16 t/s | 0 (odrzucone jako dźwignia, kod zostaje) |
| GEMV dekodu 16/8 wątków na wiersz | 43,79 t/s | 42,56 / 41,08 t/s | −2,8 / −6,2% (odrzucone) |
| `k_gdn_norm`: GDN + gated RMSNorm + int8 w jednym kernelu | dekod 43,78 / spec K=3 72,27 t/s | 44,26 / 73,59 t/s | +1,1 / +1,8% |
| `k_gemv_swiglu_q8`: gate/up + swiglu + int8 w jednym kernelu (tylko N=2..5) | spec K=2 73,80 t/s | 74,38 t/s | +0,8% (przy N=1 i N=8 wolniej, tam stara ścieżka) |
| rozmiar słownika draftu 8k/16k/32k/**64k**/96k/128k | — | 61,7/64,4/67,9/**74,4**/73,8/72,8 t/s (K=2) | 64k optimum: akceptacja 0,63 stoi powyżej, draft droższy |
| **stan GDN/conv jako ping-pong** (bez migawki 151 MB i 96 memcpy na krok) | spec K=2 / K=3 74,44 / 74,19 t/s | **77,67 / 77,58 t/s** | **+4,3 / +4,6%** (weryfikacja 25,14 → 24,28 ms, accept 0,64 → 0,35 ms) |
| `forward_all_argmax`: argmax weryfikacji na karcie (N intów zamiast N × 248k logitów) | spec K=2 77,53 t/s | 78,54 t/s | +1,3% |
| `k_attn_w`: atencja fala-na-klucz, online softmax (stara: wątek na klucz, 47,7 µs/wywołanie) | dekod 44,06; 1024 tok. bez spec / spec 39,97 / 84,49 t/s | 45,23; 44,54 / 89,83 t/s | +2,7%; +11,4 / +6,3% |
| norma RMS w epilogu GEMV (ostatni blok, licznik atomowy) | dekod 45,40 t/s | 42,16 t/s | −7% (odrzucone: `__threadfence` + atomik w ~640 blokach) |
| K-split GEMV dla macierzy ≤ 8192 wierszy | 45,15 t/s | 45,12–45,31 t/s | szum (odrzucone) |
| `k_gdn_conv_norm`: conv + L2 jako prolog kernela GDN (48 uruchomień mniej na token) | dekod 45,29; spec K=2 78,08 t/s | 45,56; 80,91 t/s | +0,6%; +3,6% (krok 25,6 → 25,5 ms, reszta: akceptacja 0,61 → 0,63 na zmienionym tekście) |
| q norm + rope jako prolog atencji (bez `k_q_prep`) | dekod 45,56 t/s; krok spec 25,46 ms | 45,77 t/s; 25,40 ms | +0,5%; +0,2% |
| **prefill przez int8 WMMA** (`v_wmma_i32_16x16x16_iu8`, kawałki 64 tokenów, kafel fali 32 × 32) | prefill 512 tok. 253,8 t/s (GEMV, kawałki 8) | **590,0 t/s** | **+132%** (llama.cpp produkcja pp4096: 1115) |
| serwer Gemini r5 (`mtp_draft_n`, p_min 0,5, K=3, argmax na karcie) + naprawa wiersza ukrytego po prefillu | `--bench` mediany: Q1 84,9 · Q2 76,5 · Q5 192,0 t/s | 151,9 · 168,4 · 217,0 t/s | ×1,79 · ×2,20 · ×1,13; całość ×3,38 vs no-spec |
| WMMA: start sum od bitów 12582912.0f (bez `v_cvt`), redukcja fal kafel po kaflu | prefill 590 t/s | 596 t/s | +1% (kafle MT2 NT4 / MT4 NT2 / MT4 NT4 wolniej: 511 / 436 / 126, rejestry) |
| GEMM z kaflem bloku 64 × 64 w LDS (wagi dekodowane raz na blok, potok dekodowania) | 596 t/s | 606 t/s | +1,7% (128 × 64: 551 i 453; bez `unroll 1` spill do 1692 B/lane) |
| `mtp_store` całego kawałka 64 naraz (WMMA zamiast 8 × GEMV) | 606 t/s | 623 t/s | +2,8% (bez MTP 634) |
| GEMV weryfikacji: 1 wiersz na falę dla N=2..5 | krok spec K=3 26,95 ms; 98,95 t/s (512 tok.) | 26,60 ms; 100,25 t/s | +1,3% (N=2/4/5: 22,84/24,53/27,39 → 22,40/24,08/26,48 ms) |
| przełączniki HIP dla grafów (`HIP_FORCE_DEV_KERNARG`, `DEBUG_CLR_GRAPH_PACKET_CAPTURE`, `GPU_MAX_HW_QUEUES`) | dekod 44,67 t/s | 44,65–44,68 | 0 (odrzucone) |
| **flash-decoding** (16 kawałków kluczy + scalanie, od kontekstu > 512) | dekod przy 2048 / 3800 tok. 41,90 / 39,13 t/s | 44,67 / 44,14 t/s | **+6,6 / +12,8%** |
| atencja prefillu z K/V wspólnymi dla 6 głów q (GQA) | prefill 2048 / 3800 tok. 583,9 / 536,6 t/s | 595,1 / 562,1 t/s | +1,9 / +4,7% |
| RMSNorm w prologu GEMV (bez kernela normy) | dekod 45,74 t/s | 25,91 t/s | −43% (odrzucone; każdy z ~2–4 tys. bloków powtarza normę) |
| flash-attention prefillu na WMMA f16 + podział kluczy na 8 bloków | prefill 3800 tok. 562,2 t/s; serwer 8263 tok. 504,1 t/s (TTFT 16,4 s) | 604,6; 585,3 t/s (TTFT 14,1 s) | +7,5%; **+16,1%** |
| GEMM prefillu na f16 WMMA (wagi dekodowane do f16 w LDS, bez epilogu skal) | prefill 512 tok. 626 t/s | 431 t/s | −31% (odrzucone: dekodowanie i synchronizacja bez potoku) |
| weryfikacja do 16 tokenów na GEMV (dokładna jak dekod; pod ogon lookupu) | krok N=8 32,1 ms | N=16 59,3 ms | odłożone: dot4 przy 16 kolumnach liczeniowo ograniczony; produkcja (MMQ) płaci +6,4 ms |
| **ponowne użycie prefiksu w rozmowie** (Gemini r7) | TTFT tury 2/3 przy promptcie ~2k: 3395 / 3500 ms | 99,7 / 99,4 ms | **×34–35** (`cache_n` 2033 / 2092) |
| KV cache w F16 jak llama.cpp (wyzwanie Gemini r7) | KV 68 KB/token; dekod 8263 tok. 43,66 t/s | 34 KB/token; 44,30 t/s | −50% pamięci KV, +1,5% |
| aktywacje prefillu jak Q8_K (skala na 256) + epilog całkowity w GEMM | prefill 512 tok. 626 t/s | 510 t/s | −19% (odrzucone: dodatkowe kernele, 192 VGPR) |
| `k_gdn_conv_norm`: wagi conv w rejestrach + wejścia następnego tokenu ładowane w tle | prefill 626,3 t/s; krok spec K=3 26,68 ms | 632,0 t/s; 26,41 ms | +0,9%; +1,0% |
| `accept()` jako graf HIP | accept 0,50 ms | 0,50 ms | 0 (koszt to praca GDN, nie uruchomienia) |
| kafle GEMM prefillu: więcej tokenów na falę / blok 128 wierszy / kafel B w LDS | 632 t/s | 484–628 t/s | wszystkie wolniej (rejestry, LDS); optimum lokalne ~632 t/s po 8 wariantach |
| `k_norm_q8` bez LDS, jedna bariera, int8 z rejestrów | krok spec 26,41 ms | 26,36 ms | w szumie, bit w bit, uproszczenie |
| przekwantowanie macierzy tylko-draftu Q6_K → Q4_K (`TURBO_DRAFT_Q4`) | — | nieprzetestowane | szacunek +~1,9% spec; jaroserverai offline od ~19:22 |
| **sprzężony Gumbel-max przy T>0** (Gemini r6: serwer + kontrakt; Kernel: `mtp_draft_n_coupled` na karcie) | T=0,7 kreatywne 72,59 t/s, akceptacja 0,55 | **81,95 t/s, 0,66** | **+12,9%**, tekst spec == bez spec bit w bit (6/6 przy T=0,7 i 1,0) |

Serwer po ping-pongu (`test_serve --compare-spec`, 5/5 bit w bit): kod C++ 191,98 t/s (×4,65), Python 168,02 (×4,07), krótkie odpowiedzi 76–90 t/s; T=0,7: 43,2 → 66,8–70,8 t/s.

Lekcja (pomiar): każda zmiana numeryki przestawia 128-tokenowy tekst testu spec i akceptację o ±0,02 (np. 0,63 → 0,61), więc spekulację porównujemy po ms/krok, a prefill na 512 tokenach po rozgrzewce (stary „prefill 64 tok” liczył przechwycenie grafu, ±10%). Lekcja (para): Gemini w rundzie 5 znalazł prawdziwy błąd Kernela (wiersz ukryty `% 8` po przejściu na kawałki 64), którego bramki nie łapały, bo tekst zostaje bezstratny, a spada tylko akceptacja.

Lekcja (cache promptu): tekst z cache prefiksu może różnić się od pełnego prefillu, bo odpowiedź poprzedniej tury przeszła przez dekod (GEMV), a w pełnym prefillu przez GEMM WMMA (inne zaokrąglenia); llama.cpp ma tę samą własność. Właściwe kryterium to cache == odtworzenie tymi samymi ścieżkami (Gemini r8).

Lekcja (dokładność a szerokość weryfikacji): u nas spec == plain bit w bit, bo weryfikacja N ≤ 8 i dekod liczą te same sumy (GEMV). Szeroka weryfikacja przez WMMA byłaby tania, ale ma inną kolejność sum float; produkcja llama.cpp to akceptuje (MMQ vs MMVQ, porównanie md5 tekstu). Tani W16 przy zachowaniu bit w bit wymaga dekodu przez ten sam układ sum co WMMA.

Porównanie z produkcją llama.cpp topka-q70 na tych samych promptach (2026-11-20, `xbench.py`, t/s, Turbo / produkcja): copy-edit Python 190,0 / 177,3 (+7%), C++ 218,1 / 182,8 (+19%); T=0,7 opowiadanie 70,4 / 91,9 (−23%); prompt 2k prefill 614,6 / 881,6, dekod 85,4 / 158,9; prompt 8k prefill 584,4 / 933,2, dekod 83,1 / 139,8. Produkcja: MTP n=4, głowica MTP IQ4_XS tylko dla draftu, lookup w łańcuchu MTP (`LLAMA_SPEC_LOOKUP=3`, okno 16), sprzężone losowanie. Turbo wygrywa na kopiach kodu, przegrywa na długich promptach (lookup z promptu) i prefillu.

Długi kontekst (`test_serve --bench-long`, 27B XTX): prompt 1989 tok. prefill 593 t/s, TTFT 3,35 s, dekod 45,5 → spec 83,3 t/s; prompt 8263 tok. prefill 504 t/s, TTFT 16,4 s, dekod 43,8 → spec 84,4 t/s (llama.cpp produkcja: pp4096 1115 t/s). Gemini r7: ponowne użycie prefiksu w rozmowach wieloturowych.

Lekcja (flash-decoding): decyzja „dzielić czy nie” musi zależeć od pozycji tokenu, nie od partii. Pierwsza wersja wybierała graf po końcu partii, więc weryfikacja spec dzieliła atencję wcześniej niż dekod pojedynczy i tekst spec rozjechał się z plain od tokenu 545 (test `spec` to złapał). Teraz token z n_kv ≤ progu liczy jeden kawałek, co daje bity identyczne z kernelem jednoprzebiegowym. Spec przy K=2..5 (512 tok., p_min 0,5): 92,3/98,9/98,3/101,3 t/s.

Profil prefillu 512 tok. (rocprofv3): GEMM WMMA 80% czasu przy ~39 TOPS (≈32% szczytu iu8 XTX), GDN 8,6%, atencja 2%. Przy ~600 t/s ogranicza epilog skal Q4_K/Q6_K (~4 VALU na element na 32 kolumny) i rejestry, nie dekodowanie ani ładowanie wag. llama.cpp produkcja: pp512 856, pp4096 1115 t/s.

Profil dekodu 27B (rocprofv3, po zmianach): GEMV średnio ~89% pasma (gate/up 877 GB/s, lm_head Q6_K 908, ffn_down 835–850, ssm_out/wo ~650 GB/s); poza GEMV ~3,8 ms/token, z czego przerwy między ~640 kernelami ~2,3 ms (mediana 3,6 µs). Lekcja: na RDNA3 synchronizacja między blokami (fence + atomik) kosztuje więcej niż przerwa między kernelami w grafie; zysk daje tylko łączenie kerneli, które i tak dzielą dane w jednym bloku.

Rozkład kroku spekulacji (K=2): draft MTP 1,69 ms, weryfikacja 25,45 ms (90%), argmax na hoście 0,26, accept 0,67, razem 28,07 ms. Weryfikacja N=1/2/4/5/8: 23,3/24,7/26,4/28,5/33,7 ms. Dźwignią jest przejście celu (GEMV 86% pasma i ~2,4 ms przerw między ~640 kernelami na token), nie draft.

Lekcja (błąd złapany po akceptacji): komentarz połknął przesunięcia `tk*…` w `k_mtp_in`, więc przebiegi MTP z N>1 pisały jeden wiersz. Test spekulacji dalej mówił „identyczne 128/128”, bo przy bezstratnej weryfikacji tekst jest zawsze ten sam; spadła tylko akceptacja 0,55 → 0,32. Akceptacja to sygnał jakości draftu i trzeba ją pilnować obok identyczności tekstu.

Lekcja (agenci): każdy agent we własnym worktree. Niezacommitowane edycje Gemini psuły build przesyłany rsync-iem na kartę; od rundy 4 Kernel pracuje w gałęzi `kernel`, Gemini w `main`. Limity: Gemini 4 Argon wyczerpany (~164 h), Neon High wyczerpał limit godzinny w rundzie 5 (reset ~1 h).

## Powiązane
- [[audyt-gemini-2026-11-19]]
- [[bramka-kld-kanarki]]
- [[kernelbench]]
