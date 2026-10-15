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
  RAM i swap.
- **Procesy**: top procesów wg CPU (z RSS).
- **I/O**: przepustowość dysków (odczyt/zapis) i sieci (pobieranie/wysyłanie).
- **LLM**: gdy działa `llama-server` – nazwa modelu (z `-m` w linii poleceń albo z logu),
  bieżące tokeny/s (z linii `print_timing ... tg_3s` w `~/qwen-opt/logs/latest.log`),
  n_gen, szczyt, ostatnie `eval` / `prompt` tok/s, średnia z 2 minut.
- **Historia**: każda kluczowa metryka ma wykres braille'owy z ostatnich ~2 minut
  (próbkowanie 2 Hz), kolorowany od zimnych (niebieski) do gorących (czerwony) wartości.
- **Rdzeń 3D**: obracający się, cieniowany torus (siatka w znakach braille'a).
  Prędkość obrotu = obciążenie GPU, kolor = temperatura junction, świetlna fala
  biegnąca po pierścieniu i pulsowanie = tokeny/s z llama-server.

Paski i liczby płynnie interpolują między próbkami. Monitor tylko **czyta** pliki
sysfs/procfs i log – nigdy nie zapisuje do sysfs, nie otwiera `/dev/kfd` ani `/dev/dri`
i nie wywołuje `rocm-smi`.

## Uruchomienie

```bash
python3 ~/KERNEL/monitor/reactor.py              # domyślnie 15 fps, układ 1
python3 ~/KERNEL/monitor/reactor.py --no-3d      # lżejszy tryb bez bryły 3D
python3 ~/KERNEL/monitor/reactor.py --fps 10     # inna liczba klatek na sekundę
python3 ~/KERNEL/monitor/reactor.py --layout 3   # od razu widok „core”
```

Opcje: `--fps N` (1–60), `--no-3d`, `--layout {1,2,3}`, `--log ŚCIEŻKA` (inny log
llama-server), `--duration S` (wyjście po S sekundach – do testów).

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
| `r`          | pełne przerysowanie ekranu                             |

## Obciążenie

Rysowanie jest różnicowe (wysyłane są tylko zmienione linie), dane czytane 2 razy
na sekundę z otwartych deskryptorów (`pread`), lista procesów co 2 s. Własne zużycie
CPU jest widoczne w nagłówku (`self … cpu`). Zmierzone w terminalu 160x45 przez 20 s:
ok. 2,5% jednego rdzenia przy domyślnych ustawieniach (15 fps, 3D), ok. 1,3–1,5%
z `--no-3d`, ok. 4% w układzie 3 (duży torus).

## Pliki

- `reactor.py` – punkt wejścia: terminal, układy paneli, animacja, klawisze.
- `sensors.py` – odczyt sysfs/procfs i śledzenie logu llama-server.
- `gfx.py` – kolory, paski, wykresy braille'owe, duże cyfry.
- `core3d.py` – renderer torusa 3D w znakach braille'a.
