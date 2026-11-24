---
typ: metoda
tags: [metody, pomiar, profilowanie, agenci, tensorfold, infra]
aktualizacja: 2026-11-24
zrodlo: klon github.com/ashhart/skills @ 0ad4b2d (2026-11-24, bez pliku licencji) w ~/kernel/zrodla/ashhart-skills; analiza podagentów AshProcess, AshDiagnose, AshRest, AshServe 2026-11-24 (ich skrypty uruchomione na naszym śladzie rocprofv3 Mai i na :8080); nasze narzędzia qwen-opt/tools/xray/
status: aktualne
---
# Skille ashhart (TensorFold): co z nich bierzemy do pomiarów, wyścigu i serwowania

**Skrypty są krótkie i robią to, co opisują, ale ich wartość to metoda: prognoza liczbowa przed budową, tani „kill-probe”, werdykt A/B w kolejności B,C,C,B z podłogą szumu, dziennik ślepych uliczek i bramki zasobów kernela. Na naszych danych dały dwa twarde wyniki: dzisiejsze „+3–7%” z fuzji było do przewidzenia jako +0,8% (zmierzone +0,6%), a nasz serwer Qwen ma zdrowy cache prefiksu i poprawne wywołania narzędzi.**

## Wyniki na naszych danych (2026-11-24)
- **Wzór na fuzje (gfx1100, graf HIP Mai):** Δściany ≈ Δczasu kerneli − (usunięte uruchomienia × 1,8 µs). Realna przerwa na węzeł grafu to ~1,8 µs (8857 µs ściany, 7572 µs kerneli, 705 uruchomień); rocprofv3 podwaja ją do 3,84 µs. Fuzje L+D: −288 + 214 µs → +0,8% przewidziane, +0,6% zmierzone. „+3–7%” agentów to rozpiętość sufitów z przerw realnych i z profilera.
- **Gdzie idzie token Inklinga (AD-Q4_K):** 3618 MB/token przy średnio 731 GB/s (76%) w kernelach wag (głowica 94%, eksperci 78–80%, q|k|v|r|gate 81%); ~500 małych kerneli „kleju” + przerwy to ~44% ściany → następna dźwignia to klej wciągnięty do prologu/epilogu GEMV, nie szybsze GEMV (sufit +6%).
- **Bramka zasobów za darmo:** CSV rocprofv3 ma VGPR, SGPR, scratch, LDS. `experts_gate_up_swiglu_g_kernel` (prefill) ma 192 VGPR i **496 B scratch na wątek** (możliwy spill, 45,8 ms w śladzie) — do sprawdzenia `-save-temps`.
- **Szum rep2:** w jednym procesie 0,1%, między restartami Q6 0,1%, L2k 0,9%; pierwsze zapytanie zimne; Q1 dwumodalny.
- **Serwer :8080 (Qwen3.8-27B Uncensored):** `coder_audit.py probe-cache` → ciepłe tury 99,3–99,5% tokenów z cache (prefill 6250 → 148 ms), kontrola bez cache 0% → HEALTHY; `probe-tools` 3/3 PASS. Szablon Qwen czysty; szablon Inkling AD bez `add_generation_prompt` (ostrzeżenie).

## Co bierzemy (ranking)
1. **Dziennik wyścigu** (port `optimization-ledger`): tag mechanizmu + klasa kernela, blokada powtórek ślepych uliczek, prognoza vs pomiar dla każdego zawodnika (Kernel, Gemini).
2. **Karta prognozy + sonda ze śladu przed budową:** Δµs z wzoru wyżej; poniżej 1% nie budujemy. Narzędzia: `qwen-opt/tools/xray/rocprof2xray.py` (ślad → kroki, przerwy, bajty) i `hip_binary_gate.py` (VGPR, spill, zajętość dla gfx1100: `min(16, 1536/roundup(vgpr,24))`).
3. **Werdykt B,C,C,B × 2** z osobnym procesem na ramię i podłogą z tych samych rund (symulacja: 1,5% fałszywych alarmów, rozróżnia 0,6% na Q6); „poniżej progu” zamiast „w szumie”.
4. **Paragony rep2:** md5 odpowiedzi, sha binarki, przełączniki, temperatura; zimne pierwsze zapytanie oznaczone.
5. **Świeży „sędzia” przed wpisem do REKORDY** (speedup-referee: czy zmiana naprawdę działała, kontrola, która musi najpierw zawieść, A/A, rozkład Δbusy + Δprzerw).
6. **Serwowanie:** `coder_audit.py lint-template / probe-cache / probe-tools` po każdej zmianie szablonu lub flag; `quant-autopsy` do porównania kwantów AtomicChat vs unsloth (możliwości, nie tylko KLD); reguła trzech z `repro_rate.py` (fix niestabilnego błędu liczy się po ⌈3N/f⌉ czystych przebiegach).

## Zgadywanie (DSpark) i serwowanie: wnioski z drafter-forge, one-stream-lanes, output-parity, moe-xray
- **Ekonomia okna weryfikacji (priory Mai z 3090):** c[B] = 11,89 + 1,57·(B−1) ms przy 7,8 ms zwykłego kroku → stały koszt otwarcia okna 0,52 kroku, wiersz 0,20; próg akceptacji a* ≈ 0,57–0,60 dla B = 3–5, a przy T=0,7 mamy ~0,5–0,6 → DSpark na granicy. Każde −0,15 stałego kosztu obniża a* o 0,05–0,08. Najpierw tniemy stały koszt okna (jedna synchronizacja na rundę, akceptacja na GPU), potem koszt wiersza.
- **Pułapka:** `drafter_forge.py` wycenia niezmierzone szerokości jako darmowe (dało fałszywe „1,68× VIABLE”) — każda szerokość z własnego pomiaru (`qwen-opt/tools/xray/breakeven.py`).
- **Lokalność ekspertów:** cache ekspertów między przejściami pętli lub tokenami na XTX nie zadziała (ponowne użycie po 550–950 MB innych wag ≫ 96 MB Infinity Cache); liczy się tylko suma ekspertów w jednym oknie (`route_locality.py` na `IK2_TRACE`).
- **Podatek draftera [INFERENCE]:** z wczytanym drafterem każdy zwykły token płaci zapis kontekstu draftera (`ik2_main.cu:6351-6354`) — możliwe 3–4% (auto-kalibracja 108,7 vs 112,3).
- **Bramka parytetu serwowanego:** `parity.py` z seedami ≥ 1 (w Mai seed 0 = losowy), T 0 i 0,7, drafting wył. vs wł.; łapie błędy okna przy T>0, których md5 logitów nie widzi.
- Plan testów E1–E6 w [[KOLEJKA-TESTOW]] (K-139).

## Czego nie bierzemy
- `loop_driver.py` (bramki przyjmują `{"passed": true}`, router na udziałach z profilera kieruje źle), `breakthrough_lab.py autotune` (jeden pomiar na konfigurację), `vram-alchemist`, `fabric-and-multi-rank` (jedna karta). Repo nie ma licencji: kod tylko lokalnie, do repo KERNEL wyłącznie nasze narzędzia.

## Powiązane
- [[maya-ik2-inkling]]
- [[tensorfold]]
- [[inference-stack]]
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
