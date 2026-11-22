---
typ: optymalizacja
tags: [optymalizacje, mmvq, topka]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24w-pair2.md:5-19,33-43; ~/KERNEL/product/research/24r-mmvq-pasmo.md:14; ~/KERNEL/product/research/24w-pair2.md:21-36; ~/qwen-opt/queue/logs/p2-md5.log
status: aktualne
technika: PAIR2 para MMVQ dla mieszanych typów
werdykt: odrzucone
zysk: +0,4% czat T=1 (115,1 → 115,6 t/s)
dowod: raport-24w-pair2
model: qwen3-8-27b
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 115.1 t/s | czat T=1 baza | 2026-10-20
  - qwen3-8-27b | rx-7900-xtx | 115.6 t/s | czat T=1 PAIR2=1 | 2026-10-20
---
# Raport 24w: PAIR2 (para MMVQ dla mieszanych typów) na topce – odrzucone (+0.4%)

**PAIR2 przeniesiony na topkę (`pair2-topka`, commity `7555f1d21`, `d7f1b7d37`, `5ac5a69b3`), bramka md5 przeszła, ale czat T=1 ABBA dał tylko 115.1 → 115.6 t/s (+0.4%, ms/krok 27.28–27.49 → 27.18–27.35) – odrzucone według zasady „wyraźna wygrana albo nic” (pomiar 2026-10-20 rano).**

- Oczekiwany zysk −40 uruchomień/krok, szac. 0.3–0.5 ms/krok ([[raport-24r-mmvq-pasmo]]); zmierzono ~0.1 ms/krok. Noc: kolejkę anulowano (zakaz testów na XTX), pomiar rano 13:55–14:04 UTC.
- Pomiar: md5 plain c4708318 / MTP 6f14e814 przy `PAIR2=1` (`MD5 OK`), spec_sweep T=1 seedy 1–3, każdy z 6 promptów +0.3…+0.6 t/s (`24w:21-34`). Nic nie instalujemy ([[lekcja-wyrazna-wygrana-albo-nic]]).
- PAIR2 wymaga commitu RPB (parametr `rows`); runtime’owy switch RPB usunięty (`24w:42`).
- Pierwszy build świeżego `build-hip` na farmie trwał > 50 min – puszczać bez limitu czasu (`24w:43`).

## Powiązane
- [[raporty-2026-10-19-20]]
- [[raport-24r-mmvq-pasmo]]
- [[raport-24n-mmvq-n5]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
