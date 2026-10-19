---
typ: karta
tags: [karty, amd, rdna3]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/hardware/rx-7900-xtx.md:6-34,100-110; ~/KERNEL/qwen-opt/STATUS-NEXT.md:8-14; ~/KERNEL/qwen-opt/NOTES.md:126; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:117,239,305; ~/qwen-opt/tools/fan.sh:1-45; /proc/cmdline; komunikat Main do WikiIngest 2026-10-18; ~/qwen-opt/tools/fan.sh:1-40,66-90; /etc/systemd/system/xtx-fan.timer
status: aktualne
---
# AMD Radeon RX 7900 XTX (główna karta)

**Nasza główna karta: RDNA3 gfx1100, 24 GB GDDR6, 960 GB/s; na niej powstało 70 łatek i rekordy Qwen 109 t/s i LFM 294 t/s.**

Parametry (hardware/rx-7900-xtx.md): 96 CU (48 WGP), wave32, VGPR 192 KiB/SIMD, LDS 128 KiB/WGP, L2 6 MiB, Infinity Cache 96 MiB, VRAM 24 GB 384-bit, 960 GB/s (standardowa wartość, oznaczona „do weryfikacji”), WMMA ~123 TFLOPS FP16 (wyliczone), brak FP8/FP4.

Zestaw: drugi GPU RTX 5060 Ti 16 GB, Ryzen 7 5700X (AVX2, bez AVX-512), 64 GB DDR4 (~51 GB/s teoretycznie, ~19× wolniej niż VRAM), Ubuntu Server headless.

Wyniki (2026-10-15, `amd-opt`, spec_sweep): Qwen3.8-27B 109.0 t/s, Uncensored 115.5, LFM2.5 293.7, LFM Uncensored 267.3; pp4096 Qwen 1115, LFM 6175. Referencja Llama 2 7B Q4_0 (scoreboard): Vulkan tg128 190.9, ROCm 170.1.

Rynek (raport 05, 2026-10): używana mediana €837, nowa $1,821; 0.40% w Steam; zero ofert na Vast, w chmurze tylko Salad (WSL2) i Hostkey (pre-order). Ustawienia: limit 285 W, wyłączone usypianie.

**Chłodzenie (2026-10-18):** overdrive przez `amdgpu.ppfeaturemask=0xfff7ffff` (GRUB, restart ~20:27 UTC). Wentylator idzie za obciążeniem: `fan.sh` z timera root `xtx-fan.timer` – GPU busy ≥ 10% → krzywa 90% przy każdej temperaturze (≈ 3300 RPM), 20 s bezczynności → 40% poniżej 50 °C i 90% od 50 °C; krzywa ponownie zapisywana po resecie GPU. Przed: junction 86–87 °C, pamięć 89–90 °C przy 44%; po: busy 99% → 3320–3500 RPM w 12 s, hotspot 73 °C, pamięć 74 °C ([[lekcja-wentylator-rdna3]]). Vulkan bez sudo: `apt-get download libvulkan1 mesa-vulkan-drivers libllvm20 …` + `dpkg -x` do `~/.local/vk/root`, ICD ze ścieżką absolutną (RADV NAVI31, API 1.4.318; [[2026-10-18-magnitude-vulkan-xtx]]).

## Powiązane
- [[karty/_hub|Karty]]
- [[rdna3-gfx1100]]
- [[amdgpu-moc-i-termika]]
- [[stan-2026-10-15]]
- [[rtx-5060-ti]]
- Inne platformy z planu: [[rx-9070-xt]], [[radeon-ai-pro-r9700]], [[strix-halo]], [[mi300x]], [[arc-b580-i-mac]]
