---
typ: lekcja
tags: [lekcje, pomiar, flagi, serwer]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66a-strata-maya.md:345-353; ~/KERNEL/product/research/66c-hyperkernel-megakernele.md:104; ~/KERNEL/product/research/66e-anatomia-serwowania-tqllm.md:154,191; ~/KERNEL/product/research/66d-saber-engine-rdna.md:127-128
status: aktualne
---
# Flaga w env to nie dowód, że ścieżka działa

**`LLAMA_SERVER_TOK_CACHE` jest w produkcji martwy: `LLAMA_SERVER_SAFE_SPECIAL=1` kieruje czat na ścieżkę tokenizacji bez cache'u, a samej flagi `run-topka.sh` nie ustawia; w pomiarze x54 log kolejki potwierdza env ramion, ale nie to, że matcher fuzji zadziałał (raporty 66a, 66c, 2026-11-07).**

- Topka-q63 czyta 283 różne `getenv("LLAMA_*|GGML_*")`. tqLLM ma rejestr 55 flag (`config/flags.yaml`), a wycofana nazwa zatrzymuje start z podpowiedzią zamiennika.
- Saber: bramka bitowa, której wejścia były w części zerami, „przechodziła” z 0 różnic; po podpięciu prawdziwych wejść różnic było 627 393 bajty. Dlatego każda bramka ma symbol kontroli negatywnej (`*_drop1`).

Reguły:
1. Każde ramię A/B loguje dowód aktywacji (licznik trafień, nazwa wybranego kernela), nie tylko env.
2. Bramka bitowa ma kontrolę negatywną, która musi ją oblać.
3. Rejestr flag topki z twardym błędem na nieznaną lub wycofaną nazwę (pomysł T7 z 66e).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-higiena-pomiaru]]
- [[wylacznik-w-kazdej-latce]]
- [[raport-54-mniej-granic]]
- [[zgodnosc-bitowa-md5]]
- [[raport-66-synteza]]
