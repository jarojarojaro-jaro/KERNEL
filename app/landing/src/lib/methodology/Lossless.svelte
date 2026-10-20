<script lang="ts">
	import { onMount } from 'svelte';
	import { play, visible } from '$lib/fx/actions';
	import { reducedMotion } from '$lib/fx/motion';
	import { num, type Lang } from '$lib/i18n';
	import { COPY } from './copy';
	import { BACKEND_OPS, GATES, KLD } from './facts';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(COPY[lang]);

	const TEXT = {
		pl: {
			ref: 'Ten sam model na tej samej karcie pisze ten sam tekst , token po tokenie , dopóki nikt nie zmieni kolejności sumowania .',
			bad: 'Ten sam model na tej samej karcie pisze ten sam tekst , ale od tego miejsca każde słowo może pójść inną drogą .'
		},
		en: {
			ref: 'The same model on the same card writes the same text , token by token , until someone changes the summation order .',
			bad: 'The same model on the same card writes the same text , but from here on every word can take another path .'
		}
	} as const;
	const ref = $derived(TEXT[lang].ref.split(' '));
	let broken = $state(false);
	const cand = $derived(broken ? TEXT[lang].bad.split(' ') : ref);
	const n = $derived(Math.max(ref.length, cand.length));

	/** FNV-1a 32-bit: a tiny stand-in for md5 so the demo hashes the visible text in the browser. */
	function fnv(s: string) {
		let h = 0x811c9dc5;
		for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193) >>> 0;
		return h.toString(16).padStart(8, '0');
	}
	const hRef = $derived(fnv(ref.join(' ')));
	const hCand = $derived(fnv(cand.join(' ')));

	/** Comparator position: tokens left of it have been checked. Rests at the end (final state). */
	let pos = $state(Infinity);
	let on = false;
	let timer = 0;
	function scan() {
		clearInterval(timer);
		if (reducedMotion()) {
			pos = Infinity;
			return;
		}
		pos = 0;
		timer = window.setInterval(() => {
			if (!on) return;
			pos += 1;
			if (pos > n) {
				clearInterval(timer);
				pos = Infinity;
			}
		}, 140);
	}
	function toggle() {
		broken = !broken;
		scan();
	}
	onMount(() => () => clearInterval(timer));
	const done = $derived(pos > n);
	const same = $derived(hRef === hCand);
	const kldMax = Math.max(...KLD.flatMap((k) => [k.ours, k.noise]));
</script>

