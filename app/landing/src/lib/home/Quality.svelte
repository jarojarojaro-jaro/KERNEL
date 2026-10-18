<script lang="ts">
	/**
	 * Jakość as one visual idea: a KLD log-scale ruler (10⁻⁴ … 2).
	 * - Left: the decade 10⁻⁴–10⁻³, "the order of upstream's own noise". Our engine's dots (model
	 *   colour + shape) and upstream's run-to-run noise ticks (SHEET.correctness.quality, RTX 3060)
	 *   all sit in it; the per-model values live in the popover.
	 * - Right: what a real quality change looks like, for scale: other LFM2.5 formats vs Q8_0 on the
	 *   RTX 5060 Ti (SHEET.lfmFormats5060), labelled as another model and format.
	 * - A heat bracket spans our worst value → the smallest format change: the hero number "≈ 310×"
	 *   (computed, rounded down to two significant digits).
	 * Below: Qwen3.8-27B compact (3090 same script with the multiplier; XTX indicative, no multiplier;
	 * NVIDIA KLD in progress) and the bit-exact validation slot (BITEXACT_XTX, not in the product yet).
	 */
	import { heatOf } from '$lib/cards/explorer';
	import { reveal } from '$lib/fx/actions';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { BITEXACT_XTX, findCard, MODEL_INFO, SHEET, variantOf } from '$lib/data/measurements';
	import { fmtRatio, fmtTps } from '$lib/format';
	import { href, num, type Lang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { copy } from '$lib/site/copy';
	import { fill } from './data';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].quality);
	const q = SHEET.correctness.quality;
	const where = findCard('rtx-3060-12')?.name ?? '';
	const where5060 = findCard('rtx-5060-ti-16')?.name ?? '';

	/** Cropped log axis: just below the smallest value (0,00021) to just above the largest (1,183). */
	const LO = Math.log10(1.5e-4);
	const HI = Math.log10(1.6);
	const x = (v: number) => (Math.log10(v) - LO) / (HI - LO);
	const ticks = [-3, -2, -1, 0];
	const digits = (v: number) => Math.max(2, -Math.floor(Math.log10(v)) + 1);

	const ours = (['saluki', 'bonsai'] as const).map((k) => ({ k, name: MODEL_INFO[k].name, ...q[k] }));
	const fmts = SHEET.lfmFormats5060.filter((r) => r.md5Same !== null);
	const worstOurs = Math.max(...ours.map((r) => r.ours.v));
	const bestFmt = Math.min(...fmts.map((r) => r.kld.v));
	/** Rounded down to two significant digits: never overstated. */
	const ratio = (() => {
		const r = bestFmt / worstOurs;
		const p = 10 ** (Math.floor(Math.log10(r)) - 1);
		return Math.floor(r / p) * p;
	})();
	const fmtName = (file: string) => file.replace(/\s*\(.*\)$/, '');
	const oursSrc = ours.flatMap((r) => [r.ours.src, r.noise.src]);
	const zoneDetail = $derived(
		`${c.zoneNote} ${ours.map((r) => `${r.name}: ${c.ours} ${num(r.ours.v, lang, digits(r.ours.v))}, ${c.noise} ${num(r.noise.v, lang, digits(r.noise.v))}`).join('; ')}. ${fill(c.where, { card: where })}`
	);

	/** Qwen3.8-27B speed: baseline vs ours on the 3090 (same script) and the XTX (different scripts). */
	const qwenRows = (['rtx-3090', 'rx-7900-xtx'] as const).flatMap((id) => {
		const card = findCard(id);
		const run = card?.runs.find((r) => r.model === 'qwen38');
		const a = run && variantOf(run, run.before)?.decode;
		const b = run && variantOf(run, run.ours)?.decode;
		return card && run && a && b ? [{ card, run, a, b }] : [];
	});
	const bx = BITEXACT_XTX;
	const bxCard = findCard(bx.card)?.name ?? '';
	const bxChecks = $derived(
		c.qwen.valChecks.map((t) =>
			fill(t, {
				nmax: bx.nMax.v,
				long: bx.longPrompts.v.map((v) => (lang === 'en' ? v.replace(',', '.') : v)).join(' / '),
				det: bx.detScenarios.v,
				ops: bx.ops.v.map((o) => `${o.name} ${num(o.pass, lang, 0)}/${num(o.total, lang, 0)}`).join(' · ')
			})
		)
	);
	const bxSrc = [bx.src, bx.speed.bitexact.src, bx.speed.longCtx.bitexact.src];
	const bxLongCost = Math.round((bx.speed.longCtx.bitexact.v / bx.speed.longCtx.prod.v - 1) * 100);
