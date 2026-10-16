"""Machine snapshot before/after each GPU block (CPU only: /proc, /sys, pgrep). Rules R08/R09/R14/R15/R26 judge it."""
from __future__ import annotations

import glob
import os
import re
import socket
import subprocess
import time
from pathlib import Path

from . import paths


def _read(p, cast=str, default=None):
    try:
        return cast(Path(p).read_text().strip())
    except (OSError, ValueError):
        return default


def _pgrep(pattern: str, exact: bool = False) -> list[str]:
    """exact: match the process name (pgrep without -f), else the full command line."""
    r = subprocess.run(["pgrep", "-a", pattern] if exact else ["pgrep", "-a", "-f", pattern],
                       capture_output=True, text=True)
    me = str(os.getpid())
    return [l for l in r.stdout.splitlines() if l and l.split()[0] != me and "pgrep" not in l]


def port_free(port: int) -> bool:
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def kfd_procs() -> list[dict]:
    """Processes holding a KFD (ROCm GPU) context, from /sys/class/kfd/kfd/proc/<pid>."""
    out = []
    for p in sorted(glob.glob("/sys/class/kfd/kfd/proc/*")):
        pid = os.path.basename(p)
        if pid.isdigit() and int(pid) != os.getpid():
            cmd = _read(f"/proc/{pid}/cmdline", lambda s: s.replace("\0", " ").strip(), "")
            out.append({"pid": int(pid), "cmd": cmd[:200]})
    return out


def snapshot(port: int | None = None, dev: Path = paths.DRM_DEVICE) -> dict:
    hw = sorted(glob.glob(str(dev / "hwmon" / "hwmon*")))
    hwd = Path(hw[0]) if hw else None
    temps = {}
    if hwd:
        for f in sorted(hwd.glob("temp*_label")):
            v = _read(str(f).replace("_label", "_input"), int)
            if v is not None:
                temps[_read(f)] = v / 1000.0
    quota = None
    cm = _read("/sys/fs/cgroup/cpu.max")
    if cm and cm.split()[0] != "max":
        q, per = cm.split()
        quota = int(q) / int(per)
    load = _read("/proc/loadavg", lambda s: [float(x) for x in s.split()[:3]], [0.0, 0.0, 0.0])
    return {
        "ts": time.time(),
        "user_server": bool(_pgrep(paths.USER_SERVER_RE)),
        "llama_servers": [re.sub(r"\s+", " ", l)[:300] for l in _pgrep("^llama-server$", exact=True)],
        "kfd_procs": kfd_procs(),
        "keepawake": bool(_pgrep("keepawake")),
        "power_control": _read(dev / "power" / "control"),
        "vram_used": _read(dev / "mem_info_vram_used", int),
        "vram_total": _read(dev / "mem_info_vram_total", int),
        "gtt_used": _read(dev / "mem_info_gtt_used", int),
        "temp_c": temps,
        "power_w": (_read(hwd / "power1_average", int, 0) / 1e6) if hwd else None,
        "power_cap_w": (_read(hwd / "power1_cap", int, 0) / 1e6) if hwd else None,
        "loadavg": load,
        "nproc": os.cpu_count(),
        "cpu_quota": quota,
        "port": port,
        "port_free": port_free(port) if port else None,
    }
