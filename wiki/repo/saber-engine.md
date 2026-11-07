---
typ: repo
tags: [repo, rdna4, silnik, spekulacja]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66d-saber-engine-rdna.md:5-149; https://github.com/GGZ14/saber-engine (c8a1e84)
status: aktualne
---
# Saber (GGZ14/saber-engine): silnik Rust + HIP dla R9700

**Przepisanie prywatnego stosu vLLM autora na 1–2 karty R9700 (gfx1201) dla Qwen3.8-27B i Flash-Next; kernele używają builtinów gfx12 (FP8 WMMA, `global_load_tr`), a numeryka jest stratna (MXFP4 W4A8, KV i głowica fp8), więc nic nie uruchomimy, ale cztery projekty są przenośne (raport 66d, 2026-11-07).**

- Deklaracje autora: TP=1 67 / 148 / 231 tok/s (proza / kod / liczenie, T=0, 256 tok., 210 W); TP=2 ~229 tok/s; wątek Reddit (6 645 pp, 316 decode) nieczytelny.
- Decode GEMM: 453 GB/s z 635 w łańcuchu (~71%); nasze MMVQ 81–88% na kernel, więc pętla GEMV nic nam nie daje.
- Przenośne:
  - atencja z falami dzielącymi wiersze Q i wspólnym kaflem KV ([[kv-raz-na-weryfikacje]]);
  - głowica draftu int2 + dokładny rerank top-K ([[glowica-draftu-rerank]]);
  - drzewo weryfikacji z GDN w formie WY ([[drzewo-weryfikacji-gdn-wy]]);
  - lookup „zastąp, gdy pewny” (do sprawdzenia offline; synteza 15 odrzuciła „lookup nadpisujący MTP”).
- Metoda: strojenie „IC-cold” (rotacja buforów + zapis 2× MALL między próbkami); wycofana reguła BK=64 dawała +30% na gorąco i −11% na zimno ([[lekcja-mikrobench-klamie]]).
- ws-h28: upload bloba wielkości pojemności co krok = +6.6 ms/krok ([[maska-kq-host-dlugi-ctx]]).
- Najlepszy publiczny wzorzec operandów WMMA gfx12 i pułapek (`__syncthreads()` opróżnia prefetch) na port topki na RDNA4.

## Powiązane
- [[repo/_hub|repo]]
- [[radeon-ai-pro-r9700]]
- [[rx-9070-xt]]
- [[fattn-kvq]]
- [[raport-66-synteza]]
