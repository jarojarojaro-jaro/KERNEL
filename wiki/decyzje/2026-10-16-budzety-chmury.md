---
typ: decyzja
tags: [decyzje, chmura, koszt]
aktualizacja: 2026-10-16
zrodlo: ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5286,5394,5415,5560; ~/KERNEL/product/research/09-chmura-3090.md:183; ~/KERNEL/product/research/09-chmura-5060ti.md:191; ~/KERNEL/product/research/09-chmura-3060.md:229; ~/KERNEL/product/research/11-mtp-pl-pilot.md:8,169
status: aktualne
---
# 2026-10-16: budżety $5 na Vast i $6 na RunPod

**Kampania NVIDIA na Vast może wydać łącznie do $5 (z przedłużeniami), a trening głowicy MTP na RunPod do $6 kosztu naszego poda.**

- Vast: „możesz wziąć na dłużej, tak żeby wydać 5 dolarów” (00:52 UTC), „możesz przedłużyć, maks 5 dolarów” (01:31 UTC); przedłużać tylko, gdy GPU pracuje.
- RunPod: limit $6 dla agenta MtpTrain (01:35 UTC), pod z automatycznym wyłączeniem po 9 h i usuwany na końcu (zatrzymany nalicza za dysk). Od 02:38 UTC liczymy tylko koszt naszego poda, a bezpiecznik salda konta obniżono, żeby nie zatrzymać drugiego poda użytkownika.
Wydatki końcowe (2026-10-16): Vast ≈ $2.77 z $5 (3090 ≈ $0.90, 5060 Ti ≈ $1.05, 3060 ≈ $0.82), RunPod (pilot MTP) $2.14 z $6; wszystkie nasze instancje i pody zniszczone.
Salda kont nie zapisujemy w wiki.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[decyzje/2026-10-16-nie-placimy-za-przestoj|nie płacimy za przestój]]
- [[2026-10-16-runpod-drugi-pod]]
- [[2026-10-16-najpierw-wynajem-na-vast]]
- [[firma-runpod]]
- [[produkt-budzet]]
