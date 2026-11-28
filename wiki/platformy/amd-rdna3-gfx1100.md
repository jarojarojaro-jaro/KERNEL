---
typ: platforma
tags: [platformy, amd, rdna3, gfx1100, rx-7900-xtx]
aktualizacja: 2026-11-28
zrodlo: wiki/REKORDY.md:18-40,273-302; wiki/stos/topki.md; wiki/optymalizacje/bilans-optymalizacji.md:27-49; wiki/KOLEJKA-TESTOW.md:78-99,119-146,293,348,1373-1379; ~/qwen-opt/topki/xtx/{qwen-uncensored,inkling}.sh (jaroserverai, odczyt 2026-11-28); uname -r na jaroserverai 2026-11-28
status: aktualne
---
# AMD RDNA3 gfx1100 (RX 7900 XTX): playbook

**Nasza karta domowa: ROCm 10.0, jądro 6.8, taśma PM4, fork „topka” i silnik Maya; tu powstała cała kolejność optymalizacji, którą przenosimy na inne Radeony.**

Topki tej karty: [[TOPKI]] i [[topki]].

## Dzień pierwszy
- Stos: ROCm 10.0 (`/opt/rocm/core-10.0`, 10.0.0~pre4) ([[rocm-stos]]); jądro `6.8.0-138-generic` (odczyt 2026-11-28). 10.1/10.2 nic nie dają dla gfx1100 ([[rocm-10-1]]).
- PM4 zawsze jawnie: `GGML_HIP_PM4=0` albo `GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0`; nieustawione = WA=0 i page fault + reset ([[lekcja-pm4-zawsze-jawnie]], [[pm4]]).
- Build tylko `~/qwen-opt/tools/rbuild <worktree> [cele]` ([[2026-10-19-buildy-przez-rbuild]]); ciężkie CPU przez `cpuheavy`, nigdy w etapie joba kolejki ([[lekcja-cpuheavy-w-jobie-kolejki]]).
- `gpu-guard.sh` działa zawsze ([[gpu-guard]]); karta fabrycznie, bez OC, profil eco 2200 MHz (liczby ok. 7% niżej niż stock; porównujemy w jednej sesji) ([[jaroserverai]]).
- Sufit pasma: 960 GB/s ze specyfikacji, 926 GB/s zmierzony odczyt (raport 24r, 2026-10-20) ([[rx-7900-xtx]]).
- Sanity Qwen3.8-27B UD-Q4_K_XL: tg128 43,2 t/s, pp4096 1115–1123 t/s (2026-10-15, REKORDY.md:35-36). LFM2.5 tg128 ok. 292 t/s ([[lfm2-5-24b-a2b]]).

## Kolejność optymalizacji
Historia Qwena (gęsty GDN hybrid) i Inklinga (MoE w Mai):
1. Spekulacja MTP n4 + słownik draftu 64k: plain 43,2 → spec_sweep 109,0 t/s (×2,5, 2026-10-15); słownik +7,5% (bilans:49) ([[glowica-mtp]]).
2. MMVQ wielokolumnowe (weryfikacja okna): MTP 68,6 → 82,3 t/s (bilans:39).
3. FA na KV q4_0 (kvq): dekod przy 94k 43,0 → 70,9 t/s (+65%) (bilans:29).
4. PM4 replay: Qwen 103,7 → 108,8 t/s, przy 1,7k +6,4% (bilans:42; REKORDY.md:25).
5. Sampler fast path i luki hosta: 113,8 → 117,9 t/s (bilans:43,48).
6. FA D256 `GGML_HIP_FA_D256_VAR=83`: fill 255k 466,3 → 493,4 t/s (+5,8%) ([[2026-11-08-fa-d256-prefill]]).
7. K-020 wyrzucanie cache kosztem: replay agenta 207,9 → 101,8 s (−51%); K-012 pary fal kvq: 94k 121,2 → 123,7 t/s (+2,1%); K-047 kernel weryfikacji GDN: wall +0,3…0,4% (REKORDY.md:273-276).
8. Maya (Inkling): K-158g wall 112,8 → 142,5; K-185 141,8 → 152,0 (+7,2%); K-158s drafter dla T=0,7 +31%; K-200 uwaga WMMA na KV q4: 90k +30,7%; K-206 planarne macierze IQ3_S: wall 1M 67,8 → 104,2 (REKORDY.md:274-302).
9. Na końcu pełny kontekst: Qwen 262 144, Inkling 557 056 / 1 048 576 ([[topki]]).

