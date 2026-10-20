---
typ: decyzja
tags: [decyzje, benchmarki, kontekst]
aktualizacja: 2026-10-20
zrodlo: polecenie użytkownika 2026-10-20 (czat z Main); ~/KERNEL/product/research/27-3090-final.md:211
status: aktualne
---
# 2026-10-20: testy na kontekście minimum 131k

**Użytkownik (2026-10-20): „ma być kontekst minimum 131k do testów, 32k to nie benchmark”. Każdy pomiar karty (U0/U1/T) idzie przy `-c ≥ 131072`, KV q4_0; reguła „≥32k” z kampanii opt-* 2026-10-20 jest nieaktualna.**

Konsekwencje:
- Kwant wybieramy tak, żeby przy 131k został zapas ~0.5 GB po długim prompcie (nie tylko po załadowaniu).
- Narzut przy 131k na Qwen3.8-27B (KV q4_0 + MTP + bufory) zmierzony na 3090: szczyt 22 198 MiB przy modelu UD-Q4_K_XL, czyli ~5.4 GB ponad plik (27-3090-final.md:211). Szacunek: karta 24 GB mieści Q4_K_XL, 16 GB około 10 GB pliku (Q2_K_XL/IQ2_M), 12 GB i 10 GB nie mieszczą Qwen 27B przy 131k.
- Wyniki kampanii opt-* przy 32–37k zostają jako historia, nie trafiają na stronę jako wynik karty.

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[2026-10-20-szybkie-iteracje]]
- [[lekcja-vast-transfer-kosztuje]]
- [[qwen3-8-27b]]
- [[2026-10-20-chmura-wstrzymana]]