</script>

<section id="quality" class="quality heat-top" aria-labelledby="quality-title">
	<div class="inner">
		<header class="head">
			<h2 id="quality-title" class="statement">{c.title}</h2>
			<!-- the whole point in one line: our difference vs the smallest format change -->
			<div class="hero-num">
				<p class="gl">{c.gapLabel}</p>
				<p class="gv">
					<span class="go">{num(worstOurs, lang, digits(worstOurs))}</span>
					<span class="gvs">vs</span>
					<span class="gf">{num(bestFmt, lang, 3)}</span>
				</p>
				<p class="gc"><span>{c.gapOurs}</span><span>{c.gapFmt}</span></p>
				<p class="lx">{fill(c.less, { x: num(ratio, lang, 0) })}</p>
			</div>
		</header>

		<figure class="ruler" use:reveal={{ threshold: 0.3 }}>
			<!-- for scale: format changes (another model), with labels above their markers -->
			<div class="plane">
				<div class="zone" style="--a:0; --b:{x(1e-3)}">
					<span class="zl">{c.zone} <SourceTip {lang} src={oursSrc} note={zoneDetail} /></span>
				</div>
				<div class="bracket" style="--a:{x(worstOurs)}; --b:{x(bestFmt)}" aria-hidden="true">
					<span class="bl">≈&nbsp;{num(ratio, lang, 0)}×</span>
				</div>
				{#each ours as r, i (r.k)}
					<span class="noise" style="--x:{x(r.noise.v)}; --d:{i * 90}ms" aria-hidden="true"><i>{num(r.noise.v, lang, digits(r.noise.v))}</i></span>
					<span class="dot" class:up={r.ours.v === worstOurs} style="--x:{x(r.ours.v)}; --d:{120 + i * 90}ms; --mc:{MODEL_STYLE[r.k].color}" aria-hidden="true">
						<ModelMark model={r.k} size="0.95rem" />
						<span class="dl"><b>{MODEL_STYLE[r.k].short.split(' ')[0]}</b> {num(r.ours.v, lang, digits(r.ours.v))}</span>
					</span>
				{/each}
				{#each fmts as r, i (r.file)}
					<span class="fmt" class:hi={i === 0} style="--x:{x(r.kld.v)}; --d:{350 + i * 120}ms" aria-hidden="true">
						<span class="fl"><ModelMark model="lfm25" size="0.7em" /> {fmtName(r.file)} <b>{num(r.kld.v, lang, 3)}</b>{#if r.kld.v > 1}<em>{' · '}{c.bad}</em>{/if}</span>
					</span>
				{/each}
				<div class="axis" aria-hidden="true">
					{#each ticks as t (t)}<span style="--t:{x(10 ** t)}">{num(10 ** t, lang, Math.max(0, -t))}</span>{/each}
				</div>
			</div>
			<p class="sr-only">{zoneDetail} {fmts.map((r) => `${fmtName(r.file)}: ${num(r.kld.v, lang, 3)}`).join(', ')}.</p>
			<figcaption class="caption">
				<span class="zcap"><i class="zsw"></i>{c.zone} <SourceTip {lang} src={oursSrc} note={zoneDetail} /></span>
				<span><ModelMark model="lfm25" size="0.7rem" /> {fill(c.fmt, { card: where5060 })} <SourceTip {lang} src={fmts.map((r) => r.kld.src)} /></span>
				<span class="ax">{c.axis}</span>
			</figcaption>
		</figure>

		<div class="below">
			<div class="qwen">
				<p class="qh"><ModelMark model="qwen38" size="0.75em" /> {MODEL_INFO.qwen38.name} <SourceTip {lang} src={qwenRows.flatMap((r) => [r.a.src, r.b.src, r.run.conditionsSrc])} note={qwenRows.map((r) => `${r.card.name}: ${r.run.metric[lang]} ${r.run.conditions[lang]}`).join(' — ')} /></p>
				{#each qwenRows as r (r.card.id)}
					<div class="qrow">
						<span class="qc">{r.card.short}</span>
						<span class="qv"><span class="steel">{fmtTps(r.a.v, lang)}</span> → <b>{fmtTps(r.b.v, lang)}</b> <small>t/s</small></span>
						{#if r.run.sameHarness}
							<span class="qg"><b class="speedup" style="--rh:{heatOf(r.b.v / r.a.v)}">{fmtRatio(r.b.v / r.a.v, lang)}</b> <small>{c.qwen.same}</small></span>
						{:else}
							<span class="qg"><small class="cross">{c.qwen.cross}</small></span>
						{/if}
					</div>
				{/each}
				<div class="qrow">
					<span class="qc">{c.qwen.kld}</span>
					<span class="pending">{c.qwen.kldPending}</span>
				</div>
			</div>

			<div class="val">
				<p class="vtag">{c.qwen.valTag}</p>
				<p class="vt"><ModelMark model={bx.model} size="0.6em" /> {fill(c.qwen.valTitle, { card: bxCard })}</p>
				<ul class="checks">
					{#each bxChecks as t, i (i)}<li><span class="ok" aria-hidden="true">✓</span>{t}</li>{/each}
				</ul>
				<div class="vbars" aria-hidden="true">
					{#each [{ k: c.qwen.valShort, bx: bx.speed.bitexact.v, pr: bx.speed.prod.v }, { k: fill(c.qwen.valLong, { ctx: bx.speed.longCtx.promptTokens.toLocaleString(lang === 'pl' ? 'pl-PL' : 'en-US') }), bx: bx.speed.longCtx.bitexact.v, pr: bx.speed.longCtx.prod.v }] as g (g.k)}
						{@const top = Math.max(g.bx, g.pr)}
						<div class="vg">
							<span class="vk">{g.k}</span>
							<span class="vrow"><span class="vn">{c.qwen.valBx}</span><span class="vb vb--bx" style="--w:{g.bx / top}"></span><b>{fmtTps(g.bx, lang)}</b></span>
							<span class="vrow"><span class="vn">{c.qwen.valProd}</span><span class="vb" style="--w:{g.pr / top}"></span><b>{fmtTps(g.pr, lang)}</b></span>
						</div>
					{/each}
				</div>
				<p class="vs">
					{fill(c.qwen.valSpeed, { a: fmtTps(bx.speed.bitexact.v, lang), b: fmtTps(bx.speed.prod.v, lang), ctx: bx.speed.longCtx.promptTokens.toLocaleString(lang === 'pl' ? 'pl-PL' : 'en-US'), la: fmtTps(bx.speed.longCtx.bitexact.v, lang), lb: fmtTps(bx.speed.longCtx.prod.v, lang), cost: `${bxLongCost > 0 ? '+' : '−'}${Math.abs(bxLongCost)} %` })}
					<SourceTip {lang} src={bxSrc} note="{MODEL_INFO.qwen38.name} {bx.quant} · {bx.run[lang]}. {fill(c.qwen.valSpeedNote, { script: bx.speed.script })}" />
				</p>
			</div>
		</div>

		<div class="foot">
			<p class="body">{c.body}</p>
			<a class="link" href={href(lang, '/methodology#quality')}>{c.link} <span aria-hidden="true">→</span></a>
		</div>
	</div>
</section>

<style>
	.quality {
		position: relative;
		background:
			radial-gradient(60% 50% at 85% 35%, rgb(255 122 26 / 0.07), transparent 70%),
			var(--bg-0);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		display: grid;
		gap: clamp(2rem, 4vw, 3.5rem);
	}
	.head {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(1.5rem, 4vw, 4rem);
		align-items: end;
	}
	.statement {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2.1rem, 0.8rem + 3vw, 4.2rem);
		font-weight: 800;
		font-stretch: 108%;
		line-height: 0.96;
		letter-spacing: -0.04em;
		color: var(--text-hi);
		text-wrap: balance;
	}
	.hero-num {
		display: grid;
		gap: 0.4rem;
		justify-items: end;
		text-align: right;
	}
	.gl {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.gv {
		margin: 0;
		display: flex;
		align-items: baseline;
		gap: 0.3em;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-size: clamp(2.6rem, 1.2rem + 4.2vw, 6rem);
		font-weight: 820;
		letter-spacing: -0.045em;
		line-height: 0.9;
	}
	.go {
		color: var(--text-hi);
	}
	.gvs {
		font-size: 0.38em;
		font-family: var(--font-mono);
		font-weight: 500;
		color: var(--text-mute);
		letter-spacing: 0.04em;
	}
	.gf {
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		padding-bottom: 0.08em;
	}
	.gc {
		margin: 0;
		display: flex;
		justify-content: flex-end;
		gap: 0.4rem 1.6rem;
		flex-wrap: wrap;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.gc span + span {
		color: var(--heat-4);
	}
	.lx {
		margin: 0.4rem 0 0;
		font-family: var(--font-display);
		font-size: clamp(1.3rem, 1rem + 0.9vw, 1.9rem);
		font-weight: 800;
		letter-spacing: -0.03em;
		color: var(--text-hi);
	}

	/* ---- the ruler: labels on the markers, no legend ---- */
	.ruler {
		margin: 0;
		display: grid;
		gap: 0.9rem;
		padding: clamp(1rem, 2.5vw, 1.75rem) clamp(1rem, 3vw, 2.25rem) clamp(0.9rem, 2vw, 1.25rem);
		border-radius: var(--r-xl);
		background: linear-gradient(180deg, rgb(255 255 255 / 0.02), transparent), var(--bg-1);
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.plane {
		position: relative;
		height: 11rem;
	}
	.plane::before {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 1.8rem;
		height: 1px;
		background: linear-gradient(90deg, var(--line-strong), rgb(255 122 26 / 0.6) 70%, var(--heat-2));
	}
	/* upstream's own noise: the decade the dots sit in */
	.zone {
		position: absolute;
		bottom: 1.8rem;
		left: calc(var(--a) * 100%);
		width: calc((var(--b) - var(--a)) * 100%);
		height: 6.4rem;
		border-radius: 8px 8px 0 0;
		background: linear-gradient(180deg, rgb(237 234 227 / 0.02), rgb(237 234 227 / 0.08));
		border: 1px dashed rgb(237 234 227 / 0.28);
		border-bottom: 0;
	}
	.zl {
		position: absolute;
		left: 0.5rem;
		top: 0.4rem;
		right: 0.3rem;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.3rem;
		font-family: var(--font-mono);
		font-size: 0.62rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		line-height: 1.25;
		color: var(--text);
	}
	.noise,
	.dot,
	.fmt {
		position: absolute;
		left: calc(var(--x) * 100%);
	}
	.noise {
		bottom: 1.8rem;
		width: 2px;
		height: 1.1rem;
		margin-left: -1px;
		background: var(--before);
	}
	.noise i {
		display: none;
	}
	.dot {
		bottom: calc(1.8rem + 1.5rem);
		display: grid;
		place-items: center;
		width: 1.7rem;
		height: 1.7rem;
		margin-left: -0.85rem;
		border-radius: 50%;
		background: color-mix(in srgb, var(--mc) 18%, var(--bg-1));
		box-shadow:
			0 0 0 1px color-mix(in srgb, var(--mc) 70%, transparent),
			0 0 18px color-mix(in srgb, var(--mc) 55%, transparent);
	}
	.dot.up {
		bottom: calc(1.8rem + 3.2rem);
	}
	.dot::after {
		content: '';
		position: absolute;
		top: 100%;
		left: 50%;
		width: 1px;
		height: 1.5rem;
		background: linear-gradient(color-mix(in srgb, var(--mc) 70%, transparent), color-mix(in srgb, var(--mc) 15%, transparent));
	}
	.dot.up::after {
		height: 3.2rem;
	}
	/* the label sits right next to its marker, in the model's colour */
	.dl {
		position: absolute;
		left: calc(100% + 0.4rem);
		top: 50%;
		transform: translateY(-50%);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-hi);
		white-space: nowrap;
	}
	.dl b {
		font-weight: 600;
		color: var(--mc);
	}
	.fmt {
		bottom: 1.8rem;
		height: 7.2rem;
		border-left: 2px dashed var(--heat-3);
	}
	.fmt:not(.hi) {
		height: 4.4rem;
		border-left-color: var(--heat-2);
	}
	.fl {
		position: absolute;
		right: 0.5rem;
		top: -0.2rem;
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.1rem 0.3rem;
		border-radius: 4px;
		background: var(--bg-1);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
		white-space: nowrap;
	}
	.fl b {
		color: var(--text-hi);
		font-weight: 500;
	}
	.fl em {
		font-style: normal;
		color: var(--text-mute);
	}
	/* the gap, in heat: our worst value → the smallest format change */
	.bracket {
		position: absolute;
		bottom: calc(1.8rem + 7.9rem);
		left: calc(var(--a) * 100%);
		width: calc((var(--b) - var(--a)) * 100%);
		height: 0.9rem;
		border: 2px solid transparent;
		border-bottom: 0;
		border-image: linear-gradient(90deg, var(--heat-2), var(--heat-3) 50%, var(--heat-4)) 1;
		filter: drop-shadow(0 0 6px rgb(255 122 26 / 0.6));
		transform-origin: 0 50%;
	}
	.bl {
		position: absolute;
		left: 50%;
		bottom: calc(100% + 0.2rem);
		transform: translateX(-50%);
		font-family: var(--font-display);
		font-size: clamp(1.1rem, 0.9rem + 0.6vw, 1.5rem);
		font-weight: 820;
		letter-spacing: -0.03em;
		color: var(--heat-5);
		white-space: nowrap;
	}
	.axis {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 1.4rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.axis span {
		position: absolute;
		left: calc(var(--t) * 100%);
		transform: translateX(-50%);
	}
	.axis span:last-child {
		transform: translateX(-100%);
	}
	@media (prefers-reduced-motion: no-preference) {
		/* resting state final; entering view replays the markers dropping onto the scale */
		:global(html.js) .ruler:global([data-in]) .dot,
		:global(html.js) .ruler:global([data-in]) .noise,
		:global(html.js) .ruler:global([data-in]) .fmt {
			animation: mark-in 0.8s var(--ease-spring) var(--d) backwards;
		}
		:global(html.js) .ruler:global([data-in]) .bracket {
			animation: bracket-in 1.1s var(--ease-out) 0.5s backwards;
		}
	}
	@keyframes mark-in {
		from {
			transform: translate3d(0, -1.5rem, 0) scale(0.3);
		}
	}
	@keyframes bracket-in {
		from {
			transform: scaleX(0);
		}
	}
	.caption {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.4rem 1.2rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.caption span {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
	}
	.zcap {
		display: none !important;
	}
	.zsw {
		width: 0.9rem;
		height: 0.65rem;
		border: 1px dashed rgb(237 234 227 / 0.45);
		background: rgb(237 234 227 / 0.06);
	}
	.caption .ax {
		color: var(--text-mute);
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}
	/* bit-exact speed: two tiny pairs of bars */
	.vbars {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.9rem 1.4rem;
	}
	.vg {
		display: grid;
		gap: 0.3rem;
		min-width: 0;
	}
	.vk {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.vrow {
		display: grid;
		grid-template-columns: 5.2rem minmax(0, 1fr) auto;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.vb {
		height: 6px;
		width: calc(var(--w) * 100%);
		border-radius: var(--r-pill);
		background: var(--before);
	}
	.vb--bx {
		background: var(--text-hi);
	}
	.vrow b {
		font-weight: 500;
		color: var(--text-hi);
	}

	/* ---- below: Qwen + validation ---- */
	.below {
		display: grid;
		grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
		gap: clamp(1rem, 2.5vw, 1.75rem);
	}
	.qwen,
	.val {
		display: grid;
		gap: 0.85rem;
		align-content: start;
		padding: clamp(1.25rem, 2.5vw, 1.75rem);
		border-radius: var(--r-xl);
		background: var(--bg-1);
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.qh {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 700;
		color: var(--text-hi);
	}
	.qrow {
		display: grid;
		grid-template-columns: 7.5rem minmax(0, 1fr) auto;
		align-items: baseline;
		gap: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--line);
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.qc {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.qv b {
		font-weight: 500;
		color: var(--text-hi);
	}
	.steel {
		color: var(--before);
	}
	.qv small,
	.qg small {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.qg b {
		font-size: var(--fs-lg);
	}
	.cross {
		color: var(--text) !important;
	}
	.pending {
		grid-column: 2 / -1;
		color: var(--text-mute);
	}
	/* in validation: secondary, quiet dashed frame = not a product claim yet */
	.val {
		background: transparent;
		box-shadow: none;
		border: 1px dashed var(--line-strong);
		gap: 0.6rem;
	}
	.vtag {
		justify-self: start;
		padding: 0.15rem 0.55rem;
		border: 1px dashed var(--text-mute);
		border-radius: var(--r-pill);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text);
	}
	.vt {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 700;
		font-size: var(--fs-md);
		color: var(--text);
	}
	.checks {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0.4rem;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.checks li {
		display: flex;
		gap: 0.55rem;
	}
	.ok {
		color: var(--text);
		font-weight: 700;
	}
	.vs {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--line);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.foot {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--sp-4);
	}
	.body {
		max-width: 60ch;
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.link {
		font-weight: 650;
		color: var(--text-hi);
		text-decoration-color: var(--heat-3);
		text-underline-offset: 0.25em;
	}
	.link:hover {
		color: var(--heat-4);
	}
	@media (max-width: 900px) {
		.head,
		.below {
			grid-template-columns: minmax(0, 1fr);
		}
		.hero-num {
			justify-items: start;
			text-align: left;
		}
		.gc {
			justify-content: flex-start;
		}
	}
	@media (max-width: 640px) {
		.axis span:nth-child(even) {
			display: none;
		}
		.qrow {
			grid-template-columns: minmax(0, 1fr) auto;
		}
		.qv {
			grid-column: 1 / -1;
			order: 3;
		}
		.gc {
			justify-content: flex-start;
		}
		.vbars {
			grid-template-columns: minmax(0, 1fr);
		}
		.zl {
			display: none;
		}
		.zcap {
			display: inline-flex !important;
		}
		/* narrow: format labels stacked above the dots' labels, the bracket above them */
		.plane {
			height: 12.5rem;
		}
		.fmt {
			height: 8.6rem;
		}
		.fmt:not(.hi) {
			height: 6.2rem;
		}
		.bracket {
			bottom: calc(1.8rem + 9.4rem);
		}
	}
</style>
