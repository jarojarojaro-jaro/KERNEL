/**
 * Build step: turns the consolidated NVIDIA benchmark sheet into `src/lib/data/cards.json`.
 *
 * Source of truth: KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md (tables copied from the
 * campaign reports, raw data in ~/qwen-opt/cloud/results/<card>-20261016/). Every number keeps
 * the file:line it was read from. The parser is deliberately strict: each section, column and
 * row is named below, and a missing or reshaped table fails the build instead of guessing.
 *
 * Cross-check: each decode median is compared with the matching cloud scorecard.json row;
 * a disagreement beyond the sheet's rounding is recorded in `checks` (shown on the methodology
 * page) and printed, never silently "fixed".
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
import type { CardHw, CardsFile, ModelKey, Num, NvidiaCard, Run, Variant, VariantKey } from '../src/lib/data/card-types';

const REL = 'KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md';

const CARDS: {
	id: string;
	heading: string;
	scorecard: string;
	sections: { model: ModelKey; heading: string; cols: VariantKey[]; before: VariantKey; flags: VariantKey; ours: VariantKey; quant: string; scorecardModel: RegExp; scorecardVariants: Partial<Record<VariantKey, string>>; ctxRow?: RegExp; gainRow: string }[];
}[] = [
	{
		id: 'rtx-3090',
		heading: '## RTX 3090',
		scorecard: '3090-20261016',
		sections: [
			{ model: 'qwen38', heading: '### Qwen3.8-27B UD-Q4_K_XL', cols: ['a0', 'a1', 'a2'], before: 'a0', flags: 'a1', ours: 'a2', quant: 'UD-Q4_K_XL', scorecardModel: /^qwen38/, scorecardVariants: { a0: 'A0', a1: 'A1', a2: 'A2' }, ctxRow: /^Qwen/, gainRow: '3090 Qwen' },
			{ model: 'lfm25', heading: '### LFM2.5-24B-A2B Q5_K_M', cols: ['a0', 'a1', 'profile'], before: 'a0', flags: 'a1', ours: 'profile', quant: 'Q5_K_M', scorecardModel: /^lfm25/, scorecardVariants: { a0: 'A0', a1: 'A1', profile: 'A2p-t' }, ctxRow: /^LFM/, gainRow: '3090 LFM' }
		]
	},
	{
		id: 'rtx-5060-ti-16',
		heading: '## RTX 5060 Ti',
		scorecard: '5060ti-20261016',
		sections: [
			{ model: 'qwen38', heading: '### Qwen3.8-27B UD-Q3_K_XL', cols: ['a0', 'a1', 'a2', 'profile'], before: 'a0', flags: 'a1', ours: 'profile', quant: 'UD-Q3_K_XL', scorecardModel: /^qwen38/, scorecardVariants: { a0: 'A0', a1: 'A1', a2: 'A2', profile: 'nasz profil' }, ctxRow: /^Qwen/, gainRow: '5060 Ti Qwen' },
			{ model: 'lfm25', heading: '### LFM2.5-24B-A2B Q4_K_M', cols: ['a0', 'a1', 'a2', 'profile'], before: 'a0', flags: 'a1', ours: 'profile', quant: 'Q4_K_M', scorecardModel: /^lfm25/, scorecardVariants: { a0: 'A0', a1: 'A1', a2: 'A2', profile: 'nasz profil' }, ctxRow: /^LFM/, gainRow: '5060 Ti LFM' }
		]
	},
	{
		id: 'rtx-3060-12',
		heading: '## RTX 3060',
		scorecard: '3060-20261016',
		sections: [
			{ model: 'saluki', heading: '### Underdog Saluki', cols: ['a0', 'a1', 'ours'], before: 'a0', flags: 'a1', ours: 'ours', quant: 'IQ2-mix', scorecardModel: /^Underdog Saluki/, scorecardVariants: { a0: 'A0', a1: 'A1', ours: 'A2t' }, gainRow: '3060 Saluki' },
			{ model: 'bonsai', heading: '### Ternary Bonsai', cols: ['a0', 'alt', 'a1', 'ours'], before: 'a0', flags: 'a1', ours: 'ours', quant: 'Q2_0 (PQ2_0 repack)', scorecardModel: /^Ternary Bonsai/, scorecardVariants: { a0: 'A0', alt: 'A1', a1: 'A1q', ours: 'A2t' }, gainRow: '3060 Bonsai' }
		]
	}
];

/** Row label (start of the first cell) → field(s). */
const ROWS: [RegExp, (keyof Variant)[]][] = [
	[/^decode t\/s/, ['decode']],
	[/^ms na (krok|token)/, ['msStep']],
	[/^tokeny na krok/, ['tokStep']],
	[/^prefill pp512 \/ pp4096/, ['pp512', 'pp4096']],
	[/^prefill pp4096/, ['pp4096']],
	[/^TTFT/, ['ttft']],
	[/^odpowiedź 500 słów EN \/ PL/, ['words500en', 'words500pl']],
	[/^500 słów EN$/, ['words500en']],
	[/^500 słów PL$/, ['words500pl']],
	[/^VRAM/, ['vram']],
	[/^tg128/, ['tg128']],
	[/^perplexity/, ['ppl']],
	[/^tg przy 8k \/ 32k/, ['tg8k', 'tg32k']]
];

