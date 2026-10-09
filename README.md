# KERNEL

Notatki i research o optymalizacji kerneli GPU pod lokalne AI (LLM), ze szczególnym naciskiem na **AMD Radeon RX 7900 XTX** (ROCm / HIP / Vulkan).

## Spis treści

| Plik | Co zawiera |
|---|---|
| [`reports/Optymalizacja kerneli na AMD.md`](reports/Optymalizacja%20kerneli%20na%20AMD.md) | **Główny raport**: architektura RDNA, ROCm, Vulkan, benchmarki, Strata, przewodnik i ścieżka nauki |
| [`hardware/rx-7900-xtx.md`](hardware/rx-7900-xtx.md) | Plan pracy pod nasz sprzęt (7900 XTX + RTX 5060 Ti, Ryzen 7 5700X, 64 GB DDR4, Ubuntu Server) i Qwen3.8-27B |
| [`sources/qwen3.8-27b.md`](sources/qwen3.8-27b.md) | Qwen3.8-27B i wersja Uncensored od OrcaRouter |
| [`sources/auto-gpu-kernel.md`](sources/auto-gpu-kernel.md) | Analiza repo auto-gpu-kernel (agent piszący kernele, zwycięzca MLSys 2026) |
| [`research_notes/Optymalizacja kerneli na AMD/`](research_notes/Optymalizacja%20kerneli%20na%20AMD/) | Surowe notatki źródłowe (architektura, ROCm, Vulkan, praktyka, Strata) |
| [`notes/wynajem-gpu.md`](notes/wynajem-gpu.md) | Gdzie (nie) da się wynająć 7900 XTX online |
| [`glossary.md`](glossary.md) | Słowniczek pojęć |
| [`scripts/sysinfo.sh`](scripts/sysinfo.sh) | Zbiera info o systemie przed benchmarkami (tylko odczyt) |
