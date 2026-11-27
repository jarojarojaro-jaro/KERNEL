---
typ: model
tags: [modele, lfm, moe]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:333-341,354,363; ~/KERNEL/qwen-opt/STATUS-NEXT.md:12; ~/KERNEL/product/research/06-produkt-ux-prawo-biznes.md:51,355; ~/KERNEL/product/research/10-post-training.md:141; ~/KERNEL/qwen-opt/tools/kld-canary.md:66-67; ls ~/models (2026-10-16); ~/KERNEL/product/research/09-chmura-5060ti.md:76-86,156,164-186,197; ~/KERNEL/product/research/09-chmura-3090.md:53-61; ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:15-33,83-89; ~/KERNEL/product/research/18-nastepna-fala.md:143-163,500-512
status: aktualne
model: lfm2-5-24b-a2b
rozmiar: 24B-A2B
kwant: Q5_K_M
karty: rx-7900-xtx, rtx-3090, rtx-5060-ti
wyniki:
  - lfm2-5-24b-a2b | rx-7900-xtx | 293.7 t/s | dekod; Q5_K_M, KV q8_0, rundy 1–4 | 2026-10-15
  - lfm2-5-24b-a2b | rx-7900-xtx | 6175 t/s | prefill pp4096; Q5_K_M | 2026-10-15
  - lfm2-5-24b-a2b | rtx-3090 | 263.9 t/s | dekod; Q5_K_M, profil Ampere | 2026-10-16
  - lfm2-5-24b-a2b | rtx-5060-ti | 226.8 t/s | dekod serwer; QAD-Q4_0 | 2026-10-16
  - lfm2-5-24b-a2b | rtx-5060-ti | 207.86 t/s | dekod; Q4_K_M | 2026-10-16
---
# LFM2.5-24B-A2B (Liquid AI)

**MoE 24B z ~2B aktywnymi parametrami i warstwami krótkiej konwolucji; na RX 7900 XTX z 173 do 294 t/s, bez spekulacji (brak draftera).**

Architektura (`lfm2moe`, NOTES 2026-10-14): 40 warstw (30 shortconv + 10 GQA 32/8), 2 pierwsze gęste, potem MoE 64 ekspertów / 4 aktywne (ffn 1536), emb 2048, słownik 128k, głowica związana z `token_embd` (Q6_K, 205 MiB). Eksperci Q5_K/Q6_K = 15.1 GiB z ~16 GiB. Bajty na token ≈ 1.8 GB → próg pasma ~1.9 ms (~500 t/s).

Plik: `~/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf` (15.86 GiB). Ustawienia (`run-llm.sh lfm`): ctx 131072, **KV q8_0** (decyzja użytkownika), bez spekulacji.

Wyniki: baza na forku przed pracą pod LFM — czat 173 t/s, tg128 198 t/s (upstream 169.3); po rundach 1–4 (2026-10-15): **293.7 t/s**, 3.41 ms/krok, pp4096 6175, tg128 289.7.

KV q8_0 vs f16: KLD 0.044 (q4_0: 0.128). Draftery: brak (jest tylko DFlash dla LFM2.5-1.2B / VL-3B). W `~/models/lfm` leży też LFM2.5-2.6B-QAD-Q4_0 (1.48 GiB), bez pomiarów w notatkach.

Na NVIDIA (raport 09, 2026-10-16): RTX 3090 Q5_K_M A0 180.2 → nasz silnik 263.9 t/s (profil Ampere); RTX 5060 Ti Q4_K_M 147.69 → 207.86 t/s. Q5_K_M (15.86 GiB) nie mieści się w 16 GB (z `--n-cpu-moe 6` tylko 120.9 t/s tg128). Najlepszy plik dla 16 GB to oficjalny **QAD-Q4_0** Liquid (quantization-aware distillation, 13.58 GB): KLD 0.2029 (Q4_K_M 0.2008), PPL(Q)/PPL(Q8) 0.869, serwer 164.5 → 226.8 t/s (+38%) i md5 forka = upstream. Prefill LFM rośnie o +56% z `-b 2048 -ub 2048`.

Licencja: LFM Open License v1.0 — za darmo komercyjnie tylko poniżej 10 M$ rocznego przychodu (dotyczy też klientów B2B).

Pasmo MoE (16g, 2026-10-18): narzut matvec 718 µs/token; gate+up ekspertów 673 GB/s, in_proj+conv 593, out_proj 519, głowica Q6_K 894 GB/s. Kandydat `GGML_HIP_MOE_GU_BLOCK`: +0.33% (szum), usuwa rozrzut między procesami (llama-bench 286.8–294.0 → 291.4–293.1 t/s) ([[2026-10-18-lfm-moe-pasmo]]).

Raport 18: KV q8_0 10 880 B/token, głowica 215 MB = 12% bajtów, roofline @0 540 t/s (zmierzone 54%); LFM2.5-2.6B-QAD ma ten sam słownik 128 000, ale jako drafter za drogi (1.5 GB/token) ([[model-kosztu-weryfikacji-moe]]).

