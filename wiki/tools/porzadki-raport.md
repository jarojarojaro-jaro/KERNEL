# Porządki wiki: wykonane 2026-11-22

Akcje: archiwum 10, hub 8, korzen 8, przenies 373, scal 37, zostaje 372

| część | przed | po |
|---|---|---|
| (korzeń) | 8 | 8 |
| archiwum | 0 | 47 |
| chmura | 6 | 0 |
| decyzje | 43 | 37 |
| ekosystem | 0 | 100 |
| eksperymenty | 85 | 0 |
| karty | 12 | 18 |
| kernele | 33 | 0 |
| latki | 8 | 0 |
| lekcje | 123 | 123 |
| llm | 7 | 4 |
| ludzie-firmy | 28 | 0 |
| metody | 58 | 24 |
| modele | 23 | 27 |
| narzedzia | 31 | 33 |
| nvidia | 10 | 0 |
| optymalizacje | 0 | 98 |
| produkt | 36 | 29 |
| repo | 91 | 0 |
| research | 166 | 81 |
| rocm | 23 | 0 |
| stos | 0 | 39 |
| testy | 0 | 123 |

Pliki repo poza wiki z odwołaniami do przenoszonych notatek: 32 (74 odwołań): product/BENCHMARKI-PRZED-PO-2026-10-19.md, product/research/57b-strata-qwen38-flash.md, product/research/69a-dspine-27b.md, product/research/28-moe-offload-silniki.md, product/research/23e-re-silniki.md, product/research/32d-localmaxxing.md, product/research/68-SYNTEZA.md, product/research/57c-dgx-spark-miaai.md, product/research/23f-podrecznik-optymalizacji-gpu.md, product/research/68c-dlugi-kontekst-gdn.md, product/research/63a-silniki-lokalne.md, product/research/21b-gpu-perf-zasoby.md, product/research/67c-nvidia-backlog-testow.md, product/research/60c-quant-and-3090-engines.md, product/research/21j-flameox.md, product/research/23d-re-runtime-amd.md, product/research/57d-freetoken-nvfp4.md, product/research/32a-maya-1117-strata-020-gyro.md, product/research/64-termika-bezpieczenstwo.md, product/research/66d-saber-engine-rdna.md, product/research/67-nvidia-vast-kampania.md, product/research/70-fa-d256-jak-to-zrobilismy.md, product/research/63c-amd-rocm-llamacpp.md, product/research/69b-tensorfold-qwen-warp.md, product/research/15d-prefill-dlugi-kontekst.md, product/research/69-SYNTEZA.md, product/research/21g-nowe-silniki.md, product/research/39a-maya-1119.md, app/engine/test/catalog.measured.json, qwen-opt/README.md, qwen-opt/patches/topka-q70/README.md, qwen-opt/env/SRODOWISKO-TRENINGOWE.md

