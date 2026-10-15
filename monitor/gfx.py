"""Colours, text-line builder and cheap cached widgets (bars, braille graphs, big digits).

All output uses foreground colours only (24-bit), so lines never need a reset and
the terminal background (e.g. Windows Terminal acrylic) shows through.
"""
from functools import lru_cache


def esc_fg(r, g, b):
    return "\x1b[38;2;%d;%d;%dm" % (r, g, b)


def _lerp(a, b, t):
    return a + (b - a) * t


def _grad(stops, t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(int(_lerp(c0[i], c1[i], u)) for i in range(3))
    return stops[-1][1]


# cool -> hot
HEAT = [(0.00, (40, 70, 255)), (0.22, (0, 170, 255)), (0.42, (0, 235, 190)),
        (0.60, (150, 255, 60)), (0.75, (255, 220, 40)), (0.88, (255, 120, 20)),
        (1.00, (255, 30, 90))]
N = 128
HEAT_RGB = [_grad(HEAT, i / (N - 1)) for i in range(N)]
HEAT_FG = [esc_fg(*c) for c in HEAT_RGB]


def heat(t):
    """Escape for value fraction t in [0,1] on the cool->hot gradient."""
    if t != t or t <= 0:
        return HEAT_FG[0]
    if t >= 1:
        return HEAT_FG[-1]
    return HEAT_FG[int(t * (N - 1))]


def heat_rgb(t):
    t = 0.0 if t != t or t < 0 else 1.0 if t > 1 else t
    return HEAT_RGB[int(t * (N - 1))]


# fixed palette
C_BORDER = esc_fg(55, 65, 95)
C_DIM = esc_fg(80, 90, 115)
C_GRID = esc_fg(45, 52, 72)
C_LABEL = esc_fg(130, 145, 175)
C_TEXT = esc_fg(200, 208, 225)
C_VAL = esc_fg(240, 244, 255)
C_ACC = esc_fg(0, 220, 255)
C_ACC2 = esc_fg(255, 70, 170)
C_OK = esc_fg(80, 255, 140)
C_WARN = esc_fg(255, 190, 40)
C_BAD = esc_fg(255, 60, 80)
RESET = "\x1b[0m"


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


@lru_cache(maxsize=4096)
def hbar(q, w):
    """Horizontal gradient bar; q = filled length in 1/8 cells. Returns (str, w)."""
    full, rem = divmod(max(0, min(q, w * 8)), 8)
    parts = []
    den = max(1, w - 1)
    for i in range(full):
        parts.append(heat(i / den))
        parts.append("█")
    if rem and full < w:
        parts.append(heat(full / den))
        parts.append(EIGHTHS[rem])
        full += 1
    if full < w:
        parts.append(C_GRID)
        parts.append("╌" * (w - full))
    return "".join(parts)


def bar(line, frac, w):
    if w <= 0:
        return line
    if frac != frac:
        frac = 0.0
    return line.raw(hbar(int(round(max(0.0, min(1.0, frac)) * w * 8)), w), w)


VBLK = " ▁▂▃▄▅▆▇█"


def vbars(levels, h, colw, gap):
    """Vertical equaliser bars. levels in [0,1]. Returns h strings (top first)."""
    rows = []
    qs = [int(round(max(0.0, min(1.0, v)) * h * 8)) for v in levels]
    for r in range(h):
        rr = h - 1 - r                       # row index from bottom
        col = heat((rr + 0.5) / h)
        parts = []
        for q in qs:
            k = q - rr * 8
            if k >= 8:
                ch = "█"
            elif k > 0:
                ch = VBLK[k]
            else:
                ch = None
            if ch:
                parts.append(col)
                parts.append(ch * colw)
            elif rr == 0:
                parts.append(C_GRID)
                parts.append("▁" * colw)
            else:
                parts.append(" " * colw)
            if gap:
                parts.append(" " * gap)
        rows.append("".join(parts))
    return rows


# braille: filled-from-bottom bit masks for left / right dot columns
_LF = (0, 0x40, 0x44, 0x46, 0x47)
_RF = (0, 0x80, 0xA0, 0xB0, 0xB8)


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


def bgraph(vals, w, h, vmax, color_max=None):
    """Filled braille area graph of the history `vals` in w x h cells (2 samples per cell).
    Cells are coloured by their value on the heat scale (relative to color_max or vmax)."""
    if w <= 0 or h <= 0:
        return []
    cols = resample(vals, 2 * w)
    vmax = vmax or 1.0
    cmax = color_max or vmax
    lv = []
    for v in cols:
        lv.append(-1 if v is None else int(round(max(0.0, min(1.0, v / vmax)) * 4 * h)))
    rows = []
    for r in range(h):
        rr = h - 1 - r
        base = rr * 4
        parts = []
        last = None
        for c in range(w):
            a, b = lv[2 * c], lv[2 * c + 1]
            fa = 0 if a < 0 else min(4, max(0, a - base))
            fb = 0 if b < 0 else min(4, max(0, b - base))
            if fa == 0 and fb == 0:
                if rr == 0 and (a >= 0 or b >= 0):
                    col, ch = C_GRID, "⣀"
                else:
                    col, ch = None, " "
            else:
                va = cols[2 * c] or 0.0
                vb = cols[2 * c + 1] or 0.0
                col = heat(max(va, vb) / cmax)
                ch = chr(0x2800 | _LF[fa] | _RF[fb])
            if col is not None and col != last:
                parts.append(col)
                last = col
            parts.append(ch)
        rows.append("".join(parts))
    return rows


# 3x5 digit font -> 3 text rows using half blocks
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


@lru_cache(maxsize=512)
def big_text(s, t_lo, t_hi):
    """Render s in the 3x5 font. Returns (rows[3], width). Colour gradient t_lo..t_hi."""
    glyphs = [_FONT.get(ch, _FONT[" "]) for ch in s]
    width = sum(len(g[0]) + 1 for g in glyphs) - 1 if glyphs else 0
    rows = []
    for pr in range(3):
        parts = []
        x = 0
        for gi, g in enumerate(glyphs):
            top = g[pr * 2]
            bot = g[pr * 2 + 1] if pr * 2 + 1 < 5 else "0" * len(top)
            for i in range(len(top)):
                parts.append(heat(t_lo + (t_hi - t_lo) * (x / max(1, width - 1))))
                parts.append(_HB[(top[i], bot[i])])
                x += 1
            if gi != len(glyphs) - 1:
                parts.append(" ")
                x += 1
        rows.append("".join(parts))
    return rows, width


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
