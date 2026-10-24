// Minimal GGUF header reader: metadata key/values and tensor infos, never tensor data.
// Format: https://github.com/ggml-org/ggml/blob/master/docs/gguf.md (v2/v3, little-endian).

export type GgufScalar = number | bigint | boolean | string;
/** Arrays longer than ARRAY_KEEP are summarised as their length only (tokenizer vocabularies are huge). */
export type GgufValue = GgufScalar | GgufScalar[] | { arrayLength: number };

export interface GgufTensor { name: string; dims: number[]; type: number }

/** ggml type id → [elements per block, bytes per block] for the types seen in our catalog (ggml.h order). */
const GGML_BLOCKS: Record<number, [number, number]> = {
  0: [1, 4], 1: [1, 2], 2: [32, 18], 3: [32, 20], 6: [32, 22], 7: [32, 24], 8: [32, 34], 10: [256, 84], 11: [256, 110],
  12: [256, 144], 13: [256, 176], 14: [256, 210], 15: [256, 292], 16: [256, 66], 17: [256, 74], 18: [256, 98],
  19: [256, 50], 20: [32, 18], 21: [256, 110], 22: [256, 82], 23: [256, 136], 29: [256, 56], 30: [1, 2], 39: [32, 17],
  40: [64, 36], 41: [16, 9],
};

/** Bytes of a tensor's data, or null for a ggml type this table does not know. */
export function tensorBytes(t: GgufTensor): number | null {
  const b = GGML_BLOCKS[t.type];
  if (!b) return null;
  const n = t.dims.reduce((a, d) => a * d, 1);
  return (n / b[0]) * b[1];
}

export interface GgufHeader { version: number; kv: Map<string, GgufValue>; tensors: GgufTensor[]; headerBytes: number }

const ARRAY_KEEP = 4096;
const CHUNK = 4 << 20;

