<script lang="ts">
	import { tick, onDestroy } from 'svelte';
	import { currentLang, href, switchLangHref, num, LANGS } from '$lib/i18n';
	import { recommend, fit, memoryNeed, measuredFor, decodeRange, LICENSES, type Model } from '$lib/estimator';
	import { M, MD5, type Measurement } from '$lib/data/measurements';
	import { T } from '$lib/desktop/i18n';
	import { proto } from '$lib/desktop/state.svelte';
	import { DEMO, DEMO_HW } from '$lib/desktop/demo';
	import Icon from '$lib/desktop/Icon.svelte';
	import ScreenHead from '$lib/desktop/ScreenHead.svelte';
	import ScanFacts from '$lib/desktop/ScanFacts.svelte';
	import SpecList from '$lib/desktop/SpecList.svelte';
	import Src from '$lib/desktop/Src.svelte';

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const w = $derived(t.wizard);

	// ---------- stepper ----------
	let step = $state(0);
	let stepHeading: HTMLElement | undefined = $state();
	async function go(i: number) {
		step = Math.max(0, Math.min(3, i));
		await tick();
		stepHeading?.focus();
	}

	// ---------- step 3: recommendation ----------
	const CTX = 32768;
	const rec = recommend(DEMO_HW, CTX);
	const options: { role: 'primary' | 'fast' | 'polish' | 'code'; model: Model }[] = [
		{ role: 'primary', model: rec.primary },
		...rec.alternatives.slice(0, 2)
	];
	let chosenId = $state(rec.primary.id);
	const chosen = $derived(options.find((o) => o.model.id === chosenId)!.model);
	const LINKS = [100, 300, 1000] as const;
	let mbps = $state<number>(300);
	const downloadMin = (m: Model) => Math.max(1, Math.ceil((m.sizeGB * 8000) / mbps / 60));
	const license = (m: Model) => LICENSES[m.license as keyof typeof LICENSES];

	// ---------- step 4: calibration (simulated timing, real or explicitly empty results) ----------
	type CalState = 'wait' | 'run' | 'ok' | 'none';
	interface CalRow {
		final: 'ok' | 'none';
		text: string;
		m?: Measurement[];
		src?: string;
	}
	const rows = $derived.by((): CalRow[] => {
		const path = measuredFor(DEMO_HW.gpu?.id, chosen.id);
		const need = memoryNeed(chosen, CTX);
		const md5 = chosen.id.startsWith('qwen38') ? MD5.qwenMtp : chosen.id.startsWith('lfm25') ? MD5.lfm : null;
		return [
			{ final: 'ok', text: w.s4.r.l0(num(M.bacoAsleep.value, lang), num(M.bacoAwake.value, lang, 0)), m: [M.bacoAsleep, M.bacoAwake] },
			{
				final: 'ok',
				text: w.s4.r.mem(num(need.lo, lang), num(need.hi, lang), num(DEMO.vramGiB, lang), `${CTX / 1024}k`),
				src: w.s4.src.mem
			},
			path ? { final: 'ok', text: w.s4.r.backend, m: [path.after] } : { final: 'none', text: w.s4.r.noLab },
			chosen.mtp === 'measured' ? { final: 'none', text: w.s4.r.spec, src: w.s4.src.spec } : { final: 'none', text: w.s4.r.specNone },
			md5 ? { final: 'ok', text: w.s4.r.logits(md5), src: 'KERNEL/qwen-opt/STATUS-NEXT.md:15' } : { final: 'none', text: w.s4.r.noLab },
			{ final: 'none', text: w.s4.r.aa }
		];
	});
	let calStates = $state<CalState[]>(Array(6).fill('wait'));
	let timer: ReturnType<typeof setInterval> | undefined;
	const calDone = $derived(calStates.every((s) => s === 'ok' || s === 'none'));
	const calRunning = $derived(calStates.some((s) => s === 'run'));

	function runCalibration() {
		clearInterval(timer);
		const finals = rows.map((r) => r.final);
		const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
		if (reduce) {
			calStates = finals;
			return;
		}
		calStates = finals.map((_, i) => (i === 0 ? 'run' : 'wait'));
		let i = 0;
		timer = setInterval(() => {
			calStates[i] = finals[i];
			i++;
			if (i < finals.length) calStates[i] = 'run';
			else clearInterval(timer);
		}, 500);
	}
	onDestroy(() => clearInterval(timer));
	// A different model invalidates the previous calibration.
	$effect(() => {
		void chosenId;
		clearInterval(timer);
		calStates = Array(6).fill('wait');
	});
