<script lang="ts">
	import { onMount } from 'svelte';
	import { CARDS, MODEL_INFO, variantOf } from '$lib/data/measurements';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { fmtRatio } from '$lib/format';
	import { visible } from '$lib/fx/actions';
	import { onFrame, reducedMotion } from '$lib/fx/motion';
	import { num, type Lang } from '$lib/i18n';
	import { COPY } from './copy';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(COPY[lang]);

	const card = CARDS.find((x) => x.id === 'rx-7900-xtx')!;
	const run = card.runs.find((r) => r.model === 'qwen38')!;
	const before = variantOf(run, run.before)!.decode!.v;
	const after = variantOf(run, run.ours)!.decode!.v;

	/** Seconds of generation shown per loop; both lanes run at their measured token rate. */
	const LOOP = 9;
	let t = $state(0);
	let on = false;
	let reduce = $state(false);

	const words = $derived(c.q.text.repeat(8).split(' '));
	/** Words written after `sec` seconds at `tps` tokens per second (Qwen3 tokens per word). */
	const shown = (tps: number, sec: number) => words.slice(0, Math.floor((tps * sec) / TOK_PER_WORD[lang])).join(' ');
	const lanes = $derived([
		{ key: 'a0', label: c.q.upstream, tps: before, text: shown(before, t), tok: Math.floor(before * t) },
		{ key: 'ours', label: c.q.ours, tps: after, text: shown(after, t), tok: Math.floor(after * t) }
	]);

	onMount(() => {
		reduce = reducedMotion();
		if (reduce) {
			t = LOOP;
			return;
		}
		return onFrame((dt) => {
			if (!on) return;
			t = t + dt > LOOP + 1.5 ? 0 : t + dt;
		});
	});
</script>

<div class="race" use:visible={(v) => (on = v)}>
	<dl class="same panel">
		<dt class="panel-h">{c.q.same}</dt>
		<div><dt>{c.q.card}</dt><dd>{card.name}<span>{card.arch} · {card.vramGB} GB</span></dd></div>
		<div><dt>{c.q.model}</dt><dd>{MODEL_INFO[run.model].name}<span>{run.quant}</span></dd></div>
		<div><dt>{c.q.file}</dt><dd class="mono">{num(run.file!.v, lang, 2)} GB<span>{lang === 'pl' ? 'ten sam plik GGUF' : 'the same GGUF file'}</span></dd></div>
		<div><dt>{c.q.ctx}</dt><dd>{c.q.ctxV}</dd></div>
	</dl>

	<div class="lanes">
		<p class="panel-h live"><span class="dot" aria-hidden="true"></span>{c.q.live}</p>
		{#each lanes as l (l.key)}
			<div class="lane {l.key}">
				<div class="lane-top">
					<span class="lab">{l.label}</span>
					<span class="rate mono"><b>{num(l.tps, lang, 1)}</b> t/s</span>
				</div>
				<p class="stream" aria-hidden="true"><span>{l.text}</span><i class="caret"></i></p>
				<div class="meter" aria-hidden="true"><i style="transform:scaleX({Math.min(1, l.tok / (after * LOOP))})"></i></div>
			</div>
		{/each}
		<p class="ratio"><span class="x speedup">{fmtRatio(after / before, lang)}</span><span class="mute">{lang === 'pl' ? 'ten sam sprzęt, ten sam plik, ten sam skrypt pomiarowy' : 'same hardware, same file, same measurement script'}</span></p>
	</div>
</div>

<style>
	.race {
		display: grid;
		grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.6fr);
		gap: var(--sp-6);
		align-items: stretch;
	}
	.same {
		margin: 0;
		display: grid;
		align-content: start;
		gap: 0;
	}
	.same > div {
		display: grid;
		gap: 0.15rem;
		padding: var(--sp-3) 0;
		border-top: 1px solid var(--line);
	}
	.same dt:not(.panel-h) {
		font-size: var(--fs-2xs);
		font-family: var(--font-mono);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.same dd {
		margin: 0;
		color: var(--text-hi);
		font-weight: 560;
		display: grid;
	}
	.same dd span {
		font-weight: 400;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		font-family: var(--font-sans, inherit);
	}
	.lanes {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
	}
	.live {
		display: flex;
		align-items: center;
		gap: var(--sp-2);
	}
	.dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: var(--heat-3);
		box-shadow: 0 0 10px var(--heat-3);
		animation: pulse 1.6s ease-in-out infinite;
	}
	@keyframes pulse {
		50% {
			opacity: 0.35;
		}
	}
	.lane {
		display: grid;
		gap: var(--sp-2);
		padding: var(--sp-4) var(--sp-5);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background: var(--bg-1);
	}
	.lane.ours {
		border-color: color-mix(in srgb, var(--heat-3) 50%, var(--line));
		background:
			radial-gradient(60% 120% at 100% 0%, color-mix(in srgb, var(--heat-3) 12%, transparent), transparent 70%),
			var(--bg-1);
		box-shadow: 0 30px 80px -50px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.lane-top {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--sp-3);
	}
	.lab {
		font-weight: 600;
		color: var(--text-hi);
	}
	.rate {
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.rate b {
		font-size: var(--fs-xl);
		color: var(--before);
		font-weight: 600;
	}
	.ours .rate b {
		color: var(--accent-ink);
	}
	.stream {
		margin: 0;
		height: 4.8em;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		font-size: var(--fs-sm);
		line-height: 1.6;
		color: var(--text);
		mask-image: linear-gradient(180deg, transparent, #000 45%);
	}
	.stream span {
		display: block;
	}
	.caret {
		display: inline-block;
		width: 0.5ch;
		height: 1em;
		background: var(--before);
		vertical-align: -0.15em;
	}
	.ours .caret {
		background: var(--heat-4);
		box-shadow: 0 0 8px var(--heat-3);
	}
	.meter {
		height: 3px;
		border-radius: 3px;
		background: var(--bg-3);
		overflow: hidden;
	}
	.meter i {
		display: block;
		height: 100%;
		transform-origin: left;
		background: var(--before);
	}
	.ours .meter i {
		background: var(--heat-ramp-hot);
	}
	.ratio {
		margin: 0;
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: var(--sp-2) var(--sp-4);
	}
	.x {
		font-size: clamp(2.4rem, 1.6rem + 3vw, 4rem);
		font-weight: 650;
		letter-spacing: -0.04em;
		line-height: 1;
	}
	.mute {
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	@media (max-width: 860px) {
		.race {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.dot {
			animation: none;
		}
	}
</style>
