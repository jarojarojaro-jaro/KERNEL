---
typ: ekosystem
tags: [ekosystem, spekulacja, dflash]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/22-lucebox.md:1-55; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:32; ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:3-14,49-56,64-82,254
status: aktualne
---
# Luce-Org/lucebox

**Serwer inferencji C++ z forkiem ggml i spekulacją DFlash2 (HEAD `54132ca`, 2026-10-14) na tym samym modelu i drafterze co my; werdykt: średnia.**

Ich pomiar (R9700, Qwen3.8-27B UD-IQ4_XS, T=0, HumanEval-10): DFlash2 blok 8 133.9 → blok 16 208.1 t/s, bajtowo jak AR; plain AR 32.3. Od 8K tokenów weryfikacja cięta do 8. Na RTX 3090: decode 413 vs 267 t/s llama.cpp (1.55×). Dla nas Q1: zdjąć przycięcie `n_max` w `common/speculative.cpp`, szacunek 175–300 t/s na kodzie zamiast ~110–130; oraz `LLAMA_ATTN_ROT_DISABLE=1` przy KV q8_0 (~1.5%, zmienia numerykę). To lucebox polecił hipfire.

## Aktualizacja 2026-10-16 (HEAD `6f2b179`, raport 15d)
- **PFlash v2** (PR #746, merge `c2569a0`): drafter Qwen3.5-0.8B BF16 (sha `cedf89af…`) liczy 15 bloków; sonda segmentów (263k parametrów), sonda żądania (265k) i głowica Q/K NoPE (2.62M) na residualu po bloku 14; budżet z krzywej 16384:0.315 → 120000:0.225; kompresja dopiero przy ≥ 16K niecache'owanych tokenów, sesje z narzędziami surowo. Jakość 92/124 vs 94, LongBench-v2 4/12 vs 7/12 (w PR na L40S 7/12 vs 6/12, czyli szum), MTRAG 189 vs 197 (pełny prefill tylko zamodelowany). TTFT ×3.7 na R9700.
- **KVFlash:** stratny (igła 14/16, zgodność tekstu GSM 8/10); bazowy prefill 694 t/s przy 32K vs llama.cpp 1168 t/s.
- **Dyskowy cache sesji:** sesja 45K po restarcie 2.6 s vs 56.2 s, bajtowo identycznie.
- #457: na gfx1100 `dflash_server` ~2× wolniejszy od llama.cpp.
Werdykt bez zmian (średnia), PFlash: pilot.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): commit `175a98737` (PR #1046, 2026-11-21)
- **Liczby są** (wpis w ZRODLA mówił „brak liczb”): FA-2 WMMA wave32 z pakowaniem GQA (do 6–8× mniej odczytu KV) i split-KV dla weryfikacji nq = 4..32; prefill 2,08–2,56× TFLOPS, weryfikacja D=256 na R9700 2,15–2,53×, drzewo w paged attention 1,50–2,76× (R9700) i 1,11–1,72× (Strix Halo); cały serwer przy 8 równoległych żądaniach na R9700: 160,0 → 188,1 t/s (+17,6%) ([PR #1046](https://github.com/Luce-Org/lucebox/pull/1046)).
- **gfx1100:** kod kompiluje się dla `RDNA3`, ale bramka w `ggml_cuda_fattn_rdna_wmma_supported` wpuszcza tylko RDNA4 i RDNA3.5; KV tylko F16/Q8_0, a nasza produkcja to q4_0 → bezpośrednio nas nie dotyczy. Pakowanie GQA w weryfikacji to ta sama idea co nasza dźwignia nr 1 z [[silniki-inferencji-2026-11-20]] i hipfire #989.
- **Czego uczy o bramce kernela (proces):** PR ma audyt ISA (`private_segment_fixed_size = 0`, czyli zero spill na obu kartach), 25 przypadków różnicowej zgodności (max_diff ≤ 2e-5, 0 NaN, B = 1..8, drzewa 4/8/16, S do 16384) i pełny ctest 166/166 na dwóch kartach. To dobry wzór listy kontrolnej dla nowych kerneli w duecie (u nas spill łapaliśmy po fakcie: [[lekcja-vgpr-limit-hak-spill]]).
- **Serwowanie:** mierzą zysk na całym serwerze przy B = 4–8 z cache 3–5k tokenów, nie tylko mikrobench — tak samo powinniśmy raportować zmiany w topce i Enigmie.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): dysk i własny serwer
- **Dyskowy cache sesji to funkcja ich serwera** (45K po restarcie 2,6 s zamiast 56,2 s, bajtowo). My zmierzyliśmy to samo na XTX (E5: Qwen 53k 2,51 s zamiast ~61,5 s, [[cache-sesji-na-dysku]]), a 19.10 właściciel zdecydował dla naszego serwera „SSD nie ruszamy”, KV tylko w RAM ([[2026-10-19-kv-tylko-w-ram]]). Enigma też tego nie ma: start llama-server bez `--slot-save-path` (`app/engine/src/server/engine.ts:570-576`). Dla użytkownika z długą rozmową restart aplikacji albo silnika to znów pełny prefill (minuta przy 53k). Zużycie SSD rozwiązuje polityka „zapis tylko przy zamknięciu albo presji RAM, top-2 sesje” (~7 GB/dzień, [[kv-na-dysku-polityka]]).
- **Własny serwer przegrywa poza swoją kartą:** `dflash_server` na gfx1100 ~2× wolniejszy od llama.cpp (#457). To ten sam wzór co R03 („własne runtime'y dają rekordy tylko dla wąskiego zestawu modeli”, [[raport-03-silniki]]) i Enigma Turbo.
- Do decyzji właściciela (decyzja 19.10 dotyczyła naszego serwera, nie produktu): zapis slotu przy zamknięciu Enigmy i odczyt przy starcie z tym samym modelem i konfiguracją (odcisk jak w Stracie: [[strata]]).

## Powiązane
- [[hipfire]]
- [[drafter-dflash]]
- [[radeon-ai-pro-r9700]]
- [[repos-30-przeglad]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[hyperqwen]]
