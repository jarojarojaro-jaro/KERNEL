#!/usr/bin/env python3
"""Graft an MTP (nextn) head from a donor GGUF onto a target GGUF of the same geometry, streaming.

Built for Ternary Bonsai 2 27B (target, any pack: PTQ1_0 / PQ2_0 / Q2_0) + unsloth Qwen3.8-27B (donor, blk.64.*).
Stdlib only: gguf-py's GGUFReader raises on PrismML's private tensor types (PQ2_0 = 142, PTQ1_0 = 143) and needs
numpy, so this script parses GGUF itself and copies bytes.

Recipe, same as Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF (graft_mtp.py) and the sudoingx PTQ1_0 "lean" graft:
  * target KV entries and tensor infos are copied verbatim, in order; the target tensor data is copied as one blob,
    so every target tensor keeps identical bytes and identical offsets;
  * <arch>.block_count := donor value (64 -> 65, the MTP block is counted);
  * <arch>.nextn_predict_layers := donor value (1), appended after the target keys (Kujira's position);
  * donor tensors blk.<M>.* for the donor's MTP blocks (M >= donor block_count - nextn) are appended with their
    donor dtype and bytes, renumbered to the target's next block index if it differs;
  * nothing else is added (no blk.<M>.nextn.embed_tokens copy: PrismML releases >= prism-b10743 apply the Hadamard
    inverse to token_embd inside the MTP graph themselves).

usage:
  graft_mtp.py graft TARGET.gguf DONOR.gguf|DONOR_URL OUT.gguf [--full-verify]
      DONOR may be an https URL (e.g. HF resolve URL): then only its header and MTP tensor bytes are fetched with
      HTTP Range requests (~0.4 GB instead of the whole 17.5 GB file).
      --full-verify also re-hashes the copied target blob (re-reads ~6-8 GB).
  graft_mtp.py inspect FILE.gguf|URL [REGEX]    header summary (KVs, tensor types; tensors matching REGEX listed)
  graft_mtp.py verify OUT.gguf TARGET.gguf DONOR.gguf|URL [--full-verify]
"""
import hashlib
import os
import re
import struct
import sys
import urllib.request

GGUF_MAGIC = b"GGUF"
CHUNK = 64 << 20

# GGUF metadata value types
T_U8, T_I8, T_U16, T_I16, T_U32, T_I32, T_F32, T_BOOL, T_STR, T_ARR, T_U64, T_I64, T_F64 = range(13)
SCALAR = {T_U8: "<B", T_I8: "<b", T_U16: "<H", T_I16: "<h", T_U32: "<I", T_I32: "<i", T_F32: "<f", T_BOOL: "<?",
          T_U64: "<Q", T_I64: "<q", T_F64: "<d"}

