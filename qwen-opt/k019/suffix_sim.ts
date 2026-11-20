// K-019: cross-session suffix cache (SuffixDecoding style) vs our in-session lookup tail, CPU simulation.
//
// Corpus: omp agent sessions (~/.omp/agent/sessions/**/*.jsonl, chronological by file name), rendered like
// product/research/15b-sim/extract_agent.py (Qwen chat format, tool calls as Qwen XML, thinking excluded, compaction
// restarts the stream). Tokenizer: Qwen3 tokenizer.json (argv[2]). Only aggregate numbers are printed.
//
// Per assistant-output position p (truth S[p..b)), three draft sources propose a continuation; r = how many of its
// first <= 15 tokens equal the truth, m = backward suffix match length (<= 12):
//   LOCAL : server lookup tail: 4-gram matches in the current stream before p, <= 64 most recent, longest suffix
//           then most recent (as product/research/21c-cplm/oracle.py BASE)
//   CROSS : the same over the outputs of all EARLIER epochs/sessions (the suffix cache; outputs only, like SuffixDecoding)
//   UNION : LOCAL when it fires, else CROSS
// Step model (oracle.py, coupled tail rule): MTP n=4 accepts k drafts with cumulative 0.779/0.565/0.404/0.293
// (common random numbers); the tail fires when m >= 6, k == 4 and r > 4, then the step advances 1 + r and costs
// T5 + TW16, else 1 + k at T5.
// Run: bun suffix_sim.ts <sessions dir> <tokenizer.json>   (needs @huggingface/tokenizers next to the script)
import { Tokenizer } from '@huggingface/tokenizers';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const [root, tokPath] = process.argv.slice(2);
const tok = new Tokenizer(JSON.parse(readFileSync(tokPath!, 'utf8')), {});
const enc = (s: string): number[] => (s ? Array.from(tok.encode(s).ids as ArrayLike<number>) : []);

const NMAX = 12, CAND = 64, KMAX = 15, MMIN = 6;
const CUM = [0.779, 0.565, 0.404, 0.293];
const T5 = 28.74, TW16 = 6.40;

function walk(d: string, out: string[]): string[] {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walk(p, out); else if (n.endsWith('.jsonl')) out.push(p);
  }
  return out;
}

function renderCall(name: string, args: unknown): string {
  const a: Record<string, unknown> = args && typeof args === 'object' ? args as Record<string, unknown> : { input: typeof args === 'string' ? args : JSON.stringify(args) };
  let s = `<tool_call>\n<function=${name}>\n`;
  for (const [k, v] of Object.entries(a)) s += `<parameter=${k}>\n${typeof v === 'string' ? v : JSON.stringify(v)}\n</parameter>\n`;
  return s + '</function>\n</tool_call>';
}
const cls = (name: string, args: any): string =>
  name === 'edit' ? (args && 'old_string' in args ? 'edit-strrep' : 'edit-hashline') : name === 'write' ? 'write' : name === 'bash' ? 'bash' : 'call-other';
const texts = (c: any): string => (Array.isArray(c) ? c : [{ type: 'text', text: c }]).filter((x: any) => x?.type === 'text').map((x: any) => x.text ?? '').join('');

type Piece = [string, string | null];
function* epochs(path: string): Generator<Piece[]> {
  let ep: Piece[] = [];
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    let d: any; try { d = JSON.parse(line); } catch { continue; }
    if (d.type === 'compaction') { if (ep.length) yield ep; ep = [[`<|im_start|>user\n${d.summary ?? ''}<|im_end|>\n`, null]]; continue; }
    const m = d.message; if (!m || typeof m !== 'object') continue;
    const c = typeof m.content === 'string' ? [{ type: 'text', text: m.content }] : m.content;
    if (!Array.isArray(c)) continue;
    if (m.role === 'user' || m.role === 'developer') ep.push([`<|im_start|>user\n${texts(c)}<|im_end|>\n`, null]);
    else if (m.role === 'assistant') {
      ep.push(['<|im_start|>assistant\n', null]);
      for (const x of c) {
        if (x.type === 'text' && x.text) ep.push([x.text + '\n', 'assistant-text']);
        else if (x.type === 'toolCall') ep.push([renderCall(x.name, x.arguments), cls(x.name, x.arguments)]);
      }
      ep.push(['<|im_end|>\n', null]);
    } else if (m.role === 'toolResult') ep.push([`<|im_start|>user\n<tool_response>\n${texts(c)}\n</tool_response><|im_end|>\n`, null]);
  }
  if (ep.length) yield ep;
}

// 4-gram index: hash -> ascending end positions (collisions harmless: candidates are verified token by token)
const h4 = (a: ArrayLike<number>, e: number): number => (((a[e - 3]! * 0x9e3779b1) ^ (a[e - 2]! * 0x85ebca6b) ^ (a[e - 1]! * 0xc2b2ae35) ^ a[e]!) >>> 0);
class Index {
  m = new Map<number, number[]>();
  add(a: ArrayLike<number>, e: number) { const k = h4(a, e); const l = this.m.get(k); if (l) l.push(e); else this.m.set(k, [e]); }
  // <= CAND most recent ends < lim, most recent first
  recent(k: number, lim: number): number[] {
    const l = this.m.get(k); if (!l) return [];
    let lo = 0, hi = l.length; while (lo < hi) { const md = (lo + hi) >> 1; if (l[md]! < lim) lo = md + 1; else hi = md; }
    return l.slice(Math.max(0, lo - CAND), lo).reverse();
  }
}

