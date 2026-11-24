---
typ: ekosystem
tags: [ekosystem, vllm, v100, dlugi-kontekst]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66b-1cat-tokenspeed.md:7-52,74-129; https://github.com/1CatAI/1Cat-vLLM (c98a8d6, release v1.5.2)
status: aktualne
---
# 1Cat-vLLM (1Cat-LLM): fork vLLM pod V100

**„Flash-Next przy 250K tylko −18% względem 1K” to własność modelu (natywna rzadka QSA z budżetem 2048 tokenów) plus stratny host KV FP8, a nie trik kernela; ich gęsty 27B traci −47% (501 → 268 t/s), tyle co my −45% (136.5 → 74.5 przy 199k) (raport 66b, 2026-11-07).**

- Sprzęt: 4× V100-SXM2 32 GB, TP4. 27B: NVFP4 + DFlash2 (7 draftów), KV FP8 E4M3. Liczby z release'u liczone przy założonej akceptacji 70% ([[lekcja-tps-z-zalozonej-akceptacji]]).
- Efektywne pasmo przyrostu KV u nich i u nas ~200 GB/s (~20% szczytu), więc żaden nie stoi na pasmie `[SZACUNEK]`.
- Bezstratne dla nas: Pack-GQA48 (8 tokenów × 6 głów w jednym kaflu, KV czytane raz): operator −20…21%, runda −8.6% przy 128K; podziały 40 → 80 (1 → 2 CTA/SM): runda −10% przy 128K ([[kv-raz-na-weryfikacje]]).
- Cache prefiksu dla hybryd: siatka stanu GDN, junction learning, warstwa dyskowa ([[siatka-checkpointow-gdn]]).
- Wyniki negatywne: split-K po D w QK ±0.4%; adres liczony przez pół warpa i rozgłaszany shuffle −2.4…−3.5%; zwarte mapowanie ogona 2 głów −6.3…−7.0%; FP8 dekodowane inline w pętli 196 vs 107 µs; PV rozbite na 3 iloczyny wolniejsze.
- CPU KV offload dla gęstej atencji: 3.6 GB na krok przez PCIe ≈ 145 ms, odpada.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Wiersz w [[ZRODLA]] streszczał tylko kernele (QSA, Pack-GQA48). 1Cat to jednak ta sama strategia co nasza: fork znanego silnika pod jedną niszową kartę („Make Volta Fast Again” vs nasza topka pod gfx1100). Różnica jest w tym, co dostaje użytkownik (66b:15-52, 140-170):
- **Wydanie:** gotowy wheel, `docker/sm70_release/serve.sh` z flagami pod 27B i Flash-Next, 128 PR w release v1.5.2 i zmiana nazwy na 1Cat-LLM z obsługą GGUF, czyli fork stał się produktem. Nasz wyróżnik (silnik ROCm gfx1100) ma w Enigmie `distribution: local`, więc użytkownik AMD go nie dostaje ([[inference-stack]], punkt 4).
- **Uczciwy opis:** release ma listę znanych ograniczeń (edycja ostatnich 10% promptu = pełne przeliczenie, +3.3 ms próbkowania, maks. 8 żądań przy 256K) i tabelę t/s według zbioru danych (HumanEval 619, MT-Bench 386, chiński 215). Słabe jest tylko to, że nagłówkowe 501 t/s liczono przy założonej akceptacji 70% ([[lekcja-tps-z-zalozonej-akceptacji]]). Enigma pokazuje jedną liczbę t/s, bez listy ograniczeń.
- **Serwer dla hybryd (bezstratnie):** siatka stanu GDN, junction learning, migawka w dokładnej pozycji końca wiadomości wyliczonej z sond szablonu czatu i warstwa dyskowa przeżywająca restart ([[siatka-checkpointow-gdn]]). Topka ma checkpointy na wiadomościach użytkownika i `--cache-ram`, ale bez siatki i dysku. Enigma to aplikacja desktopowa, która się restartuje, więc dysk daje jej najwięcej (66b T5: tura po restarcie przy 50k ~55 s → ~2–4 s `[SZACUNEK]`).
- **Offload KV do RAM:** zapis write-through w trakcie liczenia na osobnym strumieniu, osobna pula na stan GDN i eksmisja LRU/ARC. Funkcjonalnie to nasze `--cache-ram`, ale z jawnie opisaną polityką.

## Powiązane
- [[tokenspeed]]
- [[kv-raz-na-weryfikacje]]
- [[qwen-qsa-llama-cpp]]
- [[qwen38-flash-next]]
- [[raport-66-synteza]]
