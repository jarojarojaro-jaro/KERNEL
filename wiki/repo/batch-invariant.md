---
typ: repo
tags: [repo, galezie, determinizm]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master log --format=%h\ %ad\ %s 7a538d96f..batch-invariant
status: aktualne
---
# Gałąź batch-invariant (LLAMA_SPEC_BITEXACT)

**Gałąź `batch-invariant` @ `6e261fdb4` (2026-10-16) = `cuda-v070` + 4 commity: tryb `LLAMA_SPEC_BITEXACT`, w którym dekod spekulacyjny daje te same bity co zwykły.**

Commity: `c09ac6aab` – dekod niezależny od wsadu na RDNA3 (1-kolumnowe MMVQ z arytmetyką wielokolumnową, stały podział KV w FA kvq, bez fuzji GLU dla N=1, ten sam ogon ubatcha), reset MTP `pending_h` per sekwencja; `204f108de` – `llama-bx-diff` (pierwszy węzeł grafu, którego wynik różni się między plain a weryfikacją N tokenów); `77240c9b3` – FA kvq jeden token na blok; `6e261fdb4` – log uruchomień `GGML_HIP_BITEXACT_FA_LOG`. Inspiracja: Thinking Machines (batch invariance).

## Powiązane
- [[repo/_hub|repo]]
- [[galezie-rund]]
- [[cuda-v070]]
- [[2026-10-16-bit-exact]]
- [[thinking-machines]]
- [[llama-bx-diff]]
