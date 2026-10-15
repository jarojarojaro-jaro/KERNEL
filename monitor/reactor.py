#!/usr/bin/env python3
"""REACTOR - live terminal monitor for the RX 7900 XTX + Ryzen 7 5700X LLM box.

Pure standard library, raw ANSI (24-bit colour, braille, block elements).
Read-only: sysfs/procfs files and the llama-server log. Keys: q quit, p pause,
+/- frame rate, 1/2/3 layout, t card tint, r redraw.
"""
import argparse
import math
import os
import select
import signal
import socket
import sys
import termios
import time
import tty

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from gfx import (BAD, BG_OFF, FAINT, OK, RESET, SUB, TEXT, VAL, WARN, WHITE,  # noqa: E402
                 Line, Section, bar, bg, big_text, big_width, blockgraph, fg, fmt_bytes,
                 fmt_rate, heat, mix, scale, vbars)
from sensors import Sampler  # noqa: E402

FPS_STEPS = (2, 5, 8, 10, 12, 15, 20, 24, 30, 45, 60)
SAMPLE_DT = 0.5
GIB = float(2 ** 30)
LW = 7                       # label column width
MIN_W, MIN_H = 60, 18
TAU = 2 * math.pi
HEADER_BG = bg((30, 20, 60))

SEC = {
    "gpu": Section("GPU", "▣", (255, 60, 190), (255, 150, 40)),
    "cpu": Section("CPU", "◈", (0, 210, 255), (125, 115, 255)),
    "llm": Section("LLM", "◉", (150, 255, 60), (0, 235, 200)),
    "core": Section("REACTOR CORE", "◎", (0, 230, 255), (255, 60, 190)),
    "io": Section("I/O", "↕", (255, 180, 0), (255, 105, 60)),
    "procs": Section("TOP PROCESSES", "≡", (190, 120, 255), (255, 80, 200)),
}
FOOTER_KEYS = (("q", "quit", "gpu"), ("p", "pause", "cpu"), ("+/-", "fps", "llm"),
               ("1", "reactor", "io"), ("2", "data", "io"), ("3", "core", "io"),
               ("t", "tint", "procs"), ("r", "redraw", "procs"))


def tfrac(t, lo=30.0, hi=105.0):
    return 0.0 if t is None else (t - lo) / (hi - lo)


def q40(x):
    """Quantise a colour fraction (keeps the big-digit cache small)."""
    return round(max(0.0, min(1.0, x)) * 40) / 40.0


def alloc(avail, reqs):
    """reqs: list of (min, max). Grant minimums in priority order, then grow round-robin."""
    sizes = [0] * len(reqs)
    on = [False] * len(reqs)
    for i, (mn, mx) in enumerate(reqs):
        if mn <= avail and mx > 0:
            sizes[i] = mn
            on[i] = True
            avail -= mn
    grew = True
    while avail > 0 and grew:
        grew = False
        for i, (mn, mx) in enumerate(reqs):
            if avail > 0 and on[i] and sizes[i] < mx:
                sizes[i] += 1
                avail -= 1
                grew = True
    return sizes


def stack(groups, ih, iw):
    """Concatenate line groups, separated by blank lines when there is room."""
    total = sum(len(g) for g in groups)
    sep = ih - total >= len(groups) - 1
    out = []
    for i, g in enumerate(groups):
        if i and sep:
            out.append(" " * iw)
        out.extend(g)
    return out[:ih]