const cells = (line: string) =>
	line
		.trim()
		.replace(/^\||\|$/g, '')
		.split('|')
		.map((c) => c.trim());

/**
 * Parse one table cell into numbers: plain values in order. A range "[lo–hi]" or "(lo–hi)" and an
 * Ollama comparison "(Ollama 39.0)" attach to the first value; other parentheses are ignored.
 */
function parseCell(cell: string, src: string): Num[] {
	if (!cell || /^—$/.test(cell)) return [];
	const range = cell.match(/[[(]([\d.]+)[–-]([\d.]+)[\])]/);
	const ollama = cell.match(/\(Ollama ([\d.]+)/);
	const unit = cell.match(/\b(GiB|GB|s)\b/)?.[1];
	const body = cell.replace(/\[[^\]]*\]/g, ' ').replace(/\([^)]*\)/g, ' ').replace(/\*\*/g, '');
	const vals = [...body.matchAll(/(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])/g)].map((m) => Number(m[1]));
	const out: Num[] = vals.map((v) => ({ v, src, ...(unit ? { unit } : {}) }));
	if (out[0] && range) Object.assign(out[0], { lo: Number(range[1]), hi: Number(range[2]) });
	if (out[0] && ollama) out[0].paren = Number(ollama[1]);
	return out;
}

/** Variant columns of one benchmark table (header at `header`, rows in `rows`). */
function parseVariantTable(lines: string[], src: (i: number) => string, t: { header: number; rows: readonly [number, number] }, cols: VariantKey[], label: string): Variant[] {
	const head = cells(lines[t.header]);
	if (head.length !== cols.length + 1) fail(`${label}: expected ${cols.length} columns, got ${head.length - 1} (${head.join(' | ')})`);
	const variants: Variant[] = cols.map((key) => ({ key }));
	for (let r = t.rows[0]; r < t.rows[1]; r++) {
		const c = cells(lines[r]);
		const rule = ROWS.find(([re]) => re.test(c[0]));
		if (!rule) continue;
		cols.forEach((_, k) => {
			const cell = c[k + 1] ?? '';
			// Multi-value rows ("1410 / 1396", "— / 581") are positional: split first, so a dash keeps its slot.
			const parts = rule[1].length > 1 ? cell.split(' / ') : [cell];
			rule[1].forEach((field, j) => {
				const n = parseCell(parts[j] ?? '', src(r))[0];
				if (n) (variants[k] as unknown as Record<string, Num>)[field] = n;
			});
		});
	}
	return variants;
}

function tableAt(lines: string[], i: number) {
	let start = i + 1;
	while (start < lines.length && !lines[start].startsWith('|')) start++;
	let end = start;
	while (end < lines.length && lines[end].startsWith('|')) end++;
	return { header: start, rows: [start + 2, end] as const };
}

/**
 * Runs that are not in the consolidated sheet yet, read from their campaign report's
 * "Karta wyniku dla aplikacji" table (same spec_sweep method as the sheet) and cross-checked
 * against the scorecard. When the sheet gains the model, move it into CARDS above.
 */
const REPORT_RUNS: {
	card: string;
	file: string;
	model: ModelKey;
	heading: string;
	cols: VariantKey[];
	before: VariantKey;
	flags: VariantKey;
	ours: VariantKey;
	quant: string;
	scorecard: string;
	scorecardModel: RegExp;
	scorecardVariants: Partial<Record<VariantKey, string>>;
	/** Long-context table: heading, upstream row, ours row (llama-bench, report section). */
	ctx?: { heading: string; up: RegExp; ours: RegExp; kv: string };
}[] = [
	{
		card: 'rtx-3090',
		file: 'KERNEL/product/research/14-nemotron-3090.md',
		model: 'nemotron',
		heading: '### Nemotron 3.5 Bolt 74B-A9B IQ2_XXS (RTX 3090)',
		cols: ['a0', 'a1', 'ours'],
		before: 'a0',
		flags: 'a1',
		ours: 'ours',
		quant: 'IQ2_XXS',
		scorecard: 'nemotron-3090-20261016',
		scorecardModel: /^nemotron/,
		scorecardVariants: { a0: 'A0', a1: 'A1', ours: 'tuned' },
		ctx: { heading: '## 6. Długi kontekst', up: /^upstream KV q8_0/, ours: /^tuned KV q8_0/, kv: 'KV q8_0' }
	}
];