/** Reads the header of a local .gguf file in growing chunks (a few MB for any model). */
export async function readGgufHeader(path: string): Promise<GgufHeader> {
  const file = Bun.file(path);
  const size = file.size;
  let buf = new Uint8Array(await file.slice(0, Math.min(CHUNK, size)).arrayBuffer());
  let view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  let pos = 0;

  const ensure = async (n: number): Promise<void> => {
    if (pos + n <= buf.byteLength) return;
    if (pos + n > size) throw new Error(`${path}: truncated GGUF header`);
    const want = Math.min(size, Math.max(pos + n, buf.byteLength * 2));
    buf = new Uint8Array(await file.slice(0, want).arrayBuffer());
    view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  };
  const u32 = async (): Promise<number> => { await ensure(4); const v = view.getUint32(pos, true); pos += 4; return v; };
  const u64 = async (): Promise<number> => {
    await ensure(8);
    const v = view.getBigUint64(pos, true);
    pos += 8;
    if (v > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error(`${path}: GGUF length out of range`);
    return Number(v);
  };
  const str = async (): Promise<string> => {
    const n = await u64();
    await ensure(n);
    const s = new TextDecoder().decode(buf.subarray(pos, pos + n));
    pos += n;
    return s;
  };
  const scalar = async (t: number): Promise<GgufScalar> => {
    switch (t) {
      case 0: await ensure(1); pos += 1; return view.getUint8(pos - 1);
      case 1: await ensure(1); pos += 1; return view.getInt8(pos - 1);
      case 2: await ensure(2); pos += 2; return view.getUint16(pos - 2, true);
      case 3: await ensure(2); pos += 2; return view.getInt16(pos - 2, true);
      case 4: return u32();
      case 5: await ensure(4); pos += 4; return view.getInt32(pos - 4, true);
      case 6: await ensure(4); pos += 4; return view.getFloat32(pos - 4, true);
      case 7: await ensure(1); pos += 1; return view.getUint8(pos - 1) !== 0;
      case 8: return str();
      case 10: await ensure(8); pos += 8; return view.getBigUint64(pos - 8, true);
      case 11: await ensure(8); pos += 8; return view.getBigInt64(pos - 8, true);
      case 12: await ensure(8); pos += 8; return view.getFloat64(pos - 8, true);
      default: throw new Error(`${path}: unknown GGUF value type ${t}`);
    }
  };
  const FIXED: Record<number, number> = { 0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8 };
  const value = async (t: number): Promise<GgufValue> => {
    if (t !== 9) return scalar(t);
    const et = await u32();
    const n = await u64();
    const width = FIXED[et];
    if (n > ARRAY_KEEP) {
      if (width !== undefined) { await ensure(n * width); pos += n * width; }
      else for (let i = 0; i < n; i++) await value(et);
      return { arrayLength: n };
    }
    const out: GgufScalar[] = [];
    for (let i = 0; i < n; i++) {
      const v = await value(et);
      if (typeof v === 'object') throw new Error(`${path}: nested GGUF arrays are not supported`);
      out.push(v);
    }
    return out;
  };

  await ensure(4);
  if (new TextDecoder().decode(buf.subarray(0, 4)) !== 'GGUF') throw new Error(`${path}: not a GGUF file`);
  pos = 4;
  const version = await u32();
  if (version < 2) throw new Error(`${path}: GGUF v${version} is not supported`);
  const nTensors = await u64();
  const nKv = await u64();
  const kv = new Map<string, GgufValue>();
  for (let i = 0; i < nKv; i++) {
    const k = await str();
    kv.set(k, await value(await u32()));
  }
  const tensors: GgufTensor[] = [];
  for (let i = 0; i < nTensors; i++) {
    const name = await str();
    const nd = await u32();
    const dims: number[] = [];
    for (let d = 0; d < nd; d++) dims.push(await u64());
    const type = await u32();
    await u64(); // data offset
    tensors.push({ name, dims, type });
  }
  return { version, kv, tensors, headerBytes: pos };
}

/** Architecture facts the memory model needs, derived from a GGUF header. */
export interface GgufArch {
  arch: string;
  nLayer: number;
  /** Trailing MTP/NextN blocks counted in block_count. */
  nextn: number;
  nEmbd: number;
  nVocab: number;
  ctxTrain: number;
  /** Full-attention layers (cache grows with ctx) and their per-token K/V widths in elements. */
  full: { layers: number; kvHeads: number; keyLen: number; valueLen: number };
  /** Sliding-window layers (cache = window + ubatch, rounded to 256). */
  swa: { layers: number; kvHeads: number; keyLen: number; valueLen: number; window: number };
  experts: number;
  expertsUsed: number;
}

const num = (v: GgufValue | undefined): number | undefined => {
  if (typeof v === 'number') return v;
  if (typeof v === 'bigint') return Number(v);
  return undefined;
};

export function ggufArch(h: GgufHeader): GgufArch {
  const archV = h.kv.get('general.architecture');
  if (typeof archV !== 'string') throw new Error('GGUF without general.architecture');
  const arch = archV;
  const g = (k: string): GgufValue | undefined => h.kv.get(`${arch}.${k}`);
  const nLayer = num(g('block_count')) ?? 0;
  const nextn = num(g('nextn_predict_layers')) ?? 0;
  const nEmbd = num(g('embedding_length')) ?? 0;
  const nHead = num(g('attention.head_count')) ?? 0;
  const tok = h.kv.get('tokenizer.ggml.tokens');
  const byName = new Map(h.tensors.map((t) => [t.name, t]));
  const out = byName.get('output.weight') ?? byName.get('token_embd.weight');
  const nVocab = num(g('vocab_size'))
    ?? (tok && typeof tok === 'object' && !Array.isArray(tok) ? tok.arrayLength : Array.isArray(tok) ? tok.length : undefined)
    ?? out?.dims[1] ?? 0;
  const window = num(g('attention.sliding_window')) ?? 0;
  const pattern = g('attention.sliding_window_pattern');
  const isSwa = (l: number): boolean => {
    if (window <= 0) return false;
    if (Array.isArray(pattern)) return Boolean(pattern[l]);
    if (arch === 'gpt-oss') return l % 2 === 0; // llama.cpp set_swa_pattern(2): even layers slide
    return false;
  };
  const full = { layers: 0, kvHeads: 0, keyLen: 0, valueLen: 0 };
  const swa = { layers: 0, kvHeads: 0, keyLen: 0, valueLen: 0, window };
  const headCountKv = g('attention.head_count_kv');
  const keyLenDefault = num(g('attention.key_length')) ?? (nHead ? nEmbd / nHead : 0);
  for (let l = 0; l < nLayer - nextn; l++) {
    const k = byName.get(`blk.${l}.attn_k.weight`);
    if (!k) continue; // recurrent / conv / linear-attention block
    const v = byName.get(`blk.${l}.attn_v.weight`);
    const kDim = k.dims[1] ?? 0;
    const vDim = v ? v.dims[1] ?? 0 : kDim; // no attn_v: V = K, still cached (Gemma 4 global layers)
    const hkv = Array.isArray(headCountKv) ? Number(headCountKv[l] ?? 0) : num(headCountKv) ?? 0;
    const heads = hkv > 0 ? hkv : Math.max(1, Math.round(kDim / keyLenDefault));
    const target = isSwa(l) ? swa : full;
    target.layers += 1;
    target.kvHeads = heads;
    target.keyLen = kDim / heads;
    target.valueLen = vDim / heads;
  }
  return {
    arch, nLayer, nextn, nEmbd, nVocab, ctxTrain: num(g('context_length')) ?? 0, full, swa,
    experts: num(g('expert_count')) ?? 0, expertsUsed: num(g('expert_used_count')) ?? 0,
  };
}
