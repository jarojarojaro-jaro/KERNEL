---
typ: research
tags: [research, xtx, spekulacja]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/35-xtx-eksperymenty-z-researchu.md:14-25
status: aktualne
---
# Raport 35: XTX – krótkie eksperymenty z raportów 32a–32f

**DRAFT_N=5 jako profil opt-in (T=0 reasoning +6.8%, 144.4 → 154.2 t/s; czat +1.4% w szumie), checkpointy GDN to 41–81% TTFT tury agenta (→ raport 38), kary po stronie draftu odrzucone (2026-10-20).**

- Rozrzut prefillu świeżych startów 0.22% – brak problemu MES.
- Rozgrzewka z klienta zmienia md5 → tylko w serwerze (raport 45).
- Pułapka: odziedziczone `GGML_HIP_PM4=0` dało 136.2 zamiast 144.4 t/s → [[lekcja-pm4-zawsze-jawnie]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[rx-7900-xtx]]
