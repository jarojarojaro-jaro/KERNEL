<script lang="ts">
	/**
	 * The NVIDIA results page (`/pl/nvidia/`, `/en/nvidia/`).
	 *
	 * One table of 11 cards with three speeds each, the MoE alternative, models and licences, the
	 * ready-made settings, the five method points, all six caveats and the engine release. Every
	 * number comes from `$lib/data/nvidia-cards.ts`, which cites `product/SITE-NVIDIA.md` line by
	 * line; nothing is computed or filled in here except locale formatting.
	 */
	import { BRAND } from '$lib/brand';
	import { cardsHref, currentLang, href, nvidiaHref, num, resultsHref, type Lang } from '$lib/i18n';
	import { SITE_PUBLIC } from '$lib/site/public';
	import Seo from '$lib/site/Seo.svelte';
	import { breadcrumbs } from '$lib/site/jsonld';
	import { ENTRIES } from '$lib/cards/explorer';
	import {
		CAVEATS,
		ENGINE_RELEASE,
		HERO_STATS,
		METHOD,
		MOE,
		NVIDIA_CARDS,
		NVIDIA_MODELS,
		RECIPE_BASE,
		RECIPES
	} from '$lib/data/nvidia-cards';
	import { nvidiaCopy } from './copy';

	const lang = $derived(currentLang());
	const c = $derived(nvidiaCopy[lang]);
	const meta = $derived(c.meta);

	/** Trailing slash everywhere: adapter-static writes `<path>/index.html`. */
	const path = $derived(nvidiaHref(lang));
	const ld = $derived(
		breadcrumbs([
			{ name: BRAND.name, path: `/${lang}/` },
			{ name: meta.crumbs.cards, path: cardsHref(lang) },
			{ name: meta.crumbs.nvidia, path }
		])
	);

	const NB = '\u00a0';
	/** Context in tokens: grouped thousands, no decimals ("262 144" / "262,144"). */
	const ctx = (v: number) => num(v, lang, 0);
	/** A speed from the table: one decimal, or an en dash when the source has no such number. */
	const tps = (v: number | null) => (v === null ? c.table.dash : num(v, lang, 1));

	/** Release link, minus the https:// prefix the page prints as text. */
	const releaseHost = $derived(ENGINE_RELEASE.url.replace(/^https:\/\//, ''));

	/**
	 * Card ids that have their own page in the explorer (`MEASURED` + the measurement queue, the
	 * same rule as the prerender entries). A row whose card has no page links to the maker list
	 * instead of a 404 — the 2080 Ti is not in `gpus.json` today.
	 */
	const cardIds = $derived(new Set(ENTRIES.map((e) => e.id)));
	/** The explorer page for a card, or the NVIDIA maker list when the card has none. */
	const cardHref = (id: string) => cardsHref(lang, cardIds.has(id) ? `${id}/` : 'nvidia/');
</script>

<svelte:head>
	<title>{meta.title} · {BRAND.name}</title>
	<meta name="description" content={meta.description} />
</svelte:head>

<Seo title={meta.title} description={meta.description} jsonld={ld ?? undefined} />

<div class="grain" aria-hidden="true"></div>

<article class="page">
	<!-- ============ hero ============ -->
	<header class="wrap hero" aria-labelledby="nv-title">
		<p class="eyebrow">{c.hero.eyebrow}</p>
		<h1 id="nv-title" class="giga">
			{c.hero.title[0]}<br />{c.hero.title[1]}
			<span class="tail">{c.hero.titleTail}</span>
		</h1>
		<p class="lede hero-lede">{c.hero.lead}</p>

		<ul class="stats" role="list" aria-label={c.hero.statsLabel}>
			{#each HERO_STATS as s, i (s.key)}
				<li>
					<p class="stat-v mono">
						{#if s.kind === 'tps'}
							{num(s.v, lang, 1)}{NB}<small>t/s</small>
						{:else if s.kind === 'pct'}
							+{num(s.v, lang, 0)}<small>%</small>
						{:else if s.kind === 'x'}
							{num(s.v, lang, 1)}<small>×</small>
						{:else}
							{num(s.v, lang, 0)}<small> {c.table.cols.ctx.toLowerCase()}</small>
						{/if}
					</p>
					<p class="stat-k">{c.hero.stats[s.key]}</p>
					<p class="stat-m mono">{s.model}{#if s.kind === 'tps'}{NB}· {num(s.ctx, lang, 0)}{NB}{c.table.cols.ctx.toLowerCase()}{/if}{#if s.kind === 'ctx'}{NB}· {num(s.v, lang, 0)}{NB}{c.table.cols.ctx.toLowerCase()}{/if}</p>
				</li>
			{/each}
		</ul>

		<p class="cta-row">
			<a class="btn btn--primary" href="#table">{c.hero.ctaPrimary} <span class="arrow" aria-hidden="true">→</span></a>
			<a class="btn btn--secondary" href={ENGINE_RELEASE.url} rel="noopener">{c.hero.ctaSecondary}</a>
		</p>
	</header>

	<!-- ============ the eleven-card table ============ -->
	<section class="wrap blk" id="table" aria-labelledby="nv-table">
		<header class="blk-h">
			<p class="eyebrow">{c.table.kicker}</p>
			<h2 id="nv-table" class="h2">{c.table.title}</h2>
			<p class="fine">{c.table.lead}</p>
		</header>

		<div class="table-wrap">
			<table class="table nv-table">
				<caption>{c.table.caption}</caption>
				<thead>
					<tr>
						<th scope="col" class="col-card"><span class="lbl-long">{c.table.cols.card}</span><span class="lbl-short">{c.table.colsShort.card}</span></th>
						<th scope="col" class="col-model">{c.table.cols.model}</th>
						<th scope="col" class="num col-ctx">{c.table.cols.ctx}</th>
						<th scope="col" class="num">{c.table.cols.today}</th>
						<th scope="col" class="num">{c.table.cols.enigma}</th>
						<th scope="col" class="num"><span class="lbl-long">{c.table.cols.engine}</span><span class="lbl-short">{c.table.colsShort.engine}</span></th>
					</tr>
				</thead>
				<tbody>
					{#each NVIDIA_CARDS as row (row.id)}
						<tr>
							<th scope="row">
								<a href={cardHref(row.id)}>{row.name}</a>
								<span class="vram mono">{row.vramGB}{NB}GB</span>
								<span class="mini mono">{row.model}{NB}· {NB}{#if row.ctxToday === row.ctxNow}{ctx(row.ctxNow)}{:else}{ctx(row.ctxToday)} → {ctx(row.ctxNow)}{/if}</span>
							</th>
							<td class="model col-model">{row.model}</td>
							<td class="num ctx mono col-ctx">
								{#if row.ctxToday === row.ctxNow}
									{ctx(row.ctxNow)}
								{:else}
									{ctx(row.ctxToday)} <span aria-hidden="true">→</span><span class="sr-only">{c.table.to}</span> <b>{ctx(row.ctxNow)}</b>
								{/if}
							</td>
							<td class="num speed cold mono">{tps(row.today)}</td>
							<td class="num speed mono">
								{#if row.mix}<span class="mix">{c.table.mixSaluki}</span> {/if}<b>{tps(row.enigma)}</b>
								{#if row.enigmaGain}<small>({row.enigmaGain})</small>{/if}
							</td>
							<td class="num speed mono">
								{#if row.engine === null}
									–
								{:else}
									{#if row.mix}<span class="mix">{c.table.mixBonsai}</span> {/if}<b>{tps(row.engine)}</b>
									{#if row.engineGain}<small>({row.engineGain})</small>{/if}
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<div class="notes">
			<p class="fine">{c.table.legend}</p>
			<p class="fine">{c.table.note12}</p>
			<p class="fine">{c.table.note3090}</p>
		</div>
	</section>

	<!-- ============ the MoE alternative ============ -->
	<section class="wrap blk blk--alt" aria-labelledby="nv-moe">
		<div class="split">
			<header class="blk-h">
				<p class="eyebrow">{c.moe.kicker}</p>
				<h2 id="nv-moe" class="h2">{c.moe.title}</h2>
				<p class="fine">{c.moe.lead}</p>
			</header>
			<ul class="moe" role="list">
				{#each MOE.rows as r (r.id)}
					<li>
						<span class="moe-c">{r.name}</span>
						<span class="moe-v mono">{num(r.tps, lang, 1)}{NB}<small>t/s</small></span>
						<span class="moe-m mono">{MOE.model} · {c.table.cols.ctx} {ctx(MOE.ctx)}</span>
					</li>
				{/each}
			</ul>
		</div>
	</section>

	<!-- ============ models and licences ============ -->
	<section class="wrap blk" aria-labelledby="nv-models">
		<header class="blk-h">
			<p class="eyebrow">{c.models.kicker}</p>
			<h2 id="nv-models" class="h2">{c.models.title}</h2>
			<p class="fine">{c.models.lead}</p>
		</header>

		<div class="table-wrap">
			<table class="table lic-table">
				<thead>
					<tr>
						<th scope="col">{c.models.cols.model}</th>
						<th scope="col">{c.models.cols.licence}</th>
						<th scope="col">{c.models.cols.file}</th>
					</tr>
				</thead>
				<tbody>
					{#each NVIDIA_MODELS as m (m.name)}
						<tr class:nc={m.nc}>
							<th scope="row">{m.name}</th>
							<td>
								<span class="lic" class:nc={m.nc}>{m.licence[lang]}</span>
							</td>
							<td class="links">
								{#each m.urls as u, i (u)}
									{#if i > 0}<span class="sep" aria-hidden="true">·</span>{/if}
									<a href={u} rel="noopener">{u.replace('https://huggingface.co/', '')}</a>
								{/each}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<p class="fine lic-note">{c.models.salukiNote}</p>
		<p class="fine lic-note">{c.models.lfmNote}</p>
	</section>

	<!-- ============ ready-made settings ============ -->
	<section class="wrap blk blk--alt" aria-labelledby="nv-recipes">
		<header class="blk-h">
			<p class="eyebrow">{c.recipes.kicker}</p>
			<h2 id="nv-recipes" class="h2">{c.recipes.title}</h2>
			<p class="fine">{c.recipes.lead}</p>
		</header>

		<p class="base">
			<span class="base-k mono">{c.recipes.base}</span>
			<code>{RECIPE_BASE}</code>
		</p>

		<details class="advanced">
			<summary>{c.recipes.summary}</summary>
			<div class="table-wrap">
				<table class="table">
					<thead>
						<tr>
							<th scope="col">{c.recipes.cols.mem}</th>
							<th scope="col">{c.recipes.cols.engine}</th>
							<th scope="col">{c.recipes.cols.flags}</th>
							<th scope="col">{c.recipes.cols.batch}</th>
						</tr>
					</thead>
					<tbody>
						{#each RECIPES as r, i (`${r.memClass}-${i}`)}
							<tr>
								<th scope="row">{r.memClass}</th>
								<td>{r.engine}</td>
								<td class="flags">
									<code>{r.flags}</code>
									{#if r.env}<span class="env mono">{r.env}</span>{/if}
								</td>
								<td class="mono">{r.batch}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</details>
		<p class="fine">{c.recipes.note}</p>
	</section>

	<!-- ============ how we got there ============ -->
	<section class="wrap blk" aria-labelledby="nv-method">
		<header class="blk-h">
			<p class="eyebrow">{c.method.kicker}</p>
			<h2 id="nv-method" class="h2">{c.method.title}</h2>
			<p class="fine">{c.method.lead}</p>
		</header>
		<ol class="method" role="list">
			{#each METHOD as key, i (key)}
				{@const it = c.method.items[key]}
				<li>
					<span class="m-ix mono" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
					<div>
						<h3 class="m-t">{it.title}</h3>
						<p class="m-b">{it.body}</p>
					</div>
				</li>
			{/each}
		</ol>
	</section>

	<!-- ============ caveats ============ -->
	<section class="wrap blk blk--warn" aria-labelledby="nv-caveats">
		<header class="blk-h">
			<p class="eyebrow eyebrow--warn">{c.caveats.kicker}</p>
			<h2 id="nv-caveats" class="h2">{c.caveats.title}</h2>
			<p class="fine">{c.caveats.lead}</p>
		</header>
		<ul class="caveats" role="list">
			{#each CAVEATS as key (key)}
				{@const it = c.caveats.items[key]}
				<li>
					<h3 class="cv-t">{it.title}</h3>
					<p class="cv-b">{it.body}</p>
				</li>
			{/each}
		</ul>
	</section>

	<!-- ============ release + internal links ============ -->
	<section class="wrap blk release" aria-labelledby="nv-release">
		<div class="rel">
			<div>
				<p class="eyebrow">{c.release.kicker}</p>
				<h2 id="nv-release" class="h2">{c.release.title}</h2>
				<p class="fine">{c.release.body}</p>
			</div>
			<a class="btn btn--primary rel-btn" href={ENGINE_RELEASE.url} rel="noopener">
				{c.release.cta} <span class="arrow" aria-hidden="true">→</span>
			</a>
		</div>
		<p class="mono rel-url">{releaseHost}</p>

		<nav class="more" aria-label={c.links.cards}>
			<a href={cardsHref(lang, 'nvidia/')}>{c.links.cards} <span aria-hidden="true">→</span></a>
			<a href={resultsHref(lang)}>{c.links.results} <span aria-hidden="true">→</span></a>
			{#if !SITE_PUBLIC}
				<a href={href(lang, '/methodology')}>{c.links.methodology} <span aria-hidden="true">→</span></a>
			{/if}
		</nav>
		<p class="fine amd">{c.links.amd}</p>
	</section>
</article>

<style>
	.page {
		padding-top: clamp(5rem, 3rem + 4vw, 7rem);
		overflow-x: clip;
	}
	.wrap {
		width: min(100% - 2 * var(--gutter), var(--container));
		margin-inline: auto;
	}

	/* ---------- hero ---------- */
	.hero {
		display: grid;
		gap: var(--sp-5);
		padding-bottom: var(--sp-16);
	}
	.hero h1 {
		margin: 0;
		max-width: 22ch;
	}
	.tail {
		display: block;
		margin-top: var(--sp-4);
		font-size: clamp(1.05rem, 0.9rem + 0.7vw, 1.5rem);
		font-weight: 500;
		font-stretch: 100%;
		line-height: 1.35;
		letter-spacing: -0.01em;
		color: var(--accent-ink);
		text-wrap: pretty;
	}
	.hero-lede {
		max-width: 62ch;
	}

	.stats {
		list-style: none;
		margin: var(--sp-6) 0 0;
		padding: 0;
		display: grid;
		gap: 1px;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr));
		background: var(--line);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		overflow: hidden;
	}
	.stats > li {
		display: grid;
		align-content: start;
		gap: var(--sp-2);
		padding: var(--sp-5);
		background: var(--bg-1);
	}
	.stat-v {
		margin: 0;
		font-size: clamp(1.75rem, 1.2rem + 1.6vw, 2.5rem);
		font-weight: 600;
		line-height: 1;
		letter-spacing: -0.04em;
		color: var(--text-hi);
	}
	.stat-v small {
		font-size: 0.42em;
		letter-spacing: 0;
		color: var(--text-mute);
	}
	.stat-k {
		margin: 0;
		font-size: var(--fs-sm);
		line-height: 1.45;
		color: var(--text-hi);
	}
	.stat-m {
		margin: 0;
		font-size: var(--fs-xs);
		line-height: 1.5;
		color: var(--text-mute);
	}
	.cta-row {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
		margin: var(--sp-4) 0 0;
	}

	/* ---------- blocks ---------- */
	.blk {
		padding-block: var(--sp-16);
		border-top: 1px solid var(--line);
	}
	/* A grid item defaults to min-width:auto, so a wide table inside `.table-wrap` would stretch the
	   whole column past the viewport instead of scrolling inside its own box. */
	.blk > * {
		min-width: 0;
	}
	.blk--alt {
		background: var(--bg-1);
		border-block: 1px solid var(--line);
		border-top-color: var(--line);
	}
	.blk-h {
		display: grid;
		gap: var(--sp-3);
		margin-bottom: var(--sp-8);
		max-width: 70ch;
	}
	.blk-h h2 {
		margin: 0;
	}
	.blk--warn .blk-h h2 {
		color: var(--warn-ink);
	}
	.eyebrow--warn {
		color: var(--warn-ink);
	}

	/* ---------- card table ---------- */
	/* Positioned ancestor for the `.sr-only` spans inside cells: without it they anchor to the
	   initial containing block and push the document 89 px wider than the viewport at 375 px. */
	.table-wrap {
		position: relative;
	}
	.nv-table {
		font-variant-numeric: tabular-nums;
	}
	.nv-table tbody th {
		white-space: nowrap;
	}
	.nv-table tbody th a {
		color: var(--text-hi);
		text-decoration: none;
		border-bottom: 1px solid color-mix(in srgb, var(--heat-3) 45%, transparent);
	}
	.nv-table tbody th a:hover,
	.nv-table tbody th a:focus-visible {
		border-bottom-color: var(--heat-3);
	}
	/* Small screens keep the three speed columns — they are the point of the page — and fold the
	   model and context into a second line under the card name. `.mini` carries the same values
	   there, so nothing is lost, only moved. */
	.nv-table .mini {
		display: none;
		margin-top: 0.15rem;
		font-size: var(--fs-2xs);
		line-height: 1.35;
		color: var(--text-mute);
	}
	@media (max-width: 47.99rem) {
		.nv-table .col-model,
		.nv-table .col-ctx {
			display: none;
		}
		.nv-table .mini {
			display: block;
		}
		.nv-table .lbl-long {
			display: none;
		}
		.nv-table th,
		.nv-table td {
			padding-inline: var(--sp-1);
		}
		.nv-table tbody th {
			white-space: normal;
			word-break: break-word;
		}
		.nv-table .mini {
			word-break: break-word;
		}
		.nv-table thead th {
			font-size: var(--fs-2xs);
		}
		.nv-table .model {
			min-width: 0;
		}
		/* The Saluki / Bonsai 2 + MTP tags are explained in note12 right below; on a 375 px screen
		   they cost 95 px of column width and push the numbers out of view. */
		.nv-table .mix {
			display: none;
		}
		/* Fixed widths on small screens: auto layout squeezed the card name to 54 px. */
		.nv-table {
			table-layout: fixed;
			width: 100%;
		}
		.nv-table .col-card {
			width: 40%;
		}
		.nv-table .speed {
			white-space: normal;
		}
		.nv-table .speed small {
			display: block;
			margin-left: 0;
		}
	}
	.lbl-short {
		display: none;
	}
	@media (max-width: 47.99rem) {
		.lbl-short {
			display: inline;
		}
	}
	.nv-table .vram {
		display: block;
		margin-top: 0.15rem;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.nv-table .model {
		color: var(--text);
		min-width: 12rem;
	}
	.nv-table .ctx {
		white-space: nowrap;
		color: var(--text-mute);
	}
	.nv-table .ctx b {
		color: var(--text);
		font-weight: 600;
	}
	.nv-table .speed {
		white-space: nowrap;
	}
	.nv-table .speed b {
		color: var(--text-hi);
		font-weight: 600;
	}
	.nv-table .speed small {
		margin-left: 0.3em;
		color: var(--text-mute);
		font-size: 0.85em;
	}
	.nv-table .speed.cold {
		color: var(--text-mute);
	}
	.nv-table .mix {
		font-size: var(--fs-2xs);
		letter-spacing: 0.02em;
		color: var(--text-mute);
	}
	.notes {
		display: grid;
		gap: var(--sp-3);
		margin-top: var(--sp-5);
	}
	.notes .fine {
		max-width: 88ch;
	}

	/* ---------- MoE ---------- */
	.split {
		display: grid;
		gap: var(--sp-8);
		align-items: start;
	}
	@media (min-width: 60rem) {
		.split {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
			gap: var(--sp-12);
		}
		.split .blk-h {
			margin-bottom: 0;
		}
	}
	.moe {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 1px;
		background: var(--line);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		overflow: hidden;
	}
	.moe > li {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: baseline;
		gap: var(--sp-2) var(--sp-4);
		padding: var(--sp-4) var(--sp-5);
		background: var(--bg-0);
	}
	.moe-c {
		color: var(--text-hi);
		font-weight: 600;
	}
	.moe-v {
		justify-self: end;
		font-size: var(--fs-lg);
		color: var(--accent-ink);
		letter-spacing: -0.02em;
	}
	.moe-v small {
		font-size: 0.55em;
		color: var(--text-mute);
	}
	.moe-m {
		grid-column: 1 / -1;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}

	/* ---------- licences ---------- */
	.lic {
		display: inline-block;
		padding: 0.1em 0.5em;
		border-radius: var(--r-pill);
		border: 1px solid var(--line-strong);
		font-size: var(--fs-2xs);
		white-space: nowrap;
		color: var(--text);
	}
	.lic.nc {
		border-color: var(--warn);
		color: var(--warn-ink);
		background: var(--warn-soft);
	}
	.lic-table .links {
		font-size: var(--fs-2xs);
		word-break: break-word;
	}
	.lic-table .links a {
		color: var(--accent-ink);
	}
	.lic-table .sep {
		margin-inline: 0.35em;
		color: var(--text-mute);
	}
	.lic-note {
		max-width: 82ch;
		margin-top: var(--sp-4);
	}
	.lic-note + .lic-note {
		margin-top: var(--sp-2);
	}

	/* ---------- recipes ---------- */
	.base {
		display: grid;
		gap: var(--sp-2);
		margin: 0 0 var(--sp-5);
	}
	.base-k {
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	.base code,
	.flags code {
		display: block;
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--bg-0);
		color: var(--text-hi);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		line-height: 1.7;
		overflow-x: auto;
		white-space: pre-wrap;
		word-break: break-word;
	}
	.advanced {
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background: var(--bg-0);
	}
	.advanced summary {
		cursor: pointer;
		padding: var(--sp-4) var(--sp-5);
		font-weight: 600;
		color: var(--text-hi);
		list-style: none;
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		min-height: 2.75rem;
	}
	.advanced summary::-webkit-details-marker {
		display: none;
	}
	.advanced summary::before {
		content: '+';
		flex: none;
		width: 1.25rem;
		font-family: var(--font-mono);
		color: var(--heat-3);
	}
	.advanced[open] summary::before {
		content: '−';
	}
	.advanced summary:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.advanced .table-wrap {
		border: 0;
		border-top: 1px solid var(--line);
		border-radius: 0;
		background: var(--bg-2);
	}
	.flags {
		min-width: 20rem;
	}
	.flags code {
		padding: 0;
		border: 0;
		background: none;
		font-size: var(--fs-2xs);
	}
	.env {
		display: block;
		margin-top: var(--sp-2);
		font-size: var(--fs-2xs);
		color: var(--accent-ink);
	}
	.blk--alt > .fine {
		margin-top: var(--sp-4);
	}

	/* ---------- method ---------- */
	.method {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-6);
		counter-reset: m;
	}
	@media (min-width: 52rem) {
		.method {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			gap: var(--sp-8);
		}
	}
	.method > li {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: var(--sp-4);
		align-items: start;
	}
	.m-ix {
		font-size: var(--fs-sm);
		font-weight: 600;
		color: var(--heat-3);
		letter-spacing: 0.06em;
		padding-top: 0.15rem;
	}
	.m-t {
		margin: 0 0 var(--sp-2);
		font-size: var(--fs-md);
		letter-spacing: -0.01em;
		color: var(--text-hi);
	}
	.m-b {
		margin: 0;
		font-size: var(--fs-sm);
		line-height: 1.65;
		color: var(--text);
	}

	/* ---------- caveats ---------- */
	.blk--warn {
		background: linear-gradient(180deg, var(--warn-soft), transparent 70%), var(--bg-1);
		border-block: 1px solid var(--line);
	}
	.caveats {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 1px;
		background: color-mix(in srgb, var(--warn) 25%, var(--line));
		border: 1px solid color-mix(in srgb, var(--warn) 25%, var(--line));
		border-radius: var(--r-xl);
		overflow: hidden;
	}
	@media (min-width: 56rem) {
		.caveats {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	.caveats > li {
		padding: var(--sp-5);
		background: var(--bg-0);
	}
	.cv-t {
		margin: 0 0 var(--sp-2);
		font-size: var(--fs-sm);
		font-weight: 650;
		line-height: 1.35;
		color: var(--warn-ink);
	}
	.cv-b {
		margin: 0;
		font-size: var(--fs-sm);
		line-height: 1.6;
		color: var(--text);
	}

	/* ---------- release + links ---------- */
	.release {
		display: grid;
		gap: var(--sp-5);
	}
	.rel {
		display: grid;
		gap: var(--sp-5);
		align-items: center;
	}
	@media (min-width: 52rem) {
		.rel {
			grid-template-columns: minmax(0, 1fr) auto;
		}
	}
	.rel h2 {
		margin: 0 0 var(--sp-3);
	}
	.rel-btn {
		justify-self: start;
	}
	.rel-url {
		margin: 0;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		word-break: break-all;
	}
	.more {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3) var(--sp-6);
		margin-top: var(--sp-4);
		padding-top: var(--sp-5);
		border-top: 1px solid var(--line);
	}
	.more a {
		display: inline-flex;
		align-items: center;
		gap: 0.4em;
		min-height: 2.75rem;
		color: var(--text-hi);
		font-weight: 600;
		text-decoration: none;
		border-bottom: 1px solid transparent;
	}
	.more a:hover,
	.more a:focus-visible {
		border-bottom-color: var(--heat-3);
	}
	.more a span {
		color: var(--heat-3);
	}
	.amd {
		margin: var(--sp-4) 0 0;
		max-width: 80ch;
	}
</style>
