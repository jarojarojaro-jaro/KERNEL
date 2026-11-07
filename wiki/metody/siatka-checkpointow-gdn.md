---
typ: metoda
tags: [metody, cache, gdn, agent]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66b-1cat-tokenspeed.md:140-158,219-220; ~/KERNEL/product/research/66a-strata-maya.md:221,394
status: do-sprawdzenia
---
# Siatka checkpointów GDN, junction i fallback odtwarzania

**1Cat zapisuje stan GDN na granicach bloku 2048, opcjonalnie co N tokenów (`--prefix-cache-retention-interval 8192`) i w punkcie rozwidlenia wykrytym przez poprzednie żądanie („junction learning”); u nas brakuje okresowej siatki w długich pojedynczych wiadomościach, checkpointu w rozwidleniu i warstwy dyskowej (raport 66b, 2026-11-07).**

- Ograniczenie 1Cat: pierwsze rozwidlenie wciąż przelicza (edycja ostatnich 10% promptu 32–64K), pomaga dopiero następnemu żądaniu.
- Ich koszt: przy gęstej retencji 74% RAM poszłoby na migawki (Flash-Next TP4). U nas ~150 MiB na checkpoint `[INFERENCE]`, do sprawdzenia w logu „created context checkpoint”.
- Szacunek dla nas: edycja końca promptu 60k, TTFT ~65 s → ~8–10 s `[SZACUNEK]`.
- Maya #840: przy nieudanym wczytaniu slotu próbuje następnego slotu, potem checkpointu, zamiast pełnego prefillu. Wzór łańcucha fallbacku dla `--cache-ram`.
- Enigma: zapis slotu przy bezczynności i zamknięciu (CRC32C + stan draftu MTP #30574), pierwsza tura po restarcie przy 50k ~55 s → ~2–4 s `[SZACUNEK]`.
- Projektować razem z chudymi checkpointami (plan #6 z 63). Bezstratne (kopie stanu), bramka md5 trafienia vs zimny start.

## Powiązane
- [[metody/_hub|metody]]
- [[wspolny-poczatek-promptu]]
- [[lekcja-cache-ram-za-maly]]
- [[pamiec-stanu-gdn]]
- [[cache-sesji-na-dysku]]
- [[1cat-vllm]]
- [[raport-66-synteza]]
