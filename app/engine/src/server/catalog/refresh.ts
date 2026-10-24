// Refreshes the generated fields of data/catalog.json:
//  - per quant: sizeBytes + sha256 from the HF tree API (JSON only, `lfs.oid` = sha256), hostEmbdBytes, bTokGB;
//  - per model: arch (KV/attention layout, state, vocab) and ctxMax from the GGUF header of a LOCAL file when one is found
//    under ENIGMA_MODELS_DIR (header only), else from the model's HF config.json.
// Usage: ENIGMA_MODELS_DIR=~/models bun src/server/catalog/refresh.ts [--check]
//   --check: print differences, do not write.
import { readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { ggufArch, readGgufHeader, tensorBytes, type GgufHeader } from './gguf.ts';
import type { Catalog, CatalogModel, ModelArch, QuantFile } from './data.ts';

const MiB = 1024 * 1024;
const CATALOG_PATH = resolve(import.meta.dir, '../../../data/catalog.json');
const HF = 'https://huggingface.co';

type Json = Record<string, unknown>;
const obj = (v: unknown): Json => (v && typeof v === 'object' && !Array.isArray(v) ? (v as Json) : {});
const numOf = (v: unknown): number | undefined => (typeof v === 'number' ? v : undefined);
const need = (j: Json, k: string, where: string): number => {
  const v = numOf(j[k]);
  if (v === undefined) throw new Error(`${where}: config.json has no numeric ${k}`);
  return v;
};

interface TreeEntry { path: string; size: number; lfs?: { oid: string; size: number } }

async function hfJson(url: string): Promise<unknown> {
  const r = await fetch(url, { headers: { accept: 'application/json' } });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
}

const trees = new Map<string, Map<string, TreeEntry>>();
async function tree(repo: string): Promise<Map<string, TreeEntry>> {
  const hit = trees.get(repo);
  if (hit) return hit;
  const list = (await hfJson(`${HF}/api/models/${repo}/tree/main?recursive=true`)) as TreeEntry[];
  const m = new Map(list.map((e) => [e.path, e]));
  trees.set(repo, m);
  return m;
}

/** GGUF files under dir, two levels deep (CONTRACT: ENIGMA_MODELS_DIR is scanned shallowly). */
function localGgufs(dir: string | undefined): Map<string, string> {
  const out = new Map<string, string>();
  if (!dir) return out;
  const walk = (d: string, depth: number): void => {
    let names: string[];
    try { names = readdirSync(d); } catch { return; }
    for (const n of names) {
      const p = join(d, n);
      let st;
      try { st = statSync(p); } catch { continue; }
      if (st.isDirectory() && depth < 2) walk(p, depth + 1);
      else if (st.isFile() && n.endsWith('.gguf') && !out.has(n)) out.set(n, p);
    }
  };
  walk(dir.replace(/^~(?=\/|$)/, process.env.HOME ?? '~'), 0);
  return out;
}

/** Nominal bits/weight of token_embd / output for a quant name when no header is available. */
function embdBpw(quant: string): number {
  if (/Q8|MXFP4/.test(quant)) return 8.5;
  if (/Q6/.test(quant)) return 6.5625;
  if (/Q5/.test(quant)) return 5.5;
  if (/Q3/.test(quant)) return 3.4375;
  return 4.5;
}

/** Our engine's reduced MTP draft vocabulary (64k rows of head + embedding) and requant cache (qwen35, report 04/fitcalc). */
function mtpExtra(nEmbd: number, headBpw: number, embBpw: number): number {
  return (65536 * nEmbd * (headBpw + embBpw)) / 8 / MiB + (385.2 * nEmbd) / 5120;
}

function archFromGguf(h: GgufHeader, file: string): { arch: ModelArch; ctxMax: number } {
  const a = ggufArch(h);
  const g = (k: string): number => {
    const v = h.kv.get(`${a.arch}.${k}`);
    return typeof v === 'number' ? v : 0;
  };
  const byName = new Map(h.tensors.map((t) => [t.name, t]));
  const out = byName.get('output.weight');
  const emb = byName.get('token_embd.weight');
  const isMtp = (name: string): boolean => {
    const m = /^blk\.(\d+)\./.exec(name);
    return a.nextn > 0 && m !== null && Number(m[1]) >= a.nLayer - a.nextn;
  };
  let stateMiB = 0;
  const inner = g('ssm.inner_size'), state = g('ssm.state_size'), heads = g('ssm.time_step_rank');
  if (inner && state && heads) {
    const nRec = h.tensors.filter((t) => t.name.endsWith('ssm_out.weight') && !isMtp(t.name)).length;
    const S = nRec * heads * state * (inner / heads) * 4;
    const R = nRec * (g('ssm.conv_kernel') - 1) * (inner + 2 * g('ssm.group_count') * state) * 4;
    stateMiB = (S + R) / MiB;
  } else if (g('shortconv.l_cache')) {
    const nConv = a.nLayer - a.full.layers - a.swa.layers;
    stateMiB = (nConv * g('shortconv.l_cache') * a.nEmbd * 4) / MiB;
  }
  // MTP block attention (the draft context caches it at the target's KV type)
  const nextn = { layers: 0, kvHeads: 0, keyLen: 0, valueLen: 0 };
  for (let l = a.nLayer - a.nextn; l < a.nLayer; l++) {
    const k = byName.get(`blk.${l}.attn_k.weight`);
    if (!k) continue;
    const v = byName.get(`blk.${l}.attn_v.weight`);
    nextn.layers += 1;
    nextn.kvHeads = a.full.kvHeads;
    nextn.keyLen = (k.dims[1] ?? 0) / a.full.kvHeads;
    nextn.valueLen = ((v ?? k).dims[1] ?? 0) / a.full.kvHeads;
  }
  const bpw = (t: typeof out): number => {
    const b = t ? tensorBytes(t) : null;
    return t && b ? (8 * b) / t.dims.reduce((x, d) => x * d, 1) : 4.5;
  };
  const mtpExtraMiB = nextn.layers > 0 && a.arch.startsWith('qwen35') ? mtpExtra(a.nEmbd, bpw(out ?? emb), bpw(emb)) : 0;
  return {
    ctxMax: a.ctxTrain,
    arch: {
      source: `gguf:${file}`, arch: a.arch, nLayer: a.nLayer - a.nextn, nEmbd: a.nEmbd, nVocab: a.nVocab,
      tiedEmbd: !out, full: a.full, swa: a.swa, nextn, stateMiB: round(stateMiB, 2), mtpExtraMiB: round(mtpExtraMiB, 1),
    },
  };
}

function archFromConfig(cfgRoot: Json, m: CatalogModel): { arch: ModelArch; ctxMax: number } {
  const c = Object.keys(obj(cfgRoot.text_config)).length ? obj(cfgRoot.text_config) : cfgRoot;
  const where = m.configRepo;
  const types = Array.isArray(c.layer_types) ? c.layer_types.map(String) : [];
  const count = (t: string): number => types.filter((x) => x === t).length;
  const nLayer = need(c, 'num_hidden_layers', where);
  const nEmbd = need(c, 'hidden_size', where);
  const nHead = need(c, 'num_attention_heads', where);
  const headDim = numOf(c.head_dim) ?? nEmbd / nHead;
  const kvh = need(c, 'num_key_value_heads', where);
  const tiedEmbd = c.tie_word_embeddings === true || cfgRoot.tie_word_embeddings === true;
  const empty = { layers: 0, kvHeads: 0, keyLen: 0, valueLen: 0 };
  let full = { ...empty }, swa = { ...empty, window: 0 }, stateMiB = 0, nextn = { ...empty }, archName: string;
  const modelType = String(c.model_type ?? cfgRoot.model_type ?? '');
  if (count('linear_attention') > 0) { // Qwen3.5/3.6/3.8: GDN + full attention
    archName = modelType.includes('moe') ? 'qwen35moe' : 'qwen35';
    full = { layers: count('full_attention'), kvHeads: kvh, keyLen: headDim, valueLen: headDim };
    const nRec = count('linear_attention');
    const vh = need(c, 'linear_num_value_heads', where), kd = need(c, 'linear_key_head_dim', where);
    const vd = need(c, 'linear_value_head_dim', where), kh = need(c, 'linear_num_key_heads', where);
    const conv = numOf(c.linear_conv_kernel_dim) ?? 4;
    stateMiB = (nRec * vh * kd * vd * 4 + nRec * (conv - 1) * (vh * vd + 2 * kh * kd) * 4) / MiB;
    if (m.mtpInFile) nextn = { layers: numOf(c.mtp_num_hidden_layers) ?? 1, kvHeads: kvh, keyLen: headDim, valueLen: headDim };
  } else if (count('conv') > 0) { // LFM2: shortconv + GQA
    archName = modelType.includes('moe') ? 'lfm2moe' : 'lfm2';
    full = { layers: count('full_attention'), kvHeads: kvh, keyLen: headDim, valueLen: headDim };
    stateMiB = (count('conv') * (numOf(c.conv_L_cache) ?? 3) * nEmbd * 4) / MiB;
  } else if (count('sliding_attention') > 0) { // Gemma 4 (global layers: own head count/dim, V = K still cached), gpt-oss
    archName = modelType.startsWith('gemma') ? 'gemma4' : modelType === 'gpt_oss' ? 'gpt-oss' : modelType;
    const gHeads = numOf(c.num_global_key_value_heads) ?? kvh;
    const gDim = numOf(c.global_head_dim) ?? headDim;
    full = { layers: count('full_attention'), kvHeads: gHeads, keyLen: gDim, valueLen: gDim };
    swa = { layers: count('sliding_attention'), kvHeads: kvh, keyLen: headDim, valueLen: headDim, window: need(c, 'sliding_window', where) };
  } else {
    archName = modelType;
    full = { layers: nLayer, kvHeads: kvh, keyLen: headDim, valueLen: headDim };
  }
  const mtpExtraMiB = nextn.layers > 0 && archName.startsWith('qwen35') ? mtpExtra(nEmbd, 6.5625, 4.5) : 0;
  return {
    ctxMax: need(c, 'max_position_embeddings', where),
    arch: {
      source: `config:${m.configRepo}`, arch: archName, nLayer, nEmbd, nVocab: need(c, 'vocab_size', where), tiedEmbd,
      full, swa, nextn, stateMiB: round(stateMiB, 2), mtpExtraMiB: round(mtpExtraMiB, 1),
    },
  };
}

const round = (v: number, d: number): number => Math.round(v * 10 ** d) / 10 ** d;

function bTok(m: CatalogModel, q: QuantFile): number {
  const gpuBytes = q.sizeBytes - q.hostEmbdBytes;
  return round((m.kind === 'moe' ? (q.sizeBytes * m.activeB) / m.paramsB : gpuBytes) / 1e9, 2);
}

async function refreshModel(m: CatalogModel, local: Map<string, string>): Promise<string[]> {
  const notes: string[] = [];
  for (const q of m.quants) {
    const e = (await tree(q.repo)).get(q.path);
    if (!e) throw new Error(`${m.id}: ${q.repo}/${q.path} not in the HF tree`);
    const sha = e.lfs?.oid ?? '';
    if (q.sizeBytes !== e.size || q.sha256 !== sha) notes.push(`${m.id} ${q.quant}: size ${q.sizeBytes} → ${e.size}, sha ${q.sha256.slice(0, 8)} → ${sha.slice(0, 8)}`);
    q.sizeBytes = e.size;
    q.sha256 = sha;
  }
  const localHit = m.quants.map((q) => ({ q, p: local.get(q.path.split('/').pop() ?? '') })).find((x) => x.p);
  let derived: { arch: ModelArch; ctxMax: number };
  const headers = new Map<string, GgufHeader>();
  if (localHit?.p) {
    const h = await readGgufHeader(localHit.p);
    headers.set(localHit.q.quant, h);
    derived = archFromGguf(h, localHit.q.path.split('/').pop() ?? localHit.q.path);
  } else {
    derived = archFromConfig(obj(await hfJson(`${HF}/${m.configRepo}/resolve/main/config.json`)), m);
  }
  if (JSON.stringify(derived.arch) !== JSON.stringify(m.arch)) notes.push(`${m.id}: arch updated from ${derived.arch.source}`);
  if (derived.ctxMax !== m.ctxMax) notes.push(`${m.id}: ctxMax ${m.ctxMax} → ${derived.ctxMax}`);
  m.arch = derived.arch;
  m.ctxMax = derived.ctxMax;
  for (const q of m.quants) {
    const h = headers.get(q.quant);
    const emb = h?.tensors.find((t) => t.name === 'token_embd.weight');
    if (m.arch.tiedEmbd) q.hostEmbdBytes = 0;
    else if (emb) q.hostEmbdBytes = tensorBytes(emb) ?? 0;
    else q.hostEmbdBytes = Math.round((m.arch.nVocab * m.arch.nEmbd * embdBpw(q.quant)) / 8);
    q.bTokGB = bTok(m, q);
  }
  return notes;
}

if (import.meta.main) {
  const check = process.argv.includes('--check');
  const catalog = (await Bun.file(CATALOG_PATH).json()) as Catalog;
  const local = localGgufs(process.env.ENIGMA_MODELS_DIR);
  const notes: string[] = [];
  for (const m of catalog.models) notes.push(...(await refreshModel(m, local)));
  catalog._meta.refreshed = new Date().toISOString().slice(0, 10);
  for (const n of notes) console.log(n);
  if (!check) {
    await Bun.write(CATALOG_PATH, JSON.stringify(catalog, null, 1) + '\n');
    console.log(`wrote ${CATALOG_PATH} (${catalog.models.length} models, ${notes.length} changes)`);
  }
}
