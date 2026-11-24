---
typ: ekosystem
tags: [ekosystem, apple, mlx, gdn, gramatyka]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60b-apple-engines-bonsai.md:3.3; ~/qwen-opt/research/Locals (c0f9baa) README.md:66-74,120-128,175-188; docs/why-faster/README.md:31-41,103-108; docs/runtime/README.md:107-127; https://arxiv.org/abs/2610.09139
status: aktualne
---
# Locals (Generated-Computers/Locals)

**Serwer MLX dla agentów; „przełom w złożoności” dotyczy automatów gramatyki, nie DeltaNet, a kernel GDN to jeden launch na krok wart 1–2% – na nasze kernele HIP nic nie przenosi (raport 60b).**

- Praca arXiv 2610.09139 (Asadulaev): osiągalność w grafach o niewielu ścieżkach w O(log² n / log log n) pamięci; w silniku: tokeny wymuszone bez modelu, maska na GPU (3 MB zamiast do 1.5 GB), 16 agentów z narzędziami 2.5× szybciej niż mlx-lm + llguidance.
- GDN: `gdn_kernel.py` = conv + norma q/k + rekurencja + gated norm w jednym kernelu Metal (S ≤ 16, stany per token do cofania draftu); ablacja 267.6 → 272.7 tok/s (+1.9%).
- Źródło 3× (M2 Pro, Qwen3.5-4B, 8 żądań 87 → 271 tok/s): kernele 4-bit pod 2–16 wierszy, fp16 na M1/M2, fuzja projekcji, pipelining.
- Nie szybszy: jedno żądanie (64 vs 61 tok/s), prompty, formaty poza affine 4-bit g64, M5.
- Apache-2.0; compwatch (C).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

Werdykt „przełom dotyczy gramatyki, nie DeltaNet; GDN 1 launch już mamy” był prawdziwy dla kernela, ale pominął, czym Locals jest: serwerem dla wielu agentów naraz. To warstwa, której topka nie ma.
- **Zysk siedzi w wielu żądaniach, nie w jednym.** Jedno żądanie: 64 vs 61 tok/s, czyli nic. 8 żądań: 87 → 271 tok/s (M2 Pro, Qwen3.5-4B) dzięki kernelom 4-bit pod 2–16 wierszy, fuzji projekcji i pipeliningowi (raport 60b). U nas `-np 2` na XTX dał pojedynczemu żądaniu −5…−17%, a ścianie fan-outu omp +11% (K-086, KILL, [[wyniki-negatywne]]). Topka jest strojona pod jeden strumień (MMVQ N=1, weryfikacja N=5), a każdy slot to ~2,4 GB stanu. Locals pokazuje, że rój agentów wymaga kerneli i serwera projektowanych pod kilka strumieni, a nie dołożenia slotów.
- **Gramatyka jako przyspieszenie, nie tylko format.** Tokeny wymuszone przez gramatykę (stała struktura JSON wywołania narzędzia) są dopisywane bez modelu, a maska liczona jest na GPU (3 MB zamiast do 1,5 GB). 16 agentów z narzędziami działało 2,5 × szybciej niż mlx-lm + llguidance. U nas wywołania narzędzi idą zwykłym dekodem, każdy token przez model [INFERENCE: gramatyki dla narzędzi w topce nie znalazłem].
- **Związek z poprawnością agenta:** gramatyka daje też wywołania, które zawsze się parsują. To ta sama potrzeba, którą Speedy załatwia naprawą wywołań ([[speedy]]).
- **Bierzemy:** przy ponownym otwarciu K-086 najpierw rozłożyć, skąd −5…−17% pojedynczego żądania przy `-np 2` (spekulacja na slot, atencja, stan GDN), bo sam odczyt wag dla 2 sesji to ten sam kształt co weryfikacja N=5. Gramatykę z tokenami wymuszonymi zapisujemy jako kandydata dla proxy Enigmy i serwera agentów.

## Powiązane
- [[omlx]]
- [[gdn-replay]]
- [[raport-60b-apple-bonsai]]
