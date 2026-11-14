---
typ: research
tags: [research, konkurencja, compwatch, zwiad, arxiv, rss]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/product/research/watch/2026-10-20.md:1-12; ~/KERNEL/product/research/watch/INDEX.md; ~/KERNEL/tools/compwatch/README.md
status: aktualne
---
# Wywiad konkurencji (compwatch) – raporty dzienne i zwiad

**Codzienny `tools/compwatch/compwatch.py`: bazowy 2026-10-20 – 41 pozycji, top 3090/Qwen 273.1 t/s tqLLM vs nasze 93.3 (nieporównywalne, raport 32f); drugi przebieg 1 pozycja (sglang). Od 2026-11-14 to poranny zwiad sesji Kernel: także arXiv i blogi RSS/Atom.**

- Dane LocalMaxxing tylko do analizy wewnętrznej.
- Po 2026-10-20 raportów nie było. Kod działa (przebieg 2026-11-14 na serwerze bez błędu), log crona z maszyny z kartą nie był dostępny; najpewniej cron nie nadrabia przebiegów, gdy maszyna jest wyłączona o 06:30, a zerwane połączenie kończyło cały przebieg.
- Od 2026-11-14 timer systemd na serwerze 24/7 (06:30, `Persistent=true`, `nice 15`, `CPUQuota=50%`). Błąd jednego źródła trafia do „Uwag”, reszta przebiegu idzie dalej.
- Nowe źródła: repo TensorRT-LLM, MLC LLM, mistral.rs (tier B); arXiv (`cs.LG/DC/PF/AR/CL` × frazy o inferencji, 1 zapytanie na 3 s, duplikaty po id); 9 blogów (vLLM, Tri Dao, PyTorch, ROCm, NVIDIA, HF, Together, Modular, Chips and Cheese).
- Raport z nowościami → jedna wiadomość `[Zwiad · data]` w skrzynce sesji Kernel; sesja robi triage, notatki, `ZRODLA`, pozycje `K-…` i commit raportu. Ze zwiadu nic nie idzie na kartę.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[tqllm]]
- [[raport-32f-ninfer-tqllm]]
