/**
 * Build step (runs before `vite build`):
 * 1. Collects cloud scorecards from ~/qwen-opt/cloud/results/<card>-<date>/scorecard.json
 *    (written by runs/<card>/scorecard.py) into src/lib/data/cloud-results.json. Cards without a
 *    scorecard stay "in progress" on the site: no numbers are shown until a scorecard exists.
 * 3. Renders the TUI result screen (app/tui/tui_demo.py --snapshot, colourless) for the terminal page.
 * 2. Copies the scan scripts from app/scan/ into static/scan/ so the site serves the exact files
 *    that live in the repo (single source of truth).
 */
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';

const here = resolve(import.meta.dir, '..');
const resultsDir = process.env.CLOUD_RESULTS ?? join(homedir(), 'qwen-opt/cloud/results');

interface ScoreRow {
	model: string;
	card: string;
	variant: string;
	decode_tps_median: number | null;
	decode_tps_min: number | null;
	decode_tps_max: number | null;
	prefill_tps: number | null;
	ttft_ms_2k: number | null;
	vram_gb: number | null;
	md5_status: string;
	n_runs: number;
	rounds: number;
}

const cards: Record<string, { dir: string; rows: ScoreRow[] }> = {};
if (existsSync(resultsDir)) {
	for (const d of readdirSync(resultsDir, { withFileTypes: true })) {
		if (!d.isDirectory()) continue;
		const f = join(resultsDir, d.name, 'scorecard.json');
		if (!existsSync(f)) continue;
		const rows = JSON.parse(readFileSync(f, 'utf8')) as ScoreRow[];
		cards[d.name] = { dir: d.name, rows };
	}
}
writeFileSync(
	join(here, 'src/lib/data/cloud-results.json'),
	JSON.stringify({ source: '~/qwen-opt/cloud/results/*/scorecard.json', cards }, null, '\t') + '\n'
);
console.log(`cloud scorecards: ${Object.keys(cards).length ? Object.keys(cards).join(', ') : 'none yet'}`);

const scanSrc = resolve(here, '../scan');
const scanDst = join(here, 'static/scan');
mkdirSync(scanDst, { recursive: true });
for (const f of ['scan.sh', 'scan-macos.sh', 'scan.ps1']) {
	if (existsSync(join(scanSrc, f))) cpSync(join(scanSrc, f), join(scanDst, f));
	else console.warn(`missing scan script: ${f}`);
}

const tui = resolve(here, '../tui/tui_demo.py');
for (const lang of ['pl', 'en']) {
	const r = spawnSync('python3', [tui, '--snapshot', '--no-color', '--scene', 'result', '--cols', '92', '--rows', '24', '--lang', lang], { encoding: 'utf8' });
	if (r.status !== 0) {
		console.warn(`tui snapshot failed (${lang}): ${r.stderr}`);
		continue;
	}
	const lines = r.stdout.replace(/\s+$/, '').split('\n').filter((l) => !/\[1–5\]|\[1-5\]/.test(l));
	writeFileSync(join(here, `src/lib/data/tui-result-${lang}.txt`), lines.join('\n').replace(/\n{3,}/g, '\n\n') + '\n');
}
