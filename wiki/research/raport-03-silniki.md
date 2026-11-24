---
typ: research
tags: [research, silniki, stack]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/03-silniki-i-stack.md:19-43
status: aktualne
---
# Raport 03: silniki inferencji i stack

**Bazą zostaje llama.cpp jako cienki overlay łatek, nie twardy fork; rdzeń w Rust, GUI w Tauri 2, daemon z API OpenAI na 127.0.0.1.**

- Upstream wydaje ok. 24 buildy dziennie, od 2026-10-15 ma linię semver (v0.7.0). Nasz fork: 70 commitów, 69 plików, +11 401/−803 linii; w 6 dni upstream zmienił 33 z tych 69 plików.
- Własne runtime'y (Strata, TensorFold, hipfire) dają rekordy tylko dla wąskiego zestawu modeli; ik_llama.cpp traci pokrycie sprzętu.
- Polityka AI llama.cpp zakazuje automatycznych PR-ów; upstreamujemy ręcznie i selektywnie.
- Żaden silnik spoza ggml nie pokrywa NVIDIA + AMD + Intel + Apple jednym binarium; drugi backend tylko MLX na Macu (+21–87% decode).
- Dystrybucja: Vulkan 31 MB, CUDA 147–254 MB + 373–404 MB DLL, ROCm 183–654 MB na rodzinę gfx; Lemonade 10 MB z dociąganiem backendów.
- Code signing: Azure Artifact Signing od $9.99/mies. tylko dla firm z UE → potrzebna spółka; Apple $99/rok.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Wiersz w [[ZRODLA]] streszczał R03 jako „bazą zostaje llama.cpp; żaden nie bije na AMD”, a R03 był też raportem o produkcie:
- **Wzięte do Enigmy:** API tylko na 127.0.0.1 ze strażnikiem Host/Origin przeciw DNS rebinding (R03:40 → `app/engine/src/server/api.ts:28-41`); llama-server jako osobny proces potomny (R03:39). **Niewzięte:** podpisana aktualizacja (R03:39, minisign w updaterze Tauri) i mały instalator z dociąganiem silnika (R03:38, Lemonade 10 MB).
- **Przestroga, której nie posłuchaliśmy:** 10-16 R03 zapisał „własne runtime'y dają rekordy tylko dla wąskiego zestawu modeli”, a 11-20 Enigma Turbo (własny silnik od zera, Gemini) dał bełkot przy 0,7 t/s ([[enigma-turbo-gemini-2026-11-20]]). Wniosek był w raporcie, ale nie stał się regułą przy decyzji o nowym silniku. Silniki jednego modelu, które się udały (qwen-warp, Maya), mają bramkę testów i rozszerzają sprawdzoną bazę ([[qwen-warp]], [[project-maya]]).
- **Rywale aplikacji, nie silniki:** Lemonade (AMD: wykrywa sprzęt, pobiera llama.cpp ROCm per rodzina gfx, API OpenAI/Anthropic/Ollama, nocne pomiary regresji forków, [[lemonade]]), LM Studio, Jan, Ollama, KoboldCpp, llamafile. Kolejne podejście powinno porównywać ich pierwsze uruchomienie, wybór modelu, aktualizację i zachowanie przy awarii z Enigmą, nie tylko t/s.
- Drugie podejście do silników (2026-11-20, 20 klonów w `~/research/engines`): [[silniki-inferencji-2026-11-20]].

## Powiązane
- [[research/_hub|research]]
- [[raport-08-platforma]]
- [[strata]]
- [[ik-llama-cpp]]
- [[produkt-stack]]