# ggml type -> (name, block elements, block bytes); upstream gguf-py GGML_QUANT_SIZES + PrismML 142/143
QK_K = 256
GGML_TYPES = {
    0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18), 3: ("Q4_1", 32, 20), 6: ("Q5_0", 32, 22),
    7: ("Q5_1", 32, 24), 8: ("Q8_0", 32, 34), 9: ("Q8_1", 32, 36),
    10: ("Q2_K", 256, 2 + 2 + QK_K // 16 + QK_K // 4), 11: ("Q3_K", 256, 2 + QK_K // 4 + QK_K // 8 + 12),
    12: ("Q4_K", 256, 2 + 2 + QK_K // 2 + 12), 13: ("Q5_K", 256, 2 + 2 + QK_K // 2 + QK_K // 8 + 12),
    14: ("Q6_K", 256, 2 + QK_K // 2 + QK_K // 4 + QK_K // 16), 15: ("Q8_K", 256, 4 + QK_K + QK_K // 8),
    16: ("IQ2_XXS", 256, 2 + QK_K // 4), 17: ("IQ2_XS", 256, 2 + QK_K // 4 + QK_K // 32),
    18: ("IQ3_XXS", 256, 2 + QK_K // 4 + QK_K // 8), 19: ("IQ1_S", 256, 2 + QK_K // 8 + QK_K // 16),
    20: ("IQ4_NL", 32, 18), 21: ("IQ3_S", 256, 2 + QK_K // 4 + QK_K // 8 + QK_K // 32 + 4),
    22: ("IQ2_S", 256, 2 + QK_K // 4 + QK_K // 16), 23: ("IQ4_XS", 256, 2 + 2 + QK_K // 2 + QK_K // 64),
    24: ("I8", 1, 1), 25: ("I16", 1, 2), 26: ("I32", 1, 4), 27: ("I64", 1, 8), 28: ("F64", 1, 8),
    29: ("IQ1_M", 256, QK_K // 8 + QK_K // 16 + QK_K // 32), 30: ("BF16", 1, 2), 34: ("TQ1_0", 256, 2 + 4 * 13),
    35: ("TQ2_0", 256, 2 + 64), 39: ("MXFP4", 32, 17), 40: ("NVFP4", 64, 36), 41: ("Q1_0", 128, 18),
    42: ("Q2_0", 64, 18), 43: ("F8_E4M3", 1, 1), 142: ("PQ2_0", 128, 2 + 32), 143: ("PTQ1_0", 128, 2 + 24 + 2),
}


def type_name(t):
    return GGML_TYPES.get(t, ("type%d" % t,))[0]


def tensor_nbytes(ttype, dims):
    if ttype not in GGML_TYPES:
        raise ValueError("unknown ggml type %d" % ttype)
    _, be, bb = GGML_TYPES[ttype]
    n = 1
    for d in dims:
        n *= d
    if dims[0] % be:
        raise ValueError("row of %d elements is not a multiple of block %d" % (dims[0], be))
    return n // be * bb


def align(x, a):
    return (x + a - 1) // a * a


class Source:
    """Random-access byte source: local file or HTTP(S) URL read with Range requests."""

    def __init__(self, loc):
        self.loc = loc
        self.url = loc.startswith(("http://", "https://"))
        if self.url:
            self.f = None
            self.size = None
            self.pread(0, 1)  # learns the total size from Content-Range
            if self.size is None:
                raise IOError("%s: no Content-Range total in the reply" % loc)
        else:
            self.f = open(loc, "rb")
            self.size = os.fstat(self.f.fileno()).st_size

    def pread(self, off, n):
        if not self.url:
            self.f.seek(off)
            b = self.f.read(n)
        else:
            req = urllib.request.Request(self.loc, headers={"Range": "bytes=%d-%d" % (off, off + n - 1),
                                                            "User-Agent": "graft_mtp/1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                if r.status != 206:
                    raise IOError("%s: server ignored Range (HTTP %d)" % (self.loc, r.status))
                cr = r.headers.get("Content-Range", "")
                if self.size is None and "/" in cr and cr.rsplit("/", 1)[1].isdigit():
                    self.size = int(cr.rsplit("/", 1)[1])
                b = r.read()
        if len(b) != n:
            raise IOError("%s: short read at %d (%d of %d bytes)" % (self.loc, off, len(b), n))
        return b

    def stream(self, off, n, sink):
        """Feed bytes [off, off+n) to sink(chunk) in CHUNK pieces."""
        if not self.url:
            self.f.seek(off)
            left = n
            while left:
                b = self.f.read(min(CHUNK, left))
                if not b:
                    raise IOError("%s: EOF at %d" % (self.loc, off + n - left))
                sink(b)
                left -= len(b)
            return
        done = 0
        while done < n:
            k = min(CHUNK, n - done)
            for attempt in range(4):
                try:
                    b = self.pread(off + done, k)
                    break
                except (IOError, OSError):
                    if attempt == 3:
                        raise
            sink(b)
            done += k


class Cursor:
    """Sequential reader over a Source with a growing window (header parsing)."""

    def __init__(self, src, first=16 << 20):
        self.src = src
        self.buf = src.pread(0, first if src.size is None else min(first, src.size))
        self.base = 0
        self.pos = 0
        self.step = first

    def need(self, n):
        while self.pos + n > self.base + len(self.buf):
            want = max(self.step, n)
            start = self.base + len(self.buf)
            if self.src.size is not None:
                want = min(want, self.src.size - start)
                if want <= 0:
                    raise IOError("%s: header runs past EOF" % self.src.loc)
            self.buf += self.src.pread(start, want)

    def take(self, n):
        self.need(n)
        i = self.pos - self.base
        self.pos += n
        return self.buf[i:i + n]

    def unpack(self, fmt):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def string(self):
        return self.take(self.unpack("<Q")).decode("utf-8", "replace")

    def raw(self, a, b):
        return self.buf[a - self.base:b - self.base]


class KV:
    __slots__ = ("key", "vtype", "value", "raw", "atype", "alen")


class TI:
    __slots__ = ("name", "dims", "ttype", "offset", "raw", "nbytes")


class Gguf:
    def __init__(self, loc):
        self.src = Source(loc)
        c = Cursor(self.src)
        if c.take(4) != GGUF_MAGIC:
            raise ValueError("%s: not a GGUF file" % loc)
        self.version = c.unpack("<I")
        if self.version != 3:
            raise ValueError("%s: GGUF v%d unsupported (need v3)" % (loc, self.version))
        n_tensors = c.unpack("<Q")
        n_kv = c.unpack("<Q")
        self.kvs = []
        for _ in range(n_kv):
            a = c.pos
            kv = KV()
            kv.key = c.string()
            kv.vtype = c.unpack("<I")
            kv.atype = kv.alen = None
            kv.value = self._value(c, kv)
            kv.raw = bytes(c.raw(a, c.pos))
            self.kvs.append(kv)
        self.kv = {kv.key: kv for kv in self.kvs}
        self.tensors = []
        for _ in range(n_tensors):
            a = c.pos
            t = TI()
            t.name = c.string()
            nd = c.unpack("<I")
            t.dims = [c.unpack("<Q") for _ in range(nd)]
            t.ttype = c.unpack("<I")
            t.offset = c.unpack("<Q")
            t.raw = bytes(c.raw(a, c.pos))
            t.nbytes = tensor_nbytes(t.ttype, t.dims) if t.ttype in GGML_TYPES else None
            self.tensors.append(t)
        self.tensor = {t.name: t for t in self.tensors}
        self.alignment = self.get("general.alignment", 32)
        self.header_end = c.pos
        self.data_start = align(c.pos, self.alignment)
        self.arch = self.get("general.architecture")

    @staticmethod
    def _value(c, kv):
        vt = kv.vtype
        if vt in SCALAR:
            return c.unpack(SCALAR[vt])
        if vt == T_STR:
            return c.string()
        if vt != T_ARR:
            raise ValueError("bad GGUF value type %d for %s" % (vt, kv.key))
        at = c.unpack("<I")
        n = c.unpack("<Q")
        kv.atype, kv.alen = at, n
        if at == T_STR:
            out = []
            for _ in range(n):
                s = c.unpack("<Q")
                b = c.take(s)
                if len(out) < 8:
                    out.append(b.decode("utf-8", "replace"))
            return out if n <= 8 else "<%d strings>" % n
        if at not in SCALAR:
            raise ValueError("unsupported array type %d for %s" % (at, kv.key))
        sz = struct.calcsize(SCALAR[at])
        b = c.take(sz * n)
        if n <= 64:
            return list(struct.unpack("<%d%s" % (n, SCALAR[at][1]), b))
        return "<%d x %s>" % (n, SCALAR[at][1])

    def get(self, key, default=None):
        kv = self.kv.get(key)
        return default if kv is None else kv.value

    def file_size(self):
        return self.src.size


def enc_str(s):
    b = s.encode("utf-8")
    return struct.pack("<Q", len(b)) + b


def enc_kv_u32(key, v):
    return enc_str(key) + struct.pack("<II", T_U32, v)


def enc_ti(name, dims, ttype, offset):
    return enc_str(name) + struct.pack("<I", len(dims)) + b"".join(struct.pack("<Q", d) for d in dims) + \
        struct.pack("<IQ", ttype, offset)


def blk_index(name):
    m = re.match(r"blk\.(\d+)\.", name)
    return int(m.group(1)) if m else None


def plan(tg, dn):
    """Check compatibility and compute the output header + tensor placement. Returns a dict."""
    arch = tg.arch
    die = lambda msg: sys.exit("graft_mtp: " + msg)  # noqa: E731
    if arch != dn.arch:
        die("architecture mismatch: target %s, donor %s" % (arch, dn.arch))
    k_bc, k_nn = arch + ".block_count", arch + ".nextn_predict_layers"
    t_bc, d_bc = tg.get(k_bc), dn.get(k_bc)
    t_nn, d_nn = tg.get(k_nn, 0), dn.get(k_nn, 0)
    if t_nn:
        die("target already has %s = %d" % (k_nn, t_nn))
    if not d_nn:
        die("donor has no %s (no MTP head)" % k_nn)
    if t_bc != d_bc - d_nn:
        die("target %s = %s but donor trunk is %s - %s" % (k_bc, t_bc, d_bc, d_nn))
    # geometry the MTP block depends on must match exactly
    for k in ("embedding_length", "feed_forward_length", "attention.head_count", "attention.head_count_kv",
              "attention.key_length", "attention.value_length", "rope.dimension_count", "rope.freq_base",
              "attention.layer_norm_rms_epsilon", "full_attention_interval"):
        a, b = tg.get(arch + "." + k), dn.get(arch + "." + k)
        if a != b:
            die("%s.%s differs: target %r, donor %r" % (arch, k, a, b))
    tv, dv = tg.kv.get("tokenizer.ggml.tokens"), dn.kv.get("tokenizer.ggml.tokens")
    if tv is None or dv is None or tv.alen != dv.alen:
        die("vocabulary size differs")
    # per-layer array KVs sized by block_count would need a 65th entry; refuse rather than guess
    for kv in tg.kvs:
        if kv.key.startswith(arch + ".") and kv.alen == t_bc and kv.atype in SCALAR:
            die("per-layer array %s (len %d) would need an entry for the MTP block" % (kv.key, kv.alen))
    # every target tensor must exist in the donor with the same shape (Kujira's check; dtype may differ)
    for t in tg.tensors:
        d = dn.tensor.get(t.name)
        if d is None:
            die("donor lacks %s" % t.name)
        if d.dims != t.dims:
            die("shape mismatch at %s: target %s, donor %s" % (t.name, t.dims, d.dims))
    mtp_blocks = set(range(d_bc - d_nn, d_bc))
    extra = [t for t in dn.tensors if blk_index(t.name) in mtp_blocks]
    if not extra:
        die("donor has no tensors in blocks %s" % sorted(mtp_blocks))
    stray = [t.name for t in dn.tensors if t.name not in tg.tensor and blk_index(t.name) not in mtp_blocks]
    if stray:
        die("donor-only tensors outside the MTP block(s): %s" % stray[:8])
    clash = [t.name for t in tg.tensors if blk_index(t.name) is not None and blk_index(t.name) >= t_bc]
    if clash:
        die("target already has tensors past its last block: %s" % clash[:8])
    for t in extra:
        if t.nbytes is None:
            die("donor tensor %s has unknown type %d" % (t.name, t.ttype))
    shift = t_bc - (d_bc - d_nn)  # 0 for Bonsai/Qwen (both 64)

    # output layout: target header entries verbatim + block_count/nextn edits + donor infos, then target data blob,
    # then donor tensors, each aligned like the target
    a = tg.alignment
    t_size = tg.file_size()
    t_blob = t_size - tg.data_start
    t_end = max(t.offset + t.nbytes for t in tg.tensors if t.nbytes is not None) if all(
        t.nbytes is not None for t in tg.tensors) else None
    if t_end is not None and t_end > t_blob:
        die("target data shorter than its tensor table says (%d > %d)" % (t_end, t_blob))
    for t in tg.tensors:
        if t.offset % a or t.offset >= t_blob:
            die("target tensor %s has a bad offset %d" % (t.name, t.offset))
    kv_bytes = []
    for kv in tg.kvs:
        kv_bytes.append(enc_kv_u32(k_bc, d_bc + shift) if kv.key == k_bc and kv.vtype == T_U32 else kv.raw)
        if kv.key == k_bc and kv.vtype != T_U32:
            die("%s has type %d, expected u32" % (k_bc, kv.vtype))
    kv_bytes.append(dn.kv[k_nn].raw)
    n_kv = len(tg.kvs) + 1

    off = align(t_blob, a)
    placed = []
    for t in extra:
        name = t.name if not shift else re.sub(r"^blk\.(\d+)\.", lambda m: "blk.%d." % (int(m.group(1)) + shift),
                                                t.name)
        placed.append((name, t, off))
        off = align(off + t.nbytes, a)
    ti_bytes = [t.raw for t in tg.tensors] + [enc_ti(n, t.dims, t.ttype, o) for n, t, o in placed]
    header = GGUF_MAGIC + struct.pack("<IQQ", 3, len(tg.tensors) + len(placed), n_kv) + b"".join(kv_bytes) + \
        b"".join(ti_bytes)
    data_start = align(len(header), a)
    last_name, last_t, last_off = placed[-1]
    total = data_start + last_off + last_t.nbytes
    return dict(header=header, data_start=data_start, t_blob=t_blob, placed=placed, total=total, k_bc=k_bc,
                k_nn=k_nn, bc=d_bc + shift, nn=d_nn)


def write_out(tg, dn, p, out):
    tmp = out + ".part"
    t_hash = hashlib.sha256()
    donor_hash = {}
    with open(tmp, "wb") as f:
        f.write(p["header"])
        f.write(b"\0" * (p["data_start"] - len(p["header"])))

        def sink(b):
            f.write(b)
            t_hash.update(b)
        tg.src.stream(tg.data_start, p["t_blob"], sink)
        print("target data copied: %d bytes" % p["t_blob"], flush=True)
        for name, t, off in p["placed"]:
            pos = p["data_start"] + off
            if f.tell() > pos:
                sys.exit("graft_mtp: layout overlap at %s" % name)
            f.write(b"\0" * (pos - f.tell()))
            h = hashlib.sha256()

            def sink2(b, h=h):
                f.write(b)
                h.update(b)
            dn.src.stream(dn.data_start + t.offset, t.nbytes, sink2)
            donor_hash[name] = h.hexdigest()
            print("  + %-40s %-6s %-22s %10d B" % (name, type_name(t.ttype), t.dims, t.nbytes), flush=True)
        if f.tell() != p["total"]:
            sys.exit("graft_mtp: wrote %d bytes, expected %d" % (f.tell(), p["total"]))
    os.replace(tmp, out)
    return t_hash.hexdigest(), donor_hash


def verify(out, tg, dn, full=False, t_hash=None, donor_hash=None):
    """Re-read the output header and check it against target + donor; hash the grafted tensors back."""
    o = Gguf(out)
    arch = tg.arch
    bad = []
    chk = lambda cond, msg: cond or bad.append(msg)  # noqa: E731
    k_bc, k_nn = arch + ".block_count", arch + ".nextn_predict_layers"
    d_bc, d_nn = dn.get(k_bc), dn.get(k_nn)
    chk(o.arch == arch, "arch %s" % o.arch)
    chk(o.get(k_bc) == tg.get(k_bc) + d_nn, "%s = %s" % (k_bc, o.get(k_bc)))
    chk(o.get(k_nn) == d_nn, "%s = %s" % (k_nn, o.get(k_nn)))
    chk(o.alignment == tg.alignment, "alignment %d" % o.alignment)
    # every target KV unchanged except block_count; exactly one extra key
    okeys = [kv.key for kv in o.kvs]
    chk(okeys == [kv.key for kv in tg.kvs] + [k_nn], "KV key order differs from target + %s" % k_nn)
    for kv in tg.kvs:
        if kv.key != k_bc:
            chk(o.kv[kv.key].raw == kv.raw, "KV %s changed" % kv.key)
    # target tensors: same infos (name, dims, type, offset) and the data blob starts at the same relative place
    chk(len(o.tensors) == len(tg.tensors) + sum(1 for t in dn.tensors if blk_index(t.name) is not None and
                                                 blk_index(t.name) >= d_bc - d_nn),
        "tensor count %d" % len(o.tensors))
    for t in tg.tensors:
        ot = o.tensor.get(t.name)
        chk(ot is not None and (ot.dims, ot.ttype, ot.offset) == (t.dims, t.ttype, t.offset),
            "target tensor %s differs" % t.name)
    size = o.file_size()
    t_blob = tg.file_size() - tg.data_start
    shift = tg.get(k_bc) - (d_bc - d_nn)
    for t in dn.tensors:
        bi = blk_index(t.name)
        if bi is None or bi < d_bc - d_nn:
            continue
        name = "blk.%d.%s" % (bi + shift, t.name.split(".", 2)[2])
        ot = o.tensor.get(name)
        if ot is None:
            bad.append("missing %s" % name)
            continue
        chk((ot.dims, ot.ttype) == (t.dims, t.ttype), "grafted %s dims/type differ" % name)
        chk(ot.offset % o.alignment == 0 and ot.offset >= t_blob, "grafted %s offset %d" % (name, ot.offset))
        chk(o.data_start + ot.offset + ot.nbytes <= size, "grafted %s past EOF" % name)
        h = hashlib.sha256()
        o.src.stream(o.data_start + ot.offset, ot.nbytes, h.update)
        if donor_hash is not None:
            chk(h.hexdigest() == donor_hash.get(name), "grafted %s bytes differ from donor" % name)
        else:
            hd = hashlib.sha256()
            dn.src.stream(dn.data_start + t.offset, t.nbytes, hd.update)
            chk(h.hexdigest() == hd.hexdigest(), "grafted %s bytes differ from donor" % name)
    if full:
        if t_hash is None:
            ht = hashlib.sha256()
            tg.src.stream(tg.data_start, t_blob, ht.update)
            t_hash = ht.hexdigest()
        ho = hashlib.sha256()
        o.src.stream(o.data_start, t_blob, ho.update)
        chk(ho.hexdigest() == t_hash, "target data blob differs in output")
    if bad:
        print("VERIFY FAILED:\n  " + "\n  ".join(bad[:40]))
        return False
    print("verify OK: %s = %d, %s = %d, %d tensors (%d grafted), header %d B, file %d B%s"
          % (k_bc, o.get(k_bc), k_nn, o.get(k_nn), len(o.tensors), len(o.tensors) - len(tg.tensors),
             o.data_start, size, ", target blob sha256 match" if full else ""))
    return True


def inspect(loc, pattern=None):
    g = Gguf(loc)
    print("%s\n  GGUF v%d, %d KV, %d tensors, alignment %d, data_start %d"
          % (loc, g.version, len(g.kvs), len(g.tensors), g.alignment, g.data_start))
    for kv in g.kvs:
        v = kv.value
        if isinstance(v, str) and len(v) > 100:
            v = v[:100] + "..."
        print("  kv  %-48s %s" % (kv.key, v))
    hist = {}
    for t in g.tensors:
        hist[type_name(t.ttype)] = hist.get(type_name(t.ttype), 0) + 1
    print("  types", hist)
    rx = re.compile(pattern) if pattern else None
    for t in g.tensors:
        if rx and rx.search(t.name):
            print("  t   %-44s %-7s %-24s off %d nbytes %s" % (t.name, type_name(t.ttype), t.dims, t.offset, t.nbytes))


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, args = argv[1], [a for a in argv[2:] if not a.startswith("--")]
    full = "--full-verify" in argv
    if cmd == "inspect" and len(args) in (1, 2):
        inspect(*args)
        return 0
    if cmd == "graft" and len(args) == 3:
        target, donor, out = args
        if os.path.abspath(out) in (os.path.abspath(target), os.path.abspath(donor)):
            sys.exit("graft_mtp: output must be a new file")
        tg, dn = Gguf(target), Gguf(donor)
        p = plan(tg, dn)
        print("target %s: %s %s = %d, %d tensors, data %d B" % (target, tg.arch, p["k_bc"], tg.get(p["k_bc"]),
                                                                 len(tg.tensors), p["t_blob"]))
        print("donor  %s: %s = %d, %s = %d, grafting %d tensors (%d B)"
              % (donor, p["k_bc"], dn.get(p["k_bc"]), p["k_nn"], p["nn"], len(p["placed"]),
                 sum(t.nbytes for _, t, _ in p["placed"])), flush=True)
        t_hash, donor_hash = write_out(tg, dn, p, out)
        return 0 if verify(out, tg, dn, full, t_hash if full else None, donor_hash) else 1
    if cmd == "verify" and len(args) == 3:
        out, target, donor = args
        return 0 if verify(out, Gguf(target), Gguf(donor), full) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
