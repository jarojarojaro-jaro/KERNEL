---
typ: research
tags: [research, silniki, stack]
aktualizacja: 2026-10-16
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

## Powiązane
- [[research/_hub|research]]
- [[raport-08-platforma]]
- [[strata]]
- [[ik-llama-cpp]]
- [[produkt-stack]]
