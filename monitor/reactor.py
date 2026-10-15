#!/usr/bin/env python3
"""REACTOR - live terminal monitor for the RX 7900 XTX + Ryzen 7 5700X LLM box.

Pure standard library, raw ANSI (24-bit colour, braille, block elements).
Read-only: sysfs/procfs files and the llama-server log. Keys: q quit, p pause,
+/- frame rate, 1/2/3 layout, r redraw.
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

from gfx import (C_ACC, C_ACC2, C_BAD, C_BORDER, C_DIM, C_GRID, C_LABEL, C_OK,  # noqa: E402
                 C_TEXT, C_VAL, C_WARN, RESET, Line, bar, bgraph, big_text, fmt_bytes,
                 fmt_rate, heat, vbars)
from sensors import Sampler  # noqa: E402

FPS_STEPS = (2, 5, 8, 10, 12, 15, 20, 24, 30, 45, 60)
SAMPLE_DT = 0.5
GIB = float(2 ** 30)
LW = 7                       # label column width
MIN_W, MIN_H = 60, 18


def tfrac(t, lo=25.0, hi=100.0):
    return 0.0 if t is None else (t - lo) / (hi - lo)


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

    def set(self, name, target, scale):
        if target is None or target != target:
            target = 0.0
        e = self.v.get(name)
        eps = abs(scale) * 0.0015 or 1e-9
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
        self.write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[2J")
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


class App:
    def __init__(self, args):
        self.args = args
        self.fps_i = min(range(len(FPS_STEPS)), key=lambda i: abs(FPS_STEPS[i] - args.fps))
        self.fps = args.fps
        self.use3d = not args.no_3d
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
        self.cache = {}
        self.gcache = {}
        self.gseq = -1
        self.prev = {}
        self.static = {}
        self.geom = None
        self.full = True
        self.resized = True
        self.now = time.monotonic()

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

    def graph(self, name, w, h, vmax, xform=None, cmax=None):
        if self.s.seq != self.gseq:
            self.gcache.clear()
            self.gseq = self.s.seq
        key = (name, w, h, vmax, cmax)
        r = self.gcache.get(key)
        if r is None:
            vals = list(self.s.h[name].d)
            if xform:
                vals = [None if v is None else xform(v) for v in vals]
            r = self.gcache[key] = bgraph(vals, w, h, vmax, cmax)
        return r

    # ------------------------------------------------------------- panels
    def gpu_lines(self, iw, ih):
        g, A = self.s.gpu, self.anim
        if not g.ok:
            return [Line().t("no amdgpu device found in /sys/class/drm", C_BAD).render(iw)]
        n_proc = max(1, len(self.s.procs.gpu))
        nsep = 6 if ih >= 30 else 0
        _, procs, gl, gp, gt, gv, gs = alloc(ih - nsep, [
            (6, 6), (2, 1 + min(n_proc, 6)), (1, 6), (1, 4), (1, 4), (1, 3), (1, 3)])
        bw = max(4, iw - LW - 17)
        gw = iw - LW
        groups = []

        def barrow(label, frac, segs):
            L = Line().t(label.ljust(LW), C_LABEL)
            bar(L, frac, bw)
            L.t(" ")
            for s, c in segs:
                L.t(s, c)
            groups.append([L.render(iw)])

        def graph(name, h, vmax, peak, xform=None, cmax=None):
            rows = self.graph(name, gw, h, vmax, xform, cmax)
            for i, r in enumerate(rows):
                groups[-1].append(Line().t((peak if i == 0 else "").ljust(LW), C_DIM)
                                  .raw(r, gw).render(iw))

        load = A["g.load"]
        barrow("LOAD", load / 100, [("%3.0f%%" % load, heat(load / 100)),
                                    ("  mem %3.0f%%" % A["g.mbusy"], C_DIM)])
        if gl:
            graph("gpu", gl, 100, "▲%3.0f%%" % self.s.h["gpu"].peak())
        tot = g.vram_total / GIB or 1
        vr = A["g.vram"]
        barrow("VRAM", vr / tot, [("%5.2f" % vr, heat(vr / tot)), ("/%4.1f GiB" % tot, C_DIM)])
        if gv:
            graph("vram", gv, g.vram_total or 1, "▲%4.1fG" % (self.s.h["vram"].peak() / GIB))
        cap = g.cap or 285.0
        pw = A["g.power"]
        barrow("POWER", pw / cap, [("%5.1f" % pw, heat(pw / cap)), ("/%3.0f W" % cap, C_DIM)])
        if gp:
            graph("power", gp, cap, "▲%3.0fW" % self.s.h["power"].peak())
        # temperatures: edge / junction / memory with mini bars
        mb = max(2, (iw - LW - 33) // 3)
        L = Line().t("TEMP".ljust(LW), C_LABEL)
        for nm, key, raw in (("edge", "g.te", g.t_edge), ("junc", "g.tj", g.t_junc),
                             ("mem ", "g.tm", g.t_mem)):
            v = A[key]
            L.t(nm + " ", C_DIM)
            L.t(("%3.0f°" % v) if raw is not None else " n/a", heat(tfrac(v)))
            L.t(" ")
            bar(L, tfrac(v), mb)
            L.t(" ")
        groups.append([L.render(iw)])
        if gt:
            graph("tj", gt, 85.0, "▲%3.0f°" % self.s.h["tj"].peak(),
                  xform=lambda v: v - 25.0, cmax=75.0)
        # clocks
        mb2 = max(2, (iw - LW - 32) // 2)
        L = Line().t("CLOCK".ljust(LW), C_LABEL)
        sc = A["g.sclk"]
        if g.sclk == 0:
            L.t("sclk ", C_DIM).t("  GFXOFF ", C_ACC)
        else:
            L.t("sclk ", C_DIM).t("%4.0f" % sc, heat(sc / g.sclk_max)).t(" MHz ", C_DIM)
        bar(L, sc / g.sclk_max, mb2)
        mc = A["g.mclk"]
        L.t("  mclk ", C_DIM).t("%4.0f" % mc, heat(mc / g.mclk_max)).t(" MHz ", C_DIM)
        bar(L, mc / g.mclk_max, mb2)
        groups.append([L.render(iw)])
        if gs:
            graph("sclk", gs, g.sclk_max, "▲%4.0f" % self.s.h["sclk"].peak())
        # fan / link / dpm
        fan = A["g.fan"]
        L = Line().t("FAN".ljust(LW), C_LABEL)
        L.t("%4.0f" % fan, heat(fan / g.fan_max)).t(" rpm ", C_DIM)
        bar(L, fan / g.fan_max, 6)
        L.opt("  " + g.link, C_TEXT, iw)
        if g.sclk_lvl is not None:
            L.opt("  dpm s%d/%d m%d/%d" % (g.sclk_lvl, g.sclk_nlvl - 1, g.mclk_lvl or 0,
                                           g.mclk_nlvl - 1), C_DIM, iw)
        groups.append([L.render(iw)])
        if procs:
            grp = [Line().t("    PID  ", C_DIM).t("GPU PROCESS (KFD)", C_LABEL)
                   .right("VRAM", C_DIM, iw).render(iw)]
            rows = self.s.procs.gpu[:procs - 1]
            if not rows:
                grp.append(Line().t("         no compute process holds the GPU", C_DIM)
                           .render(iw))
            pb = max(4, iw - 9 - 17 - 10)
            for vram, pid, comm in rows:
                L = Line().t("%7d  " % pid, C_DIM).t(comm[:15].ljust(17), C_TEXT)
                bar(L, vram / (g.vram_total or 1), pb)
                L.right("%6.2f G" % (vram / GIB), heat(vram / (g.vram_total or 1)), iw)
                grp.append(L.render(iw))
            groups.append(grp)
        return stack(groups, ih, iw)

    def cpu_lines(self, iw, ih):
        c, A = self.s.cpu, self.anim
        n = len(c.threads) or 1
        colw, gap = (2, 1) if iw >= n * 3 else (1, 1) if iw >= n * 2 else (1, 0)
        nsep = 5 if ih >= 26 else 0
        eq, _, gtot, gtemp, gram = alloc(ih - nsep, [(4, 9), (5, 5), (1, 4), (1, 3), (1, 2)])
        bw = max(4, iw - LW - 22)
        gw = iw - LW
        groups = []

        def barrow(label, frac, segs):
            L = Line().t(label.ljust(LW), C_LABEL)
            bar(L, frac, bw)
            L.t(" ")
            for s, cc in segs:
                L.t(s, cc)
            groups.append([L.render(iw)])

        def graph(name, h, vmax, peak, xform=None, cmax=None):
            for i, r in enumerate(self.graph(name, gw, h, vmax, xform, cmax)):
                groups[-1].append(Line().t((peak if i == 0 else "").ljust(LW), C_DIM)
                                  .raw(r, gw).render(iw))

        if eq:
            levels = [A["c.t%d" % i] / 100 for i in range(n)]
            width = n * (colw + gap) - gap
            left = max(0, (iw - width) // 2)
            grp = [Line().t(" " * left).raw(r, n * (colw + gap)).render(iw)
                   for r in vbars(levels, eq - 1, colw, gap)]
            L = Line().t(" " * left)
            for i in range(n):
                v = A["c.t%d" % i]
                s = ("%2d" % min(99, v)) if colw == 2 else ("%x" % i)
                L.t(s, heat(v / 100) if colw == 2 else C_DIM)
                if gap:
                    L.t(" " * gap)
            grp.append(L.render(iw))
            groups.append(grp)
        tot = A["c.total"]
        barrow("TOTAL", tot / 100, [("%3.0f%%" % tot, heat(tot / 100)),
                                    ("  load %4.2f" % c.load[0], C_DIM)])
        if gtot:
            graph("cpu", gtot, 100, "▲%3.0f%%" % self.s.h["cpu"].peak())
        t = A["c.temp"]
        segs = [("%5.1f°C" % t, heat(tfrac(t, 30, 95)))]
        if c.nvme_temp is not None:
            segs.append(("  nvme %2.0f°" % c.nvme_temp, C_DIM))
        barrow("TCTL", tfrac(t, 30, 95), segs)
        if gtemp:
            graph("ctemp", gtemp, 65.0, "▲%3.0f°" % self.s.h["ctemp"].peak(),
                  xform=lambda v: v - 30.0)
        fa, fm = A["c.favg"], A["c.fmax"]
        barrow("FREQ", fa / c.fmax, [("%4.2f" % (fa / 1000), heat(fa / c.fmax)),
                                     (" max %4.2f GHz" % (fm / 1000), C_DIM)])
        mt = c.mem_total / GIB or 1
        ram = A["c.ram"]
        barrow("RAM", ram / mt, [("%5.1f" % ram, heat(ram / mt)), ("/%4.1f GiB" % mt, C_DIM)])
        if gram:
            graph("ram", gram, c.mem_total or 1, "▲%4.1fG" % (self.s.h["ram"].peak() / GIB))
        st = c.swap_total / GIB
        sw = A["c.swap"]
        barrow("SWAP", sw / st if st else 0, [("%5.1f" % sw, heat(sw / st if st else 0)),
                                              ("/%4.1f GiB" % st, C_DIM)])
        return stack(groups, ih, iw)

    def io_lines(self, iw, ih):
        io, h = self.s.io, self.s.h
        dg, ng = alloc(max(0, ih - 2), [(2, 10), (2, 10)])
        gw = iw - LW
        out = []
        dmax = max(h["rd"].peak(), h["wr"].peak(), 1e6)
        nmax = max(h["rx"].peak(), h["tx"].peak(), 1.25e5)

        def rate_row(label, a_lbl, a, b_lbl, b, vmax, extra=""):
            L = Line().t(label.ljust(LW), C_LABEL)
            L.t(a_lbl, C_DIM).t(fmt_rate(a), heat(a / vmax)).t("  " + b_lbl, C_DIM)
            L.t(fmt_rate(b), heat(b / vmax))
            if extra:
                L.right(extra, C_GRID, iw, optional=True)
            out.append(L.render(iw))

        def graphs(n, a, b, la, lb, vmax):
            ha = (n + 1) // 2
            hb = n - ha
            for name, hh, lbl in ((a, ha, la), (b, hb, lb)):
                for i, r in enumerate(self.graph(name, gw, hh, vmax) if hh else []):
                    out.append(Line().t((lbl if i == 0 else "").rjust(LW - 1).ljust(LW), C_DIM)
                               .raw(r, gw).render(iw))

        rate_row("DISK", "R ", io.rd, "W ", io.wr, dmax, "▲" + fmt_rate(dmax).strip())
        if dg:
            graphs(dg, "rd", "wr", "read", "write", dmax)
        rate_row("NET", "↓ ", io.rx, "↑ ", io.tx, nmax, "▲" + fmt_rate(nmax).strip())
        if ng:
            graphs(ng, "rx", "tx", "down", "up", nmax)
        return out[:ih]

    def proc_lines(self, iw, ih):
        out = [Line().t("    PID  ", C_DIM).t("PROCESS", C_LABEL).right("CPU%      RSS", C_DIM, iw)
               .render(iw)]
        pb = max(3, iw - 9 - 17 - 16)
        for cpu, rss, pid, comm in self.s.procs.top[:max(0, ih - 1)]:
            L = Line().t("%7d  " % pid, C_DIM)
            L.t(comm[:15].ljust(17), C_ACC if comm == "llama-server" else C_TEXT)
            bar(L, cpu / 100.0, pb)
            L.right("%5.1f" % cpu, heat(cpu / 100), iw - 9).right(fmt_bytes(rss), C_TEXT, iw)
            out.append(L.render(iw))
        return out

    def llm_lines(self, iw, ih, now):
        s = self.s
        log, run = s.log, s.procs.llama
        tok = self.anim["l.tok"]
        live = log.live_rate() > 0
        model = (run[1] if run and run[1] else None) or log.model or "-"
        L = Line()
        if live:
            L.t("● ", heat(0.55 + 0.45 * math.sin(now * 7))).t("GENERATING", C_OK)
        elif run:
            L.t("○ ", C_ACC).t("IDLE", C_ACC)
        else:
            L.t("○ ", C_DIM).t("OFFLINE", C_DIM)
        if iw >= 40:
            L.t("  ").t(model, C_VAL if run else C_DIM)
            out = [L.render(iw)]
        else:
            out = [L.render(iw), Line().t(model, C_VAL if run else C_DIM).render(iw)]
        if ih < 2:
            return out
        txt = ("%.1f" % tok) if tok < 1000 else "%d" % tok
        tf = min(1.0, tok / 320.0)
        q = lambda x: round(x * 20) / 20.0  # noqa: E731
        rows, bw = big_text(txt, q(tf * 0.55), q(tf))
        pk = s.h["tok"].peak()
        side = [Line().t("tok/s", C_LABEL),
                Line().t("n_gen ", C_DIM).t(str(log.n_gen) if log.n_gen is not None else "-", C_TEXT),
                Line().t("peak  ", C_DIM).t("%.1f" % pk, heat(min(1, pk / 320)))]
        for i in range(3):
            L = Line().t(" ").raw(rows[i], bw).t("  ")
            for seg in side[i].segs:
                L.t(seg[1], seg[0])
            out.append(L.render(iw))
        rest = ih - len(out)
        if rest >= 2:
            gh = min(10, rest - 1)
            vmax = max(50.0, pk * 1.1)
            for r in self.graph("tok", iw, gh, vmax, cmax=320.0):
                out.append(r)
        if len(out) < ih:
            L = Line().t("last ", C_DIM)
            L.t("eval %.1f" % log.last_eval if log.last_eval else "eval -", C_TEXT)
            L.opt("  prompt %.1f t/s" % log.last_prompt if log.last_prompt else "  prompt -",
                  C_TEXT, iw)
            L.right("2m avg %.0f" % s.h["tok"].avg(), C_DIM, iw, optional=True)
            out.append(L.render(iw))
        return out

    # ------------------------------------------------------------- layout
    def panel_frame(self, x, y, w, h, title, sub=""):
        """Static border into self.static."""
        st = self.static
        inner = w - 2
        L = Line().t("╭─", C_BORDER).t("▐", C_ACC).t(" " + title + " ", C_VAL).t("▌", C_ACC)
        tail = (" " + sub + " ") if sub else ""
        fill = inner - (L.n - 1) - len(tail) - 1
        if fill < 1:
            tail, fill = "", inner - (L.n - 1) - 1
        L.t("─" * max(0, fill), C_BORDER).t(tail, C_DIM).t("─╮", C_BORDER)
        st[(y, x)] = L.render(w)
        for i in range(1, h - 1):
            st[(y + i, x)] = C_BORDER + "│ "
            st[(y + i, x + w - 2)] = C_BORDER + " │"
        st[(y + h - 1, x)] = C_BORDER + "╰" + "─" * (w - 2) + "╯"
        return (x + 2, y + 1, w - 4, h - 2)

    def build_layout(self, W, H):
        """Compute regions: dict name -> (x, y, w, h) of panel interiors."""
        self.static = {}
        reg = {}
        g, c = self.s.gpu, self.s.cpu
        top, bot = 1, H - 1
        bh = bot - top
        gsub = "%s · %s" % (g.name, g.gfx) if g.gfx else g.name
        csub = "%s · %dT" % (c.model, c.n)
        if W < MIN_W or H < MIN_H:
            return {"small": None}
        if self.layout == 3 and self.use3d:
            hw = 34 if W >= 140 else 26
            reg["hudl"] = self.panel_frame(0, top, hw, bh, "GPU", g.name)
            reg["hudr"] = self.panel_frame(W - hw, top, hw, bh, "CPU · LLM")
            reg["torus"] = (hw + 1, top, W - 2 * hw - 2, bh)
            return reg
        if W >= 140:
            lw = max(40, int(W * 0.30))
            mw = (W - lw) // 2
            rw = W - lw - mw
            if self.use3d and self.layout == 1:
                ioh = max(8, min(12, bh // 4))
                title = "REACTOR CORE"
            else:
                ioh = max(8, bh - 17)
                title = "LLM"
            reg["reactor"] = self.panel_frame(0, top, lw, bh - ioh, title, "llama-server")
            reg["io"] = self.panel_frame(0, top + bh - ioh, lw, ioh, "I/O")
            reg["gpu"] = self.panel_frame(lw, top, mw, bh, "GPU", gsub)
            ch = min(bh - 6, max(18, int(bh * 0.6)))
            reg["cpu"] = self.panel_frame(lw + mw, top, rw, ch, "CPU", csub)
            reg["procs"] = self.panel_frame(lw + mw, top + ch, rw, bh - ch, "TOP PROCESSES",
                                            "by CPU")
        else:
            lw = W // 2
            rw = W - lw
            rh = max(7, min(14, int(bh * 0.36)))
            reg["gpu"] = self.panel_frame(0, top, lw, bh - rh, "GPU", gsub)
            reg["reactor_h"] = self.panel_frame(0, top + bh - rh, lw, rh, "REACTOR", "LLM")
            ch = max(12, min(bh - 7, int(bh * 0.6)))
            reg["cpu"] = self.panel_frame(lw, top, rw, ch, "CPU", csub)
            reg["sys"] = self.panel_frame(lw, top + ch, rw, bh - ch, "I/O · PROCESSES")
        return reg

    def torus_box(self, reg):
        """(x, y, w, h) of the 3D viewport inside the current layout, or None."""
        if not self.use3d or self.layout == 2:
            return None
        if "torus" in reg:
            x, y, w, h = reg["torus"]
            return (x, y, w, h)
        if "reactor" in reg:
            x, y, w, h = reg["reactor"]
            th = min(h - 7, int(w * 0.38))
            return (x, y, w, th) if th >= 6 else None
        if "reactor_h" in reg:
            x, y, w, h = reg["reactor_h"]
            tw = min(w // 2 - 2, int(h * 2.5) + 2)
            return (x, y, tw, h) if tw >= 12 and h >= 4 else None
        return None

    # ------------------------------------------------------------ framing
    def place(self, fr, region, lines):
        x, y, w, h = region
        blank = " " * w
        for i in range(h):
            fr[(y + i, x)] = lines[i] if i < len(lines) else blank

    def hud(self, iw, ih, side):
        g, c, A, s = self.s.gpu, self.s.cpu, self.anim, self.s
        out = []

        def item(label, val, vcol, frac):
            out.append(Line().t(label, C_LABEL).right(val, vcol, iw).render(iw))
            L = Line()
            bar(L, frac, iw)
            out.append(L.render(iw))
            out.append(" " * iw)

        def big(val, frac, unit):
            rows, bw = big_text(val, round(frac * 10) / 20, round(frac * 20) / 20)
            for i, r in enumerate(rows):
                L = Line().raw(r, bw)
                if i == 2:
                    L.t(" " + unit, C_LABEL)
                out.append(L.render(iw))
            out.append(" " * iw)

        if side == "l":
            ld = A["g.load"]
            big("%.0f" % ld, ld / 100, "% GPU")
            tot = g.vram_total / GIB or 1
            item("VRAM", "%.2f / %.1f GiB" % (A["g.vram"], tot), C_VAL, A["g.vram"] / tot)
            cap = g.cap or 285
            item("POWER", "%.1f / %.0f W" % (A["g.power"], cap), heat(A["g.power"] / cap),
                 A["g.power"] / cap)
            for nm, k in (("JUNCTION", "g.tj"), ("EDGE", "g.te"), ("MEM", "g.tm")):
                item(nm, "%.0f°C" % A[k], heat(tfrac(A[k])), tfrac(A[k]))
            item("SCLK", "%.0f MHz" % A["g.sclk"], C_VAL, A["g.sclk"] / g.sclk_max)
            item("MCLK", "%.0f MHz" % A["g.mclk"], C_VAL, A["g.mclk"] / g.mclk_max)
            item("FAN", "%.0f rpm" % A["g.fan"], C_VAL, A["g.fan"] / g.fan_max)
        else:
            tok = A["l.tok"]
            big("%.1f" % tok, min(1, tok / 320), "tok/s")
            run = s.procs.llama
            out.append(Line().t((run[1] if run and run[1] else s.log.model) or "llama-server offline",
                                C_VAL if run else C_DIM).render(iw))
            out.append(" " * iw)
            n = len(c.threads)
            for r in vbars([A["c.t%d" % i] / 100 for i in range(n)], 3, 1, 0):
                out.append(Line().raw(r, n).render(iw))
            out.append(" " * iw)
            item("CPU", "%.0f%%" % A["c.total"], heat(A["c.total"] / 100), A["c.total"] / 100)
            item("TCTL", "%.1f°C" % A["c.temp"], heat(tfrac(A["c.temp"], 30, 95)),
                 tfrac(A["c.temp"], 30, 95))
            mt = c.mem_total / GIB or 1
            item("RAM", "%.1f / %.1f GiB" % (A["c.ram"], mt), C_VAL, A["c.ram"] / mt)
            item("FREQ", "%.2f GHz" % (A["c.favg"] / 1000), C_VAL, A["c.favg"] / c.fmax)
        return out[:ih]

    def frame(self, W, H, now):
        if self.geom != (W, H, self.layout):
            self.geom = (W, H, self.layout)
            self.reg = self.build_layout(W, H)
            self.cache.clear()
            self.full = True
        reg = self.reg
        fr = {}
        seq = self.s.seq
        dirty = self.anim.dirty
        self.anim.dirty = set()
        fr[(0, 0)] = self.header(W, now)
        fr[(H - 1, 0)] = self.footer(W)
        if "small" in reg:
            msg = "terminal %dx%d too small - need at least %dx%d (100x30 recommended)" % (
                W, H, MIN_W, MIN_H)
            fr[(H // 2, 0)] = Line().pad_to(max(0, (W - len(msg)) // 2)).t(msg, C_WARN).render(W)
            return fr
        tb = self.torus_box(reg)

        def put(name, groups, fn, region, *args, extra=0):
            """Rebuild a panel only on new samples, moving animations or a changed key."""
            key = (seq, region, extra)
            e = self.cache.get(name)
            if e is None or e[0] != key or any(gr in dirty for gr in groups):
                lines = fn(region[2], region[3], *args)
                self.cache[name] = (key, lines)
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
            x, y, w, h = reg["sys"]
            ioh = min(h, max(2, (h + 1) // 2 if h < 12 else 6))
            put("io", "i", self.io_lines, (x, y, w, ioh))
            if h - ioh > 1:
                put("procs", "p", self.proc_lines, (x, y + ioh, w, h - ioh))
        live = self.s.log.live_rate() > 0
        pulse_key = int(now * 8) if live else 0
        for rname in ("reactor", "reactor_h"):
            if rname in reg:
                x, y, w, h = reg[rname]
                if tb is None:
                    region = (x, y, w, h)
                elif rname == "reactor":
                    fr[(y + tb[3], x)] = Line().t(
                        "spin = GPU load · hue = Tj · pulse = tok/s", C_GRID).render(w)
                    region = (x, y + tb[3] + 1, w, h - tb[3] - 1)
                else:
                    region = (x + tb[2] + 2, y, w - tb[2] - 2, h)
                    for i in range(h):
                        fr[(y + i, x + tb[2])] = C_GRID + "│ "
                put("llm", "l", self.llm_lines, region, now, extra=pulse_key)
        if "hudl" in reg:
            for side, rn in (("l", "hudl"), ("r", "hudr")):
                put(rn, "gcl", self.hud, reg[rn], side)
        if tb is not None:
            g = self.s.gpu
            hue = (self.anim["g.tj"] - 30.0) / 65.0 if g.t_junc is not None else 0.3
            t = self.t_anim
            rows = self.torus.render(tb[2], tb[3], 0.98 + 0.18 * math.sin(t * 0.23), self.spin,
                                     0.35 * math.sin(t * 0.17), hue, self.wave, self.wave_amp,
                                     1.0 + 0.05 * self.pulse)
            x, y = tb[0], tb[1]
            for i, r in enumerate(rows):
                fr[(y + i, x)] = r
        return fr

    def header(self, W, now):
        L = Line()
        ph = 0.0 if self.paused else now
        title = "R E A C T O R"
        L.t(" ▐", C_ACC2)
        for i, ch in enumerate(title):
            L.t(ch, heat(0.55 + 0.45 * math.sin(ph * 2.2 - i * 0.45)))
        L.t("▌ ", C_ACC2)
        right = Line()
        if self.paused:
            right.t("‖ PAUSED  ", C_WARN)
        right.t("self ", C_DIM).t("%4.1f%% cpu" % self.self_cpu, C_TEXT)
        right.t("  %d fps  " % self.fps, C_DIM).t(time.strftime("%H:%M:%S"), C_VAL).t(" ")
        room = W - right.n - 1
        up = self.s.cpu.uptime
        L.opt(self.host, C_VAL, room)
        L.opt("  up %dd %02d:%02d" % (up // 86400, up % 86400 // 3600, up % 3600 // 60),
              C_DIM, room)
        L.opt("   %s  ×  %s" % (self.s.gpu.name, self.s.cpu.model), C_LABEL, room)
        L.pad_to(W - right.n)
        L.segs.extend(right.segs)
        L.n += right.n
        return L.render(W)

    def footer(self, W):
        L = Line().t(" ")
        for k, d in (("q", "quit"), ("p", "pause"), ("+/-", "fps"), ("1", "reactor"),
                     ("2", "data"), ("3", "core"), ("r", "redraw")):
            L.t(k, C_ACC).t(" " + d + "   ", C_DIM)
        L.right("sysfs read-only · 2 Hz sampling · layout %d " % self.layout, C_GRID, W,
                optional=True)
        return L.render(W)

    # ------------------------------------------------------------- main
    def advance(self, dt):
        if self.paused:
            self.anim.step(dt, snap=True)
            return
        self.anim.step(dt)
        load = self.anim["g.load"] / 100.0
        self.t_anim += dt
        self.spin += dt * (0.2 + 1.8 * load)
        tok = self.anim["l.tok"]
        target_amp = 0.0 if tok < 1 else min(1.1, 0.35 + tok / 300.0)
        self.wave_amp += (target_amp - self.wave_amp) * min(1.0, dt * 3)
        self.wave = (self.wave + dt * (0.15 + tok / 180.0)) % 1.0
        self.pulse *= math.exp(-dt * 4.0)

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
                out.append("\x1b[2J")
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
                elif ch in "rR":
                    self.geom = None


def main():
    ap = argparse.ArgumentParser(description="REACTOR - live GPU/CPU/LLM terminal monitor")
    ap.add_argument("--fps", type=int, default=15, help="animation frame rate (default 15)")
    ap.add_argument("--no-3d", action="store_true", help="disable the 3D core (lighter)")
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
