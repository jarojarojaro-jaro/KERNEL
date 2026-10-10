# KERNEL

Notatki i research o optymalizacji kerneli GPU pod lokalne AI (LLM), ze szczególnym naciskiem na **AMD Radeon RX 7900 XTX** (ROCm / HIP / Vulkan).

## Spis treści

| Plik | Co zawiera |
|---|---|
| [`reports/Optymalizacja kerneli na AMD.md`](reports/Optymalizacja%20kerneli%20na%20AMD.md) | **Główny raport**: architektura RDNA, ROCm, Vulkan, benchmarki, Strata, przewodnik i ścieżka nauki |
| [`hardware/rx-7900-xtx.md`](hardware/rx-7900-xtx.md) | Plan pracy pod nasz sprzęt (7900 XTX + RTX 5060 Ti, Ryzen 7 5700X, 64 GB DDR4, Ubuntu Server) i Qwen3.8-27B |
| [`benchmarks/2026-10-09-rx7900xtx-qwen38-27b.md`](benchmarks/2026-10-09-rx7900xtx-qwen38-27b.md) | Pomiary na naszej karcie: Qwen3.8-27B 59 → 92 t/s (200k ctx), co dało przyspieszenie |
| [`sources/qwen3.8-27b.md`](sources/qwen3.8-27b.md) | Qwen3.8-27B i wersja Uncensored od OrcaRouter |
| [`sources/auto-gpu-kernel.md`](sources/auto-gpu-kernel.md) | Analiza repo auto-gpu-kernel (agent piszący kernele, zwycięzca MLSys 2026) |
| [`research_notes/Optymalizacja kerneli na AMD/`](research_notes/Optymalizacja%20kerneli%20na%20AMD/) | Surowe notatki źródłowe (architektura, ROCm, Vulkan, praktyka, Strata) |
| [`glossary.md`](glossary.md) | Słowniczek pojęć |
| [`scripts/sysinfo.sh`](scripts/sysinfo.sh) | Zbiera info o systemie przed benchmarkami (tylko odczyt) |
