---
typ: ekosystem
tags: [ekosystem, vllm, serwowanie, testy, metryki]
aktualizacja: 2026-11-24
zrodlo: klon ~/research/engines/vllm @ 6c6e159 (2026-11-20); ~/KERNEL/product/research/03-silniki-i-stack.md:270-273,294; ~/KERNEL/product/research/15a-monokernel.md; ~/KERNEL/product/research/21f-inferencex.md:218-276; ~/KERNEL/wiki/ekosystem/inference-stack.md
status: aktualne
---
# vLLM jako wzór serwowania: czego uczy poza monokernelem i Kimi K3

**Cztery raporty (R03, R15a, R21b, R21f) czytały vLLM jako źródło kerneli albo wyników i żaden nie porównał go z naszą warstwą serwowania (topka llama-server, proxy Enigmy), choć to standard, na którym stoją inni (np. [[inference-stack]]): metryki cache według źródła, testy regresji akceptacji draftu, tolerancja remisów i spekulacja z sufiksów wbudowana w serwer.**

## Porównanie z naszym odpowiednikiem (klon `6c6e159`)

| warstwa | vLLM | my |
|---|---|---|
| metryki cache | tokeny z cache liczone według źródła: GPU, RAM hosta, P2P, dysk (`vllm/v1/metrics/cache_hit_source.py:10-24`), eksport Prometheus (`vllm/v1/metrics/prometheus.py`) | topka: log prefiksów i ręczne pomiary (E4); Enigma: brak `/metrics` ([[inference-stack]]) |
| regresja spekulacji | średnia długość akceptacji ≥ 95% wzorca na każdy zbiór (`tests/v1/e2e/spec_decode/acceptance_rates/utils.py:84-95`); DFlash2 na Qwen3.8-27B przypięty 6,14 (`…/acceptance_rates/dflash/test_dflash.py:44`) | md5 przy T=0 i KLD ([[bramka-kld-kanarki]]); długości akceptacji jako bramki regresji nie mamy |
| bezstratność przy remisach | `check_logprobs_close(near_tie_tol=…)`: token spoza top-k drugiej strony przechodzi, jeśli mieści się w tolerancji (`tests/models/utils.py:141-175`) | md5 albo KLD; remis w fabryce = NEEDS-HUMAN ([[fabryka-cli]]) |
| spekulacja z historii | metoda `suffix` w serwerze, z testami (`tests/v1/e2e/spec_decode/ngram_suffix/`) | lookup w kontekście jednego slotu; cache między sesjami: sprzeczne pomiary offline ([[suffixdecoding]]) |
| sprzęt | ROCm na gfx1100 produkcyjnie (KV 3-bit `ROCM_OCTAVE`, [[vllm-rocm-octave]]); bez natywnego Windows | llama.cpp HIP, Vulkan, CUDA, Windows |

## Wnioski
- Dla produktu Enigma vLLM nie zastąpi llama.cpp: brak Windows, ciężki stos, RDNA4 −23% wobec llama.cpp Vulkan (R03:270-273,294). Ale jego testy i metryki to gotowa lista tego, czego brakuje naszej warstwie serwowania.
- Bierzemy: (1) test regresji długości akceptacji MTP/DSpark na stałym zbiorze z progiem 95% wzorca, obok md5; (2) licznik tokenów z cache (i skąd) w metrykach topki i Enigmy; (3) jawną tolerancję remisów zamiast ręcznej oceny.
- Kernele: monokernel to reżim latencji klastrów MI355X ([[vllm-monokernel]]), Kimi K3 to reżim komunikacji 16×GB300 ([[vllm-kimi-k3-specialized-decode]]).

## Powiązane
- [[inference-stack]]
- [[vllm-monokernel]]
- [[vllm-kimi-k3-specialized-decode]]
- [[vllm-rocm-octave]]
- [[suffixdecoding]]
- [[qwen-warp]]
