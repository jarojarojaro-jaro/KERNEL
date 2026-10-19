#!/usr/bin/env python3
"""pm4_synth_tape.py HSACO KERNEL_SYMBOL OUT.bin [--wa N]

Builds a 2-dispatch PM4 IB byte-for-byte the way ggml_hip_pm4_build (hip-pm4.cu @ b7fb3fe85) does, using the real
kernel descriptor (<sym>.kd) of a gfx1100 code object. Addresses are fake (kernarg 0x7f0000001000, code 0x7f0000100000).
Purpose: decode offline with `umr -f <asic> -df OUT.bin` and check RSRC1.PRIV / initiator / RESTART_* per WA level.
"""
import struct, subprocess, sys

LLVM = '/opt/rocm/llvm/bin/'
OP_SET_SH_REG, OP_DISPATCH_DIRECT, OP_EVENT_WRITE, OP_ACQUIRE_MEM = 0x76, 0x15, 0x46, 0x58
R_NUM_THREAD_X, R_PGM_LO, R_PGM_RSRC1, R_RESOURCE_LIMITS = 0x207, 0x20c, 0x212, 0x215
R_TMPRING_SIZE, R_RESTART_X, R_PGM_RSRC3, R_USER_DATA_0 = 0x218, 0x21b, 0x228, 0x240


def pkt3(op, body, compute):
    return (3 << 30) | ((body - 1) << 16) | (op << 8) | (2 if compute else 0)


def kernel_descriptor(hsaco, sym):
    """Return (rsrc1, rsrc2, rsrc3, props, group_segment) from the 64-byte <sym>.kd in .rodata."""
    syms = subprocess.run([LLVM + 'llvm-nm', '--defined-only', '-S', hsaco], capture_output=True, text=True).stdout
    for line in syms.splitlines():
        p = line.split()
        if len(p) == 4 and p[3] == sym + '.kd':
            addr = int(p[0], 16)
            break
    else:
        sys.exit(f'{sym}.kd not found')
    hdr = subprocess.run([LLVM + 'llvm-readelf', '-S', '-W', hsaco], capture_output=True, text=True).stdout
    for line in hdr.splitlines():
        if ' .rodata ' in line:
            f = line.split()
            i = f.index('.rodata')
            sec_addr, sec_off = int(f[i + 2], 16), int(f[i + 3], 16)
    with open(hsaco, 'rb') as fh:
        fh.seek(sec_off + addr - sec_addr)
        kd = fh.read(64)
    group, = struct.unpack_from('<I', kd, 0)
    rsrc3, rsrc1, rsrc2 = struct.unpack_from('<III', kd, 44)
    props, = struct.unpack_from('<H', kd, 56)
    return rsrc1, rsrc2, rsrc3, props, group


def build(kd, wa, n=2, grid=(1280, 1, 1), block=(32, 4, 1)):
    rsrc1, rsrc2_kd, rsrc3, props, group = kd
    dw = []
    sh = lambda reg, v: dw.extend([pkt3(OP_SET_SH_REG, 1 + len(v), True), reg, *v])
    dw += [pkt3(OP_ACQUIRE_MEM, 7, False), 0, 0xffffffff, 0xff, 0, 0, 4,
           (1 << 16) | (1 << 15) | (1 << 14) | (1 << 9) | (1 << 8) | (1 << 7) | (1 << 6) | (1 << 5) | (1 << 4) | 1]
    code, ka = 0x7f0000100000, 0x7f0000001000
    for i in range(n):
        if i > 0:
            dw += [pkt3(OP_EVENT_WRITE, 1, False), 0x407]
            dw += [pkt3(OP_ACQUIRE_MEM, 7, False), 0, 0xffffffff, 0x00ffffff, 0, 0, 10, 0x380]
        lds_blocks = (group + 511) // 512
        rsrc2 = (rsrc2_kd & ~0x00ff8000) | (lds_blocks << 15)
        kaddr = ka + 0x100 * i
        sh(R_PGM_LO, [(code >> 8) & 0xffffffff, (code >> 40) & 0xffffffff])
        sh(R_PGM_RSRC1, [rsrc1 | ((1 << 20) if wa >= 1 else 0), rsrc2])
        sh(R_PGM_RSRC3, [rsrc3])
        sh(R_TMPRING_SIZE, [0])
        sh(R_NUM_THREAD_X, list(block))
        sh(R_RESOURCE_LIMITS, [0])
        if wa >= 2:
            sh(R_RESTART_X, [0, 0, 0])
        if props & 1:
            sh(R_USER_DATA_0, [0, 0, 0, 0, kaddr & 0xffffffff, kaddr >> 32])
        else:
            sh(R_USER_DATA_0, [kaddr & 0xffffffff, kaddr >> 32])
        initiator = 1 | 4 | (0 if wa >= 2 else 8) | ((1 << 15) if props & (1 << 10) else 0)
        dw += [pkt3(OP_DISPATCH_DIRECT, 4, True), *grid, initiator]
    dw += [pkt3(OP_EVENT_WRITE, 1, False), 0x407]
    dw += [pkt3(OP_ACQUIRE_MEM, 7, False), 0, 0xffffffff, 0xff, 0, 0, 4,
           (1 << 16) | (1 << 15) | (1 << 14) | (1 << 9) | (1 << 8) | (1 << 7) | (1 << 6) | (1 << 5) | (1 << 4) | 1]
    return dw


if __name__ == '__main__':
    hsaco, sym, out = sys.argv[1:4]
    wa = int(sys.argv[sys.argv.index('--wa') + 1]) if '--wa' in sys.argv else 0
    kd = kernel_descriptor(hsaco, sym)
    print(f'descriptor: rsrc1=0x{kd[0]:08x} (PRIV={kd[0] >> 20 & 1}) rsrc2=0x{kd[1]:08x} '
          f'(TRAP_PRESENT={kd[1] >> 6 & 1}) rsrc3=0x{kd[2]:08x} props=0x{kd[3]:04x} lds={kd[4]}')
    dw = build(kd, wa)
    with open(out, 'wb') as fh:
        fh.write(struct.pack(f'<{len(dw)}I', *dw))
    print(f'{len(dw)} dwords -> {out}')
