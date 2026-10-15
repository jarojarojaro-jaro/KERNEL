"""Colours, sections, text-line builder and cheap cached widgets
(glowing gradient bars, gradient-filled graphs, equaliser bars, big digits).

Every string that is written to the terminal starts with an explicit background
(panel tint or default), so the diff renderer never depends on leftover SGR state.
"""
from functools import lru_cache

WHITE = (255, 255, 255)
BG_OFF = "\x1b[49m"
RESET = "\x1b[0m"


def fg(c):
    return "\x1b[38;2;%d;%d;%dm" % c


def bg(c):
    return "\x1b[48;2;%d;%d;%dm" % c


def esc_fg(r, g, b):
    return "\x1b[38;2;%d;%d;%dm" % (r, g, b)


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def scale(c, k):
    return (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))


def _grad(stops, t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0.0)
    return stops[-1][1]


# cool -> hot, every stop bright and saturated (readable on black and on tinted cards)
HEAT = [(0.00, (0, 190, 255)), (0.22, (0, 255, 200)), (0.42, (110, 255, 70)),
        (0.60, (255, 236, 0)), (0.76, (255, 150, 0)), (0.89, (255, 60, 70)),
        (1.00, (255, 40, 170))]
N = 128
HEAT_RGB = [_grad(HEAT, i / (N - 1)) for i in range(N)]
HEAT_FG = [fg(c) for c in HEAT_RGB]
GLOW_FG = [fg(mix(c, WHITE, 0.45)) for c in HEAT_RGB]
BODY_FG = [fg(scale(c, 0.8)) for c in HEAT_RGB]      # graph fill below the glowing edge


def _idx(t):
    if t != t or t <= 0:
        return 0
    if t >= 1:
        return N - 1
    return int(t * (N - 1))


def heat(t):
    """Escape for value fraction t in [0,1] on the cool->hot gradient."""
    return HEAT_FG[_idx(t)]


def glow(t):
    """Whitened ("glowing") variant of heat(t)."""
    return GLOW_FG[_idx(t)]


def heat_rgb(t):
    return HEAT_RGB[_idx(t)]


# fixed palette: no dark greys for anything that carries data
TEXT = fg((230, 236, 250))
VAL = fg(WHITE)
SUB = fg((170, 186, 222))          # secondary text, still clearly readable
FAINT = fg((118, 132, 172))        # captions / grid only
INK = fg((10, 10, 24))             # dark text on bright chips
OK = fg((90, 255, 150))
WARN = fg((255, 205, 40))
BAD = fg((255, 70, 110))
CARD_BASE = (10, 11, 20)


class Section:
    """Colour identity of one dashboard card."""

    def __init__(self, title, glyph, accent, accent2):
        self.title = title
        self.glyph = glyph
        self.rgb = accent
        self.rgb2 = accent2
        self.A = fg(accent)
        self.A2 = fg(accent2)
        self.lab = fg(mix(accent, WHITE, 0.22))         # labels inside the card
        self.track = fg(scale(accent, 0.45))            # empty part of bars, baselines
        self.tint_rgb = mix(CARD_BASE, accent, 0.085)   # card background
        self.chip = bg(accent) + INK                    # title tag


class Line:
    """Accumulates (colour, text) segments and renders to an exact visible width."""
    __slots__ = ("segs", "n")

    def __init__(self):
        self.segs = []
        self.n = 0

    def t(self, s, c=""):
        if s:
            self.segs.append((c, s))
            self.n += len(s)
        return self

    def raw(self, s, n):
        """Pre-coloured string with known visible width n."""
        self.segs.append((None, s, n))
        self.n += n
        return self

    def pad_to(self, col):
        if self.n < col:
            self.t(" " * (col - self.n))
        return self

    def right(self, s, c, width, optional=False):
        """Append s right-aligned so that it ends at column `width`.
        optional: drop s instead of overflowing when it does not fit."""
        if optional and self.n + 1 + len(s) > width:
            return self
        self.pad_to(width - len(s))
        return self.t(s, c)

    def opt(self, s, c, width):
        """Append s only if it fits within `width`."""
        if self.n + len(s) <= width:
            self.t(s, c)
        return self

    def render(self, w):
        out = []
        n = 0
        for seg in self.segs:
            if len(seg) == 3:
                _, s, k = seg
                if n + k > w:
                    break
                out.append(s)
                n += k
                continue
            c, s = seg
            room = w - n
            if room <= 0:
                break
            if len(s) > room:
                s = s[:room]
            out.append(c)
            out.append(s)
            n += len(s)
        if n < w:
            out.append(" " * (w - n))
        return "".join(out)


EIGHTHS = " ▏▎▍▌▋▊▉"


@lru_cache(maxsize=8192)
def hbar(q, w, track):
    """Horizontal gradient bar with a glowing tip; q = filled length in 1/8 cells."""
    full, rem = divmod(max(0, min(q, w * 8)), 8)
    parts = []
    den = max(1, w - 1)
    tip = full if rem else full - 1
    for i in range(full):
        parts.append(glow(i / den) if i == tip else heat(i / den))
        parts.append("█")
    if rem and full < w:
        parts.append(glow(full / den))
        parts.append(EIGHTHS[rem])
        full += 1
    if full < w:
        parts.append(track)
        parts.append("─" * (w - full))
    return "".join(parts)


def bar(line, frac, w, track):
    if w <= 0:
        return line
    if frac != frac:
        frac = 0.0
    return line.raw(hbar(int(round(max(0.0, min(1.0, frac)) * w * 8)), w, track), w)


VBLK = " ▁▂▃▄▅▆▇█"


