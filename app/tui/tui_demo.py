#!/usr/bin/env python3
"""TUI/CLI mockup of the product: scan -> recommend -> calibrate -> result -> night.

Pure Python 3.12 standard library, raw ANSI (24-bit colour, rounded cards, braille,
block elements, big digits) in the REACTOR style (KERNEL/monitor), refined to the
design-system palette (KERNEL/app/design/tokens.css).

STATIC DEMO DATA ONLY: nothing here touches the GPU, opens device nodes or runs
a model. Every speed/telemetry number is a lab measurement with its source file:line
(registry: app/landing/src/lib/data/measurements.ts). Animations are UI simulations
and are labelled as such on screen.

Keys: 1-5 scene, Left/Right previous/next, p pause all motion, u undo (night), q quit.
Run `python3 tui_demo.py --help` for flags.
"""
import argparse
import html
import math
import os
import random
import signal
import sys
import textwrap
import time

BRAND = "Podkręt"  # single place to rename the product (mirror of landing/src/lib/brand.ts)

# ---------------------------------------------------------------- palette (tokens.css)
BG0 = (7, 8, 13)          # --bg-0 page
BG1 = (12, 14, 22)        # --bg-1 band
BG2 = (18, 21, 34)        # --bg-2 card
BG3 = (26, 30, 47)        # --bg-3 inset
LINE = (35, 40, 64)       # --line
LINE_S = (58, 65, 97)     # --line-strong
HI = (242, 245, 251)      # --text-hi
TEXT = (201, 208, 226)    # --text
MUTE = (147, 156, 183)    # --text-mute
ACC = (200, 255, 61)      # --accent (volt)
ON_ACC = (10, 13, 3)      # --on-accent
INFO = (61, 214, 255)     # --info (ion)
WARN = (255, 178, 62)     # --warn
DANGER = (255, 77, 141)   # --danger
DANGER_INK = (255, 122, 168)
OK = (91, 228, 155)       # --ok
BEFORE = (127, 137, 166)  # --before
WHITE = (255, 255, 255)

SCENES = ("scan", "recommend", "calibrate", "result", "night")
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
EIGHTHS = " ▏▎▍▌▋▊▉"
GIB = float(2 ** 30)
TOK_PER_WORD = {"pl": 2.69, "en": 1.17}   # estimator.ts TOK_PER_WORD

# ---------------------------------------------------------------- measured data (sourced)
# RX 7900 XTX, Qwen3.8-27B UD-Q4_K_XL. 38.8 and 85.6: serve_bench (NOTES.md:48);
# 109.0: spec_sweep median (STATUS-NEXT.md:10). Different measurement scripts.
T_BEFORE, T_L1, T_L3 = 38.8, 85.6, 109.0
MD5_MTP, MD5_PLAIN = "6f14e814", "c4708318"


