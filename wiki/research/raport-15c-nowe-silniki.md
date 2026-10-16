---
typ: research
tags: [research, konkurencja, silniki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15c-nowe-silniki.md:1-45,225-254,374-396
status: do-sprawdzenia
---
# Raport 15c: nowe silniki konkurencji (Magnitude, tqLLM, Actual, TensorFold 1.0.12)

**Strojenie kerneli na komputerze użytkownika przestało być unikalne (Magnitude), a „spekulacja nie zmienia odpowiedzi” robią już tqLLM, Actual i TensorFold; unikalne zostaje AMD natywnie, dowolny GGUF, przed → po wobec tuned upstream i opublikowana bramka md5/KLD.**

Raport 2026-10-16, kod czytany statycznie, bez GPU; liczby konkurencji do sprawdzenia.
- **Magnitude:** własny silnik Rust („Seismic”, Metal/CUDA/Vulkan, bez HIP), autotune 60 s przy pierwszym załadowaniu z bramką α = 8 kroków zaokrąglenia (nie bitową), KV K8V4; „2.19× vs Ollama” zmierzone na kopiowaniu przy 64k; bez spekulacji vs llama.cpp +19% decode (CUDA, Spark).
- **tqLLM:** 273.1 t/s na 3090 w LocalMaxxing przy T=0, 320 tokenach, mal 6.15, z prywatnego buildu; plain per bajt jak my (77% pasma).
- **Actual „e”:** host w asemblerze AArch64 + 86 cubinów sm_103a, tylko DGX Station; 455 / 8,046 t/s z własnego benchu; konsumencko vendored llama.cpp albo „malibu”.
- **TensorFold 1.0.12:** LFM2.5 tylko na Metal (M5 Ultra 261.5 t/s = 30% pasma vs nasz XTX 293.7 = 54%); twins, Recall, TP ekspertów; HIP preview słaby.
- Najtańsze działania: (a) wpisy do LocalMaxxing (XTX nie ma żadnego verified runu Qwen3.8-27B) i raportowanie dwóch klas obciążenia (kopia i nie-kopia); (b) spec-copy / n-gram z wyceną kosztu okna; (c) batch-invariant verify.
- Plan X1: Magnitude vs nasz fork na 3090 i 5060 Ti (~$1.5–2, kill: Magnitude ≥ fork −5% na nie-kopii).
- PLAN §0.1: tezę „żaden nie robi naraz” trzeba zawęzić – zob. notatkę do decyzji.

## Powiązane
- [[research/_hub|research]]
- [[magnitude]]
- [[tqllm]]
- [[actual-computer]]
- [[tensorfold]]
- [[zawezenie-tezy-produktu]]
