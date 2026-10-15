"""Real-time shaded wireframe torus rendered into braille dots (2x4 per cell).

Motion is driven by the caller: tumble speed (GPU load), hue (junction temp),
an energy wave running around the ring (tokens/s) and a scale pulse.
Geometry is precomputed; per frame each point costs one rotation + projection.
"""
import math

from gfx import HEAT_RGB, N as HEAT_N, esc_fg

R_MAJOR = 1.0
R_MINOR = 0.42
K2 = 4.2                        # camera distance
LIGHT = (-0.45, 0.65, -0.62)    # view space, towards the light (y up, viewer at -z)
NB = 64                          # wave buckets around the major angle
LEVELS = 20                      # 0..15 normal shading, 16..19 over-bright (wave)

# braille dot bits indexed by (row & 3) * 2 + (col & 1)
_BIT = (0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80)


def _shade_table(hue_idx):
    r0, g0, b0 = HEAT_RGB[hue_idx]
    out = []
    for lv in range(LEVELS):
        if lv < 16:
            k = 0.10 + 0.90 * (lv / 15.0) ** 1.15
            out.append(esc_fg(int(r0 * k), int(g0 * k), int(b0 * k)))
        else:
            u = (lv - 15) / 4.0        # blend towards white-hot
            out.append(esc_fg(int(r0 + (255 - r0) * u), int(g0 + (255 - g0) * u),
                              int(b0 + (255 - b0) * u)))
    return out


_SHADES = {}


def shades(hue):
    i = int(max(0.0, min(1.0, hue)) * (HEAT_N - 1)) & ~1     # 64 distinct hues
    t = _SHADES.get(i)
    if t is None:
        t = _SHADES[i] = _shade_table(i)
    return t


