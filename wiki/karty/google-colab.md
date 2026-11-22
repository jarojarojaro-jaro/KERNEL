---
typ: karta
tags: [karty, nvidia, chmura]
aktualizacja: 2026-11-22
zrodlo: wiadomość operatora (polecenie JARO) 2026-11-22 03:15, „Reczne · gpu”; ~/kernel/KERNEL-SESJA.md (sekcja „Google Colab: drugie GPU”)
status: aktualne
karta: google-colab
gdzie: Google Colab (subskrypcja Google AI Pro JARO)
stan: dostępny od 2026-11-22, 200 jednostek/mies.
---
# Google Colab: drugie GPU (NVIDIA T4, L4, G4, A100, H100)

**Od 2026-11-22 mamy Colab z subskrypcji JARO (200 jednostek miesięcznie) jako drugie GPU obok [[jaroserverai]]: T4 i L4 od razu, A100 i H100 tylko z zapowiedzią kosztu; maszynę zawsze wyłączamy po pracy.**

- **Polecenia (`colab`, CLI 0.8.0, zalogowane na serwerze Jarva):** `colab usage`; `colab run --gpu T4|L4|G4|A100|H100 skrypt.py` (wyłącza się sama); dłużej `colab new -s nazwa --gpu …`, `colab exec -f plik.py`, `colab download`, `colab stop`.
- **Zasady:** w raporcie karta, czas i „wyłączona”; nie przepalamy jednostek na to, co zrobi jaroserverai; przed pobraniem modelu `nvidia-smi` (limit mocy i zegar pamięci jak na [[vast-ai]]).
- **Próba operatora (2026-11-22):** T4, 29 s łącznie, 3,5 TFLOPS fp32, wyłączona.
- **Do czego:** pomiary na NVIDIA (CUDA, fork NVIDIA, Inkling 2 Mini na L4 24 GB), gdy jaroserverai jest wyłączony.

## Powiązane
- [[jaroserverai]]
- [[vast-ai]]
- [[runpod]]
