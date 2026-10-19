---
typ: produkt
tags: [produkt, decyzje, silnik]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/app/REPORT.md:92-109; ~/KERNEL/product/PLAN.md:491-499; ~/KERNEL/product/research/15c-nowe-silniki.md:395; ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:122; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:146-149,547; ~/KERNEL/product/research/12-bit-exact-spekulacja.md:334-343,340-342; ~/KERNEL/product/research/16e-kwanty-kld.md:282-292; ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:10; ~/KERNEL/product/research/16f-xtx-szybkie.md:19-45,238; ~/KERNEL/product/research/16b-lookup-tail.md:163-165; ~/KERNEL/product/research/17-gpu-page-fault.md:22-26; ~/KERNEL/product/research/21h-rsi.md:340-363,483-525
status: aktualne
---
# Otwarte decyzje techniczne (silnik, flagi, wydatki)

**Rekomendacje agentów, które czekają na decyzję użytkownika: zmiany flag `run-llm.sh`, scalenie łatek do `amd-opt`, testy GPU z ryzykiem i wydatki na chmurę; po decyzji wiersz przechodzi do [[decyzje/_hub|decyzji]].**

| temat | stan | do decyzji |
|---|---|---|
| tryb „identyczne odpowiedzi” | gałąź `batch-invariant` @ `365af3e5e`, przełącznik wyłączony = produkcja | opt-in `LLAMA_SPEC_BITEXACT=1`? MTP 0% krótki, −9% przy ~27k ([[2026-10-16-bit-exact]]) |
| model 16 GB | UD-Q3_K_XL (U3) | AP-Q3_K_XL po bramce? KLD czat −12%, kod −23% ([[2026-10-18-e1-kwanty-27b-kld]]) |
| model 12 GB | Saluki/Bonsai | IQ3_XXS-mtp (Swift W3 lub ISTA)? KLD-PL 0.108 vs 0.320 |
| łatka 0071 `GGML_HIP_MOE_GU_BLOCK` | gałąź `opt-lfmmoe` @ `7c5b2a116`, poza produkcją | scalić, domyślnie wł.? bitowa, LFM +0.33%, Uncensored +1.39% ([[2026-10-18-lfm-moe-pasmo]]) |
| flagi `run-llm.sh` (16f) | bez zmian | LFM `-ub 2048` (+17% prefillu) i `CACHE_SHARE_MIN=1024` ([[raport-16f-xtx-szybkie]]) |
| ogon lookupu dla Qwena (16b) | gałąź `lookup-tail`, poza produkcją | `LLAMA_SPEC_LOOKUP=3`, `_W=16` (mvs ×2.41) po tygodniu logu `=1` na ruchu omp ([[raport-16b-lookup-tail]]) |
| PM4 w serwerach (raport 17) | `~/llama-opt` z PM4 domyślnie (~1 reset/330 req.) | `GGML_HIP_PM4=0`? (−4.7% / −12%); testy S1–S6, `HSA_USE_SVM=0` ([[2026-10-19-pm4-priv-analiza]]) |
| RSI-F pilot P0/P1 (21h) | fabryka bez werdyktu na GPU | P0 ~20 min + P1 ~60–80 min GPU XTX, $0 ([[petla-rsi-f]]) |
| E1: RSR-27B vs Qwen (21h) | niezmierzone | ~$40–70 na wynajętych 3090 ([[2026-10-19-plan-e1-rsr27b]]) |

## Powiązane
- [[produkt/_hub|produkt]]
- [[otwarte-decyzje-produktu]]
- [[REKORDY]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
