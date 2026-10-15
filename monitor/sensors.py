"""Read-only data collection for reactor.py (sysfs / procfs / llama-server log).

Everything here only *reads* files. File descriptors of frequently polled
files are kept open and re-read with pread(…, 0) to avoid open/close churn.
Nothing touches /dev/kfd or /dev/dri.
"""
import glob
import os
import time
from collections import deque

HIST = 240                      # samples kept per metric (2 min at 2 Hz)
CLK_TCK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")


class PFile:
    """A read-only fd that is re-read from offset 0 on every call."""
    __slots__ = ("fd",)

    def __init__(self, path):
        try:
            self.fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
        except OSError:
            self.fd = None

    def read(self, n=65536):
        if self.fd is None:
            return b""
        try:
            return os.pread(self.fd, n, 0)
        except OSError:
            return b""

    def int(self):
        b = self.read(64)
        try:
            return int(b.split()[0])
        except (ValueError, IndexError):
            return None


def _rd(path, n=65536):
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def _int(path):
    try:
        return int(_rd(path, 64).split()[0])
    except (ValueError, IndexError):
        return None


def _dpm(raw):
    """Parse pp_dpm_* -> (current_mhz or None, max_mhz, current_index, n_levels)."""
    cur = None
    idx = None
    mx = 0
    lines = raw.decode("ascii", "replace").strip().splitlines()
    for i, ln in enumerate(lines):
        try:
            mhz = int(ln.split(":")[1].split("Mhz")[0])
        except (IndexError, ValueError):
            continue
        mx = max(mx, mhz)
        if ln.rstrip().endswith("*"):
            cur, idx = mhz, i
    return cur, mx, idx, len(lines)


class Hist:
    """Fixed-size history of one metric."""
    __slots__ = ("d",)

    def __init__(self):
        self.d = deque(maxlen=HIST)

    def push(self, v):
        self.d.append(v)

    def peak(self):
        vals = [v for v in self.d if v is not None]
        return max(vals) if vals else 0.0

    def avg(self):
        vals = [v for v in self.d if v is not None]
        return sum(vals) / len(vals) if vals else 0.0


# --------------------------------------------------------------------- GPU
_GPU_NAMES = {"0x744c": "RX 7900 XT", "0x7448": "RX 7900 GRE", "0x7480": "RX 7600"}


def find_amdgpu():
    best = None
    for card in sorted(glob.glob("/sys/class/drm/card[0-9]*")):
        if "-" in os.path.basename(card):
            continue
        dev = card + "/device"
        if not os.path.realpath(dev + "/driver").endswith("/amdgpu"):
            continue
        total = _int(dev + "/mem_info_vram_total") or 0
        if best is None or total > best[1]:
            best = (dev, total)
    return best[0] if best else None