def vbars(levels, peaks, h, colw, gap, track):
    """Vertical equaliser bars (levels in [0,1]) with falling peak-hold caps.
    Returns h strings (top first)."""
    rows = []
    qs = [int(round(max(0.0, min(1.0, v)) * h * 8)) for v in levels]
    prow = [min(h - 1, int(max(0.0, min(1.0, p)) * h - 0.15)) if p > 0.02 else -1
            for p in peaks]
    pad = " " * gap
    for r in range(h):
        rr = h - 1 - r                       # row index from bottom
        col = heat((rr + 0.5) / h)
        top = glow((rr + 0.5) / h)
        parts = []
        last = None
        for i, q in enumerate(qs):
            k = q - rr * 8
            if k >= 8:
                c, ch = (top if k == 8 else col), "█"
            elif k > 0:
                c, ch = top, VBLK[k]
            elif prow[i] == rr:
                c, ch = VAL, "▔"
            elif rr == 0:
                c, ch = track, "▁"
            else:
                c, ch = None, " "
            if c is not None and c is not last:
                parts.append(c)
                last = c
            parts.append(ch * colw)
            if gap:
                parts.append(pad)
        rows.append("".join(parts))
    return rows


def resample(vals, n):
    """Map a history (list, may contain None) onto n columns, right-aligned."""
    m = len(vals)
    if m <= n:
        return [None] * (n - m) + list(vals)
    out = []
    step = m / n
    for i in range(n):
        a = int(i * step)
        b = max(a + 1, int((i + 1) * step))
        seg = [v for v in vals[a:b] if v is not None]
        out.append(sum(seg) / len(seg) if seg else None)
    return out


def blockgraph(vals, w, h, vmax, cmax, track):
    """Area graph of the history in w x h cells, one sample per column, 8 levels per cell.
    Filled with a vertical cool->hot gradient (by absolute level, relative to cmax) and a
    glowing top edge."""
    if w <= 0 or h <= 0:
        return []
    cols = resample(vals, w)
    vmax = vmax or 1.0
    ratio = vmax / (cmax or vmax)
    qs = [-1 if v is None else int(round(max(0.0, min(1.0, v / vmax)) * h * 8)) for v in cols]
    tops = [glow(q / (8.0 * h) * ratio) for q in qs]      # glowing edge in the value's colour
    rows = []
    for r in range(h):
        rr = h - 1 - r
        body = BODY_FG[_idx((rr + 1) / h * ratio)]
        base = rr * 8
        parts = []
        last = None
        for i, q in enumerate(qs):
            k = q - base
            if k >= 8:
                c, ch = (tops[i] if k == 8 else body), "█"
            elif k > 0:
                c, ch = tops[i], VBLK[k]
            elif rr == 0 and q >= 0:
                c, ch = track, "▁"
            else:
                c, ch = None, " "
            if c is not None and c is not last:
                parts.append(c)
                last = c
            parts.append(ch)
        rows.append("".join(parts))
    return rows


# 3x5 pixel font
_FONT = {
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"), "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "111"),
    ".": ("0", "0", "0", "0", "1"), "-": ("000", "000", "111", "000", "000"),
    " ": ("000", "000", "000", "000", "000"),
}
_HB = {("1", "1"): "█", ("1", "0"): "▀", ("0", "1"): "▄", ("0", "0"): " "}
_GLOSS1 = (0.40, 0.12, 0.0)                 # whitening per text row (glossy top)
_GLOSS2 = (0.50, 0.30, 0.14, 0.0, 0.0)


def big_width(s, size):
    gl = [_FONT.get(ch, _FONT[" "]) for ch in s]
    if size == 1:
        return sum(len(g[0]) + 1 for g in gl) - 1 if gl else 0
    return sum(2 * len(g[0]) + 2 for g in gl) - 2 if gl else 0


@lru_cache(maxsize=1024)
def big_text(s, frac, size=1):
    """Render s in the pixel font, coloured by value fraction `frac` with a glossy top.
    size 1: 3 rows (half blocks); size 2: 5 rows, double-width pixels.
    Returns (rows, width)."""
    glyphs = [_FONT.get(ch, _FONT[" "]) for ch in s]
    base = heat_rgb(frac)
    rows = []
    if size == 1:
        for pr in range(3):
            parts = [fg(mix(base, WHITE, _GLOSS1[pr]))]
            for gi, g in enumerate(glyphs):
                top = g[pr * 2]
                bot = g[pr * 2 + 1] if pr * 2 + 1 < 5 else "0" * len(top)
                parts.extend(_HB[(top[i], bot[i])] for i in range(len(top)))
                if gi != len(glyphs) - 1:
                    parts.append(" ")
            rows.append("".join(parts))
    else:
        for pr in range(5):
            parts = [fg(mix(base, WHITE, _GLOSS2[pr]))]
            for gi, g in enumerate(glyphs):
                parts.extend("██" if p == "1" else "  " for p in g[pr])
                if gi != len(glyphs) - 1:
                    parts.append("  ")
            rows.append("".join(parts))
    return rows, big_width(s, size)


def fmt_bytes(b, unit=True):
    b = float(b or 0)
    for u in ("B", "K", "M", "G", "T"):
        if abs(b) < 1024 or u == "T":
            if u == "B":
                return "%d%s" % (b, u if unit else "")
            return ("%.1f%s" if b < 100 else "%.0f%s") % (b, u if unit else "")
        b /= 1024.0
    return "?"


def fmt_rate(b):
    b = float(b or 0)
    if b < 1e3:
        return "%3.0f B/s" % b
    if b < 1e6:
        return "%5.1f KB/s" % (b / 1e3)
    if b < 1e9:
        return "%5.1f MB/s" % (b / 1e6)
    return "%5.2f GB/s" % (b / 1e9)
