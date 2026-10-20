<script lang="ts">
	import { onMount } from 'svelte';
	import { reducedMotion } from '$lib/fx/motion';
	import { num, type Lang } from '$lib/i18n';
	import { COPY } from './copy';
	import { OCC, PM4, SIMD, wavesFor } from './facts';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(COPY[lang]);

	/* ---- the investigation, one step at a time ---- */
	let story = $state(3);

	/* ---- COMPUTE_PGM_RSRC1: flip PRIV, then preempt ---- */
	let priv = $state(false);
	/** idle → saving (waves leave) → restored (ok or fault). */
	let evict = $state<'idle' | 'out' | 'ok' | 'fault'>('idle');
	let tm = 0;
	function preempt() {
		clearTimeout(tm);
		if (reducedMotion()) {
			evict = priv ? 'ok' : 'fault';
			return;
		}
		evict = 'out';
		tm = window.setTimeout(() => (evict = priv ? 'ok' : 'fault'), 700);
	}
	function flip() {
		priv = !priv;
		evict = 'idle';
	}
	onMount(() => () => clearTimeout(tm));
	const BITS = 32;

	/* ---- occupancy ---- */
	let vgpr = $state<number>(OCC.before);
	const waves = $derived(wavesFor(vgpr));
	const alloc = $derived(Math.ceil(vgpr / SIMD.granule) * SIMD.granule);
</script>

