---
typ: repo
tags: [repo, agenci]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/06-kernelagent.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:16
status: aktualne
---
# meta-pytorch/KernelAgent

**Wieloagentowy system Meta zamieniający PyTorch na kernele Triton (HEAD `e0647170`, 2026-07-15); bierzemy strukturę pętli; werdykt: średnia (proces).**

Deterministyczna płaszczyzna sterowania w Pythonie, test pisany raz i zamrożony, regexowy zakaz oszukiwania, równoległe ziarna „pierwszy poprawny wygrywa”, dedup przez znormalizowany odcisk PTX, pętla profil NCU → diagnoza → przepisanie → test → pomiar. Liczby z bloga (H100, ich): 2.02× vs własne kernele „tylko poprawne”, 1.56× vs `torch.compile` bez CUDA graphs. Dla nas: zamrożona bramka testów, odcisk ISA wariantu, miner łańcuchów fuzji z trace'ów.

## Powiązane
- [[repo/_hub|repo]]
- [[kernelbench]]
- [[ako4all]]
- [[playbook-optymalizacji]]
- [[repos-30-przeglad]]
