---
typ: karta
tags: [karty, amd, rdna3]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/hardware/rx-7900-xtx.md:6-34,100-110; ~/KERNEL/qwen-opt/STATUS-NEXT.md:8-14; ~/KERNEL/qwen-opt/NOTES.md:126; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:117,239,305; ~/qwen-opt/tools/fan.sh:1-45; /proc/cmdline; komunikat Main do WikiIngest 2026-10-18; ~/qwen-opt/tools/fan.sh:1-40,66-90; /etc/systemd/system/xtx-fan.timer; komunikat Main do WikiIngest 2026-10-19 (decyzja użytkownika 00:00 UTC); ~/KERNEL/qwen-opt/tools/gpu-guard.sh:1-45
status: aktualne
karta: rx-7900-xtx
vram: 24 GB
pasmo: 960 GB/s
gdzie: jaroserverai
stan: główna karta, produkcja topka
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 109.0 t/s | dekod MTP T=1; amd-opt spec_sweep | 2026-10-15
  - qwen3-8-27b-uncensored | rx-7900-xtx | 115.5 t/s | dekod MTP T=1; amd-opt spec_sweep | 2026-10-15
  - lfm2-5-24b-a2b | rx-7900-xtx | 293.7 t/s | dekod; amd-opt | 2026-10-15
  - lfm2-5-uncensored | rx-7900-xtx | 267.3 t/s | dekod; amd-opt | 2026-10-15
  - qwen3-8-27b | rx-7900-xtx | 1115 t/s | prefill pp4096; amd-opt | 2026-10-15
  - lfm2-5-24b-a2b | rx-7900-xtx | 6175 t/s | prefill pp4096; amd-opt | 2026-10-15
---
# AMD Radeon RX 7900 XTX (główna karta)

**Nasza główna karta: RDNA3 gfx1100, 24 GB GDDR6, 960 GB/s; na niej powstało 70 łatek; rekordy Qwen: spec_sweep T=1 120,58 t/s (2026-11-05) i dekod MTP przy prompcie 1,7k 133,9 t/s (2026-11-14, topka-q70, [[REKORDY]]), LFM 294 t/s.**

Parametry (hardware/rx-7900-xtx.md): 96 CU (48 WGP), wave32, VGPR 192 KiB/SIMD, LDS 128 KiB/WGP, L2 6 MiB, Infinity Cache 96 MiB, VRAM 24 GB 384-bit, 960 GB/s (standardowa wartość, oznaczona „do weryfikacji”), WMMA ~123 TFLOPS FP16 (wyliczone), brak FP8/FP4.

Zestaw: drugi GPU RTX 5060 Ti 16 GB, Ryzen 7 5700X (AVX2, bez AVX-512), 64 GB DDR4 (~51 GB/s teoretycznie, ~19× wolniej niż VRAM), Ubuntu Server headless.

Wyniki (2026-10-15, `amd-opt`, spec_sweep): Qwen3.8-27B 109.0 t/s, Uncensored 115.5, LFM2.5 293.7, LFM Uncensored 267.3; pp4096 Qwen 1115, LFM 6175. Referencja Llama 2 7B Q4_0 (scoreboard): Vulkan tg128 190.9, ROCm 170.1.

Rynek (raport 05, 2026-10): używana mediana €837, nowa $1,821; 0.40% w Steam; zero ofert na Vast, w chmurze tylko Salad (WSL2) i Hostkey (pre-order). Ustawienia: limit 285 W, wyłączone usypianie.

**Chłodzenie (2026-10-18):** overdrive przez `amdgpu.ppfeaturemask=0xfff7ffff` (GRUB, restart ~20:27 UTC). Wentylator idzie za obciążeniem: `fan.sh` z timera root `xtx-fan.timer` – GPU busy ≥ 10% → krzywa 100% przy każdej temperaturze (od 2026-10-19 decyzją użytkownika, [[2026-10-19-wentylator-100-przy-pracy]]; busy 95% → 3426 RPM), 20 s bezczynności → 40% poniżej 50 °C i 100% od 50 °C; krzywa ponownie zapisywana po resecie GPU. Przed: junction 86–87 °C, pamięć 89–90 °C przy 44%; po: busy 99% → 3320–3500 RPM w 12 s, hotspot 73 °C, pamięć 74 °C ([[lekcja-wentylator-rdna3]]). Vulkan bez sudo: `apt-get download libvulkan1 mesa-vulkan-drivers libllvm20 …` + `dpkg -x` do `~/.local/vk/root`, ICD ze ścieżką absolutną (RADV NAVI31, API 1.4.318; [[2026-10-18-magnitude-vulkan-xtx]]).

Bezpieczeństwo (2026-10-19): twarda zasada użytkownika [[2026-10-19-bezpieczenstwo-sprzetu]], strażnik [[gpu-guard]]; page faulty SQC @0 w analizie ([[pm4-replay]]).

**Termika i eco (2026-11-05/06):** raport 64 – limit `OD_SCLK` bezpieczny, ale na jądrze 6.8 commit OD gubi krzywą wentylatora ([[raport-64-termika]], [[lekcja-od-commit-gubi-krzywa]]). Stock 2026-11-05 (14:41–16:32, ≥ 250 W, cap 285 W, wentylator 100%): junction śr. 78 / maks. 89 °C, Δ hotspot−edge śr. 25 °C (maks. 38); 65–66 °C to tylko próbka 30 s. xtx-eco zainstalowane 2026-11-06 12:07 UTC; fabryczny `OD_SCLK 1` zmienia się między bootami (2885 → 2935 MHz) ([[2026-11-06-xtx-eco-instalacja]]). Produkcja Qwen od 2026-11-05: topka-q63, −1.0 GiB VRAM ([[2026-11-05-q63-topka]]).

<!-- TABELE:START -->
## Wyniki z notatek (229)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-28); pełna tabela: [[najlepsze-wyniki]].