<div class="metal">
	<div class="panel story">
		<p class="panel-h">{c.x.storyTitle}</p>
		<ol class="steps" aria-label={c.x.storyTitle}>
			{#each c.x.story as [k], i (k)}
				<li>
					<button type="button" class:on={story === i} class:past={i < story} aria-pressed={story === i} onclick={() => (story = i)}>
						<span class="sn mono">{i + 1}</span><span class="sk">{k}</span>
					</button>
				</li>
			{/each}
		</ol>
		<div class="sbody" aria-live="polite">
			{#key story}
				<p class="st">{c.x.story[story][0]}</p>
				<p>{c.x.story[story][1]}</p>
			{/key}
		</div>
		<div class="nav">
			<button type="button" class="btn-m ghost" disabled={story === 0} onclick={() => (story -= 1)}>←</button>
			<button type="button" class="btn-m ghost" disabled={story === c.x.story.length - 1} onclick={() => (story += 1)}>→</button>
		</div>
	</div>

	<div class="panel reg" class:fault={evict === 'fault'} class:good={evict === 'ok'}>
		<div>
			<p class="panel-h">{c.x.regTitle} <span class="tag-ill">{c.illustr}</span></p>
			<p class="small">{c.x.regLead}</p>
		</div>
		<div class="bits" aria-hidden="true">
			{#each { length: BITS } as _, i (i)}
				{@const b = BITS - 1 - i}
				<span class="bit" class:privb={b === 20} class:set={b === 20 && priv}>{b === 20 ? (priv ? 1 : 0) : ''}</span>
			{/each}
		</div>
		<div class="ctrl">
			<button type="button" class="btn-m switch" role="switch" aria-checked={priv} onclick={flip}><span class="knob" aria-hidden="true"></span>{c.x.bit} = {priv ? 1 : 0}</button>
			<button type="button" class="btn-m hot" onclick={preempt}>{c.x.evict}</button>
		</div>
		<div class="tape">
			<ol class="waves" class:out={evict === 'out'} aria-hidden="true">
				{#each { length: 12 } as _, i (i)}<li style="--i:{i}"></li>{/each}
			</ol>
		</div>
		<p class="status mono" aria-live="polite">
			{evict === 'idle' || evict === 'out' ? c.x.idle : evict === 'ok' ? c.x.ok : c.x.bad}
		</p>
	</div>

	<div class="panel res">
		<p class="panel-h">{c.x.resultTitle} <span class="tag-m">{c.measured}</span></p>
		<dl class="stats">
			<div><dt>{c.x.requests}</dt><dd class="mono">{num(PM4.requests, lang, 0)}</dd></div>
			<div><dt>{c.x.faults}</dt><dd class="mono ok">{PM4.faults}</dd></div>
			<div><dt>LFM2.5 · tg128</dt><dd class="mono hot">+{num(PM4.lfm.pct, lang, 1)}%</dd><dd class="sub mono">{num(PM4.lfm.before, lang, 1)} → {num(PM4.lfm.after, lang, 1)} t/s</dd></div>
			<div><dt>Qwen3.8 · spec_sweep T=1</dt><dd class="mono hot">+{num(PM4.qwen.pct, lang, 1)}%</dd><dd class="sub mono">{num(PM4.qwen.before, lang, 1)} → {num(PM4.qwen.after, lang, 1)} t/s</dd></div>
		</dl>
	</div>

	<div class="panel occ">
		<div class="occ-head">
			<p class="panel-h">{c.x.occTitle}</p>
			<p class="small">{c.x.occLead}</p>
		</div>
		<div class="occ-body">
			<div class="ctl">
				<label for="vgpr" class="vl"><span>{c.x.vgpr}</span><b class="mono">{vgpr}</b></label>
				<input id="vgpr" type="range" min="24" max="256" step="1" bind:value={vgpr} aria-valuetext="{vgpr} VGPR, {waves} {c.x.waves}" />
				<div class="presets">
					{#each [OCC.before, OCC.after] as v (v)}
						<button type="button" class="btn-m ghost" aria-pressed={vgpr === v} onclick={() => (vgpr = v)}>{c.x.preset(v)}</button>
					{/each}
				</div>
				<p class="fine mono">ceil({vgpr} / {SIMD.granule}) × {SIMD.granule} = {alloc} · ⌊{SIMD.vgprs} / {alloc}⌋ = {Math.floor(SIMD.vgprs / alloc)}{Math.floor(SIMD.vgprs / alloc) > SIMD.maxWaves ? ` → max ${SIMD.maxWaves}` : ''}</p>
			</div>
			<div class="simd">
				<p class="wv"><b class="mono">{waves}</b> <span>{c.x.waves}</span></p>
				<ol class="slots" aria-hidden="true">
					{#each { length: SIMD.maxWaves } as _, i (i)}<li class:on={i < waves} style="--i:{i}"></li>{/each}
				</ol>
				<div class="rf" aria-hidden="true">
					<i style="transform:scaleX({(waves * alloc) / SIMD.vgprs})"></i>
				</div>
			</div>
		</div>
		<p class="take">{c.x.cliff}</p>
	</div>
</div>

<style>
	.metal {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: var(--sp-6);
	}
	.story,
	.reg,
	.res,
	.occ {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
	}
	.steps {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: var(--sp-1);
	}
	.steps button {
		width: 100%;
		display: grid;
		gap: var(--sp-1);
		justify-items: start;
		padding: var(--sp-2);
		min-height: 2.75rem;
		border: 0;
		border-top: 2px solid var(--line);
		background: none;
		color: var(--text-mute);
		font-size: var(--fs-2xs);
		text-align: left;
		cursor: pointer;
		transition:
			color var(--dur-2),
			border-color var(--dur-3);
	}
	.steps button.past {
		border-top-color: color-mix(in srgb, var(--heat-3) 50%, var(--line));
	}
	.steps button.on {
		border-top-color: var(--heat-3);
		color: var(--text-hi);
	}
	.steps button:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.sn {
		font-size: var(--fs-xs);
		color: var(--accent-ink);
	}
	.sk {
		overflow-wrap: anywhere;
	}
	.sbody {
		min-height: 9.5rem;
	}
	.sbody p {
		margin: 0 0 var(--sp-2);
		line-height: 1.6;
		animation: rise 0.45s var(--ease-out) both;
	}
	@keyframes rise {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
	}
	.st {
		font-size: var(--fs-lg);
		font-weight: 600;
		color: var(--text-hi);
	}
	.nav {
		display: flex;
		gap: var(--sp-2);
	}
	.bits {
		display: grid;
		grid-template-columns: repeat(32, minmax(0, 1fr));
		gap: 2px;
	}
	.bit {
		aspect-ratio: 1 / 2.2;
		border-radius: 2px;
		background: var(--bg-3);
		display: grid;
		place-items: center;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
	}
	.bit.privb {
		background: var(--danger-soft);
		outline: 1px solid var(--danger);
		color: var(--danger-ink);
		font-weight: 700;
	}
	.bit.privb.set {
		background: var(--heat-3);
		outline-color: var(--heat-4);
		color: var(--on-accent);
		box-shadow: 0 0 14px var(--heat-3);
	}
	.ctrl {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.switch {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
	}
	.knob {
		position: relative;
		width: 2rem;
		height: 1.1rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		border: 1px solid var(--line-strong);
	}
	.knob::after {
		content: '';
		position: absolute;
		top: 2px;
		left: 2px;
		width: calc(1.1rem - 6px);
		height: calc(1.1rem - 6px);
		border-radius: 50%;
		background: var(--text-mute);
		transition: transform var(--dur-3) var(--ease-spring);
	}
	.switch[aria-checked='true'] .knob {
		background: var(--accent-soft);
		border-color: var(--heat-3);
	}
	.switch[aria-checked='true'] .knob::after {
		transform: translateX(0.9rem);
		background: var(--heat-3);
	}
	.tape {
		padding: var(--sp-3);
		border-radius: var(--r-md);
		background: var(--bg-2);
		border: 1px solid var(--line);
		overflow: hidden;
	}
	.waves {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(12, minmax(0, 1fr));
		gap: 4px;
	}
	.waves li {
		height: 1.6rem;
		border-radius: 3px;
		background: linear-gradient(180deg, var(--heat-4), var(--heat-2));
		transition:
			transform 0.5s var(--ease-in-out),
			opacity 0.5s,
			background-color 0.3s;
		transition-delay: calc(var(--i) * 25ms);
	}
	.waves.out li {
		transform: translateY(140%);
		opacity: 0;
	}
	.reg.fault .waves li {
		background: var(--danger);
		animation: shake 0.4s linear 2;
	}
	.reg.good .waves li {
		background: linear-gradient(180deg, var(--ok), color-mix(in srgb, var(--ok) 50%, var(--bg-2)));
	}
	@keyframes shake {
		25% {
			transform: translateX(-3px);
		}
		75% {
			transform: translateX(3px);
		}
	}
	.reg.fault {
		border-color: color-mix(in srgb, var(--danger) 55%, var(--line));
	}
	.reg.good {
		border-color: color-mix(in srgb, var(--ok) 50%, var(--line));
	}
	.status {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text);
		min-height: 2.6em;
	}
	.reg.fault .status {
		color: var(--danger-ink);
	}
	.reg.good .status {
		color: var(--ok-ink);
	}
	.stats {
		margin: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
		gap: var(--sp-5) var(--sp-4);
	}
	.stats div {
		display: grid;
		gap: 0.15rem;
	}
	.stats dt {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.stats dd {
		margin: 0;
		font-size: clamp(1.8rem, 1.3rem + 1.8vw, 2.8rem);
		font-weight: 600;
		letter-spacing: -0.04em;
		line-height: 1.05;
		color: var(--text-hi);
	}
	.stats dd.ok {
		color: var(--ok-ink);
	}
	.stats dd.hot {
		color: var(--accent-ink);
	}
	.stats dd.sub {
		font-size: var(--fs-xs);
		font-weight: 400;
		letter-spacing: 0;
		color: var(--text-mute);
	}
	.occ,
	.res {
		grid-column: 1 / -1;
	}
	.occ-head {
		display: grid;
		gap: var(--sp-2);
		max-width: 75ch;
	}
	.occ-body {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
		gap: var(--sp-8);
		align-items: center;
	}
	.ctl {
		display: grid;
		gap: var(--sp-3);
	}
	.vl {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.vl b {
		font-size: var(--fs-2xl, 1.8rem);
		color: var(--text-hi);
	}
	input[type='range'] {
		width: 100%;
		accent-color: var(--heat-3);
		min-height: 2.75rem;
	}
	.presets {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.simd {
		display: grid;
		gap: var(--sp-3);
	}
	.wv {
		margin: 0;
		display: flex;
		align-items: baseline;
		gap: var(--sp-2);
		color: var(--text-mute);
	}
	.wv b {
		font-size: clamp(2.6rem, 2rem + 2vw, 3.8rem);
		font-weight: 650;
		letter-spacing: -0.05em;
		line-height: 1.1;
		/* room for the ink of the last digit (negative tracking) */
		padding-inline-end: 0.1em;
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.slots {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(16, minmax(0, 1fr));
		gap: 4px;
	}
	.slots li {
		height: 3.2rem;
		border-radius: 3px;
		border: 1px dashed var(--line-strong);
		position: relative;
		overflow: hidden;
	}
	.slots li::after {
		content: '';
		position: absolute;
		inset: 0;
		background: linear-gradient(180deg, var(--heat-4), var(--heat-2));
		transform: scaleY(0);
		transform-origin: bottom;
		transition: transform 0.45s var(--ease-spring);
		transition-delay: calc(var(--i) * 15ms);
	}
	.slots li.on {
		border-style: solid;
		border-color: transparent;
	}
	.slots li.on::after {
		transform: scaleY(1);
	}
	.rf {
		height: 0.5rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.rf i {
		display: block;
		height: 100%;
		background: var(--before);
		transform-origin: left;
		transition: transform 0.45s var(--ease-out);
	}
	.take {
		margin: 0;
		color: var(--text-hi);
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
	}
	@media (max-width: 960px) {
		.metal,
		.occ-body {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 520px) {
		.steps {
			grid-template-columns: repeat(5, minmax(0, 1fr));
		}
		.sk {
			display: none;
		}
		.steps button {
			justify-items: center;
		}
		.slots {
			grid-template-columns: repeat(8, minmax(0, 1fr));
		}
		.slots li {
			height: 2.2rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.sbody p,
		.reg.fault .waves li {
			animation: none;
		}
		.waves li,
		.slots li::after,
		.rf i {
			transition: none;
		}
	}
</style>
