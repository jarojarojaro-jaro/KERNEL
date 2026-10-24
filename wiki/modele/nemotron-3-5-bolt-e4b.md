---
typ: model
tags: [modele, telefon, nvidia, gemma]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60c-quant-and-3090-engines.md:189-194,217; https://huggingface.co/unsloth/NVIDIA-Nemotron-3.5-Bolt-E4B-GGUF; https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-BF16
status: aktualne
---
# NVIDIA Nemotron-3.5-Bolt-E4B (Gemma-4-E4B po RL)

**SLM NVIDIA na telefon i edge, wydany 2026-10-23: Gemma-4-E4B-it po RL (GRPO) pod narzędzia, rozmowę i instrukcje. Q4_K_M ma 6.18 GB i zajmuje „~4 GB VRAM”. Na drafter Qwen3.8-27B się nie nadaje.**

- Architektura (`config.json`):
  - 42 warstwy, hidden 2560, 8 głów Q / 2 KV, head_dim 256;
  - okno przesuwne 512 z co szóstą warstwą pełną, 18 warstw dzieli KV;
  - PLE 256 na warstwę, czyli ~2.8B parametrów osadzeń: stąd „8B (4B effective)”;
  - kontekst 64K.
- Słownik ma 262 144 tokeny, Qwen 248 320, więc jako drafter odpada. Nasze MTP i tak jest prawie darmowe.
- Ma własny drafter `…-E4B-4GB-DFlash` (BF16 GGUF) dla stock llama.cpp b11459 (`--spec-type draft-dflash`, n_max 7).
- Benchmarki NVIDIA (BF16): Tau2 55.10 przy 75.06 dla Qwen3.5-4B, BFCL-v3 68.51 przy 70.95, MultiChallenge 53.10 przy 51.76.
- Licencja OpenMDW-1.1.
- Dla nas: kandydat do katalogu 6–8 GB i telefonu; nie dla XTX.

## Powiązane
- [[modele/_hub|modele]]
- [[nemotron-3-5-bolt-74b-a9b]]
- [[gemma-4]]
- [[modele-telefon]]
- [[raport-60c-quant-3090]]
