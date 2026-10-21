---
typ: repo
tags: [repo, spekulacja, cuda, determinizm]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/15b-spekulacja-frontier.md:22-26,125-148; ~/KERNEL/product/research/15c-nowe-silniki.md:23-27,68-80,166-186,362; ~/KERNEL/product/research/15f-agentowa-nauka.md:58-63; ~/KERNEL/product/research/32f-ninfer-tqllm-dflash2.md:14-22
status: do-sprawdzenia
---
# tqLLM (turbo-tan): silnik CUDA dla Qwen3.8

**Własny silnik C++/CUDA tylko dla Qwen3.5/3.8 na NVIDIA (sm_86/89/120/121) z kwantem TQ3_4S, DFlash2 i dokładną spekulacją greedy; rekord 273.1 t/s na 3090 w LocalMaxxing przy T=0 z prywatnego buildu, a per bajt plain decode ma parytet z nami.**

Repo `turbo-tan/tqllm` @ `23af3c9`, ~57 tys. linii, 15★.
- **LocalMaxxing 3090:** 273.1 t/s reasoning-v1 i 199.5 code-v1 („submitted, approved”), T=0, 320 tokenów, mal 6.15 / 4.56, 22.5 ms/krok przy 13.9 GB/krok; zmierzone prywatnym commitem `8c12e1a`. Na streszczeniach WikiText 131–155 t/s. Plain 55.5 t/s = 77% pasma (my 71–78%). `[do-sprawdzenia]`: brak niezależnych reprodukcji.
- **Exactness:** każdy blok wielkości weryfikacji, łącznie z dekodowaniem N=1, idzie przez te same kernele; punkt podziału atencji zależy tylko od pozycji (`tq_split_point`); matvec testowany `memcmp` przy 1..16 kolumnach. Naprawione dopiero 2026-10-13 (`7d7382b`); błąd wychodził tylko przy niektórych `ubatch` (`-ub 4096`). Dotyczy greedy i 1 slotu.
- **TQ3_4S:** blok 32 wag = 4 skale E3M5 + 3-bitowe kody, wagi w bazie WHT32; KLD TQ_S 0.055, TQ_XS 0.079 vs BF16 (HF YTan2000), TQ3_4S-v2 bez KLD.
- Inne: DFlash2 blok 8 + drzewo z 8 węzłów; MoE per-expert w pinned RAM (`--moe-host-mb`); prefill int8 IMMA na Ampere (pp 2,258 t/s przy 2K vs nasze 1,378–1,410).
- Bramka „near-tie”: pierwszy rozjazd greedy akceptowany, gdy wybrany token jest drugim w FP32 przy marginesie ≤ 0.1 logita (`tests/golden_check.py:1-25`) – kandydat na bramkę fork vs upstream.
- „Agenci zastępują samych siebie”: `[NIEZWERYFIKOWANE]` (repo: 80 commitów, 3 autorów).

## Aktualizacja 2026-10-21
- Rekord 3090 273.1 t/s nieporównywalny (T=0, reasoning-v1, TQ3_4S z KLD gorszym niż UD-Q4_K_XL); luka ×2.2 rozłożona w [[raport-32f-ninfer-tqllm]].

## Powiązane
- [[repo/_hub|repo]]
- [[hyperqwen]]
- [[magnitude]]
- [[raport-15c-nowe-silniki]]
- [[batch-invariant]]
- [[lekcja-benchmark-kopia]]