// best (m, r) over candidates: longest suffix, then most recent; S = current stream, src = candidate array (-1 = separator)
function best(src: ArrayLike<number>, cands: number[], S: number[], p: number, b: number, srcEnd: number): [number, number] {
  let bm = 0, br = 0;
  for (const e of cands) {
    let ml = 0; while (ml < NMAX && e - ml >= 0 && p - 1 - ml >= 0 && src[e - ml] === S[p - 1 - ml]) ml++;
    if (ml <= bm) continue;
    const vv = Math.min(KMAX, srcEnd - 1 - e);
    let r = 0; while (r < vv && p + r < b && src[e + 1 + r] === S[p + r]) r++;
    bm = ml; br = r;
  }
  return [bm, br];
}

let seed = 1;
const rnd = (): number => { seed = (seed + 0x6d2b79f5) | 0; let t = seed; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

const G: number[] = []; // outputs of earlier epochs, -1 between segments
const gIdx = new Index();
const POL = ['LOCAL', 'CROSS', 'UNION'];
const agg = new Map<string, number[]>(); // class -> [tokens, steps x3, ms x3, cross-fires, local-fires]
const files = walk(root!, []).sort();
let nEp = 0;
for (const f of files) {
  for (const ep of epochs(f)) {
    const S: number[] = []; const segs: [number, number, string][] = [];
    for (const [t, c] of ep) { const ids = enc(t); if (c && ids.length) segs.push([S.length, S.length + ids.length, c]); for (const x of ids) S.push(x); }
    if (!segs.length) continue;
    nEp++;
    const lIdx = new Index(); let indexed = 3;
    for (const [a, b, c] of segs) {
      while (indexed < a) lIdx.add(S, indexed++);
      const L = b - a; const rows = [new Int8Array(L), new Int8Array(L), new Int8Array(L)];
      for (let i = 0; i < L; i++) {
        const p = a + i;
        while (indexed < p) lIdx.add(S, indexed++); // history = S[..p)
        if (p < 4) continue;
        const k = h4(S, p - 1);
        const [ml, rl] = best(S, lIdx.recent(k, p - 1), S, p, b, p);
        const [mc, rc] = best(G, gIdx.recent(k, G.length), S, p, b, G.length);
        const lr = ml >= MMIN ? rl : 0, cr = mc >= MMIN ? rc : 0;
        rows[0]![i] = lr; rows[1]![i] = cr; rows[2]![i] = lr > 4 ? lr : cr;
      }
      const u = Array.from({ length: L }, rnd);
      const v = agg.get(c) ?? new Array(9).fill(0); v[0] += L;
      for (let pol = 0; pol < 3; pol++) {
        let p = 0, st = 0, ms = 0, fires = 0;
        while (p < L) {
          const kk = CUM.filter((x) => u[p]! < x).length; const r = rows[pol]![p]!;
          const use = kk === 4 && r > 4; p += 1 + (use ? r : kk); st++; ms += T5 + (use ? TW16 : 0); fires += use ? 1 : 0;
        }
        v[1 + pol] += st; v[4 + pol] += ms; if (pol === 1) v[7] += fires; if (pol === 0) v[8] += fires;
      }
      agg.set(c, v);
    }
    for (const [a, b] of segs) { for (let i = a; i < b; i++) { G.push(S[i]!); if (G.length - (i - a) > 4 && i - a >= 3) gIdx.add(G, G.length - 1); } G.push(-1); }
  }
  process.stderr.write(`${files.indexOf(f) + 1}/${files.length} epochs ${nEp} cache ${G.length}\n`);
}

const fmt = (name: string, v: number[]) => {
  const tps = [0, 1, 2].map((j) => 1000 * v[0]! / v[4 + j]!);
  console.log(`${name.padEnd(22)} ${String(v[0]).padStart(9)} ${[0, 1, 2].map((j) => (v[0]! / v[1 + j]!).toFixed(3)).join(' ')} | ${tps.map((x) => x.toFixed(1)).join(' ')} | CROSS ${(100 * (tps[1]! / tps[0]! - 1)).toFixed(1)}% UNION ${(100 * (tps[2]! / tps[0]! - 1)).toFixed(1)}% | fires local ${v[8]} cross ${v[7]}`);
};
console.log(`epochs ${nEp}, suffix cache ${G.length} tokens; class tokens tok/step ${POL.join(' ')} | t/s (model) | vs LOCAL`);
const tot = new Array(9).fill(0);
for (const [k, v] of [...agg].sort()) { fmt(k, v); v.forEach((x, i) => (tot[i] += x)); }
fmt('ALL', tot);
