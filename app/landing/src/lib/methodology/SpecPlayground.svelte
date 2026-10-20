<script lang="ts">
	import { onMount } from 'svelte';
	import { fmtRatio } from '$lib/format';
	import { play, visible } from '$lib/fx/actions';
	import { reducedMotion } from '$lib/fx/motion';
	import { num, type Lang } from '$lib/i18n';
	import { COPY } from './copy';
	import { CHAT_TOK_STEP, SPEC } from './facts';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(COPY[lang]);

	/**
	 * Per-draft acceptance p for a prefix-accept chain of `k` drafts, chosen so that the expected
	 * tokens per step (accepted prefix + 1 from the model) equals the measured mean.
	 */
	function acceptP(k: number, mean: number) {
		const target = mean - 1;
		let lo = 0;
		let hi = 1;
		for (let it = 0; it < 40; it++) {
			const p = (lo + hi) / 2;
			let e = 0;
			for (let i = 1; i <= k; i++) e += p ** i;
			if (e < target) lo = p;
			else hi = p;
		}
		return (lo + hi) / 2;
	}
	const MODES = {
		chat: { k: 4, mean: CHAT_TOK_STEP },
		code: { k: SPEC.tail.of - 1, mean: SPEC.tail.got }
	} as const;
	type Mode = keyof typeof MODES;
	let mode = $state<Mode>('chat');
	const P = { chat: acceptP(MODES.chat.k, MODES.chat.mean), code: acceptP(MODES.code.k, MODES.code.mean) };

	/** Deterministic PRNG so every visitor sees the same plausible run (mulberry32). */
	function rng(seed: number) {
		return () => {
			seed = (seed + 0x6d2b79f5) | 0;
			let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
			t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
			return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
		};
	}
	let rand = rng(7);

	const tokenize = (s: string) => s.match(/\s*[\p{L}\p{N}_]+|\s*[^\s\p{L}\p{N}_]/gu) ?? [];
	/** Wrong guesses shown for rejected drafts. */
	const DECOYS = {
		chat: { pl: ['jednak', 'nawet', 'raczej', 'potem', 'czasem'], en: ['however', 'even', 'rather', 'later', 'often'] },
		code: { pl: ['map', 'filter', '1', '+', 'total'], en: ['map', 'filter', '1', '+', 'total'] }
	};
	const toks = $derived(tokenize(mode === 'chat' ? c.p.chatText : c.p.codeText));

	let out = $state(0);
	let steps = $state(0);
	/** Draft of the current step: tokens and how many of them the model accepted (-1 = not verified yet). */
	let draft = $state<{ text: string; ok: boolean }[]>([]);
	let phase = $state<'idle' | 'draft' | 'verify'>('idle');
	let auto = $state(false);
	let on = false;
	let timer = 0;

	function reset(m: Mode = mode) {
		mode = m;
		rand = rng(m === 'chat' ? 7 : 11);
		out = 0;
		steps = 0;
		draft = [];
		phase = 'idle';
	}
	/** One speculative step in two beats: show the draft, then verify it. */
	function step() {
		if (out >= toks.length) reset();
		if (phase !== 'draft') {
			const { k } = MODES[mode];
			const p = P[mode];
			let acc = 0;
			while (acc < k && rand() < p) acc++;
			const left = toks.length - out;
			const d: { text: string; ok: boolean }[] = [];
			for (let i = 0; i < Math.min(k, left); i++) {
				const ok = i < acc;
				d.push({ text: ok ? toks[out + i] : DECOYS[mode][lang][i % 5], ok });
			}
			draft = d;
			phase = 'draft';
			return;
		}
		const acc = draft.findIndex((d) => !d.ok);
		const n = acc === -1 ? draft.length : acc;
		out = Math.min(toks.length, out + n + 1);
		steps += 1;
		phase = 'verify';
	}

	onMount(() => {
		const id = window.setInterval(() => {
			if (auto && on) step();
		}, 650);
		timer = id;
		return () => clearInterval(timer);
	});
	const avg = $derived(steps ? out / steps : 0);
	const accepted = $derived(phase === 'verify' ? draft.findIndex((d) => !d.ok) : -2);

	const rows = $derived([
		{ id: 'chat', label: c.p.chatRow, v: SPEC.chat },
		{ id: 'code', label: c.p.codeRow, v: SPEC.code }
	]);
