---
typ: produkt
tags: [produkt, plan, warstwy]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:66-85
status: aktualne
---
# Anatomia „przed → po”: warstwy L0–L3

**Zysk dzieli się na cztery warstwy: L0 naprawy (do ×20, gdy coś zepsute), L1 konfiguracja (×1.5–2.2), L2 strojenie nocne (+0–15%), L3 przepis z labu (+30–70%).**

- L0: BACO (u nas 4.4 vs 92 t/s), wylewanie VRAM do RAM na NVIDIA/Windows, model na CPU, obcięty kontekst; sekundy, lokalnie.
- L1: backend, `--fit`, spekulacja MTP/DFlash/n-gram, typ KV tylko za zgodą, `ubatch`, sampler; 1–5 min; Qwen na Vulkanie 38.8 → 85.6 t/s samym włączeniem MTP.
- L2: wybór prekompilowanych wariantów kerneli, MoE offload, długość draftu na tekstach użytkownika; godziny.
- L3: nowe kernele i fuzje per (arch × rodzina), podpisana paczka; Qwen na gfx1100 85.6 → 109 t/s, LFM 198 → 294.
Ekran wyniku: trzy słupki („typowa aplikacja”, „nasz silnik od razu”, „po nocy”), słowa/s, mediana z ABBA, odznaka bit w bit, „brak istotnej zmiany”, gdy w szumie. Obietnica jakości: identyczne względem standardowego trybu, nie względem dekodowania bez spekulacji.

## Powiązane
- [[produkt/_hub|produkt]]
- [[werdykt]]
- [[produkt-optymalizacja-u-uzytkownika]]
- [[baco-runtime-suspend]]
- [[raport-02-autotuning]]
