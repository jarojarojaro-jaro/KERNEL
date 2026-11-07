---
typ: repo
tags: [repo, megakernel, nvidia, konkurencja]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66c-hyperkernel-megakernele.md:11-87; https://github.com/Hyperstitioncc/Hyperkernel (7048c586); https://x.com/hyperstition_cc/status/2118432349352595528
status: aktualne
---
# Hyperkernel (Hyperstition): rezydentny megakernel na B300

**Repo zawiera tylko gotowe pakiety SASS/cubin dla B300 (`sm_103a`) i host w Ruście, bez generatora i źródeł kerneli; ścieżki AMD nie ma (0 trafień `hip|rocm|amd|gfx`), więc na gfx1100 nie ma czego portować (raport 66c, 2026-11-07).**

- Konstrukcja (z symboli SASS): jeden kooperacyjny `mega_main`, 148 CTA × 384 wątki, klaster 16, 227 KB SMEM, uruchomiony raz na całe życie serwera. Statyczny harmonogram per SM, 140 etapów `spine_body*`, zależności przez monotoniczne liczniki (atomik bez odpowiedzi + poll wątku 0). Próbkowanie i akceptacja draftu (blok 6) na GPU; host daje „grant” na 2 kroki naprzód.
- Nagłówek +36.7% (1129.6 vs 826.5 tok/s/user, 4×B300, DeepSeek-V4.1-Flash): bazą jest liczba vLLM opublikowana przez NVIDIA, nie powtórzona. AgentX wymusza akceptację w bazach, a Hyperkernel liczy na prawdziwej, której nie podaje. Słupek C4 +90.6% porównuje ze słabszą bazą. Jakość: 7 pytań z odpowiedziami, bez KL.
- Generator zapowiedziany „w kilka tygodni”; AMD tylko jako zdanie w wątku.
- Wzorce warte zapamiętania: ≤ 1 atomik na WG na etap, liczniki co 128 B, prefetch wag przed czekaniem, grant z horyzontem dla pętli MTP, znaczniki czasu per etap.

## Powiązane
- [[repo/_hub|repo]]
- [[megakernele-prior-art]]
- [[budzet-megakernela-qwen-xtx]]
- [[lekcja-tps-z-zalozonej-akceptacji]]
- [[firma-nvidia]]
- [[raport-66-synteza]]
