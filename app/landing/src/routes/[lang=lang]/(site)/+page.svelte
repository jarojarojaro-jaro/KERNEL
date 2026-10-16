<script lang="ts">
	import { BRAND } from '$lib/brand';
	import cloud from '$lib/data/cloud-results.json';
	import { KLD_EXCEPTIONS, M, type MeasurementId } from '$lib/data/measurements';
	import gpuData from '$lib/data/gpus.json';
	import { currentLang, href, num } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import Results from '$lib/site/Results.svelte';
	import SpeedDuel from '$lib/site/SpeedDuel.svelte';
	import Waitlist from '$lib/site/Waitlist.svelte';

	const lang = $derived(currentLang());
	const c = $derived(copy[lang]);

	/** Cloud scorecards whose md5 check reports a difference against upstream (shown, not hidden). */
	const cudaDiff = Object.values(cloud.cards as Record<string, { dir: string; rows: { md5_status: string }[] }>)
		.filter((card) => card.rows.some((r) => /DIFF/.test(r.md5_status)))
		.map((card) => card.dir);

	const groups = $derived([
		{ key: 'measured', label: c.hardware.groups.measured, gpus: (gpuData.gpus as { id: string; name: string; arch: string; vram?: number; bw: number; lab: string | null; labDir?: string }[]).filter((g) => g.lab === 'measured') },
		{ key: 'progress', label: c.hardware.groups.progress, gpus: (gpuData.gpus as { id: string; name: string; arch: string; vram?: number; bw: number; lab: string | null; labDir?: string }[]).filter((g) => g.lab === 'in-progress') },
		{ key: 'soon', label: c.hardware.groups.soon, gpus: (gpuData.gpus as { id: string; name: string; arch: string; vram?: number; bw: number; lab: string | null; labDir?: string }[]).filter((g) => g.lab === 'planned') }
	]);
</script>

<svelte:head>
	<title>{c.meta.title}</title>
	<meta name="description" content={c.meta.description} />
	<meta property="og:title" content={c.meta.title} />
	<meta property="og:description" content={c.meta.description} />
	<meta property="og:type" content="website" />
	<meta property="og:locale" content={lang === 'pl' ? 'pl_PL' : 'en_US'} />
</svelte:head>

