<script lang="ts">
	/**
	 * Jakość: one log-scale KLD meter (1e-4 … 2). Top lane: our engine vs upstream next to upstream's
	 * own run-to-run noise (SHEET.correctness.quality, RTX 3060): four marks bunched at the far left.
	 * Bottom lane, for scale: what a real quality change looks like on the same sheet: other LFM2.5
	 * formats vs Q8_0 on the RTX 5060 Ti (SHEET.lfmFormats5060), clearly labelled as another model
	 * and format. The badge says "the order of upstream's own noise" and cites the report's line; we
	 * do not draw a tolerance band our values would have to sit in. The ratio is computed (smallest
	 * format KLD ÷ our largest KLD) and labelled "≈". Markers carry the model's identity colour + shape.
	 * Below: Qwen3.8-27B: speed on the 3090 (same script, with the multiplier) and the XTX (different
	 * scripts: labelled, no multiplier), its NVIDIA KLD marked "in progress", and the bit-exact
	 * validation slot (BITEXACT_XTX, dashed = not a product claim yet).
	 */
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

	const LO = -4;
	const HI = Math.log10(2);
	const x = (v: number) => (Math.log10(v) - LO) / (HI - LO);
	const ticks = [-4, -3, -2, -1, 0];
	const digits = (v: number) => Math.max(2, -Math.floor(Math.log10(v)) + 1);

	const ours = (['saluki', 'bonsai'] as const).map((k) => ({ k, name: MODEL_INFO[k].name, ...q[k] }));
	const fmts = SHEET.lfmFormats5060.filter((r) => r.md5Same !== null);
	const worstOurs = Math.max(...ours.map((r) => r.ours.v));
	const bestFmt = Math.min(...fmts.map((r) => r.kld.v));
	/** Rounded down to two significant digits: "≈ 310×", never overstated. */
	const ratio = (() => {
		const r = bestFmt / worstOurs;
		const p = 10 ** (Math.floor(Math.log10(r)) - 1);
		return Math.floor(r / p) * p;
	})();
	const fmtName = (file: string) => file.replace(/\s*\(.*\)$/, '');

	/** Qwen3.8-27B speed: baseline vs ours on the 3090 (same script) and the XTX (different scripts). */
	const qwenRows = (['rtx-3090', 'rx-7900-xtx'] as const).flatMap((id) => {
		const card = findCard(id);
		const run = card?.runs.find((r) => r.model === 'qwen38');
		const a = run && variantOf(run, run.before)?.decode;
		const b = run && variantOf(run, run.ours)?.decode;
		return card && run && a && b ? [{ card, run, a, b }] : [];
	});
	const qMax = Math.max(...qwenRows.map((r) => r.b.v));
	const bx = BITEXACT_XTX;
	const bxCard = findCard(bx.card)?.name ?? '';
</script>

