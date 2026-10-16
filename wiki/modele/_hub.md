---
typ: hub
tags: [modele, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Modele

**Modele, które uruchamiamy lub rozważamy: architektura, kwanty, KV, najlepsze zmierzone t/s, licencja.**

Liczby t/s zawsze z datą i warunkami (kwant, KV, MTP/DFlash, prompt, T). Aktualny stan instalacji: [[stan-2026-10-15]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (13)

- [[drafter-dflash|Drafter DFlash2 dla Qwen3.8-27B]] — Osobny mały model draftujący (z-lab / incoai, 5 warstw) — świetny na angielski kod przy T=0, ale na szerszym zestawie i po polsku nie bije głowicy MTP, więc domyślnie używamy MTP.
- [[glowica-mtp|Głowica MTP Qwen3.8-27B (spekulacja bez osobnego draftera)]] — Wbudowana warstwa `blk.64` (nextn) zgaduje kolejne tokeny, a główny model weryfikuje je jednym przebiegiem; to podstawa naszego 109 t/s, z ~3 tokenami na krok.
- [[kwanty-gguf|Kwanty wag i KV, których używamy]] — Wagi trzymamy w kwantach K/I GGUF ładowanych w całości do VRAM; KV cache to q4_0 dla Qwena i q8_0 dla LFM (decyzja użytkownika); zmiana kwantu = inny model, więc to nie jest „optymalizacja bezstratna”.
- [[lfm2-5-24b-a2b|LFM2.5-24B-A2B (Liquid AI)]] — MoE 24B z ~2B aktywnymi parametrami i warstwami krótkiej konwolucji; na RX 7900 XTX z 173 do 294 t/s, bez spekulacji (brak draftera).
- [[lfm2-5-uncensored|LFM2.5-24B-A2B-Uncensored (AtomicChat, AD-Q5_K_M)]] — Abliterowany LFM2.5 od AtomicChat; ma więcej tensorów Q8_0, dlatego dostał własną łatkę MMVQ (0064) i działa z 267.3 t/s.
- [[modele-katalogowe|Modele katalogu produktu i testów (gpt-oss, Gemma 4, Qwen3.5-9B, Bielik, Mistral)]] — Modele z licencją Apache 2.0, które produkt ma polecać i które testujemy na kartach NVIDIA; dla nich nie mamy jeszcze własnych kerneli.
- [[modele-telefon|Modele na telefon: MiniCPM-V 4.7 1B i EmbeddingGemma 2]] — Osobny projekt (`jarojarojaro-jaro/phoneuse`): lokalny agent na telefonie realme Note 50 (Unisoc UMS9230H), gdzie EmbeddingGemma dopasowuje podpisy ekranu, a MiniCPM-V jest opcjonalny; zasada: model nigdy nie klika z pewnością w złe miejsce.
- [[nemotron-3-5-bolt-74b-a9b|NVIDIA Nemotron 3.5 Bolt 74B-A9B]] — Hybrydowy MoE NVIDIA (Mamba-2 + LatentMoE + 8 warstw attention, ~9B aktywnych) w pliku IQ2_XXS 22 018 326 528 B; na RTX 3090 z drafterem DFlash nasz silnik daje 141.1 t/s.
- [[qwen3-8-27b|Qwen3.8-27B (główny model)]] — Gęsty hybrydowy model 27B (48 warstw Gated DeltaNet + 16 pełnej uwagi) z wbudowaną głowicą MTP; na RX 7900 XTX przyspieszony z 59.2 do 109 t/s.
- [[qwen3-8-27b-uncensored|Qwen3.8-27B-Uncensored (OrcaRouter)]] — Abliterowana wersja Qwen3.8-27B od OrcaRouter: usunięty „kierunek odmowy”, architektura bez zmian; u nas najszybszy wariant Qwena (115.5 t/s).
- [[swift-1-5|Swift 1.5 (UkisAI): Qwen3.8-27B z krótszym myśleniem]] — Fine-tune RL/OPD Qwen3.8-27B na krótsze myślenie (deklaracja: −41.9% średnio i −58.5% w medianie tokenów GPQA-D przy +0.31 pp); kwanty GSQ-RCO z alokacją ISTA 1:1, głowica MTP niedouczona, licencja z progiem US$1M przychodu.
- [[bonsai|Ternary Bonsai 2 27B (PrismML)]] — Qwen3.8-27B w trytach {−1, 0, +1} od PrismML; najszybszy jest w forku prism jako PTQ1_0 (44.75 t/s na RTX 3060), a PQ2_0 można bezstratnie przepakować do upstreamowego Q2_0 i uruchomić na czystym llama.cpp i naszym forku.
- [[saluki|Underdog Saluki 27B 1.0 (Qwen3.8-27B w 2 bitach)]] — Qwen3.8-27B skwantyzowany do 7.90 GB (IQ2-mix na bazie ISTA GSQ-RCO), strojony pod tool calling; na RTX 3060 działa z czystym upstreamem, ma najlepsze PPL i polszczyznę wśród naszych 2-bitowych 27B, ale bez MTP i z prędkością ~23 t/s.
<!-- AUTO:END -->
