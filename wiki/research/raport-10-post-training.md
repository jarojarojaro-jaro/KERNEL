---
typ: research
tags: [research, trening, mtp, kwanty]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/10-post-training.md:1-52; ~/KERNEL/product/research/11-mtp-pl-pilot.md:3-9
status: aktualne
---
# Raport 10: trening i post-training

**Do obietnicy produktu najlepiej pasuje trening draftera, nie modelu: fine-tune głowicy MTP Qwen3.8-27B przez self-distillation na trunku Q4, szacunek +10–17% tok/krok na czacie PL za $0–4.**

Stan 2026-10-16, bez GPU. Ceny Vast (feed 2026-10-16 00:30 UTC): RTX 3090 $0.21/h, A100 80 GB PCIe $0.73, H100 SXM $3.07.
- Dowody: Red Hat τ +6.8% na natywnym MTP; FastMTP 1.83 → 2.73; TensorFold: drafter trenowany na niekwantyzowanym modelu traci na trunku Q4 (4.2 → 3.0–3.3 tok/rundę).
- EAGLE-3/DFlash od zera: nie teraz (natywny MTP τ 3.74 vs publiczny EAGLE-3 2.2–2.4).
- Model decyzyjny w pętli spekulacji: u nas T2 dało 0%, oczekiwane +0–5%; encodery typu Laya za wolne per token (7–14 ms na M3 Max).
- QAT/niskie bity (Bonsai, GSQ-RCO, Saluki) zmieniają wyjście → osobny „Tryb maksymalny”.
- Ścieżka: <$1 MTP Qwen3.5-0.8B przez speculators na 3090; ~$3–4 pilot MTP-PL; stretch $5–16.

Wynik pilota (raport 11, 2026-10-16): douczenie głowicy MTP na 1.7 M tokenów dało ±0.2% tok/krok zamiast szacowanych +10–17%.

## Powiązane
- [[research/_hub|research]]
- [[raport-12-bit-exact]]
- [[raport-07-metody]]
- [[speculators-specforge]]
- [[glowica-mtp]]
- [[raport-11-mtp-pl-pilot]]
