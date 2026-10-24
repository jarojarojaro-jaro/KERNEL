---
typ: lekcja
tags: [lekcje, enigma, aplikacja, testy, sprzet]
aktualizacja: 2026-10-24
zrodlo: zgłoszenie użytkownika (Windows, „AMD Radeon(TM) Graphics · 1 GB · 31 GB RAM”); `app/engine/test/catalog.fixtures.ts` (stan z commitu cba67ca)
status: aktualne
---
# Enigma: zintegrowana grafika potraktowana jak karta graficzna

**Pierwszy test aplikacji na prawdziwym PC użytkownika (Windows, AMD APU, 31 GB RAM) pokazał „Pamięć karty 19,0 z 20,5 GB”, Vulkan i Qwen3.6-35B-A3B z szacunkiem 34 t/s — aplikacja potraktowała zintegrowaną grafikę jak kartę z pamięcią współdzieloną typu Apple i liczyła prędkość z niewłaściwej przepustowości.**

Dlaczego tego nie wyłapaliśmy:
- Fixture'y testów obejmowały tylko osobne karty (8–32 GB), Maca i „czysty CPU” — **żadnego APU ani laptopa z iGPU**, czyli najczęstszego komputera klienta.
- Klasyfikator miał dwie klasy pamięci: osobna VRAM albo „unified” (napisana pod Apple). Każda grafika z małą VRAM i dużą pamięcią współdzieloną wpadała do „unified” z budżetem 66–75% RAM i przepustowością jak dla karty.
- Testy E2E na Vast to wyłącznie osobne karty NVIDIA; brak Windows/laptopów w labie.

Reguła: macierz sprzętu do testów = **rozkład realnych klientów**, nie nasz lab: APU AMD (DDR4/DDR5), laptop Intel iGPU, CPU-only, osobne karty 8/12/16/24 GB, Mac. Każda nowa klasa sprzętu dostaje fixture z prawdziwego skanu przed wydaniem. Prędkość dla iGPU/CPU zawsze z przepustowości RAM (typ, MT/s, kanały), jako przedział z etykietą „szacunek”.
