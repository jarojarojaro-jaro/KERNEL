---
typ: ekosystem
tags: [ekosystem, dlugi-kontekst, rtx-3090, kv]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/63a-silniki-lokalne.md:24-26,389-407,471-487; https://github.com/tuan3w/qwen-warp (`146a654`, 2026-11-05; `689901c` v0.8.0, 2026-11-07); ~/KERNEL/product/research/69b-tensorfold-qwen-warp.md:7-8,15-38,73-77; qwen-opt/cloud/nv69q/summary.txt (pomiar 2026-11-09)
status: aktualne
---
# qwen-warp (tuan3w): 262k na jednej RTX 3090

**Graf CUDA z fuzjami W4A16 (Swift-1.5 INT4), MTP k ≤ 3 + ogon prompt-lookup; decode 124 / 115 / 102 / 94 t/s przy 32k / 100k / 190k / 262k (2026-11-05).**

- Po przeskalowaniu pasma (×1.026) ~105 / 96 t/s wobec naszych 74.5 przy 199k: najmocniejszy dowód zapasu przy ≥ 100k.
- Lekcja z ich portu: atencja w weryfikacji była 15–20% wolniejsza przy 190k, bo dekwantyzowała ten sam kafel KV raz na kafel zapytań; naprawa = raz na grupę. To nasz otwarty punkt w [[fattn-kvq]] (dwa przejścia po KV przy 30 kolumnach).
- KV 4-bit z rotacją WHT i dokładnym pierścieniem fp16 (4 sinki + 256 ostatnich): tool-call 46 → 92–96%. Zmienia numerykę KV, więc u nas odrzucone ([[2026-11-05-tylko-bezstratne]]).
- Akcja bezstratna: jedno przejście KV na weryfikację, oczekiwane +5…15% przy 94–199k `[SZACUNEK]`.

## Delta v0.6.0 → v0.8.0 (`689901c`, 2026-11-07, raport 69b)
- **DFlash2 w silniku** (`incoai/Qwen3.8-27B-DFlash2`, W4A16, 1.15–1.4 GiB): cały cykl w jednym grafie CUDA, 21.0 ms (verify T=8 + accept 18.6 ms, drafter 2.50 ms), 4.48 tok/cykl wobec 2.98 dla MTP k=3. Serwer, KV bf16, 3090 350 W, zachłannie: kod 183.9 → 276.7 t/s (×1.51), czat ×1.34, 12 zadań ×1.07, proza ×0.96; **tury agenta z kopiowaniem −31%** (230 vs 334 t/s) – zgodne z [[lekcja-benchmark-kopia]]. KV draftera 20 KiB/token bez pierścienia: maks. ~125k, 262k na 24 GB się nie mieści.
- **Multiuser:** GEMV W4 z dwoma kaflami n8 (16 wierszy na przejście po wagach), 5 slotów: 154 / 278 / 425 / 441 t/s przy 1/2/4/8 klientach.
- Długi kontekst (94–133 t/s przy 32k–262k) bez zmian. Zasilanie: tylko limit 350 W, nic do przeniesienia.
- Dla Enigmy 3090: najmocniejszy publiczny punkt odniesienia.

