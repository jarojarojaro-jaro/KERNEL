---
typ: hub
tags: [ludzie-firmy, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Ludzie i firmy

**Firmy, dostawcy, konkurenci i ludzie związani z projektem.**

Dostawcy chmury są w [[chmura/_hub|Chmurze]], projekty open source w [[repo/_hub|Repo]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (25)

- [[actual-computer|Actual Computer (silnik „e”, relay)]] — Firma z silnikiem „e” (host w asemblerze AArch64 + cubiny sm_103a, tylko DGX Station GB300) i relayem na AWS Nitro; na sprzęcie konsumenckim uruchamia vendored llama.cpp albo silnik „malibu”.
- [[firma-amd|AMD]] — Producent naszej karty RX 7900 XTX i stosu ROCm; dla produktu raczej kanał dystrybucji niż konkurent.
- [[conway-research|ConwayResearch (Underdog)]] — Autor Underdog Saluki 27B: IQ2-mix Qwen3.8-27B (7.89 GB) na bazie ISTA GSQ-RCO, strojony pod zachowanie tool callingu.
- [[ggml-org|ggml-org / llama.cpp]] — Upstream naszego silnika: llama.cpp wydaje ok. 24 buildy dziennie i od 2026-10-15 linię semver (v0.7.0); polityka AI zakazuje automatycznych PR-ów.
- [[gigagpu|GigaGPU (UK)]] — Brytyjski dostawca dedyków w abonamencie miesięcznym z rootem: RX 9070 XT, R9700, Ryzen AI Max+ 395 i Intel Arc Pro B60/B70.
- [[hostkey|Hostkey]] — Dostawca bare metal z rootem: RX 7900 XTX (pre-order) i Radeon AI PRO R9700 (RDNA4, gfx1201) za €0.471/h.
- [[hugging-face|Hugging Face]] — Hub modeli, z którego pobieramy GGUF; od lutego 2026 dom ggml.ai (llama.cpp), a 2026-09-03 NVIDIA ogłosiła jego przejęcie za 12,93 mld $.
- [[ista-daslab|ISTA-DASLab]] — Grupa z Institute of Science and Technology Austria, autorzy GSQ-RCO: PTQ, która dopracowuje publiczne GGUF K-quanty w tym samym formacie.
- [[jan|Jan (Menlo Research)]] — Darmowa aplikacja desktop z wbudowanym llama.cpp (CUDA 13 + Vulkan, bez ROCm), z etykietami „Fits / May be slow / Won't fit”.
- [[lemonade|Lemonade (AMD)]] — Serwer/aplikacja AMD do uruchamiania GGUF (llama.cpp) na Ryzen AI i Radeonach, z instalatorem 10 MB i dociąganiem backendów.
- [[liquidai|LiquidAI]] — Twórca rodziny LFM, w tym naszego drugiego modelu LFM2.5-24B-A2B (2026-10-12), na licencji LFM Open License v1.0 z progiem 10 mln USD przychodu.
- [[lm-studio|LM Studio]] — Własnościowa aplikacja desktop na llama.cpp + MLX, darmowa także do pracy; zarabia na chmurze (Bionic+ 20 $/mies., Pro 100 $/mies.).
- [[metr-sakana|METR i Sakana (agenci kerneli)]] — Dwa punkty odniesienia dla agentów piszących kernele: METR (1.81× średnio, ~$20/zadanie) i Sakana AI CUDA Engineer (wycofane „10–100×”, 3.13× → 1.49× po usunięciu reward hackingu).
- [[firma-nvidia|NVIDIA]] — Lider rynku GPU (~76% Steam) i główny wolumen dla produktu; zamknął ChatRTX i wnosi przyspieszenia do llama.cpp, Ollamy i LM Studio.
- [[ollama|Ollama]] — Najpopularniejsza aplikacja do lokalnych LLM i główny punkt odniesienia „przed” (65 M$ Series B w lipcu 2026).
- [[prismml|PrismML]] — Autor Ternary Bonsai 2 27B (Qwen3.8-27B w trytach, Apache-2.0) i forka llama.cpp z formatami PQ2_0/PTQ1_0.
- [[qwen-alibaba|Qwen / Alibaba]] — Twórca Qwen3.8-27B, naszego flagowego modelu (Apache-2.0); Alibaba publikuje też atrex-kernel-agent.
- [[firma-runpod|RunPod]] — Chmura GPU z Community i Secure Cloud; NVIDIA od 3070 do 5090 i A100, z AMD tylko MI300X ($2.39).
- [[firma-salad|Salad (SaladCloud)]] — Rozproszona chmura na komputerach graczy; jedyne godzinowe konsumenckie Radeony, ale tylko w kontenerze WSL2 bez `/dev/kfd` i bez SSH.
- [[scaleway|Scaleway]] — Francuski dostawca z Mac mini as-a-service (bare metal macOS); nasza droga do testów Metal przed zakupem Maca.
- [[thinking-machines|Thinking Machines (batch invariance)]] — Laboratorium AI, autor wpisu „Defeating Nondeterminism in LLM Inference” (10.09.2025) o niezależności wyniku od wielkości wsadu (batch invariance).
- [[turbollm|TurboLLM]] — Flag-tuner dla llama.cpp (285★, FSL-1.1 → Apache-2.0): mierzy przy ładowaniu i dobiera warstwy, MoE offload, KV quant i sampling.
- [[ukisai|UkisAI (autor Swift)]] — Autor Swift 1.0/1.5 – fine-tune’ów Qwen3.8-27B na krótsze myślenie – z licencją Swift Open License v1.0, która dopuszcza użycie komercyjne tylko poniżej US$1M przychodu rocznie.
- [[unsloth|Unsloth]] — Autor kwantów GGUF „UD” (Unsloth Dynamic), z których korzystamy (Qwen3.8-27B UD-Q4_K_XL), oraz narzędzi do fine-tune/QLoRA.
- [[firma-vast-ai|Vast.ai]] — Rynek wynajmu GPU na godziny; nasze główne źródło NVIDIA do testów (kontenery do benchmarków, VM do profilowania).
<!-- AUTO:END -->