class Torus:
    def __init__(self):
        self._geo_key = None
        self.pts = []
        self._k1 = None
        self._k1_box = None
        # coarse surface grid used to fit the perspective projection into the viewport
        self.fit_pts = []
        for i in range(24):
            phi = 2 * math.pi * i / 24
            for j in range(8):
                th = 2 * math.pi * j / 8
                rr = R_MAJOR + R_MINOR * math.cos(th)
                self.fit_pts.append((rr * math.cos(phi), rr * math.sin(phi),
                                     R_MINOR * math.sin(th)))

    N_PAR = 4          # rings around the tube (parallels)
    N_MER = 12         # rings around the hole (meridians)
    SPACING = 1.2      # target distance between samples, in braille dots
    PHASE = 0.0        # angular offset of the first parallel on the tube

    def _geometry(self, d):
        """Point cloud of meridians + parallels with ~SPACING dots between samples at a
        projected torus diameter of about d dots."""
        key = max(8, min(400, d)) // 8
        if key == self._geo_key:
            return
        self._geo_key = key
        unit = key * 8 * 0.5 / (R_MAJOR + R_MINOR)       # dots per world unit
        pts = []

        def add(phi, th):
            cp, sph = math.cos(phi), math.sin(phi)
            ct, st = math.cos(th), math.sin(th)
            rr = R_MAJOR + R_MINOR * ct
            nx, ny, nz = ct * cp, ct * sph, st
            b = int((phi % (2 * math.pi)) / (2 * math.pi) * NB) % NB
            pts.append((rr * cp, rr * sph, R_MINOR * st, nx, ny, nz, b))

        for i in range(self.N_PAR):
            th = 2 * math.pi * i / self.N_PAR + self.PHASE
            rr = R_MAJOR + R_MINOR * math.cos(th)
            n = max(24, int(2 * math.pi * rr * unit / self.SPACING))
            for j in range(n):
                add(2 * math.pi * j / n, th)
        n = max(10, int(2 * math.pi * R_MINOR * unit / self.SPACING))
        for i in range(self.N_MER):
            phi = 2 * math.pi * i / self.N_MER
            for j in range(n):
                add(phi, 2 * math.pi * j / n)
        self.pts = pts

    def render(self, w, h, tilt, spin, yaw, hue, wave_pos, wave_amp, scale=1.0):
        """Returns h strings of w visible cells.

        spin: rotation about the torus' own axis, tilt: about screen x (0 = face-on),
        yaw: about screen y. R = Ry(yaw) . Rx(tilt) . Rz(spin)."""
        dw, dh = 2 * w, 4 * h
        self._geometry(min(dw, dh))
        cs, ss = math.cos(spin), math.sin(spin)
        ct, st = math.cos(tilt), math.sin(tilt)
        cy_, sy_ = math.cos(yaw), math.sin(yaw)
        m0 = (cs, -ss, 0.0)
        m1 = (ct * ss, ct * cs, -st)
        m2 = (st * ss, st * cs, ct)
        r00, r01, r02 = (cy_ * m0[i] + sy_ * m2[i] for i in range(3))
        r10, r11, r12 = m1
        r20, r21, r22 = (-sy_ * m0[i] + cy_ * m2[i] for i in range(3))
        lx, ly, lz = LIGHT
        n = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / n, ly / n, lz / n
        # light in object space: R^T L
        ox = r00 * lx + r10 * ly + r20 * lz
        oy = r01 * lx + r11 * ly + r21 * lz
        oz = r02 * lx + r12 * ly + r22 * lz
        # fit: projected extent of a coarse surface grid, smoothed to avoid size jitter
        mx = my = 1e-6
        for x, y, z in self.fit_pts:
            iz = 1.0 / (r20 * x + r21 * y + r22 * z + K2)
            px = (r00 * x + r01 * y + r02 * z) * iz
            py = (r10 * x + r11 * y + r12 * z) * iz
            if px < 0.0:
                px = -px
            if py < 0.0:
                py = -py
            if px > mx:
                mx = px
            if py > my:
                my = py
        k1t = min((dw * 0.5 - 2) / mx, (dh * 0.5 - 2) / my)
        if self._k1 is None or self._k1_box != (w, h):
            self._k1, self._k1_box = k1t, (w, h)
        else:
            self._k1 += (k1t - self._k1) * 0.25
        k1 = self._k1 * scale
        cx, cy = dw * 0.5, dh * 0.5
        # wave brightness per major-angle bucket (comet with a tail)
        wb = [0.0] * NB
        if wave_amp > 0.01:
            head = int(wave_pos * NB) % NB
            tail = 10
            for k in range(tail):
                wb[(head - k) % NB] = wave_amp * (1.0 - k / tail)
                wb[(head - k + NB // 2) % NB] = wave_amp * 0.6 * (1.0 - k / tail)
        ncell = w * h
        bits = [0] * ncell        # front-facing dots
        back = [0] * ncell        # back-facing dots, shown only in otherwise empty cells
        lum = [0.0] * ncell
        bit = _BIT
        for x, y, z, nx, ny, nz, bk in self.pts:
            ooz = k1 / (r20 * x + r21 * y + r22 * z + K2)
            xs = int(cx + (r00 * x + r01 * y + r02 * z) * ooz)
            ys = int(cy - (r10 * x + r11 * y + r12 * z) * ooz)
            if xs < 0 or ys < 0 or xs >= dw or ys >= dh:
                continue
            ci = (ys >> 2) * w + (xs >> 1)
            if r20 * nx + r21 * ny + r22 * nz >= 0.0:          # facing away
                back[ci] |= bit[((ys & 3) << 1) | (xs & 1)]
                continue
            l = ox * nx + oy * ny + oz * nz
            v = (0.22 + 0.78 * l if l > 0.0 else 0.22) + wb[bk]
            bits[ci] |= bit[((ys & 3) << 1) | (xs & 1)]
            if v > lum[ci]:
                lum[ci] = v
        tab = shades(hue)
        ghost = tab[3]
        rows = []
        top = LEVELS - 1
        for r in range(h):
            parts = []
            last = None
            base = r * w
            for c in range(w):
                bt = bits[base + c]
                if bt:
                    lv = int(lum[base + c] * 15.0)
                    col = tab[lv if lv < top else top]
                elif back[base + c]:
                    bt = back[base + c]
                    col = ghost
                else:
                    parts.append(" ")
                    continue
                if col is not last:
                    parts.append(col)
                    last = col
                parts.append(chr(0x2800 | bt))
            rows.append("".join(parts))
        return rows
