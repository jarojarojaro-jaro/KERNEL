---
typ: ekosystem
tags: [ekosystem, spekulacja, trening]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/10-post-training.md:50,76,86-87,129,449-452,472,506-508
status: aktualne
---
# vLLM speculators i SGLang SpecForge

**Dwa narzędzia do trenowania drafterów (MTP, EAGLE-3); speculators to nasza ścieżka do fine-tune głowicy MTP.**

speculators (vLLM) ma MTP: convert → train → stitch, β=0.6; oficjalny tutorial: `prepare-data` → `launch_vllm.py Qwen/Qwen3.5-0.8B --target-layer-ids <ostatnia>` → `generate-offline-data` → `train` → stitch. SpecForge (SGLang) i speculators są najdojrzalsze dla EAGLE-3; llama.cpp ma konwerter dla formatów SpecForge i vLLM/AngelSlim. Plan z raportu 10: E1a toolchain MTP na Qwen3.5-0.8B na Vast RTX 3090 (~2–3 h); kontrola przez speculators na trunku bf16 na A100 80 GB, 6–8 h, ~$5–7. EAGLE-3 od zera przegra z natywnym MTP (τ 2.2–2.4 vs 3.74).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Stan faktyczny: pilot douczania głowicy MTP 27B nie użył speculators. Poszedł własną drogą: `llama-mtp-extract` (gałąź [[mtp-train]]) → lustro grafu MTP w PyTorch (parytet tok/krok 3.268 vs 3.266) → FastMTP → GGUF. Wynik negatywny: offline +0.2%, online 0 do −1.7% poza PL-prozą, $2.14 ([[2026-10-16-mtp-pl-pilot]]).
- Czego uczy porównanie: speculators i SpecForge dają gotowy łańcuch convert → train → stitch z danymi generowanymi przez serwer vLLM/SGLang; my zbudowaliśmy lustro sami, bo nasz trunk to GGUF Q4 i liczy się akceptacja na naszych wagach. Lustro z parytetem było dobrym ruchem (zysk mierzony wprost na naszym pniu).
- Dla nauki treningu drafterów to nadal podstawowe narzędzia ([[trening-llm-mapa]]); jako „ścieżka do prędkości” temat zamknięty, dopóki nie zmieni się model albo dane.

## Powiązane
- [[mtp-train]]
- [[laya-mlx]]
- [[glowica-mtp]]
- [[2026-10-12-mtp-trening-faza1]]