</script>

<svelte:head>
	<title>{t.shell.title(w.title)}</title>
</svelte:head>

<ScreenHead overline={w.overline} title={w.title} />

<ol class="stepper" aria-label={w.stepperLabel}>
	{#each w.steps as name, i (i)}
		<li>
			<button
				type="button"
				class="st"
				class:done={i < step}
				aria-current={i === step ? 'step' : undefined}
				onclick={() => go(i)}
			>
				<span class="dot num" aria-hidden="true">{#if i < step}<Icon name="check" size={14} />{:else}{i + 1}{/if}</span>
				<span class="lbl">
					<span class="sr-only">{w.stepOf(i + 1, w.steps.length)}:</span>
					{name}
					{#if i < step}<span class="sr-only">({w.done})</span>{/if}
				</span>
			</button>
		</li>
	{/each}
</ol>

<section class="panel" aria-labelledby="step-h">
	<p class="step-index">{w.stepOf(step + 1, w.steps.length).toUpperCase()}</p>
	<h2 id="step-h" class="h3" tabindex="-1" bind:this={stepHeading}>{w.steps[step]}</h2>

	{#if step === 0}
		<div class="s1">
			<section class="card lang" aria-labelledby="lang-h">
				<h3 id="lang-h" class="h3">{w.s1.langTitle}</h3>
				<div class="cluster langs">
					{#each LANGS as l (l)}
						<a
							class="btn btn--sm {l === lang ? 'btn--primary' : 'btn--secondary'}"
							href={switchLangHref(l)}
							hreflang={l}
							lang={l}
							aria-current={l === lang ? 'true' : undefined}
							data-sveltekit-noscroll
							data-sveltekit-keepfocus>{l === 'pl' ? 'Polski' : 'English'}</a
						>
					{/each}
				</div>
				<p class="hint">{w.s1.langHint}</p>
			</section>

			<section class="card consent" aria-labelledby="consent-h">
				<h3 id="consent-h" class="h3">{w.s1.consentTitle}</h3>
				<div class="always">
					<span class="ok-ic"><Icon name="check" size={18} /></span>
					<div>
						<p class="strong">{w.s1.scanTitle}</p>
						<p class="small">{w.s1.scanBody}</p>
					</div>
				</div>
				<label class="check">
					<input type="checkbox" bind:checked={proto.telemetry} aria-describedby="tel-hint" />
					<span><span class="strong">{w.s1.telemetry}</span><span id="tel-hint" class="hint block">{w.s1.telemetryHint}</span></span>
				</label>
				<label class="check">
					<input type="checkbox" bind:checked={proto.crashReports} aria-describedby="crash-hint" />
					<span><span class="strong">{w.s1.crash}</span><span id="crash-hint" class="hint block">{w.s1.crashHint}</span></span>
				</label>
				<a class="small" href={href(lang, '/legal/privacy')}>{w.s1.privacy}</a>
			</section>

			<ScanFacts level={3} />
		</div>
	{:else if step === 1}
		<p class="lead step-lead">{w.s2.lead}</p>
		<p><span class="badge badge--ok">{w.s2.done}</span></p>
		<SpecList />
		<div class="card selftest">
			<div class="row-head">
				<h3 class="h3">{w.s2.selfTest}</h3>
				<span class="badge badge--prototype">{t.common.example}</span>
			</div>
			<ul class="checks">
				{#each w.s2.checks as c (c)}
					<li><span class="ok-ic"><Icon name="check" size={16} /></span>{c}</li>
				{/each}
			</ul>
			<p class="small mute">{w.s2.selfTestNote}</p>
		</div>
		<p class="notice notice--info"><span class="notice__icon" aria-hidden="true">i</span><span>{w.s2.problem}</span></p>
	{:else if step === 2}
		<p class="lead step-lead">{w.s3.lead(num(DEMO.vramGiB, lang), `${CTX / 1024}k`)}</p>
		<div class="field link">
			<label class="label" for="link">{w.s3.link}</label>
			<select id="link" class="select" bind:value={mbps} aria-describedby="link-hint">
				{#each LINKS as l (l)}<option value={l}>{l} Mb/s</option>{/each}
			</select>
			<p id="link-hint" class="hint">{w.s3.linkHint}</p>
		</div>
		<fieldset class="recs">
			<legend class="sr-only">{w.s3.title}</legend>
			{#each options as o (o.model.id)}
				{@const lic = license(o.model)}
				{@const path = measuredFor(DEMO_HW.gpu?.id, o.model.id)}
				{@const f = fit(o.model, DEMO_HW, CTX)}
				{@const est = f === 'fits' || f === 'tight' ? decodeRange(o.model, DEMO_HW.gpu) : null}
				<label class="card rec" class:sel={chosenId === o.model.id} class:primary={o.role === 'primary'}>
					<span class="rec-top">
						<input
							type="radio"
							name="model"
							value={o.model.id}
							bind:group={chosenId}
							aria-labelledby="rec-{o.model.id}-r rec-{o.model.id}-n"
							aria-describedby="rec-{o.model.id}-d"
						/>
						<span class="overline" id="rec-{o.model.id}-r">{o.role === 'primary' ? w.s3.primary : w.s3.roles[o.role]}</span>
						<span class="badge {f === 'fits' ? 'badge--ok' : 'badge--estimate'}">{t.models.fit[f]}</span>
					</span>
					<span class="rec-name" id="rec-{o.model.id}-n">{o.model.name} <span class="sr-only">{o.model.quant}</span></span>
					<span class="mute small" aria-hidden="true">{t.models.sizes[o.model.size]} · {o.model.quant}</span>
					<span class="kv" id="rec-{o.model.id}-d">
						<span class="k">{w.s3.size}</span><span class="v num">{num(o.model.sizeGB, lang, 2)} GB</span>
						<span class="k">{w.s3.time}</span><span class="v num">~{downloadMin(o.model)} min <span class="mute">{w.s3.timeAt(mbps)}</span></span>
						<span class="k">{w.s3.license}</span>
						<span class="v"><span class="badge {lic.commercial === 'yes' ? 'badge--ok' : 'badge--estimate'} badge--plain">{lic.name}</span></span>
						<span class="k">{w.s3.speed}</span>
						<span class="v num">
							{#if path}{w.s3.speedMeasured(num(path.after.value, lang))}
							{:else if est}{w.s3.speedEstimate(num(est.lo, lang, 0), num(est.hi, lang, 0))}{:else}—{/if}
						</span>
					</span>
					{#if lic.commercial !== 'yes'}<span class="small lic-note">{lic.note[lang]}</span>{/if}
					{#if path}<Src as="span" m={path.after} src={t.common.sizeSrc} />{:else}<Src as="span" src={est ? [t.common.estSrc, t.common.sizeSrc] : t.common.sizeSrc} />{/if}
				</label>
			{/each}
		</fieldset>
		<p class="small mute">{w.s3.downloadNote}</p>
		<div>
			<button type="button" class="btn btn--primary" onclick={() => go(3)}>
				<Icon name="download" size={16} />{w.s3.download}
			</button>
		</div>
	{:else}
		<p class="lead step-lead">{w.s4.lead}</p>
		<div class="card cal">
			<div class="row-head">
				<p class="small"><span class="mute">{w.s4.r.model}:</span> <strong>{chosen.name} {chosen.quant}</strong></p>
				<button type="button" class="btn btn--secondary btn--sm" onclick={runCalibration} disabled={calRunning}>
					<Icon name={calDone ? 'refresh' : 'play'} size={16} />{calDone ? w.s4.restart : w.s4.start}
				</button>
			</div>
			<ol class="cal-steps" aria-live="polite">
				{#each rows as r, i (i)}
					{@const s = calStates[i]}
					<li class="cal-row" data-state={s}>
						<span class="cal-ix num" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
						<div class="cal-body">
							<div class="cal-name">
								<span>{w.s4.stepNames[i]}</span>
								<span
									class="badge {s === 'ok' ? 'badge--ok' : s === 'run' ? 'badge--progress' : 'badge--soon'}"
									>{w.s4.state[s]}</span
								>
							</div>
							{#if s === 'ok' || s === 'none'}
								<p class="small">{r.text}</p>
								{#if r.m || r.src}<Src m={r.m} src={r.src} />{/if}
							{/if}
						</div>
					</li>
				{/each}
			</ol>
			<p class="small mute">{w.s4.simNote}</p>
		</div>
		{#if calDone}
			<div class="notice notice--ok ready">
				<span class="notice__icon" aria-hidden="true">✓</span>
				<div class="ready-body">
					<strong>{w.s4.ready}</strong>
					<div class="cluster">
						<a class="btn btn--primary btn--sm" href={href(lang, '/app/chat')}>{w.s4.firstChat}<Icon name="arrowRight" size={16} /></a>
						<a class="btn btn--secondary btn--sm" href={href(lang, '/app/result')}>{w.s4.seeResult}</a>
					</div>
				</div>
			</div>
		{/if}
	{/if}

	<div class="nav-row">
		<button type="button" class="btn btn--ghost" onclick={() => go(step - 1)} disabled={step === 0}>
			<Icon name="arrowLeft" size={16} />{t.common.back}
		</button>
		{#if step < 3}
			<button type="button" class="btn btn--primary" onclick={() => go(step + 1)}>
				{t.common.next}<Icon name="arrowRight" size={16} />
			</button>
		{:else}
			<a class="btn btn--primary" href={href(lang, '/app/chat')}>{w.finish}<Icon name="arrowRight" size={16} /></a>
		{/if}
	</div>
</section>

<style>
	.stepper {
		list-style: none;
		margin: 0 0 var(--sp-6);
		padding: 0;
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: var(--sp-2);
		counter-reset: none;
	}
	.st {
		width: 100%;
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding: var(--sp-3);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--bg-2);
		color: var(--text-mute);
		font: inherit;
		font-size: var(--fs-sm);
		text-align: left;
		cursor: pointer;
		position: relative;
		overflow: hidden;
	}
	.st:hover {
		border-color: var(--line-strong);
		color: var(--text-hi);
	}
	.st::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 2px;
		background: transparent;
	}
	.st[aria-current='step'] {
		color: var(--text-hi);
		border-color: var(--line-strong);
	}
	.st[aria-current='step']::after {
		background: var(--accent);
	}
	.st.done {
		color: var(--text);
	}
	.dot {
		display: grid;
		place-items: center;
		width: 1.625rem;
		height: 1.625rem;
		flex: none;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		font-size: var(--fs-xs);
	}
	.st[aria-current='step'] .dot {
		background: var(--accent);
		border-color: var(--accent);
		color: var(--on-accent);
	}
	.st.done .dot {
		color: var(--ok-ink);
		border-color: var(--ok);
	}
	.panel {
		display: grid;
		gap: var(--sp-5);
	}
	.panel > h2 {
		margin-top: calc(-1 * var(--sp-4));
		outline-offset: 4px;
	}
	.step-lead {
		font-size: var(--fs-base);
		max-width: 46rem;
	}
	.s1 {
		display: grid;
		gap: var(--sp-5);
	}
	fieldset {
		margin: 0;
		min-width: 0;
	}
	.lang,
	.consent {
		display: grid;
		gap: var(--sp-4);
		justify-items: start;
	}
	.consent > .always,
	.consent > .check {
		justify-self: stretch;
	}
	.always {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-3);
		padding: var(--sp-4);
		border-radius: var(--r-sm);
		background: var(--ok-soft);
	}
	.strong {
		color: var(--text-hi);
		font-weight: var(--fw-semibold);
	}
	.block {
		display: block;
		margin-top: var(--sp-1);
	}
	.ok-ic {
		color: var(--ok-ink);
		margin-top: 0.15rem;
	}
	.selftest {
		display: grid;
		gap: var(--sp-3);
	}
	.row-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
	}
	.checks {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-2);
		font-size: var(--fs-sm);
	}
	.checks li {
		display: flex;
		gap: var(--sp-2);
		align-items: flex-start;
	}
	.link {
		max-width: 16rem;
	}
	.recs {
		border: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
		gap: var(--sp-4);
	}
	.rec {
		display: grid;
		gap: var(--sp-2);
		align-content: start;
		cursor: pointer;
		padding: var(--sp-5);
		transition: border-color var(--dur-1) var(--ease-out);
	}
	.rec:hover {
		border-color: var(--line-strong);
	}
	.rec.sel {
		border-color: var(--accent-ink);
		box-shadow: var(--accent-glow);
	}
	.rec:has(input:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.rec-top {
		display: flex;
		align-items: center;
		gap: var(--sp-2);
	}
	.rec-top .badge {
		margin-left: auto;
	}
	.rec input {
		width: 1.1rem;
		height: 1.1rem;
		margin: 0;
		accent-color: var(--accent-ink);
	}
	.rec-name {
		font-size: var(--fs-lg);
		font-weight: var(--fw-semibold);
		color: var(--text-hi);
		letter-spacing: var(--tracking-tight);
	}
	.kv {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-2) var(--sp-4);
		margin-top: var(--sp-2);
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
		font-size: var(--fs-sm);
	}
	.k {
		color: var(--text-mute);
	}
	.v {
		color: var(--text-hi);
		text-align: right;
	}
	.lic-note {
		color: var(--warn-ink);
	}
	.cal {
		display: grid;
		gap: var(--sp-4);
	}
	.cal-steps {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		overflow: hidden;
	}
	.cal-row {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-4);
		padding: var(--sp-3) var(--sp-4);
		background: var(--bg-1);
		border-bottom: 1px solid var(--line);
	}
	.cal-row:last-child {
		border-bottom: 0;
	}
	.cal-row[data-state='run'] {
		background: var(--info-soft);
	}
	.cal-ix {
		color: var(--text-mute);
		font-size: var(--fs-xs);
		padding-top: 0.2rem;
	}
	.cal-row[data-state='ok'] .cal-ix {
		color: var(--ok-ink);
	}
	.cal-body {
		display: grid;
		gap: var(--sp-1);
		min-width: 0;
	}
	.cal-name {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-2);
		color: var(--text-hi);
		font-weight: var(--fw-medium);
		font-size: var(--fs-sm);
	}
	.ready-body {
		display: grid;
		gap: var(--sp-3);
	}
	.nav-row {
		display: flex;
		justify-content: space-between;
		gap: var(--sp-3);
		padding-top: var(--sp-5);
		border-top: 1px solid var(--line);
	}
	.btn:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}

	@media (max-width: 900px) {
		.stepper {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 480px) {
		.lbl {
			font-size: var(--fs-xs);
		}
	}
</style>
