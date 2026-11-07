# KERNEL

Notatki i research o optymalizacji kerneli GPU pod lokalne AI (LLM), ze szczególnym naciskiem na **AMD Radeon RX 7900 XTX** (ROCm / HIP / Vulkan).

## Spis treści

| Plik | Co zawiera |
|---|---|
| [`reports/Optymalizacja kerneli na AMD.md`](reports/Optymalizacja%20kerneli%20na%20AMD.md) | **Główny raport**: architektura RDNA, ROCm, Vulkan, benchmarki, Strata, przewodnik i ścieżka nauki |
| [`hardware/rx-7900-xtx.md`](hardware/rx-7900-xtx.md) | Plan pracy pod nasz sprzęt (7900 XTX + RTX 5060 Ti, Ryzen 7 5700X, 64 GB DDR4, Ubuntu Server) i Qwen3.8-27B |
| [`benchmarks/2026-10-09-rx7900xtx-qwen38-27b.md`](benchmarks/2026-10-09-rx7900xtx-qwen38-27b.md) | Pierwsze pomiary (9 października, Vulkan): Qwen3.8-27B 59 → 92 t/s na krótkich promptach |
| [`qwen-opt/`](qwen-opt/) | **Aktualny setup (ROCm, final mode od 2026-11-06: eco 2200 MHz + pełny kontekst 262 144)**: łatki llama.cpp, launcher, pomiary, research. Qwen3.8-27B Uncensored: spec_sweep 118 t/s, prawdziwa praca agentowa średnio **120,8 t/s** (127 t/s do 32k, 123 t/s przy 96–128k, 96 t/s przy 128–160k), przy 255k w kontekście prefill 465 / decode 78,7 t/s; 241 W zamiast 280 W. LFM2.5-24B-A2B (KV q8_0) 294 t/s, 213 t/s przy 98k. Rekordy: [`wiki/REKORDY.md`](wiki/REKORDY.md) |
| [`product/PLAN.md`](product/PLAN.md) | **Plan produktu konsumenckiego** (lokalne AI plug and play, które samo się przyspiesza): werdykt, architektura, fabryka przepisów, roadmapa z fazą 0, budżet, ryzyka, decyzje; 7 raportów w `product/research/` |
| [`sources/qwen3.8-27b.md`](sources/qwen3.8-27b.md) | Qwen3.8-27B i wersja Uncensored od OrcaRouter |
| [`sources/auto-gpu-kernel.md`](sources/auto-gpu-kernel.md) | Analiza repo auto-gpu-kernel (agent piszący kernele, zwycięzca MLSys 2026) |
| [`research_notes/Optymalizacja kerneli na AMD/`](research_notes/Optymalizacja%20kerneli%20na%20AMD/) | Surowe notatki źródłowe (architektura, ROCm, Vulkan, praktyka, Strata) |
| [`glossary.md`](glossary.md) | Słowniczek pojęć |
| [`scripts/sysinfo.sh`](scripts/sysinfo.sh) | Zbiera info o systemie przed benchmarkami (tylko odczyt) |
