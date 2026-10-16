<script lang="ts">
	import cloud from '$lib/data/cloud-results.json';
	import { M, type Measurement } from '$lib/data/measurements';
	import gpuData from '$lib/data/gpus.json';
	import { currentLang, href, num } from '$lib/i18n';
	import { copy } from './copy';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang].results);

	const rows: { before: Measurement; after: Measurement; note?: { pl: string; en: string } }[] = [
		{ before: M.qwenUpstreamVulkanPlain, after: M.qwenOursMtp },
		{
			before: M.qwenUpstreamRocmMtp,
			after: M.qwenOursMtp,
			note: { pl: 'oba ze spekulacją MTP (upstream n=3, nasz n=4)', en: 'both with MTP speculation (upstream n=3, ours n=4)' }
		},
		{
			before: M.lfmUpstreamTg128,
			after: M.lfmOursTg128,
			note: {
				pl: `nasz z wolniejszym KV q8_0; w serwerze ${num(M.lfmOursServer.value, 'pl')} t/s (spec_sweep)`,
				en: `ours with the slower q8_0 KV; ${num(M.lfmOursServer.value, 'en')} t/s in the server (spec_sweep)`
			}
		}
	];

	type CloudCard = { dir: string; rows: { variant: string; model: string; decode_tps_median: number | null; decode_tps_min: number | null; decode_tps_max: number | null; md5_status: string; n_runs: number }[] };
	const cloudCards = cloud.cards as Record<string, CloudCard>;
	const inProgress = (gpuData.gpus as { id: string; name: string; arch: string; vram?: number; bw: number; lab: string | null; labDir?: string }[]).filter((g) => g.lab === 'in-progress');
	/** Variant ids from qwen-opt/cloud/PLAN-TESTOW.md:55-59. */
	const VARIANT: Record<string, { pl: string; en: string }> = {
		A0: { pl: 'upstream, ustawienia domyślne', en: 'upstream, default settings' },
		A1: { pl: 'upstream + konfiguracja L1', en: 'upstream + L1 configuration' },
		A2: { pl: 'nasz silnik, te same flagi', en: 'our engine, same flags' },
		A2s: { pl: 'nasz silnik, przełączniki wyłączone', en: 'our engine, switches off' },
		A3: { pl: 'nasz silnik, pełny stos', en: 'our engine, full stack' }
	};
	const MODEL_NAME: Record<string, string> = { 'qwen38-27b': 'Qwen3.8-27B', 'lfm25-24b-q5': 'LFM2.5-24B-A2B', 'lfm25-24b-q4': 'LFM2.5-24B-A2B Q4', 'qwen38-27b-q3': 'Qwen3.8-27B Q3' };
	const bitOk = (s: string) => /\bBIT\b/.test(s) && !/DIFF/.test(s);
</script>