Scalenia (B → A):
- chmura/harness-chmurowy → narzedzia/skrypty-chmury: te same skrypty ~/qwen-opt/cloud dwa razy
- ludzie-firmy/firma-magnitude → ekosystem/magnitude: ten sam konkurent dwa razy (firma i repo)
- ludzie-firmy/firma-runpod → karty/runpod: ten sam dostawca dwa razy (firma i chmura)
- ludzie-firmy/firma-salad → karty/salad: ten sam dostawca dwa razy (firma i chmura)
- ludzie-firmy/firma-vast-ai → karty/vast-ai: ten sam dostawca dwa razy (firma i chmura)
- modele/qwen38-27b-inferencex → research/raport-21f-inferencex: wpis InferenceX to część raportu 21f, nie model
- nvidia/nvidia-wyniki-2026-10-16 → testy/2026-10-16-kampania-nvidia: ta sama kampania 2026-10-16 dwa razy
- produkt/produkt-analiza-platformy → metody/analiza-platformy: analiza platformy dwa razy (plan i metoda)
- repo/cuda-compat-galaz → stos/cuda-compat: ta sama gałąź cuda-compat dwa razy
- research/raport-11-mtp-pl-pilot → testy/2026-10-16-mtp-pl-pilot: ten sam raport 11 dwa razy
- research/raport-12-bit-exact → testy/2026-10-16-bit-exact: ten sam raport 12 dwa razy
- research/raport-13-rocm-10-1 → stos/rocm-10-1: ten sam raport 13 dwa razy
- research/raport-14-nemotron-3090 → testy/2026-10-16-nemotron-3090: ten sam raport 14 dwa razy
- research/raport-16a-pm4-pdl → testy/2026-10-18-pm4-pdl-x1: ten sam raport 16a dwa razy
- research/raport-16b-lookup-tail → testy/2026-10-18-lookup-ogon: ten sam raport 16b dwa razy
- research/raport-16c-kvq-cuda → testy/2026-10-16-kvq-cuda: ten sam raport 16c dwa razy
- research/raport-16d-magnitude-vs-nasz → testy/2026-10-16-magnitude-vs-fork: ten sam raport 16d dwa razy
- research/raport-16e-kwanty-kld → testy/2026-10-18-e1-kwanty-27b-kld: ten sam raport 16e dwa razy
- research/raport-16g-lfm-moe-pasmo → testy/2026-10-18-lfm-moe-pasmo: ten sam raport 16g dwa razy
- research/raport-16h-fabryka-v1 → metody/fabryka-v1: ten sam raport 16h dwa razy
- research/raport-16j-magnitude-vulkan-xtx → testy/2026-10-18-magnitude-vulkan-xtx: ten sam raport 16j dwa razy
- research/raport-16k-sprzezone-probkowanie → testy/2026-10-18-sprzezone-probkowanie-mtp: ten sam raport 16k dwa razy
- research/raport-17-gpu-page-fault → testy/2026-10-19-page-faulty-gpu-analiza: ten sam raport 17 dwa razy
- research/raport-19-kb-wyszukiwanie → narzedzia/kb: raport 19 opisuje narzędzie kb
- research/raport-20-build-topka → testy/2026-10-19-build-topka: ten sam raport 20 dwa razy
- research/raport-21j-flameox → ekosystem/flameox: repo i raport o nim to jeden podmiot
- research/raport-21k-smokinggun → ekosystem/smokinggun: repo i raport o nim to jeden podmiot
- research/raport-23b2-bariery-lds → research/raport-23b-re-kernele-amd: druga część tego samego RE kerneli AMD
- research/raport-23f-podrecznik-gpu → metody/podrecznik-gpu: podręcznik GPU dwa razy
- research/raport-24a-bariera-lds → optymalizacje/bariera-lds-rdna3: ta sama technika (bariera tylko LDS) dwa razy
- research/raport-32b-deepinfer → ekosystem/deepinfer: repo i raport o nim to jeden podmiot
- research/raport-32e-safe-special → stos/bezpieczenstwo-tokenow-specjalnych: SAFE_SPECIAL dwa razy
- research/raport-39f-nvidia-flare → ekosystem/nvidia-flare: repo i raport o nim to jeden podmiot
- research/raport-45-opoznienia → optymalizacje/opoznienia-ttft: opóźnienia topki dwa razy
- research/raport-52-eagle4 → ekosystem/eagle-4: repo i raport o nim to jeden podmiot
- research/raport-67-kampania-nvidia → testy/2026-11-07-kampania-nvidia-vast: kampania 67 dwa razy
- research/runda-6-raporty → testy/runda-6: runda 6 dwa razy

Archiwum:
- decyzje/2026-10-09-limit-mocy-odlozony (następca: decyzje/2026-10-20-karta-fabrycznie): uchylona: od 20.10 karta fabrycznie (bez zmian limitu mocy), od 06.11 profil eco 2200 MHz; 285 W z 09.10 nie obowiązuje
- decyzje/2026-10-15-zakaz-gpu-w-nocy (następca: brak): czasowy zakaz z 15.10 (od 00:45 do 02:00), minął tej samej nocy
- decyzje/2026-10-16-bez-lokalnego-gpu (następca: kernel-od-a-do-z): uchylona: od 19.11 testy na XTX na polecenie JARO (mapa Kernela, „Czego nie robię bez zgody”; kolejka K-… na XTX)
- decyzje/2026-10-16-budzety-chmury (następca: karty/vast-ai): jednorazowa kampania 16.10 ($5 Vast, $6 RunPod), zamknięta i rozliczona; dziś budżet każdorazowo ze zgody JARO
- decyzje/2026-10-16-saluki-bonsai-na-3060 (następca: decyzje/2026-11-14-saluki-usuniety): Saluki usunięty 14.11
- decyzje/2026-10-20-chmura-wstrzymana (następca: karty/vast-ai): uchylona: od 17.11 testy na Vaście ze zgodą i budżetem JARO (K-114, K-118, Colab od 22.11)
- eksperymenty/2026-10-19-plan-e1-rsr27b (następca: KOLEJKA-TESTOW): plan niewykonany, zastąpiony pozycją K-074
- eksperymenty/2026-10-19-plan-retro-rsr-0070 (następca: KOLEJKA-TESTOW): plan niewykonany, zastąpiony pozycją K-060
- nvidia/backlog-testow-nvidia (następca: KOLEJKA-TESTOW): backlog ze stanem 2026-11-07, pozycje są w kolejce K-…
- produkt/kv-na-dysku-polityka (następca: decyzje/2026-10-19-kv-tylko-w-ram): status nieaktualne, zastąpiona decyzją KV tylko w RAM

Wynik: {'przenies': 373, 'scal': 37, 'archiwum': 10, 'linkow': 1658, 'huby': {'usuniete_huby': ['chmura/_hub', 'eksperymenty/_hub', 'kernele/_hub', 'latki/_hub', 'ludzie-firmy/_hub', 'nvidia/_hub', 'repo/_hub', 'rocm/_hub'], 'linki': 19}, 'index': 'zaktualizowano 14 plików', 'lint': '805 notatek, 0 błędów, 67 ostrzeżeń'}

Pełny plan: tools/porzadki-plan.tsv (stara, nowa, akcja, cel, powód).
