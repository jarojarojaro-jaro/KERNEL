---
typ: ekosystem
tags: [ekosystem, agenci]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/06-kernelagent.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:16
status: aktualne
---
# meta-pytorch/KernelAgent

**Wieloagentowy system Meta zamieniający PyTorch na kernele Triton (HEAD `e0647170`, 2026-07-15); bierzemy strukturę pętli; werdykt: średnia (proces).**

Deterministyczna płaszczyzna sterowania w Pythonie, test pisany raz i zamrożony, regexowy zakaz oszukiwania, równoległe ziarna „pierwszy poprawny wygrywa”, dedup przez znormalizowany odcisk PTX, pętla profil NCU → diagnoza → przepisanie → test → pomiar. Liczby z bloga (H100, ich): 2.02× vs własne kernele „tylko poprawne”, 1.56× vs `torch.compile` bez CUDA graphs. Dla nas: zamrożona bramka testów, odcisk ISA wariantu, miner łańcuchów fuzji z trace'ów.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Porównanie z naszą pracą agentów ([[fabryka-v1]], `qwen-opt/factory/README.md`): sterowanie w kodzie zamiast w LLM mamy (weryfikator to skrypt, jedyny zapisuje werdykty); test zamrożony mamy mocniej (bramka bitowa, hash logitów, a u nich test pisze LLM, `qwen-opt/research/repos/06-kernelagent.md:159-165`); „czy zmiana się wykonała” mamy jako G3 `probe` (`factory/README.md:58,80`); ledger z prognozą przed pomiarem mamy (`factory/fk/report.py:70`, `expected_effect_pct`).
- Czego nie mamy: dedup kandydatów po znormalizowanym ISA i statyczny profil z ISA zamiast liczników PMC (u nas rocprofv3 PMC daje 0), pomysł 2 w `06-…md:66-81`. To dalej najtańszy nowy element (~1 dzień, bez GPU).
- Czego nie kopiować: pomiar `do_bench` średnią w jednym procesie i wybór minimum z 90 kandydatów, czyli klątwa zwycięzcy (~2.5σ przy N=90, `06-…md:130,153-158`). Nasze ABBA + A/A jest lepsze.
- Lekcja o porównaniach: „2.02×” liczone względem własnych słabych kerneli, „1.56×” względem `torch.compile` bez CUDA graphs, „89% roofline” to w praktyce ~56% pasma (`06-…md:170-175`). Ten sam błąd grozi u nas, gdy porównujemy silnik z „bazą”, którą sami wybieramy.

## Powiązane
- [[kernelbench]]
- [[ako4all]]
- [[playbook-optymalizacji]]
- [[repos-30-przeglad]]
