---
typ: ekosystem
tags: [ekosystem, pomiar, szum, chmura, narzedzia]
aktualizacja: 2026-11-25
zrodlo: https://x.com/StasBekman/status/2125250482344210595 (2026-11-24); github.com/stas00/ml-engineering commit cd2c58664d4b3c66c4fd1f2a303c759bf8b239b6, compute/accelerator/benchmarks/gpu-straggler-finder.py i README.md#straggler-finder (przegląd podagenta 2026-11-25)
status: aktualne
---
# gpu-straggler-finder (Stas Bekman)

**Narzędzie znajduje GPU, które co jakiś czas zwalniają o kilka procent: patrzy na 90. percentyl okien 2 s względem mediany węzła, a nie na średnią; dla nas bierzemy statystykę do A/B i bramki hostów Vast, nie całe narzędzie.**

## Mechanizm
- Cztery obciążenia równolegle na każdym GPU węzła, bez komunikacji: krok 32 warstw Llama-3.1-8B (fwd+bwd, bf16, 8192 tok., 100 ms przerwy, 60 s), matmul 8192³ bf16 (30 s), kopia 1 GiB, stream `c=a+b` 1 GiB.
- Czas w oknach 2 s, każde okno dzielone przez medianę GPU węzła; okna z medianą > 5% wolniejszą to „stall” i wypadają. Ocena po oknie p90.
- „slow”: MAD z-score > 3,5 i > 1% wolniej od mediany; „unsteady”: p90 > 1,25% nad własną medianą okien; węzeł „slow”: > 3% od mediany węzłów. `--baseline` porównuje z JSON zdrowych węzłów (identyczne argumenty).
- PyTorch + gloo; telemetria (zegar SM, moc, temperatura) tylko NVML. Na ROCm same czasy, AMD nietestowane.

## Liczby ze źródła
- 32 × B200: krok 404,85 ms (rozrzut 3,2%), matmul 1315 TFLOPS (6,2%). Straggler: p90 +3,4%, mediana +1,0%, zegar SM 1462 MHz wobec 1537–1574 u sąsiadów przy tej samej mocy 1000 W; wolny 3–4% przez 20–25 s po bezczynności, potem ok. 1%.
- Matmul i DCGM diag stragglera nie wykryły: średnia i krótki test go ukrywają.

## Czego uczy nas
- **Nasze A/B na XTX** (ABBA, xtxbench): raportujemy medianę rund; dokładamy p90 okien i „stretch” (p90 − mediana), bo wolne okresy (np. po bezczynności karty) to składnik szumu, którego mediana nie pokaże. Bezczynność przed pomiarem ma znaczenie: przerwy w kolejce (restore :8080) zmieniają zegar startowy.
- **Bramka hostów Vast** (`qwen-opt/cloud`, `hosty-zle.txt`): dziś sprawdzamy limit mocy i zegar z `nvidia-smi` bez obciążenia. Straggler przechodzi taki test. Dodać 60 s obciążenia z oknami 2 s i porównaniem z plikiem bazowym dobrego hosta tej samej karty, zanim zapłacimy za pomiar.
- **Enigma u klienta**: jedna karta, więc tylko „unsteady” (p90 vs mediana własnych okien) + zegar; lepszy sygnał „karta dławi” niż jedna średnia w raporcie przed → po.
- Wiele GPU (przyszłe TP na kilku kartach): tu narzędzie ma pełny sens; port telemetrii na `amdsmi`.

## Werdykt
Port statystyk do naszych bramek tak; całe narzędzie dopiero przy ≥ 2 GPU. Test: statystyka okien na zapisanych seriach czasów xtxbench (CPU), potem jeden przebieg `--layers 4 --duration 300` na XTX (ok. 6 min) porównany z szumem ABBA.

## Powiązane
- [[pomiar-abba]]
- [[xtxbench-szybki-ab]]
- [[gpu-guard]]
- [[2026-11-07-kampania-nvidia-vast]]
