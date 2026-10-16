<script lang="ts">
	import { onMount } from 'svelte';
	import { M } from '$lib/data/measurements';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { currentLang, href, num } from '$lib/i18n';
	import { copy } from './copy';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang].duel);
	const words = $derived(t.text.split(/\s+/).length);
	const totalTok = $derived(Math.round(words * TOK_PER_WORD[lang]));

	const lanes = $derived([
		{ key: 'before', title: t.left, sub: t.leftSub, tps: M.qwenUpstreamVulkanPlain.value },
		{ key: 'after', title: t.right, sub: t.rightSub, tps: M.qwenOursMtp.value }
	]);
	const slowest = $derived(totalTok / Math.min(...lanes.map((l) => l.tps)));

	const HOLD = 2.8; // seconds the finished state stays on screen before the loop restarts
	let elapsed = $state(0);
	let playing = $state(false);
	let loop = $state(true);
	let visible = $state(true);
	let root: HTMLElement | undefined = $state();

	onMount(() => {
		const reduce = matchMedia('(prefers-reduced-motion: reduce)');
		if (reduce.matches) {
			elapsed = slowest; // static final frame, nothing moves until the user presses play
			loop = false;
		} else playing = true;

		const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting), { threshold: 0.15 });
		if (root) io.observe(root);

		let last = performance.now();
		let raf = 0;
		const frame = (now: number) => {
			const dt = Math.min(0.1, (now - last) / 1000);
			last = now;
			if (playing && visible && !document.hidden) {
				elapsed += dt;
				if (elapsed >= slowest + (loop ? HOLD : 0)) {
					if (loop) elapsed = 0;
					else {
						elapsed = slowest;
						playing = false;
					}
				}
			}
			raf = requestAnimationFrame(frame);
		};
		raf = requestAnimationFrame(frame);
		return () => {
			cancelAnimationFrame(raf);
			io.disconnect();
		};
	});

	function toggle() {
		if (!playing && elapsed >= slowest) elapsed = 0;
		playing = !playing;
	}

	const progress = (tps: number) => Math.min(1, (elapsed * tps) / totalTok);
	const secs = (tps: number) => Math.min(elapsed, totalTok / tps);
</script>

