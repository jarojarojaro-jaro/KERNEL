---
typ: research
tags: [research, zrodla, nauka]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:31-71,305-340
status: aktualne
---
# Lista wafer-ai „gpu-perf-engineering-resources”: ocena

**Dobry spis lektur, ale nie przepis na nasz problem: 5 z 6 działów dotyczy serwerów z dużym batchem, Hoppera/B200 i rozproszenia (NVLink, DeepEP, EPLB, disaggregation), dział AMD to tylko CDNA/Instinct, a o RDNA3, batch 1 na kartach konsumenckich i skwantyzowanym GEMV nie ma nic (raport 21b, 2026-10-19).**

Blackwell Tuning Guide v13.4 dotyczy B200/GB200 (HBM3, L2 126 MB, NVLink 5); dla sm_120 podaje tylko limity (48 warpów/SM, 128 KB shared/SM, 99 KB na blok, 32 bloki/SM). Opis z listy („Tensor memory, Blackwell execution features”) nie zgadza się z treścią – o tensor memory przewodnik milczy, a sm_120 jej nie ma ([[sm-86-89-120]]). Kolejność lektur dla zespołu: raport 21b §6.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Ocena „o RDNA3 nic” była trafna dla kerneli, ale raport 21b odrzucił jako „pomijalne” dział 4–5: Orca, vLLM, Sarathi, SGLang, DistServe, Mooncake, Dynamo, llm-d (`product/research/21b-gpu-perf-zasoby.md:47-48,337`). To lektury o serwowaniu, a serwowanie to nasza topka i aplikacja Enigma.
- Przykład kosztu: router llm-d wybiera replikę po trafieniu w cache prefiksu (waga 3, [[inference-stack]]). To ten sam problem co nasza polityka slotów: obce zapytanie wyrzucało cache agenta, poprawka `LLAMA_SERVER_CACHE_SHARE_MIN=1024` dała Qwen 8,0 → 1,6 s. Lektura z listy dałaby nam nazwę i wzorzec wcześniej.
- Dla zespołu i nauki: sekcja „Start here” (kipply, scaling-book, roofline) i dział 2 mają wysoką wartość niezależnie od sprzętu; „Frontier” (KernelBench-Verified, KernelGuard) zasila naszą fabrykę.
- Bierzemy do kolejności czytania: Orca (planowanie na poziomie iteracji), Sarathi (dzielenie prefillu), SGLang RadixAttention (cache prefiksu), llm-d (routing po prefiksie), standard metryk serwowania (TTFT, opóźnienie między tokenami, kolejka).

## Powiązane
- [[research/_hub|research]]
- [[raport-21b-gpu-perf-zasoby]]
- [[repos-30-przeglad]]