## Pomiar na wynajętym 3090 (2026-11-09, [[2026-11-09-qwen-warp-vs-fork-3090]])
- Ta sama karta (350 W), te same 6 promptów, ten sam klient streamingowy, oba silniki przy 262 144. T=0 / T=1: 16k 114.0 / 121.0 wobec forka 76.8 / 66.7; 64k ×1.58 / ×1.59; 128k ×1.60 / ×1.65; 262k 68.3 / 68.6 wobec 51.1 / 45.1 (×1.34 / ×1.52). Kill (< ×1.15) nie zachodzi, temat portu zostaje.
- Około ×1.24 to lżejsze wagi (W4 g128 wobec UD-Q4_K_XL) `[SZACUNEK]`. Reszta to dokładne próbkowanie spekulacyjne przy T=1 (fork traci tam 7–13%, warp nie), GEMV W4 na rdzeniach tensorowych i cykl w jednym grafie.
- Deklaracje vendora na naszych promptach: „155 czat” to 117–128, a „94 przy 262k” to 68 t/s. Oba silniki mieszczą 262 144 na 24 GB.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- **To silnik pod jeden model, który się udał** — w przeciwieństwie do naszego Enigma Turbo (odłożony 20.11, długie prompty −41…−46% wobec topki, `wiki/log.md:560,580`). Na tej samej 3090 i tych samych promptach qwen-warp bije nasz fork ×1,34–1,65 ([[2026-11-09-qwen-warp-vs-fork-3090]]).
- **Co zrobili inaczej niż my w Turbo:** (1) cały cykl spekulacji w jednym grafie CUDA (21,0 ms na cykl DFlash2), (2) dokładne próbkowanie spekulacyjne przy T=1 (fork traci tam 7–13%, oni nie), (3) jakość mierzona jawnie: tool-call 46 → 92–96% z pierścieniem fp16 w KV — mierzą wpływ na zadanie, nie tylko t/s. Turbo zaczynał od kerneli, a przegrywał na długim kontekście i spekulacji.
- **Serwowanie:** 5 slotów, GEMV W4 z dwoma kaflami n8 → 154 / 278 / 425 / 441 t/s przy 1/2/4/8 klientach. Nasza topka ma jeden slot agenta i politykę cache (`CACHE_SHARE_MIN`); dla Enigmy przy kilku agentach naraz to gotowy punkt odniesienia, jak skaluje się serwer na jednej karcie.
- **Uczciwość deklaracji:** „155 czat” = 117–128 t/s na naszych promptach, „94 przy 262k” = 68 t/s. Ich README zawyża o 20–40%, ale kod i pomiar się bronią.
- **Co bierzemy:** wzór „cykl spekulacji w jednym grafie + dokładne próbkowanie T=1” do forka CUDA Enigmy; tabela jakości (tool-call) przy każdej zmianie KV; skalowanie wielu klientów jako test serwera Enigmy.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość): bramka testów
Główna różnica wobec Enigma Turbo to nie język ani kernele, tylko bramka. Enigma Turbo od Gemini miał testy tylko na syntetycznym modelu 256 × 4 i ogłaszał „ALL PASS” przy bełkocie ([[enigma-turbo-gemini-2026-11-20]]). qwen-warp (klon `d4bce14`, 2026-11-18) opisuje swoją w `docs/TESTING.md:35-75`, każdą zasadę z cytatem z llama.cpp albo vLLM:
- niezależna referencja w torch pisana z checkpointu, nie z kodu CUDA, w dwóch trybach: zdekwantowane wagi W4 (różnica = błąd kernela) i bf16 (różnica = jakość kwantu);
- tolerancje z pomiaru z zapasem, zapisane: GEMV W4 NMSE 8,6e-14, próg 1e-10 (próg 1e-6 przepuściłby błąd); NaN zawsze błąd;
- wyjście zatrute NaN i otoczone słowami-strażnikami: niezapisany kafel albo zapis poza zakresem wychodzi od razu; pierwszy drafter CUDA miał 4 prawdziwe błędy, które wyszły tylko tak;
- „bezstratne” = te same id aż do remisu dwóch najlepszych logitów celu (margines ≤ 0,3; zmierzone 7 przeskoków na 13 promptach przy 0,005–0,136), a błąd odbiega daleko od remisu;
- jakość draftu osobno: tokeny na cykl ≥ 85% wzorca na prompt i ≥ 95% średnio; to samo zapytanie dwa razy = te same bajty; plik wzorcowy z odciskiem checkpointu („wygeneruj ponownie” zamiast niejasnej porażki).
- **Proces:** zmiana +3,6% na angielskim kodzie nie weszła, bo na 13 promptach w 5 językach dała −1% (francuski 152 → 106 t/s); „bramka kampanii nie widziała straty, bo nie miała promptu po francusku ani po chińsku” (`CHANGELOG.md:57`). Ten sam błąd grozi nam, jeśli zestaw pomiaru nie ma polskiego.
- **Serwowanie:** profile `--profile long|multiuser` (`server/serve.py:5-6,49`) i głębokość draftu zależna od liczby równoległych zapytań `K_BY_B = {1–4: 3, 5: 2, 6–8: 1}` (`server/smk_batch.py:30`), bo B × (k + 1) ≤ 16 wierszy na przejście po wagach. Topka ma jedną głębokość MTP niezależnie od liczby rozmów.
- Bierzemy: referencję + zatrute wyjście + regułę remisu top-2 + próg akceptacji jako bramkę wejścia każdego nowego silnika lub kernela od agenta (Enigma Turbo, łatki Mai ik2), zanim trafi na kartę.

## Research 2026-11-26: skąd przewaga
- Bajty na token: warp ok. 13,25 GB vs nasz UD-Q4_K_XL 16,48 GB (×1,24 z ×1,31 na czacie to lżejszy kwant, jakość niezmierzona). Reszta i kopia 64k ×1,78 to kernel wag 92–96% pasma i tania szeroka weryfikacja: [[qwen-warp-dlaczego-szybszy-2026-11-26]], K-182.

## Powiązane
- [[fattn-kvq]]
- [[qwen-qsa-llama-cpp]]
- [[raport-63-synteza]]
- [[final-recipes-nvidia]]