<section id="quality" class="quality" aria-labelledby="quality-title">
	<div class="inner">
		<header class="head">
			<h2 id="quality-title" class="statement">{c.title}</h2>
		</header>
		<div class="board">
			<div class="word">
				<span class="kld" aria-hidden="true">{c.kld}</span>
				<p class="def"><b>{c.kld}</b> — {c.kldDef}</p>
				<p class="less">
					<span class="lx">{fill(c.less, { x: num(ratio, lang, 0) })}</span>
					<span class="ln">{c.lessNote}</span>
				</p>
			</div>
			<figure class="meter" use:reveal={{ threshold: 0.3 }}>
				<div class="lane">
					<div class="lh">
						<span class="lt">{fill(c.rowOurs, { card: where })}</span>
						<span class="badge">{c.verdict}</span>
						<SourceTip {lang} src={ours.flatMap((r) => [r.ours.src, r.noise.src])} note="{c.verdictNote} {fill(c.where, { card: where })}" />
					</div>
					<div class="track">
						{#each ours as r, i (r.k)}
							<span class="mk mk--noise" style="--x:{x(r.noise.v)}; --d:{i * 120}ms; --mc:{MODEL_STYLE[r.k].color}"></span>
							<span class="mk mk--ours" style="--x:{x(r.ours.v)}; --d:{i * 120 + 60}ms; --mc:{MODEL_STYLE[r.k].color}"><span class="cap"><ModelMark model={r.k} size="0.7rem" /></span></span>
						{/each}
					</div>
					<ul class="vals">
						{#each ours as r (r.k)}
							<li>
								<span class="vn"><ModelMark model={r.k} size="0.75em" /> {r.name}</span>
								<span><i class="sw sw--ours"></i>{c.ours} <b>{num(r.ours.v, lang, digits(r.ours.v))}</b></span>
								<span><i class="sw sw--noise"></i>{c.noise} <b class="steel">{num(r.noise.v, lang, digits(r.noise.v))}</b></span>
							</li>
						{/each}
					</ul>
				</div>
				<div class="lane lane--fmt">
					<div class="lh">
						<span class="lt">{fill(c.rowFmt, { card: where5060 })}</span>
						<SourceTip {lang} src={fmts.map((r) => r.kld.src)} />
					</div>
					<div class="track">
						{#each fmts as r, i (r.file)}
							<span class="mk mk--fmt" style="--x:{x(r.kld.v)}; --d:{300 + i * 140}ms; --mc:{MODEL_STYLE.lfm25.color}">
								<span class="fl"><ModelMark model="lfm25" size="0.7em" /> {fmtName(r.file)} <b>{num(r.kld.v, lang, 3)}</b>{#if r.kld.v > 1}<em>{' · '}{c.bad}</em>{/if}</span>
							</span>
						{/each}
					</div>
				</div>
				<div class="axis" aria-hidden="true">
					{#each ticks as t (t)}<span style="--t:{x(10 ** t)}">{num(10 ** t, lang, Math.max(0, -t))}</span>{/each}
				</div>
				<figcaption>{c.axis}</figcaption>
			</figure>
		</div>
		<div class="qwen">
			<h3 class="qt"><ModelMark model="qwen38" size="0.5em" /> {c.qwen.title} <span class="qn">{MODEL_INFO.qwen38.name}</span></h3>
			<div class="qgrid">
				<div class="qbox">
					<p class="qh">{c.qwen.speed}</p>
					{#each qwenRows as r (r.card.id)}
						<div class="qrow" style="--a:{r.a.v / qMax}; --b:{r.b.v / qMax}">
							<p class="qc">
								<b>{r.card.name}</b>
								<span class="qq">{r.run.quant}</span>
								{#if r.run.sameHarness}
									<span class="speedup qg">{fmtRatio(r.b.v / r.a.v, lang)}</span>
								{/if}
								<SourceTip {lang} src={[r.a.src, r.b.src, r.run.conditionsSrc]} note="{r.run.metric[lang]} {r.run.conditions[lang]}." />
							</p>
							<span class="qbar qbar--a" aria-hidden="true"></span>
							<span class="qbar qbar--b" aria-hidden="true"></span>
							<p class="qv">
								<span>{c.qwen.typical} <b class="steel">{fmtTps(r.a.v, lang)}</b></span>
								<span>{c.qwen.ours} <b>{fmtTps(r.b.v, lang)}</b> t/s</span>
								<span class="qs" class:cross={!r.run.sameHarness}>{r.run.sameHarness ? c.qwen.same : c.qwen.cross}</span>
							</p>
						</div>
					{/each}
					<p class="qk"><span>{c.qwen.kld}</span><span class="pending">{c.qwen.kldPending}</span></p>
				</div>
				<div class="qbox val">
					<p class="vtag">{c.qwen.valTag}</p>
					<p class="vt">{fill(c.qwen.valTitle, { card: bxCard })}</p>
					<p class="vb">{fill(c.qwen.valBody, { md5: bx.md5.slice(0, 8), chars: num(bx.chars, lang, 0) })}</p>
					<p class="vc">{MODEL_INFO.qwen38.name} {bx.quant} · {bx.conditions[lang]}</p>
					<p class="vp">{c.qwen.valPending} <SourceTip {lang} src={[bx.src, bx.pendingSrc]} note="md5 {bx.md5}" /></p>
				</div>
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
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		border-top: 1px solid var(--line);
		background:
			radial-gradient(50% 60% at 15% 100%, rgb(125 135 148 / 0.08), transparent 70%),
			var(--bg-0);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		gap: clamp(2rem, 4vw, 3.5rem);
	}
	.head {
		display: grid;
		gap: var(--sp-5);
	}
	.statement {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2.2rem, 0.9rem + 4vw, 5.2rem);
		font-weight: 760;
		font-stretch: 100%;
		line-height: 0.98;
		letter-spacing: -0.035em;
		color: var(--text-hi);
		text-wrap: balance;
		max-width: 20ch;
	}
	.board {
		display: grid;
		grid-template-columns: minmax(0, 0.75fr) minmax(0, 1.45fr);
		gap: clamp(2rem, 5vw, 5rem);
		align-items: center;
	}
	.word {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
	}
	/* the acronym as the headline object: solid, bone fading into the page (no outlines) */
	.kld {
		font-family: var(--font-display);
		font-size: clamp(5rem, 2rem + 11vw, 14rem);
		font-weight: 860;
		font-stretch: 125%;
		letter-spacing: -0.05em;
		line-height: 0.8;
		background: linear-gradient(180deg, var(--text-hi) 20%, rgb(237 234 227 / 0.12));
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.def {
		max-width: 36ch;
		color: var(--text);
		line-height: 1.5;
	}
	.def b {
		color: var(--text-hi);
	}
	.less {
		display: grid;
		gap: 0.2rem;
		margin-top: var(--sp-3);
		padding-top: var(--sp-4);
		border-top: 1px solid var(--line);
	}
	.lx {
		font-family: var(--font-display);
		font-size: clamp(2rem, 1rem + 2.6vw, 3.4rem);
		font-weight: 820;
		font-stretch: 115%;
		letter-spacing: -0.035em;
		color: var(--text-hi);
		line-height: 1;
	}
	.ln {
		font-size: var(--fs-sm);
		color: var(--text-mute);
		max-width: 34ch;
	}
	.meter {
		margin: 0;
		display: grid;
		gap: clamp(1.75rem, 3vw, 2.5rem);
		padding: clamp(1.5rem, 3vw, 2.5rem);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-1);
	}
	.lane {
		display: grid;
		gap: var(--sp-3);
	}
	.lh {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
	}
	.lt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text);
	}
	.badge {
		padding: 0.2rem 0.6rem;
		border: 1px solid var(--text-hi);
		border-radius: var(--r-pill);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-hi);
	}
	.track {
		position: relative;
		height: 3.4rem;
		border-bottom: 1px solid var(--line-strong);
		background: repeating-linear-gradient(90deg, rgb(237 234 227 / 0.07) 0 1px, transparent 1px calc(100% / 4.3));
	}
	.mk {
		position: absolute;
		bottom: 0;
		left: calc(var(--x) * 100%);
		width: 2px;
		margin-left: -1px;
	}
	/* our engine: a solid line in the model's colour, capped with the model's shape */
	.mk--ours {
		height: 100%;
		background: var(--mc);
		box-shadow: 0 0 10px color-mix(in srgb, var(--mc) 60%, transparent);
	}
	.cap {
		position: absolute;
		bottom: 100%;
		left: 50%;
		transform: translate(-50%, -2px);
		display: flex;
	}
	/* upstream's own noise: a steel mark with a dot head */
	.mk--noise {
		height: 72%;
		background: var(--before);
	}
	.mk--noise::before {
		content: '';
		position: absolute;
		top: -4px;
		left: -3px;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--before);
	}
	/* another model and format: a dashed steel marker with its label above */
	.mk--fmt {
		height: 100%;
		border-left: 2px dashed var(--mc);
		width: 0;
	}
	.fl {
		position: absolute;
		top: -0.2rem;
		right: 0.5rem;
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
	.lane--fmt .track {
		height: 4.6rem;
	}
	/* labels sit left of their marker on two rows; the upper one masks the lines it crosses */
	.lane--fmt .mk--fmt:first-child .fl {
		top: 2.3rem;
	}
	.lane--fmt .mk--fmt:not(:first-child) .fl {
		padding: 0.1rem 0.4rem;
		background: var(--bg-1);
		z-index: 1;
	}
	.vals {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.vals li {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-1) var(--sp-5);
	}
	.vn {
		min-width: 13rem;
		color: var(--text);
		font-family: var(--font-sans);
		font-weight: 650;
	}
	.vals span {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		white-space: nowrap;
	}
	.vals b {
		font-weight: 500;
		color: var(--text-hi);
	}
	.vals b.steel {
		color: var(--before);
	}
	.sw {
		display: inline-block;
		flex: none;
	}
	.sw--ours {
		width: 2px;
		height: 0.9rem;
		background: var(--text-hi);
	}
	.vn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
	}
	/* ---- Qwen3.8-27B: speed on two cards + the bit-exact validation slot ---- */
	.qwen {
		display: grid;
		gap: var(--sp-5);
		padding-top: var(--sp-6);
		border-top: 1px solid var(--line);
	}
	.qt {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.8rem;
		font-family: var(--font-display);
		font-size: clamp(1.5rem, 1rem + 1.5vw, 2.4rem);
		font-weight: 780;
		letter-spacing: -0.03em;
		color: var(--text-hi);
	}
	.qn {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		font-weight: 400;
		letter-spacing: 0.04em;
		color: var(--text-mute);
	}
	.qgrid {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: var(--sp-5);
	}
	.qbox {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
		padding: clamp(1.25rem, 2.5vw, 2rem);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-1);
	}
	.qh,
	.vtag {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	.qrow {
		display: grid;
		gap: 0.35rem;
	}
	.qc {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.3rem 0.7rem;
		color: var(--text);
	}
	.qc b {
		color: var(--text-hi);
		font-weight: 650;
	}
	.qq {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.qg {
		font-size: var(--fs-lg);
	}
	.qbar {
		display: block;
		height: 6px;
		border-radius: var(--r-pill);
		transform-origin: 0 50%;
	}
	.qbar--a {
		width: calc(var(--a) * 100%);
		background: var(--before);
	}
	.qbar--b {
		width: calc(var(--b) * 100%);
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 10px rgb(255 122 26 / 0.4);
	}
	.qv {
		display: flex;
		flex-wrap: wrap;
		gap: 0.2rem 1.2rem;
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.qv b {
		font-weight: 500;
		color: var(--text-hi);
	}
	.qv b.steel {
		color: var(--before);
	}
	.qs.cross {
		color: var(--text);
	}
	.qk {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--sp-2);
		padding-top: var(--sp-3);
		border-top: 1px dashed var(--line-strong);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.pending {
		color: var(--text-mute);
	}
	/* in validation: dashed frame = not a product claim yet */
	.val {
		border-style: dashed;
		border-color: var(--line-strong);
		background: transparent;
	}
	.vtag {
		justify-self: start;
		padding: 0.2rem 0.6rem;
		border: 1px dashed var(--text);
		border-radius: var(--r-pill);
		color: var(--text);
	}
	.vt {
		font-family: var(--font-display);
		font-size: var(--fs-xl);
		font-weight: 760;
		letter-spacing: -0.02em;
		color: var(--text-hi);
	}
	.vb {
		color: var(--text);
		line-height: 1.5;
	}
	.vc {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.vp {
		font-size: var(--fs-sm);
		color: var(--text-mute);
		line-height: 1.5;
	}
	.sw--noise {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--before);
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .meter:not([data-in]) .mk {
			left: 0;
			opacity: 0;
		}
		.mk {
			transition:
				left 1.3s var(--ease-out) var(--d),
				opacity 0.3s var(--d);
		}
	}
	.axis {
		position: relative;
		height: 1.2rem;
		margin-top: calc(-1 * var(--sp-5));
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.axis span {
		position: absolute;
		left: calc(var(--t) * 100%);
		transform: translateX(-50%);
		white-space: nowrap;
	}
	.axis span:first-child {
		transform: none;
	}
	figcaption {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	.foot {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: end;
		gap: var(--sp-6);
	}
	.body {
		font-size: clamp(1.05rem, 0.9rem + 0.4vw, 1.3rem);
		line-height: 1.5;
		color: var(--text);
		max-width: 56ch;
	}
	.link {
		font-weight: 650;
		color: var(--text-hi);
		white-space: nowrap;
	}
	@media (max-width: 640px) {
		.axis span:nth-child(even) {
			display: none;
		}
	}
	@media (max-width: 900px) {
		.board,
		.qgrid,
		.foot {
			grid-template-columns: minmax(0, 1fr);
		}
		.vn {
			min-width: 0;
			flex-basis: 100%;
		}
	}
</style>
