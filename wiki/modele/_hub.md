---
typ: hub
tags: [modele, hub]
aktualizacja: 2026-11-22
zrodlo: wiki/tools/wiki.py index
status: aktualne
streszczono: 2026-11-22
---
# Modele

**Modele, które uruchamiamy lub rozważamy: architektura, kwanty, KV, najlepsze zmierzone t/s, licencja.**

<!-- Jarvo:STRESZCZENIE -->
Produkcja na XTX: [[qwen3-8-27b-uncensored]] Q4_K_M ze spekulacją MTP (REKORDY: dekod MTP 1,7k 133,9 t/s, 2026-11-14; tg128 bez spekulacji 43,2 t/s). Najszybszy model na XTX: [[lfm2-5-24b-a2b]] (copy 288,2 t/s, raport 24d). W toku: [[inkling-2-mini]] (MoE z pętlą; XTX 26,9 → 49,5 t/s bez spekulacji po rundach duetu, DSpark 85 t/s kopie; K-133, K-134). Dla kart 8–12 GB: [[qwen3-5-9b]], [[bonsai]]. Najlepszy wynik każdego modelu na każdej karcie: [[najlepsze-wyniki]]; blok „Wyniki z notatek” w notatce modelu składa się sam z pól.
<!-- /Jarvo:STRESZCZENIE -->

