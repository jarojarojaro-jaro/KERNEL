<script lang="ts">
	import { currentLang, num } from '$lib/i18n';
	import { MODELS, LICENSES, CTX_OPTIONS, fit, decodeRange, measuredFor, type Model, type FitLabel } from '$lib/estimator';
	import { T } from '$lib/desktop/i18n';
	import { DEMO, DEMO_HW, ACTIVE_MODEL_ID } from '$lib/desktop/demo';
	import ScreenHead from '$lib/desktop/ScreenHead.svelte';
	import Src from '$lib/desktop/Src.svelte';

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const md = $derived(t.models);

	let ctx = $state<number>(32768);
	type Chip = 'chat' | 'code' | 'polish' | 'fast';
	const CHIPS: Chip[] = ['chat', 'code', 'polish', 'fast'];
	let active = $state<Record<Chip, boolean>>({ chat: false, code: false, polish: false, fast: false });

	const test: Record<Chip, (m: Model) => boolean> = {
		chat: (m) => m.use !== 'code',
		code: (m) => m.use === 'code',
		polish: (m) => m.pl,
		fast: (m) => !!m.fast || m.kind === 'moe'
	};
	const rows = $derived(
		MODELS.filter((m) => CHIPS.every((c) => !active[c] || test[c](m))).map((m) => {
			const f = fit(m, DEMO_HW, ctx);
			const path = measuredFor(DEMO_HW.gpu?.id, m.id);
			const est = f === 'fits' || f === 'tight' ? decodeRange(m, DEMO_HW.gpu) : null;
			return { m, f, path, est, lic: LICENSES[m.license as keyof typeof LICENSES] };
		})
	);
	const fitClass: Record<FitLabel, string> = {
		fits: 'badge--ok',
		tight: 'badge--estimate',
		slow: 'badge--estimate',
		no: 'badge--danger'
	};
	const conditional = Object.values(LICENSES).filter((l) => l.commercial !== 'yes');
</script>

<svelte:head>
	<title>{t.shell.title(md.title)}</title>
</svelte:head>

<ScreenHead overline={md.overline} title={md.title} lead={md.lead(num(DEMO.vramGiB, lang), num(DEMO.ramGiB, lang))} />

