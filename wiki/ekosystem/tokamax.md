---
typ: ekosystem
tags: [ekosystem, jax, gdn]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/15-tokamax.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:25
status: aktualne
---
# openxla/tokamax

**Kernele Google/DeepMind w JAX + Pallas (HEAD `b500ee4`, 2026-10-14), kod inference tylko pod TPU; werdykt: niska.**

Ragged dot / MoE z wyrównanym startem kafli, swap-AB dla wag kwantyzowanych, maska rozkładana na `is_causal` + granice per wiersz. Repo nie podaje prawie żadnych liczb wydajności. Dla nas: conv1d w kernelu GDN (−48 kerneli/krok Qwena) oraz testy „5 tokenów naraz = 5 pojedynczych”.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Kod inference jest pod TPU, ale lekcje o testach i serwowaniu są ogólne.
- Akceptacja draftu jako kanarek: w ich RPA ze spekulacją błąd zapisu KV „po cichu kosztuje ~24 punkty akceptacji MTP” (`experimental/batched_rpa/kernel/kernel.py:267-277`, raport `qwen-opt/research/repos/15-tokamax.md:25,90`). Wyjście nadal jest poprawne, spada tylko prędkość. U nas topka i aplikacja działają z MTP, a `bench.ts` wypisuje akceptację (`app/engine/src/server/bench.ts:213-218`), ale nic nie alarmuje przy spadku. Bierzemy: alarm, gdy tok/krok spada > 3% przy tym samym ziarnie (P4d), w kolejce i w optymalizacji aplikacji.
- Autotuner: cache konfiguracji per urządzenie, klucz = pełna specyfikacja argumentów, heurystyka przy chybieniu, ostrzeżenie, że wybór konfiguracji zmienia numerykę (`15-…md:31`). To ten sam problem co przepisy w `app/engine/src/server/optimize.ts`; nasza wersja jest ostrzejsza (drugi pomiar zwycięzcy, próg szumu, md5 tekstu, `optimize.ts:1-20`).
- Testy „5 tokenów naraz = 5 pojedynczych” bitowo i testy dopełnienia szerokości (P4a, P4c) pasują do naszej weryfikacji spekulacji.

## Powiązane
- [[flashinfer]]
- [[vllm-xpu-kernels]]
- [[conv-lag]]
- [[repos-30-przeglad]]