<!-- HERO -->
<section class="hero bg-grid" aria-labelledby="hero-title">
	<div class="container hero-grid">
		<div class="hero-copy">
			<p class="overline overline--accent">{c.hero.overline}</p>
			<h1 id="hero-title" class="display">
				{#each c.hero.title as line, i (line)}<span class="line" class:hl={i === 2}>{line}</span>{/each}
			</h1>
			<p class="lead">{c.hero.lead}</p>
			<div class="cluster ctas">
				<a class="btn btn--primary btn--lg" href={href(lang, '/start')}>{c.hero.cta} <span class="arrow" aria-hidden="true">→</span></a>
				<a class="btn btn--secondary btn--lg" href={href(lang, '/methodology')}>{c.hero.ctaSecondary}</a>
			</div>
			<ul class="chips" role="list">
				{#each c.hero.chips as chip (chip)}<li>{chip}</li>{/each}
			</ul>
		</div>
		<div class="hero-visual">
			<SpeedDuel />
		</div>
	</div>
</section>

<!-- PROOF STRIP -->
<section class="proof" aria-labelledby="proof-title">
	<div class="container">
		<h2 id="proof-title" class="sr-only">{c.proof.title}</h2>
		<dl class="proof-grid">
			{#each c.proof.items as p (p.id)}
				{@const m = M[p.id as MeasurementId]}
				<div class="stat">
					<dt class="stat__label">{p.label}</dt>
					<dd class="stat__value" class:accent={p.id !== 'qwenUpstreamVulkanPlain'}>{num(m.value, lang)}<span class="stat__unit">t/s</span></dd>
				</div>
			{/each}
			<div class="stat">
				<dt class="stat__label">{c.proof.patches}</dt>
				<dd class="stat__value">70</dd>
			</div>
		</dl>
		<p class="source">{c.proof.note} <a href={href(lang, '/methodology')}>{c.nav.methodology} →</a></p>
	</div>
</section>

<!-- HOW -->
<section id="how" class="section" aria-labelledby="how-title">
	<div class="container stack" style="--stack: var(--sp-10)">
		<header class="section-head">
			<p class="overline">{c.how.overline}</p>
			<h2 id="how-title" class="h2">{c.how.title}</h2>
			<p class="lead">{c.how.lead}</p>
		</header>
		<ol class="steps-grid">
			{#each c.how.steps as s (s.k)}
				<li class="card step">
					<span class="step-index">{s.k}</span>
					<h3 class="h3">{s.title}</h3>
					<p>{s.body}</p>
				</li>
			{/each}
		</ol>
		<div class="stack" style="--stack: var(--sp-4)">
			<h3 class="h3">{c.how.layers.title}</h3>
			<div class="table-wrap">
				<table class="table">
					<thead>
						<tr>{#each c.how.layers.head as h (h)}<th scope="col">{h}</th>{/each}</tr>
					</thead>
					<tbody>
						{#each c.how.layers.rows as row (row[0])}
							<tr>
								<th scope="row"><span class="layer">{row[0].split(' ')[0]}</span> {row[0].split(' ').slice(1).join(' ')}</th>
								<td>{row[1]}</td>
								<td class="nowrap">{row[2]}</td>
								<td>{row[3]}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<p class="source">{c.how.layers.note} {M.bacoAsleep.source} · {M.qwenUpstreamVulkanMtp.source} · {M.qwenOursMtp.source}</p>
		</div>
	</div>
</section>

<!-- RESULTS -->
<section id="results" class="section section--band" aria-labelledby="results-title">
	<div class="container stack" style="--stack: var(--sp-8)">
		<header class="section-head">
			<p class="overline">{c.results.overline}</p>
			<h2 id="results-title" class="h2">{c.results.title}</h2>
			<p class="lead">{c.results.lead}</p>
		</header>
		<Results />
	</div>
</section>

<!-- BIT FOR BIT -->
<section id="bits" class="section" aria-labelledby="bits-title">
	<div class="container bits-grid">
		<header class="section-head">
			<p class="overline">{c.bits.overline}</p>
			<h2 id="bits-title" class="h2">{c.bits.title}</h2>
			<p class="lead">{c.bits.lead}</p>
			<div class="hash hud" aria-hidden="true">
				<div class="hash-row head"><span></span><span class="mute">{lang === 'pl' ? 'baza' : 'base'}</span><span></span><span class="mute">{lang === 'pl' ? 'po instalacji' : 'installed'}</span></div>
				<div class="hash-row"><span class="mute">plain</span><span class="num">c4708318…</span><span class="eq">=</span><span class="num">c4708318…</span></div>
				<div class="hash-row"><span class="mute">MTP</span><span class="num">6f14e814…</span><span class="eq">=</span><span class="num">6f14e814…</span></div>
				<div class="hash-foot"><span class="badge badge--ok">{c.bits.badge}</span><span class="source">STATUS-NEXT.md:15</span></div>
			</div>
		</header>
		<div class="stack" style="--stack: var(--sp-6)">
			<ul class="how-checks" role="list">
				{#each c.bits.how as h (h.title)}
					<li>
						<h3 class="h3">{h.title}</h3>
						<p>{h.body}</p>
					</li>
				{/each}
			</ul>
			<div class="card card--inset stack" style="--stack: var(--sp-3)">
				<h3 class="h3">{c.bits.statusTitle}</h3>
				<ul class="status">
					{#each c.bits.status as s (s)}<li>{s}</li>{/each}
					{#if cudaDiff.length}<li class="warn">{c.bits.cudaDiff} ({cudaDiff.join(', ')})</li>{/if}
				</ul>
				<p class="source">
					{#each KLD_EXCEPTIONS as k (k.source)}{k.what[lang]}: {k.result[lang]} ({k.source})<br />{/each}
				</p>
				<p class="promise">{c.bits.promise}</p>
			</div>
		</div>
	</div>
</section>

<!-- HARDWARE -->
<section id="hardware" class="section section--band" aria-labelledby="hw-title">
	<div class="container stack" style="--stack: var(--sp-8)">
		<header class="section-head">
			<p class="overline">{c.hardware.overline}</p>
			<h2 id="hw-title" class="h2">{c.hardware.title}</h2>
			<p class="lead">{c.hardware.lead}</p>
		</header>
		<div class="hw-groups">
			{#each groups as g (g.key)}
				<div class="hw-group">
					<h3 class="overline">{g.label} · {g.gpus.length}</h3>
					<ul role="list">
						{#each g.gpus as gpu (gpu.id)}
							<li class="hw {g.key}">
								<span class="hw-name">{gpu.name}</span>
								<span class="hw-meta num">{gpu.vram ? `${gpu.vram} GB · ` : ''}{gpu.arch}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>
		<div class="platforms">
			{#each c.hardware.platforms as p (p.os)}
				<div class="card platform">
					<div class="cluster"><h3 class="h3">{p.os}</h3><span class="badge {p.state === 'measured' ? 'badge--measured' : 'badge--soon'}">{p.state === 'measured' ? c.hardware.measured : c.hardware.soon}</span></div>
					<p class="small">{p.body}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- PRIVACY -->
<section id="privacy" class="section" aria-labelledby="privacy-title">
	<div class="container privacy-grid">
		<header class="section-head">
			<p class="overline">{c.privacy.overline}</p>
			<h2 id="privacy-title" class="h2">{c.privacy.title}</h2>
			<p class="lead">{c.privacy.lead}</p>
			<p class="small mute">{c.privacy.telemetry}</p>
			<div class="cluster">
				<a class="btn btn--secondary" href={href(lang, '/scan')}>{c.privacy.scanLink}</a>
				<a class="btn btn--ghost" href="/scan/scan.sh">{c.privacy.code}</a>
			</div>
		</header>
		<div class="lists">
			<div class="card">
				<h3 class="h3 list-title"><span class="dot ok" aria-hidden="true"></span>{c.privacy.reads}</h3>
				<ul class="ticks-list">{#each c.privacy.readList as r (r)}<li>{r}</li>{/each}</ul>
			</div>
			<div class="card">
				<h3 class="h3 list-title"><span class="dot no" aria-hidden="true"></span>{c.privacy.never}</h3>
				<ul class="cross-list">{#each c.privacy.neverList as r (r)}<li>{r}</li>{/each}</ul>
			</div>
			<pre class="code-sample" aria-label="HW1">HW1;os=linux;gpu=Navi 31 [Radeon RX 7900 XT/7900 XTX/7900M];sub=PULSE RX 7900 XTX;vendor=amd;vram=24.0;ngpu=1;drv=amdgpu 6.8.0-138-generic;ram=62.7;thr=16;isa=avx2;pcie=4x16;um=0;sum=…</pre>
		</div>
	</div>
</section>

<!-- PRICING -->
<section id="pricing" class="section section--band" aria-labelledby="pricing-title">
	<div class="container stack" style="--stack: var(--sp-8)">
		<header class="section-head">
			<p class="overline">{c.pricing.overline}</p>
			<h2 id="pricing-title" class="h2">{c.pricing.title}</h2>
			<p class="lead">{c.pricing.lead}</p>
		</header>
		<div class="pricing-grid">
			<div class="plans">
				{#each c.pricing.plans as p (p.id)}
					<div class="card plan" class:featured={p.featured}>
						<div class="cluster plan-head">
							<h3 class="h3">{BRAND.name} {p.name}</h3>
							{#if p.featured}<span class="badge badge--estimate">{lang === 'pl' ? 'hipoteza ceny' : 'price hypothesis'}</span>{/if}
						</div>
						<p class="price"><span class="num">{p.price}</span> <span class="mute small">{p.per}</span></p>
						<ul class="ticks-list">{#each p.items as it (it)}<li>{it}</li>{/each}</ul>
					</div>
				{/each}
				<p class="source">{c.pricing.hypothesis}</p>
			</div>
			<Waitlist />
		</div>
	</div>
</section>

<!-- FAQ -->
<section id="faq" class="section" aria-labelledby="faq-title">
	<div class="container faq-grid">
		<header class="section-head">
			<p class="overline">{c.faq.overline}</p>
			<h2 id="faq-title" class="h2">{c.faq.title}</h2>
		</header>
		<div>
			{#each c.faq.items as [q, a] (q)}
				<details class="disclosure">
					<summary>{q}</summary>
					<div class="disclosure__body"><p>{a}</p></div>
				</details>
			{/each}
		</div>
	</div>
</section>

<!-- FINAL CTA -->
<section class="final" aria-labelledby="final-title">
	<div class="container final-inner hud">
		<h2 id="final-title" class="h2">{c.hero.title.join(' ')}</h2>
		<a class="btn btn--primary btn--lg" href={href(lang, '/start')}>{c.hero.cta} <span class="arrow" aria-hidden="true">→</span></a>
	</div>
</section>

<style>
	/* hero */
	.hero {
		position: relative;
		padding-block: clamp(3rem, 1rem + 6vw, 6rem) clamp(3rem, 2rem + 4vw, 5rem);
		border-bottom: 1px solid var(--line);
		overflow: hidden;
	}
	.hero::after {
		content: '';
		position: absolute;
		inset: auto 0 0 0;
		height: 12rem;
		background: linear-gradient(transparent, var(--bg-0));
		pointer-events: none;
	}
	.hero-grid {
		position: relative;
		z-index: 1;
		display: grid;
		grid-template-columns: minmax(0, 1.12fr) minmax(0, 1fr);
		gap: clamp(2rem, 1rem + 3vw, 3.5rem);
		/* top-aligned: the copy never moves if the animated panel's height settles after load */
		align-items: start;
	}
	.hero-copy {
		padding-top: var(--sp-8);
		display: grid;
		gap: var(--sp-6);
		justify-items: start;
	}
	.hero .display {
		font-size: clamp(2.5rem, 0.9rem + 4.1vw, 4rem);
	}
	.line {
		display: block;
	}
	@media (min-width: 640px) {
		.line {
			white-space: nowrap;
		}
	}
	.line.hl {
		color: var(--accent-ink);
	}
	.ctas {
		--cluster: var(--sp-3);
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.chips li {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-mute);
		padding: 0.3rem 0.6rem;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
	}
	.chips li::before {
		content: '✓ ';
		color: var(--accent-ink);
	}
	@media (max-width: 1000px) {
		.hero-grid {
			grid-template-columns: 1fr;
		}
	}

	/* proof */
	.proof {
		padding-block: var(--sp-10);
		border-bottom: 1px solid var(--line);
	}
	.proof-grid {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: var(--sp-6);
		margin: 0 0 var(--sp-4);
	}
	.proof-grid .stat {
		padding-left: var(--sp-4);
		border-left: 2px solid var(--line-strong);
		display: flex;
		flex-direction: column-reverse;
		justify-content: start;
		gap: var(--sp-2);
	}
	.proof-grid dd {
		margin: 0;
	}
	.stat__value.accent {
		color: var(--accent-ink);
	}
	@media (max-width: 760px) {
		.proof-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}

	.section-head {
		display: grid;
		gap: var(--sp-4);
		max-width: 48rem;
		align-content: start;
	}
	.steps-grid {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-4);
	}
	.step {
		display: grid;
		gap: var(--sp-3);
		align-content: start;
		position: relative;
	}
	.step::after {
		content: '';
		position: absolute;
		top: var(--sp-6);
		right: var(--sp-6);
		width: 2.5rem;
		height: 1px;
		background: linear-gradient(90deg, var(--line-strong), transparent);
	}
	@media (max-width: 860px) {
		.steps-grid {
			grid-template-columns: 1fr;
		}
	}
	.layer {
		font-family: var(--font-mono);
		color: var(--accent-ink);
		margin-right: 0.25em;
	}
	.nowrap {
		white-space: nowrap;
	}

	/* bits */
	.bits-grid,
	.privacy-grid,
	.faq-grid {
		display: grid;
		grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
		gap: clamp(2rem, 1rem + 4vw, 5rem);
		align-items: start;
	}
	@media (max-width: 900px) {
		.bits-grid,
		.privacy-grid,
		.faq-grid {
			grid-template-columns: 1fr;
		}
	}
	.hash {
		margin-top: var(--sp-4);
		padding: var(--sp-5);
		display: grid;
		gap: var(--sp-3);
		--hud-c: var(--ok-ink);
	}
	.hash-row {
		display: grid;
		grid-template-columns: 3.5rem 1fr auto 1fr;
		gap: var(--sp-3);
		align-items: center;
		font-size: var(--fs-sm);
		color: var(--text-hi);
	}
	.hash-row .mute {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
	}
	.eq {
		color: var(--ok-ink);
		font-weight: var(--fw-bold);
	}
	.hash-foot {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--sp-3);
		flex-wrap: wrap;
		padding-top: var(--sp-3);
		border-top: 1px dashed var(--line);
	}
	.how-checks {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-5);
	}
	.how-checks li {
		display: grid;
		gap: var(--sp-2);
		padding-left: var(--sp-5);
		border-left: 2px solid var(--accent-ink);
	}
	.status {
		margin: 0;
		padding-left: 1.2em;
		display: grid;
		gap: var(--sp-2);
	}
	.status .warn {
		color: var(--warn-ink);
	}
	.hash-row.head .mute {
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}
	.promise {
		color: var(--text-hi);
		font-weight: var(--fw-medium);
	}

	/* hardware */
	.hw-groups {
		display: grid;
		grid-template-columns: 1fr 1fr 1.6fr;
		gap: var(--sp-6);
		align-items: start;
	}
	@media (max-width: 960px) {
		.hw-groups {
			grid-template-columns: 1fr;
		}
	}
	.hw-group ul {
		list-style: none;
		margin: var(--sp-4) 0 0;
		padding: 0;
		display: grid;
		gap: var(--sp-2);
	}
	.hw-group:last-child ul {
		grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
	}
	.hw {
		display: grid;
		gap: var(--sp-1);
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--bg-2);
	}
	.hw.measured {
		border-color: color-mix(in srgb, var(--accent-ink) 50%, var(--line));
		box-shadow: var(--accent-glow);
	}
	.hw.progress {
		border-left: 3px solid var(--info-ink);
	}
	.hw.soon {
		border-style: dashed;
		background: transparent;
	}
	.hw-name {
		color: var(--text-hi);
		font-weight: var(--fw-medium);
		font-size: var(--fs-sm);
	}
	.hw-meta {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.platforms {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-4);
	}
	.platform {
		display: grid;
		gap: var(--sp-3);
		align-content: start;
	}
	@media (max-width: 860px) {
		.platforms {
			grid-template-columns: 1fr;
		}
	}

	/* privacy */
	.lists {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-4);
	}
	.list-title {
		display: flex;
		align-items: center;
		gap: var(--sp-2);
		font-size: var(--fs-md);
		margin-bottom: var(--sp-4);
	}
	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	.dot.ok {
		background: var(--ok);
	}
	.dot.no {
		background: var(--danger);
	}
	.ticks-list,
	.cross-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-2);
		font-size: var(--fs-sm);
	}
	.ticks-list li,
	.cross-list li {
		display: grid;
		grid-template-columns: 1.25rem 1fr;
	}
	.ticks-list li::before {
		content: '✓';
		color: var(--ok-ink);
	}
	.cross-list li::before {
		content: '×';
		color: var(--danger-ink);
		font-weight: var(--fw-bold);
	}
	.code-sample {
		grid-column: 1 / -1;
		margin: 0;
		padding: var(--sp-4);
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-md);
		background: var(--bg-1);
		color: var(--text);
		font-size: var(--fs-xs);
		white-space: pre-wrap;
		word-break: break-all;
	}
	@media (max-width: 560px) {
		.lists {
			grid-template-columns: 1fr;
		}
	}

	/* pricing */
	.pricing-grid {
		display: grid;
		grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
		gap: var(--sp-6);
		align-items: start;
	}
	.plans {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-4);
		align-content: start;
	}
	.plans .source {
		grid-column: 1 / -1;
	}
	.plan {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
	}
	.plan.featured {
		border-color: color-mix(in srgb, var(--accent-ink) 55%, var(--line));
	}
	.plan-head {
		justify-content: space-between;
	}
	.price .num {
		font-size: var(--fs-2xl);
		color: var(--text-hi);
		letter-spacing: -0.03em;
	}
	@media (max-width: 960px) {
		.pricing-grid {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 560px) {
		.plans {
			grid-template-columns: 1fr;
		}
	}

	/* final */
	.final {
		padding-block: var(--sp-10) 0;
	}
	.final-inner {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-6);
		align-items: center;
		justify-content: space-between;
		padding: clamp(1.5rem, 1rem + 3vw, 3rem);
		background:
			radial-gradient(80% 140% at 100% 100%, var(--accent-soft), transparent 60%),
			var(--bg-2);
	}
	.final-inner h2 {
		max-width: 22ch;
	}
</style>