<div class="controls">
	<div class="field ctx">
		<label class="label" for="ctx">{md.ctx}</label>
		<select id="ctx" class="select" bind:value={ctx}>
			{#each CTX_OPTIONS as c (c)}<option value={c}>{md.ctxOption(c / 1024)}</option>{/each}
		</select>
	</div>
	<div class="field">
		<span class="label" id="chips-l">{md.filters}</span>
		<div class="chips" role="group" aria-labelledby="chips-l" aria-describedby="chips-h">
			{#each CHIPS as c (c)}
				<button type="button" class="chip" aria-pressed={active[c]} onclick={() => (active[c] = !active[c])}>
					{md.chips[c]}
				</button>
			{/each}
		</div>
		<p id="chips-h" class="hint">{md.chipHint}</p>
	</div>
	<aside class="card card--inset quant" aria-labelledby="quant-h">
		<h2 id="quant-h" class="h3">{md.quantTitle}</h2>
		<p class="small">{md.quantBody}</p>
	</aside>
</div>

<p class="count small mute" role="status">{md.count(rows.length)}</p>

{#if rows.length === 0}
	<p class="card empty">{md.empty}</p>
{:else}
	<div class="table-wrap">
		<table class="table models">
			<caption>{md.caption}</caption>
			<thead>
				<tr>
					<th scope="col">{md.col.model}</th>
					<th scope="col" class="num">{md.col.size}</th>
					<th scope="col">{md.col.quant}</th>
					<th scope="col">{md.col.license}</th>
					<th scope="col">{md.col.fit}</th>
					<th scope="col" class="num">{md.col.speed}</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as r (r.m.id)}
					<tr>
						<th scope="row">
							<span class="mname">{r.m.name}</span>
							<span class="tags">
								<span class="size">{md.sizes[r.m.size]}</span>
								{#if r.m.pl}<span class="badge badge--measured badge--plain">{md.polish}</span>{/if}
								{#if r.m.id === ACTIVE_MODEL_ID}<span class="badge badge--progress">{md.active}</span>{/if}
							</span>
						</th>
						<td class="num" data-label={md.col.size}>{num(r.m.sizeGB, lang, 2)} GB</td>
						<td data-label={md.col.quant}><code>{r.m.quant}</code></td>
						<td data-label={md.col.license}>
							<span class="badge badge--plain {r.lic.commercial === 'yes' ? 'badge--ok' : 'badge--estimate'}">{r.lic.name}</span>
							{#if r.lic.commercial !== 'yes'}<span class="lic-warn small">{r.lic.note[lang]}</span>{/if}
						</td>
						<td data-label={md.col.fit}>
							<span class="badge {fitClass[r.f]}">{md.fit[r.f]}</span>
							<span class="fit-hint small">{md.fitHint[r.f]}</span>
						</td>
						<td class="num" data-label={md.col.speed}>
							{#if r.path}
								<span class="speed">{md.measured(num(r.path.after.value, lang))}</span>
								<span class="badge badge--measured">{t.common.measured}</span>
							{:else if r.est}
								<span class="speed">{md.estimated(num(r.est.lo, lang, 0), num(r.est.hi, lang, 0))}</span>
								<span class="badge badge--estimate">{t.common.estimate}</span>
							{:else}
								<span class="mute">—</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<div class="notes">
	<p class="small">{md.speedNote}</p>
	<Src m={[measuredFor('rx-7900-xtx', 'qwen38-27b-q4kxl')!.after, measuredFor('rx-7900-xtx', 'lfm25-24b-q5km')!.after]} src={[t.common.estSrc, t.common.sizeSrc]} />

	<section class="card card--inset lic" aria-labelledby="lic-h">
		<h2 id="lic-h" class="h3">{md.licenseNoteTitle}</h2>
		<ul>
			{#each conditional as l (l.name)}
				<li><strong>{l.name}:</strong> {l.note[lang]}</li>
			{/each}
		</ul>
		<p class="notice notice--info"><span class="notice__icon" aria-hidden="true">i</span><span>{md.llama4}</span></p>
		<Src src={lang === 'pl' ? 'raport 06 §2.4.2' : 'report 06 §2.4.2'} />
	</section>
</div>

<style>
	.controls {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) minmax(16rem, 22rem);
		gap: var(--sp-5);
		align-items: start;
		margin-bottom: var(--sp-5);
	}
	.ctx {
		min-width: 12rem;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.chip {
		appearance: none;
		padding: 0.4rem 0.85rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: transparent;
		color: var(--text);
		font: inherit;
		font-size: var(--fs-sm);
		cursor: pointer;
		transition:
			background-color var(--dur-1) var(--ease-out),
			color var(--dur-1) var(--ease-out);
	}
	.chip:hover {
		background: var(--bg-3);
		color: var(--text-hi);
	}
	.chip[aria-pressed='true'] {
		background: var(--accent);
		border-color: var(--accent);
		color: var(--on-accent);
		font-weight: var(--fw-semibold);
	}
	.quant {
		display: grid;
		gap: var(--sp-2);
		padding: var(--sp-4) var(--sp-5);
	}
	.count {
		margin-bottom: var(--sp-3);
	}
	.empty {
		color: var(--text-mute);
	}
	.mname {
		display: block;
		color: var(--text-hi);
		font-weight: var(--fw-semibold);
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
		margin-top: var(--sp-1);
	}
	.size {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		font-weight: var(--fw-regular);
	}
	code {
		color: var(--text-hi);
		font-size: var(--fs-xs);
	}
	.lic-warn,
	.fit-hint {
		display: block;
		margin-top: var(--sp-1);
		max-width: 16rem;
		color: var(--text-mute);
		font-size: var(--fs-xs);
	}
	.lic-warn {
		color: var(--warn-ink);
	}
	.speed {
		display: block;
		color: var(--text-hi);
		font-family: var(--font-mono);
		margin-bottom: var(--sp-1);
	}
	.notes {
		display: grid;
		gap: var(--sp-3);
		margin-top: var(--sp-5);
	}
	.lic {
		display: grid;
		gap: var(--sp-3);
		margin-top: var(--sp-4);
	}
	.lic ul {
		margin: 0;
		padding-left: 1.1rem;
		font-size: var(--fs-sm);
	}

	@media (max-width: 1100px) {
		.controls {
			grid-template-columns: auto minmax(0, 1fr);
		}
		.quant {
			grid-column: 1 / -1;
		}
	}
	@media (max-width: 720px) {
		.controls {
			grid-template-columns: minmax(0, 1fr);
		}
		.models thead {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip: rect(0, 0, 0, 0);
		}
		.models tr {
			display: grid;
			grid-template-columns: 1fr 1fr;
			border-bottom: 1px solid var(--line);
		}
		.models tbody tr:last-child {
			border-bottom: 0;
		}
		.models th,
		.models td {
			display: block;
			border-bottom: 0;
			padding: var(--sp-2) var(--sp-4);
			text-align: left;
		}
		.models tbody th {
			grid-column: 1 / -1;
			padding-top: var(--sp-4);
		}
		.models td::before {
			content: attr(data-label);
			display: block;
			font-family: var(--font-mono);
			font-size: var(--fs-2xs);
			letter-spacing: var(--tracking-overline);
			text-transform: uppercase;
			color: var(--text-mute);
			margin-bottom: var(--sp-1);
		}
		.models td.num {
			text-align: left;
		}
	}
</style>
