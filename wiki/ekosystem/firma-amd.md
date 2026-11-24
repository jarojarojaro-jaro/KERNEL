---
typ: ekosystem
tags: [ekosystem, producent-gpu]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/01-konkurencja.md:43,58; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:38-40; ~/KERNEL/product/research/13-rocm-10.1.md:26
status: aktualne
---
# AMD

**Producent naszej karty RX 7900 XTX i stosu ROCm; dla produktu raczej kanał dystrybucji niż konkurent.**

Rola w projekcie: sprzęt (RDNA3 gfx1100, RDNA4), sterownik amdgpu, ROCm/ROCr/HIP, profilery. Dla rynku: dołącza Ollamę i LM Studio do sterownika („AI Bundle”, 01.2026), prowadzi Lemonade z grupą roboczą „Auto-Tune” (nic nie wydano do 2026-10-15), ROCm CLI 0.2.0 z silnikiem Lemonade. Programy: $100 kredytu na MI300X w AMD Developer Cloud (30 dni), „Radeon Test Drive” (W7800, W7900, R9700) maks. 14 dni, bez użycia komercyjnego. PLAN zakłada rozmowę z AMD jako kanał.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): ROCm 10.2.0

ROCm 10.2.0 (2026-11-18) zamknęliśmy zdaniem „dla gfx1100 bez nowego GEMV ani FA”. Kernelowo to prawda (K-130 dalej sprawdza tylko kompilator). Wydanie pokazuje jednak, że AMD buduje to samo co Enigma, i zmienia dane wejściowe naszej aplikacji. (https://rocm.blogs.amd.com/ecosystems-and-partners/rocm-10.2-blog/README.html)
- **Konkurent i wzór produktu:** ROCm CLI 0.3.0 robi `rocm install sdk` i `rocm serve`, czyli „od czystej maszyny do działającego modelu”. Silniki to vLLM, Lemonade i AIM, a do tego nowy endpoint `/v1/messages` (API Anthropic z narzędziami i strumieniem). Proxy Enigmy przepuszcza tylko `/v1/*` OpenAI do llama-server (`app/engine/src/server/api.ts:104,156`). Klienci typu Claude Code mówią jednak `/v1/messages`.
- **InferaSim:** z kilku krótkich pomiarów na GPU szacuje na CPU, czy konfiguracja się zmieści i ile replik potrzeba na zadane opóźnienie. To dokładnie zadanie naszego katalogu i planera (`app/engine/src/server/catalog/memory.ts`) plus benchmarku Enigmy. Różnica: my mierzymy każdy wariant w całości.
- **Hyperloom:** agent AMD optymalizuje wdrożenie, teraz z budżetem mocy (cel = wydajność na wat, nie sam t/s). Wczesny dostęp na R9700. To kierunek naszej „optymalizacji u użytkownika” ([[produkt-optymalizacja-u-uzytkownika]]), a AMD robi ją dla własnych kart.
- **AMD Skills** (`npx skills add amd/skills`): skille dla agentów do pisania kerneli (FlyDSL) i portu CUDA → HIP. Ta sama forma co [[skill-io-przeglad]], a my nie wydajemy naszej wiedzy w tej formie.
- **Sprzęt klientów:** 18 nowych procesorów Ryzen na gfx1103 (Radeon 700M) z oficjalnym HIP, PyTorch i vLLM na Windows i Linux. Enigma zakłada, że oficjalne buildy ROCm nie mają kerneli dla starszych APU (`app/engine/src/server/hw/common.ts:21-31`), a wydajemy upstream na ROCm 10.0 (`data/engines.json:57-73`). Ta reguła się zestarzeje, gdy llama.cpp wyda build ROCm 10.2 z gfx1103.
- **vLLM i SGLang na Radeonach w oficjalnych obrazach, AITER bez ręcznej instalacji** (kernele kompilują się przy pierwszym użyciu, czyli pierwsze żądanie jest wolne). Stos typu Inference Stack ([[inference-stack]], dotąd tylko NVIDIA) da się wtedy złożyć na XTX bez własnych łatek [INFERENCE: blog pisze „Radeon”, listy kart nie sprawdzałem]. To punkt odniesienia dla topki przy wielu użytkownikach.
- Szum: „2,2× na Qwen3.8-27B przy wielu równoległych zapytaniach” (X, 2026-11-21) nie podaje bazy, karty ani silnika.

## Powiązane
- [[firma-nvidia]]
- [[lemonade]]
- [[rx-7900-xtx]]
- [[amd-dev-cloud]]
