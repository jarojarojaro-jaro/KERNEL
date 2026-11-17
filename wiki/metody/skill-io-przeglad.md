---
typ: metoda
tags: [metody, hill-climb, sufit, skill-io, nauka]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e (github.com/sybil-solutions/inference-optimisation-skill, MIT; Telegram „gpu” 2026-11-17) — README.md:1-151, PROMPT.md:1-94, skills/inference-optimisation/SKILL.md:1-166, references/*.md, scripts/*, examples/*.json; wszystkie 17 plików przeczytane w całości
status: aktualne
---
# Skill „inference-optimisation” (Sybil Solutions): wspinaczka po prędkości serwera LLM — przegląd i lekcje

**Agentowy przepis na strojenie serwera LLM na dowolnym sprzęcie. Sześć kroków: policz sufit, zmieniaj jedną rzecz, mierz między kontrolami, loguj także porażki, bramkuj igłami w długim kontekście, publikuj z czystego przypiętego buildu (`README.md:13-20`). Robimy to samo od miesiąca. Najcenniejsze dla nas są sufity jako stała kolumna raportu oraz bramki, których nie mamy: igły, round trip narzędzi, flaga pętli.**

**Ich wyniki** (`README.md:28-36`):
- B390 iGPU, MoE 35B-A3B: 43,6 → 53 t/s, czyli ~55% sufitu.
- B70, Qwen3.8-27B EXL3 4 bpw na vLLM z własnymi kernelami: 91,2 t/s.
- **3090, Qwen3.8-27B EXL3 3 bpw + MTP: 96,2 proza / 141,1 kod.** Nasz fork na 3090: 80,0 (Q4_K_XL, T=1, inny harness).
- **XTX:** produkcja 119–134 t/s.

**Procedura** (`SKILL.md:38-150`):
- **Inwentarz i własne pomiary pasma i FLOPS** (`:45-51`). Pasmo mamy (926 GB/s); FLOPS nie, to K-108.
- **Katalog roboczy** PLAN, THEORY, ledger, configs, best (`:53-58`). U nas to samo: wiki eksperymenty + REKORDY + kolejka.
- **Sufity:** [[skill-io-sufity]].
- **10 zasad twardych:** [[skill-io-metodyka]].
- **Pętla:** profil → dźwignia o największym (luka do sufitu × prawdopodobieństwo) → config → A/B z kontrolami (`:106-110`).
- **Kolejność dźwigni:** [[skill-io-dzwignie]].
- **Plateau = 3 dźwignie z rzędu w szumie** (`:142-150`). Wtedy sekcja STATUS z rankingiem pozostałych dźwigni.
- **Publikacja:** [[skill-io-publikacja]]. **Pułapki:** [[skill-io-pulapki]]. **Skrypty:** [[skill-io-skrypty]].

**Najważniejsze lekcje dla nas:**
1. **Liczymy sufit przed każdą dźwignią.** Dla naszej produkcji: dekod czatu 167 t/s przy 2k, mierzymy 119–127, czyli 71–77%. Krok MTP: sufit 19,2 ms, mierzymy 26,9. Prefill przy 128k jest na 93% (486 z 521).
   - **Wniosek:** zapas leży w dekodzie (czas kroku), nie w prefillu i nie w akceptacji draftu.
2. **Spekulacja to koszt kroku, nie akceptacja** (`README.md:138-141`). U nas wyższa akceptacja DRAFT_N=5 nie dała t/s, a lookup W16 jest neutralny (K-002). Zgodne.
3. **Bramka igieł 50% / 100% kontekstu** jako warunek „najlepsze”. Nie mamy jej, a fill 255k z md5 nie dowodzi, że model czyta cały kontekst (K-109).
4. **Flaga pętli** w harnessie: ich „rekord 117 t/s” był pętlą. U nas MMLU-Pro zapętlił się do 32 768 tok. i znaleźliśmy to ręcznie.
5. **Porównanie silników tylko z bootstrapowym CI** (`methodology.md:23`). Przyjmujemy do K-110 i przyszłych porównań Enigmy.
6. **Sufit pamięci:** zostawiać ≥ 1,5 GB. Mamy ~1,1 GiB przy 262k. Ryzyko znane, soak przeszedł.
7. **Nie mierzyć wymyślonych dźwigni bez sufitu:** po K-003 i K-104 (0 ms) widać, że liczyć trzeba najpierw.

**Testy w kolejce** ([[KOLEJKA-TESTOW]]):
- K-108: zmierzyć szczyt FLOPS i kopię.
- K-109: bramka igieł.
- K-110: ich `bench.py` na XTX 1:1.
- K-111: rozkład luki kroku 26,9 vs 19,2 ms na kernele.

**Zakres: AMD i NVIDIA (właściciel 2026-11-17).** Wszystkie notatki skill-io mają sekcję dla obu firm:
- sufity 18 kart (RDNA2/3/4, CDNA2/3/4, Ampere, Ada, Blackwell, Hopper): [[skill-io-sufity]];
- dźwignie per architektura: [[skill-io-dzwignie]];
- pułapki per firma: [[skill-io-pulapki]];
- narzędzia pomiaru ROCm i CUDA: [[skill-io-metodyka]];
- przypinanie: [[skill-io-publikacja]].

**Kluczowa liczba:** XTX jest na 69–71% sufitu dekodu, karty NVIDIA z naszym forkiem na 41–59%. Tam leży największy zapas. Testy NVIDIA w kolejce: K-112…K-115.

## Powiązane
- [[metody/_hub|metody]]
- [[mapa-inferencji-roadmap]]
- [[REKORDY]]
- [[sufit-pasma-i-mapa-czasu]]
- [[KOLEJKA-TESTOW]]