def mix(a, b, t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def paste_code(fields):
    """Scan paste-code line with checksum (shared contract with scan scripts / web form)."""
    body = "HW1;" + ";".join("%s=%s" % kv for kv in fields)
    h = 0
    for b in body.encode("ascii"):
        h = (h * 31 + b) % 65521
    return "%s;sum=%04X" % (body, h)


SCAN_CODE = paste_code((
    ("os", "linux"), ("gpu", "Navi 31 [Radeon RX 7900 XT/7900 XTX/7900M]"),
    ("sub", "PULSE RX 7900 XTX"), ("vendor", "amd"), ("vram", "24.0"), ("ngpu", "1"),
    ("drv", "amdgpu 6.8.0-138-generic"), ("ram", "62.7"), ("thr", "16"), ("isa", "avx2"),
    ("pcie", "4x16"), ("um", "0")))

# ---------------------------------------------------------------- strings
STR = {
    "pl": {
        "tagline": "lokalne AI · demo TUI",
        "tabs": ("skan", "dobór", "kalibracja", "wynik", "noc"),
        "titles": ("Skan sprzętu", "Dobór modelu", "Kalibracja", "Przed → po", "Strojenie nocne"),
        "proto": "prototyp · dane przykładowe · bez dostępu do GPU",
        "k_scenes": "sceny", "k_switch": "zmiana", "k_pause": "pauza", "k_resume": "wznów",
        "k_undo": "cofnij", "k_quit": "wyjście",
        "paused": "WSTRZYMANO",
        "sim_ui": "symulacja interfejsu",
        "too_small": "Okno za małe: potrzeba co najmniej 60×20 znaków.",
        # scan
        "scan_card": "SKAN SPRZĘTU", "scan_sub": "tylko odczyt plików systemowych",
        "scan_rows": (
            ("GPU", "AMD Radeon RX 7900 XTX · Navi 31", "lspci, /sys/class/drm"),
            ("VRAM", "24,0 GiB", "sysfs mem_info_vram_total"),
            ("Sterownik", "amdgpu · jądro 6.8.0-138-generic", "/sys/module/amdgpu"),
            ("CPU", "AMD Ryzen 7 5700X · 16 wątków · AVX2", "/proc/cpuinfo"),
            ("RAM", "62,7 GiB", "/proc/meminfo"),
            ("PCIe", "4.0 ×16", "sysfs current_link_*"),
            ("System", "Linux", "uname"),
            ("Pamięć wspólna", "nie (osobna VRAM)", "sysfs"),
        ),
        "scan_reading": "odczyt…",
        "mem_card": "PAMIĘĆ", "mem_vram": "VRAM", "mem_ram": "RAM",
        "mem_tier": "klasa sprzętu: 20+ GiB VRAM",
        "mem_tier2": "modele do 27B w Q4 w całości na GPU",
        "priv_card": "PRYWATNOŚĆ",
        "priv_head": "nic nie zostało wysłane",
        "priv_body": "Skan działa lokalnie. Wynik zostaje na tym komputerze, dopóki sam go nie skopiujesz.",
        "priv_code": "kod do wklejenia na stronie (opcjonalnie, sprawdź przed wysłaniem):",
        # recommend
        "rec_card": "POLECANY", "alt_card": "ALTERNATYWA",
        "rec_sub": "dla RX 7900 XTX 24 GiB",
        "fit": "mieści się", "estimate": "szacunek",
        "why_main": "najlepsza jakość, która mieści się w całości w VRAM",
        "why_lfm": "najszybszy, licencja z progiem",
        "why_bielik": "po polsku",
        "file": "plik", "of": "z", "mem": "pamięć", "speed": "prędkość", "licence": "licencja",
        "measured_ours": "zmierzone na RX 7900 XTX · nasz silnik, MTP",
        "measured_lfm": "zmierzone na RX 7900 XTX · nasz silnik, serwer",
        "measured_short": "zmierzone, nasz silnik",
        "before_line": "przed: upstream llama.cpp, Vulkan, bez spekulacji",
        "soon": "wkrótce", "soon_long": "jeszcze nie zmierzone na tym GPU",
        "lfm_note": "LFM Open 1.0: komercyjnie tylko poniżej 10 mln USD rocznego przychodu; prywatnie bez ograniczeń.",
        "btn_get": "▶ pobierz i skalibruj", "btn_note": "(prototyp: przycisk nieaktywny)",
        "rec_foot": "Dobór działa lokalnie, na podstawie skanu. „wkrótce” = jeszcze niezmierzone: nie pokazujemy zgadywanych liczb.",
        # calibrate
        "cal_banner": "SYMULACJA INTERFEJSU — ta animacja nie wykonuje żadnych pomiarów",
        "cal_card": "KALIBRACJA", "cal_sub": "Qwen3.8-27B UD-Q4_K_XL",
        "cal_steps": (
            ("L0 naprawy", "usypianie GPU (BACO), model na CPU, wyciek VRAM do RAM"),
            ("dopasowanie pamięci", "model + kontekst w całości w VRAM"),
            ("backend", "Vulkan czy ROCm: krótki test na tym sprzęcie"),
            ("koszt spekulacji", "czy MTP się opłaca: akceptacja vs koszt weryfikacji"),
            ("samotest logitów", "porównanie z referencją: KLD i greedy md5"),
            ("bazowa A/A", "dwa identyczne przebiegi wyznaczają szum pomiaru"),
        ),
        "st_done": "gotowe", "st_run": "trwa", "st_wait": "czeka",
        "progress": "postęp",
        "how_card": "UCZCIWY POMIAR",
        "how": (
            ("A/A", "dwa takie same przebiegi: ile wynosi szum"),
            ("ABBA", "przeplatane przed/po: dopiero wtedy przedział ufności"),
            ("KLD", "zmiana dopuszczona tylko, gdy logity zostają w szumie"),
            ("md5", "greedy md5 porównany z referencją"),
            ("L0", "u nas uśpione GPU dawało 4,4 zamiast 92 t/s (NOTES.md:124)"),
        ),
        # result
        "res_card": "PRZED → PO", "res_sub": "ten sam sprzęt · ten sam model",
        "res_over": "Qwen3.8-27B UD-Q4_K_XL · RX 7900 XTX 24 GiB",
        "cap_before": "upstream · Vulkan · bez spekulacji",
        "cap_after": "nasz silnik · ROCm · MTP",
        "bars": ("przed · upstream, Vulkan, bez spekulacji", "L1 · upstream, Vulkan, MTP n=4",
                 "L3 · nasz silnik, ROCm, 70 łatek, MTP"),
        "bars_short": ("przed · upstream Vulkan", "L1 · + MTP n=4", "L3 · nasz silnik"),
        "words_card": "SŁOWA NA SEKUNDĘ", "words_sub": "przeliczone z t/s",
        "col_before": "przed", "col_l1": "L1", "col_l3": "L3",
        "wps": "słowa/s %s", "w500": "500 słów %s",
        "tpw": "tokenów na słowo: PL 2,69 · EN 1,17",
        "layers_card": "WARSTWY",
        "layers": (
            ("L0", "naprawy", None, "nic do naprawy"),
            ("L1", "konfiguracja", T_L1 - T_BEFORE, "MTP n=4"),
            ("L2", "noc", None, "wkrótce"),
            ("L3", "przepis", T_L3 - T_L1, "nasz silnik"),
        ),
        "honest_card": "UCZCIWOŚĆ",
        "ci": "przedział ufności: po kalibracji ABBA",
        "md5": "greedy md5: MTP %s… · bez spekulacji %s… — spekulacja zmienia wynik greedy (także w upstream); tryb bit w bit: w badaniach" % (MD5_MTP, MD5_PLAIN),
        "mix_note": "85,6: mieszanka promptów EN+PL (NOTES.md:50)",
        "sources": "źródła: KERNEL/qwen-opt/NOTES.md:48, STATUS-NEXT.md:10; 38.8 i 109.0 z różnych skryptów pomiarowych",
        # night
        "night_card": "NOC · STROJENIE L2", "night_sub": "Qwen3.8-27B · RX 7900 XTX",
        "layout_ex": "przykład układu",
        "running": "trwa strojenie",
        "trial": "próba %d z %d",
        "cond": ("zasilanie sieciowe (AC)", "komputer bezczynny", "temperatury w zakresie"),
        "night_rule": "Każda zmiana przechodzi samotest logitów; odrzucone nie trafiają do profilu. Rano: raport przed → po.",
        "tele_card": "TELEMETRIA", "tele_sub": "symulacja",
        "metrics": ("generowanie", "junction", "edge", "moc", "wentylatory"),
        "tele_note": "symulacja: drobny szum wokół wartości obserwowanych · 109,0 t/s (STATUS-NEXT.md:10) · 284 W, junction 85–88 °C, edge 64–67 °C, ~1850 RPM (NOTES.md:146)",
        "log_card": "DZIENNIK",
        "log": (
            ("ok", "przyjęto", "długość draftu MTP dopasowana do Twoich tekstów"),
            ("bad", "odrzucono", "wariant kernela: nie przeszedł samotestu logitów"),
            ("run", "trwa", "wariant kernela mul_mat_vec, kolumny 2–8"),
            ("wait", "czeka", "rozmiar ubatch przy długim kontekście"),
        ),
        "undone": "cofnięto ostatnią przyjętą zmianę (symulacja)",
        # plain
        "plain_head": "%s · tryb tekstowy (czytnik ekranu / log) · dane przykładowe, bez dostępu do GPU",
        "plain_scene": "Scena %d z 5: %s",
    },
    "en": {
        "tagline": "local AI · TUI demo",
        "tabs": ("scan", "pick", "calibrate", "result", "night"),
        "titles": ("Hardware scan", "Model pick", "Calibration", "Before → after", "Overnight tuning"),
        "proto": "prototype · sample data · no GPU access",
        "k_scenes": "scenes", "k_switch": "switch", "k_pause": "pause", "k_resume": "resume",
        "k_undo": "undo", "k_quit": "quit",
        "paused": "PAUSED",
        "sim_ui": "UI simulation",
        "too_small": "Window too small: need at least 60×20 characters.",
        "scan_card": "HARDWARE SCAN", "scan_sub": "reads system files only",
        "scan_rows": (
            ("GPU", "AMD Radeon RX 7900 XTX · Navi 31", "lspci, /sys/class/drm"),
            ("VRAM", "24.0 GiB", "sysfs mem_info_vram_total"),
            ("Driver", "amdgpu · kernel 6.8.0-138-generic", "/sys/module/amdgpu"),
            ("CPU", "AMD Ryzen 7 5700X · 16 threads · AVX2", "/proc/cpuinfo"),
            ("RAM", "62.7 GiB", "/proc/meminfo"),
            ("PCIe", "4.0 ×16", "sysfs current_link_*"),
            ("OS", "Linux", "uname"),
            ("Unified memory", "no (dedicated VRAM)", "sysfs"),
        ),
        "scan_reading": "reading…",
        "mem_card": "MEMORY", "mem_vram": "VRAM", "mem_ram": "RAM",
        "mem_tier": "hardware class: 20+ GiB VRAM",
        "mem_tier2": "models up to 27B at Q4 fully on the GPU",
        "priv_card": "PRIVACY",
        "priv_head": "nothing was sent",
        "priv_body": "The scan runs locally. The result stays on this computer unless you copy it yourself.",
        "priv_code": "code to paste on the website (optional, review before sending):",
        "rec_card": "RECOMMENDED", "alt_card": "ALTERNATIVE",
        "rec_sub": "for RX 7900 XTX 24 GiB",
        "fit": "fits", "estimate": "estimate",
        "why_main": "best quality that fits entirely in VRAM",
        "why_lfm": "fastest, licence with a threshold",
        "why_bielik": "for Polish",
        "file": "file", "of": "of", "mem": "memory", "speed": "speed", "licence": "licence",
        "measured_ours": "measured on RX 7900 XTX · our engine, MTP",
        "measured_lfm": "measured on RX 7900 XTX · our engine, server",
        "measured_short": "measured, our engine",
        "before_line": "before: upstream llama.cpp, Vulkan, no speculation",
        "soon": "soon", "soon_long": "not yet measured on this GPU",
        "lfm_note": "LFM Open 1.0: commercial use only below USD 10M annual revenue; no limits for private use.",
        "btn_get": "▶ download and calibrate", "btn_note": "(prototype: button inactive)",
        "rec_foot": "The pick runs locally, from the scan. “soon” = not measured yet: we never show guessed numbers.",
        "cal_banner": "UI SIMULATION — this animation does not measure anything",
        "cal_card": "CALIBRATION", "cal_sub": "Qwen3.8-27B UD-Q4_K_XL",
        "cal_steps": (
            ("L0 fixes", "GPU sleep (BACO), model on CPU, VRAM spilling to RAM"),
            ("memory fit", "model + context entirely in VRAM"),
            ("backend", "Vulkan or ROCm: a short test on this hardware"),
            ("speculation cost", "does MTP pay off: acceptance vs verification cost"),
            ("logit self-test", "compare with the reference: KLD and greedy md5"),
            ("A/A baseline", "two identical runs give the measurement noise"),
        ),
        "st_done": "done", "st_run": "running", "st_wait": "queued",
        "progress": "progress",
        "how_card": "HONEST MEASUREMENT",
        "how": (
            ("A/A", "two identical runs: how big is the noise"),
            ("ABBA", "interleaved before/after: only then a confidence interval"),
            ("KLD", "a change is accepted only if logits stay within noise"),
            ("md5", "greedy md5 compared with the reference"),
            ("L0", "in our lab a sleeping GPU gave 4.4 instead of 92 t/s (NOTES.md:124)"),
        ),
        "res_card": "BEFORE → AFTER", "res_sub": "same hardware · same model",
        "res_over": "Qwen3.8-27B UD-Q4_K_XL · RX 7900 XTX 24 GiB",
        "cap_before": "upstream · Vulkan · no speculation",
        "cap_after": "our engine · ROCm · MTP",
        "bars": ("before · upstream, Vulkan, no speculation", "L1 · upstream, Vulkan, MTP n=4",
                 "L3 · our engine, ROCm, 70 patches, MTP"),
        "bars_short": ("before · upstream Vulkan", "L1 · + MTP n=4", "L3 · our engine"),
        "words_card": "WORDS PER SECOND", "words_sub": "converted from t/s",
        "col_before": "before", "col_l1": "L1", "col_l3": "L3",
        "wps": "words/s %s", "w500": "500 words %s",
        "tpw": "tokens per word: PL 2.69 · EN 1.17",
        "layers_card": "LAYERS",
        "layers": (
            ("L0", "fixes", None, "nothing to fix"),
            ("L1", "configuration", T_L1 - T_BEFORE, "MTP n=4"),
            ("L2", "night", None, "soon"),
            ("L3", "recipe", T_L3 - T_L1, "our engine"),
        ),
        "honest_card": "HONESTY",
        "ci": "confidence interval: after ABBA calibration",
        "md5": "greedy md5: MTP %s… · no speculation %s… — speculation changes the greedy output (upstream too); bit-exact mode: in research" % (MD5_MTP, MD5_PLAIN),
        "mix_note": "85.6: mixed EN+PL prompts (NOTES.md:50)",
        "sources": "sources: KERNEL/qwen-opt/NOTES.md:48, STATUS-NEXT.md:10; 38.8 and 109.0 come from different measurement scripts",
        "night_card": "NIGHT · L2 TUNING", "night_sub": "Qwen3.8-27B · RX 7900 XTX",
        "layout_ex": "layout example",
        "running": "tuning in progress",
        "trial": "trial %d of %d",
        "cond": ("on AC power", "computer idle", "temperatures in range"),
        "night_rule": "Every change passes the logit self-test; rejected ones never enter the profile. In the morning: a before → after report.",
        "tele_card": "TELEMETRY", "tele_sub": "simulation",
        "metrics": ("generation", "junction", "edge", "power", "fans"),
        "tele_note": "simulation: small noise around observed values · 109.0 t/s (STATUS-NEXT.md:10) · 284 W, junction 85–88 °C, edge 64–67 °C, ~1850 RPM (NOTES.md:146)",
        "log_card": "LOG",
        "log": (
            ("ok", "accepted", "MTP draft length matched to your texts"),
            ("bad", "rejected", "kernel variant: failed the logit self-test"),
            ("run", "running", "mul_mat_vec kernel variant, columns 2–8"),
            ("wait", "queued", "ubatch size for long context"),
        ),
        "undone": "undid the last accepted change (simulation)",
        "plain_head": "%s · text mode (screen reader / log) · sample data, no GPU access",
        "plain_scene": "Scene %d of 5: %s",
    },
}

LANG = "pl"
S = STR["pl"]


def fmt(v, d=1):
    s = "%.*f" % (d, v)
    return s.replace(".", ",") if LANG == "pl" else s


def ease(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return 1 - (1 - t) ** 3


# ---------------------------------------------------------------- canvas
class Canvas:
    """Cell grid (char, fg, bg, bold); renders to ANSI, monochrome text or HTML."""

    def __init__(self, w, h, color=True):
        self.w, self.h, self.color = w, h, color
        self.cells = [[[" ", TEXT, BG0, False] for _ in range(w)] for _ in range(h)]

    def put(self, x, y, s, fg=TEXT, bg=None, bold=False, maxw=None):
        """Write s at (x, y); bg None keeps the existing background. Returns end x."""
        if maxw is not None and len(s) > maxw:
            s = s[:max(0, maxw - 1)] + "…" if maxw > 0 else ""
        if y < 0 or y >= self.h:
            return x + len(s)
        row = self.cells[y]
        for i, ch in enumerate(s):
            cx = x + i
            if 0 <= cx < self.w:
                c = row[cx]
                c[0] = ch
                c[1] = fg
                if bg is not None:
                    c[2] = bg
                c[3] = bold
        return x + len(s)

    def fill(self, x, y, w, h, bg):
        for yy in range(max(0, y), min(self.h, y + h)):
            row = self.cells[yy]
            for xx in range(max(0, x), min(self.w, x + w)):
                row[xx][0] = " "
                row[xx][2] = bg

    def bg_at(self, x, y):
        if 0 <= y < self.h and 0 <= x < self.w:
            return self.cells[y][x][2]
        return BG0

    def ansi_rows(self):
        rows = []
        for row in self.cells:
            if not self.color:
                rows.append("".join(c[0] for c in row).rstrip())
                continue
            out, last = [], None
            for ch, f, b, bold in row:
                key = (f, b, bold)
                if key != last:
                    out.append("\x1b[%s;38;2;%d;%d;%d;48;2;%d;%d;%dm"
                               % ("1" if bold else "22", f[0], f[1], f[2], b[0], b[1], b[2]))
                    last = key
                out.append(ch)
            out.append("\x1b[0m")
            rows.append("".join(out))
        return rows

    def html(self, title, lang):
        lines = []
        for row in self.cells:
            out, run, key = [], [], None
            for ch, f, b, bold in row:
                k = (f, b, bold) if self.color else None
                if k != key and run:
                    out.append(_span(key, "".join(run)))
                    run = []
                key = k
                run.append(ch)
            if run:
                out.append(_span(key, "".join(run)))
            lines.append("".join(out))
        return HTML_DOC % {"lang": lang, "title": html.escape(title), "body": "\n".join(lines)}


def _hex(c):
    return "#%02x%02x%02x" % c


def _span(key, text):
    t = html.escape(text, quote=False)
    if key is None:
        return t
    f, b, bold = key
    st = "color:" + _hex(f)
    if b != BG0:
        st += ";background:" + _hex(b)
    if bold:
        st += ";font-weight:600"
    return '<span style="%s">%s</span>' % (st, t)


HTML_DOC = """<!doctype html>
<html lang="%(lang)s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>
html,body{margin:0;background:#07080d;color:#c9d0e2}
body{display:flex;justify-content:center;padding:24px}
pre{margin:0;font-family:'Geist Mono',ui-monospace,monospace;font-size:14px;line-height:1.2;
font-variant-ligatures:none;letter-spacing:0;tab-size:4}
</style>
</head>
<body>
<pre>%(body)s</pre>
</body>
</html>
"""


# ---------------------------------------------------------------- widgets
def card(cv, x, y, w, h, title, acc, sub="", glint=None, tint=0.055):
    """Rounded card with a coloured title chip; returns the interior rect (x, y, w, h)."""
    if w < 8 or h < 3:
        return (x, y, 0, 0)
    tbg = mix(BG2, acc, tint)
    cv.fill(x + 1, y + 1, w - 2, h - 2, tbg)
    if not cv.color:
        cv.put(x, y, "╭─ " + title + " " + "─" * max(0, w - 5 - len(title)) + "╮")
        for i in range(1, h - 1):
            cv.put(x, y + i, "│")
            cv.put(x + w - 1, y + i, "│")
        cv.put(x, y + h - 1, "╰" + "─" * (w - 2) + "╯")
        if sub and len(title) + len(sub) + 10 < w:
            cv.put(x + w - 4 - len(sub), y, " " + sub + " ")
        return (x + 2, y + 1, w - 4, h - 2)
    cv.put(x, y, "╭─", acc, BG0)
    chip = " " + title + " "
    chip = chip[:max(0, w - 6)]
    cx = cv.put(x + 2, y, chip, ON_ACC, acc, bold=True)
    tail = " " + sub + " " if sub else ""
    fill = x + w - 3 - cx - len(tail)
    if fill < 2:
        tail, fill = "", x + w - 3 - cx
    for j in range(max(0, fill)):
        c = mix(acc, LINE_S, 0.25 + 0.6 * j / max(1, fill))
        if glint is not None:
            k = 1.0 - abs(j - glint * (fill + 10) + 5) / 4.0
            if k > 0:
                c = mix(c, WHITE, 0.8 * k)
        cv.put(cx + j, y, "─", c, BG0)
    if tail:
        cv.put(cx + fill, y, tail, MUTE, BG0)
    cv.put(x + w - 3, y, "─", LINE_S, BG0)
    cv.put(x + w - 2, y, "●", acc, BG0)
    cv.put(x + w - 1, y, "╮", LINE_S, BG0)
    for i in range(1, h - 1):
        c = mix(acc, LINE_S, i / max(1, h - 1) * 1.3)
        cv.put(x, y + i, "│", c, BG0)
        cv.put(x + w - 1, y + i, "│", mix(LINE_S, LINE, 0.4), BG0)
    cv.put(x, y + h - 1, "╰" + "─" * (w - 2) + "╯", LINE_S, BG0)
    return (x + 2, y + 1, w - 4, h - 2)


def hbar(cv, x, y, w, frac, col, col2=None):
    """Smooth horizontal bar (eighth blocks) on a tinted track; optional gradient."""
    if w <= 0:
        return
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
    units = int(round(frac * w * 8))
    full, rem = divmod(units, 8)
    under = cv.bg_at(x, y)
    track = mix(under, col, 0.14)
    for i in range(w):
        c = mix(col, col2, i / max(1, w - 1)) if col2 else col
        if i < full:
            cv.put(x + i, y, "█", c, track)
        elif i == full and rem:
            cv.put(x + i, y, EIGHTHS[rem], c, track)
        else:
            cv.put(x + i, y, " " if cv.color else "·", MUTE, track)


def tag(cv, x, y, text, col, maxw=None):
    """Small badge: soft tinted background with coloured ink."""
    s = " " + text + " "
    if maxw is not None and len(s) > maxw:
        return x
    if not cv.color:
        return cv.put(x, y, "[" + text + "]") + 1
    return cv.put(x, y, s, col, mix(cv.bg_at(x, y), col, 0.16), bold=True) + 1


def keycap(cv, x, y, key, label):
    if not cv.color:
        return cv.put(x, y, "[%s] %s  " % (key, label))
    x = cv.put(x, y, " " + key + " ", HI, BG3, bold=True)
    return cv.put(x, y, " " + label + "   ", MUTE)


def wrap(text, w):
    return textwrap.wrap(text, max(8, w)) or [""]


# 3x5 pixel font for the hero numbers
FONT = {
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"), "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "111"),
    ".": ("0", "0", "0", "0", "1"), ",": ("0", "0", "0", "1", "1"), " ": ("0", "0", "0", "0", "0"),
}
HALF = {("1", "1"): "█", ("1", "0"): "▀", ("0", "1"): "▄", ("0", "0"): " "}


def big_width(s, size):
    g = [FONT.get(ch, FONT[" "]) for ch in s]
    if size == 1:
        return sum(len(x[0]) + 1 for x in g) - 1
    return sum(2 * len(x[0]) + 2 for x in g) - 2


def big(cv, x, y, s, col, size=1):
    """Pixel-font number; size 1 = 3 rows (half blocks), size 2 = 5 rows double width.
    Glossy top: upper rows are mixed towards white. Returns width."""
    glyphs = [FONT.get(ch, FONT[" "]) for ch in s]
    if size == 1:
        gloss = (0.35, 0.1, 0.0)
        for pr in range(3):
            cx = x
            for g in glyphs:
                top = g[pr * 2]
                bot = g[pr * 2 + 1] if pr * 2 + 1 < 5 else "0" * len(top)
                cv.put(cx, y + pr, "".join(HALF[(top[i], bot[i])] for i in range(len(top))),
                       mix(col, WHITE, gloss[pr]))
                cx += len(top) + 1
    else:
        gloss = (0.45, 0.25, 0.1, 0.0, 0.0)
        for pr in range(5):
            cx = x
            for g in glyphs:
                cv.put(cx, y + pr, "".join("██" if p == "1" else "  " for p in g[pr]),
                       mix(col, WHITE, gloss[pr]))
                cx += 2 * len(g[pr]) + 2
    return big_width(s, size)


def spark(cv, x, y, w, h, vals, lo, hi, col):
    """Braille area graph: w cells × h rows, two samples per cell, filled to the bottom."""
    n = 2 * w
    vals = vals[-n:]
    if len(vals) < n:
        vals = [vals[0]] * (n - len(vals)) + vals
    dots = 4 * h
    lv = [max(1, min(dots, int(round((v - lo) / (hi - lo) * dots)))) for v in vals]
    bits_l, bits_r = (0x01, 0x02, 0x04, 0x40), (0x08, 0x10, 0x20, 0x80)
    for cy in range(h):
        c = mix(col, WHITE, 0.25) if cy == 0 else mix(col, cv.bg_at(x, y + cy), 0.25 * cy / max(1, h))
        row = []
        for cx in range(w):
            b = 0
            for r in range(4):
                g = cy * 4 + r
                if g >= dots - lv[2 * cx]:
                    b |= bits_l[r]
                if g >= dots - lv[2 * cx + 1]:
                    b |= bits_r[r]
            row.append(chr(0x2800 + b))
        cv.put(x, y + cy, "".join(row), c)


def noise(seed, k):
    """Smooth deterministic noise in [-1, 1] (cosine interpolation of seeded knots)."""
    i, f = divmod(k / 6.0, 1.0)
    a = random.Random(seed * 1000003 + int(i)).random()
    b = random.Random(seed * 1000003 + int(i) + 1).random()
    t = (1 - math.cos(f * math.pi)) / 2
    return (a + (b - a) * t) * 2 - 1


# ---------------------------------------------------------------- scenes
class State:
    def __init__(self, t, paused=False, undo_t=None, anim=True):
        self.t, self.paused, self.undo_t, self.anim = t, paused, undo_t, anim


def code_chunks(code, w):
    """Wrap the paste code at ';' boundaries without altering a single character."""
    parts = code.split(";")
    pieces = [p + ";" for p in parts[:-1]] + [parts[-1]]
    out, cur = [], ""
    for piece in pieces:
        if cur and len(cur) + len(piece) > w:
            out.append(cur)
            cur = ""
        cur += piece
    out.append(cur)
    return [ln[i:i + w] for ln in out for i in range(0, len(ln), w)]


def scene_scan(cv, X, Y, W, H, st):
    rows = S["scan_rows"]
    wide = W >= 100
    reveal = (lambda i: True) if not st.anim else (lambda i: st.t >= 0.3 * (i + 1))
    glint = (st.t % 7.0) / 1.6 if st.anim and st.t % 7.0 < 1.6 else None
    code_lines = code_chunks(SCAN_CODE, W - 4)
    body_lines = [] if wide else wrap(S["priv_body"], W - 4)
    roomy = H >= 26
    priv_h = 2 + 2 + len(body_lines) + len(code_lines) + (2 if roomy else 0)
    vgap = 1 if H >= 22 else 0
    inv_h = H - priv_h - vgap
    inv_w = int(W * 0.62) if wide else W
    ix, iy, iw, ih = card(cv, X, Y, inv_w, inv_h, S["scan_card"], INFO, S["scan_sub"], glint)
    lw = max(len(r[0]) for r in rows) + 2
    gap = 1 if ih >= 2 * len(rows) else 0
    top = iy + (1 if ih > len(rows) + gap * len(rows) else 0)
    for i, (lab, val, src) in enumerate(rows):
        yy = top + i * (1 + gap)
        if yy >= iy + ih:
            break
        if reveal(i):
            cv.put(ix, yy, "✓", OK, bold=True)
            cv.put(ix + 2, yy, lab, MUTE)
            end = cv.put(ix + 2 + lw, yy, val, HI, bold=(i in (0, 3)), maxw=iw - lw - 2)
            if wide and end + len(src) + 3 < ix + iw:
                cv.put(ix + iw - len(src), yy, src, mix(MUTE, LINE_S, 0.35))
        else:
            cv.put(ix, yy, SPIN[int(st.t * 12) % len(SPIN)], INFO)
            cv.put(ix + 2, yy, lab, MUTE)
            cv.put(ix + 2 + lw, yy, S["scan_reading"], mix(MUTE, LINE_S, 0.4))
    if wide:
        mx_, my, mw, mh = card(cv, X + inv_w + 1, Y, W - inv_w - 1, inv_h, S["mem_card"], ACC)
        size = 2 if mh >= 16 and mw >= 30 else 1
        bh = 5 if size == 2 else 3
        yy = my + 1
        for lab, val, col in ((S["mem_vram"], fmt(24.0), ACC), (S["mem_ram"], fmt(62.7), TEXT)):
            if yy + bh + 1 > my + mh:
                break
            cv.put(mx_, yy, lab, MUTE)
            bw = big(cv, mx_, yy + 1, val, col, size)
            cv.put(mx_ + bw + 2, yy + bh, "GiB", MUTE)
            yy += bh + 2
        if yy + 1 < my + mh:
            cv.put(mx_, yy, S["mem_tier"], TEXT, maxw=mw)
            cv.put(mx_, yy + 1, S["mem_tier2"], MUTE, maxw=mw)
    py = Y + inv_h + vgap
    px, pyy, pw, ph = card(cv, X, py, W, min(priv_h, Y + H - py), S["priv_card"], OK)
    hx = cv.put(px, pyy, "✓ " + S["priv_head"], OK, bold=True)
    if wide:
        cv.put(hx + 2, pyy, S["priv_body"], TEXT, maxw=px + pw - hx - 2)
    yy = pyy + 1
    for ln in body_lines:
        cv.put(px, yy, ln, TEXT, maxw=pw)
        yy += 1
    yy += 1 if roomy else 0
    cv.put(px, yy, S["priv_code"], MUTE, maxw=pw)
    for i, ln in enumerate(code_lines):
        if yy + 1 + i < pyy + ph:
            cv.put(px, yy + 1 + i, ln, INFO, maxw=pw)


def model_block(cv, x, y, w, h, m, compact):
    """Contents of one model card."""
    name_end = cv.put(x, y, m["name"], HI, bold=True)
    cv.put(name_end + 1, y, m["quant"], MUTE)
    fit = "● " + S["fit"]
    cv.put(x + w - len(fit), y, fit, OK, bold=True)
    yy = y + 1
    tx = tag(cv, x, yy, m["why"], m["why_col"])
    tx = tag(cv, tx, yy, m["lic"], m["lic_col"], maxw=x + w - tx)
    if m.get("mtp") and tx + 6 < x + w:
        tag(cv, tx, yy, "MTP", INFO)
    yy += 1 if compact else 2
    gib = m["gb"] * 1e9 / GIB
    lab = "%s %s GB · %s %s %s GiB · %s" % (S["file"], fmt(m["gb"], 2), fmt(gib), S["of"], fmt(24.0),
                                            S["estimate"])
    lw = 9 if not compact else 0
    if not compact:
        cv.put(x, yy, S["mem"], MUTE)
    bw = max(6, min(36, w - lw - len(lab) - 2))
    if lw + bw + len(lab) + 2 > w:
        lab = "%s GB · %s GiB" % (fmt(m["gb"], 2), fmt(gib))
        bw = max(6, w - lw - len(lab) - 2)
    hbar(cv, x + lw, yy, bw, gib / 24.0, m["bar"])
    cv.put(x + lw + bw + 2, yy, lab, TEXT, maxw=w - lw - bw - 2)
    yy += 1
    if yy >= y + h:
        return
    if not compact:
        cv.put(x, yy, S["speed"], MUTE)
    sx = x + lw
    if m["tps"] is None:
        sx = tag(cv, sx, yy, S["soon"], WARN)
        cv.put(sx, yy, S["soon_long"], MUTE, maxw=x + w - sx)
    else:
        sx = cv.put(sx, yy, fmt(m["tps"]) + " t/s", ACC, bold=True) + 2
        note = m["tps_short"] if compact else m["tps_note"]
        if sx + len(note) <= x + w or compact:
            cv.put(sx, yy, note, MUTE, maxw=x + w - sx)
        else:
            for ln in wrap(note, x + w - sx):
                if yy >= y + h:
                    return
                cv.put(sx, yy, ln, MUTE)
                yy += 1
            yy -= 1
    yy += 1
    for extra, col in m.get("extra", ()):
        if yy >= y + h:
            return
        for ln in wrap(extra, w - lw):
            if yy >= y + h:
                return
            cv.put(x + lw, yy, ln, col, maxw=w - lw)
            yy += 1


def rec_models():
    return (
        {"name": "Qwen3.8-27B", "quant": "UD-Q4_K_XL", "gb": 17.56, "why": S["why_main"],
         "why_col": ACC, "lic": "Apache-2.0", "lic_col": OK, "mtp": True, "bar": ACC,
         "tps": T_L3, "tps_note": S["measured_ours"] + " · STATUS-NEXT.md:10",
         "tps_short": S["measured_short"] + " · STATUS-NEXT.md:10",
         "extra": ((S["before_line"] + ": " + fmt(T_BEFORE) + " t/s · NOTES.md:48", MUTE),)},
        {"name": "LFM2.5-24B-A2B", "quant": "Q5_K_M", "gb": 17.03, "why": S["why_lfm"],
         "why_col": WARN, "lic": "LFM Open 1.0", "lic_col": WARN, "bar": INFO,
         "tps": 293.7, "tps_note": S["measured_lfm"] + " · STATUS-NEXT.md:12",
         "tps_short": S["measured_short"] + " · STATUS-NEXT.md:12",
         "extra": ((S["lfm_note"], WARN),)},
        {"name": "Bielik-11B v3", "quant": "Q8_0", "gb": 11.87, "why": S["why_bielik"],
         "why_col": INFO, "lic": "Apache-2.0", "lic_col": OK, "bar": INFO, "tps": None},
    )


def scene_recommend(cv, X, Y, W, H, st):
    ms = rec_models()
    glint = (st.t % 7.0) / 1.6 if st.anim and st.t % 7.0 < 1.6 else None
    wide = W >= 100 and H >= 26
    if wide:
        ph = 11
        x, y, w, h = card(cv, X, Y, W, ph, S["rec_card"], ACC, S["rec_sub"], glint, tint=0.07)
        model_block(cv, x, y, w, h - 2, ms[0], False)
        bx = cv.put(x + 9, y + h - 1, " " + S["btn_get"] + " ", ON_ACC, ACC, bold=True) \
            if cv.color else cv.put(x + 9, y + h - 1, "[" + S["btn_get"] + "]")
        cv.put(bx + 2, y + h - 1, S["btn_note"], MUTE)
        ay = Y + ph + 1
        ah = min(11, H - ph - 3)
        aw = (W - 1) // 2
        for i, m in enumerate(ms[1:]):
            x, y, w, h = card(cv, X + i * (aw + 1), ay, aw if i == 0 else W - aw - 1, ah,
                              S["alt_card"], m["why_col"])
            model_block(cv, x, y, w, h, m, False)
        fy = ay + ah + 1
        for i, ln in enumerate(wrap(S["rec_foot"], W)):
            if fy + i < Y + H:
                cv.put(X, fy + i, ln, MUTE)
    else:
        heights = (6, 6, 6)
        y0 = Y
        for i, m in enumerate(ms):
            hh = heights[i]
            if y0 + hh > Y + H:
                break
            x, y, w, h = card(cv, X, y0, W, hh, S["rec_card"] if i == 0 else S["alt_card"],
                              ACC if i == 0 else m["why_col"], S["rec_sub"] if i == 0 else "",
                              glint if i == 0 else None)
            model_block(cv, x, y, w, h, m, True)
            y0 += hh + (1 if H >= 20 else 0)


CAL_STEP = 2.2


def scene_calibrate(cv, X, Y, W, H, st):
    steps = S["cal_steps"]
    n = len(steps)
    total = n * CAL_STEP
    t = st.t % (total + 2.5)
    banner = "▲ " + S["cal_banner"]
    if cv.color:
        cv.fill(X, Y, W, 1, mix(BG0, WARN, 0.12))
    cv.put(X + 1, Y, banner, WARN, bold=True, maxw=W - 2)
    wide = W >= 100
    cw = int(W * 0.62) if wide else W
    ch = H - 2
    x, y, w, h = card(cv, X, Y + 2, cw, ch, S["cal_card"], ACC, S["cal_sub"])
    per = max(1, min(4, (h - 3) // n))
    yy = y + 1
    nlab = max(len(s[0]) for s in steps) + 2
    for i, (lab, desc) in enumerate(steps):
        p = (t - i * CAL_STEP) / CAL_STEP
        if p >= 1:
            icon, icol, state, scol = "✓", OK, S["st_done"], OK
        elif p >= 0:
            icon, icol, state, scol = SPIN[int(st.t * 12) % len(SPIN)], ACC, S["st_run"], ACC
        else:
            icon, icol, state, scol = "·", LINE_S, S["st_wait"], MUTE
        running = 0 <= p < 1
        cv.put(x, yy, icon, icol, bold=True)
        cv.put(x + 2, yy, "%d/%d" % (i + 1, n), MUTE)
        cv.put(x + 6, yy, lab, HI if p >= 0 else TEXT, bold=running)
        dx = x + 6 + nlab
        if running:
            bw = max(6, min(24, w - nlab - 6 - len(state) - 8))
            hbar(cv, dx, yy, bw, p, ACC)
            cv.put(dx + bw + 1, yy, "%3d%%" % int(p * 100), ACC)
        elif per == 1:
            cv.put(dx, yy, desc, MUTE, maxw=x + w - dx - len(state) - 2)
        cv.put(x + w - len(state), yy, state, scol)
        if per >= 2:
            cv.put(x + 6, yy + 1, desc, TEXT if running else MUTE, maxw=w - 6 - len(state) - 2)
        yy += per
    frac = min(1.0, t / total)
    yy = y + h - 1
    cv.put(x, yy, S["progress"], MUTE)
    pl = len(S["progress"]) + 1
    tail = "%3d%% · %s" % (int(frac * 100), S["sim_ui"])
    hbar(cv, x + pl, yy, w - pl - len(tail) - 2, frac, INFO, ACC)
    cv.put(x + w - len(tail), yy, tail, MUTE)
    if wide:
        x2, y2, w2, h2 = card(cv, X + cw + 1, Y + 2, W - cw - 1, ch, S["how_card"], INFO)
        yy = y2 + 1
        for k, v in S["how"]:
            lines = wrap(v, w2 - 6)
            if yy + len(lines) > y2 + h2:
                break
            cv.put(x2, yy, k, INFO, bold=True)
            for ln in lines:
                cv.put(x2 + 6, yy, ln, TEXT)
                yy += 1
            yy += 1


def scene_result(cv, X, Y, W, H, st):
    grow = ease(st.t / 1.2) if st.anim else 1.0
    wide = W >= 100 and H >= 30
    size = 2 if wide else 1
    bh = 5 if size == 2 else 3
    hero_h = 2 + 1 + bh + (1 if wide else 0) + 1 + 3 + (1 if wide else 0)
    x, y, w, h = card(cv, X, Y, W, hero_h, S["res_card"], ACC, S["res_sub"],
                      tint=0.065)
    cv.put(x, y, S["res_over"], MUTE, maxw=w)
    yy = y + 1 + (1 if wide else 0)
    b_txt, a_txt = fmt(T_BEFORE), fmt(T_L3)
    bx = x + 1
    bw = big(cv, bx, yy, b_txt, BEFORE, size)
    cv.put(bx + bw + 1, yy + bh - 1, "t/s", MUTE)
    if wide:
        cv.put(bx, yy + bh, S["cap_before"], MUTE)
    ax = bx + max(bw + 6, len(S["cap_before"]) + 3 if wide else 0)
    cv.put(ax, yy + bh // 2, "──▶", ACC, bold=True)
    ax += 5
    aw = big(cv, ax, yy, a_txt, ACC, size)
    cv.put(ax + aw + 1, yy + bh - 1, "t/s", ACC)
    if wide:
        cv.put(ax, yy + bh, S["cap_after"], TEXT)
    yy += bh + (2 if wide else 1)
    labs = S["bars"] if w >= 100 else S["bars_short"]
    lw = min(max(len(s) for s in labs) + 1, w // 2 - 4)
    vw = 12
    barw = w - lw - vw
    vmax = T_L3 * 1.04
    for i, (lab, v, col) in enumerate(zip(labs, (T_BEFORE, T_L1, T_L3), (BEFORE, INFO, ACC))):
        cv.put(x, yy + i, lab, TEXT if i else MUTE, maxw=lw - 1)
        hbar(cv, x + lw, yy + i, barw, v / vmax * grow, col)
        cv.put(x + lw + barw + 1, yy + i, "%6s t/s" % fmt(v), col if i else TEXT, bold=(i == 2))
    by = Y + hero_h + (1 if wide else 0)
    tpw = TOK_PER_WORD
    seq = (T_BEFORE, T_L1, T_L3)
    if wide:
        ww = int(W * 0.5)
        bh2 = 8
        x, y, w, h = card(cv, X, by, ww, bh2, S["words_card"], INFO, S["words_sub"])
        c0 = max(len(S["wps"] % "PL"), len(S["w500"] % "PL")) + 2
        cols = (S["col_before"], S["col_l1"], S["col_l3"])
        cw = (w - c0) // 3
        for j, c in enumerate(cols):
            cv.put(x + c0 + j * cw + cw - 2 - len(c), y, c, MUTE, bold=True)
        rows = []
        for lg in ("pl", "en"):
            code = lg.upper()
            rows.append((S["wps"] % code, [fmt(t / tpw[lg]) for t in seq], ""))
            rows.append((S["w500"] % code, [fmt(500 * tpw[lg] / t) for t in seq], " s"))
        for i, (lab, vals, unit) in enumerate(rows):
            cv.put(x, y + 1 + i, lab, TEXT)
            for j, v in enumerate(vals):
                s = v + unit
                cv.put(x + c0 + j * cw + cw - 2 - len(s), y + 1 + i, s,
                       (BEFORE, INFO, ACC)[j], bold=(j == 2))
        cv.put(x, y + h - 1, S["tpw"], MUTE, maxw=w)
        x, y, w, h = card(cv, X + ww + 1, by, W - ww - 1, bh2, S["layers_card"], ACC)
        for i, (lk, name, gain, note) in enumerate(S["layers"]):
            yy = y + i
            cv.put(x, yy, lk, ACC if gain else MUTE, bold=True)
            cv.put(x + 3, yy, name, TEXT)
            gx = x + 17
            if gain:
                cv.put(gx, yy, "+" + fmt(gain) + " t/s", ACC, bold=True)
                hbar(cv, gx + 11, yy, 8, gain / (T_L3 - T_BEFORE) * grow, ACC if lk == "L3" else INFO)
                cv.put(gx + 21, yy, note, MUTE, maxw=x + w - gx - 21)
            else:
                cv.put(gx, yy, "—", MUTE)
                cv.put(gx + 21, yy, note, WARN if lk == "L2" else MUTE, maxw=x + w - gx - 21)
        yy = y + 5
        cv.put(x, yy, S["mix_note"], MUTE, maxw=w)
        hy = by + bh2 + 1
        x, y, w, h = card(cv, X, hy, W, min(6, Y + H - hy), S["honest_card"], WARN)
        tx = tag(cv, x, y, "CI", WARN)
        cv.put(tx, y, S["ci"], TEXT, maxw=w - 6)
        tx = tag(cv, x, y + 1, "md5", INFO)
        lines = wrap(S["md5"], w - 6)
        for i, ln in enumerate(lines[:2]):
            cv.put(x + 6, y + 1 + i, ln, TEXT)
        cv.put(x, y + h - 1, S["sources"], MUTE, maxw=w)
    else:
        # compact: words per second inline, then honesty lines without cards
        x, y, w, h = card(cv, X, by, W, 4, S["words_card"], INFO)
        for i, lg in enumerate(("pl", "en")):
            code = lg.upper()
            s1 = " → ".join(fmt(t / tpw[lg]) for t in seq)
            s2 = " → ".join(fmt(500 * tpw[lg] / t) for t in seq)
            cv.put(x, y + i, "%s  %s  ·  %s  %s s" % (S["wps"] % code, s1, S["w500"] % code, s2),
                   TEXT, maxw=w)
        yy = by + 4
        lay = " · ".join("%s %s" % (lk, ("+" + fmt(g)) if g else note.split(",")[0])
                         for lk, _, g, note in S["layers"])
        items = [(lay, ACC), (S["ci"], WARN), (S["md5"], TEXT), (S["sources"], MUTE)]
        for txt, col in items:
            for ln in wrap(txt, W - 2):
                if yy >= Y + H:
                    return
                cv.put(X + 1, yy, ln, col)
                yy += 1


def tele_series(t, n):
    """Simulated telemetry history (deterministic jitter inside observed bounds)."""
    k_end = int(t * 4)
    ks = range(k_end - n + 1, k_end + 1)
    return {
        "tps": [T_L3 + 1.6 * noise(1, k) for k in ks],
        "jn": [86.5 + 1.5 * noise(2, k) for k in ks],
        "edge": [65.5 + 1.5 * noise(3, k) for k in ks],
        "pw": [283.0 + 2.0 * noise(4, k) for k in ks],
        "fan": [1850 + 25 * noise(5, k) for k in ks],
    }


def scene_night(cv, X, Y, W, H, st):
    wide = W >= 100
    nh = 7 if H >= 20 else 6
    x, y, w, h = card(cv, X, Y, W, nh, S["night_card"], ACC, S["night_sub"])
    if st.paused:
        sx = cv.put(x, y, "‖ " + S["paused"], WARN, bold=True)
    else:
        sx = cv.put(x, y, SPIN[int(st.t * 12) % len(SPIN)] + " " + S["running"], ACC, bold=True)
    tag(cv, sx + 2, y, S["layout_ex"], WARN)
    trial_n, trial_of = 14, 38   # layout example, labelled on screen
    frac = (trial_n - 1 + ((st.t / 9.0) % 1.0 if st.anim else 0.4)) / trial_of
    lab = S["trial"] % (trial_n, trial_of) + " · %d%%" % int(frac * 100)
    hbar(cv, x, y + 1, w - len(lab) - 2, frac, INFO, ACC)
    cv.put(x + w - len(lab), y + 1, lab, TEXT)
    cx = x
    for c in S["cond"]:
        if cx + len(c) + 2 > x + w:
            break
        cv.put(cx, y + 2, "✓", OK, bold=True)
        cx = cv.put(cx + 2, y + 2, c, TEXT) + 2
    for i, ln in enumerate(wrap(S["night_rule"], w)[:h - 3]):
        cv.put(x, y + 3 + i, ln, MUTE)
    ty = Y + nh + (1 if H >= 22 else 0)
    rest = Y + H - ty
    tw = int(W * 0.62) if wide else W
    note_lines = wrap(S["tele_note"], tw - 4)
    if wide:
        th = rest
    else:
        th = min(rest, 5 + 2 + len(note_lines))
    x, y, w, h = card(cv, X, ty, tw, th, S["tele_card"], INFO, S["tele_sub"])
    ser = tele_series(st.t, 2 * max(10, w - 26))
    metrics = (
        (S["metrics"][0], ser["tps"], "%s t/s" % fmt(ser["tps"][-1]), 100.0, 112.0, ACC),
        (S["metrics"][1], ser["jn"], "%s °C" % fmt(ser["jn"][-1]), 80.0, 90.0, DANGER),
        (S["metrics"][2], ser["edge"], "%s °C" % fmt(ser["edge"][-1]), 60.0, 70.0, WARN),
        (S["metrics"][3], ser["pw"], "%d W" % round(ser["pw"][-1]), 270.0, 290.0, INFO),
        (S["metrics"][4], ser["fan"], "%d RPM" % round(ser["fan"][-1]), 1780.0, 1900.0, OK),
    )
    graph_rows = max(1, min(3, (h - len(note_lines)) // 5 - 1))
    step = graph_rows + 1 if wide else 1
    for i, (lab, vals, val, lo, hi, col) in enumerate(metrics):
        yy = y + i * step
        if yy >= y + h - len(note_lines):
            break
        cv.put(x, yy, lab, MUTE)
        cv.put(x + 12, yy, val, col, bold=True)
        if wide:
            gx = x + 24
            spark(cv, gx, yy, w - 24, graph_rows, vals, lo, hi, col)
    for i, ln in enumerate(note_lines):
        if y + h - len(note_lines) + i >= y:
            cv.put(x, y + h - len(note_lines) + i, ln, MUTE)
    entries = []
    if st.undo_t is not None:
        entries.append(("undo", "↶", S["undone"]))
    entries += list(S["log"])

    def icon_of(kind):
        return {"ok": ("✓", OK), "bad": ("✗", DANGER_INK), "wait": ("·", MUTE), "undo": ("↶", WARN),
                "run": (SPIN[int(st.t * 12) % len(SPIN)] if not st.paused else "‖", ACC)}[kind]

    if wide:
        x, y, w, h = card(cv, X + tw + 1, ty, W - tw - 1, rest, S["log_card"], LINE_S, S["layout_ex"])
        yy = y
        for kind, state, text in entries:
            icon, col = icon_of(kind)
            if yy >= y + h:
                break
            cv.put(x, yy, icon, col, bold=True)
            if kind == "undo":
                lines = wrap(text, w - 2)
                for ln in lines:
                    cv.put(x + 2, yy, ln, WARN, bold=True)
                    yy += 1
                yy += 1
                continue
            cv.put(x + 2, yy, state, col)
            for ln in wrap(text, w - 2):
                yy += 1
                if yy >= y + h:
                    break
                cv.put(x + 2, yy, ln, TEXT)
            yy += 2
    else:
        yy = ty + th
        if yy < Y + H:
            cv.put(X + 1, yy, S["log_card"].capitalize() + " · " + S["layout_ex"], MUTE, bold=True)
            yy += 1
        for kind, state, text in entries:
            if yy >= Y + H:
                break
            icon, col = icon_of(kind)
            cv.put(X + 1, yy, icon, col, bold=True)
            lx = cv.put(X + 3, yy, "" if kind == "undo" else state + ":", col)
            cv.put(lx + (0 if kind == "undo" else 1), yy, text, WARN if kind == "undo" else TEXT,
                   maxw=X + W - lx - 1)
            yy += 1


DRAW = {"scan": scene_scan, "recommend": scene_recommend, "calibrate": scene_calibrate,
        "result": scene_result, "night": scene_night}


def header(cv, idx, st):
    W = cv.w
    cv.fill(0, 0, W, 1, BG1)
    x = cv.put(1, 0, " ◆ " + BRAND + " ", ON_ACC, ACC, bold=True) if cv.color \
        else cv.put(1, 0, "◆ " + BRAND)
    if W >= 110:
        x = cv.put(x + 1, 0, S["tagline"], MUTE)
    x += 2
    right = ("‖ " + S["paused"] + "  " if st.paused else "") + LANG.upper()
    full = sum(len(" %d %s " % (i + 1, n)) for i, n in enumerate(S["tabs"]))
    compact = x + full + len(right) + 3 > W
    for i, name in enumerate(S["tabs"]):
        s = " %d %s " % (i + 1, name) if (i == idx or not compact) else " %d " % (i + 1)
        if i == idx:
            if cv.color:
                x = cv.put(x, 0, s, HI, BG3, bold=True)
                cv.put(x - len(s) + 1, 0, str(i + 1), ACC, BG3, bold=True)
            else:
                x = cv.put(x, 0, "[" + s.strip() + "]")
        else:
            x = cv.put(x, 0, s, MUTE)
    if W - x > len(right) + len(S["proto"]) + 4:
        right = S["proto"] + "  " + right
    cv.put(W - len(right) - 1, 0, right, WARN if st.paused else MUTE)


def footer(cv, scene, st):
    W, y = cv.w, cv.h - 1
    cv.fill(0, y, W, 1, BG1)
    x = keycap(cv, 1, y, "1–5", S["k_scenes"])
    x = keycap(cv, x, y, "←/→", S["k_switch"])
    x = keycap(cv, x, y, "p", S["k_resume"] if st.paused else S["k_pause"])
    if scene == "night":
        x = keycap(cv, x, y, "u", S["k_undo"])
    x = keycap(cv, x, y, "q", S["k_quit"])
    r = S["sim_ui"] + " · " + BRAND
    if W - x > len(r) + 2:
        cv.put(W - len(r) - 1, y, r, mix(MUTE, LINE_S, 0.3))


def render(scene, W, H, st, color=True):
    cv = Canvas(W, H, color)
    idx = SCENES.index(scene)
    header(cv, idx, st)
    footer(cv, scene, st)
    if W < 60 or H < 20:
        cv.put(1, 2, S["too_small"], WARN, maxw=W - 2)
        return cv
    DRAW[scene](cv, 1, 2, W - 2, H - 4, st)
    return cv


# ---------------------------------------------------------------- plain (screen reader / log)
def plain_scene(scene):
    o = []
    if scene == "scan":
        for lab, val, src in S["scan_rows"]:
            o.append("%s: %s (%s)" % (lab, val, src))
        o.append(S["mem_tier"] + "; " + S["mem_tier2"] + ".")
        o.append(S["priv_head"][0].upper() + S["priv_head"][1:] + ". " + S["priv_body"])
        o.append(S["priv_code"])
        o.append(SCAN_CODE)
    elif scene == "recommend":
        for i, m in enumerate(rec_models()):
            head = S["rec_card"] if i == 0 else S["alt_card"]
            o.append("%s: %s %s, %s GB — %s (%s %s GiB %s %s GiB VRAM, %s); %s; %s %s." % (
                head.capitalize(), m["name"], m["quant"], fmt(m["gb"], 2), S["fit"], S["file"],
                fmt(m["gb"] * 1e9 / GIB), S["of"], fmt(24.0), S["estimate"], m["why"],
                S["licence"], m["lic"]))
            if m["tps"] is None:
                o.append("  %s: %s (%s)." % (S["speed"], S["soon"], S["soon_long"]))
            else:
                o.append("  %s: %s t/s, %s." % (S["speed"], fmt(m["tps"]), m["tps_note"]))
            for extra, _ in m.get("extra", ()):
                o.append("  " + extra)
        o.append(S["rec_foot"])
    elif scene == "calibrate":
        o.append(S["cal_banner"] + ".")
        for i, (lab, desc) in enumerate(S["cal_steps"]):
            o.append("%d/%d %s: %s." % (i + 1, len(S["cal_steps"]), lab, desc))
        for k, v in S["how"]:
            o.append("%s: %s." % (k, v))
    elif scene == "result":
        o.append(S["res_over"] + " — " + S["res_sub"] + ".")
        for lab, v in zip(S["bars"], (T_BEFORE, T_L1, T_L3)):
            o.append("%s: %s t/s." % (lab, fmt(v)))
        for lg in ("pl", "en"):
            code = lg.upper()
            seq = (T_BEFORE, T_L1, T_L3)
            o.append("%s: %s." % (S["wps"] % code, " → ".join(fmt(t / TOK_PER_WORD[lg]) for t in seq)))
            o.append("%s: %s s." % (S["w500"] % code,
                                    " → ".join(fmt(500 * TOK_PER_WORD[lg] / t) for t in seq)))
        o.append(S["tpw"] + ".")
        for lk, name, gain, note in S["layers"]:
            o.append("%s %s: %s." % (lk, name, ("+" + fmt(gain) + " t/s, " + note) if gain else note))
        o += [S["ci"] + ".", S["md5"] + ".", S["mix_note"] + ".", S["sources"] + "."]
    elif scene == "night":
        o.append("%s (%s): %s." % (S["running"].capitalize(), S["layout_ex"], S["trial"] % (14, 38)))
        o.append(", ".join(S["cond"]) + ".")
        o.append(S["night_rule"])
        ser = tele_series(60.0, 1)
        o.append("%s: %s t/s; %s %s °C; %s %s °C; %s %d W; %s %d RPM." % (
            S["metrics"][0], fmt(ser["tps"][-1]), S["metrics"][1], fmt(ser["jn"][-1]),
            S["metrics"][2], fmt(ser["edge"][-1]), S["metrics"][3], round(ser["pw"][-1]),
            S["metrics"][4], round(ser["fan"][-1])))
        o.append(S["tele_note"] + ".")
        for _, state, text in S["log"]:
            o.append("%s (%s): %s." % (state, S["layout_ex"], text))
    return o


def plain(scenes):
    out = [S["plain_head"] % BRAND, ""]
    for sc in scenes:
        i = SCENES.index(sc)
        out.append(S["plain_scene"] % (i + 1, S["titles"][i]))
        out += plain_scene(sc)
        out.append("")
    sys.stdout.write("\n".join(out))


# ---------------------------------------------------------------- live terminal
SNAP_T = {"scan": 99.0, "recommend": 99.0, "calibrate": 8.0, "result": 99.0, "night": 60.0}


class Term:
    def __init__(self):
        self.out = sys.stdout.fileno()
        self.inp = sys.stdin.fileno()
        self.tty = os.isatty(self.inp)
        self.old = None

    def write(self, s):
        b = s.encode("utf-8")
        while b:
            try:
                n = os.write(self.out, b)
            except InterruptedError:
                continue
            b = b[n:]

    def __enter__(self):
        if self.tty:
            import termios
            import tty
            self.old = termios.tcgetattr(self.inp)
            tty.setcbreak(self.inp)
        self.write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[0m\x1b[2J")
        return self

    def __exit__(self, *exc):
        self.write("\x1b[0m\x1b[?7h\x1b[?25h\x1b[2J\x1b[?1049l")
        if self.old is not None:
            import termios
            termios.tcsetattr(self.inp, termios.TCSADRAIN, self.old)
        return False

    def size(self):
        try:
            s = os.get_terminal_size(self.out)
            return s.columns, s.lines
        except OSError:
            return 120, 36

    def keys(self, timeout):
        import select
        if not self.tty:
            time.sleep(max(0.0, timeout))
            return b""
        try:
            r, _, _ = select.select([self.inp], [], [], max(0.0, timeout))
        except InterruptedError:
            return b""
        if r:
            try:
                return os.read(self.inp, 64)
            except OSError:
                return b""
        return b""


def parse_keys(buf):
    out, i = [], 0
    while i < len(buf):
        if buf[i:i + 3] in (b"\x1b[C", b"\x1bOC"):
            out.append("right")
            i += 3
        elif buf[i:i + 3] in (b"\x1b[D", b"\x1bOD"):
            out.append("left")
            i += 3
        elif buf[i:i + 1] == b"\x1b":
            i += 1
        else:
            out.append(chr(buf[i]).lower())
            i += 1
    return out


AUTO_DWELL = {"scan": 6.0, "recommend": 7.0, "calibrate": 6 * CAL_STEP + 2.0, "result": 9.0,
              "night": 10.0}


def run(args):
    term = Term()
    resized = [True]

    def on_winch(*_):
        resized[0] = True

    def on_term(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGWINCH, on_winch)
    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGHUP, on_term)
    idx = SCENES.index(args.scene)
    dt = 1.0 / args.fps
    st = State(0.0)
    t_start = last = time.monotonic()
    prev = []
    try:
        with term:
            while True:
                now = time.monotonic()
                if args.duration and now - t_start >= args.duration:
                    break
                if not st.paused:
                    st.t += now - last
                last = now
                if st.undo_t is not None and now - st.undo_t > 4.0:
                    st.undo_t = None
                if args.auto and not st.paused and st.t >= AUTO_DWELL[SCENES[idx]]:
                    idx = (idx + 1) % len(SCENES)
                    st.t = 0.0
                if resized[0]:
                    resized[0] = False
                    prev = []
                    term.write("\x1b[0m\x1b[2J")
                W, H = term.size()
                rows = render(SCENES[idx], W, H, st, not args.no_color).ansi_rows()
                out = []
                for y, r in enumerate(rows):
                    if y >= len(prev) or prev[y] != r:
                        out.append("\x1b[%d;1H%s" % (y + 1, r))
                if out:
                    term.write("".join(out))
                prev = rows
                for k in parse_keys(term.keys(max(0.0, dt - (time.monotonic() - now)))):
                    if k in ("q", "\x03"):
                        return
                    if k in "12345" and len(k) == 1:
                        idx, st.t = int(k) - 1, 0.0
                    elif k == "right":
                        idx, st.t = (idx + 1) % len(SCENES), 0.0
                    elif k == "left":
                        idx, st.t = (idx - 1) % len(SCENES), 0.0
                    elif k == "p":
                        st.paused = not st.paused
                    elif k == "u" and SCENES[idx] == "night":
                        st.undo_t = time.monotonic()
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------- main
def main():
    global LANG, S
    ap = argparse.ArgumentParser(
        description="%s — TUI/CLI mockup (static demo data, never touches the GPU)" % BRAND)
    ap.add_argument("--lang", choices=("pl", "en"), default="pl", help="language (default pl)")
    ap.add_argument("--scene", choices=SCENES, default="scan", help="starting / snapshot scene")
    ap.add_argument("--auto", action="store_true", help="auto-advance through the scenes")
    ap.add_argument("--fps", type=int, default=20, help="frame rate (1-60, default 20)")
    ap.add_argument("--duration", type=float, default=0, help="exit after S seconds (0 = never)")
    ap.add_argument("--plain", action="store_true",
                    help="screen-reader/log mode: linear text, no boxes, colour or animation "
                         "(all scenes, or only --scene if given explicitly)")
    ap.add_argument("--no-color", action="store_true", help="no colour (box drawing kept)")
    ap.add_argument("--snapshot", action="store_true",
                    help="print one static frame of --scene at --cols×--rows and exit")
    ap.add_argument("--cols", type=int, default=120, help="snapshot width (default 120)")
    ap.add_argument("--rows", type=int, default=36, help="snapshot height (default 36)")
    ap.add_argument("--html", metavar="OUT.html", help="write the snapshot as a self-contained HTML file")
    args = ap.parse_args()
    LANG, S = args.lang, STR[args.lang]
    args.fps = max(1, min(60, args.fps))

    if args.plain:
        explicit = any(a == "--scene" or a.startswith("--scene=") for a in sys.argv[1:])
        plain([args.scene] if explicit else list(SCENES))
        return
    if args.snapshot or args.html or not os.isatty(sys.stdout.fileno()):
        st = State(SNAP_T[args.scene], anim=False)
        cols, rows = max(20, args.cols), max(6, args.rows)
        if args.html:
            cv = render(args.scene, cols, rows, st, not args.no_color)
            title = "%s — TUI: %s (%s)" % (BRAND, S["titles"][SCENES.index(args.scene)], args.lang)
            with open(args.html, "w", encoding="utf-8") as f:
                f.write(cv.html(title, args.lang))
            if not args.snapshot:
                return
        cv = render(args.scene, cols, rows, st, not args.no_color)
        sys.stdout.write("\n".join(cv.ansi_rows()) + "\n")
        return
    run(args)


if __name__ == "__main__":
    main()
