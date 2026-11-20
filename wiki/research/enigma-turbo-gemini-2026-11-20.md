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

## Powiązane
- [[audyt-gemini-2026-11-19]]
- [[bramka-kld-kanarki]]
- [[kernelbench]]