function buildReportRun(cfg: (typeof REPORT_RUNS)[number], resultsDir: string, checks: CardsFile['checks']): Run | null {
	const path = join(homedir(), cfg.file);
	if (!existsSync(path)) return null;
	const lines = readFileSync(path, 'utf8').split('\n');
	const src = (i: number) => `${cfg.file}:${i + 1}`;
	const si = lines.findIndex((l) => l.startsWith(cfg.heading));
	if (si < 0) fail(`missing ${cfg.heading} in ${cfg.file}`);
	const variants = parseVariantTable(lines, src, tableAt(lines, si), cfg.cols, cfg.heading);
	const fileI = lines.findIndex((l) => /^- Plik: .*\.gguf`, ([\d ]+) B/.test(l));
	const bytes = fileI >= 0 ? Number(lines[fileI].match(/, ([\d ]+) B/)![1].replace(/ /g, '')) : null;
	const run: Run = {
		model: cfg.model,
		title: cfg.heading.replace(/^### /, '').replace(/ \(.*\)$/, ''),
		quant: cfg.quant,
		src: src(si),
		variants,
		before: cfg.before,
		flags: cfg.flags,
		ours: cfg.ours,
		...(bytes ? { file: { v: Math.round(bytes / 1e7) / 100, src: src(fileI), unit: 'GB' } } : {})
	};
	// Gain split: "- A0 → nasz: **×1.62**." and "- Rozkład A0 → nasz: flagi (DFlash) ×1.51, łatki ×1.07."
	const totI = lines.findIndex((l, i) => i > si && /^- A0 → nasz: \*\*×[\d.]+\*\*/.test(l));
	const splitI = lines.findIndex((l, i) => i > si && /^- Rozkład A0 → nasz:/.test(l));
	if (totI > 0 && splitI > 0) {
		const total = Number(lines[totI].match(/×(\d+(?:\.\d+)?)/)![1]);
		const m = lines[splitI].match(/flagi( \([^)]*\))? ×(\d+(?:\.\d+)?), łatki ×(\d+(?:\.\d+)?)/);
		if (m)
			run.gain = {
				flags: { v: Number(m[2]), src: src(splitI) },
				engine: { v: Number(m[3]), src: src(splitI) },
				total: { v: total, src: src(totI) },
				text: [`×${m[2]}${m[1] ?? ''}`, `×${m[3]} (łatki)`, `×${total}`],
				src: src(splitI)
			};
	}
	if (cfg.ctx) {
		const ci = lines.findIndex((l) => l.startsWith(cfg.ctx!.heading));
		if (ci >= 0) {
			const t = tableAt(lines, ci);
			const depths = cells(lines[t.header]).slice(1).map((d) => (/k$/.test(d) ? Number(d.slice(0, -1)) * 1024 : Number(d.replace(/^d/, ''))));
			let up: Num[] | null = null;
			let ours: Num[] | null = null;
			for (let r = t.rows[0]; r < t.rows[1]; r++) {
				const c = cells(lines[r]);
				const vals = c.slice(1).map((x) => parseCell(x, src(r))[0]);
				if (cfg.ctx.up.test(c[0])) up = vals;
				if (cfg.ctx.ours.test(c[0])) ours = vals;
			}
			if (up && ours) run.longCtx = { depths, up, ours, kv: cfg.ctx.kv };
		}
	}
	const scFile = join(resultsDir, cfg.scorecard, 'scorecard.json');
	if (existsSync(scFile)) {
		const sc = JSON.parse(readFileSync(scFile, 'utf8')) as Record<string, unknown>[];
		for (const v of variants) {
			const want = cfg.scorecardVariants[v.key];
			const row = want && v.decode ? sc.find((x) => cfg.scorecardModel.test(String(x.model)) && String(x.variant) === want) : null;
			if (!row || !v.decode) continue;
			const scv = Number(row.decode_tps_median);
			v.scorecard = { file: `qwen-opt/cloud/results/${cfg.scorecard}/scorecard.json`, variant: String(row.variant), decode: scv };
			const digits = (String(v.decode.v).split('.')[1] ?? '').length;
			if (Math.abs(scv - v.decode.v) > 0.5 * 10 ** -digits + 1e-9) checks.push({ card: cfg.card, model: cfg.model, variant: v.key, sheet: v.decode.v, scorecard: scv, file: v.scorecard.file });
		}
	}
	return run;
}

function fail(msg: string): never {
	throw new Error(`cards.ts: ${msg}`);
}

export function buildCards(sheetPath: string, resultsDir: string): CardsFile {
	const lines = readFileSync(sheetPath, 'utf8').split('\n');
	const src = (i: number) => `${REL}:${i + 1}`;
	const find = (pred: (l: string) => boolean, from = 0, to = lines.length) => {
		for (let i = from; i < to; i++) if (pred(lines[i])) return i;
		return -1;
	};
	const tableAfter = (i: number) => tableAt(lines, i);
	const checks: { card: string; model: string; variant: string; sheet: number; scorecard: number; file: string }[] = [];

	const gainHead = find((l) => l.startsWith('## Skąd zysk'));
	if (gainHead < 0) fail('missing "## Skąd zysk"');
	const gainTable = tableAfter(gainHead);

	const out: NvidiaCard[] = CARDS.map((card) => {
		const ci = find((l) => l.startsWith(card.heading));
		if (ci < 0) fail(`missing ${card.heading}`);
		const nextCard = find((l) => l.startsWith('## '), ci + 1);
		const hwI = find((l) => l.startsWith('- **Sprzęt:**'), ci, nextCard);
		if (hwI < 0) fail(`missing hardware line for ${card.id}`);
		const hwLine = lines[hwI].replace('- **Sprzęt:** ', '');
		const power = hwLine.match(/(\d+) W/);
		const bw = hwLine.match(/(\d+) GB\/s/);
		const pcie = hwLine.match(/PCIe (gen\d x\d+)/);
		if (!power || !bw || !pcie) fail(`hardware line for ${card.id} is missing power/bandwidth/PCIe`);
		const hw: CardHw = { powerW: { v: Number(power[1]), src: src(hwI) }, bwGBs: { v: Number(bw[1]), src: src(hwI) }, pcie: pcie[1], line: hwLine, src: src(hwI) };

		let sc: Record<string, unknown>[] = [];
		const scFile = join(resultsDir, card.scorecard, 'scorecard.json');
		if (existsSync(scFile)) sc = JSON.parse(readFileSync(scFile, 'utf8'));

		const ctxI = find((l) => l.startsWith('### Długi kontekst'), ci, nextCard);
		const profI = find((l) => l.startsWith('### Profil kroku'), ci, nextCard);

		const runs: Run[] = card.sections.map((s) => {
			const si = find((l) => l.startsWith(s.heading), ci, nextCard);
			if (si < 0) fail(`missing ${s.heading} under ${card.heading}`);
			const variants = parseVariantTable(lines, src, tableAfter(si), s.cols, s.heading);
			const fileM = lines[si].match(/\(([\d.]+) GB/);
			const run: Run = {
				model: s.model,
				title: lines[si].replace(/^### /, ''),
				quant: s.quant,
				src: src(si),
				variants,
				before: s.before,
				flags: s.flags,
				ours: s.ours,
				...(fileM ? { file: { v: Number(fileM[1]), src: src(si), unit: 'GB' } } : {})
			};
			for (const v of variants) {
				const want = s.scorecardVariants[v.key];
				if (!want || !v.decode) continue;
				const row = sc.find((x) => s.scorecardModel.test(String(x.model)) && String(x.variant).startsWith(want));
				if (!row) continue;
				const scv = Number(row.decode_tps_median);
				v.scorecard = { file: `qwen-opt/cloud/results/${card.scorecard}/scorecard.json`, variant: String(row.variant), decode: scv };
				const digits = (String(v.decode.v).split('.')[1] ?? '').length;
				if (Math.abs(scv - v.decode.v) > 0.5 * 10 ** -digits + 1e-9) checks.push({ card: card.id, model: s.model, variant: v.key, sheet: v.decode.v, scorecard: scv, file: v.scorecard.file });
			}
			if (ctxI > 0 && s.ctxRow) {
				const ct = tableAfter(ctxI);
				const depths = cells(lines[ct.header]).slice(1).map((d) => (d.endsWith('k') ? Number(d.slice(0, -1)) * 1024 : Number(d)));
				const kv = lines[ctxI].match(/KV q\d_0/)?.[0] ?? '';
				for (let r = ct.rows[0]; r < ct.rows[1]; r++) {
					const c = cells(lines[r]);
					if (!s.ctxRow.test(c[0])) continue;
					const pairs = c.slice(1).map((x) => parseCell(x, src(r)));
					if (pairs.some((p) => p.length !== 2)) fail(`long-context row "${c[0]}" is not upstream / ours`);
					run.longCtx = { depths, up: pairs.map((p) => p[0]), ours: pairs.map((p) => p[1]), kv: c[0].match(/KV q\d_0/)?.[0] ?? kv };
				}
			}
			if (profI > 0) {
				const pt = tableAfter(profI);
				for (let r = pt.rows[0]; r < pt.rows[1]; r++) {
					const c = cells(lines[r]);
					if (!c[0].toLowerCase().startsWith(s.model === 'qwen38' ? 'qwen' : 'lfm')) continue;
					const k = parseCell(c[1].replace('→', ' '), src(r));
					const g = parseCell(c[2].replace('→', ' '), src(r));
					const p = parseCell(c[3].replace('→', ' '), src(r));
					run.kernels = { up: k[0], ours: k[1], gpuMs: [g[0], g[1]], gapMs: [p[0], p[1]] };
				}
			}
			for (let r = gainTable.rows[0]; r < gainTable.rows[1]; r++) {
				const c = cells(lines[r]);
				if (c[0] !== s.gainRow) continue;
				const x = (cell: string): Num | null => {
					const m = cell.replace(/\*\*/g, '').match(/^×([\d.]+)/);
					return m ? { v: Number(m[1]), src: src(r) } : null;
				};
				run.gain = { flags: x(c[1]), engine: x(c[2]), total: x(c[3]), text: [c[1], c[2], c[3].replace(/\*\*/g, '')], src: src(r) };
			}
			return run;
		});
		return { id: card.id, heading: lines[ci].replace(/^## /, ''), src: src(ci), scorecard: card.scorecard, hw, runs };
	});

	// Correctness facts (line-cited): KLD vs upstream noise on the 3060, test-backend-ops.
	const kldI = find((l) => /KLD nasz vs upstream na 3060/.test(l));
	const kld = lines[kldI]?.match(/Saluki ([\d.]+), Bonsai ([\d.]+)\).*?\(([\d.]+) \/ ([\d.]+)\)/);
	if (!kld) fail('KLD line not found');
	const quality = {
		saluki: { ours: { v: Number(kld[1]), src: src(kldI) }, noise: { v: Number(kld[3]), src: src(kldI) } },
		bonsai: { ours: { v: Number(kld[2]), src: src(kldI) }, noise: { v: Number(kld[4]), src: src(kldI) } }
	};
	const md5I = find((l) => l.includes('Greedy md5 nasz ≠ upstream'));
	const tboI = find((l) => l.trim().startsWith('- 3090: 19253/19253'));
	const tbo5I = find((l) => l.trim().startsWith('- 5060 Ti: 19251/19253'));

	// Other LFM formats on the 5060 Ti.
	const fmtI = find((l) => l.startsWith('### Inne formaty LFM'));
	const fmt = tableAfter(fmtI);
	const lfmFormats: CardsFile['lfmFormats5060'] = [];
	for (let r = fmt.rows[0]; r < fmt.rows[1]; r++) {
		const c = cells(lines[r]);
		const sp = c[2].replace(/\*\*/g, '').split(c[2].includes('→') ? '→' : ' / ').map((x) => parseCell(x.replace(/\(.*\)/, ''), src(r))[0] ?? null);
		lfmFormats.push({ file: c[0], gb: parseCell(c[1], src(r))[0], up: sp[0] ?? null, ours: sp[1] ?? null, kld: parseCell(c[3], src(r))[0], md5Same: c[4] === 'identyczne' ? true : c[4] === '—' ? null : false });
	}

	for (const cfg of REPORT_RUNS) {
		const run = buildReportRun(cfg, resultsDir, checks);
		const card = out.find((c) => c.id === cfg.card);
		if (run && card) card.runs.push(run);
	}

	const methodI = find((l) => l.startsWith('- **Generowanie (decode t/s):**'));
	return {
		source: REL,
		generated: 'scripts/cards.ts (bun scripts/sync-results.ts)',
		method: { decode: src(methodI) },
		correctness: { md5Diff: src(md5I), tbo3090: src(tboI), tbo5060: src(tbo5I), quality },
		lfmFormats5060: lfmFormats,
		checks,
		cards: out
	};
}
