---
typ: lekcja
tags: [lekcje, chmura, vast, ssh]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16c-kvq-cuda.md:170-176,204-206; ~/qwen-opt/cloud/runs/kvq-cuda/up.sh:56-59
status: aktualne
---
# Vast: sshd odrzuca klucz przez prawa do authorized_keys

**Pierwsza 3090 w E1 (host w Jordanii) odrzucała klucz SSH z błędem „bad ownership or modes for /root/.ssh/authorized_keys”; instancję zniszczono po ~4 min (~$0.02), a naprawą jest pętla `chown`/`chmod` w onstart (2026-10-16).**

Reguła: onstart każdej instancji ustawia właściciela root i prawa 700/600 dla `/root/.ssh` przed pierwszym logowaniem; nie zakładać, że obraz ma je poprawne.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-vast-cli-klucz]]
- [[lekcja-brak-column-w-obrazie]]
- [[vast-ai]]