<div class="grid">
	<div class="demo panel" use:visible={(v) => (on = v)} use:play={{ onplay: scan }}>
		<div class="demo-head">
			<p class="panel-h">{c.l.demoTitle} <span class="tag-ill">{c.illustr}</span></p>
			<p class="small">{c.l.demoLead}</p>
		</div>
		{#each [{ k: 'ref', label: c.l.ref, toks: ref, h: hRef }, { k: 'cand', label: c.l.cand, toks: cand, h: hCand }] as row (row.k)}
			<div class="row">
				<p class="row-l mono">{row.label}</p>
				<ol class="toks" aria-label={row.label}>
					{#each row.toks as tok, i (i)}
						{@const checked = i < pos}
						{@const diff = ref[i] !== cand[i]}
						<li class="tok" class:checked class:diff={checked && diff} class:match={checked && !diff}>{tok}</li>
					{/each}
				</ol>
				<p class="hash mono"><span>{c.l.hash}</span> {done ? row.h : '········'}</p>
			</div>
		{/each}
		<div class="gate" class:pass={done && same} class:fail={done && !same} aria-live="polite">
			<span class="lamp" aria-hidden="true"></span>
			<strong class="mono">{done ? (same ? c.l.pass : c.l.fail) : '…'}</strong>
			<span class="small">{done && !same ? c.l.failNote : c.l.tokens(ref.length)}</span>
		</div>
		<div class="ctrl">
			<button type="button" class="btn-m" class:hot={!broken} onclick={toggle}>{broken ? c.l.heal : c.l.inject}</button>
			<button type="button" class="btn-m ghost" onclick={scan}>{c.replay}</button>
		</div>
		<p class="fine">{c.l.demoNote}</p>
	</div>

	<div class="side">
		<div class="panel">
			<p class="panel-h">{c.l.gates}</p>
			<ul class="md5">
				{#each GATES as g (g.id)}
					<li><span>{g.label} <span class="mute">{g.mode}</span></span><code class="mono">{g.md5}…</code><span class="ok mono" aria-label="OK">✓</span></li>
				{/each}
			</ul>
			<p class="fine">{c.l.gatesNote}</p>
		</div>
		<div class="panel">
			<p class="panel-h">{c.l.opsTitle}</p>
			<ul class="ops">
				{#each BACKEND_OPS as o (o.op)}
					<li><span class="mono">{o.op}</span><span class="frac mono">{o.pass}/{o.of}</span></li>
				{/each}
			</ul>
			<p class="fine">{c.l.opsNote}</p>
		</div>
	</div>

	<div class="kld panel">
		<div>
			<p class="panel-h">{c.l.kldTitle}</p>
			<p class="small">{c.l.kldLead}</p>
		</div>
		<div class="kld-rows">
			{#each KLD as k (k.id)}
				<div class="kr">
					<p class="km">{k.model} <span class="mute">· RTX 3060</span></p>
					<div class="kb">
						<span class="kl">{c.l.kldOurs}</span>
						<span class="track" aria-hidden="true"><i class="ours" style="transform:scaleX({k.ours / kldMax})"></i></span>
						<span class="kv mono">{num(k.ours, lang, 5)}</span>
					</div>
					<div class="kb">
						<span class="kl">{c.l.kldNoise}</span>
						<span class="track" aria-hidden="true"><i style="transform:scaleX({k.noise / kldMax})"></i></span>
						<span class="kv mono mute">{num(k.noise, lang, 5)}</span>
					</div>
				</div>
			{/each}
		</div>
	</div>
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
		gap: var(--sp-6);
	}
	.demo {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
	}
	.demo-head {
		display: grid;
		gap: var(--sp-2);
	}
	.row {
		display: grid;
		gap: var(--sp-2);
	}
	.row-l {
		margin: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.toks {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
	}
	.tok {
		padding: 0.2rem 0.45rem;
		border-radius: var(--r-xs);
		border: 1px solid var(--line);
		background: var(--bg-2);
		font-size: var(--fs-xs);
		color: var(--text-mute);
		transition:
			background-color var(--dur-3),
			border-color var(--dur-3),
			color var(--dur-3),
			transform var(--dur-3) var(--ease-spring);
	}
	.tok.match {
		color: var(--text-hi);
		border-color: color-mix(in srgb, var(--ok) 45%, var(--line));
		background: var(--ok-soft);
	}
	.tok.diff {
		color: var(--danger-ink);
		border-color: color-mix(in srgb, var(--danger) 60%, var(--line));
		background: var(--danger-soft);
		transform: translateY(-2px);
	}
	.hash {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.hash span {
		color: var(--text-mute);
	}
	.gate {
		display: grid;
		grid-template-columns: auto auto minmax(0, 1fr);
		align-items: center;
		gap: var(--sp-3);
		padding: var(--sp-3) var(--sp-4);
		border-radius: var(--r-md);
		border: 1px solid var(--line);
		background: var(--bg-2);
		transition:
			border-color var(--dur-3),
			background-color var(--dur-3);
	}
	.lamp {
		width: 0.75rem;
		height: 0.75rem;
		border-radius: 50%;
		background: var(--line-strong);
	}
	.gate.pass {
		border-color: color-mix(in srgb, var(--ok) 50%, var(--line));
		background: var(--ok-soft);
	}
	.gate.pass .lamp {
		background: var(--ok);
		box-shadow: 0 0 12px var(--ok);
	}
	.gate.pass strong {
		color: var(--ok-ink);
	}
	.gate.fail {
		border-color: color-mix(in srgb, var(--danger) 55%, var(--line));
		background: var(--danger-soft);
	}
	.gate.fail .lamp {
		background: var(--danger);
		box-shadow: 0 0 12px var(--danger);
	}
	.gate.fail strong {
		color: var(--danger-ink);
	}
	.ctrl {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.side {
		display: grid;
		gap: var(--sp-6);
		align-content: start;
	}
	.side .panel {
		display: grid;
		gap: var(--sp-3);
	}
	.md5,
	.ops {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
	}
	.md5 li {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto auto;
		gap: var(--sp-3);
		align-items: center;
		padding: var(--sp-2) 0;
		border-bottom: 1px solid var(--line);
		font-size: var(--fs-sm);
	}
	.md5 code {
		color: var(--accent-ink);
		font-size: var(--fs-sm);
	}
	.ok {
		color: var(--ok-ink);
	}
	.mute {
		color: var(--text-mute);
	}
	.ops {
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--sp-2);
	}
	.ops li {
		display: grid;
		gap: 0.1rem;
		padding: var(--sp-2) var(--sp-3);
		border-radius: var(--r-sm);
		background: var(--bg-2);
		border: 1px solid var(--line);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.frac {
		font-size: var(--fs-lg);
		color: var(--ok-ink);
		font-weight: 600;
	}
	.kld {
		grid-column: 1 / -1;
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr);
		gap: var(--sp-6);
		align-items: center;
	}
	.kld-rows {
		display: grid;
		gap: var(--sp-5);
	}
	.kr {
		display: grid;
		gap: var(--sp-2);
	}
	.km {
		margin: 0;
		font-weight: 600;
		color: var(--text-hi);
	}
	.kb {
		display: grid;
		grid-template-columns: 9rem minmax(0, 1fr) 5.5rem;
		gap: var(--sp-3);
		align-items: center;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.track {
		height: 0.6rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
		transform-origin: left;
		background: var(--before);
		border-radius: inherit;
	}
	.track i.ours {
		background: var(--heat-ramp-hot);
	}
	.kv {
		text-align: right;
		font-size: var(--fs-sm);
		color: var(--accent-ink);
	}
	.kv.mute {
		color: var(--text-mute);
	}
	@media (max-width: 960px) {
		.grid,
		.kld {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 520px) {
		.kb {
			grid-template-columns: minmax(0, 1fr) 4.8rem;
		}
		.kb .track {
			grid-column: 1 / -1;
			grid-row: 2;
		}
		.gate {
			grid-template-columns: auto minmax(0, 1fr);
		}
		.gate .small {
			grid-column: 1 / -1;
		}
	}
</style>
