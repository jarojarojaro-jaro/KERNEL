---
typ: model
tags: [modele, spekulacja, drafter]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/product/research/21a-dspine.md:13-38,39-77,307-321; ~/KERNEL/product/research/69a-dspine-27b.md:16-37,45-57,74-86,100-141,185-213; https://arxiv.org/abs/2609.36173; https://huggingface.co/tencent/Qwen3-8B-DSpine-b16; https://huggingface.co/tencent/Qwen3.8-27B-DSpine-b16; https://github.com/Ajay9o9/llama.cpp/tree/dspine
status: aktualne
---
# Drafter DSpine (Tencent YouTu): DFlash z przyczynowym kręgosłupem

**Drafter z rodziny DFlash (5 warstw, blok 16, K/V z cech 5 warstw celu) z przyczynową atencją w bloku, wiadomością z przewidywanej cechy poprzednika i wyborem tokenu warunkowanym poprzednikiem (arXiv 2609.36173v2); wersja 27B wyszła 2026-11-07, na XTX ma sens najwyżej jako drafter klasy „nowy kod” przy ctx ≤ 16k.**

## 8B (raport 21a, 2026-10-19)
- 1.24 mld parametrów BF16, plik 2.48 GB; trening ≤ 3072 tokenów, dane Open-PerfectBlend (1.42 M próbek, praktycznie tylko EN, ~42% matematyki) – brak PL i długiego kontekstu.
- τ Qwen3-8B przy tych samych danych (karta HF): T=0 7.83 vs DFlash2 7.55 (+3.7%), T=1 6.98 vs 6.53 (+6.9%); artykuł (ShareGPT) 4.82 vs 4.39 (+10%). Nagłówek „+27.8% nad DFlash” liczy od DFlasha przetrenowanego przez autorów (3.77) zamiast oficjalnego (5.92) – [[lekcja-naglowki-drafterow]].
- Przepustowość H100 +11.1% nad DFlash2 `[INFERENCE]`. Wtedy: tylko SGLang 0.5.20, port do forka 5–7 osobodni (nieaktualne od 69a, niżej). Ocena: [[raport-21a-dspine]].

## 27B (raport 69a, 2026-11-09)
- **Wydanie:** HF `tencent/Qwen3.8-27B-DSpine-b16` (`ea909c0`), 2.03 B parametrów BF16, warstwy celu [1,16,31,46,61]; **wszystkie 5 warstw SWA 8192** ⇒ KV draftu ~47 MB (q4_0) zamiast 1.18 GB z 21a. Dane 27B nieujawnione, kod treningu w SpecForge #1038.
- **Port llama.cpp:** Ajay9o9 `d493f84` = 1 commit, +323 linie, tylko graf (op-y istniejące, lattice DFlash2 z upstreamu); HIP nietestowany. U nas ~1–2 dni `[INFERENCE]` zamiast 5–7. Rozkładowo bezstratny.
- **Twierdzenia vs fakty:** „28.2 t/s” = AR **bez MTP** na 3090 (~31% wolniej niż nasze 40.93); „1.75× nad DFlash2” = 90.1/51.7 przy T=0, DFlash2 blok 8 na wolnej ścieżce MMQ; „3.3×” = SGLang przy c=8; „94–132 t/s” nie ma w źródłach. Krok DSpine na 3090 = 1.68× AR.
- **Model XTX:** krok 37.5–43.5 ms przy 2k ⇒ wymagane τ 1.39–1.62× MTP4. Per klasa (2k): en-code +9…+57%, pl-kod −14…+33%, en-tech −45…−15%, en-chat −48…−23%, pl-tech −58…−30%, pl-proza −67…−40%; mieszanka agentowa +0…+4%. Poza oknem 8192 τ spada (v1: −35% przy 13k).
- **Następny krok:** T1 (fork pod HIP, pobranie 1.26 GB), decyzja w [[raport-69-synteza]].

## Powiązane
- [[modele/_hub|Modele]]
- [[drafter-dflash]]
- [[glowica-mtp]]
- [[lekcja-drafter-gleboki-vs-mtp]]
- [[koszt-szerokosci-weryfikacji]]
- [[lekcja-akceptacja-h100-nie-przenosi-sie]]
