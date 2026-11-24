---
typ: ekosystem
tags: [ekosystem, atencja, dlugi-kontekst, odrzucone]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63d-atencja-spec-kwant.md:9-19,67-167; https://github.com/Prefrontal-AI/latent-sparse-attention (`5ebea73`, 2026-11-04); arXiv 2610.42147 v2
status: aktualne
---
# Latent Sparse Attention (Prefrontal AI + ETH)

**Klucze bez RoPE rzutowane do 64 wymiarów, klastrowane metodą Warda w kubełki; zapytanie wybiera top-1024 kubełków. Nagłówkowe 72.4× (prefill jednej warstwy) i TTFT ~1/9 dotyczą 10M tokenów na 8×H200; przy 512k TTFT 1.03× (H200) i 0.68× (B300) (2026-11-05).**

- Baseline „pełna atencja” to Qwen ze stałym YaRN ×40 także przy 4k; mapę destylowano pod tę rotację. Na natywnym RoPE nikt jej nie mierzył.
- W tej samej tabeli block-sparse flat (styl QSA) wygrywa do 512k (1.61×).
- U nas atencja to 11.5% prefillu przy 32k i 51% przy 262k (model T(N) = aN + bN²); port 4–7 tygodni.
- **Odrzucone** ([[2026-11-05-tylko-bezstratne]]): rzadka atencja zmienia wyjście. Lekcja: „N× przy 10M” nie przenosi się na ≤ 262k.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Werdykt prędkościowy zostaje: przy ≤ 262k LSA nic nam nie da, a do tego jest stratna. Notatka pominęła jednak to, czego ta praca uczy o sposobie pracy (63d:116-125):
- **Kolejność pracy autorów:** najpierw zmierzyli, gdzie idzie czas (indekser to 98% przy 10M), potem wyrocznią top-k sprawdzili, czy rzadka atencja w ogóle wystarcza (k=512 trzyma 98% RULER przy 128k), a kernel napisali na końcu. Poniżej 256k zostawili zwykły GEMM + `topk`, bo specjalny kernel się nie opłacał. U nas ten sam porządek opisują [[lekcja-sufit-wzorca]] i [[physics-floor-check]]. Enigma Turbo poszła odwrotnie: najpierw kod, bramki nie było wcale ([[enigma-turbo-gemini-2026-11-20]]).
- **Odtwarzalność:** pełne konfiguracje, RULER odtwarzany deterministycznie z sumami kontrolnymi (0.974/0.968 wobec 0.975/0.966 w pracy), przedziały ufności przy każdym benchmarku i wariant PCA jako kontrola. Tak powinien wyglądać nasz rekord w [[REKORDY]].
- **Pułapka baseline'u:** „pełna atencja” chodziła ze stałym YaRN ×40 także przy 4k, czyli to inny model niż nasz serwer na natywnym RoPE. Przed każdym cudzym „N×” trzeba sprawdzić, czy baseline to ten sam model w tym samym ustawieniu ([[lekcja-baseline-wlasnego-silnika]]).
- **Uczciwość pomiaru:** harness kerneli mierzy w trybie `--time-only`, bez sprawdzania wyboru kluczy, i autorzy piszą o tym wprost. Liczba czasu bez bramki poprawności to tylko połowa wyniku.
- Tani test offline E4 (63d:425-430, mapa vs nasze Q4 przy 128k, 10 min GPU) dalej nie był robiony. Ma sens tylko wtedy, gdy wrócimy do rzadkiego prefillu.

## Powiązane
- [[qwen-qsa-llama-cpp]]
- [[strata-kva]]
- [[raport-63-synteza]]
- [[opoznienia-ttft]]
