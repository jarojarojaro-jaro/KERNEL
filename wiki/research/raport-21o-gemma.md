---
typ: research
tags: [research, spekulacja, mtp, gemma]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/21o-gemma-ai.md:6-9,18,65-96; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:12
status: aktualne
---
# Raport 21o: techniki Gemma 4 (gemma.ai) a nasz MTP

**Klastrowa głowica Gemmy nie zastąpi słownika 64k (−4…−11% trafień d1); hybryda 64k + klastrowy ogon OOV dała offline +0.92% tok/krok, a na GPU −1.5% t/s – odrzucona (2026-10-19, kolejka 26).**

- Wierna Gemmie głowica (2048 klastrów, top-32, ~5.9k wierszy) traci 4–11% trafień d1 (`21o:6,18`).
- Hybryda (commit `cfc463dc1`, `LLAMA_MTP_TAIL`): offline k=8 +0.92% tok/krok przy ~1 GB VRAM, wersje tanie +0.33…+0.41% (`21o:65-76`).
- Pomiar GPU (kolejka wieczorna): 111.0/110.9 → 109.4/109.2 t/s, −1.5% → odrzucone (`26:12`, [[raport-26-kolejka-gpu]]).
- Nasz MTP nie współdzieli KV z celem; zysk z przeuczenia mały (`21o:8`).
- Produkt: Qwen3.8-27B zostaje flagowcem 24 GB, Gemma 4 dla 8/12 GB; K=V w globalnych warstwach Gemmy da −50% KV globalnego (`21o:9`).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[2026-10-19-tokeny-spoza-slownika-draftu]]
- [[raport-24b-draft-pelny-slownik]]
- [[glowica-mtp]]
- [[raport-26-kolejka-gpu]]