<figure class="duel" bind:this={root} aria-labelledby="duel-cap">
	<p class="sr-only">{t.srSummary}</p>
	<div class="frame hud" aria-hidden="true">
		<div class="top">
			<span class="overline">{t.prompt}</span>
			<span class="meta num">{totalTok} {t.tokens}</span>
		</div>
		<div class="lanes">
			{#each lanes as l (l.key)}
				{@const p = progress(l.tps)}
				{@const shown = Math.floor(t.text.length * p)}
				<div class="lane {l.key}" class:done={p >= 1}>
					<div class="lane-head">
						<span class="led"></span>
						<span class="name">{l.title}</span>
						<span class="clock num">
							<span class="tag" class:pending={p < 1}>{t.done}</span>
							{num(secs(l.tps), lang)} s
						</span>
						<span class="sub">{l.sub}</span>
					</div>
					<p class="out">
						{t.text.slice(0, shown)}<span class="caret" class:hide={p >= 1}></span><span class="ghost">{t.text.slice(shown)}</span>
					</p>
					<div class="readout">
						<div class="rate">
							<span class="val num">{num(l.tps, lang)}</span><span class="unit">t/s</span>
							<span class="wps num">≈ {num(l.tps / TOK_PER_WORD[lang], lang, 0)} {t.wps}</span>
						</div>
					</div>
					<div class="bar bar--tall" class:bar--before={l.key === 'before'} style="--v:{p}"><i></i></div>
				</div>
			{/each}
		</div>
	</div>
	<div class="controls">
		<button class="btn btn--ghost btn--sm" type="button" onclick={toggle} aria-pressed={!playing}>
			{#if playing}
				<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
				{t.pause}
			{:else}
				<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 5.5v13a1 1 0 0 0 1.5.9l10.4-6.5a1 1 0 0 0 0-1.8L8.5 4.6A1 1 0 0 0 7 5.5Z" /></svg>
				{elapsed >= slowest ? t.replay : t.play}
			{/if}
		</button>
	</div>
	<figcaption id="duel-cap" class="source">
		{t.caption}
		<a href={href(lang, '/methodology')}>{copy[lang].nav.methodology} →</a>
	</figcaption>
</figure>

<style>
	.duel {
		margin: 0;
		display: grid;
		gap: var(--sp-3);
	}
	.frame {
		padding: var(--sp-4);
		background:
			radial-gradient(120% 60% at 100% 0%, var(--accent-soft), transparent 60%),
			var(--bg-2);
		box-shadow: var(--shadow-2);
	}
	.top {
		display: flex;
		justify-content: space-between;
		gap: var(--sp-3);
		padding-bottom: var(--sp-3);
		border-bottom: 1px dashed var(--line);
		margin-bottom: var(--sp-3);
	}
	.meta {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.lanes {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-3);
	}
	.lane {
		display: grid;
		grid-template-rows: auto 1fr auto auto;
		gap: var(--sp-3);
		padding: var(--sp-4);
		border-radius: var(--r-md);
		border: 1px solid var(--line);
		background: var(--bg-1);
		min-width: 0;
	}
	.lane.after {
		border-color: color-mix(in srgb, var(--accent-ink) 45%, var(--line));
	}
	.lane-head {
		display: grid;
		grid-template-columns: auto 1fr auto;
		column-gap: var(--sp-2);
		align-items: center;
	}
	.led {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--before);
	}
	.after .led {
		background: var(--accent);
		box-shadow: 0 0 10px var(--accent);
	}
	.name {
		font-weight: var(--fw-semibold);
		color: var(--text-hi);
		font-size: var(--fs-sm);
	}
	.sub {
		grid-column: 2;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.out {
		font-size: 0.8125rem;
		line-height: 1.55;
		color: var(--text);
		margin: 0;
		min-height: 11.5em;
	}
	.ghost {
		visibility: hidden;
	}
	.caret {
		display: inline-block;
		width: 0.5em;
		height: 1.05em;
		/* zero net advance: the caret never pushes text to a new line (no layout shift) */
		margin-right: -0.5em;
		vertical-align: -0.15em;
		background: var(--before);
	}
	.after .caret {
		background: var(--accent);
	}
	.caret.hide {
		display: none;
	}
	.readout {
		display: flex;
		align-items: end;
		justify-content: space-between;
		gap: var(--sp-2);
		flex-wrap: wrap;
	}
	.val {
		font-size: var(--fs-xl);
		color: var(--text-hi);
		font-weight: var(--fw-medium);
		letter-spacing: -0.03em;
		line-height: 1;
	}
	.after .val {
		color: var(--accent-ink);
	}
	.unit {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
		margin-left: 0.3em;
	}
	.wps {
		display: block;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		margin-top: var(--sp-1);
	}
	.clock {
		grid-row: 1 / 3;
		grid-column: 3;
		align-self: start;
		display: grid;
		justify-items: end;
		white-space: nowrap;
		font-size: var(--fs-sm);
		color: var(--text-hi);
	}
	.tag.pending {
		visibility: hidden;
	}
	.tag {
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--ok-ink);
	}
	.lane .bar > :global(i) {
		transition: none;
	}
	.controls {
		display: flex;
		justify-content: flex-end;
		margin-top: calc(-1 * var(--sp-1));
	}
	@media (max-width: 560px) {
		.lanes {
			grid-template-columns: 1fr;
		}
		.out {
			min-height: 0;
			display: -webkit-box;
			-webkit-line-clamp: 5;
			line-clamp: 5;
			-webkit-box-orient: vertical;
			overflow: hidden;
		}
	}
	@media (prefers-reduced-motion: no-preference) {
		.caret {
			animation: blink 1s steps(1) infinite;
		}
	}
</style>