class Anim:
    """Exponential interpolation of displayed values towards the latest samples."""

    def __init__(self, tau=0.11):
        self.tau = tau
        self.v = {}
        self.dirty = set()

    def set(self, name, target, scale_):
        if target is None or target != target:
            target = 0.0
        e = self.v.get(name)
        eps = abs(scale_) * 0.0015 or 1e-9
        if e is None:
            self.v[name] = [float(target), float(target), eps]
            self.dirty.add(name[0])
        else:
            e[1] = float(target)
            e[2] = eps

    def step(self, dt, snap=False):
        k = 1.0 - math.exp(-dt / self.tau)
        d = self.dirty
        for name, e in self.v.items():
            diff = e[1] - e[0]
            if diff:
                if snap or abs(diff) < e[2]:
                    e[0] = e[1]
                else:
                    e[0] += diff * k
                d.add(name[0])

    def __getitem__(self, name):
        e = self.v.get(name)
        return e[0] if e else 0.0


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
            self.old = termios.tcgetattr(self.inp)
            tty.setcbreak(self.inp)
        self.write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[0m\x1b[2J")
        return self

    def __exit__(self, *exc):
        self.write(RESET + "\x1b[?7h\x1b[?25h\x1b[2J\x1b[?1049l")
        if self.old is not None:
            termios.tcsetattr(self.inp, termios.TCSADRAIN, self.old)
        return False

    def size(self):
        try:
            s = os.get_terminal_size(self.out)
            return s.columns, s.lines
        except OSError:
            return 160, 45

    def keys(self, timeout):
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


class Card:
    """Collects line groups for one panel in the colours of its section."""

    def __init__(self, app, sk, iw, value_w):
        self.app = app
        self.s = SEC[sk]
        self.iw = iw
        self.bw = max(4, iw - LW - value_w)
        self.gw = iw - LW
        self.groups = []

    def row(self, label, frac, segs):
        L = Line().t(label.ljust(LW), self.s.lab)
        bar(L, frac, self.bw, self.s.track)
        L.t(" ")
        for txt, c in segs:
            L.t(txt, c)
        self.groups.append([L.render(self.iw)])

    def graph(self, name, h, vmax, peak, xform=None, cmax=None):
        rows = self.app.graph(name, self.gw, h, vmax, self.s.track, xform, cmax)
        for i, r in enumerate(rows):
            self.groups[-1].append(Line().t((peak if i == 0 else "").ljust(LW), SUB)
                                   .raw(r, self.gw).render(self.iw))

    def lines(self, ih):
        return stack(self.groups, ih, self.iw)


class App:
    def __init__(self, args):
        self.args = args
        self.fps_i = min(range(len(FPS_STEPS)), key=lambda i: abs(FPS_STEPS[i] - args.fps))
        self.fps = args.fps
        self.use3d = not args.no_3d
        self.tint = not args.no_tint
        self.layout = args.layout if (self.use3d or args.layout != 3) else 2
        self.paused = False
        self.s = Sampler(args.log)
        self.anim = Anim()
        self.torus = None
        if self.use3d:
            from core3d import Torus
            self.torus = Torus()
        self.host = socket.gethostname()
        self.spin = 0.0
        self.t_anim = 0.0
        self.wave = 0.0
        self.wave_amp = 0.0
        self.pulse = 0.0
        self.last_events = 0
        self.self_cpu = 0.0
        self._cpu_mark = (time.monotonic(), sum(os.times()[:2]))
        self.peaks = []
        self.hold = []
        self.led_ph = {}
        self.led_act = {}
        self.colcache = {}
        self.cache = {}
        self.gcache = {}
        self.gseq = -1
        self.prev = {}
        self.static = {}
        self.panels = []
        self.pre = {}
        self.reg = {}
        self.geom = None
        self.full = True
        self.resized = True

    # ------------------------------------------------------------ sampling
    def sample(self):
        s = self.s
        s.sample()
        g, c, A = s.gpu, s.cpu, self.anim
        A.set("g.load", g.busy, 100)
        A.set("g.mbusy", g.mbusy, 100)
        A.set("g.vram", (g.vram_used or 0) / GIB, g.vram_total / GIB or 1)
        A.set("g.power", g.power, g.cap or 285)
        A.set("g.te", g.t_edge, 100)
        A.set("g.tj", g.t_junc, 100)
        A.set("g.tm", g.t_mem, 100)
        A.set("g.sclk", g.sclk, g.sclk_max)
        A.set("g.mclk", g.mclk, g.mclk_max)
        A.set("g.fan", g.fan, g.fan_max)
        A.set("c.total", c.total, 100)
        for i, v in enumerate(c.threads):
            A.set("c.t%d" % i, v, 100)
        A.set("c.temp", c.temp, 100)
        A.set("c.favg", c.freq_avg, c.fmax)
        A.set("c.fmax", c.freq_max, c.fmax)
        A.set("c.ram", c.mem_used / GIB, c.mem_total / GIB or 1)
        A.set("c.swap", c.swap_used / GIB, c.swap_total / GIB or 1)
        A.set("l.tok", s.log.live_rate(), 300)
        if s.log.events != self.last_events:
            self.last_events = s.log.events
            self.pulse = 1.0
        t = time.monotonic()
        cpu = sum(os.times()[:2])
        t0, c0 = self._cpu_mark
        if t - t0 >= 2.0:
            self.self_cpu = 100.0 * (cpu - c0) / (t - t0)
            self._cpu_mark = (t, cpu)

    def graph(self, name, w, h, vmax, track, xform=None, cmax=None):
        if self.s.seq != self.gseq:
            self.gcache.clear()
            self.gseq = self.s.seq
        key = (name, w, h, vmax, cmax, track)
        r = self.gcache.get(key)
        if r is None:
            vals = list(self.s.h[name].d)
            if xform:
                vals = [None if v is None else xform(v) for v in vals]
            r = self.gcache[key] = blockgraph(vals, w, h, vmax, cmax, track)
        return r

    def col(self, rgb):
        e = self.colcache.get(rgb)
        if e is None:
            e = self.colcache[rgb] = fg(rgb)
        return e

    def hero(self, sec, iw, items, size=1):
        """Big colour-coded numbers side by side: items = (label, text, unit, frac)."""
        nrow = 3 if size == 1 else 5
        cw = iw // max(1, len(items))
        lines = [Line() for _ in range(nrow + 1)]
        for i, (label, txt, unit, frac) in enumerate(items):
            rows, bw = big_text(txt, q40(frac), size)
            blk = max(bw + 1 + len(unit), len(label))
            x0 = i * cw + max(0, (cw - blk) // 2)
            lines[0].pad_to(x0).t(label, sec.lab)
            for k in range(nrow):
                lines[k + 1].pad_to(x0).raw(rows[k], bw)
            lines[nrow].t(" " + unit, SUB)
        return [L.render(iw) for L in lines]

    # ------------------------------------------------------------- panels
    def gpu_lines(self, iw, ih):
        g, A, h = self.s.gpu, self.anim, self.s.h
        sec = SEC["gpu"]
        if not g.ok:
            return [Line().t("no amdgpu device found in /sys/class/drm", BAD).render(iw)]
        C = Card(self, "gpu", iw, 17)
        n_proc = max(1, len(self.s.procs.gpu))
        nsep = 7 if ih >= 36 else 0
        hero, procs, gl, gp, gt, gv, gs = alloc(ih - nsep - 6, [
            (4, 4), (2, 1 + min(n_proc, 6)), (1, 6), (1, 4), (1, 4), (1, 3), (1, 3)])
        load = A["g.load"]
        cap = g.cap or 285.0
        pw = A["g.power"]
        tj = A["g.tj"]
        if hero:
            C.groups.append(self.hero(sec, iw, [
                ("LOAD", "%.0f" % load, "%", load / 100),
                ("JUNCTION", "%.0f" % tj if g.t_junc is not None else "--", "°C",
                 tfrac(tj)),
                ("POWER", "%.0f" % pw, "W", pw / cap)]))
        C.row("LOAD", load / 100, [("%3.0f%%" % load, heat(load / 100)),
                                   ("  mem %3.0f%%" % A["g.mbusy"], SUB)])
        if gl:
            C.graph("gpu", gl, 100, "▲%3.0f%%" % h["gpu"].peak())
        tot = g.vram_total / GIB or 1
        vr = A["g.vram"]
        C.row("VRAM", vr / tot, [("%5.2f" % vr, heat(vr / tot)), ("/%4.1f GiB" % tot, SUB)])
        if gv:
            C.graph("vram", gv, g.vram_total or 1, "▲%4.1fG" % (h["vram"].peak() / GIB))
        C.row("POWER", pw / cap, [("%5.1f" % pw, heat(pw / cap)), ("/%3.0f W" % cap, SUB)])
        if gp:
            C.graph("power", gp, cap, "▲%3.0fW" % h["power"].peak())
        mb = max(2, (iw - LW - 33) // 3)
        L = Line().t("TEMP".ljust(LW), sec.lab)
        for nm, key, raw in (("edge", "g.te", g.t_edge), ("junc", "g.tj", g.t_junc),
                             ("mem ", "g.tm", g.t_mem)):
            v = A[key]
            L.t(nm + " ", SUB)
            L.t(("%3.0f°" % v) if raw is not None else " n/a", heat(tfrac(v)))
            L.t(" ")
            bar(L, tfrac(v), mb, sec.track)
            L.t(" ")
        C.groups.append([L.render(iw)])
        if gt:
            C.graph("tj", gt, 80.0, "▲%3.0f°" % h["tj"].peak(),
                    xform=lambda v: v - 30.0, cmax=75.0)
        mb2 = max(2, (iw - LW - 32) // 2)
        L = Line().t("CLOCK".ljust(LW), sec.lab)
        sc = A["g.sclk"]
        if g.sclk == 0:
            L.t("sclk ", SUB).t("  GFXOFF ", SEC["cpu"].A)
        else:
            L.t("sclk ", SUB).t("%4.0f" % sc, heat(sc / g.sclk_max)).t(" MHz ", SUB)
        bar(L, sc / g.sclk_max, mb2, sec.track)
        mc = A["g.mclk"]
        L.t("  mclk ", SUB).t("%4.0f" % mc, heat(mc / g.mclk_max)).t(" MHz ", SUB)
        bar(L, mc / g.mclk_max, mb2, sec.track)
        C.groups.append([L.render(iw)])
        if gs:
            C.graph("sclk", gs, g.sclk_max, "▲%4.0f" % h["sclk"].peak())
        fan = A["g.fan"]
        L = Line().t("FAN".ljust(LW), sec.lab)
        L.t("%4.0f" % fan, heat(fan / g.fan_max)).t(" rpm ", SUB)
        bar(L, fan / g.fan_max, 6, sec.track)
        L.opt("  " + g.link, TEXT, iw)
        if g.sclk_lvl is not None:
            L.opt("  dpm s%d/%d m%d/%d" % (g.sclk_lvl, g.sclk_nlvl - 1, g.mclk_lvl or 0,
                                           g.mclk_nlvl - 1), SUB, iw)
        C.groups.append([L.render(iw)])
        if procs:
            grp = [Line().t("    PID  ", SUB).t("GPU PROCESS (KFD)", sec.lab)
                   .right("VRAM", SUB, iw).render(iw)]
            rows = self.s.procs.gpu[:procs - 1]
            if not rows:
                grp.append(Line().t("         no compute process holds the GPU", SUB)
                           .render(iw))
            pb = max(4, iw - 9 - 17 - 10)
            for vram, pid, comm in rows:
                L = Line().t("%7d  " % pid, SUB).t(comm[:15].ljust(17), TEXT)
                bar(L, vram / (g.vram_total or 1), pb, sec.track)
                L.right("%6.2f G" % (vram / GIB), heat(vram / (g.vram_total or 1)), iw)
                grp.append(L.render(iw))
            C.groups.append(grp)
        return C.lines(ih)

    def cpu_lines(self, iw, ih):
        c, A, h = self.s.cpu, self.anim, self.s.h
        sec = SEC["cpu"]
        C = Card(self, "cpu", iw, 22)
        n = len(c.threads) or 1
        colw, gap = (2, 1) if iw >= n * 3 else (1, 1) if iw >= n * 2 else (1, 0)
        nsep = 6 if ih >= 30 else 0
        eq, gtot, hero, gtemp, gram = alloc(ih - nsep - 5, [(4, 9), (1, 4), (4, 4), (1, 3),
                                                            (1, 2)])
        tot = A["c.total"]
        t = A["c.temp"]
        fa, fm = A["c.favg"], A["c.fmax"]
        mt = c.mem_total / GIB or 1
        ram = A["c.ram"]
        if hero:
            items = [("TOTAL", "%.0f" % tot, "%", tot / 100),
                     ("TCTL", "%.0f" % t if c.temp is not None else "--", "°C", tfrac(t, 30, 95)),
                     ("FREQ", "%.1f" % (fa / 1000), "GHz", fa / c.fmax),
                     ("RAM", "%.0f" % ram, "GiB", ram / mt)]
            if iw < 50:
                items = [items[0], items[1], items[3]]
            C.groups.append(self.hero(sec, iw, items))
        if eq:
            levels = [A["c.t%d" % i] / 100 for i in range(n)]
            peaks = self.peaks if len(self.peaks) == n else levels
            width = n * (colw + gap) - gap
            left = max(0, (iw - width) // 2)
            grp = [Line().t(" " * left).raw(r, n * (colw + gap)).render(iw)
                   for r in vbars(levels, peaks, eq - 1, colw, gap, sec.track)]
            L = Line().t(" " * left)
            for i in range(n):
                v = A["c.t%d" % i]
                L.t(("%2d" % min(99, v)) if colw == 2 else ("%x" % i),
                    heat(v / 100) if colw == 2 else SUB)
                if gap:
                    L.t(" " * gap)
            grp.append(L.render(iw))
            C.groups.append(grp)
        C.row("TOTAL", tot / 100, [("%3.0f%%" % tot, heat(tot / 100)),
                                   ("  load %4.2f" % c.load[0], SUB)])
        if gtot:
            C.graph("cpu", gtot, 100, "▲%3.0f%%" % h["cpu"].peak())
        segs = [("%5.1f°C" % t, heat(tfrac(t, 30, 95)))]
        if c.nvme_temp is not None:
            segs.append(("  nvme %2.0f°" % c.nvme_temp, SUB))
        C.row("TCTL", tfrac(t, 30, 95), segs)
        if gtemp:
            C.graph("ctemp", gtemp, 65.0, "▲%3.0f°" % h["ctemp"].peak(),
                    xform=lambda v: v - 30.0)
        C.row("FREQ", fa / c.fmax, [("%4.2f" % (fa / 1000), heat(fa / c.fmax)),
                                    (" max %4.2f GHz" % (fm / 1000), SUB)])
        C.row("RAM", ram / mt, [("%5.1f" % ram, heat(ram / mt)), ("/%4.1f GiB" % mt, SUB)])
        if gram:
            C.graph("ram", gram, c.mem_total or 1, "▲%4.1fG" % (h["ram"].peak() / GIB))
        st = c.swap_total / GIB
        sw = A["c.swap"]
        C.row("SWAP", sw / st if st else 0, [("%5.1f" % sw, heat(sw / st if st else 0)),
                                             ("/%4.1f GiB" % st, SUB)])
        return C.lines(ih)

    def io_lines(self, iw, ih):
        io, h = self.s.io, self.s.h
        sec = SEC["io"]
        dg, ng = alloc(max(0, ih - 2), [(2, 10), (2, 10)])
        gw = iw - LW
        out = []
        dmax = max(h["rd"].peak(), h["wr"].peak(), 1e6)
        nmax = max(h["rx"].peak(), h["tx"].peak(), 1.25e5)

        def rate_row(label, a_lbl, a, b_lbl, b, vmax):
            L = Line().t(label.ljust(LW), sec.lab)
            L.t(a_lbl, SUB).t(fmt_rate(a), heat(a / vmax)).t("  " + b_lbl, SUB)
            L.t(fmt_rate(b), heat(b / vmax))
            L.right("▲" + fmt_rate(vmax).strip(), SUB, iw, optional=True)
            out.append(L.render(iw))

        def graphs(n, a, b, la, lb, vmax):
            ha = (n + 1) // 2
            for name, hh, lbl in ((a, ha, la), (b, n - ha, lb)):
                for i, r in enumerate(self.graph(name, gw, hh, vmax, sec.track) if hh else []):
                    out.append(Line().t((lbl if i == 0 else "").rjust(LW - 1).ljust(LW), SUB)
                               .raw(r, gw).render(iw))

        rate_row("DISK", "R ", io.rd, "W ", io.wr, dmax)
        if dg:
            graphs(dg, "rd", "wr", "read", "write", dmax)
        rate_row("NET", "↓ ", io.rx, "↑ ", io.tx, nmax)
        if ng:
            graphs(ng, "rx", "tx", "down", "up", nmax)
        return out[:ih]

    def proc_lines(self, iw, ih):
        sec = SEC["procs"]
        out = [Line().t("    PID  ", SUB).t("PROCESS", sec.lab).right("CPU%      RSS", SUB, iw)
               .render(iw)]
        pb = max(3, iw - 9 - 17 - 16)
        for cpu, rss, pid, comm in self.s.procs.top[:max(0, ih - 1)]:
            L = Line().t("%7d  " % pid, SUB)
            L.t(comm[:15].ljust(17), SEC["llm"].A if comm == "llama-server" else TEXT)
            bar(L, cpu / 100.0, pb, sec.track)
            L.right("%5.1f" % cpu, heat(cpu / 100), iw - 9).right(fmt_bytes(rss), TEXT, iw)
            out.append(L.render(iw))
        return out

    def status_line(self, iw, now, split):
        """LLM status (pulsing dot) + model name; returns 1 or 2 lines."""
        s = self.s
        run = s.procs.llama
        model = (run[1] if run and run[1] else None) or s.log.model or "-"
        L = Line()
        if s.log.live_rate() > 0:
            b = 0.5 + 0.5 * math.sin(now * 7)
            L.t("● ", self.col(mix((40, 160, 70), (210, 255, 220), round(b * 8) / 8)))
            L.t("GENERATING", OK)
        elif run:
            L.t("◉ ", SEC["cpu"].A).t("IDLE", SEC["cpu"].A)
        else:
            L.t("○ ", SUB).t("OFFLINE", SUB)
        if not split:
            L.t("  ").t(model, VAL if run else SUB)
            return [L.render(iw)]
        return [L.render(iw), Line().t(model, VAL if run else SUB).render(iw)]

    def llm_lines(self, iw, ih, now):
        s = self.s
        sec = SEC["llm"]
        log = s.log
        tok = self.anim["l.tok"]
        out = self.status_line(iw, now, iw < 40)
        if ih <= len(out):
            return out[:ih]
        txt = "%.0f" % tok
        frac = min(1.0, tok / 320.0)
        pk = s.h["tok"].peak()
        avg = s.h["tok"].avg()
        size = 2 if (ih - len(out) >= 8 and big_width(txt, 2) + 18 <= iw) else 1
        rows, bw = big_text(txt, q40(frac), size)
        info = [("tok/s", sec.lab, ""),
                ("n_gen ", SUB, str(log.n_gen) if log.n_gen is not None else "-"),
                ("peak  ", SUB, "%.1f" % pk),
                ("avg   ", SUB, "%.0f" % avg)]
        if size == 1:
            info = info[:3]
        else:
            info.insert(1, ("", SUB, ""))
        for i, r in enumerate(rows):
            L = Line().t(" ").raw(r, bw).t("   ")
            if i < len(info):
                lab, c, v = info[i]
                L.t(lab, c).t(v, VAL if i else c)
            out.append(L.render(iw))
        rest = ih - len(out)
        if rest >= 2:
            vmax = max(50.0, pk * 1.1)
            out.extend(self.graph("tok", iw, min(10, rest - 1), vmax, sec.track, cmax=320.0))
        if len(out) < ih:
            L = Line().t("last ", SUB)
            L.t("eval %.1f" % log.last_eval if log.last_eval else "eval -", TEXT)
            L.opt("  prompt %.1f t/s" % log.last_prompt if log.last_prompt else "  prompt -",
                  TEXT, iw)
            L.right("2m avg %.0f" % avg, SUB, iw, optional=True)
            out.append(L.render(iw))
        return out[:ih]

    def hud(self, iw, ih, side):
        g, c, A, s = self.s.gpu, self.s.cpu, self.anim, self.s
        out = []
        blank = " " * iw
        sec = SEC["gpu" if side == "l" else "llm"]

        def item(label, val, vcol, frac):
            out.append(Line().t(label, sec.lab).right(val, vcol, iw).render(iw))
            L = Line()
            bar(L, frac, iw, sec.track)
            out.append(L.render(iw))
            out.append(blank)

        def big(label, txt, unit, frac):
            rows, bw = big_text(txt, q40(frac), 2)
            out.append(Line().t(label, sec.lab).render(iw))
            for i, r in enumerate(rows):
                L = Line().raw(r, bw)
                if i == 4:
                    L.t(" " + unit, SUB)
                out.append(L.render(iw))
            out.append(blank)

        if side == "l":
            ld = A["g.load"]
            big("GPU LOAD", "%.0f" % ld, "%", ld / 100)
            cap = g.cap or 285
            tj, pw = A["g.tj"], A["g.power"]
            out.extend(self.hero(sec, iw, [("JUNCTION", "%.0f" % tj, "°C", tfrac(tj)),
                                           ("POWER", "%.0f" % pw, "W", pw / cap)]))
            out.append(blank)
            tot = g.vram_total / GIB or 1
            item("VRAM", "%.2f / %.1f GiB" % (A["g.vram"], tot), VAL, A["g.vram"] / tot)
            for nm, k in (("EDGE", "g.te"), ("MEM", "g.tm")):
                item(nm, "%.0f°C" % A[k], heat(tfrac(A[k])), tfrac(A[k]))
            item("SCLK", "%.0f MHz" % A["g.sclk"], VAL, A["g.sclk"] / g.sclk_max)
            item("MCLK", "%.0f MHz" % A["g.mclk"], VAL, A["g.mclk"] / g.mclk_max)
            item("FAN", "%.0f rpm" % A["g.fan"], VAL, A["g.fan"] / g.fan_max)
        else:
            tok = A["l.tok"]
            big("TOKENS / S", "%.0f" % tok, "tok/s", min(1, tok / 320))
            out.extend(self.status_line(iw, time.monotonic(), True))
            out.append(blank)
            n = len(c.threads)
            levels = [A["c.t%d" % i] / 100 for i in range(n)]
            peaks = self.peaks if len(self.peaks) == n else levels
            gap = 1 if iw >= 2 * n - 1 else 0
            for r in vbars(levels, peaks, 4, 1, gap, SEC["cpu"].track):
                out.append(Line().raw(r, n * (1 + gap)).render(iw))
            out.append(blank)
            item("CPU", "%.0f%%" % A["c.total"], heat(A["c.total"] / 100), A["c.total"] / 100)
            item("TCTL", "%.1f°C" % A["c.temp"], heat(tfrac(A["c.temp"], 30, 95)),
                 tfrac(A["c.temp"], 30, 95))
            mt = c.mem_total / GIB or 1
            item("RAM", "%.1f / %.1f GiB" % (A["c.ram"], mt), VAL, A["c.ram"] / mt)
            item("FREQ", "%.2f GHz" % (A["c.favg"] / 1000), VAL, A["c.favg"] / c.fmax)
        return out[:ih]

    # ------------------------------------------------------------- layout
    def panel_frame(self, sk, x, y, w, h, title, sub=""):
        """Static sides/bottom of a card (vertical accent gradient); the top edge is
        animated and drawn every frame by top_border()."""
        s = SEC[sk]
        p = self.pre[sk]
        st = self.static
        for i in range(1, h - 1):
            c = fg(mix(s.rgb, s.rgb2, i / max(1, h - 1)))
            st[(y + i, x)] = BG_OFF + c + "│" + p + " "
            st[(y + i, x + w - 2)] = p + " " + BG_OFF + c + "│"
        st[(y + h - 1, x)] = BG_OFF + s.A2 + "╰" + "─" * (w - 2) + "╯"
        self.panels.append((sk, x, y, w, title, sub))
        return (x + 2, y + 1, w - 4, h - 2, sk)

    def top_border(self, i, panel):
        sk, x, y, w, title, sub = panel
        s = SEC[sk]
        chip = " %s %s " % (s.glyph, title)
        tail = " %s " % sub if sub else ""
        fill = w - 6 - len(chip) - len(tail)
        if fill < 2:
            tail = ""
            fill = w - 6 - len(chip)
        if fill < 0:
            chip = chip[:max(0, len(chip) + fill)]
            fill = 0
        parts = [BG_OFF, s.A, "╭─", s.chip, chip, BG_OFF]
        gp = self.glint_pos(i, fill)
        if gp is None:
            parts.append(s.A)
            parts.append("─" * fill)
        else:
            last = None
            for j in range(fill):
                k = 1.0 - abs(j - gp) / 4.0
                c = self.glint_col(sk, int(k * 4 + 0.5) if k > 0 else 0)
                if c is not last:
                    parts.append(c)
                    last = c
                parts.append("─")
        if tail:
            parts.append(SUB)
            parts.append(tail)
        parts += [s.A, "─", self.led(sk), s.A, "─╮"]
        return "".join(parts)

    def glint_pos(self, i, n):
        """A highlight sweeps along each card's top edge every 7 s (staggered per card)."""
        ph = (self.t_anim + i * 1.37) % 7.0
        if ph >= 1.6 or n <= 0:
            return None
        return ph / 1.6 * (n + 10) - 5

    def glint_col(self, sk, lv):
        key = ("g", sk, lv)
        e = self.colcache.get(key)
        if e is None:
            s = SEC[sk]
            e = self.colcache[key] = fg(mix(s.rgb, WHITE, 0.85 * lv / 4.0)) if lv else s.A
        return e

    def led(self, sk):
        """Activity LED: blink rate follows the section's activity, off = hollow."""
        if self.led_act.get(sk) is None:
            return SUB + "○"
        lv = int((0.5 + 0.5 * math.sin(self.led_ph.get(sk, 0.0))) * 8 + 0.5)
        key = ("l", sk, lv)
        e = self.colcache.get(key)
        if e is None:
            s = SEC[sk]
            e = self.colcache[key] = fg(mix(scale(s.rgb, 0.35), mix(s.rgb, WHITE, 0.6),
                                            lv / 8.0)) + "●"
        return e

    def build_layout(self, W, H):
        """Compute regions: dict name -> (x, y, w, h, section) of card interiors."""
        self.static = {}
        self.panels = []
        self.pre = {k: (bg(s.tint_rgb) if self.tint else BG_OFF) for k, s in SEC.items()}
        reg = {}
        g, c = self.s.gpu, self.s.cpu
        if W < MIN_W or H < MIN_H:
            return {"small": None}
        top = 1
        bh = H - 2
        vg = 1 if H >= 40 else 0
        hg = 1
        gsub = "%s · %s" % (g.name, g.gfx) if g.gfx else g.name
        csub = "%s · %dT" % (c.model, c.n)
        core_on = self.use3d and self.layout != 2
        if self.layout == 3 and self.use3d:
            hw = 34 if W >= 140 else 28
            reg["hudl"] = self.panel_frame("gpu", 0, top, hw, bh, "GPU", g.name)
            reg["hudr"] = self.panel_frame("llm", W - hw, top, hw, bh, "LLM · CPU")
            reg["torus"] = self.panel_frame("core", hw + hg, top, W - 2 * hw - 2 * hg, bh,
                                            "REACTOR CORE", "spin=GPU load · hue=Tj · pulse=tok/s")
            return reg
        if W >= 140:
            lw = max(40, int(W * 0.30))
            mw = (W - lw - 2 * hg) // 2
            rw = W - lw - mw - 2 * hg
            x1 = lw + hg
            x2 = x1 + mw + hg
            ioh = max(8, min(12, bh // 4)) if core_on else max(8, bh - 17 - vg)
            reg["reactor"] = self.panel_frame("llm", 0, top, lw, bh - ioh - vg,
                                              "REACTOR · LLM" if core_on else "LLM",
                                              "llama-server")
            reg["io"] = self.panel_frame("io", 0, top + bh - ioh, lw, ioh, "I/O")
            reg["gpu"] = self.panel_frame("gpu", x1, top, mw, bh, "GPU", gsub)
            ch = min(bh - 8, max(18, int(bh * 0.6)))
            reg["cpu"] = self.panel_frame("cpu", x2, top, rw, ch, "CPU", csub)
            reg["procs"] = self.panel_frame("procs", x2, top + ch + vg, rw, bh - ch - vg,
                                            "TOP PROCESSES", "by CPU")
        else:
            lw = (W - hg) // 2
            rw = W - lw - hg
            rh = max(7, min(14, int(bh * 0.36)))
            reg["gpu"] = self.panel_frame("gpu", 0, top, lw, bh - rh - vg, "GPU", gsub)
            reg["reactor_h"] = self.panel_frame("llm", 0, top + bh - rh, lw, rh,
                                                "REACTOR · LLM" if core_on else "LLM")
            ch = max(12, min(bh - 7, int(bh * 0.6)))
            reg["cpu"] = self.panel_frame("cpu", lw + hg, top, rw, ch, "CPU", csub)
            reg["sys"] = self.panel_frame("io", lw + hg, top + ch + vg, rw, bh - ch - vg,
                                          "I/O · PROCESSES")
        return reg

    def torus_box(self, reg):
        """(x, y, w, h, section) of the 3D viewport inside the current layout, or None."""
        if not self.use3d or self.layout == 2:
            return None
        if "torus" in reg:
            return reg["torus"]
        if "reactor" in reg:
            x, y, w, h, sk = reg["reactor"]
            th = min(h - 7, int(w * 0.38))
            return (x, y, w, th, sk) if th >= 6 else None
        if "reactor_h" in reg:
            x, y, w, h, sk = reg["reactor_h"]
            tw = min(w // 2 - 2, int(h * 2.5) + 2)
            return (x, y, tw, h, sk) if tw >= 12 and h >= 4 else None
        return None

    # ------------------------------------------------------------ framing
    def place(self, fr, region, lines):
        x, y, w, h, sk = region
        p = self.pre[sk]
        blank = " " * w
        for i in range(h):
            fr[(y + i, x)] = p + (lines[i] if i < len(lines) else blank)

    def frame(self, W, H, now):
        key = (W, H, self.layout, self.tint)
        if self.geom != key:
            self.geom = key
            self.reg = self.build_layout(W, H)
            self.cache.clear()
            self.full = True
        reg = self.reg
        fr = {}
        seq = self.s.seq
        dirty = self.anim.dirty
        self.anim.dirty = set()
        fr[(0, 0)] = self.header(W)
        fr[(H - 1, 0)] = self.footer(W)
        if "small" in reg:
            msg = "terminal %dx%d too small - need at least %dx%d (100x30 recommended)" % (
                W, H, MIN_W, MIN_H)
            fr[(H // 2, 0)] = BG_OFF + Line().pad_to(max(0, (W - len(msg)) // 2)).t(
                msg, WARN).render(W)
            return fr
        for i, p in enumerate(self.panels):
            fr[(p[2], p[1])] = self.top_border(i, p)
        tb = self.torus_box(reg)

        def put(name, groups, fn, region, *args, extra=0):
            """Rebuild a panel only on new samples, moving animations or a changed key."""
            k = (seq, region, extra)
            e = self.cache.get(name)
            if e is None or e[0] != k or any(gr in dirty for gr in groups):
                lines = fn(region[2], region[3], *args)
                self.cache[name] = (k, lines)
            else:
                lines = e[1]
            self.place(fr, region, lines)

        if "gpu" in reg:
            put("gpu", "g", self.gpu_lines, reg["gpu"])
        if "cpu" in reg:
            put("cpu", "c", self.cpu_lines, reg["cpu"])
        if "io" in reg:
            put("io", "i", self.io_lines, reg["io"])
        if "procs" in reg:
            put("procs", "p", self.proc_lines, reg["procs"])
        if "sys" in reg:
            x, y, w, h, sk = reg["sys"]
            ioh = min(h, max(2, (h + 1) // 2 if h < 12 else 6))
            put("io", "i", self.io_lines, (x, y, w, ioh, sk))
            if h - ioh > 1:
                put("procs", "p", self.proc_lines, (x, y + ioh, w, h - ioh, sk))
        live = self.s.log.live_rate() > 0
        pulse_key = int(now * 8) if live else 0
        for rname in ("reactor", "reactor_h"):
            if rname in reg:
                x, y, w, h, sk = reg[rname]
                p = self.pre[sk]
                if tb is None:
                    region = reg[rname]
                elif rname == "reactor":
                    fr[(y + tb[3], x)] = p + Line().t(
                        "spin = GPU load · hue = Tj · pulse = tok/s", FAINT).render(w)
                    region = (x, y + tb[3] + 1, w, h - tb[3] - 1, sk)
                else:
                    region = (x + tb[2] + 2, y, w - tb[2] - 2, h, sk)
                    for i in range(h):
                        fr[(y + i, x + tb[2])] = p + SEC[sk].track + "│ "
                put("llm", "l", self.llm_lines, region, now, extra=pulse_key)
        if "hudl" in reg:
            put("hudl", "gcl", self.hud, reg["hudl"], "l", extra=pulse_key)
            put("hudr", "gcl", self.hud, reg["hudr"], "r", extra=pulse_key)
        if tb is not None:
            g = self.s.gpu
            hue = (self.anim["g.tj"] - 30.0) / 65.0 if g.t_junc is not None else 0.3
            t = self.t_anim
            rows = self.torus.render(tb[2], tb[3], 0.98 + 0.18 * math.sin(t * 0.23), self.spin,
                                     0.35 * math.sin(t * 0.17), hue, self.wave, self.wave_amp,
                                     1.0 + 0.05 * self.pulse)
            x, y, p = tb[0], tb[1], self.pre[tb[4]]
            for i, r in enumerate(rows):
                fr[(y + i, x)] = p + r
        return fr

    def header(self, W):
        t = self.t_anim
        L = Line().t(" ◢", SEC["gpu"].A)
        for i, ch in enumerate(" R E A C T O R "):
            L.t(ch, heat(0.5 + 0.5 * math.sin(t * 1.6 - i * 0.42)))
        L.t("◣ ", SEC["cpu"].A)
        right = Line()
        if self.paused:
            right.t("‖ PAUSED  ", WARN)
        mem = self.s.cpu
        mt = mem.mem_total or 1
        right.t("RAM ", SUB).t("%.1f" % (mem.mem_used / GIB), heat(mem.mem_used / mt))
        right.t("/%.0fG  " % (mt / GIB), SUB)
        right.t("self ", SUB).t("%4.1f%%" % self.self_cpu, VAL).t(" cpu", SUB)
        right.t("  %d fps  " % self.fps, SUB).t(time.strftime("%H:%M:%S"), VAL).t(" ")
        room = W - right.n - 1
        up = self.s.cpu.uptime
        L.opt(self.host, VAL, room)
        L.opt("  up %dd %02d:%02d" % (up // 86400, up % 86400 // 3600, up % 3600 // 60),
              SUB, room)
        L.opt("   %s  ×  %s" % (self.s.gpu.name, self.s.cpu.model), TEXT, room)
        L.pad_to(W - right.n)
        L.segs.extend(right.segs)
        L.n += right.n
        return HEADER_BG + L.render(W)

    def footer(self, W):
        parts = [BG_OFF, " "]
        n = 1
        for k, d, sk in FOOTER_KEYS:
            chip = " %s " % k
            wd = len(chip) + len(d) + 3
            if n + wd > W:
                break
            parts += [SEC[sk].chip, chip, BG_OFF, TEXT, " ", d, "  "]
            n += wd
        right = "read-only · 2 Hz sampling · layout %d " % self.layout
        if n + len(right) + 1 <= W:
            parts += [" " * (W - n - len(right)), SUB, right]
        else:
            parts.append(" " * (W - n))
        return "".join(parts)

    # ------------------------------------------------------------- main
    def advance(self, dt):
        if self.paused:
            self.anim.step(dt, snap=True)
            return
        A = self.anim
        A.step(dt)
        load = A["g.load"] / 100.0
        self.t_anim += dt
        self.spin += dt * (0.2 + 1.8 * load)
        tok = A["l.tok"]
        target_amp = 0.0 if tok < 1 else min(1.1, 0.35 + tok / 300.0)
        self.wave_amp += (target_amp - self.wave_amp) * min(1.0, dt * 3)
        self.wave = (self.wave + dt * (0.15 + tok / 180.0)) % 1.0
        self.pulse *= math.exp(-dt * 4.0)
        # peak-hold caps of the per-thread bars: hold 1 s, then fall
        n = len(self.s.cpu.threads)
        if len(self.peaks) != n:
            self.peaks = [0.0] * n
            self.hold = [0.0] * n
        falling = False
        for i in range(n):
            v = A["c.t%d" % i] / 100.0
            if v >= self.peaks[i]:
                self.peaks[i] = v
                self.hold[i] = 1.0
            elif self.hold[i] > 0:
                self.hold[i] -= dt
            else:
                self.peaks[i] = max(v, self.peaks[i] - dt * 0.4)
                falling = True
        if falling:
            A.dirty.add("c")
        # section activity LEDs
        io = self.s.io
        cpu = A["c.total"] / 100.0
        if self.s.log.live_rate() > 0:
            llm = 0.75
        else:
            llm = 0.0 if self.s.procs.llama else None
        act = {"gpu": load, "core": load, "cpu": cpu, "procs": cpu, "llm": llm,
               "io": min(1.0, (io.rd + io.wr) / 2e8 + (io.rx + io.tx) / 1.25e7)}
        for k, a in act.items():
            if a is not None:
                self.led_ph[k] = (self.led_ph.get(k, 0.0) + dt * TAU * (0.25 + 2.5 * a)) % TAU
        self.led_act = act

    def run(self, term):
        stop_after = self.args.duration
        t_start = time.monotonic()
        next_frame = last = t_start
        self.sample()
        next_sample = t_start + SAMPLE_DT
        while True:
            now = time.monotonic()
            if stop_after and now - t_start >= stop_after:
                return
            if now >= next_sample:
                self.sample()
                next_sample += SAMPLE_DT
                if next_sample <= now:
                    next_sample = now + SAMPLE_DT
            if self.resized:
                self.resized = False
                self.geom = None
            self.advance(now - last)
            last = now
            W, H = term.size()
            fr = self.frame(W, H, now)
            out = []
            if self.full:
                self.full = False
                self.prev = {}
                out.append("\x1b[0m\x1b[2J")
                for (y, x), s in self.static.items():
                    if y < H and x < W:
                        out.append("\x1b[%d;%dH%s" % (y + 1, x + 1, s))
            prev = self.prev
            for k, s in fr.items():
                if prev.get(k) != s and k[0] < H and k[1] < W:
                    out.append("\x1b[%d;%dH%s" % (k[0] + 1, k[1] + 1, s))
            self.prev = fr
            if out:
                term.write("\x1b[?2026h" + "".join(out) + "\x1b[?2026l")
            # wait for the next frame / sample / key
            if self.paused:
                wake = next_sample
            else:
                next_frame += 1.0 / self.fps
                if next_frame <= now:
                    next_frame = now + 1.0 / self.fps
                wake = min(next_frame, next_sample)
            for ch in term.keys(wake - time.monotonic()).decode("latin-1"):
                if ch in "qQ":
                    return
                if ch in "pP ":
                    self.paused = not self.paused
                elif ch in "+=":
                    self.fps_i = min(len(FPS_STEPS) - 1, self.fps_i + 1)
                    self.fps = FPS_STEPS[self.fps_i]
                elif ch in "-_":
                    self.fps_i = max(0, self.fps_i - 1)
                    self.fps = FPS_STEPS[self.fps_i]
                elif ch in "123":
                    lay = int(ch)
                    if lay == 3 and not self.use3d:
                        lay = 2
                    self.layout = lay
                elif ch in "tT":
                    self.tint = not self.tint
                elif ch in "rR":
                    self.geom = None


def main():
    ap = argparse.ArgumentParser(description="REACTOR - live GPU/CPU/LLM terminal monitor")
    ap.add_argument("--fps", type=int, default=15, help="animation frame rate (default 15)")
    ap.add_argument("--no-3d", action="store_true", help="disable the 3D core (lighter)")
    ap.add_argument("--no-tint", action="store_true",
                    help="no coloured card backgrounds (terminal background shows through)")
    ap.add_argument("--layout", type=int, choices=(1, 2, 3), default=1,
                    help="1 reactor (default), 2 data, 3 core")
    ap.add_argument("--log", default="~/qwen-opt/logs/latest.log",
                    help="llama-server log to tail for tokens/s")
    ap.add_argument("--duration", type=float, default=0,
                    help="exit automatically after N seconds (testing)")
    args = ap.parse_args()
    args.fps = max(1, min(60, args.fps))
    app = App(args)

    def on_winch(*_):
        app.resized = True

    def on_term(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGWINCH, on_winch)
    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGHUP, on_term)
    try:
        with Term() as term:
            app.run(term)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
