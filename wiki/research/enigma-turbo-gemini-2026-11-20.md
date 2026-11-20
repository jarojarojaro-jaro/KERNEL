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

Serwer po ping-pongu (`test_serve --compare-spec`, 5/5 bit w bit): kod C++ 191,98 t/s (×4,65), Python 168,02 (×4,07), krótkie odpowiedzi 76–90 t/s; T=0,7: 43,2 → 66,8–70,8 t/s.

Profil dekodu 27B (rocprofv3, po zmianach): GEMV średnio ~89% pasma (gate/up 877 GB/s, lm_head Q6_K 908, ffn_down 835–850, ssm_out/wo ~650 GB/s); poza GEMV ~3,8 ms/token, z czego przerwy między ~640 kernelami ~2,3 ms (mediana 3,6 µs). Lekcja: na RDNA3 synchronizacja między blokami (fence + atomik) kosztuje więcej niż przerwa między kernelami w grafie; zysk daje tylko łączenie kerneli, które i tak dzielą dane w jednym bloku.

Rozkład kroku spekulacji (K=2): draft MTP 1,69 ms, weryfikacja 25,45 ms (90%), argmax na hoście 0,26, accept 0,67, razem 28,07 ms. Weryfikacja N=1/2/4/5/8: 23,3/24,7/26,4/28,5/33,7 ms. Dźwignią jest przejście celu (GEMV 86% pasma i ~2,4 ms przerw między ~640 kernelami na token), nie draft.

Lekcja (błąd złapany po akceptacji): komentarz połknął przesunięcia `tk*…` w `k_mtp_in`, więc przebiegi MTP z N>1 pisały jeden wiersz. Test spekulacji dalej mówił „identyczne 128/128”, bo przy bezstratnej weryfikacji tekst jest zawsze ten sam; spadła tylko akceptacja 0,55 → 0,32. Akceptacja to sygnał jakości draftu i trzeba ją pilnować obok identyczności tekstu.

Lekcja (agenci): każdy agent we własnym worktree. Niezacommitowane edycje Gemini psuły build przesyłany rsync-iem na kartę; od rundy 4 Kernel pracuje w gałęzi `kernel`, Gemini w `main`. Limity: Gemini 4 Argon wyczerpany (~164 h), Neon High wyczerpał limit godzinny w rundzie 5 (reset ~1 h).

## Powiązane
- [[audyt-gemini-2026-11-19]]
- [[bramka-kld-kanarki]]
- [[kernelbench]]
