#!/usr/bin/env python3
"""Run `evalplus.evaluate` on UNTRUSTED generated code inside an unprivileged sandbox.

Layers (no bubblewrap/firejail on the host, unprivileged user namespaces are blocked by AppArmor, so no
`unshare -n`; systemd --user cannot apply IPAddressDeny/PrivateNetwork):
  1. Landlock (kernel ABI >= 4), applied to this process before evalplus forks its workers, inherited and
     irrevocable: no TCP connect/bind on any port; filesystem writes only below the samples' directory, the
     private scratch TMPDIR, /dev/shm (multiprocessing semaphores) and /dev/null. Reads stay allowed.
  2. Python-level socket guard: socket.socket/create_connection raise (also blocks UDP/unix sockets from Python).
  3. evalplus's own reliability_guard in every worker (RLIMIT_AS/DATA/STACK, os.kill/system/fork/rmtree...
     disabled, subprocess disabled) and per-test time limits.
  4. Caller (jakosc-mini.sh) wraps this in `systemd-run --user --scope -p MemoryMax=4G -p CPUQuota=200%`
     and `nice -n 19`, as the normal user (refuses root).
Usage: sandbox_eval.py --dataset humaneval|mbpp --samples X.jsonl [--parallel 2]
"""
import argparse, ctypes, os, socket, sys, tempfile

LL_CREATE, LL_ADD_RULE, LL_RESTRICT = 444, 445, 446
FS_WRITE = sum(1 << b for b in (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14))  # write/remove/make*/refer/truncate
FILE_RIGHTS = (1 << 1) | (1 << 14)  # WRITE_FILE | TRUNCATE (rights valid on a non-directory)
NET_ALL = 1 | 2  # BIND_TCP | CONNECT_TCP


class RulesetAttr(ctypes.Structure):
    _fields_ = [("fs", ctypes.c_uint64), ("net", ctypes.c_uint64)]


class PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed", ctypes.c_uint64), ("fd", ctypes.c_int32)]


def landlock(write_dirs):
    libc = ctypes.CDLL(None, use_errno=True)
    abi = libc.syscall(LL_CREATE, None, 0, 1)
    if abi < 4:
        sys.exit(f"sandbox: Landlock ABI {abi} < 4 (no TCP rules) - refusing to run untrusted code")
    attr = RulesetAttr(FS_WRITE, NET_ALL)
    rfd = libc.syscall(LL_CREATE, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    if rfd < 0:
        sys.exit(f"sandbox: landlock_create_ruleset errno {ctypes.get_errno()}")
    for p in write_dirs:
        fd = os.open(p, os.O_PATH | os.O_CLOEXEC)
        rights = FS_WRITE if os.path.isdir(p) else FILE_RIGHTS
        pb = PathBeneath(rights, fd)
        if libc.syscall(LL_ADD_RULE, rfd, 1, ctypes.byref(pb), 0) != 0:
            sys.exit(f"sandbox: add_rule {p} errno {ctypes.get_errno()}")
        os.close(fd)
    # no NET_PORT rules: every TCP bind/connect is denied
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        sys.exit("sandbox: no_new_privs failed")
    if libc.syscall(LL_RESTRICT, rfd, 0) != 0:
        sys.exit(f"sandbox: landlock_restrict_self errno {ctypes.get_errno()}")
    os.close(rfd)


def socket_guard():
    def deny(*a, **k):
        raise PermissionError("network disabled in the evalplus sandbox")
    socket.socket = deny
    socket.create_connection = deny
    socket.socketpair = deny


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["humaneval", "mbpp"])
    ap.add_argument("--samples", required=True)
    ap.add_argument("--parallel", type=int, default=2)
    a = ap.parse_args()
    if os.geteuid() == 0:
        sys.exit("sandbox: refusing to run untrusted code as root")
    samples = os.path.abspath(a.samples)
    # ground truth (trusted canonical solutions) is computed and cached BEFORE the sandbox closes,
    # so the sandbox does not need write access to ~/.cache/evalplus
    from evalplus.data import get_human_eval_plus, get_human_eval_plus_hash, get_mbpp_plus, get_mbpp_plus_hash
    from evalplus.evaluate import get_groundtruth, evaluate
    from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS
    if a.dataset == "humaneval":
        get_groundtruth(get_human_eval_plus(), get_human_eval_plus_hash(), [])
    else:
        get_groundtruth(get_mbpp_plus(), get_mbpp_plus_hash(), MBPP_OUTPUT_NOT_NONE_TASKS)
    scratch = tempfile.mkdtemp(prefix="evalplus-sbx-", dir=os.path.dirname(samples))
    os.environ["TMPDIR"] = scratch
    tempfile.tempdir = scratch
    landlock([os.path.dirname(samples), "/dev/shm", "/dev/null"])
    socket_guard()
    print(f"sandbox: landlock(net TCP denied, fs writes -> {os.path.dirname(samples)}, /dev/shm), "
          f"socket guard, uid {os.getuid()}", flush=True)
    evaluate(dataset=a.dataset, samples=samples, parallel=a.parallel)


if __name__ == "__main__":
    main()
