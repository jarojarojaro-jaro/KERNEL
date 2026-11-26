---
typ: research
tags: [research, linki, dfly2, spekulacja, kernele, amd, moe, kv, sparse-attention]
aktualizacja: 2026-11-26
zrodlo: panel JARO 2026-11-26 20:26 (8 linków X); źródła pierwotne niżej; triage podagentów LnkKernelsHub, LnkDFly2, LnkSparseMisc; treść 3 tweetów przez grok
status: aktualne
---
# Linki JARO 2026-11-26 wieczór: DFly2, AMD na HF Kernel Hub, expert streaming, NVFP4 KV, YASA, gfx1170

**Nic z tych ośmiu nie przyspiesza dziś bezstratnie naszych modeli na XTX: DFly2 wymaga modelu z rzadką uwagą typu DeepSeek (DSA), YASA i NVFP4 KV są stratne, Megatron-LM jest otwarty od 2019. Zostają dwie lekcje do pracy: drafter czytający cache celu (stały koszt draftu przy każdej długości kontekstu) i pula slotów ekspertów z odczytem z wyprzedzeniem dla MoE na kartach 12–16 GB w Enigmie.**

| link | co to jest | liczby (warunki) | werdykt dla nas |
|---|---|---|---|
| Tencent DFly2 (tencentai_news, tencenthunyuan) | drafter blokowy, 3 warstwy; każda czyta latentny KV i top-k indeksera sparowanej warstwy celu, bez własnego KV ([arXiv 2611.34776](https://arxiv.org/abs/2611.34776), [AngelSpec](https://github.com/Tencent/AngelSpec)) | akceptacja +3,9…10,5% vs DSpark (ogólne), +10…31,5% (agentowe do 128k); DS-V4.1-Flash SWE 64k +81% przepustowości przy tej samej prędkości na użytkownika; Hy4 flash agentowo 3,41× vs DSpark 2,63×; H20, vLLM, tp8. „4,2×” z tweeta w papierze nie ma (najlepszy pojedynczy zbiór 4,55×) | tylko lekcja: Qwen3.8 (GDN + uwaga) i Inkling (SWA + pełna GQA) nie mają indeksera; Hy4 flash 220B/12B aktywnych, licencja z klauzulą MaaS |
| AMD na HF Kernel Hub (ariG23498) | 6 kerneli AITER przez bibliotekę `kernels` ([hf.co/amd/kernels](https://huggingface.co/amd/kernels)) | gfx1100 oznaczone w `aiter-kernels`, `aiter-flash-attn`, `aiter-rope`; AITER ocenia gfx1100 jako „Experimental”, buildy tylko gfx942/950 | dla llama.cpp nic (własne kernele HIP); ewentualnie Python/Torch; niski priorytet |
| HF Kernel Hub + expert streaming (lysandrejik) | [moe-expert-streaming](https://huggingface.co/blog/moe-expert-streaming): eksperci z dysku, pula slotów współdzielona przez warstwy, router 2 warstwy naprzód, 1 ekspert z wyprzedzeniem | A10G 24 GB, Qwen3.6-35B-A3B: Strata Q8_0 82–88 t/s, llama.cpp `--fit on` 63–64, vLLM offload 7–20; `--moe-cache-mib` w llama.cpp tnie graf (2 → 50 podziałów/token, −10%) | lekcja dla Enigmy (MoE na 12–16 GB); na XTX Inkling mieści się w VRAM; GGUF-w-transformers tylko Metal |
| YASA w Kolibri 1.1 (alessio__serra) | rzadka uwaga z dwustopniowym indeksem (bloki 16 → 2048 tokenów + 8 sink + 128 ostatnich), KV NVFP4 współdzielony ([blog](https://aleph-alpha.com/en/blog/sparse-attention-in-kolibri-1-1/)) | 14× dekod przy 1M względem Kolibri 1 (już SWA w 40/50 warstw), 4× B300; dotrenowanie 805 mld tokenów | stratne, wymaga treningu: lekcja |
| NVFP4 KV na Hopperze (yuvrajinfer) | kernel dekodu z KV 4-bit pod TMA i rdzenie tensorowe | H200: 67–75% pasma, 1,12–1,49× vs FP8, w vLLM 1,12–1,64× dekod, 1,63× więcej tokenów | KV 4-bit to zmiana liczb (nasza zasada: bez kwantyzacji dla prędkości); lekcja: źle napisany kernel 4-bit był 1,7× wolniejszy od FP8 |
| gfx1170/gfx1171 w vLLM (bebuu_ai) | nowe identyfikatory AMD w [commicie vLLM](https://github.com/vllm-project/vllm/commit/15c90d1a8dc0cc2cd2e045a13f9c521e92690ab5) | brak liczb | do obserwacji w karty/; nic do testu |
| Megatron-LM „właśnie otwarty” (crazyshyyt) | repo od 2019-03, [arXiv 1909.08053](https://arxiv.org/abs/1909.08053) | – | bzdura (stary projekt) |

## Co bierzemy
1. **Lekcja dla drafterów:** DFly2 pokazuje, że drafter może nie mieć własnego KV, tylko czytać cache celu. Nasz MTP Qwena już tak robi (jedna warstwa na stanie celu). Dla DFlash2/DSpark Inklinga koszt draftu rośnie z kontekstem; warto zmierzyć propose przy 2k/32k/96k, zanim cokolwiek budujemy (bez karty: z istniejących logów K158 bench, gdy będą przy różnych P).
2. **Enigma, MoE na mniejszych kartach:** pula slotów ekspertów + odczyt jednego eksperta z wyprzedzeniem. U nas K-026 pokazał, że spekulacja przy `--n-cpu-moe` traci 41–62%; Strata z offloadem jest szybsza od llama.cpp `--fit` o ~35% na A10G. Pozycja do kolejki NVIDIA, nie XTX.
3. **AITER na gfx1100:** test importu i czasu RoPE/norm tylko, jeśli kiedyś Maya przejdzie na ścieżkę Torch; dziś brak zastosowania.

## Na później (decyzja [[2026-11-26-wiedza-na-pozniej]])
- **Model z rzadką uwagą (DeepSeek-V4.x, GLM-5.3-Flash, Hy4 flash) w Enigmie albo na większych kartach:** DFly2 jako pierwszy kandydat na drafter (gotowe wagi w AngelSlim, vLLM/SGLang `method: dfly`); spodziewany zysk przy długim kontekście i zadaniach agentowych +12…31% względem DSpark.
- **Karty Hopper/Blackwell (wynajem, klienci Enigmy z H100/H200/B200):** KV NVFP4 z kernelem pod TMA jako opcja „więcej kontekstu na tej samej karcie” dla klienta, który zgodzi się na zmianę liczb; wtedy bramka KLD, nie md5.
- **MoE większe niż VRAM (Qwen3.6-35B-A3B, Inkling na 12–16 GB, przyszłe duże MoE):** pula slotów ekspertów + router 2 warstwy naprzód + 1 ekspert z wyprzedzeniem (wzór Strata/HF); u nas spekulacja przy offloadzie traci 41–62% (K-026), więc to droga do dobrego offloadu.
- **Własny trening albo dotrenowanie długiego kontekstu:** YASA (indeks dwustopniowy, KV współdzielony, inicjalizacja SVD) jako przepis na rzadką uwagę z istniejącego checkpointu, koszt ~¼ pretreningu.
- **Nowe karty AMD (gfx1170/1171, RDNA4-class macierze):** przy pojawieniu się — od razu wiersz w `karty/` i test naszych kerneli WMMA.
- **AITER:** gdy Maya albo produkt przejdzie na ścieżkę Torch na Radeonie, kernele RoPE/norm/flash-attn z HF Kernel Hub do porównania.

## Powiązane
- [[edycja-wag-a-z]]
- [[ZRODLA]]
