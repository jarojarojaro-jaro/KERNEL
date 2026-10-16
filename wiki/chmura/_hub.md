---
typ: hub
tags: [chmura, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Chmura GPU

**Wynajem GPU (Vast, RunPod, Salad, AMD Dev Cloud) i nasz harness do kampanii w chmurze.**

Klucze API leżą wyłącznie na serwerze (poza repo) i nigdy nie trafiają do wiki.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (6)

- [[amd-dev-cloud|AMD Developer Cloud i inne programy AMD]] — AMD daje $100 kredytu na MI300X (30 dni) i krótkie testy stacji Radeon PRO, ale z zakazami użycia komercyjnego; dla nas tylko do sanity-checku kodu HIP na CDNA3.
- [[radeony-do-wynajecia|Gdzie wynająć Radeona, Arca i Maca (Hostkey, GigaGPU, Scaleway, hyperscalerzy)]] — Konsumenckich Radeonów z root prawie nie ma w chmurze godzinowej; jedynym RDNA4 na godziny jest Hostkey R9700, reszta to dedyki miesięczne albo WSL2 bez `/dev/kfd`.
- [[harness-chmurowy|Harness chmurowy (~/qwen-opt/cloud)]] — Zestaw skryptów, który wynajmuje kartę na Vast, buduje upstream i nasz fork, mierzy poprawność i prędkość według stałego protokołu i niszczy instancję; każdy skrypt domyślnie tylko wypisuje komendy, wydaje pieniądze dopiero z `--go`.
- [[runpod|RunPod]] — Druga chmura w harnessie: Community i Secure Cloud z kartami 3070…5090, jedyne AMD to MI300X ($2.39/h); u nas przewidziany dla RTX 4090 i 5090, których nie ma w pierwszej rundzie.
- [[salad|SaladCloud (domowe PC graczy, WSL2)]] — Sieć domowych komputerów do gier: tanie NVIDIA (3060…5090) i pięć klas Radeonów, ale tylko jako kontener w WSL2 bez SSH; nadaje się do sprawdzenia „czy działa u gracza na Windowsie”, nie do strojenia kerneli.
- [[vast-ai|Vast.ai (główne źródło kart NVIDIA)]] — Marketplace hostów z kartami NVIDIA od GTX 10xx do RTX 50xx; tu wynajmujemy karty do kampanii (3060, 5060 Ti, 3090), bo zakup jest dużo droższy; AMD na Vast nie ma.
<!-- AUTO:END -->
