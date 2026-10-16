---
typ: research
tags: [research, konkurencja, rynek]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/01-konkurencja.md:1,14-72; ~/KERNEL/product/research/15c-nowe-silniki.md:374-396
status: aktualne
---
# Raport 01: konkurencja

**Detekcja sprzętu i rekomendacja modelu to już standard; żaden produkt konsumencki nie łączy pomiaru, długiej optymalizacji poza flagami, weryfikacji bitowej i raportu przed → po (stan 2026-10-15).**

- Sprawdzone m.in.: LM Studio, Ollama, Jan, GPT4All, Msty, KoboldCpp, llamafile, Lemonade, Foundry Local.
- Najbliżej luki: flag-tunery (TurboLLM 285★: 74.7 vs 61 t/s na tej samej llama.cpp co LM Studio), silniki jednego modelu (Strata 25.4k★, MTPLX 14.4 → 23.0 tok/s), AMD Lemonade „Auto-Tune” (nic nie wydano), NVIDIA TensorRT for RTX.
- Popyt: Strata 25.4k★, llmfit 38k★, w trackerze Ollamy 190 issues ze „slow” i 165 z etykietą `amd`.
- Producenci sprzętu to kanał, nie konkurent: NVIDIA zamknęła ChatRTX 2026-01-21, AMD dołącza Ollamę i LM Studio do sterownika, Intel zarchiwizował IPEX-LLM 2026-01-28.
- Najgroźniejszy scenariusz: LM Studio/Ollama/Jan same włączą spekulację. Upstream z ręczną spekulacją na 7900 XTX: 68.6 t/s (MTP, ROCm), 85.6 t/s (MTP, Vulkan), 97.7 t/s (DFlash2); nasze kernele dokładają +10–25%.
Werdykt: nisza jest, ale wąska i łatwa do skopiowania; bronią nas dane i bramki.

Aktualizacja (raport 15c, 2026-10-16): teza „kernele u konsumenta: nikt” jest nieaktualna – Magnitude stroi kernele na urządzeniu (60 s, bramka α = 8, nie bitowa), a tqLLM wybiera warianty bit-identyczne przy ładowaniu. Nowa teza: nikt nie łączy strojenia z bitową bramką ani z publikowanym KLD. Nowe wiersze: Magnitude (6.9k★ w 4 miesiące), tqLLM, Actual Computer.

## Powiązane
- [[research/_hub|research]]
- [[raport-02-autotuning]]
- [[raport-06-produkt]]
- [[turbollm]]
- [[ollama]]
- [[raport-15c-nowe-silniki]]
- [[magnitude]]