| model | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | czat T=0,7, prism Q2_0 + MTP n2, KV q4_0 | **77.7 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | czat T=0,7, topka-bonsai PM4 + env produkcji + MTP n2 + słownik draftu 64k, ctx 262144 | **106.0 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | czat T=0,7, topka-k157 PM4 + env produkcji + MTP n2 + słownik 64k, ctx 262144 | **116.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | dekod bez spekulacji, topka-best PM4, ctx 262144 | **70.6 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | dekod bez spekulacji, topka-k157 PM4 | **76.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | dekod T=0 (Q4 160 tok.), prism Q2_0 + MTP n2 | **117.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | dekod T=0 (Q4), MTP n2 + ngram-mod | **188.4 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | edycja/kopia kodu T=0 (copy_bench short), topka-k157 | **446.4 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | edycja/kopia kodu T=0 (copy_bench short, mediana), topka-best PM4 + MTP n2 + lookup W16 + słownik 64k | **426.1 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | konfiguracja Dogukana (temp 1,0) na topka-best, MTP n2 | **121.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Ternary Bonsai 2.5 27B Uncensored [[bonsai-2-5-uncensored]] | llama-bench tg128 bez spekulacji, Q2_0 | **54.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| Drafter DFlash2 dla Qwen3.8-27B [[drafter-dflash]] | dekod EN | **115.7 t/s** | n=6, cache q8_1 | 2026-10-09 | [[drafter-dflash]] |
| Drafter DFlash2 dla Qwen3.8-27B [[drafter-dflash]] | dekod EN kod | **104.8 t/s** | n=6, runda 5 | 2026-10-15 | [[drafter-dflash]] |
| Drafter DFlash2 dla Qwen3.8-27B [[drafter-dflash]] | dekod mediana T=0 | **90.6 t/s** | PL/EN, n=6, 285 W | 2026-10-10 | [[drafter-dflash]] |
| Drafter DFlash2 dla Qwen3.8-27B [[drafter-dflash]] | dekod mediana T=1 | **71.9 t/s** | PL/EN, n=6 | 2026-10-10 | [[drafter-dflash]] |
| Głowica MTP Qwen3.8-27B [[glowica-mtp]] | akceptacja held-out | **3.266 tok/krok** | n=4, głowica fabryczna | 2026-10-16 | [[glowica-mtp]] |
| Głowica MTP Qwen3.8-27B [[glowica-mtp]] | akceptacja offline | **3.04 tok/krok** | n_draft=4, 69 207 tokenów | 2026-10-12 | [[glowica-mtp]] |
| Głowica MTP Qwen3.8-27B [[glowica-mtp]] | dekod T=1 | **102.7 t/s** | MTP n=4 | 2026-10-15 | [[glowica-mtp]] |
| Inkling 2 Mini [[inkling-2-mini]] | dekod plain | **49,5 t/s** | po rundach 1–6 duetu | 2026-11-21 | [[inkling-2-mini]] |
| Inkling 2 Mini [[inkling-2-mini]] | dekod tg64 | **26,9 t/s** | AtomicChat AD-Q4_K, stock PR #32695, eco 2200 | 2026-11-21 | [[inkling-2-mini]] |
| Inkling 2 Mini [[inkling-2-mini]] | prefill pp2048 | **1125 t/s** | AD-Q4_K, PR #32695 | 2026-11-21 | [[inkling-2-mini]] |
| Inkling 2 Mini [[inkling-2-mini]] | prefill pp512 | **1333 t/s** | AD-Q4_K, PR #32695 | 2026-11-21 | [[inkling-2-mini]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | copy bez lookup | **288.2 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | copy lookup W16 | **312.4 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | copy lookup W8 | **334.7 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | czat | **274.1 t/s** | topka (upstream 146.8) | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | czat T=1 | **173 t/s** | Q5_K_M, KV q4_0, bez MTP | 2026-10-14 | [[lfm-baza]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod | **293.7 t/s** | amd-opt | 2026-10-15 | [[rx-7900-xtx]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod budżet myślenia | **292.9 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod narzędzia omp | **294.3 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod plain PM4 off | **259.3 t/s** |  | 2026-10-19 | [[trwala-siatka-bez-pm4]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod plain PM4 on | **293.7 t/s** |  | 2026-10-19 | [[trwala-siatka-bez-pm4]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod plain tg128 | **292,1 t/s** | PM4 replay | 2026-10-14 | [[pm4-replay]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod reasoning_control | **292.9 t/s** | sampler fast (było 256.9) | 2026-10-15 | [[2026-10-15-sampler]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod spec_sweep | **293.7 t/s** | Q5_K_M, 3404 µs/token | 2026-10-16 | [[2026-10-16-budzet-lfm-megakernel]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | MoE down Q5_K produkcja | **11.64 µs** | moebench | 2026-10-18 | [[2026-10-18-lfm-moe-negatywne]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | odczyt sesji 53k z SSD | **0,53 s** | slot-save-path | 2026-10-18 | [[cache-sesji-na-dysku]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | pp4096 | **6180 t/s** | fork | 2026-10-14 | [[lfm-baza]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | prefill 64k | **14.6 s** | (Magnitude 32.7 s) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | prefill pp16384 | **6680 t/s** | ub 2048 (ub 512 5654) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | prefill pp4096 | **7148 t/s** | ub 2048 (ub 512 6108) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | serwer lfm none | **218.6 t/s** | łatki 0048–0052 | 2026-10-14 | [[lfm-runda-1]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | spec_sweep | **293.7 t/s** | KV q8_0 | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | spec_sweep lfm none T=1 | **293.75 t/s** | PM4 replay | 2026-10-14 | [[lfm-runda-4-pm4]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | spec_sweep T=1 | **293.7 t/s** | Q5_K_M, KV q8_0 | 2026-10-15 | [[stan-2026-10-15]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | start sesji agenta | **230 ms** | CACHE_SHARE_MIN=1024 (było 1357) | 2026-10-18 | [[2026-10-18-cache-promptu-agenta]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | sweep plain | **322.9 t/s** | Q4_K_M (Magnitude 219.6) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | tg128 | **292.22 t/s** | MOE_GU_BLOCK 7c5b2a116 (=0 291.26) | 2026-10-18 | [[2026-10-18-lfm-moe-pasmo]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | tg128 98k | **191.4 t/s** | KV q8_0, kvq q8 (baza 152.4) | 2026-10-14 | [[lfm-runda-3]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | tg128 górna granica | **323.97 t/s** | PM4_UB down,mmvq1 bez synchronizacji | 2026-10-18 | [[2026-10-18-pm4-ub-lfm]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | tg128 głębokość 0 | **262.1 t/s** | KV q8_0, łatki 0055–0059 | 2026-10-14 | [[lfm-runda-3]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | tg128 głębokość 98304 | **212.95 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | tg128 KV q8_0 | **294.84 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | token 98k | **5,462 ms** | KV q8_0, kvq 0055 | 2026-10-14 | [[fattn-kvq]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | token tg | **3,402 ms** | po 0062 CONV_ROWS4 | 2026-10-14 | [[lfm-shortconv]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | TTFT 32k | **5690 ms** | ub 2048 (ub 512 6676) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |
| LFM2.5-24B-A2B-Uncensored [[lfm2-5-uncensored]] | dekod | **267.3 t/s** | amd-opt | 2026-10-15 | [[rx-7900-xtx]] |
| LFM2.5-24B-A2B-Uncensored [[lfm2-5-uncensored]] | dekod llama-bench | **268.27 t/s** | GGML_HIP_MOE_GU_BLOCK | 2026-10-18 | [[lfm2-5-uncensored]] |
| LFM2.5-24B-A2B-Uncensored [[lfm2-5-uncensored]] | prefill pp4096 | **6291 t/s** |  | 2026-10-15 | [[lfm2-5-uncensored]] |
| LFM2.5-24B-A2B-Uncensored [[lfm2-5-uncensored]] | spec_sweep T=1 | **267.3 t/s** | AD-Q5_K_M, KV q8_0 | 2026-10-15 | [[stan-2026-10-15]] |
| Qwen3.8-27B [[qwen3-8-27b]] | akceptacja głowicy MTP | **3.04 tok/krok** | UD-Q4_K_XL, amd-opt c90db29c6 | 2026-10-12 | [[2026-10-12-mtp-trening-faza1]] |
| Qwen3.8-27B [[qwen3-8-27b]] | bufor MTP ROCm0 | **40.28 MiB** |  | 2026-11-06 | [[raport-65-vram-rezerwa-mtp]] |
| Qwen3.8-27B [[qwen3-8-27b]] | code-edit | **419.9 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| Qwen3.8-27B [[qwen3-8-27b]] | copy 64k | **141.2 t/s** | ROCm MTP (Magnitude 63.7) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| Qwen3.8-27B [[qwen3-8-27b]] | czat | **115.8 t/s** | PM4 WA=2 + GUARD (baza 110.8) | 2026-10-19 | [[raport-26-kolejka-gpu]] |
| Qwen3.8-27B [[qwen3-8-27b]] | czat T=1 | **115.6 t/s** | PAIR2 (było 115.1) | 2026-10-20 | [[2026-10-20-podsumowanie-nocy]] |
| Qwen3.8-27B [[qwen3-8-27b]] | czat T=1 baza | **115.1 t/s** |  | 2026-10-20 | [[raport-24w-pair2]] |
| Qwen3.8-27B [[qwen3-8-27b]] | czat T=1 PAIR2=1 | **115.6 t/s** |  | 2026-10-20 | [[raport-24w-pair2]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod 1.7k | **136.5 t/s** | sam MTP, LOOKUP=0 | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod 1.7k T=0 | **126.0 t/s** | K3 | 2026-10-13 | [[2026-10-13-k3-host]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod 94k | **70.9 t/s** | po kvq, MTP n=4 T=0 | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod 94k T=0 | **100.6 t/s** | KV draftu q4_0 | 2026-10-14 | [[2026-10-14-prefill-k5-t3]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod copy T=0 | **355.0 t/s** | W16 (MTP4 163.4) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod deep 32630 tok. | **111.3 t/s** | Enigma | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod DFlash n=6 T=0 | **90.6 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod DFlash n=6 T=1 | **71.9 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod Enigma uczciwy bench | **97.8 t/s** | effort low (baseline 35.0) | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod long 30k T=0 | **373.5 t/s** | W16 (MTP4 156.7) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP | **113,2 t/s** | blok MTP IQ4_XS, 28.14 ms/krok | 2026-10-18 | [[latki-spekulacji]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP 27k bitexact | **102.66 t/s** | (prod 111.77) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP budżet myślenia | **107.0 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n=4 | **101.7 t/s** | K4 WMMA d3a0973ae | 2026-10-13 | [[2026-10-13-k4-i-hw-queues]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n=4 T=1 | **102.6 t/s** | po T1, 29.36 ms/krok | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n=5 | **105.4 t/s** | K4 WMMA d3a0973ae | 2026-10-13 | [[2026-10-13-k4-i-hw-queues]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n=5 T=0 | **86.3 t/s** | Vulkan 285 W | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n=5 T=1 | **81.1 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP narzędzia omp | **113.2 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP reasoning_control | **109.5 t/s** | sampler fast (było 101.6) | 2026-10-15 | [[2026-10-15-sampler]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP T=0 | **91.8 t/s** | Vulkan RADV + słownik 64k, n=5 | 2026-10-09 | [[2026-10-09-pierwsze-pomiary]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP T=0.7 | **118.3 t/s** | COUPLED=1 (off 112.7) | 2026-10-18 | [[2026-10-18-sprzezone-probkowanie-mtp]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP T=1 | **120.54 t/s** | spec_sweep, topka-q63 | 2026-11-05 | [[qwen3-8-27b]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP T=1 bez sprzężenia | **107.6 t/s** |  | 2026-10-20 | [[raport-24p-sprzezone-t1]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP T=1 SPEC_COUPLED=1 | **111.4 t/s** |  | 2026-10-20 | [[raport-24p-sprzezone-t1]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod mvs T=0 | **433.0 t/s** | topka-next coupled=1 + host-gap (było 420.2) | 2026-10-20 | [[2026-10-20-podsumowanie-nocy]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod mvs T=1 | **375.8 t/s** | W16 (MTP4 166.1) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod plain tg128 | **43.2 t/s** | amd-opt | 2026-10-15 | [[qwen3-8-27b]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod po odtworzeniu slotu | **116.1 t/s** | topka-q63 | 2026-11-05 | [[qwen3-8-27b]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod serwer 94k | **70,9 t/s** | KV q4_0, kvq 0011 | 2026-10-12 | [[fattn-kvq]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod spec_sweep T=1 | **123,6 t/s** | stock, topka-q63 UD-Q4_K_XL | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod ~32k | **111.6 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| Qwen3.8-27B [[qwen3-8-27b]] | energia | **2,07 J/token** | sclk 2200 (stock 2,27) | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| Qwen3.8-27B [[qwen3-8-27b]] | fill 255k | **492.5 t/s** | topka-q70, Uncensored | 2026-11-09 | [[qwen3-8-27b]] |
| Qwen3.8-27B [[qwen3-8-27b]] | koszt haka MTP prefill 32k | **768 ms** | 2.2% TTFT | 2026-10-18 | [[2026-10-18-hak-mtp-i-checkpointy]] |
| Qwen3.8-27B [[qwen3-8-27b]] | krok B | **27.40 ms** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| Qwen3.8-27B [[qwen3-8-27b]] | krok MTP4 mvs | **29.62 ms** |  | 2026-10-19 | [[raport-24k-koszt-weryfikacji]] |
| Qwen3.8-27B [[qwen3-8-27b]] | krok prozy T=1 | **27.38 ms** | 2.63 tok/krok, stara metryka | 2026-10-20 | [[raport-36-xtx-roadmap]] |
| Qwen3.8-27B [[qwen3-8-27b]] | krok spec_sweep RPB=1 | **28.80 ms** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| Qwen3.8-27B [[qwen3-8-27b]] | krok Vulkan 0007–0010 | **41.46 ms** | Qwen UD | 2026-10-12 | [[vulkan-mmvq]] |
| Qwen3.8-27B [[qwen3-8-27b]] | krok W16 mvs | **35.61 ms** |  | 2026-10-19 | [[raport-24k-koszt-weryfikacji]] |
| Qwen3.8-27B [[qwen3-8-27b]] | ms/krok MTP T=1 | **41.46 ms** | Vulkan łatki MMVQ | 2026-10-12 | [[2026-10-12-vulkan-krok-po-kroku]] |
| Qwen3.8-27B [[qwen3-8-27b]] | mvs | **433.8 t/s** | topka f9b84bcfa | 2026-10-21 | [[raport-43-integracja]] |
| Qwen3.8-27B [[qwen3-8-27b]] | mvs A | **428.49 t/s** |  | 2026-10-21 | [[raport-54-mniej-granic]] |
| Qwen3.8-27B [[qwen3-8-27b]] | mvs B ATTN_PREP_MT+KVQ_FWHT_GATE | **428.55 t/s** |  | 2026-10-21 | [[raport-54-mniej-granic]] |
| Qwen3.8-27B [[qwen3-8-27b]] | mvs bez GPU verify | **410.4 t/s** |  | 2026-10-19 | [[raport-24m-weryfikacja-gpu]] |
| Qwen3.8-27B [[qwen3-8-27b]] | mvs GPU verify | **420.1 t/s** | f2217bac7 | 2026-10-19 | [[raport-24m-weryfikacja-gpu]] |
| Qwen3.8-27B [[qwen3-8-27b]] | odczyt sesji 53k z SSD | **2,51 s** | slot-save-path, MTP | 2026-10-18 | [[cache-sesji-na-dysku]] |
| Qwen3.8-27B [[qwen3-8-27b]] | pasmo weryfikacji n=5 | **762 GB/s** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| Qwen3.8-27B [[qwen3-8-27b]] | pp4096 | **1123.2 t/s** | epilog MMQ 0070 (baza 1099.5) | 2026-10-15 | [[runda-6]] |
| Qwen3.8-27B [[qwen3-8-27b]] | pp4096 MMQ YDB=2 (wycofane, YDB=0 1097) | **1066 t/s** |  | 2026-10-15 | [[qwen-runda-5]] |
| Qwen3.8-27B [[qwen3-8-27b]] | pp5 d32768 bitexact | **133.8 t/s** | (prod 152.1) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill 128k | **708 t/s** | q63 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill 12k | **940 t/s** | sclk 2200 (stock 1030) | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill 29.5k | **943 t/s** | K5+T3 | 2026-10-14 | [[2026-10-14-prefill-k5-t3]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill 32k | **969 t/s** | q63 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill 94k | **767 t/s** | K5+T3 0040-0045 | 2026-10-14 | [[prefill-mmq-fa]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill Enigma | **1041 t/s** | kandydat enigma | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill pp4096 | **1123,2 t/s** | MMQ epilog 0070 | 2026-10-15 | [[mmq-epilog]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill zimny 27k | **31.9 s** | cache promptu domyślny | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prompt 94k + 1000 tok. | **165 s** | ROCm (Vulkan 260 s) | 2026-10-12 | [[2026-10-12-rocm-vs-vulkan]] |
| Qwen3.8-27B [[qwen3-8-27b]] | proza E0 | **78.93 t/s** |  | 2026-10-21 | [[qwen3-8-27b]] |
| Qwen3.8-27B [[qwen3-8-27b]] | proza E0 T=1 | **78.93 t/s** | produkcja, thinking off | 2026-10-20 | [[metryka-prozy-e0]] |
| Qwen3.8-27B [[qwen3-8-27b]] | pytanie uzupełniające 27k | **0.7 s** | cache promptu | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec blok MTP IQ4_XS | **113.2 t/s** | 5 seedów (Q6_K 109.4) | 2026-10-18 | [[raport-16f-xtx-szybkie]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep | **109.0 t/s** | produkcja (fork 74.5) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep baza | **111.4 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep bitexact | **108.3 t/s** | 365af3e5e (prod 107.7) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep MMVQ_OCC | **110.8 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep MMVQ_OCC serializacja | **104.3 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep qwen mtp T=1 | **108.82 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep T=1 | **120.50 t/s** | topka-q63 c0576e3e8 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep T=1 1 seed | **105.1 t/s** | topka | 2026-10-19 | [[2026-10-19-build-topka]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep T=1 A | **113.8 t/s** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep T=1 B przełączniki hosta | **117.9 t/s** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| Qwen3.8-27B [[qwen3-8-27b]] | start serwera | **6.5 s** | topka f9b84bcfa (baza 39.8) | 2026-10-21 | [[raport-43-integracja]] |
| Qwen3.8-27B [[qwen3-8-27b]] | start sesji agenta | **1612 ms** | CACHE_SHARE_MIN=1024 (było 8019) | 2026-10-18 | [[2026-10-18-cache-promptu-agenta]] |
| Qwen3.8-27B [[qwen3-8-27b]] | sufit odczytu | **926 GB/s** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| Qwen3.8-27B [[qwen3-8-27b]] | sweep T=1 | **100.0 t/s** | ROCm MTP (Magnitude Vulkan 50.1) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| Qwen3.8-27B [[qwen3-8-27b]] | szczyt VRAM fill 255k | **23367 MiB** |  | 2026-11-06 | [[raport-65-vram-rezerwa-mtp]] |
| Qwen3.8-27B [[qwen3-8-27b]] | T=0 reasoning | **154.2 t/s** | DRAFT_N=5 (baza 144.4) | 2026-10-20 | [[raport-35-xtx-eksperymenty]] |
| Qwen3.8-27B [[qwen3-8-27b]] | tg128 bitexact | **41.79 t/s** | 365af3e5e (prod 43.17) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| Qwen3.8-27B [[qwen3-8-27b]] | tg128 wide off | **40.86 t/s** |  | 2026-10-20 | [[raport-24f-mmvq-fa]] |
| Qwen3.8-27B [[qwen3-8-27b]] | tg128 wide=2 | **40.41 t/s** |  | 2026-10-20 | [[raport-24f-mmvq-fa]] |
| Qwen3.8-27B [[qwen3-8-27b]] | trening MTP | **2.3 k tok/s** | bf16 K=4 T=2048, szczyt 12.1 GiB | 2026-10-12 | [[2026-10-12-mtp-trening-faza1]] |
| Qwen3.8-27B [[qwen3-8-27b]] | TTFT 32k MTP | **35050 ms** | (bez spekulacji 33619) | 2026-10-18 | [[2026-10-18-hak-mtp-i-checkpointy]] |
| Qwen3.8-27B [[qwen3-8-27b]] | tura agenta S2-turn2 | **197 ms** | CKPT_VRAM=2 | 2026-10-20 | [[raport-38-ckpt-vram]] |
| Qwen3.8-27B [[qwen3-8-27b]] | utworzenie checkpointu | **14.9 ms** | CKPT_VRAM=2 | 2026-10-20 | [[raport-38-ckpt-vram]] |
| Qwen3.8-27B [[qwen3-8-27b]] | V16 − V5 przy 2k | **6.40 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| Qwen3.8-27B [[qwen3-8-27b]] | V16 − V5 przy 32k | **9.50 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| Qwen3.8-27B [[qwen3-8-27b]] | V16 − V5 przy 64k | **12.45 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| Qwen3.8-27B [[qwen3-8-27b]] | VRAM | **22319 MB** | lean reserve MTP (było 23360) | 2026-11-05 | [[2026-11-05-q63-topka]] |
| Qwen3.8-27B [[qwen3-8-27b]] | weryfikacja n=16 | **35.0 ms** | WMMA 0037 | 2026-10-13 | [[wmma-small-n]] |
| Qwen3.8-27B [[qwen3-8-27b]] | weryfikacja n=9 | **32.1 ms** | WMMA 0037 | 2026-10-13 | [[wmma-small-n]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | bench.py skill-io c1 | **110,3 t/s** | T 0,6, 6 × 512 tok. | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod 1,7k | **128,0 t/s** | SHORT_TAIL=32 (KILL, produkcja 135,4) | 2026-11-14 | [[2026-11-14-k104-krotki-ogon-promptu]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod 1,7k T=0 | **129,23 t/s** | xtxbench A/A, produkcja | 2026-11-09 | [[xtxbench-szybki-ab]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod 199k T=0 | **95.81 t/s** | KVQ_ONCE=1 (KILL, baza 94.12) | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod 255k | **78,7 t/s** | MTP n=4 eco 2200 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod 94k T=0 | **122.04 t/s** | KVQ_ONCE=1 (baza 120.97) | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod HumanEval+ ważony | **174,2 t/s** | T=0, MTP n4 + lookup | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod MTP | **115,3 t/s** | PM4 replay | 2026-10-14 | [[pm4-replay]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod MTP n=4 T=1 | **105.0 t/s** | po T1, 28.28 ms/krok | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod MTP n=5 T=1 | **108.4 t/s** | po T1 | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod MTP T=1 | **115.5 t/s** | amd-opt spec_sweep | 2026-10-15 | [[rx-7900-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod mvs T=0 | **414.8 t/s** | topka lookup W16, PM4=0 | 2026-10-19 | [[2026-10-19-build-topka]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod plain tg128 | **44.0 t/s** |  | 2026-10-15 | [[qwen3-8-27b-uncensored]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod po fillu 222k | **86,3 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod po fillu 255k | **73,6 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod sesja omp 0–32k | **127,2 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod sesja omp 128–160k | **95,8 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod sesja omp ważone | **120,8 t/s** | final mode, do 139k | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod spec_sweep T=1 mediana | **118,3 t/s** | final mode | 2026-11-06 | [[2026-11-06-final-mode]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod T=0 1,7k | **131,2 t/s** | LLAMA_SPEC_LOOKUP=0 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod ważony evalplus | **162,0 t/s** | T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | dekod ważony jakość-mini | **142.4 t/s** | T=0 | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | FA na krok przy 199k | **11.32 ms** | rocprofv3, ONCE=0 | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | fill 255k | **493,4 t/s** | FA D256 VAR 83, Q4_K_M, KV q4_0 (baza 466,3) | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | greedy 256 tok. | **106,4 t/s** | final mode | 2026-11-06 | [[2026-11-06-final-mode]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | HumanEval pass@1 | **97,6 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | HumanEval+ pass@1 | **92,7 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | jakość-mini 255/290 | **87.9 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | krok Vulkan 0007–0010 | **39.92 ms** |  | 2026-10-12 | [[vulkan-mmvq]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | llama-bench pp d128k | **486,3 t/s** | VAR 83 (baza 459,5) | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | MBPP+ pass@1 | **80,2 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | MMLU-Pro 140 pytań | **82.1 %** | effort low | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | MMVQ draftów na krok 1,7k | **1,93 ms** | ślad rocprofv3 | 2026-11-07 | [[2026-11-19-k111-k123-krok-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | MMVQ weryfikacji na krok 1,7k | **20,16 ms** | ślad rocprofv3, PM4 off, topka-q63 | 2026-11-07 | [[2026-11-19-k111-k123-krok-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | ms/krok MTP T=1 | **39.92 ms** | Vulkan łatki MMVQ | 2026-10-12 | [[2026-10-12-vulkan-krok-po-kroku]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | ms/krok spec_sweep T=1 | **26,86 ms** | eco 2200 (stock 26,32) | 2026-11-06 | [[2026-11-06-eco-szybki-bench]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | mvs | **434.9 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | pierwszy dekod K-001 | **130,7 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | pp4096 Q6K_WIDE (KILL, −0,01%) | **1000,6 t/s** | Q4_K_M, topka-q63, ABBA | 2026-11-07 | [[2026-11-07-q6k-mmq-skale]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill 12k | **916,0 t/s** | eco 2200 (stock 1036,8) | 2026-11-06 | [[2026-11-06-eco-szybki-bench]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill 130k | **650,8 t/s** | igły 3/3 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill 222k | **527,0 t/s** | igły 3/3, topka-q70, KV q4_0 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill 255k | **465,1 t/s** | topka-q63 eco 2200, KV q4_0 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill 32k | **865,61 t/s** | xtxbench A/A | 2026-11-09 | [[xtxbench-szybki-ab]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill 4242 tok. przy 103k | **498,6 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill 94k | **762 t/s** | K5+T3 0040-0045 | 2026-10-14 | [[prefill-mmq-fa]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill long 32k | **859,1 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill pp4096 | **1109 t/s** |  | 2026-10-15 | [[qwen3-8-27b-uncensored]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prefill ~16k bench.py | **932,9 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prompt krótkiego żądania mediana | **139,1 ms** | AP_TIMING | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | prompt krótkiej tury mediana | **148,5 ms** | SHORT_TAIL=32 (produkcja 148,7) | 2026-11-14 | [[2026-11-14-k104-krotki-ogon-promptu]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | spec_sweep | **115.5 t/s** | produkcja | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | spec_sweep T=1 | **119,2 t/s** | VAR 83 | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | spec_sweep T=1 1 seed | **106.9 t/s** | topka | 2026-10-19 | [[2026-10-19-build-topka]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | spec_sweep T=1 mediana | **119,3 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | tg128 | **268.27 t/s** | MOE_GU_BLOCK (=0 264.60) | 2026-10-18 | [[2026-10-18-lfm-moe-pasmo]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | tokenizacja mediana 82–119k | **6,6 ms** | TOK_CACHE+PARSE_INC (baza 14,0) | 2026-11-08 | [[2026-11-08-l1-tokenizacja-parser]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | top-1 zgodny kvq vs f16 | **97,595 %** | topka-q70 | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | tura agenta mediana | **12 441 ms** | #30137 + huge pages (A 13 413 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | tura agenta mediana 76–112k | **12 029 ms** | topka-q70 (baza 13 413) | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | tura poza prefillem | **1 619 ms** | TOK_CACHE+PARSE_INC (baza 1 704) | 2026-11-08 | [[2026-11-08-l1-tokenizacja-parser]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | update cache | **437,9 ms** | #30137 + huge pages (A 1 321,7 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | V16 − V5 przy 2k | **7,1 ms** | llama-bench, PM4, VAR 83 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | V16 − V5 przy 32k | **10,1 ms** | llama-bench, PM4, VAR 83 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | VRAM szczyt 255k | **23367 MiB** | ctx 262144 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | zapis wpisu cache | **266,6 ms** | #30137 + huge pages (A 1 055,5 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| Qwen3.8-27B-Uncensored [[qwen3-8-27b-uncensored]] | średnie KLD kvq vs f16 | **0,003862 KLD** | wikitext-2 c 8192, ub 5 (standard 0,004522) | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |

Optymalizacje na tej karcie ([[bilans-optymalizacji]]): [[argmax-dpp|argmax DPP (0026)]] (przyjete, 16.8 → 4.3 µs na wywołanie); [[attn-prep-fwht|attn prep + FWHT (0019, 0057, 0058)]] (przyjete, LFM 4.043 → 3.907 ms/token (0057), 3.928 → 3.879 (0058)); [[bariera-lds-rdna3|bariera tylko LDS (GGML_HIP_LDS_BARRIER)]] (odrzucone, w szumie (pp4096 1133.2 → 1129.7 t/s, czat 102.5 → 102.4)); [[budzet-megakernela-qwen-xtx|megakernel Qwen]] (w-toku, sufit ~4 ms/krok (+12%) wg szacunku, niezmierzone); [[cache-q8-1|cache q8_1 i producenci q8_1 (0003, 0015, 0049, 0056)]] (przyjete, +2–4% e2e (0003); 37.73 → 37.04 ms (0015)); [[cache-sesji-na-dysku|cache sesji na dysku (slot save/restore)]] (odrzucone, restore 53k 23–24× szybciej niż prefill (Qwen 2.51 s vs ~61.5 s); decyzja KV tylko w RAM); [[clamp-q8-1|clamp q8_1 do ±65504 (0023)]] (przyjete, poprawka poprawności, bitowo bez zmian); [[conv-lag|conv lag (0038)]] (przyjete, draft 8 krok 40.8 → 37.2 ms, draft 12 45.7 → 41.1 ms); [[fattn-kvq|FA kvq (0011, 0055, 0058)]] (przyjete, serwer 94k decode 43.0 → 70.9 t/s (+65%)); [[fuzje-lfm-moe|fuzje MoE LFM (0049, 0051, 0053, 0056)]] (przyjete, −0.565 ms/token (5.067 → 3.973 ms/token)); [[fuzje-weryfikacji|fuzje weryfikacji Qwena A3–A6]] (przyjete, 41.7 → 36.38 ms/krok (74.8 → 86.4 t/s)); [[gdn-fast|GDN fast (DPP)]] (odrzucone, +0.15% tg128, pp512 +0.7% (szum)); [[gdn-fuzje-k2|fuzje GDN (0027, 0028, 0045)]] (przyjete, 0028 ~0.33 ms/krok; 0045 pp2048 1082 → 1108 (+2.4%)); [[gdn-replay|GDN replay (S4, 0033–0036)]] (przyjete, GDN 793 → 638 µs/weryfikację; VRAM stanów 748 → 195 MiB); [[glowica-draftu-rerank|głowica draftu gruba + rerank top-K]] (w-toku, niezmierzone; cel odzyskać −2–3% akceptacji IQ4_XS); [[gumbel-max|op GGML_OP_GUMBEL_MAX]] (przyjete, koszt +0.11 ms/krok (27.74 → 27.85) w wersji 2); [[kontroler-szerokosci-draftu|kontroler szerokości draftu]] (odrzucone, T2 103.6 vs 102.7 t/s (nic); kontroler 5/8/16 wynik zerowy); [[kv-raz-na-weryfikacje|KV raz na weryfikację (GGML_HIP_KVQ_ONCE)]] (odrzucone, FA −6.1% przy 199k (próg −10%), e2e 199k +1.79%); [[latki-hostowe|łatki hostowe (0029, 0047, 0059)]] (przyjete, K3 32.14 → 30.97 ms/krok (97.8 → 101.5 t/s); 0047 102.6 → 104.2 t/s); [[latki-spekulacji|słownik draftu 64k + draft IQ4_XS (0004, 0032)]] (przyjete, 0004 +7.5% (64k); 0032 netto +1–3% t/s); [[lfm-shortconv|fuzje shortconv LFM (0050, 0054, 0062)]] (przyjete, −0.366 ms/token (~22% zysku LFM)); [[mmq-epilog|epilog MMQ VOPD (0070)]] (przyjete, +2.2% pp4096 (1099.5 → 1123.2 t/s)); [[mmq-q6k-skale-lds|MMQ Q6_K skale przez b128]] (odrzucone, 0,0% (pp4096 1000,7 → 1000,6)); [[mmvq-moe-gate-up-blok|MMVQ MoE gate+up blok (GGML_HIP_MOE_GU_BLOCK)]] (przyjete, mikrobench −7% (24.16 → 22.32 µs)); [[mmvq-multikolumnowe|MMVQ wielokolumnowe (0001, 0002, 0021, 0022)]] (przyjete, Qwen MTP 68.6 → 82.3 t/s; K1 35.67 → 33.17 ms/krok); [[mmvq-n1-wiersze|MMVQ n=1 2 wiersze na blok (0052, 0064)]] (przyjete, LFM 4.610 → 4.509 ms/token (+2.2%); Uncensored 3.933 → 3.706 ms (+6.1%); 3090 LFM +8.5%); [[mtp-draft-graf|draft MTP jednym grafem (0020) + scheduler (0030)]] (przyjete, 36.39 → 35.67 ms/krok (0020); 31.89 → 31.59 ms (0030)); [[opoznienia-ttft|cache MTP + CKPT_VRAM=2 (TTFT)]] (przyjete, start 38.5 → 6.55 s; tura agenta 687/579 → 197 ms); [[para-mmvq|para MMVQ jedną siatką (0024)]] (przyjete, K2 33.17 → 32.14 ms/krok); [[pm4-replay|PM4 replay (0060, 0061, 0063)]] (przyjete, LFM 3.887 → 3.424 ms/token; Qwen MTP 103.7 → 108.8 t/s); [[prefill-mmq-fa|kafle MMQ i FA prefill (0040–0045)]] (przyjete, prefill 94k 668 → 767 t/s); [[raport-24c-wiele-zapytan|wiele zapytań -np 2/4]] (odrzucone, −5…−17% single; fan-out wall 258.0 → 287.4 s (+11%)); [[raport-24d-lfm-lookup|lookup kontekstowy bez draftera (LFM)]] (odrzucone, +17% copy W8 (288,2 → 334,7 t/s), tekst T=0 ≠ plain); [[raport-24f-mmvq-fa|MMVQ n=1 szeroki loader (wide=2)]] (odrzucone, −1,0% tg128 (40,86 → 40,41 t/s)); [[raport-24h-kv-jeden-przebieg|jeden przebieg KV w fattn-kvq dla weryfikacji MTP]] (odrzucone, sufit +3,0…6,6% e2e przy 94k, ≤ 2,3% przy 32k (cel +8%)); [[raport-24k-koszt-weryfikacji|profil kosztu weryfikacji W16 vs MTP4]] (w-toku, krok W16 35,61 ms vs MTP4 29,62 ms (+20%)); [[raport-24l-fuzja-norm|fuzja RMS norm do MMVQ (ogon producenta)]] (odrzucone, page fault + mode1 reset GPU, matvec różny 13/216); [[raport-24m-weryfikacja-gpu|weryfikacja draftu top-128 na GPU (LLAMA_GPU_VERIFY)]] (przyjete, +2,4% mvs (410,4 → 420,1 t/s)); [[raport-24n-mmvq-n5|obłożenie MMVQ n=5 (GGML_HIP_MMVQ_OCC)]] (odrzucone, −0,5% spec_sweep (111,4 → 110,8 t/s), serializacja −6,4%); [[raport-24o-luki-hosta|przełączniki luk hosta (YIELD_FAST=2, PM4_MIN_DISPATCH=16, PM4_LAZY_EXEC=1)]] (przyjete, czat T=1 113,8 → 117,9 t/s); [[raport-24p-sprzezone-t1|sprzężone próbkowanie draftu (LLAMA_SPEC_COUPLED)]] (przyjete, +3,5% T=1 (107,6 → 111,4 t/s)); [[raport-24q-adaptacyjna-spekulacja|adaptacyjna spekulacja (bramka ogona, głębokość MTP)]] (odrzucone, bramka ogona ≤ +0,5%; głębokość adaptacyjna zmienia greedy md5); [[raport-24r-mmvq-pasmo|MMVQ n=5 RPB=1]] (odrzucone, −3,0% (27,98 → 28,80 ms/krok)); [[raport-24u-norm-quant|osobny kernel rms_norm × w + quantize q8_1]] (odrzucone, ≈ 0,012 ms/krok (próg 0,25 ms)); [[raport-24v-prefill-fa|FA D=256 prefill bez spilli (sched_barrier)]] (odrzucone, +0,84% pp512@d32k, +0,40% pp16384); [[raport-24w-pair2|PAIR2 para MMVQ dla mieszanych typów]] (odrzucone, +0,4% czat T=1 (115,1 → 115,6 t/s)); [[raport-38-ckpt-vram|checkpointy GDN w VRAM (LLAMA_CKPT_VRAM=2)]] (przyjete, TTFT 2k −22%, S2-turn2 687 → 197 ms); [[raport-44-spec-route|routing profili spekulacji (LLAMA_SPEC_ROUTE)]] (w-toku, brak pomiaru (ABBA padło)); [[raport-46-mmvq-big|MMVQ n=5 duże kształty (pipelining Q4_K + 8 fal)]] (odrzucone, −15% mikrobench 17408×5120, ABBA bez zysku); [[raport-48-norma-gdn-bank|drugi bank stanu GDN]] (odrzucone, E0 −0,4% (v1/v2); v3 nierozstrzygnięty); [[raport-49-mmvq-ogon-1024|MMVQ n=5 ogon k/v 1024 wierszy]] (w-toku, szac. −0,03 ms/krok, bez bramki); [[raport-50a-mmvq-q4k|MMVQ Q4_K n=5 kernel strumieniowy]] (w-toku, plain −3…−6%, pary −10…−21% (mikrobench)); [[raport-50b-mmvq-q5k|MMVQ Q5_K n=5 big_rows]] (w-toku, −1,3…−3,5% na 8192–34816 wierszach); [[raport-50c-mmvq-q6k|MMVQ Q6_K n=5 potok ping-pong]] (w-toku, szac. −0,15 ms/krok, bramki nieuruchomione); [[raport-50d-mmvq-iq4xs|MMVQ IQ4_XS n=5 ryp2]] (w-toku, para ffn −3,7%, down+residual −6,8%); [[raport-51-male-kernele|małe kernele weryfikacji (rms_norm, FA kvq, GDN)]] (odrzucone, sufit ≤ 0,26 ms/krok, brak zwycięzcy); [[raport-53-draft-shortlist|shortlist w głowicy draftu MTP (LLAMA_DRAFT_SHORTLIST)]] (w-toku, bramka recall nie przeszła (40,8% ridge K=1024), VRAM +536 MiB); [[raport-54-mniej-granic|fuzje ATTN_PREP_MT i KVQ_FWHT_GATE (mniej granic dispatchy)]] (odrzucone, proza +0,24% (szum), mvs 0,0% (428,49 → 428,55 t/s)); [[raport-65-vram-rezerwa-mtp|chuda rezerwa grafu kontekstu draftu MTP]] (przyjete, bufor MTP 1081,23 → 40,28 MiB, kontekst 262 144 (+28%)); [[rmsnorm-dpp|rms_norm·mul(+q8_1) z redukcjami DPP (0025)]] (przyjete, 5,87 → 4,51 µs przy 5120 kolumnach); [[sampler-fast-path|szybka ścieżka samplera (0031, 0048, 0065–0069)]] (przyjete, narzędzia omp Qwen MTP 104,8 → 113,2 t/s, LFM 254,2 → 294,3); [[seria-amd-opt|kandydat 0071 GGML_HIP_MOE_GU_BLOCK]] (w-toku, LFM +0,33% / Uncensored +1,39%); [[sprzezone-probkowanie-draftu|sprzężone próbkowanie draftu (Gumbel-max)]] (przyjete, +3,5% T=1 (107,6 → 111,4 t/s)); [[trwala-siatka-bez-pm4|trwała siatka MoE bez PM4]] (w-toku, strata PM4-off 293,7 → 259,3 t/s do odzyskania); [[tryb-stratny-pflash|PFlash tryb stratny długich dokumentów]] (w-toku, niezmierzone (pilot etap C)); [[vulkan-mmvq|Vulkan RDNA matvec i MMVQ (0006–0010)]] (odrzucone, −5,2% ms/krok (43,73 → 41,46), backend poza domyślną ścieżką); [[wmma-small-n|WMMA small-N weryfikacja 9–16 kolumn (0037)]] (przyjete, n=9 49,2 → 32,1 ms, n=16 51,0 → 35,0 ms).
<!-- TABELE:END -->

## Powiązane
- [[karty/_hub|Karty]]
- [[rdna3-gfx1100]]
- [[amdgpu-moc-i-termika]]
- [[stan-2026-10-15]]
- [[rtx-5060-ti]]
- Inne platformy z planu: [[rx-9070-xt]], [[radeon-ai-pro-r9700]], [[strix-halo]], [[mi300x]], [[arc-b580-i-mac]]