<!-- TABELE:START -->
## Wyniki z notatek (49)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-27); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod | **102,47 t/s** | UD-IQ3_XXS ctx 131 072 | 2026-11-07 | [[rtx-3060]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod | **263.9 t/s** | nasz silnik (A0 180.2) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod T=1 | **263.9 t/s** | Q5_K_M fork (A1 176.0) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| NVIDIA RTX 3090 [[rtx-3090]] | serwer A2p | **263.9 t/s** | profil Ampere | 2026-10-16 | [[raport-09-chmura-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | sweep fork | **291.6 t/s** | (Magnitude 209.0) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg64 64k | **208.12 t/s** | kvq CUDA, q8_0 (bez 159.65) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg64@64k | **208,12 t/s** | kvq-mma f08dc78bb | 2026-10-16 | [[fattn-kvq]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod | **149.4 t/s** | QAD-Q4_0 | 2026-10-20 | [[rtx-4060-ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | serwer | **149.4 t/s** | QAD-Q4_0 | 2026-10-20 | [[raport-29-4060ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[rtx-5060-ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod serwer | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[lfm2-5-24b-a2b]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod T=1 | **207.86 t/s** | Q4_K_M fork (A1 144.47) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | serwer | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[raport-09-chmura-5060ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | sweep 32k fork | **205.1 t/s** | (Magnitude 157.8) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | tg64 64k | **155.77 t/s** | kvq CUDA, Q4_K_M (bez 119.82) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | copy bez lookup | **288.2 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | copy lookup W16 | **312.4 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | copy lookup W8 | **334.7 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat | **274.1 t/s** | topka (upstream 146.8) | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=1 | **173 t/s** | Q5_K_M, KV q4_0, bez MTP | 2026-10-14 | [[lfm-baza]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod | **293.7 t/s** | amd-opt | 2026-10-15 | [[rx-7900-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod budżet myślenia | **292.9 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod narzędzia omp | **294.3 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain PM4 off | **259.3 t/s** |  | 2026-10-19 | [[trwala-siatka-bez-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain PM4 on | **293.7 t/s** |  | 2026-10-19 | [[trwala-siatka-bez-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain tg128 | **292,1 t/s** | PM4 replay | 2026-10-14 | [[pm4-replay]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod reasoning_control | **292.9 t/s** | sampler fast (było 256.9) | 2026-10-15 | [[2026-10-15-sampler]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod spec_sweep | **293.7 t/s** | Q5_K_M, 3404 µs/token | 2026-10-16 | [[2026-10-16-budzet-lfm-megakernel]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MoE down Q5_K produkcja | **11.64 µs** | moebench | 2026-10-18 | [[2026-10-18-lfm-moe-negatywne]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | odczyt sesji 53k z SSD | **0,53 s** | slot-save-path | 2026-10-18 | [[cache-sesji-na-dysku]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp4096 | **6180 t/s** | fork | 2026-10-14 | [[lfm-baza]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 64k | **14.6 s** | (Magnitude 32.7 s) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp16384 | **6680 t/s** | ub 2048 (ub 512 5654) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp4096 | **7148 t/s** | ub 2048 (ub 512 6108) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | serwer lfm none | **218.6 t/s** | łatki 0048–0052 | 2026-10-14 | [[lfm-runda-1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep | **293.7 t/s** | KV q8_0 | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep lfm none T=1 | **293.75 t/s** | PM4 replay | 2026-10-14 | [[lfm-runda-4-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 | **293.7 t/s** | Q5_K_M, KV q8_0 | 2026-10-15 | [[stan-2026-10-15]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | start sesji agenta | **230 ms** | CACHE_SHARE_MIN=1024 (było 1357) | 2026-10-18 | [[2026-10-18-cache-promptu-agenta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | sweep plain | **322.9 t/s** | Q4_K_M (Magnitude 219.6) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 | **292.22 t/s** | MOE_GU_BLOCK 7c5b2a116 (=0 291.26) | 2026-10-18 | [[2026-10-18-lfm-moe-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 98k | **191.4 t/s** | KV q8_0, kvq q8 (baza 152.4) | 2026-10-14 | [[lfm-runda-3]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 górna granica | **323.97 t/s** | PM4_UB down,mmvq1 bez synchronizacji | 2026-10-18 | [[2026-10-18-pm4-ub-lfm]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 głębokość 0 | **262.1 t/s** | KV q8_0, łatki 0055–0059 | 2026-10-14 | [[lfm-runda-3]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 głębokość 98304 | **212.95 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 KV q8_0 | **294.84 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | token 98k | **5,462 ms** | KV q8_0, kvq 0055 | 2026-10-14 | [[fattn-kvq]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | token tg | **3,402 ms** | po 0062 CONV_ROWS4 | 2026-10-14 | [[lfm-shortconv]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | TTFT 32k | **5690 ms** | ub 2048 (ub 512 6676) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |
<!-- TABELE:END -->

## Powiązane
- [[modele/_hub|Modele]]
- [[lfm2-5-uncensored]]
- [[fuzje-lfm-moe]]
- [[liquidai]]
- [[lfm-runda-4-pm4]]
- [[raport-09-chmura-5060ti]]
