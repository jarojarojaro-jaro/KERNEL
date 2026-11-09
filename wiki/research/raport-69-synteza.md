---
typ: research
tags: [research, synteza, spekulacja, enigma]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/product/research/69-SYNTEZA.md; 69a-dspine-27b.md; 69b-tensorfold-qwen-warp.md; 69c-astra-stop.md; 69d-amd-sterownik-ssd.md
status: aktualne
---
# Raport 69: DSpine-27B, qwen-warp/TensorFold, Astra-Stop, sterownik AMD a SSD

**Runda bez pewnego zysku dla XTX: DSpine-27B tylko jako drafter „nowy kod” ≤ 16k po teście τ (pobranie 1.26 GB), qwen-warp jako referencja dla Enigmy 3090, Astra-Stop jako zmiana zachowania do decyzji, błąd Adrenalina jako karta UX Enigmy; wszystkie testy czekają na decyzję użytkownika (2026-11-09).**

- [[drafter-dspine]]: krok 37.5–43.5 ms na XTX przy 2k ⇒ τ musi być 1.39–1.62× MTP4; en-code +9…+57%, PL proza −67…−40%, mieszanka agentowa +0…+4%. Port Ajaya `d493f84` = 323 linie, SWA 8192.
- [[qwen-warp]] 0.8.0: DFlash2 w grafie (czat ×1.34, agent z kopiowaniem −31%, 262k się nie mieści); [[tensorfold]]: gfx1100 dalej brak.
- [[astra-stop]]: mediana myślenia −35.5% (xhigh, replikacja), `</think>` w treści 11/32; LoRA 90 KB gotowa; opcje: nic / opt-in LoRA / wpiec / tylko strażnik.
- [[amd-adrenalin-zapisy-ssd]]: serwer nie dotyczy; ostrzeżenie oparte na pomiarze, nigdy „wyłącz ReBAR”.
- Decyzje: (1) DSpine T1, (2) Astra-Stop, (3) qwen-warp vs fork na 3090, (4) karta AMD, (5) mini-zestaw jakości lm-eval/EvalPlus/BFCL (dziesiątki MB), (6) dynamiczna głębokość MTP z 68b. Próg adopcji: ≥ 3–5% decode/prefill lub ≥ 1 s na turę. Tabela: [synteza](../../product/research/69-SYNTEZA.md).

## Powiązane
- [[research/_hub|research]]
- [[raport-66-synteza]]
- [[raport-21a-dspine]]
- [[koszt-szerokosci-weryfikacji]]
- [[final-recipes-nvidia]]
- [[ZRODLA]]
