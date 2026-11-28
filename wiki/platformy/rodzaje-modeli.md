---
typ: platforma
tags: [platformy, modele, spekulacja, moe, gdn]
aktualizacja: 2026-11-28
zrodlo: wiki/testy/skill-io-sufity.md:30-40; wiki/optymalizacje/bilans-optymalizacji.md (tabela przyjętych, 2026-11-28); wiki/modele/drafter-dflash.md:25-33; wiki/REKORDY.md:31,203,243,276-279,301-307; wiki/KOLEJKA-TESTOW.md:84-109,348,493,1412; wiki/modele/inkling-2-mini.md; wiki/testy/2026-11-27-k204-enigma-16gb-inkling.md; wiki/testy/2026-11-28-k207-ablacja-zamiast-lora.md; wiki/modele/bonsai-2-5-uncensored.md; wiki/modele/lfm2-5-24b-a2b.md; wiki/log.md:838,870
status: aktualne
---
# Rodzaje modeli: kolejność pracy i nasze dowody

**Każdy rodzaj modelu ma inny składnik, który dominuje w kroku. Pierwsze dźwignie wybieramy po zmierzonym zysku, a główną liczbą jest zawsze czat z pełnym stosem spekulacji.**

## Dense 27B (Qwen3.8-27B)
- **Krok:** odczyt ok. 16,5 GB wag na przebieg. Plain 43,2 t/s to 76% sufitu na XTX. Krok MTP 26,9 ms przy sufitu 19,2 ms ([[skill-io-sufity]]).
- **Dźwignie po zysku:**
  1. MTP n4: 43,2 → 119–127 t/s (czat T=1).
  2. Lookup W16 dla kopii i edycji: mvs 400,9 t/s wobec 170,0 bez lookupu ([[REKORDY]]:31,34).
  3. FA `kvq` na KV q4_0: 94k 43,0 → 70,9 t/s (+65%, [[fattn-kvq]]).
  4. MMVQ wielokolumnowe: MTP 68,6 → 82,3. Fuzje weryfikacji: 74,8 → 86,4 ([[bilans-optymalizacji]]).
  5. DFlash2 tylko dla kodu i EN: po polsku 65 vs MTP 78 t/s. n = 15 daje średnio 97,9 < MTP 108,8 ([[drafter-dflash]]).
- **Bramki:** md5 T=0 z drafterem = bez, KLD KV q4 vs f16 (`kld_gate.py`), igły przy 262k.
- **Co zabija:** głęboki draft na prozie PL, VRAM przy 16 GB (Q4_K_M się nie mieści, więc IQ3_XXS).

## MoE A2B/A3B (LFM2.5-24B-A2B, Qwen3.6-35B-A3B)
- **Krok:** mało bajtów (LFM ok. 1,8 GB/token, sufit ok. 500 t/s), więc dominuje liczba kerneli i matvec ekspertów. Narzut matvec 718 µs/token ([[lfm2-5-24b-a2b]]).
- **Dźwignie (LFM, XTX):**
  1. Fuzje MoE: 5,067 → 3,973 ms/token.
  2. PM4 replay: 3,887 → 3,424 ms/token.
  3. Fuzje shortconv: −0,366 ms/token.
  4. Szybki sampler: 254,2 → 294,3 t/s.
  5. MMVQ n=1 po 2 wiersze: +2,2% (3090 +8,5%) ([[bilans-optymalizacji]]).
- **Offload `--n-cpu-moe`:** 3080 LFM 131k 20,4 → 40,83 t/s po doborze ncm ([[REKORDY]]:203). Na 5060 Ti `-ncmoe 3` daje 60,0 t/s, `--moe-cache-mib` −55%, Strata auto −27% ([[2026-11-27-nvq5]]).
- **Bramki:** KLD KV (LFM q8_0: 0,044; q4_0: 0,128), J5 TTFT 32k ≤ 120 s przy offloadzie.
- **Co zabija:** spekulacja przy ekspertach w RAM. Inkling `-ncmoe 12`: bez draftu 15,7, n1 9,2, n4 6,0 t/s (K-026). LFM nie ma draftera.

## Hybryda GDN (Qwen3.8)
- **Krok:** weryfikacja GDN i stan rekurencyjny cofany przy odrzuceniu.
- **Dźwignie:**
  1. GDN replay: 793 → 638 µs na weryfikację, stan 748 → 195 MiB ([[gdn-replay]]).
  2. Checkpointy GDN w VRAM: TTFT 2k −22%, druga tura 687 → 197 ms.
  3. Fuzje GDN: pp2048 +2,4%.
  4. K-047, osobny kernel weryfikacji: +0,3–0,4% wall, md5 identyczne ([[REKORDY]]:276).
- **Bramki:** okna weryfikacji bitowo = dekod, `test-backend-ops`.
- **Co zabija:** adaptacyjna głębokość zmienia md5 greedy ([[bilans-optymalizacji]]).

## Ternary (Bonsai 2.5 27B, Q2_0 / PTQ1_0)
- **Krok:** 5,99 GB wag, więc rosną udziały hosta, dekodu trytów i draftu.
- **Dźwignie:** nasza topka zamiast silnika prism (77,7 → 116,9 t/s przy T=0,7, +50%) i MTP n2. Plain 54,9 → 76,9. Lookup daje edycję kodu 446 t/s ([[bonsai-2-5-uncensored]]).
- **Bramki:** KLD 0,000000 do bazowego portu, odmowy 0/24 według AtomicChat.
- **Co zabija:** głęboki draft, bo krok jest tani, a weryfikacja kosztuje względnie dużo (n2 zamiast n4).

## Inkling 2 Mini (MoE z pętlą warstw)
- **Krok:** liczba kerneli (ok. 7700 na token), nie pasmo: stock 26,9 t/s mimo ok. 3,3 GB/token ([[inkling-2-mini]]).
- **Dźwignie:**
  1. Silnik Maya zamiast llama.cpp: plain 93,6 vs nasze 49,5 t/s.
  2. Drafter DSpark w Mai: K-158g wall T=0 112,8 → 142,5. K-158s T=0,7 112,7 → 147,7 (+31%).
  3. K-200 natywne WMMA uwagi na KV q4: 90k 80,8 → 105,6 (+30,7%).
  4. Ablacja zamiast LoRA: +41% (EPYC), +15–28% (Ryzen), odmowy 0/5 (K-207).
  5. IQ3_S GSQ na 1M: K-206 wall 67,8 → 104,2 (+54%) bez straty, KL 0,0019.
- **DSpark vs MTP:** Inkling nie ma głowicy MTP, więc drafterem jest DSpark. W llama.cpp najlepsze n2: +104% nad przepisem Qwena (K-204), n4 słabsze.
- **Kontekst z drafterem:** `IK2_DRAFT_CTX=131072` daje 557 056 przy igłach 5/5. Jako dźwignia prędkości K-194 KILL: akceptacja 0,24 → 0,16–0,20.
- **Bramki:** md5 z drafterem = bez. K-208 złapał okna sufiksowe, które nie były bitowe. Do tego igły 5/5, odmowy 0/5, KL z ramieniem podłogi.
- **Co zabija:** LoRA w locie (−17–33% dekodu), stratna konwersja Q8 (KL 0,013), KV draftera q4 (OOM na 1. zapytaniu), `--n-cpu-moe` ze spekulacją.

## Powiązane
- [[procedura-nowy-model-znana-karta]]
- [[procedura-znany-model-nowa-karta]]
- [[bilans-optymalizacji]]
- [[lekcja-mierz-z-drafterem]]
- [[TOPKI]]
