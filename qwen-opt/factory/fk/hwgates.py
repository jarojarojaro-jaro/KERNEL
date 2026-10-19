"""Hardware gates H0-H11 of RSI-F (report 21h §5.4; user rules 2026-10-19). Code, not prompt: the factory checks
them before every GPU block (fk/gpu.py) and `rsi cycle` before every cycle; a gate that fires refuses the work.

H0  one GPU job at a time: every block is `flock /tmp/gpu.lock flock /tmp/quiet.lock timeout <=290`; both lock
    files must already exist (we never create, touch or delete them)
H1  gpu-guard.sh runs; a block starts only at hotspot < 70 C and VRAM < 75 C (transient: the runner waits)
H2  GGML_HIP_PM4=0 in every block, unless the card is about PM4 and state/pm4-safe.json declares it safe
H3  quarantine: the build that was on the GPU when a page fault / ring timeout / reset appeared never runs again;
    any new fault halts the whole loop until a human acknowledges it (`factory rsi hw ack --reason`)
H4  kernel log of ALL boots since the acknowledged watermark (`journalctl -k -b N`), once before each block
H5  a kernel change (.cu/.cuh/.c/.cpp under ggml-cuda/ggml-hip) must declare ops: G1 test-backend-ops runs as the
    short supervised smoke before any long measurement
H6  budget: factory GPU time <= 60 min per 24 h and <= 15 h per 30 days; 2 consecutive hardware INVALIDs stop
H7  no clock/voltage/power-limit changes: deny-list on diff, argv and env (sysfs writes, amdgpu parameters,
    pp_od_clk_voltage, power cap, performance level, sudo, rocm-smi/amd-smi setters); the power cap, performance
    level and OD table must equal the baseline recorded at the last acknowledgement
H8  the user's server: refuse while anything listens on :8080 (`ss -ltn 'sport = :8080'`, never pgrep -f)
H9  SSD: factory-written state (runs/, rsi/, cache/, playbooks/, ledger) <= 2 GiB, <= 512 MiB new per 24 h,
    >= 20 GiB free on the disk
H10 cloud: only with a watchdog script, a deadline and a cost limit
H11 CPU (user rule, CPU 73 C): every heavy command is `flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 CMD`
    (one heavy job machine-wide, <= 2 cores, builds -j <= 2); 1-min load below half the cores before a GPU block
    (transient: the runner waits)

State (machine-global, not per ledger) lives in paths.RSI_STATE: hw.json (watermark, baseline, halt, streak),
quarantine.jsonl, gpu-time.jsonl, ssd.json.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from . import hashing, paths, preflight

LOCK_FILES = ("/tmp/gpu.lock", "/tmp/quiet.lock")
WRAP = ["flock", LOCK_FILES[0], "flock", LOCK_FILES[1]]
MAX_BLOCK_S = 290
START_HOTSPOT_MAX_C = 70.0
START_VRAM_MAX_C = 75.0
DAY_GPU_S = 60 * 60
MONTH_GPU_S = 15 * 3600
MAX_HW_INVALID_STREAK = 2
SSD_CAP_BYTES = 2 << 30
SSD_DAY_BYTES = 512 << 20
MIN_FREE_BYTES = 20 << 30
CPU_LOCK, HEAVY_NICE, MAX_CORES = "/tmp/cpuheavy.lock", 19, 2  # user rule 2026-10-19: CPU at 67-73 C
FAULT_RE = r"amdgpu.*(page fault|ring .* timeout|GPU reset begin|MES might be)"
WAIT_POLL_S = 30            # transient gates (H1 temperature, H11 load) are re-read at most every 30 s
WAIT_MAX_S = 15 * 60
TRANSIENT = ("H1", "H11")
KERNEL_SRC_RE = re.compile(r"^ggml/src/ggml-(cuda|hip)/.*\.(cu|cuh|c|cpp|h)$")
H7_DENY = [
    (re.compile(r"/sys/(class|bus|module|kernel|devices)/"), "sysfs"),
    (re.compile(r"\bpp_od_clk_voltage\b"), "OD clock/voltage table"),
    (re.compile(r"\bpower\d*_cap\b|\bpower_cap\b"), "power limit"),
    (re.compile(r"\bpower_dpm_force_performance_level\b|\bpp_dpm_(sclk|mclk|fclk|socclk)\b"), "clock level"),
    (re.compile(r"\bamdgpu\.\w+=|modprobe\s+amdgpu|/sys/module/amdgpu/parameters"), "amdgpu module parameter"),
    (re.compile(r"(^|[\s;&|(])sudo\b"), "sudo"),
    (re.compile(r"\brocm-smi\b.*--set|\brocm-smi\b.*--(setsclk|setmclk|setpoweroverdrive|setperflevel|resetclocks)"
                r"|\bamd-smi\s+set\b"), "SMI setter"),
    (re.compile(r"\b(upp|amdgpu-clocks|corectrl|lact)\b"), "overclocking tool"),
]
H8_NOTE = "the user's server listens on :8080 (ss -ltn); stop it explicitly (rsi cycle --stop-topka) or wait"


class HwRefused(Exception):
    def __init__(self, failures: dict):
        self.failures = failures
        super().__init__("; ".join(f"{g}: {m}" for g, ms in failures.items() for m in ms))


class HardwareStop(HwRefused):
    """A new GPU fault appeared: build quarantined, loop halted (H3/H4)."""


# ---------------------------------------------------------------------------------------------- state
def _state_file(name):
    return paths.RSI_STATE / name


def load_state() -> dict:
    f = _state_file("hw.json")
    if not f.exists():
        return {}
    return json.loads(f.read_text())


def save_state(st: dict):
    paths.RSI_STATE.mkdir(parents=True, exist_ok=True)
    f = _state_file("hw.json")
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, f)


def _jsonl(name) -> list[dict]:
    f = _state_file(name)
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


def _append(name, row: dict):
    paths.RSI_STATE.mkdir(parents=True, exist_ok=True)
    with open(_state_file(name), "a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------------------------- probes (CPU only)
def guard_running() -> bool:
    r = subprocess.run(["pgrep", "-f", f"bash .*{paths.GPU_GUARD.name}"], capture_output=True, text=True)
    return r.returncode == 0


def temps(dev: Path = paths.DRM_DEVICE) -> dict:
    out = {}
    for hw in sorted((dev / "hwmon").glob("hwmon*")):
        for f in sorted(hw.glob("temp*_label")):
            try:
                out[f.read_text().strip()] = int(Path(str(f).replace("_label", "_input")).read_text()) / 1000.0
            except (OSError, ValueError):
                pass
        break
    return out


OD_HASHED = ("OD_SCLK", "OD_MCLK", "OD_VDDGFX_OFFSET")


def od_clock_voltage(od: str) -> str:
    """Clock/voltage part of pp_od_clk_voltage: only the OD_SCLK, OD_MCLK and OD_VDDGFX_OFFSET sections. Fan curve
    sections (OD_FAN_*, ACOUSTIC_*, also exposed under gpu_od/fan_ctrl/) and OD_RANGE are excluded: the root timer
    xtx-fan flips the fan curve between 'load' and 'idle' constantly, which must not trip H7."""
    keep, out = False, []
    for line in od.splitlines():
        s = line.strip()
        if s.endswith(":") and s[:-1].replace("_", "").isalnum() and s[:-1].isupper():
            keep = s[:-1] in OD_HASHED
        if keep and s:
            out.append(s)
    return "\n".join(out)


def power_facts(dev: Path = paths.DRM_DEVICE) -> dict:
    """Fields H7 compares with the baseline: power1_cap, power_dpm_force_performance_level and the sha256 of the
    clock/voltage OD sections. Nothing under gpu_od/fan_ctrl/ is read."""
    def rd(p):
        try:
            return Path(p).read_text().strip()
        except OSError:
            return None
    hw = sorted((dev / "hwmon").glob("hwmon*"))
    cap = rd(hw[0] / "power1_cap") if hw else None
    od = rd(dev / "pp_od_clk_voltage")
    return {"power_cap_uw": cap, "perf_level": rd(dev / "power_dpm_force_performance_level"),
            "od_sha256": hashing.sha256_bytes(od_clock_voltage(od).encode()) if od is not None else None}


def boots() -> list[dict]:
    """`journalctl --list-boots` (UTC): [{idx, id, first, last}] with 'YYYY-MM-DD HH:MM:SS' strings."""
    r = subprocess.run(["journalctl", "--list-boots", "--no-pager"], capture_output=True, text=True,
                       env={**os.environ, "TZ": "UTC"})
    out = []
    pat = re.compile(r"^\s*(-?\d+)\s+([0-9a-f]{32})\s+\w{3}\s+(\S+ \S+)\s+\S+\s+\w{3}\s+(\S+ \S+)\s+\S+")
    for l in r.stdout.splitlines():
        m = pat.match(l)
        if m:
            out.append({"idx": int(m.group(1)), "id": m.group(2), "first": m.group(3), "last": m.group(4)})
    return out


def kernel_faults(since: str, current_boot_only: bool = False) -> list[str]:
    """Fault lines (page fault, ring timeout, reset) in the kernel log of every boot that ended after `since`."""
    lines = []
    bl = boots()
    if not bl:
        return [f"journalctl --list-boots gave nothing: cannot check the kernel log (fail closed)"]
    for b in bl:
        if current_boot_only and b["idx"] != 0:
            continue
        if b["last"] < since:
            continue
        r = subprocess.run(["journalctl", "-k", "-b", b["id"], "--since", since, "-g", FAULT_RE, "-o", "short-iso",
                            "--no-pager", "-q"], capture_output=True, text=True, env={**os.environ, "TZ": "UTC"})
        lines += [f"boot {b['idx']}: {l.strip()}" for l in r.stdout.splitlines() if l.strip()]
    return lines


def ssd_bytes() -> int:
    total = 0
    roots = [paths.RUNS, paths.RSI, paths.CACHE, paths.PLAYBOOKS, paths.EVIDENCE]
    for root in roots:
        if not root.exists():
            continue
        for dirpath, _, files in os.walk(root):
            for n in files:
                try:
                    total += os.lstat(os.path.join(dirpath, n)).st_size
                except OSError:
                    pass
    for f in paths.FACTORY.glob("ledger*.jsonl*"):
        total += f.stat().st_size
    return total


def ssd_day_growth(now_bytes: int) -> int:
    """Bytes added since the first check in the last 24 h (state/ssd.json keeps that first reading)."""
    f = _state_file("ssd.json")
    st = json.loads(f.read_text()) if f.exists() else {}
    t = time.time()
    if not st or t - st.get("t0", 0) > 86400:
        st = {"t0": t, "bytes0": now_bytes}
        paths.RSI_STATE.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(st) + "\n")
    return max(0, now_bytes - st["bytes0"])


def gpu_seconds(window_s: float) -> float:
    t = time.time()
    return sum(r.get("secs") or 0 for r in _jsonl("gpu-time.jsonl") if t - r.get("t", 0) <= window_s)


def build_tree(build_dir) -> str | None:
    try:
        return hashing.tree_sha(hashing.hash_build(build_dir)) if build_dir and Path(build_dir).is_dir() else None
    except OSError:
        return None


def quarantined() -> dict:
    return {r["build_tree"]: r for r in _jsonl("quarantine.jsonl")}


# ---------------------------------------------------------------------------------------------- facts
def text_items(ctx: dict) -> list[str]:
    """Everything H7 scans: added diff lines, argv, env assignments, commands."""
    items = []
    diff = ctx.get("diff")
    if diff:
        items += [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    if ctx.get("argv"):
        items.append(" ".join(map(str, ctx["argv"])))
    items += [f"{k}={v}" for k, v in (ctx.get("env") or {}).items()]
    items += [c["cmd"] if isinstance(c, dict) else str(c) for c in ctx.get("commands") or []]
    return items


def loadavg1() -> float | None:
    try:
        return float(Path("/proc/loadavg").read_text().split()[0])
    except (OSError, ValueError):
        return None


def collect(ctx: dict | None = None) -> dict:
    """Facts for every gate from the live machine. ctx: env (block env), argv, card, builds [dirs], diff, cloud,
    commands [{kind, cmd}], wrap (block command prefix), block_timeout."""
    ctx = ctx or {}
    st = load_state()
    builds = [b for b in ctx.get("builds") or [] if b]
    nb = ssd_bytes()
    load1 = loadavg1()
    return {
        "wrap": ctx.get("wrap", list(paths.GPU_WRAP)), "block_timeout": ctx.get("block_timeout", paths.BLOCK_TIMEOUT_S),
        "locks": {p: os.path.exists(p) for p in LOCK_FILES},
        "guard": guard_running(), "temp_c": temps(),
        "env": ctx.get("env"), "card": ctx.get("card"),
        "pm4_safe": _state_file("pm4-safe.json").exists(),
        "halt": st.get("halt"), "initialized": bool(st.get("watermark")),
        "builds": {b: build_tree(b) for b in builds}, "quarantine": quarantined(),
        "faults": kernel_faults(st["watermark"]) if st.get("watermark") else [],
        "gpu_s_day": gpu_seconds(86400), "gpu_s_30d": gpu_seconds(30 * 86400),
        "hw_invalid_streak": st.get("hw_invalid_streak", 0),
        "texts": text_items(ctx), "power": power_facts(), "baseline": st.get("baseline"),
        "port_user": preflight.user_server_listening() and not ctx.get("stop_topka"),  # else the block stops it
        "ssd_bytes": nb, "ssd_day": ssd_day_growth(nb), "disk_free": shutil.disk_usage(paths.FACTORY).free,
        "cloud": ctx.get("cloud"), "where": ctx.get("where", "local"),
        "commands": ctx.get("commands") or [], "load1": load1, "nproc": os.cpu_count() or 1,
    }


# ---------------------------------------------------------------------------------------------- gates
def h0(f):
    out = []
    if "wrap" in f and list(f["wrap"])[:4] != WRAP:
        out.append(f"block wrapper {f['wrap']} is not {' '.join(WRAP)}")
    if "block_timeout" in f and not (0 < f["block_timeout"] <= MAX_BLOCK_S):
        out.append(f"block timeout {f['block_timeout']} s outside 1-{MAX_BLOCK_S}")
    for p, ok in (f.get("locks") or {}).items():
        if not ok:
            out.append(f"{p} missing: never create lock files; the owner of the GPU workflow must")
    return out


def h1(f):
    out = []
    if "guard" in f and not f["guard"]:
        out.append(f"{paths.GPU_GUARD.name} is not running (start it before any GPU work)")
    if "temp_c" in f:
        t = f["temp_c"] or {}
        hot, mem = t.get("junction"), t.get("mem")
        if hot is None or mem is None:
            out.append(f"no hotspot/VRAM temperature readable {t} (fail closed)")
        else:
            if hot >= START_HOTSPOT_MAX_C:
                out.append(f"hotspot {hot:.0f} C >= {START_HOTSPOT_MAX_C:.0f} C start limit")
            if mem >= START_VRAM_MAX_C:
                out.append(f"VRAM {mem:.0f} C >= {START_VRAM_MAX_C:.0f} C start limit")
    return out


def is_pm4_card(card) -> bool:
    c = card or {}
    return bool(c.get("pm4")) or "PM4" in str((c.get("switch") or {}).get("name", ""))


def h2(f):
    env = f.get("env")
    if env is None:
        return []
    v = str(env.get("GGML_HIP_PM4", ""))
    if v == "0":
        return []
    if is_pm4_card(f.get("card")) and f.get("pm4_safe"):
        return []
    return [f"GGML_HIP_PM4={v or '<unset>'}: PM4 replay must be 0 (report 17) unless a PM4 card is declared safe"]


def h3(f):
    out = []
    if f.get("halt"):
        h = f["halt"]
        out.append(f"loop halted since {h.get('ts')}: {h.get('reason', '')[:160]} (human: factory rsi hw ack)")
    q = f.get("quarantine") or {}
    for d, tree in (f.get("builds") or {}).items():
        if tree and tree in q:
            out.append(f"build {d} (tree {tree[:12]}) is quarantined: {q[tree].get('reason', '')[:120]}")
    return out


def h4(f):
    if "initialized" in f and not f["initialized"]:
        return ["hardware state not initialized: `factory rsi hw ack --reason ...` records the fault watermark"]
    return [f"new kernel fault since the acknowledged watermark: {l[:200]}" for l in (f.get("faults") or [])[:5]]


def h5(f):
    c = f.get("card")
    if not c:
        return []
    kern = [p for p in c.get("touched_paths") or [] if KERNEL_SRC_RE.match(p)]
    if kern and not c.get("ops"):
        return [f"kernel change {kern[:3]} without ops: G1 test-backend-ops must run before measuring"]
    return []


def h6(f):
    out = []
    if "gpu_s_day" in f and f["gpu_s_day"] + MAX_BLOCK_S > DAY_GPU_S:
        out.append(f"daily GPU budget: {f['gpu_s_day'] / 60:.1f} min used in 24 h, a block may take "
                   f"{MAX_BLOCK_S / 60:.1f}, limit {DAY_GPU_S / 60:.0f}")
    if "gpu_s_30d" in f and f["gpu_s_30d"] + MAX_BLOCK_S > MONTH_GPU_S:
        out.append(f"30-day GPU budget: {f['gpu_s_30d'] / 3600:.2f} h used, limit {MONTH_GPU_S / 3600:.0f} h")
    if f.get("hw_invalid_streak", 0) >= MAX_HW_INVALID_STREAK:
        out.append(f"{f['hw_invalid_streak']} consecutive hardware INVALID verdicts: cycle over")
    return out


def h7(f):
    out = []
    for t in f.get("texts") or []:
        for rx, why in H7_DENY:
            if rx.search(t):
                out.append(f"{why}: {t.strip()[:120]}")
                break
    p, b = f.get("power"), f.get("baseline")
    if p and b:
        for k in ("power_cap_uw", "perf_level", "od_sha256"):
            if b.get(k) is not None and p.get(k) != b.get(k):
                out.append(f"{k} changed: {p.get(k)} != baseline {b.get(k)} (no clock/voltage/power changes)")
    return out


def h8(f):
    return [H8_NOTE] if f.get("port_user") else []


def h9(f):
    out = []
    if f.get("ssd_bytes", 0) > SSD_CAP_BYTES:
        out.append(f"factory state {f['ssd_bytes'] / 2**30:.2f} GiB > {SSD_CAP_BYTES / 2**30:.0f} GiB")
    if f.get("ssd_day", 0) > SSD_DAY_BYTES:
        out.append(f"{f['ssd_day'] / 2**20:.0f} MiB written in 24 h > {SSD_DAY_BYTES / 2**20:.0f} MiB")
    if "disk_free" in f and f["disk_free"] < MIN_FREE_BYTES:
        out.append(f"only {f['disk_free'] / 2**30:.1f} GiB free on the disk")
    return out


def h10(f):
    if f.get("where", "local") != "cloud":
        return []
    c = f.get("cloud") or {}
    out = []
    if not c.get("watchdog") or not Path(c["watchdog"]).exists():
        out.append("cloud run without a watchdog script (cloud/watchdog.sh pattern)")
    if not (isinstance(c.get("deadline_min"), (int, float)) and 0 < c["deadline_min"] <= 240):
        out.append("cloud run without a deadline (deadline_min 1-240)")
    if not (isinstance(c.get("max_usd"), (int, float)) and 0 < c["max_usd"]):
        out.append("cloud run without a cost limit (max_usd)")
    return out


_NICE = re.compile(r"\bnice\s+(?:-n\s*)?(-?\d+)")
_JOBS = re.compile(r"(?:^|\s)(?:-j\s*|--parallel[= ]\s*)(\d+)")
_THREADS = re.compile(r"(?:\s-t\s+|--threads[= ]|OMP_NUM_THREADS=|-j\s*)(\d+)")
_BUILD = re.compile(r"\bcmake\s+--build\b|(^|[\s;&])(make|ninja)\b")
_TASKSET = re.compile(r"\btaskset\s+-c\s+([0-9,\-]+)")


def _cores(spec: str) -> int:
    n = 0
    for part in spec.split(","):
        a, _, b = part.partition("-")
        n += (int(b) - int(a) + 1) if b else 1
    return n


def h11(f):
    """User rule 2026-10-19 (CPU 73 C): every heavy command (build, configure, heavy script) runs as
    `flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 CMD` (one heavy job machine-wide, <= 2 cores, builds -j <= 2,
    scripts <= 4 threads); a GPU block starts only when the 1-min load is below half the cores."""
    out = []
    for c in f.get("commands") or []:
        kind, cmd = (c.get("kind"), c["cmd"]) if isinstance(c, dict) else ("build" if _BUILD.search(c) else "script", c)
        if kind not in ("build", "configure", "script"):
            continue
        helper = re.match(r"\s*(?:cd \S+ && )?(?:\S+=\S+ )*cpuheavy\s", cmd)
        if helper:  # Main's queue helper (2 slots x 2 cores, nice 19): builds must take quiet.lock through it
            if kind == "build" and "--quiet" not in cmd.split("cpuheavy", 1)[1].split()[:1]:
                out.append(f"build via cpuheavy without --quiet (quiet.lock only after a CPU slot): {cmd[:100]}")
            if re.search(r"flock\s+-s\s+/tmp/quiet\.lock[^|;&]*cpuheavy", cmd):
                out.append(f"holds quiet.lock while waiting for a CPU slot: {cmd[:100]}")
        else:
            m = _NICE.search(cmd)
            nice = int(m.group(1)) if m else 0
            ts = _TASKSET.search(cmd)
            if CPU_LOCK not in cmd:
                out.append(f"{kind} outside `cpuheavy` / `flock {CPU_LOCK}` (one heavy queue): {cmd[:100]}")
            if nice < HEAVY_NICE:
                out.append(f"{kind} without nice -n {HEAVY_NICE}: {cmd[:100]}")
            if not ts or _cores(ts.group(1)) > MAX_CORES:
                out.append(f"{kind} without taskset -c to <= {MAX_CORES} cores: {cmd[:100]}")
        if kind == "build":
            j = _JOBS.search(cmd)
            if not j or int(j.group(1)) > MAX_CORES:
                out.append(f"build needs -j <= {MAX_CORES}: {cmd[:100]}")
        if kind == "script":
            t = _THREADS.search(cmd)
            if t and int(t.group(1)) > MAX_CORES:
                out.append(f"script with {t.group(1)} threads > {MAX_CORES}: {cmd[:100]}")
    if f.get("load1") is not None and f.get("nproc") and f["load1"] >= f["nproc"] / 2:
        out.append(f"load {f['load1']:.1f} >= half of {f['nproc']} cores: CPU busy, the block would be noisy")
    return out


GATES = {"H0": h0, "H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5, "H6": h6, "H7": h7, "H8": h8, "H9": h9,
         "H10": h10, "H11": h11}


def check(facts: dict, only=None) -> dict:
    """{gate: [messages]} of the gates that fire."""
    out = {}
    for g, fn in GATES.items():
        if only and g not in only:
            continue
        m = fn(facts)
        if m:
            out[g] = m
    return out


def enforce(ctx: dict | None = None, wait: bool = False, log=print, sleep=time.sleep) -> dict:
    """Refuse (HwRefused) if any gate fires. wait=True: transient gates (H1 temperature, H11 load) are re-read every
    WAIT_POLL_S (sysfs and /proc only) for up to WAIT_MAX_S before refusing. Returns the facts used."""
    facts = collect(ctx)
    bad = check(facts)
    waited = 0
    while wait and bad and set(bad) <= set(TRANSIENT) and waited < WAIT_MAX_S:
        log(f"  [hw] waiting {WAIT_POLL_S} s: {'; '.join(m for ms in bad.values() for m in ms)[:200]}")
        sleep(WAIT_POLL_S)
        waited += WAIT_POLL_S
        facts["temp_c"] = temps()
        facts["load1"] = loadavg1()
        bad = check(facts)
    if bad:
        raise HwRefused(bad)
    return facts


# ---------------------------------------------------------------------------------------------- events
def ack(reason: str, by: str) -> dict:
    """Human acknowledgement: faults up to now are known; the watermark moves to now, the halt is cleared, the power
    baseline is (re)recorded and the hardware INVALID streak resets. Quarantined builds stay quarantined."""
    if not reason.strip():
        raise ValueError("ack needs a reason")
    st = load_state()
    since = st.get("watermark") or "1970-01-01 00:00:00"
    seen = kernel_faults(since)
    now = utcnow()
    st.update(watermark=now, halt=None, baseline=power_facts(), hw_invalid_streak=0)
    st.setdefault("acks", []).append({"ts": now, "by": by, "reason": reason, "faults_acknowledged": len(seen),
                                      "first": seen[:1], "last": seen[-1:]})
    save_state(st)
    return {"watermark": now, "faults_acknowledged": len(seen), "sample": seen[:3] + seen[-2:]}


def quarantine(build_dir, reason: str, lines=()):
    tree = build_tree(build_dir)
    if tree and tree not in quarantined():
        _append("quarantine.jsonl", {"ts": utcnow(), "build_dir": str(build_dir), "build_tree": tree, "reason": reason,
                                     "kernel": list(lines)[:5]})
    return tree


def halt(reason: str, lines=()):
    st = load_state()
    st["halt"] = {"ts": utcnow(), "reason": reason, "kernel": list(lines)[:5]}
    save_state(st)


def record_block(vid: str, name: str, secs: float):
    _append("gpu-time.jsonl", {"t": time.time(), "ts": utcnow(), "vid": vid, "block": name, "secs": round(secs, 1)})


HW_INVALID_RE = re.compile(r"\b(H3|H4|fault|timeout|R14|R30|without a result|reset)\b", re.I)


def record_verdict(verdict: str | None, reasons: list[str]):
    st = load_state()
    hw = verdict == "INVALID" and any(HW_INVALID_RE.search(r) for r in reasons or [])
    st["hw_invalid_streak"] = st.get("hw_invalid_streak", 0) + 1 if hw else 0
    save_state(st)
    return st["hw_invalid_streak"]


def after_block(start_utc: str, build_dir, vid: str, name: str):
    """Once after each block: faults since the block started -> quarantine its build, halt the loop, stop (H3)."""
    lines = kernel_faults(start_utc, current_boot_only=True)
    if lines:
        tree = quarantine(build_dir, f"GPU fault during {vid} block {name}", lines)
        halt(f"GPU fault during {vid} block {name}; build tree {str(tree)[:12]} quarantined", lines)
        raise HardwareStop({"H3": [f"fault during block {name}: {lines[0][:200]}"]})
