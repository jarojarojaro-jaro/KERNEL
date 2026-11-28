---
typ: platforma
tags: [platformy, amd, rdna4, gfx1201, rx-9070-xt, r9700]
aktualizacja: 2026-11-28
zrodlo: wiki/karty/rx-9070-xt.md; wiki/karty/radeon-ai-pro-r9700.md; wiki/ekosystem/saber-engine.md:10,21; wiki/optymalizacje/skill-io-dzwignie.md:54,64-71; wiki/optymalizacje/fattn-kvq.md:38; wiki/optymalizacje/wmma-small-n.md:27; wiki/platformy/amd-rdna3-gfx1100.md
status: aktualne
---
# AMD RDNA4 gfx1201 (RX 9070 XT, Radeon AI PRO R9700): playbook

**Ten sam Navi48 z 640 GB/s (16 GB w 9070 XT, 32 GB w R9700); u nas brak pomiaru, a nasze kernele WMMA z gfx1100 trzeba tu portować, więc kolejność zaczyna się od logiki hosta i spekulacji.**

Topki: [[TOPKI]]. Wzorzec kolejności: [[amd-rdna3-gfx1100]].

## Dzień pierwszy
- Sprzęt: R9700 na godziny w Hostkey (€0,471/h) ([[radeon-ai-pro-r9700]]); 9070 XT w planie zakupu ([[rx-9070-xt]]).
- ROCm: ten sam 10.0 co na XTX (TheRock wydaje koła per rodzina gfx, [[therock]]); wersja jądra na wynajętym hoście: brak pomiaru, zapisać `uname -r`.
- PM4: `GGML_HIP_PM4=0` zawsze. Taśma jest tylko nasza i tylko gfx1100; na RDNA4 nie przenosi się bez osobnego testu ([[skill-io-dzwignie]], [[lekcja-pm4-zawsze-jawnie]]).
- Build: na zdalnym hoście `cmake -DAMDGPU_TARGETS=gfx1201`; u nas przez `rbuild` + `cpuheavy` ([[2026-10-19-buildy-przez-rbuild]]). Bez strażnika `gpu-guard` na obcym hoście pilnować `dmesg` ręcznie.
- Zegary fabryczne, bez OC.
- Sufit pasma: 640 GB/s ze specyfikacji; Saber zmierzył szczyt DRAM 635 GB/s na R9700 ([[saber-engine]]).
- Sanity: gęsty Qwen 27B w llama.cpp 29,7–30,9 t/s (ok. 71% pasma, Lucebox); Llama 2 7B Q4_0 tg Vulkan 138,8 vs ROCm 7.2 98,0 (raport AMD, 07/2026) ([[radeon-ai-pro-r9700]]). Nasz pomiar: brak.

## Kolejność optymalizacji
Zyski z XTX są szacunkiem do sprawdzenia, nie pomiarem na RDNA4:
1. Spekulacja MTP n4 + słownik 64k (na XTX ×2,5) i drafter: logika hosta, przenosi się od razu.
2. Sampler fast path, luki hosta, K-020 wyrzucanie cache kosztem (XTX −51% replay agenta): bez zmian.
3. FA na KV q4_0 (XTX +65% przy 94k): kod tylko gfx110x, RDNA4 wymaga portu na układ operandów WMMA gfx12 ([[fattn-kvq]]).
4. MMVQ wielokolumnowe i WMMA small-N: port, bo inny układ WMMA ([[wmma-small-n]]). `__byte_perm` → `v_perm_b32` dało +15% dekodu na R9700 (46,0 → 53,0 t/s, [[radeon-ai-pro-r9700]]).
5. FA D256, K-012, K-047: port po 3–4.
6. Maya: K-200 (uwaga WMMA) wymaga portu; K-185 i K-158s to host + kernele ekspertów, przenoszą się.
7. Grafy HIP zamiast PM4.
- Raport 07 (szacunek): łatki ogólne +5–10%, kampania WMMA gfx12 +30–60% ([[rx-9070-xt]]).

Różnice: WMMA gfx12 ma inny układ operandów niż gfx11 i FP8 (INT8 = 2× FP16); `__syncthreads()` = `s_wait_loadcnt 0` opróżnia prefetch; L2 8 MiB, Infinity Cache 64 MiB (XTX: 6 / 96 MiB), więc KV długiego kontekstu rzadziej siedzi w cache. FP8 nie zmienia kwantu (zakaz), tylko format obliczeń.

## Testy
- Te same skrypty co na XTX: `spec_sweep.py`, `long_ctx_bench.py`, `nib/wall.py` ABBA, `k202srv.py` (igły), `IK2_K158_BENCH=1` ([[spec-sweep]]).
- Przed każdym portem: `test-backend-ops` (MUL_MAT, FLASH_ATTN_EXT, GATED_DELTA_NET) na kształtach produkcji, md5 T=0 vs upstream na tej samej karcie, KLD ([[bramka-kld-kanarki]]).
- Kolejka `kol`/`kolp` dotyczy tylko jaroserverai; na wynajętym hoście osobny skrypt chmury.

## Kiedy topka jest gotowa
Pełny stos ze spekulacją, KV q4, pełny kontekst (16 GB: tyle, ile się mieści; 32 GB: pełne 262 144), igły 5/5, md5/KLD PASS, wall bez regresji, liczba w [[REKORDY]] z datą i ścieżką logu.

## Pułapki
- Mikrobench kernela nie decyduje ([[lekcja-mikrobench-klamie]]).
- Port WMMA zmienia kolejność sum: FMA contraction ([[lekcja-fma-kontrakcja-bitowa-zgodnosc]]).
- Akceptacja draftu z jednej karty nie przenosi się ([[lekcja-akceptacja-h100-nie-przenosi-sie]]).
- Liczby AMD/społeczności (152,7 t/s = 91% pasma) oznaczone jako niezweryfikowane.

## Rodzaje modeli
- Gęsty 27B / GDN hybrid: na 16 GB najpierw zmieścić MTP i kontekst ([[lekcja-fit-mtp-16gb]]), potem spekulacja.
- MoE A2B/A3B: na 16 GB najkorzystniejsze; lookup ważniejszy niż MTP.
- Ternary: kernele Q2_0 z topki-k157 to WMMA/MMVQ gfx11, port.
- Inkling: Maya wymaga portu kerneli; do tego czasu llama.cpp z DSpark.

## Powiązane
- [[radeon-ai-pro-r9700]]
- [[rx-9070-xt]]
- [[saber-engine]]
- [[amd-rdna3-gfx1100]]
