---
typ: model
tags: [modele, mtp, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/mtp-train/RESULTS.md:1-10,52-127; ~/KERNEL/qwen-opt/NOTES.md:128-146,233,317; ~/KERNEL/qwen-opt/research/drafters.md:9-13; git -C ~/llama.cpp log mtp-train -1; ~/KERNEL/product/research/11-mtp-pl-pilot.md:3-9,24-30,66-93
status: aktualne
---
# Głowica MTP Qwen3.8-27B (spekulacja bez osobnego draftera)

**Wbudowana warstwa `blk.64` (nextn) zgaduje kolejne tokeny, a główny model weryfikuje je jednym przebiegiem; to podstawa naszego 109 t/s, z ~3 tokenami na krok.**

Ustawienia: draft n=4 (n=5 lepszy na kod, gorszy na czat/prozę; po T1 Qwen n=4 102.7 vs n=5 103.0), słownik draftu 64k, głowica przekwantyzowana do IQ4_XS, greedy łańcuch draftu.

Akceptacja głowicy (pomiar offline 2026-10-12, 69 207 tokenów odpowiedzi, n_draft=4): średnio 3.04 tok/krok (EN 3.11, PL 2.97); en-code 3.76, en-chat 2.68, pl-prose 2.48. Wyrocznia (greedy z argmax celu): 3.93.

Wnioski z `mtp-train/RESULTS.md`:
- brak luki językowej: PL proza jest wolna, bo sam model jest mniej przewidywalny (wyrocznia PL 3.89 vs EN 3.96);
- jest ogólna luka głębokości: akceptacja warunkowa spada z 0.78 (d1) do 0.72 (d2+), a wyrocznia zostaje 0.87–0.89;
- głowica jest „za pewna siebie” dla rejection sampling, dlatego `--spec-draft-sampling probabilistic` nie pomógł;
- rekomendacja: GO dla pilota samodestylacji na 2 M tokenów, oczekiwany zysk greedy +5–11% tok/krok, bez osobnej głowicy PL.

**Pilot douczania (2026-10-16, raport 11) – wynik negatywny:** na 1.7 M tokenów (0.39 M on-policy) głowica zmienia tok/krok o ±2% (offline najlepiej +0.2%; online n=4 PL-proza +2.3%, reszta 0 do −1.7%). Na held-out fabryczna głowica ma 3.266 tok/krok przy n=4, wyrocznia 3.960 (+21%), ale trening jej nie przybliża. W pliku głowica jest w Q6_K/Q8_0/F32 (351 008 768 B); IQ4_XS powstaje dopiero przy ładowaniu (−0.45% tok/krok offline). Nie skalujemy tego do 10 M tokenów.

Publicznie (drafters.md): nie ma EAGLE-3, Medusa ani przetrenowanej głowicy MTP dla Qwen3.8-27B. Gałąź `mtp-train` (2026-10-16) dodaje narzędzie `llama-mtp-extract`.

## Powiązane
- [[modele/_hub|Modele]]
- [[drafter-dflash]]
- [[mtp-draft-graf]]
- [[latki-spekulacji]]
- [[raport-10-post-training]]
- [[raport-11-mtp-pl-pilot]]
- [[2026-10-16-mtp-pl-pilot]]
