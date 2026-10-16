---
typ: research
tags: [research, agenci, fabryka, bramki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:1-63,353-368
status: aktualne
---
# Raport 15f: agentowa nauka (Sakana v3, KernelGuard) a nasza fabryka

**Z systemów automatycznej nauki warto przenieść dyscyplinę artefaktów (ewaluator poza zasięgiem agenta, ledger, reguły z fixture’ami), ale nie promocję „wynik ściśle większy” bez statystyki; propozycja fabryki v1 za ~8–9 osobodni.**

Raport 2026-10-16, bez GPU, pięć eksperymentów CPU na naszych danych.
- **Sakana AI-Scientist-v3:** ewaluację uruchamia harness, ewaluator przypięty hashami i `:ro`, finalna ocena raz w osobnych kontenerach; ale statystyka to tylko `{n, mean, std, min, max}`, a promocja `score > best` bez marginesu szumu. W 2 z 3 przebiegów GRPO agent zmienił protokół ewaluacji niezauważony przez bramki.
- **KernelGuard (GPU MODE):** reguły z fixture’ami historycznych hacków + „physics floor” z roofline’u; oszukane zgłoszenia 3.45% → 0.37% w 32 dni.
- **Nasze dane:** tylko 25/70 commitów ma komplet dowodu, 0/70 podaje CI; A/A w sesji 0.09% ms/krok, ale label „base” dryfuje 29.12–29.81 ms między sesjami; wybór konfiguracji spekulacji na promptach selekcji zmienia znak przewagi na odłożonym w 2–3 z 5–6 przypadków; reguła anomalii łapie incydent 5.6 t/s.
- **Fabryka v1:** role (Planista, Implementer, Weryfikator jako kod, Audytor liczb, Kronikarz, Człowiek), karta twierdzenia przed pomiarem, `ledger.jsonl` z łańcuchem hashy, kaskada bramek G0–G7.
- Koszt pełnej weryfikacji twierdzenia BIT ~27 min GPU; wszystkich 70 łatek ≈ 32 GPU-h, ze wspólną bazą jak w `loo.py` ≈ 9 GPU-h.
Ranking: 1. ledger + karta twierdzenia, 2. reguły z fixture’ami, 3. `factory verify`, 4. zestaw odłożony, 5. audyt liczb.

## Powiązane
- [[research/_hub|research]]
- [[fabryka-v1]]
- [[sakana-agentic-scientist]]
- [[kernelguard]]
- [[produkt-fabryka]]
- [[raport-07-metody]]
- [[lekcja-agent-zmienia-protokol]]