<div class="table-wrap">
	<table class="table results">
		<caption>{t.caption}</caption>
		<thead>
			<tr>
				{#each t.head as h (h)}<th scope="col">{h}</th>{/each}
			</tr>
		</thead>
		<tbody>
			{#each rows as r (r.before.id)}
				{@const same = r.before.harness === r.after.harness}
				<tr>
					<th scope="row">
						<span class="model">{r.after.model}</span>
						<span class="q num">{r.after.quant}</span>
					</th>
					<td>
						<span class="v num before">{num(r.before.value, lang)}<small> t/s</small></span>
						<span class="cfg">{r.before.build.replace(' llama.cpp', '')} · {r.before.backend} · {r.before.config[lang]}</span>
					</td>
					<td>
						<span class="v num after">{num(r.after.value, lang)}<small> t/s</small></span>
						<span class="cfg">{r.after.backend} · {r.after.config[lang]}</span>
					</td>
					<td class="how">
						<span class="badge {same ? 'badge--measured' : 'badge--estimate'}">{same ? t.sameHarness : t.diffHarness}</span>
						{#if r.note}<span class="cfg">{r.note[lang]}</span>{/if}
						<span class="source">{r.before.source}<br />{r.after.source}</span>
					</td>
				</tr>
				<tr class="bars" aria-hidden="true">
					<td colspan="4">
						<div class="pair">
							<div class="bar bar--before" style="--v:{r.before.value / r.after.value}"><i></i></div>
							<div class="bar" style="--v:1"><i></i></div>
						</div>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<div class="cloud">
	<div class="cloud-head">
		<h3 class="h3">{t.cloudTitle}</h3>
		<p class="mute small">{t.cloudLead}</p>
	</div>
	<ul class="cloud-list">
		{#each inProgress as g (g.id)}
			{@const card = g.labDir ? cloudCards[g.labDir] : undefined}
			<li class="card card--inset">
				<div class="cluster">
					<strong>{g.name}</strong>
					<span class="badge badge--progress">{copy[lang].hardware.progress}</span>
				</div>
				<p class="source">{g.arch} · {g.vram} GB · {g.bw} GB/s</p>
				{#if card && card.rows.length}
					<p class="badge badge--estimate">{t.cloudPrelim}</p>
					<table class="table mini">
						<caption class="sr-only">{g.name}</caption>
						<thead><tr><th scope="col">{t.cloudVariant}</th><th scope="col" class="num">t/s</th></tr></thead>
						<tbody>
							{#each card.rows as row (row.model + row.variant)}
								<tr>
									<td>
										<span class="vm">{MODEL_NAME[row.model] ?? row.model}</span>
										<span class="cfg">{row.variant} · {VARIANT[row.variant]?.[lang] ?? row.variant}</span>
										{#if row.md5_status && !row.md5_status.startsWith('reference')}
											<span class="md5 {bitOk(row.md5_status) ? 'ok' : 'diff'}">md5: {row.md5_status}</span>
										{/if}
									</td>
									<td class="num">
										{row.decode_tps_median != null ? num(row.decode_tps_median, lang) : '—'}
										{#if row.decode_tps_min != null}<span class="cfg">{num(row.decode_tps_min, lang)}–{num(row.decode_tps_max ?? row.decode_tps_min, lang)}</span>{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
					<p class="source">~/qwen-opt/cloud/results/{card.dir}/scorecard.json · {t.cloudMethod}</p>
				{:else}
					<p class="small mute">{t.cloudNone}</p>
				{/if}
			</li>
		{/each}
	</ul>
	<p><a href={href(lang, '/methodology')}>{t.more} →</a></p>
</div>

<style>
	.results th[scope='row'] {
		min-width: 9rem;
	}
	.model {
		display: block;
		color: var(--text-hi);
	}
	.q {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.v {
		display: block;
		font-size: var(--fs-xl);
		line-height: 1.1;
		font-weight: var(--fw-medium);
		letter-spacing: -0.03em;
	}
	.v small {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		letter-spacing: 0;
	}
	.v.before {
		color: var(--text);
	}
	.v.after {
		color: var(--accent-ink);
	}
	.cfg {
		display: block;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		margin-top: var(--sp-1);
		max-width: 22rem;
	}
	.how {
		display: grid;
		gap: var(--sp-2);
		justify-items: start;
		min-width: 14rem;
	}
	.how .badge {
		white-space: normal;
	}
	tr:has(+ .bars) > * {
		border-bottom: 0;
	}
	.bars td {
		padding-top: 0;
	}
	.pair {
		display: grid;
		gap: 4px;
	}
	.pair .bar {
		height: 6px;
	}
	.cloud {
		margin-top: var(--sp-10);
		display: grid;
		gap: var(--sp-5);
	}
	.cloud-head {
		display: grid;
		gap: var(--sp-2);
		max-width: 44rem;
	}
	.cloud-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr));
		gap: var(--sp-3);
	}
	.cloud-list li {
		padding: var(--sp-4);
		display: grid;
		gap: var(--sp-2);
		align-content: start;
	}
	.mini th,
	.mini td {
		padding: var(--sp-2) var(--sp-2);
	}
	.vm {
		color: var(--text-hi);
		font-weight: var(--fw-medium);
	}
	.md5 {
		display: block;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		margin-top: var(--sp-1);
		overflow-wrap: anywhere;
	}
	.md5.diff {
		color: var(--warn-ink);
	}
	.md5.ok {
		color: var(--ok-ink);
	}
</style>