</script>

<div class="play">
	<div class="panel pg" use:visible={(v) => (on = v)} use:play={{ onplay: () => (auto = true) }}>
		<div class="top">
			<div class="seg" role="group" aria-label={c.p.chat + ' / ' + c.p.code}>
				<button type="button" aria-pressed={mode === 'chat'} onclick={() => reset('chat')}>{c.p.chat}</button>
				<button type="button" aria-pressed={mode === 'code'} onclick={() => reset('code')}>{c.p.code}</button>
			</div>
			<div class="ctrl">
				<button type="button" class="btn-m hot" onclick={step}>{c.step} →</button>
				<button type="button" class="btn-m ghost" aria-pressed={auto} onclick={() => (auto = !reducedMotion() && !auto)}>{auto ? c.pause : c.p.auto}</button>
				<button type="button" class="btn-m ghost" onclick={() => reset()}>{c.reset}</button>
			</div>
		</div>

		<p class="written" class:code={mode === 'code'} aria-live="polite">
			<span class="done">{toks.slice(0, out).join('')}</span>{#if out < toks.length}<span class="rest" aria-hidden="true">{toks.slice(out).join('')}</span>{/if}
		</p>

		<div class="draft-row">
			<span class="dl mono">{c.p.draft}</span>
			<ol class="draft" class:wide={mode === 'code'}>
				{#each draft as d, i (steps + '-' + i)}
					{@const st = phase === 'verify' ? (accepted === -1 || i < accepted ? 'acc' : i === accepted ? 'rej' : 'drop') : 'pend'}
					<li class="chip d {st}" style="--i:{i}">{d.text.trim() || '·'}</li>
				{/each}
				{#if phase === 'verify'}
					<li class="chip d bonus" style="--i:{draft.length}">+1</li>
				{/if}
			</ol>
		</div>
		<ul class="legend">
			<li><i class="acc"></i>{c.p.accepted}</li>
			<li><i class="rej"></i>{c.p.rejected}</li>
			<li><i class="bonus"></i>{c.p.bonus}</li>
		</ul>

		<dl class="kpis">
			<div><dt>{c.p.steps}</dt><dd class="mono">{steps}</dd></div>
			<div><dt>{c.p.vs}</dt><dd class="mono mute">{out}</dd></div>
			<div><dt>{c.p.perStep}</dt><dd class="mono hot">{num(avg, lang, 1)}</dd></div>
		</dl>
		<p class="fine">
			{mode === 'chat' ? c.p.chatNote(num(CHAT_TOK_STEP, lang, 1)) : c.p.codeNote(num(SPEC.tail.got, lang, 1), String(SPEC.tail.of))}
			<span class="tag-ill">{c.illustr}</span>
		</p>
	</div>

	<div class="panel speed">
		<p class="panel-h">{c.p.speed} <span class="tag-m">{c.measured}</span></p>
		{#each rows as r (r.id)}
			{@const max = r.v.ours}
			<div class="srow">
				<p class="sl">{r.label}<span class="x speedup">{fmtRatio(r.v.ours / r.v.a0, lang)}</span></p>
				{#each [{ k: 'a0', l: c.p.a0, v: r.v.a0 }, { k: 'a1', l: c.p.a1, v: r.v.a1 }, { k: 'ours', l: c.p.ours, v: r.v.ours }] as b (b.k)}
					<div class="b {b.k}">
						<span class="bl">{b.l}</span>
						<span class="track" aria-hidden="true"><i style="transform:scaleX({b.v / max})"></i></span>
						<span class="bv mono">{num(b.v, lang, 1)}</span>
					</div>
				{/each}
			</div>
		{/each}
		<p class="fine">t/s · RX 7900 XTX · Qwen3.8-27B UD-Q4_K_XL</p>
	</div>
</div>

<style>
	.play {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: var(--sp-6);
	}
	.pg,
	.speed {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
	}
	.top {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--sp-3);
	}
	.ctrl {
		display: flex;
		gap: var(--sp-2);
		flex-wrap: wrap;
	}
	.written {
		margin: 0;
		min-height: 5.5em;
		padding: var(--sp-4);
		border-radius: var(--r-md);
		background: var(--bg-2);
		border: 1px solid var(--line);
		line-height: 1.6;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.written.code {
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
	}
	.done {
		color: var(--text-hi);
	}
	.rest {
		color: var(--text-mute);
		opacity: 0.35;
	}
	.draft-row {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: var(--sp-3);
		align-items: start;
		min-height: 2.5rem;
	}
	.dl {
		padding-top: 0.35rem;
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.draft {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
	}
	.d {
		animation: pop 0.45s var(--ease-spring) both;
		animation-delay: calc(var(--i) * 35ms);
	}
	@keyframes pop {
		from {
			opacity: 0;
			transform: translateY(6px) scale(0.9);
		}
	}
	.d.pend {
		border-style: dashed;
		color: var(--text-mute);
	}
	.d.acc {
		color: var(--on-accent);
		background: var(--heat-3);
		border-color: var(--heat-3);
	}
	.d.rej {
		color: var(--danger-ink);
		border-color: var(--danger);
		text-decoration: line-through;
	}
	.d.drop {
		opacity: 0.3;
		text-decoration: line-through;
	}
	.d.bonus {
		color: var(--text-inv);
		background: var(--heat-5);
		border-color: var(--heat-5);
		font-weight: 650;
	}
	.legend {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2) var(--sp-4);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.legend li {
		display: inline-flex;
		gap: var(--sp-2);
		align-items: center;
	}
	.legend i {
		width: 0.8rem;
		height: 0.8rem;
		border-radius: 3px;
	}
	.legend .acc {
		background: var(--heat-3);
	}
	.legend .rej {
		border: 1px solid var(--danger);
	}
	.legend .bonus {
		background: var(--heat-5);
	}
	.kpis {
		margin: 0;
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-3);
		border-top: 1px solid var(--line);
		padding-top: var(--sp-3);
	}
	.kpis div {
		display: grid;
		gap: 0.1rem;
	}
	.kpis dt {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.kpis dd {
		margin: 0;
		font-size: var(--fs-2xl, 1.8rem);
		font-weight: 600;
		color: var(--text-hi);
		letter-spacing: -0.03em;
	}
	.kpis .mute {
		color: var(--before);
	}
	.kpis .hot {
		color: var(--accent-ink);
	}
	.srow {
		display: grid;
		gap: var(--sp-2);
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
	}
	.sl {
		margin: 0;
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--sp-3);
		font-weight: 560;
		color: var(--text-hi);
	}
	.x {
		font-size: var(--fs-2xl, 1.8rem);
		font-weight: 650;
		letter-spacing: -0.03em;
	}
	.b {
		display: grid;
		grid-template-columns: 8.5rem minmax(0, 1fr) 3.5rem;
		gap: var(--sp-3);
		align-items: center;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.track {
		height: 0.55rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
		border-radius: inherit;
		transform-origin: left;
		background: var(--before);
		transition: transform 1s var(--ease-out);
	}
	.a1 .track i {
		background: color-mix(in srgb, var(--heat-1) 70%, var(--before));
	}
	.ours .track i {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 14px -2px var(--heat-3);
	}
	.bv {
		text-align: right;
		color: var(--text);
	}
	.ours .bv,
	.ours .bl {
		color: var(--accent-ink);
		font-weight: 600;
	}
	@media (max-width: 960px) {
		.play {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 420px) {
		.b {
			grid-template-columns: minmax(0, 1fr) 3.5rem;
		}
		.b .track {
			grid-column: 1 / -1;
			grid-row: 2;
		}
		.kpis dd {
			font-size: var(--fs-xl);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.d {
			animation: none;
		}
	}
</style>
