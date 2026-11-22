---
typ: model
tags: [modele, looped, architektura, enigma, telegram]
aktualizacja: 2026-11-17
zrodlo: https://x.com/SenseTime_AI/status/2122702684985938356 (Telegram „gpu”, 2026-11-17); github.com/OpenSenseNova/SenseNova-Loop README (2026-11-17); huggingface.co/sensenova/SenseNova-Loop-9B (gated, safetensors 18,83 GB); llama.cpp issue #31571 (otwarte); huggingface.co/AtomicChat/SenseNova-Loop-9B-Preview-GGUF README; arXiv 2611.19896 (LoopSkim)
status: aktualne
---
# SenseNova-Loop-9B: model z pętlą warstw — pamięć jak 9B, pasmo jak ~14B, jakość wg producenta blisko Qwen3.8-27B

**Model z prawdziwej firmy, z prawdziwymi wagami (Apache-2.0), ale jakość to na razie tylko tabela producenta. Dla nas najważniejsze są dwie rzeczy. Pętla zmienia liczenie sufitu: bajty na token liczymy z wykonań warstw, nie z rozmiaru pliku. Model jest też kandydatem do Enigmy na karty 8–16 GB, ale upstream llama.cpp go jeszcze nie obsługuje.**

**Mechanizm** (README):
- 32 fizyczne warstwy; warstwy 4–27 wykonują się dwa razy, B(B(h)), co daje 56 wykonań na token.
- Producent podaje „~14,6B parametrów efektywnych przy inferencji”.
- Atencja hybrydowa jak w Qwen3.5/3.8: w każdej czwórce 3 warstwy liniowe i 1 pełna.
- mHC: dwa strumienie resztkowe mieszane macierzą normalizowaną Sinkhornem (20 iteracji), routing w FP32.
- Wymiary: hidden 4096, FFN 12 288, słownik 248 320 (ten sam co Qwen3.8), 16/4 głowy pełnej atencji, kontekst 512K, wejście tekst + obraz.

**Jakość** (producent, bez niezależnego pomiaru):

| test | Loop-9B | Qwen3.8-27B |
|---|---|---|
| NL2Repo | 41,36 | 44,60 |
| AIDABench | 65,31 | 65,01 |
| AutomationBench | 36,67 | 36,67 |

Względem wersji Preview: GAIA 37,86 → 69,90, Terminal-Bench 2.1 40,45 → 59,55. Skalowanie pętli przy tych samych danych: 3–4 przejścia dają +6,4…16,9% względnie nad 1 przejściem. Domyślnie 2 przejścia, dla szybkości.

**Sufit dekodu u nas** (metoda [[skill-io-sufity]]):
- Bajty na token (Q4_K_M, [INFERENCE]): warstwa ~0,2 mld parametrów × 4,9 bpw ≈ 0,12 GB; 56 wykonań to ~6,9 GB, głowica Q6_K ~0,83 GB, razem **~7,7 GB/token**. Plik waży ~5,3 GB, a Qwen3.8-27B czyta 16,1 GB/token.
- Sufit bez spekulacji (Loop-9B / Qwen3.8-27B, t/s): XTX 120 / 57, 3090 122 / 58, 4090 131 / 62, 5060 Ti 58 / 28, 3060 47 / 22, M4 Max 71 / 34, B580 59 / 28. Około **2,1 × szybciej niż 27B**, a nie 3 ×, jak sugeruje liczba parametrów.
- Infinity Cache (96 MB) i L2 nie pomogą przy drugim przejściu: blok pętli to ~2,9 GB, a przejścia idą po sobie dla każdego tokenu.
- KV i stan też liczą się per wykonanie [INFERENCE]: ~14 instancji KV pełnej atencji (8 fizycznych warstw) i ~42 stany GDN. Zgadza się to z tabelą producenta: 256K przy KV 8-bit to ~15 GiB.

**Lekcje:**
1. `ceiling.py` i `karty.py` zakładają, że każda warstwa jest czytana raz. Dla modeli z pętlą (SenseNova-Loop, Ouro, Raven) trzeba pomnożyć bajty bloku przez liczbę przejść, a KV i stan przez liczbę wykonań. Inaczej sufit wychodzi 1,6 × za wysoki.
2. **Pętla daje darmowego draftera:** odczyt po pierwszym przejściu przewiduje następny token. LoopSkim (arXiv 2611.19896) weryfikuje drafty na kolejnych głębokościach bez osobnej głowicy, bezstratnie także przy próbkowaniu; ×1,73 względem LoopSpec. Dla nas: przy modelu z pętlą spekulacja bez MTP, dokładając lookup, który już mamy.
3. Trening (filar `llm/`): więcej obliczeń przy tej samej liczbie parametrów to oś skalowania niezależna od rozmiaru wag. Przy bandwidth-bound dekodzie płaci się jednak bajtami, nie FLOPami.

**Stan wsparcia:**
- llama.cpp: brak; feature request #31571 otwarty od 2026-11-03.
- GGUF wersji Preview istnieją tylko dla łatanego buildu (AtomicChat, baza `5047748f11`, „upstream PR pending”), bez wizji.
- SGLang: PR #47281. LightLLM: tak.
- Oficjalne AWQ 4-bit: ~4,9 GB.

**Co dalej:** właściciel (2026-11-17): model nie jest do optymalizacji, tylko do pobrania i sprawdzenia, jak naprawdę działa. Plan: K-119 w [[KOLEJKA-TESTOW]] (AWQ 4-bit w SGLang/vLLM na wynajętej karcie albo GGUF z llama.cpp, gdy będzie obsługa; ręczny panel + jakość-mini + EvalPlus). Zmiana modelu w produkcji lub w Enigmie to decyzja właściciela.

## Powiązane
- [[trening-llm-mapa]]
- [[mapa-inferencji-roadmap]]
- [[skill-io-sufity]]
- [[zwiad-2026-11-17]]
- [[final-recipes-nvidia]]