Liczby t/s zawsze z datą i warunkami (kwant, KV, MTP/DFlash, prompt, T). Aktualny stan instalacji: [[stan-2026-10-15]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (30)

- [[astra-stop|Astra-Stop: rank-1 edycja, która skraca myślenie Qwen3.8-27B]] — Jedna macierz `layers.63.mlp.down_proj` zmieniona wzorem `W' = (I + u uᵀ)W` (u = odczyt tokena `</think>` przez głowicę LM, cos 0.9998 na naszym GGUF): mediana myślenia −35.5% przy effort xhigh, ale `</think>` przecieka do odpowiedzi w 11/32 – to zmiana zachowania, nie bezstratna optymalizacja (2026-11-09).
- [[daisyrose-27b|DaisyRose-27B (RadixArk): pełny RL na Qwen3.8-27B, 144 × H200 przez 18 dni — duży koszt, mały zysk poza Terminal-Bench 4.1]] — RadixArk (twórcy DSpark) wytrenował nasz model bazowy samym RL-em (bez SFT i destylacji) na ~1200 długich zadaniach agentowych, z sesjami do 1M tokenów. Koszt to 144 H200 × 18 dni ≈ 62 tys. GPU-godzin. Zysk: Terminal-Bench 4.1 5,6 → 12,0%, na pozostałych testach +0,4…+4 pp. Ta sama architektura i ten sam szablon, więc zastępuje Qwen3.8-27B bez zmian; GGUF Q4_K_M działa w naszym silniku bez łatek [INFERENCE: ten sam typ `qwen35`].
- [[drafter-dflash|Drafter DFlash2 dla Qwen3.8-27B]] — Osobny mały model draftujący (z-lab / incoai, 5 warstw) — świetny na angielski kod przy T=0, ale na szerszym zestawie i po polsku nie bije głowicy MTP, więc domyślnie używamy MTP.
- [[drafter-dspine|Drafter DSpine (Tencent YouTu): DFlash z przyczynowym kręgosłupem]] — Drafter z rodziny DFlash (5 warstw, blok 16, K/V z cech 5 warstw celu) z przyczynową atencją w bloku, wiadomością z przewidywanej cechy poprzednika i wyborem tokenu warunkowanym poprzednikiem (arXiv 2609.36173v2); wersja 27B wyszła 2026-11-07, na XTX ma sens najwyżej jako drafter klasy „nowy kod” przy ctx ≤ 16k.
- [[gemma-4|Gemma 4 (26B-A4B, 31B, 12B)]] — Gemma 4 ma iSWA (okno 1024: 25/30 warstw SWA w 26B, 50/60 w 31B, 40/48 w 12B), co fitcalc v2 uwzględnia; w raporcie 33 nie wygrała żadnej klasy kart.
- [[gyro-coder|Gyro-Coder (Qwen3.8-Flash-Next, 256/512 ekspertów) i format Gyro TQ]] — AgentionAI przyciął Flash-Next do 256 z 512 ekspertów w każdej warstwie, zapisał ich w trellisie TQ2_T (2.125 bpw) i zmieścił model w 19.92 GiB GPU. Do tego dochodzi 50.7 GiB tabeli n-gramów na NVMe.
- [[glowica-mtp|Głowica MTP Qwen3.8-27B (spekulacja bez osobnego draftera)]] — Wbudowana warstwa `blk.64` (nextn) zgaduje kolejne tokeny, a główny model weryfikuje je jednym przebiegiem; to podstawa naszego 109 t/s, z ~3 tokenami na krok.
- [[inkling-2-mini|Inkling 2 Mini (Thinking Machines, 2026-11-20): MoE z pętlą warstw, jakość jak Qwen3.8-27B przy ~5× mniejszym odczycie na token]] — Prawdziwy i ważny dla nas: według producenta jakość Qwen3.8-27B (AA Index 20,1 vs 20,1) przy ok. 3,3 GB odczytu wag na token zamiast ~16 GB.
- [[kwanty-gguf|Kwanty wag i KV, których używamy]] — Wagi trzymamy w kwantach K/I GGUF ładowanych w całości do VRAM; KV cache to q4_0 dla Qwena i q8_0 dla LFM (decyzja użytkownika); zmiana kwantu = inny model, więc to nie jest „optymalizacja bezstratna”.
- [[lfm2-5-24b-a2b|LFM2.5-24B-A2B (Liquid AI)]] — MoE 24B z ~2B aktywnymi parametrami i warstwami krótkiej konwolucji; na RX 7900 XTX z 173 do 294 t/s, bez spekulacji (brak draftera).
- [[lfm2-5-uncensored|LFM2.5-24B-A2B-Uncensored (AtomicChat, AD-Q5_K_M)]] — Abliterowany LFM2.5 od AtomicChat; ma więcej tensorów Q8_0, dlatego dostał własną łatkę MMVQ (0064) i działa z 267.3 t/s.
- [[lfm-czulosc-na-podzial-batcha|LFM2.5: logity zależą od podziału promptu na ubatche]] — Dowolne dwa rozmiary ubatcha (128–2048) dają dla LFM2.5-24B-A2B KLD 0.055–0.068 i 88–89% tego samego top-1, przy KV q8_0 i f16, a upstream `e60eff95f` daje bit w bit te same liczby co fork; A/A (ub 512 vs 512) to KLD 0 (2026-10-18).
- [[modele-katalogowe|Modele katalogu produktu i testów (gpt-oss, Gemma 4, Qwen3.5-9B, Bielik, Mistral)]] — Modele z licencją Apache 2.0, które produkt ma polecać i które testujemy na kartach NVIDIA; dla nich nie mamy jeszcze własnych kerneli.
- [[modele-telefon|Modele na telefon: MiniCPM-V 4.7 1B i EmbeddingGemma 2]] — Osobny projekt (`jarojarojaro-jaro/phoneuse`): lokalny agent na telefonie realme Note 50 (Unisoc UMS9230H), gdzie EmbeddingGemma dopasowuje podpisy ekranu, a MiniCPM-V jest opcjonalny; zasada: model nigdy nie klika z pewnością w złe miejsce.
- [[nanbeige4-3-33b|Nanbeige4.3-33B: gęsty model agentowy, który pokazuje, że Enigma liczy prędkość zamiast czasu zadania]] — Gęsty model (Llama, 52 warstwy) z AA v5 20,4 (Qwen3.8-27B 20,1) i Terminal-Bench 4.0 30% wobec 6% Qwena, ale z 44% większą liczbą tokenów na zadanie i KV 58,5 KB/token przy q4_0 (3,2× Qwen); na 24 GB mieści Q4_K_M tylko do 64k (R67b, 2026-11-07).
- [[nvfp4|NVFP4 (4-bitowy format NVIDIA)]] — NVFP4 to 4-bitowy format liczb NVIDIA, sprzętowo liczony od Blackwella (np. RTX 5060 Ti); RX 7900 XTX nie ma FP4/FP8, a my go nie używamy, bo zmienia model.
- [[nemotron-3-5-bolt-74b-a9b|NVIDIA Nemotron 3.5 Bolt 74B-A9B]] — Hybrydowy MoE NVIDIA (Mamba-2 + LatentMoE + 8 warstw attention, ~9B aktywnych) w pliku IQ2_XXS 22 018 326 528 B; na RTX 3090 z drafterem DFlash nasz silnik daje 141.1 t/s.
- [[nemotron-3-5-bolt-e4b|NVIDIA Nemotron-3.5-Bolt-E4B (Gemma-4-E4B po RL)]] — SLM NVIDIA na telefon i edge, wydany 2026-10-23: Gemma-4-E4B-it po RL (GRPO) pod narzędzia, rozmowę i instrukcje. Q4_K_M ma 6.18 GB i zajmuje „~4 GB VRAM”. Na drafter Qwen3.8-27B się nie nadaje.
- [[qwen3-5-9b|Qwen3.5-9B (mały Qwen do kart 8–12 GB)]] — Mały model Qwena, który mierzymy jako model dla kart z 8–12 GB VRAM: na 5060 Ti nasz fork CUDA daje 239,0 t/s przy edycji kodu i 121,0 t/s w sweepie (1 runda, 2026-10-16).
- [[qwen3-6-35b-a3b|Qwen3.6-35B-A3B (MoE 35B/3B)]] — Wybór raportu 33 dla kart 10–16 GB przy ctx ≥ 131k: eksperci częściowo w RAM (`--n-cpu-moe`), KV q4_0; szacunki fitcalc, niezmierzone u nas (2026-10-20).
- [[qwen3-8-27b|Qwen3.8-27B (główny model)]] — Gęsty hybrydowy model 27B (48 warstw Gated DeltaNet + 16 pełnej uwagi) z wbudowaną głowicą MTP; na RX 7900 XTX przyspieszony z 59.2 do 109 t/s.
- [[qwen3-8-27b-uncensored|Qwen3.8-27B-Uncensored (OrcaRouter)]] — Abliterowana wersja Qwen3.8-27B od OrcaRouter: usunięty „kierunek odmowy”, architektura bez zmian; u nas najszybszy wariant Qwena (115.5 t/s).
- [[qwen38-flash-next|Qwen3.8-Flash-Next (125B MoE, 6B aktywnych, zapowiedź architektury Qwen4)]] — Na XTX 24 GB + 62.72 GiB DDR4 najlepszy kwant przy tym rozmiarze to Unsloth v3.1 UD-IQ3_XXS (83.6 GB, KLD ~0.052 vs ~0.065 GSQ IQ3_S według stronniczego wykresu Unsloth), w Stracie albo w llama.cpp master ≥ b11330 z MTP; GSQ-RCO IQ3_S zostaje bezpieczną alternatywą w Stracie (raporty 66f i 66a, 2026-11-07).
- [[rsr-27b|RSR-27B (IntelligenceLab): Qwen3.8-27B po RSR + RL]] — Wydany model `IntelligenceLab/RSR-27B` (Apache-2.0, `qwen3_5`, 64 warstwy, 27.78 mld parametrów BF16) to Qwen3.8-27B dostrojony na przepisanych trajektoriach RSR + „dodatkowe RL”; tensory `mtp.*` (15) i `model.visual.*` są skopiowane z bazy (`model-missing-from-origin-*.safetensors`), więc głowica MTP nie pasuje do zmienionego pnia (2026-10-19).
- [[sensenova-loop-9b|SenseNova-Loop-9B: model z pętlą warstw — pamięć jak 9B, pasmo jak ~14B, jakość wg producenta blisko Qwen3.8-27B]] — Model z prawdziwej firmy, z prawdziwymi wagami (Apache-2.0), ale jakość to na razie tylko tabela producenta. Dla nas najważniejsze są dwie rzeczy. Pętla zmienia liczenie sufitu: bajty na token liczymy z wykonań warstw, nie z rozmiaru pliku. Model jest też kandydatem do Enigmy na karty 8–16 GB, ale upstream llama.cpp go jeszcze nie obsługuje.
- [[swift-1-5|Swift 1.5 (UkisAI): Qwen3.8-27B z krótszym myśleniem]] — Fine-tune RL/OPD Qwen3.8-27B na krótsze myślenie (deklaracja: −41.9% średnio i −58.5% w medianie tokenów GPQA-D przy +0.31 pp); kwanty GSQ-RCO z alokacją ISTA 1:1, głowica MTP niedouczona, licencja z progiem US$1M przychodu.
- [[bonsai|Ternary Bonsai 2 27B (PrismML)]] — Qwen3.8-27B w trytach {−1, 0, +1} od PrismML; najszybszy jest w forku prism jako PTQ1_0 (44.75 t/s na RTX 3060), a PQ2_0 można bezstratnie przepakować do upstreamowego Q2_0 i uruchomić na czystym llama.cpp i naszym forku.
- [[bonsai-2-5-uncensored|Ternary Bonsai 2.5 27B Uncensored (AtomicChat)]] — Bonsai 2.5 bez cenzury od AtomicChat to Qwen3.8-27B w trytach (5,99 GB); na XTX najszybciej idzie w naszej topce (`topka-k157`: port Hadamarda, PM4, 4 nowe łatki) jako bezstratny Q2_0 z MTP n2: przy pełnym kontekście 262k czat T=0,7 115–117 t/s, edycja kodu 434–446 t/s, bez spekulacji 76,7 t/s.
- [[uncensored-ablacja-kierunku|Uncensored = Main + edycja rank-1 kierunku w „pisarzach” strumienia]] — Oba nasze modele Uncensored to analityczne edycje wag Maina, nie fine-tune: Qwen3.8-27B-Uncensored (OrcaRouter) ma jeden globalny kierunek r rzutowany ze wszystkich writerów strumienia rezydualnego (s = 0.994–1.000), a LFM2.5-Uncensored (AtomicChat) ma osobny kierunek r_l w każdej warstwie 14–39 ze skalą 1.75 (analiza wag na CPU, raport 21e, 2026-10-19).
- [[saluki|Underdog Saluki 27B 1.0 (Qwen3.8-27B w 2 bitach)]] — Qwen3.8-27B skwantyzowany do 7.90 GB (IQ2-mix na bazie ISTA GSQ-RCO), strojony pod tool calling; na RTX 3060 działa z czystym upstreamem, ma najlepsze PPL i polszczyznę wśród naszych 2-bitowych 27B, ale bez MTP i z prędkością ~23 t/s.
<!-- AUTO:END -->
