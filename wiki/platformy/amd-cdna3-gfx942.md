---
typ: platforma
tags: [platformy, amd, cdna3, gfx942, mi300x]
aktualizacja: 2026-11-28
zrodlo: wiki/karty/mi300x.md; wiki/karty/amd-dev-cloud.md; wiki/optymalizacje/skill-io-dzwignie.md:55,64-71; wiki/platformy/amd-rdna3-gfx1100.md
status: aktualne
---
# AMD CDNA3 gfx942 (MI300X): playbook

**Datacenterowy CDNA3 z wave64 i MFMA; nie jest rynkiem produktu, służy do sanity-checku wspólnego kodu HIP z darmowego kredytu, a u nas wciąż brak pomiaru.**

Topki: [[TOPKI]]. Wzorzec kolejności: [[amd-rdna3-gfx1100]].

## Dzień pierwszy
- Dostęp: AMD Developer Cloud ($100 na 30 dni; warunki komercyjne do zapytania AMD), RunPod Secure $2,39/h ([[amd-dev-cloud]], [[mi300x]]).
- ROCm: ten sam 10.0 co na XTX, jeśli obraz pozwala; wersję ROCm i jądra zapisać z hosta (brak pomiaru).
- PM4: `GGML_HIP_PM4=0`. Taśma jest tylko dla gfx1100 i nie przenosi się na CDNA bez testu ([[skill-io-dzwignie]]).
- Build: `-DAMDGPU_TARGETS=gfx942`; u nas `rbuild` i `cpuheavy` tylko do kompilacji krzyżowej przed wynajmem ([[lekcja-build-przed-wynajmem]]). `gpu-guard` nie działa na obcym hoście: ręcznie `dmesg` / `amd-smi`.
- Zegary fabryczne.
- Sufit pasma: 5,3 TB/s HBM3 ze specyfikacji producenta; nasz pomiar: brak. Infinity Cache 256 MiB, LDS 64 KiB na CU ([[mi300x]]).
- Sanity: brak naszego pomiaru tg/pp; pierwszy bieg = llama-bench tg128/pp4096 Qwen3.8-27B upstream vs topka.

## Kolejność optymalizacji
1. Spekulacja MTP n4 + słownik 64k, drafter: logika hosta, przenosi się. Przy 5,3 TB/s krok dekodu jest krótki, więc rośnie udział hosta: sampler fast path i luki hosta (XTX 113,8 → 117,9) ważą więcej.
2. K-020 wyrzucanie cache kosztem: bez zmian.
3. FA kvq, MMVQ wielokolumnowe, FA D256, K-012, K-047, K-200: kernele WMMA wave32 z gfx11; na CDNA3 przepisanie na MFMA wave64 (osobne AccVGPR, 4× SIMD16 na CU). Alternatywa: CK/AITER na CDNA zamiast naszej FA ([[skill-io-dzwignie]]).
4. Kafle FA/MMQ strojone pod gfx1100 nie pasują do CDNA; strojenie per karta.
5. Grafy HIP zamiast PM4.
Zysków z XTX nie przenosimy liczbowo: brak pomiaru.

## Testy
- `test-backend-ops` (MUL_MAT, MUL_MAT_ID, FLASH_ATTN_EXT, GATED_DELTA_NET) — główny cel: czy wspólny kod HIP liczy poprawnie przy wave64.
- md5 T=0 vs upstream na tej samej karcie, KLD ([[bramka-kld-kanarki]]).
- `spec_sweep.py`, `long_ctx_bench.py`, `nib/wall.py` ABBA, `k202srv.py` igły — te same skrypty co na XTX ([[spec-sweep]]).

## Kiedy topka jest gotowa
Dla produktu nie jest potrzebna. Jeśli robimy: pełny stos ze spekulacją, KV q4, pełny kontekst modelu (192 GB HBM mieści każdy nasz model), igły 5/5, md5/KLD PASS, wpis w [[REKORDY]].

## Pułapki
- Kod z `warpSize == 32` na sztywno psuje redukcje przy wave64.
- FMA contraction zmienia bity po przepisaniu na MFMA ([[lekcja-fma-kontrakcja-bitowa-zgodnosc]]).
- Mikrobench nie decyduje ([[lekcja-mikrobench-klamie]]).
- Godziny płatne: build przed wynajmem ([[lekcja-build-przed-wynajmem]]).

## Rodzaje modeli
- Gęsty 27B / GDN hybrid: przy tym paśmie host i launch overhead dominują; spekulacja i grafy pierwsze.
- MoE A2B/A3B: bardzo małe kroki, koszt hosta jeszcze większy; lookup.
- Ternary i Inkling: Maya i kernele Q2_0 są pod wave32 gfx11, wymagają przepisania; do tego czasu llama.cpp upstream z DSpark.

## Powiązane
- [[mi300x]]
- [[amd-dev-cloud]]
- [[skill-io-dzwignie]]
- [[amd-rdna3-gfx1100]]
