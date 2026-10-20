---
typ: research
tags: [research, hipfire, fuzje, gdn]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24g-hipfire-pomysly.md:8-12,21-33,60-63; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:13
status: aktualne
---
# Raport 24g: pomysły z hipfire – kwanty, fuzje małych kerneli, stan GDN int8

**Zmiana kwantów porzucona decyzją użytkownika, stan GDN int8 zabity (KLD 0.0234 przy progu 0.005), a jedynym kandydatem ≥ 0.3 ms są normy: pominięcie 129 norm daje tg128 40.82 → 42.69 t/s (+4.6%, górna granica) (2026-10-19).**

- Profil dekodu topki: 808 kerneli/token, MMVQ 20.4 ms, poza MMVQ 2.23 ms w 446 launchach; `rms_norm_mul_f32_unrolled` 129 × 5.31 µs = 0.69 ms (`24g:21-26,60`).
- Fuzja qkvza < 0.15 ms/token – kill; moe_down nie dotyczy modelu gęstego (`24g:39-41`).
- Górna granica norm (kolejka 26): `26:13`. Próby realizacji: ogon producenta [[raport-24l-fuzja-norm]] (fault, stop), osobny kernel [[raport-24u-norm-quant]] (już jest jednym launchem).
- Repo: [[hipfire]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[hipfire]]
- [[raport-24l-fuzja-norm]]
- [[raport-24u-norm-quant]]
- [[raport-23e-re-silniki]]
