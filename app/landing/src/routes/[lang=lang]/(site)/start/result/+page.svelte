<script lang="ts">
	import { onMount } from 'svelte';
	import { M } from '$lib/data/measurements';
	import {
		CTX_OPTIONS,
		ETA,
		L1_MTP_BAND,
		LICENSES,
		TOK_PER_WORD,
		answerSeconds,
		budget,
		decodeRange,
		findGpu,
		fit,
		l1Range,
		measuredFor,
		memoryNeed,
		recommend,
		type Hw,
		type Model,
		type Os,
		type Range
	} from '$lib/estimator';
	import { fmtRatio } from '$lib/format';
	import { currentLang, href, num } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import ResultGauge from '$lib/onboarding/ResultGauge.svelte';
	import Shell from '$lib/onboarding/Shell.svelte';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].result);

	let hw = $state<Hw | null>(null);
	let ready = $state(false);
	let ctx = $state<number>(32768);
	let query = $state('');

	onMount(() => {
		const q = new URLSearchParams(location.search);
		query = location.search;
		const gpu = findGpu(q.get('gpu'));
		const ram = Number(q.get('ram'));
		if (gpu && ram > 0) {
			const os = (['windows', 'linux', 'macos'].includes(q.get('os') ?? '') ? q.get('os') : 'windows') as Os;
			hw = { gpu, ramGiB: ram, os, vramGiB: gpu.unified || gpu.cpuOnly ? null : Number(q.get('vram')) || gpu.vram || null };
		}
		ready = true;
	});

	const rec = $derived(hw ? recommend(hw, ctx) : null);
	const b = $derived(hw ? budget(hw) : null);

	const fmtRange = (r: Range, d = 0) => (Math.abs(r.hi - r.lo) < 0.5 ? num(r.lo, lang, d) : `${num(r.lo, lang, d)}–${num(r.hi, lang, d)}`);
	const wps = (tps: number, l: 'pl' | 'en') => tps / TOK_PER_WORD[l];
	const answerLang = $derived(lang);
	const words = 500;

	function forecast(m: Model) {
		if (!hw) return null;
		const f = fit(m, hw, ctx);
		const measured = measuredFor(hw.gpu?.id, m.id);
		const before = f === 'fits' || f === 'tight' ? decodeRange(m, hw.gpu) : null;
		return { f, measured, before, l1: before ? l1Range(m, before) : null, need: memoryNeed(m, ctx) };
	}
	const primaryF = $derived(rec ? forecast(rec.primary) : null);
	const licenseOf = (m: Model) => LICENSES[m.license as keyof typeof LICENSES];
	const fitBadge = { fits: 'badge--ok', tight: 'badge--estimate', slow: 'badge--estimate', no: 'badge--danger' } as const;
	const L1A = M.qwenUpstreamVulkanPlain;
	const L1B = M.qwenUpstreamVulkanMtp;
	const howSpeed = $derived(t.howSpeed(num(ETA.dense.lo, lang, 2), num(ETA.dense.hi, lang, 2), num(ETA.moe.lo, lang, 2), num(ETA.moe.hi, lang, 2)));
	const howL1 = $derived(
		t.howL1(`${num(L1_MTP_BAND.lo, lang, 1)}–${fmtRatio(L1_MTP_BAND.hi, lang)}`, fmtRatio(L1B.value / L1A.value, lang), num(L1A.value, lang, 1), num(L1B.value, lang, 1))
	);
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell title={t.title} lead={t.lead} wide back="/start/hardware">
	{#if ready && (!hw || !rec || !primaryF || !b)}
		<div class="notice notice--warn"><span class="notice__icon">!</span><p>{t.missing} <a href={href(lang, '/start/hardware')}>{t.toForm}</a></p></div>
	{:else if hw && rec && primaryF && b}
		{@const m = rec.primary}
		{@const lic = licenseOf(m)}
		<ResultGauge
			gpuId={hw.gpu?.id}
			gpuName={hw.gpu?.name ?? ''}
			{lang}
			estimate={primaryF.before ? { before: primaryF.before, best: primaryF.l1 ?? primaryF.before, l1: !!primaryF.l1 } : null}
		/>
		<div class="layout">
			<!-- machine -->
			<section class="card card--inset machine" aria-labelledby="mach-title">
				<div class="cluster between">
					<h2 id="mach-title" class="overline">{t.machine}</h2>
					<a class="small" href="{href(lang, '/start/hardware')}{query}">{t.edit}</a>
				</div>
				<p class="gpu">{hw.gpu?.name}</p>
				<p class="num small mute">
					{hw.gpu?.unified ? `${hw.ramGiB} GB unified` : hw.gpu?.cpuOnly ? `${hw.ramGiB} GB RAM` : `${hw.vramGiB} GB VRAM · ${hw.ramGiB} GB RAM`} · {hw.os} · {hw.gpu?.bw} GB/s
				</p>
				<div class="field ctx">
					<label for="ctx" class="label">{t.ctx}</label>
					<select id="ctx" class="select" bind:value={ctx}>
						{#each CTX_OPTIONS as c (c)}<option value={c}>{num(c / 1024, lang, 0)}k {t.ctxTokens}</option>{/each}
					</select>
				</div>
			</section>

			<!-- primary model -->
			<section class="card heat-card primary" aria-labelledby="prim-title">
				<p class="overline overline--accent" id="prim-title">{t.primary}</p>
				<div class="model-head">
					<h2 class="h2">{m.name}</h2>
					<span class="num quant">{m.quant}</span>
					<span class="badge {fitBadge[primaryF.f]}">{t.fit[primaryF.f]}</span>
				</div>
				<p class="small">{t.fitHint[primaryF.f]}</p>
				<dl class="facts">
					<div><dt>{t.size}</dt><dd class="num">{num(m.sizeGB, lang, 2)} {t.mb}</dd></div>
					<div><dt>{t.memory}</dt><dd class="num">{fmtRange(primaryF.need, 1)} GiB</dd></div>
					<div><dt>{t.budget}</dt><dd class="num">{fmtRange(b, 1)} GiB</dd></div>
					<div><dt>{t.license}</dt><dd><span class="badge {lic.commercial === 'yes' ? 'badge--ok' : 'badge--estimate'} badge--plain">{lic.name}</span></dd></div>
				</dl>
				<div class="membar" aria-hidden="true">
					<div class="bar bar--tall"><i style="width:{Math.min(100, (primaryF.need.hi / b.hi) * 100)}%"></i></div>
					<span class="num small mute">{Math.round((primaryF.need.hi / b.hi) * 100)}%</span>
				</div>
				{#if lic.commercial !== 'yes'}<p class="source">{lic.note[lang]}</p>{/if}
			</section>

			<!-- speed -->
			<section class="card speed" aria-labelledby="speed-title">
				<h2 id="speed-title" class="h3">{t.speed}</h2>
				{#if primaryF.measured}
					{@const p = primaryF.measured}
					{@const rows = [
						{ label: t.before, m: p.before, cls: 'bar--before' },
						...(p.l1 ? [{ label: t.l1, m: p.l1, cls: 'mid' }] : []),
						{ label: p.l1 ? t.l3 : lang === 'pl' ? 'Nasz silnik' : 'Our engine', m: p.after, cls: '' }
					]}
					<ul class="bars" role="list">
						{#each rows as r (r.m.id)}
							<li>
								<div class="bar-label">
									<span>{r.label}</span>
									<span class="badge badge--measured">{t.measured}</span>
								</div>
								<div class="bar-row">
									<div class="bar bar--tall {r.cls}" style="--v:{r.m.value / p.after.value}"><i></i></div>
									<span class="v num">{num(r.m.value, lang)} <small>{t.tps}</small></span>
								</div>
								<p class="source">{r.m.backend} · {r.m.config[lang]} · {r.m.harness} · {r.m.source}</p>
							</li>
						{/each}
					</ul>
					<p class="small {p.sameHarness ? 'ok' : 'warn'}">{p.sameHarness ? t.sameHarness : t.harnessWarn} {t.measuredNote}</p>
					<div class="human">
						<div class="stat"><span class="stat__value">{num(wps(p.after.value, 'pl'), lang, 0)}</span><span class="stat__label">{t.wpsPl}</span></div>
						<div class="stat"><span class="stat__value">{num(wps(p.after.value, 'en'), lang, 0)}</span><span class="stat__label">{t.wpsEn}</span></div>
						<div class="stat">
							<span class="stat__value">{num(answerSeconds(words, p.before.value, answerLang), lang)} → {num(answerSeconds(words, p.after.value, answerLang), lang)}<span class="stat__unit">s</span></span>
							<span class="stat__label">{t.answer}</span>
						</div>
					</div>
				{:else if primaryF.before}
					{@const before = primaryF.before}
					{@const top = primaryF.l1 ? primaryF.l1.hi : before.hi}
					<ul class="bars" role="list">
						<li>
							<div class="bar-label"><span>{t.before}</span><span class="badge badge--estimate">{t.estimate}</span></div>
							<div class="bar-row">
								<div class="bar bar--tall bar--range bar--before span" style="--lo:{before.lo / top};--hi:{before.hi / top}"><i></i></div>
								<span class="v num">{fmtRange(before)} <small>{t.tps}</small></span>
							</div>
						</li>
						<li>
							<div class="bar-label"><span>{t.l1}</span>{#if primaryF.l1}<span class="badge badge--estimate">{t.estimate}</span>{:else}<span class="badge badge--soon">{t.soon}</span>{/if}</div>
							{#if primaryF.l1}
								<div class="bar-row">
									<div class="bar bar--tall bar--range span" style="--lo:{primaryF.l1.lo / top};--hi:{primaryF.l1.hi / top}"><i></i></div>
									<span class="v num">{fmtRange(primaryF.l1)} <small>{t.tps}</small></span>
								</div>
							{:else}
								<p class="small mute">{t.noMtp}</p>
							{/if}
						</li>
						<li>
							<div class="bar-label"><span>{t.l3}</span><span class="badge badge--soon">{t.soon}</span></div>
							<p class="small mute">{t.l3Soon}</p>
						</li>
					</ul>
					{@const best = primaryF.l1 ?? before}
					<div class="human">
						<div class="stat"><span class="stat__value">{fmtRange({ lo: wps(best.lo, 'pl'), hi: wps(best.hi, 'pl') })}</span><span class="stat__label">{t.wpsPl}</span></div>
						<div class="stat"><span class="stat__value">{fmtRange({ lo: wps(best.lo, 'en'), hi: wps(best.hi, 'en') })}</span><span class="stat__label">{t.wpsEn}</span></div>
						<div class="stat">
							<span class="stat__value">{fmtRange({ lo: answerSeconds(words, best.hi, answerLang), hi: answerSeconds(words, best.lo, answerLang) })}<span class="stat__unit">s</span></span>
							<span class="stat__label">{t.answer}</span>
						</div>
					</div>
				{:else}
					<p class="notice notice--warn"><span class="notice__icon">!</span><span>{t.noSpeed}</span></p>
				{/if}
				<details class="disclosure">
					<summary>{t.howTitle}</summary>
					<div class="disclosure__body stack small">
						<p>{t.howMem}</p>
						<p>{howSpeed}</p>
						<p>{howL1}</p>
						<p>
							{t.howBw}: <span class="num">{hw.gpu?.bw}{hw.gpu?.bwMax ? `/${hw.gpu.bwMax}` : ''} GB/s</span>
							({hw.gpu?.bwSource === 'r04' ? t.bwR04 : t.bwSpec}); B_tok {m.name} {m.quant}: <span class="num">{num(m.bTok, lang, 2)} GB</span> ({m.bTokSource}).
						</p>
					</div>
				</details>
			</section>

			<!-- alternatives -->
			{#if rec.alternatives.length}
				<section class="alts" aria-labelledby="alt-title">
					<h2 id="alt-title" class="h3">{t.alternatives}</h2>
					<ul role="list">
						{#each rec.alternatives as a (a.role)}
							{@const fa = forecast(a.model)}
							{@const la = licenseOf(a.model)}
							<li class="card alt">
								<span class="overline">{t.roles[a.role]}</span>
								<p class="alt-name">{a.model.name} <span class="num quant">{a.model.quant}</span></p>
								<div class="cluster">
									{#if fa}<span class="badge {fitBadge[fa.f]}">{t.fit[fa.f]}</span>{/if}
									<span class="badge {la.commercial === 'yes' ? 'badge--ok' : 'badge--estimate'} badge--plain">{la.name}</span>
								</div>
								<p class="num small mute">{num(a.model.sizeGB, lang, 2)} {t.mb}</p>
								{#if fa?.measured}
									<p class="small"><span class="num">{num(fa.measured.before.value, lang)} → <strong class="acc">{num(fa.measured.after.value, lang)}</strong> {t.tps}</span> <span class="badge badge--measured">{t.measured}</span></p>
									<p class="source">{fa.measured.before.source} · {fa.measured.after.source}</p>
								{:else if fa?.before}
									<p class="small"><span class="num">{fmtRange(fa.before)} {t.tps}</span> <span class="badge badge--estimate">{t.estimate}</span></p>
								{/if}
								{#if la.commercial !== 'yes'}<p class="source">{la.note[lang]}</p>{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- next -->
			<section class="card card--inset next" aria-labelledby="next-title">
				<h2 id="next-title" class="h3">{t.nextTitle}</h2>
				<p class="small">{t.nextLead}</p>
				<div class="cluster">
					<a class="btn btn--primary" href={href(lang, '/start/download')}>{t.toDownload} <span class="arrow" aria-hidden="true">→</span></a>
					<a class="btn btn--secondary" href={href(lang, '/start/terminal')}>{t.toTerminal}</a>
				</div>
			</section>
		</div>
	{/if}
</Shell>

<style>
	.layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.35fr);
		gap: var(--sp-5);
		align-items: start;
	}
	.machine,
	.primary {
		grid-column: 1;
	}
	.speed {
		grid-column: 2;
		grid-row: 1 / span 3;
	}
	.alts,
	.next {
		grid-column: 1;
	}
	@media (max-width: 960px) {
		.layout {
			grid-template-columns: 1fr;
		}
		.machine,
		.primary,
		.speed,
		.alts,
		.next {
			grid-column: 1;
			grid-row: auto;
		}
	}
	.between {
		justify-content: space-between;
	}
	.machine {
		display: grid;
		gap: var(--sp-2);
	}
	.gpu {
		color: var(--text-hi);
		font-size: var(--fs-lg);
		font-weight: var(--fw-semibold);
		letter-spacing: -0.02em;
	}
	.ctx {
		margin-top: var(--sp-3);
	}
	.primary {
		display: grid;
		gap: var(--sp-4);
		padding: var(--sp-6);
	}
	.model-head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--sp-3);
	}
	.quant {
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.facts {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-3) var(--sp-5);
		margin: 0;
	}
	.facts dt {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.facts dd {
		margin: 0;
		color: var(--text-hi);
	}
	.membar {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: var(--sp-3);
		align-items: center;
	}
	.membar .bar > i {
		position: absolute;
		inset: 0 auto 0 0;
		background: var(--text);
		border-radius: inherit;
	}
	.speed {
		display: grid;
		gap: var(--sp-5);
		padding: var(--sp-6);
	}
	.bars {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-5);
	}
	.bar-label {
		display: flex;
		justify-content: space-between;
		gap: var(--sp-3);
		font-size: var(--fs-sm);
		color: var(--text-hi);
		margin-bottom: var(--sp-2);
	}
	.bar-row {
		display: grid;
		grid-template-columns: 1fr 8.5rem;
		gap: var(--sp-3);
		align-items: center;
	}
	.bar.mid > :global(i) {
		background: linear-gradient(90deg, var(--heat-1), var(--heat-2));
	}
	:global(:root[data-theme='light']) .bar.mid > :global(i) {
		background: linear-gradient(90deg, color-mix(in srgb, var(--heat-4) 55%, var(--bg-3)), color-mix(in srgb, var(--heat-3) 65%, var(--bg-3)));
	}
	.bar.span > :global(i) {
		left: calc(var(--lo) * 100%);
		width: calc((var(--hi) - var(--lo)) * 100%);
		min-width: 6px;
	}
	.v {
		text-align: right;
		color: var(--text-hi);
		font-size: var(--fs-lg);
		letter-spacing: -0.02em;
	}
	.v small {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.ok {
		color: var(--ok-ink);
	}
	.warn {
		color: var(--warn-ink);
	}
	.human {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr));
		gap: var(--sp-4);
		padding-top: var(--sp-5);
		border-top: 1px solid var(--line);
	}
	.human .stat__value {
		font-size: var(--fs-lg);
		white-space: nowrap;
	}
	@media (max-width: 560px) {
		.human {
			grid-template-columns: 1fr;
		}
		.bar-row {
			grid-template-columns: 1fr 7rem;
		}
	}
	.alts {
		display: grid;
		gap: var(--sp-3);
	}
	.alts ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-3);
	}
	.alt {
		display: grid;
		gap: var(--sp-2);
		padding: var(--sp-4) var(--sp-5);
	}
	.alt-name {
		color: var(--text-hi);
		font-weight: var(--fw-semibold);
	}
	.acc {
		color: var(--accent-ink);
	}
	.next {
		display: grid;
		gap: var(--sp-3);
	}
</style>
