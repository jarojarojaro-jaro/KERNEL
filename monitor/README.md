# REACTOR – monitor GPU/CPU/LLM w terminalu

Pełnoekranowy monitor na żywo dla tego serwera (Radeon RX 7900 XTX + Ryzen 7 5700X),
pomyślany pod uruchamianie lokalnych LLM. Czysty Python 3.12 (tylko biblioteka
standardowa), surowe sekwencje ANSI: 24-bitowe kolory, znaki braille'a i bloki.

## Co pokazuje

- **GPU** (`/sys/class/drm/card*/device` + hwmon amdgpu): obciążenie GPU i kontrolera
  pamięci, VRAM zajęty/całkowity, temperatury edge / junction / mem, pobór mocy
  względem limitu (285 W), zegary sclk/mclk (z oznaczeniem GFXOFF w spoczynku), obroty
  wentylatora, łącze PCIe, aktualny poziom DPM, procesy trzymające GPU (KFD) z ich VRAM.
- **CPU**: obciążenie każdego z 16 wątków (animowany „equalizer”), suma, load average,
  temperatura Tctl (k10temp), temperatura NVMe, częstotliwość średnia i maksymalna,
  RAM (dużymi cyframi obok TOTAL/TCTL/FREQ, pasek z wykresem i w nagłówku) i swap.
- **Procesy**: top procesów wg CPU (z RSS).
- **I/O**: przepustowość dysków (odczyt/zapis) i sieci (pobieranie/wysyłanie).
- **LLM**: gdy działa `llama-server` – nazwa modelu (z `-m` w linii poleceń albo z logu),
  bieżące tokeny/s (z linii `print_timing ... tg_3s` w `~/qwen-opt/logs/latest.log`),
  n_gen, szczyt, ostatnie `eval` / `prompt` tok/s, średnia z 2 minut.
- **Duże liczby**: obciążenie GPU %, temperatura junction, moc W, tokeny/s (oraz CPU %,
  Tctl, częstotliwość) rysowane dużą czcionką blokową, kolor zależny od wartości.
- **Historia**: każda kluczowa metryka ma wykres z ostatnich ~2 minut (próbkowanie
  2 Hz), wypełniony gradientem od zimnych (cyjan) do gorących (róż/czerwień) wartości,
  ze świecącą górną krawędzią.
- **Rdzeń 3D**: obracający się, cieniowany torus (siatka w znakach braille'a).
  Prędkość obrotu = obciążenie GPU, kolor = temperatura junction, świetlna fala
  biegnąca po pierścieniu i pulsowanie = tokeny/s z llama-server.

## Wygląd

Każda sekcja to osobna „karta” z zaokrągloną ramką w swoim kolorze (GPU – róż/pomarańcz,
CPU – cyjan/fiolet, LLM – limonka, I/O – pomarańcz, procesy – fiolet), kolorową
etykietą z ikoną i lekko zabarwionym tłem. Po górnej krawędzi każdej karty co kilka
sekund przebiega błysk, a w prawym górnym rogu miga dioda aktywności (szybciej przy
większym obciążeniu sekcji; pusta ○ = brak llama-server). Paski mają gradient i jasną
końcówkę, słupki 16 wątków CPU mają opadające znaczniki szczytu, tytuł w nagłówku
mieni się kolorami. Paski i liczby płynnie interpolują między próbkami.

Jeśli tło terminala jest przezroczyste/akrylowe albo zabarwienie kart nie pasuje do
motywu, użyj `--no-tint` (lub klawisza `t`) – wtedy widać tło terminala.

Monitor tylko **czyta** pliki sysfs/procfs i log – nigdy nie zapisuje do sysfs, nie
otwiera `/dev/kfd` ani `/dev/dri` i nie wywołuje `rocm-smi`.

## Uruchomienie

```bash
python3 ~/KERNEL/monitor/reactor.py              # domyślnie 15 fps, układ 1
python3 ~/KERNEL/monitor/reactor.py --no-3d      # lżejszy tryb bez bryły 3D
python3 ~/KERNEL/monitor/reactor.py --fps 10     # inna liczba klatek na sekundę
python3 ~/KERNEL/monitor/reactor.py --layout 3   # od razu widok „core”
```

Opcje: `--fps N` (1–60), `--no-3d`, `--no-tint`, `--layout {1,2,3}`, `--log ŚCIEŻKA`
(inny log llama-server), `--duration S` (wyjście po S sekundach – do testów).

Zalecany rozmiar terminala to co najmniej **100x30** (najlepiej ok. 160x45).
Przy mniejszym oknie panele chowają wykresy, a poniżej 60x18 pojawia się komunikat.

### Przez SSH z Windows

Najlepiej użyć **Windows Terminal** (obsługuje 24-bitowe kolory i synchronizowane
odświeżanie) z czcionką zawierającą znaki braille'a i bloki, np. **Cascadia Mono**
(domyślna w Windows Terminal) lub Cascadia Code. Klasyczna konsola `powershell.exe`
(conhost) też zadziała, ale wykresy i torus mogą wyglądać gorzej. Przykład:

```powershell
ssh -t jaro@serwer "python3 ~/KERNEL/monitor/reactor.py"
```

## Klawisze

| Klawisz      | Działanie                                              |
|--------------|--------------------------------------------------------|
| `q`, Ctrl+C  | wyjście (terminal zostaje przywrócony)                 |
| `p`, spacja  | pauza animacji (dane dalej się odświeżają)             |
| `+` / `-`    | więcej / mniej klatek na sekundę (2–60)                |
| `1`          | układ „reactor”: rdzeń 3D + LLM, GPU, CPU, I/O, procesy |
| `2`          | układ „data”: bez 3D, większe wykresy LLM i I/O        |
| `3`          | układ „core”: duży torus na środku, kluczowe liczby po bokach |
| `t`          | włącz/wyłącz zabarwione tło kart                       |
| `r`          | pełne przerysowanie ekranu                             |

## Obciążenie

Rysowanie jest różnicowe (wysyłane są tylko zmienione linie), dane czytane 2 razy
na sekundę z otwartych deskryptorów (`pread`), lista procesów co 2 s. Własne zużycie
CPU jest widoczne w nagłówku (`self … cpu`). Zmierzone w terminalu 160x45 przez 20 s:
ok. 3,3–3,6% jednego rdzenia przy domyślnych ustawieniach (15 fps, 3D), ok. 1,8–2,1%
z `--no-3d`, ok. 4,5% w układzie 3 (duży torus); w oknie 100x30 odpowiednio ok. 2,2%
i 1,4%. Temperatura NVMe jest czytana co 10 s, bo jej odczyt blokuje ok. 25 ms.

## Pliki

- `reactor.py` – punkt wejścia: terminal, układy paneli, animacja, klawisze.
- `sensors.py` – odczyt sysfs/procfs i śledzenie logu llama-server.
- `gfx.py` – paleta, sekcje (karty), paski, wykresy z gradientem, duże cyfry.
- `core3d.py` – renderer torusa 3D w znakach braille'a.