Przenoszalność: 1, 5, 7 (K-020) i drafter to logika hosta, idą wszędzie. 2, 3, 6, K-012, K-200 to WMMA gfx11: RDNA4 wymaga portu operandów, CDNA3 przepisania na MFMA wave64, Strix Halo (gfx1151) bierze je prawie bez zmian (te same bramki gfx115x). PM4 jest tylko nasze i tylko gfx1100 ([[skill-io-dzwignie]]).

## Testy
- Kolejka: `kol pusc/czekaj/wynik`, `kolp JOBS [limit] [summary]` ([[kol]]).
- Szybkie A/B produkcji: `~/qwen-opt/xtxbench/xtxbench.py` (1,7k/94k/199k + prefill, ok. 4 min) ([[xtxbench-szybki-ab]]).
- `~/qwen-opt/spec_sweep.py` ([[spec-sweep]]), `~/qwen-opt/long_ctx_bench.py`, `~/qwen-opt/nib/wall.py` ABBA 8 kategorii.
- Inkling: `~/k134/k202srv.py` (igły 5/5 na głębokości), `IK2_K158_BENCH=1` (księga rundy: propose/verify ms).
- Bramki: md5 T=0 i T=0,7 = produkcja, KLD ([[bramka-kld-kanarki]]), `test-backend-ops` na kształtach produkcji.

## Kiedy topka jest gotowa
Pełny stos ze spekulacją, KV q4 (maks. q6), pełny kontekst przy szczycie VRAM < 24 GiB, igły 5/5 przy 95% głębokości, md5/KLD PASS, wall ABBA bez regresji w żadnej kategorii, wpis w `topki/xtx/<model>.sh` i [[REKORDY]].

## Pułapki
- Maya chodziła miesiąc z 16k kontekstu ([[lekcja-maya-16k-kontekstu]]).
- Kontrakcja FMA psuje bitowość między kernelami: `#pragma clang fp contract(off)` + jawne `fmaf` ([[lekcja-fma-kontrakcja-bitowa-zgodnosc]]).
- Mikrobench daje inną decyzję niż model ([[lekcja-mikrobench-klamie]]).
- K-209: loady nietemporalne w MMVQ topki: weryfikacja −25,6%, wall −24…−26% (KOLEJKA:1379).
- K-210: okna sufiksowe Mai nie były bitowe; dokładna wersja kosztuje −29…−41% kopii, nie wdrożona (KOLEJKA:83).
- Fault w PM4 = reset GPU 9/10; nie zabijać serwera w trakcie ([[lekcja-pm4-zamienia-fault-w-reset]], [[lekcja-nie-zabijaj-pm4-w-trakcie]]).

## Rodzaje modeli
- Gęsty 27B / GDN hybrid (Qwen3.8): spekulacja daje najwięcej, bo weryfikacja czyta wagi raz; potem kvq + K-047 GDN ([[lekcja-dense-szybszy-od-moe-ze-spekulacja]]).
- MoE A2B/A3B (LFM2.5): PM4 ważniejsze (293,7 vs 259,3 bez PM4, [[trwala-siatka-bez-pm4]]), lookup zamiast MTP.
- Ternary (Bonsai Q2_0): topka-k157 + MTP n2: 116,9 t/s ([[bonsai-2-5-uncensored]]).
- Inkling (MoE): Maya, drafter DSpark, eksperci raz na okno (K-185), uwaga K-200 dla długiego kontekstu ([[inkling-2-mini]]).

## Powiązane
- [[rx-7900-xtx]]
- [[rdna3-gfx1100]]
- [[bilans-optymalizacji]]
- [[topki]]
