---
typ: research
tags: [research, telegram, linux, pamiec, offload, amdgpu, enigma]
aktualizacja: 2026-11-20
zrodlo: https://x.com/Biggest/status/2123541780889284976 (Telegram „gpu” 2026-11-20); https://kernelnewbies.org/Linux_7.2 (wydanie 2026-08-16); product/research/13-rocm-10.1.md:341-342 (jądro jaroserverai)
status: aktualne
---
# Linux 7.2 a LLM: zmiany pamięci pomagają przy odciążaniu do RAM/SSD, nie przy modelu w całości w VRAM

**Tweet (@Biggest, 19.11): „jeśli nie masz jądra 7.2+, zaktualizuj; nowe zarządzanie pamięcią i eksmisja robią LLM-y dużo płynniejszymi”. Bez liczb i bez konfiguracji. Zmiany w 7.2 (16.08.2026) są prawdziwe, ale pomagają tylko tam, gdzie model albo jego cache siedzi w RAM lub na dysku pod presją pamięci. Na XTX z całym modelem w VRAM tempo pisania się nie zmieni [INFERENCE: niezmierzone].**

## Co w 7.2 dotyczy LLM (kernelnewbies, Linux_7.2)

| zmiana | co robi | kogo dotyczy | liczba ze źródła |
|---|---|---|---|
| MGLRU: pętla odzyskiwania i writeback | lepszy wybór stron do eksmisji, mniej ponownych odczytów plików | modele w `mmap` przy małym RAM, odciążanie ekspertów MoE z RAM/SSD (Maya, QuixiInfer, Strata), duży `--cache-ram` | do ~30% w MongoDB/YCSB, „duży spadek file refault”, mniej OOM |
| `filemap`: dokładniejsze liczenie `mmap_miss` | mniej zbędnego synchronicznego readahead przy losowym dostępie do `mmap` | czytanie ekspertów MoE z pliku `mmap` (losowe skoki po GGUF) | „drastycznie” mniej odczytanych GB (bez liczby) |
| swap table faza IV | szybszy, chudszy swap | maszyny, które swapują przy dużym modelu | – |
| sprawiedliwszy planista DRM (GPU) | interaktywne programy nie zacinają się, gdy GPU jest pod pełnym obciążeniem | pulpit na tej samej karcie co LLM (Enigma na komputerze użytkownika); dotyczy amdgpu, Intel Xe i innych sterowników DRM. NVIDIA (sterownik własnościowy) nie | – |
| amdgpu: kilka kolejek SDMA dla operacji TTM | szybsze przenoszenie buforów VRAM ↔ RAM | ładowanie modelu i eksmisja VRAM na Radeonach | – |
| khugepaged: zwijanie do mTHP; plikowe THP dla zapisywalnych plików | więcej dużych stron, mniej chybień TLB | wagi i KV w RAM przy wnioskowaniu na CPU i iGPU (Strix Halo, Apple nie) | – |

## Dla nas

- **XTX (topka):** model 16 GB i KV w VRAM, a tempo zależy od pasma karty. Jądro wpływa najwyżej na:
  - start (wczytanie GGUF z page cache);
  - `--cache-ram 40960`, czyli wpisy cache promptów w RAM: przy presji pamięci MGLRU może je lepiej trzymać;
  - pulpit na tej samej karcie (planista DRM).
- **jaroserverai bootuje jądro 6.8.0-138**, a 7.0 jest tylko zainstalowane (R13, `13-rocm-10.1.md:341-342`). Skok na 7.2 to zmiana systemu pod ROCm 10.0 i PM4. Jest osobnym eksperymentem z nowymi pomiarami bazowymi i zależy od decyzji właściciela (K-132).
- **Enigma na Linuksie:** dla użytkowników z małą kartą i modelem MoE częściowo w RAM (odciążanie ekspertów) to realny argument. Można to dopisać do porad: „jądro ≥ 7.2 przy odciążaniu do RAM”, ale dopiero po pomiarze.
- Wszystkie firmy:
  - MGLRU, mmap i THP to zmiany po stronie CPU i RAM, więc działają niezależnie od producenta GPU;
  - planista DRM dotyczy AMD, Intela i otwartych sterowników, nie własnościowego sterownika NVIDIA;
  - Apple ma swoje jądro, więc nie dotyczy.

## Następny krok

K-132 (niski priorytet, za zgodą właściciela): jaroserverai z jądrem 7.0 albo 7.2 w porównaniu z 6.8. Mierzymy start do `/health`, TTFT po restore z `--cache-ram` przy presji RAM i dekod 1,7k (kontrola, oczekiwane bez zmian). Do tego na CPU odciążanie MoE z `mmap` (np. Qwen3.8 Flash na serwerze Jarva albo flocie), refault i t/s.

## Powiązane
- [[KOLEJKA-TESTOW]]
- [[project-maya]]