class GPU:
    def __init__(self):
        self.dev = find_amdgpu()
        self.ok = self.dev is not None
        d = self.dev or "/nonexistent"
        hw = sorted(glob.glob(d + "/hwmon/hwmon*"))
        h = hw[0] if hw else "/nonexistent"
        self.f_busy = PFile(d + "/gpu_busy_percent")
        self.f_mbusy = PFile(d + "/mem_busy_percent")
        self.f_vused = PFile(d + "/mem_info_vram_used")
        self.f_sclk_dpm = PFile(d + "/pp_dpm_sclk")
        self.f_mclk_dpm = PFile(d + "/pp_dpm_mclk")
        self.f_edge = PFile(h + "/temp1_input")
        self.f_junc = PFile(h + "/temp2_input")
        self.f_mem = PFile(h + "/temp3_input")
        self.f_power = PFile(h + "/power1_average")
        if self.f_power.fd is None:
            self.f_power = PFile(h + "/power1_input")
        self.f_cap = PFile(h + "/power1_cap")
        self.f_fan = PFile(h + "/fan1_input")
        self.f_sclk = PFile(h + "/freq1_input")
        self.f_mclk = PFile(h + "/freq2_input")
        self.vram_total = _int(d + "/mem_info_vram_total") or 0
        self.fan_max = _int(h + "/fan1_max") or 3600
        self.crit_junc = (_int(h + "/temp2_crit") or 110000) / 1000.0
        devid = _rd(d + "/device").decode().strip()
        name = _GPU_NAMES.get(devid, "AMD GPU %s" % devid)
        if devid == "0x744c" and self.vram_total > 22 * 2**30:
            name = "RX 7900 XTX"
        self.name = name
        self.gfx = ""
        for props in glob.glob("/sys/class/kfd/kfd/topology/nodes/*/properties"):
            for ln in _rd(props).decode().splitlines():
                if ln.startswith("gfx_target_version"):
                    v = int(ln.split()[1])
                    if v:
                        self.gfx = "gfx%d%x%x" % (v // 10000, (v // 100) % 100, v % 100)
        self.link = ""
        self.read_link()
        _, self.sclk_max, _, _ = _dpm(self.f_sclk_dpm.read())
        _, self.mclk_max, _, _ = _dpm(self.f_mclk_dpm.read())
        self.sclk_max = self.sclk_max or 3000
        self.mclk_max = self.mclk_max or 1250
        self.cap = 0.0
        # current values
        self.busy = self.mbusy = None
        self.vram_used = None
        self.t_edge = self.t_junc = self.t_mem = None
        self.power = None
        self.fan = None
        self.sclk = self.mclk = None
        self.sclk_lvl = self.mclk_lvl = None
        self.sclk_nlvl = self.mclk_nlvl = 0

    def read_link(self):
        d = self.dev or "/nonexistent"
        sp = _rd(d + "/current_link_speed").decode().strip().replace(" PCIe", "")
        wd = _rd(d + "/current_link_width").decode().strip()
        gen = {"2.5": 1, "5.0": 2, "8.0": 3, "16.0": 4, "32.0": 5}.get(sp.split(" ")[0])
        if gen:
            self.link = "PCIe%d x%s" % (gen, wd)
        else:
            self.link = ("PCIe %s x%s" % (sp, wd)) if sp else ""

    def sample(self):
        if not self.ok:
            return

        def t(f):
            v = f.int()
            return v / 1000.0 if v is not None else None

        self.busy = self.f_busy.int()
        self.mbusy = self.f_mbusy.int()
        self.vram_used = self.f_vused.int()
        self.t_edge = t(self.f_edge)
        self.t_junc = t(self.f_junc)
        self.t_mem = t(self.f_mem)
        p = self.f_power.int()
        self.power = p / 1e6 if p is not None else None
        c = self.f_cap.int()
        self.cap = c / 1e6 if c else 285.0
        self.fan = self.f_fan.int()
        s = self.f_sclk.int()
        m = self.f_mclk.int()
        self.sclk = s / 1e6 if s is not None else None
        self.mclk = m / 1e6 if m is not None else None
        _, _, self.sclk_lvl, self.sclk_nlvl = _dpm(self.f_sclk_dpm.read())
        _, _, self.mclk_lvl, self.mclk_nlvl = _dpm(self.f_mclk_dpm.read())


# --------------------------------------------------------------------- CPU
def _hwmon_by_name(name):
    for n in glob.glob("/sys/class/hwmon/hwmon*/name"):
        if _rd(n).decode().strip() == name:
            return os.path.dirname(n)
    return None


class CPU:
    def __init__(self):
        self.model = "CPU"
        for ln in _rd("/proc/cpuinfo", 1 << 16).decode().splitlines():
            if ln.startswith("model name"):
                m = ln.split(":", 1)[1].strip()
                for junk in (" Processor", "AMD ", "(R)", "(TM)", " CPU"):
                    m = m.replace(junk, "")
                self.model = " ".join(m.split())
                break
        self.n = os.cpu_count() or 1
        self.f_stat = PFile("/proc/stat")
        self.f_mem = PFile("/proc/meminfo")
        self.f_load = PFile("/proc/loadavg")
        self.f_up = PFile("/proc/uptime")
        self.f_freq = [PFile("/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq" % i)
                       for i in range(self.n)]
        self.fmax = (_int("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq") or 4600000) / 1000.0
        k10 = _hwmon_by_name("k10temp") or _hwmon_by_name("coretemp")
        self.f_temp = PFile((k10 or "/nonexistent") + "/temp1_input")
        nv = _hwmon_by_name("nvme")
        self.f_nvme = PFile((nv or "/nonexistent") + "/temp1_input")
        self.prev = None
        self.threads = [0.0] * self.n
        self.total = 0.0
        self.temp = None
        self.nvme_temp = None
        self.freq_avg = self.freq_max = 0.0
        self.load = (0.0, 0.0, 0.0)
        self.tasks = ""
        self.uptime = 0.0
        self.mem_total = self.mem_used = self.swap_total = self.swap_used = 0
        self.mem_cache = 0

    def sample(self):
        cur = []
        for ln in self.f_stat.read().split(b"\n"):
            if not ln.startswith(b"cpu"):
                if cur:
                    break
                continue
            f = ln.split()
            v = [int(x) for x in f[1:9]]
            idle = v[3] + v[4]
            cur.append((sum(v), idle))
        if self.prev and len(self.prev) == len(cur):
            out = []
            for (t1, i1), (t0, i0) in zip(cur, self.prev):
                dt = t1 - t0
                out.append(100.0 * (dt - (i1 - i0)) / dt if dt > 0 else 0.0)
            self.total = out[0]
            self.threads = out[1:self.n + 1]
        self.prev = cur
        fr = [f.int() or 0 for f in self.f_freq]
        if fr:
            self.freq_avg = sum(fr) / len(fr) / 1000.0
            self.freq_max = max(fr) / 1000.0
        t = self.f_temp.int()
        self.temp = t / 1000.0 if t is not None else None
        t = self.f_nvme.int()
        self.nvme_temp = t / 1000.0 if t is not None else None
        la = self.f_load.read().split()
        if len(la) >= 4:
            self.load = (float(la[0]), float(la[1]), float(la[2]))
            self.tasks = la[3].decode()
        up = self.f_up.read().split()
        if up:
            self.uptime = float(up[0])
        mi = {}
        for ln in self.f_mem.read().split(b"\n"):
            p = ln.split()
            if len(p) >= 2:
                mi[p[0]] = int(p[1]) * 1024
        self.mem_total = mi.get(b"MemTotal:", 0)
        self.mem_used = self.mem_total - mi.get(b"MemAvailable:", 0)
        self.mem_cache = mi.get(b"Cached:", 0) + mi.get(b"Buffers:", 0)
        self.swap_total = mi.get(b"SwapTotal:", 0)
        self.swap_used = self.swap_total - mi.get(b"SwapFree:", 0)


# ---------------------------------------------------------------------- IO
class IO:
    def __init__(self):
        self.f_disk = PFile("/proc/diskstats")
        self.f_net = PFile("/proc/net/dev")
        self.nics = {os.path.basename(os.path.dirname(p))
                     for p in glob.glob("/sys/class/net/*/device")}
        self.disks = {os.path.basename(p) for p in glob.glob("/sys/block/*")
                      if os.path.exists(p + "/device")}
        self.prev = None
        self.prev_t = None
        self.rd = self.wr = self.rx = self.tx = 0.0

    def _counters(self):
        r = w = 0
        for ln in self.f_disk.read().split(b"\n"):
            f = ln.split()
            if len(f) > 9 and f[2].decode() in self.disks:
                r += int(f[5])
                w += int(f[9])
        rx = tx = 0
        for ln in self.f_net.read().split(b"\n"):
            if b":" not in ln:
                continue
            name, rest = ln.split(b":", 1)
            name = name.strip().decode()
            if name == "lo" or (self.nics and name not in self.nics):
                continue
            f = rest.split()
            rx += int(f[0])
            tx += int(f[8])
        return r * 512, w * 512, rx, tx

    def sample(self):
        now = time.monotonic()
        c = self._counters()
        if self.prev:
            dt = max(1e-3, now - self.prev_t)
            self.rd, self.wr, self.rx, self.tx = ((a - b) / dt for a, b in zip(c, self.prev))
        self.prev, self.prev_t = c, now


# --------------------------------------------------------------- processes
class Procs:
    """Top CPU consumers, GPU (KFD) processes and the llama-server command line."""

    def __init__(self):
        self.prev = {}
        self.prev_t = None
        self.top = []          # (cpu%, pid, comm, rss_bytes)
        self.gpu = []          # (vram_bytes, pid, comm)
        self.llama = None      # (pid, model_name) or None
        self.self_pid = os.getpid()

    def sample(self):
        now = time.monotonic()
        dt = (now - self.prev_t) if self.prev_t else None
        cur = {}
        rows = []
        llama = None
        try:
            pids = os.listdir("/proc")
        except OSError:
            pids = []
        for p in pids:
            if not p.isdigit():
                continue
            raw = _rd("/proc/%s/stat" % p, 4096)
            if not raw:
                continue
            rp = raw.rfind(b")")
            comm = raw[raw.find(b"(") + 1:rp].decode("utf-8", "replace")
            f = raw[rp + 2:].split()
            try:
                ticks = int(f[11]) + int(f[12])
                rss = int(f[21]) * PAGE
            except (IndexError, ValueError):
                continue
            pid = int(p)
            cur[pid] = ticks
            if dt and pid in self.prev:
                cpu = (ticks - self.prev[pid]) * 100.0 / CLK_TCK / dt
            else:
                cpu = 0.0
            rows.append((cpu, rss, pid, comm))
            if comm == "llama-server" and llama is None:
                llama = (pid, _model_from_cmdline(_rd("/proc/%s/cmdline" % p)))
        rows.sort(reverse=True)
        self.top = rows[:12]
        self.prev, self.prev_t = cur, now
        self.llama = llama
        gpu = []
        try:
            kp = os.listdir("/sys/class/kfd/kfd/proc")
        except OSError:
            kp = []
        for p in kp:
            vram = 0
            try:
                for fn in os.listdir("/sys/class/kfd/kfd/proc/" + p):
                    if fn.startswith("vram_"):
                        vram += _int("/sys/class/kfd/kfd/proc/%s/%s" % (p, fn)) or 0
            except OSError:
                continue
            comm = _rd("/proc/%s/comm" % p).decode("utf-8", "replace").strip() or "?"
            gpu.append((vram, int(p) if p.isdigit() else 0, comm))
        gpu.sort(reverse=True)
        self.gpu = gpu


def _model_from_cmdline(raw):
    args = raw.decode("utf-8", "replace").split("\0")
    for i, a in enumerate(args):
        if a in ("-m", "--model") and i + 1 < len(args):
            return _model_name(args[i + 1])
        if a.startswith("--model="):
            return _model_name(a.split("=", 1)[1])
    return None


def _model_name(path):
    b = os.path.basename(path.strip().strip("'\""))
    return b[:-5] if b.endswith(".gguf") else b


# --------------------------------------------------------------- llama log
class LlamaLog:
    """Incrementally tails the llama-server log (follows the latest.log symlink)."""
    ACTIVE_WINDOW = 5.0

    def __init__(self, path):
        self.path = os.path.expanduser(path)
        self.real = None
        self.pos = 0
        self.part = b""
        self.model = None
        self.rate = None          # most recent t/s reading (tg_3s or eval)
        self.rate_t = 0.0         # monotonic time we saw it (only for live lines)
        self.n_gen = None
        self.last_eval = None
        self.last_prompt = None
        self.generating = False
        self.stopped = False
        self.events = 0           # increments on each fresh rate reading (drives pulses)
        self.mtime = 0.0

    def poll(self):
        try:
            real = os.path.realpath(self.path)
            st = os.stat(real)
        except OSError:
            self.real = None
            return
        fresh = True
        if real != self.real or st.st_size < self.pos:
            self.real = real
            self.pos = max(0, st.st_size - 256 * 1024)
            self.part = b""
            fresh = False
            # the model path is printed at start-up; grab it from the head
            for ln in _rd(real, 16384).split(b"\n"):
                if b"loading model" in ln:
                    self._line(ln, False)
        self.mtime = st.st_mtime
        if st.st_size <= self.pos:
            return
        if st.st_size - self.pos > 4 * 1024 * 1024:
            self.pos = st.st_size - 256 * 1024
            self.part = b""
        try:
            with open(real, "rb") as f:
                f.seek(self.pos)
                data = f.read(st.st_size - self.pos)
        except OSError:
            return
        self.pos += len(data)
        data = self.part + data
        lines = data.split(b"\n")
        self.part = lines.pop()
        for ln in lines:
            self._line(ln, fresh)

    def _line(self, ln, fresh):
        if b"print_timing" in ln:
            if b"n_gen" in ln and b"tg_3s" in ln:
                try:
                    s = ln.decode("ascii", "replace")
                    self.n_gen = int(s.split("n_gen =")[1].split(",")[0])
                    self.rate = float(s.split("tg_3s =")[1].split("t/s")[0])
                except (IndexError, ValueError):
                    return
                self._fresh(fresh)
                self.generating = True
            elif b"prompt eval time" in ln:
                v = _tps(ln)
                if v is not None:
                    self.last_prompt = v
            elif b"eval time" in ln:
                v = _tps(ln)
                if v is not None:
                    self.last_eval = v
                    self.rate = v
                    self._fresh(fresh)
                    try:
                        self.n_gen = int(ln.split(b"/")[1].split(b"tokens")[0])
                    except (IndexError, ValueError):
                        pass
        elif b"launch_slot_" in ln:
            self.generating = True
            self.stopped = False
        elif b"slot      release" in ln or b"stop processing" in ln:
            self.generating = False
        elif b"loading model" in ln:
            try:
                self.model = _model_name(ln.split(b"'")[1].decode("utf-8", "replace"))
            except IndexError:
                pass
            self.stopped = False
        elif b"cleaning up before exit" in ln:
            self.generating = False
            self.stopped = True

    def _fresh(self, fresh):
        if fresh:
            self.rate_t = time.monotonic()
            self.events += 1

    def live_rate(self):
        """Tokens/s if the server produced a reading in the last few seconds, else 0."""
        if self.rate is None or time.monotonic() - self.rate_t > self.ACTIVE_WINDOW:
            return 0.0
        return self.rate


def _tps(ln):
    try:
        return float(ln.split(b"(")[1].split(b",")[1].split(b"tokens per second")[0])
    except (IndexError, ValueError):
        return None


# ------------------------------------------------------------------ facade
class Sampler:
    def __init__(self, log_path):
        self.gpu = GPU()
        self.cpu = CPU()
        self.io = IO()
        self.procs = Procs()
        self.log = LlamaLog(log_path)
        self.seq = 0
        self.h = {k: Hist() for k in (
            "gpu", "vram", "power", "tj", "te", "tm", "sclk", "mclk", "fan", "mbusy",
            "cpu", "ctemp", "cfreq", "ram", "rd", "wr", "rx", "tx", "tok")}
        self.tick = 0

    def sample(self):
        g, c, io = self.gpu, self.cpu, self.io
        g.sample()
        c.sample()
        io.sample()
        self.log.poll()
        if self.tick % 4 == 0:          # processes every 2 s
            self.procs.sample()
        if self.tick % 20 == 0:
            g.read_link()
        self.tick += 1
        h = self.h
        h["gpu"].push(g.busy)
        h["vram"].push(g.vram_used)
        h["power"].push(g.power)
        h["tj"].push(g.t_junc)
        h["te"].push(g.t_edge)
        h["tm"].push(g.t_mem)
        h["sclk"].push(g.sclk)
        h["mclk"].push(g.mclk)
        h["fan"].push(g.fan)
        h["mbusy"].push(g.mbusy)
        h["cpu"].push(c.total)
        h["ctemp"].push(c.temp)
        h["cfreq"].push(c.freq_avg)
        h["ram"].push(c.mem_used)
        h["rd"].push(io.rd)
        h["wr"].push(io.wr)
        h["rx"].push(io.rx)
        h["tx"].push(io.tx)
        h["tok"].push(self.log.live_rate())
        self.seq += 1
