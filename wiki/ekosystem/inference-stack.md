---
typ: ekosystem
tags: [ekosystem, serwowanie, infra, produkt, enigma]
aktualizacja: 2026-11-24
zrodlo: klon BerriAI/inference-stack @ 812b448 (v0.4.1 preview, 2026-11-23) w ~/kernel/zrodla/inference-stack; raport product/research/inference-stack-vs-enigma-2026-11-24.md (plik:linia); 61/99 ich testów uruchomione lokalnie, wszystkie przechodzą
status: aktualne
---
# Inference Stack (BerriAI, zespół LiteLLM): co robi lepiej od naszej aplikacji Enigma i czego się uczymy

**To nie silnik, tylko ~1,2 tys. linii FastAPI sklejających sprawdzone części: vLLM, router llm-d (Envoy + endpoint picker), LiteLLM, Prometheus/Grafana i Lens. Cała praca poszła w to, co dzieje się po „gotowe”: restart po awarii, metryki, instalator z aktualizacją i wycofaniem, symulator bez GPU, czyste diagnostyki. Enigma jest daleko przed nimi w dopasowaniu modelu i prędkości (AMD, ≥131k kontekstu, zmierzone przepisy, uczciwy benchmark), a daleko za nimi w utrzymaniu działania.**

## Jak to działa (plik:linia w raporcie)
- Ścieżka zapytania: aplikacja → LiteLLM :4000 → Envoy → llm-d endpoint picker (gRPC ext_proc) → nagłówek z wybraną repliką → vLLM.
- **Router llm-d:** każda replika dostaje ocenę = Σ waga × wynik oceniacza; tu kolejka 2, zajętość KV 2, **trafienie w cache prefiksu 3**, „bez trafienia → najdawniej używana” 2 (`compose/router/epp-config.yaml:17-27`). Idea: wysyłać prompt tam, gdzie jego początek już leży w KV, chyba że replika jest zatłoczona. Na jednej karcie to ten sam problem co wybór slotu — u nas E4: obce zapytanie wyrzucało cache agenta, `LLAMA_SERVER_CACHE_SHARE_MIN=1024` dało Qwen 8,0 → 1,6 s.
- **LiteLLM:** jedno API OpenAI nad wieloma backendami, klucze, zespoły, budżety, metryki; modele rejestrowane przez API (`/model/new`), nie plik.
- **Launcher:** wyszukiwanie HF, prosty szacunek pamięci `wagi × 1,25 + 2 GB` (bez KV, kontekst 4096 domyślnie), stan wdrożenia zapisywany atomowo i odporny na restart, szybki błąd, gdy kontener padnie, **tryb symulacji** (llm-d-inference-sim zamiast vLLM: cała ścieżka bez GPU), diagnostyki z wyciętymi sekretami i gotowymi komendami.
- **Obserwowalność:** 5 dashboardów od bramy przez router po silnik: TTFT p95, tok/s, czekające zapytania, zajętość KV i trafienia prefiksu na replikę, zapytania na zespół.
- **Instalator:** suma kontrolna paczki, wygenerowane sekrety, aktualizacja z kopią poprzedniej wersji i powrotem przy błędzie; ścieżka AWS z harmonogramem wyłączenia GPU ustawianym **przed** wydaniem pieniędzy.
- Testy nazwane od awarii („diagnostyka nigdy nie pokazuje haseł”, „drogi przydział nie wynajmie GPU”), 99 sztuk.
- Słabe: tylko NVIDIA, kontekst 4096, brak modelu KV, zero liczb wydajności, `docker.sock` w launcherze, Grafana anonimowa.

## Dlaczego nasza Enigma wyszła gorzej (hipotezy z dowodami z naszych plików)
1. Zbudowaliśmy połowę „żeby było szybko”, a połowę „żeby działało” zostawiliśmy w dokumencie (APP-ARCHITECTURE: nadzorca, watchdog, /metrics, restart, aktualizacje — nic z tego nie powstało; po `ready` nikt nie pilnuje procesu, klient dostaje 502).
2. Wysiłek poszedł w witrynę: 97 commitów landingu vs 28 aplikacji, 12 rund jurora.
3. Testowaliśmy na naszym labie, nie na sprzęcie klientów (APU pomylone z kartą: „PODSTAWOWY BŁĄD”).
4. Nasz wyróżnik nie trafia do użytkownika: silnik ROCm gfx1100 ma `distribution: local`, użytkownik AMD dostaje tylko zwykłe llama.cpp.
5. Pisanie silnika od zera (Enigma Turbo: CPU 0,7 t/s, bełkot) powtórzyło błąd w większej skali; oni nie napisali ani silnika, ani routera, ani bramy.

## Co bierzemy (ranking wartość/koszt)
1. `--metrics` w llama-server + metryki na naszym proxy (TTFT, t/s, akceptacja draftu, tokeny z cache) i pokazanie ich w UI — ½ dnia.
2. Watchdog po `ready`: restart z backoffem, potem konfiguracja bazowa, potem upstream — 1 dzień.
3. Symulator silnika do testów całej ścieżki bez GPU — 1–2 dni.
4. Panel diagnostyki z wyciętymi sekretami i komendami — ½ dnia.
5. Instalator jedną komendą z sumą i podpisem (mamy klucze Ed25519) + kopia poprzedniej wersji — 2 dni.
6. **Wysłać silnik AMD do użytkowników** — bez tego wyróżnik nie istnieje — 1–2 dni pakowania.
7. Macierz testów = sprzęt klientów (APU, iGPU, 8/12/16 GB, Windows), testy nazwane od awarii.
8. Dashboard Grafana dla naszego labu (:8080, topka) już teraz.

## Wiedza ogólna (infra)
- Standard metryk serwowania: na zapytanie TTFT, opóźnienie między tokenami, czas kolejki/prefillu/dekodu; na silnik: zapytania w toku/czekające, zajętość KV, trafienia prefiksu, liczniki tokenów; na bramę: zapytania i błędy na klucz. llama.cpp ma własne `llamacpp:*` (także tokeny z cache i zaakceptowane drafty).
- Routing świadomy cache KV to kompromis trafienie prefiksu vs obciążenie; zimne prefiksy rozkłada się LRU.

## Powiązane
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
- [[produkt-dla-kogo-i-ekrany]]
- [[lekcja-enigma-apu-jako-karta]]
- [[lista-dostawcow-inferencji]]
