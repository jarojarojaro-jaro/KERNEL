<script lang="ts">
	/** The headline result: writing speed baseline → now and the gain, large. Only measured numbers. */
	import type { BenchResult } from '../../shared/types';
	import { gainPct } from '../lib/bench';
	import { num, pct } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	let { base, now }: { base: BenchResult; now: BenchResult } = $props();
	const t = $derived(store.t.hi);
	const lang = $derived(store.lang);
	const g = $derived(gainPct(base.decode.tps, now.decode.tps) ?? 0);
	const up = $derived(g >= 0.5);
	const down = $derived(g <= -0.5);
</script>

<div class="gh panel panel--heat">
	<p class="eyebrow">{t.decode}</p>
	<div class="row">
		<p class="flow num">
			<span class="b">{num(base.decode.tps, lang, 1)}</span>
			<span class="arr" aria-hidden="true">→</span>
			<span class="n" class:hot={up}>{num(now.decode.tps, lang, 1)}</span>
			<span class="u">t/s</span>
		</p>
		<p class="gain">
			<span class="gv num" class:hot={up} class:down>{up || down ? pct(g, lang) : '±0'}</span>
			<span class="gl">{up ? t.faster : down ? t.slower : t.same}</span>
		</p>
	</div>
</div>

<style>
	.gh {
		display: grid;
		gap: var(--sp-3);
	}
	.eyebrow {
		margin: 0;
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--sp-4) var(--sp-8);
	}
	.flow {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		margin: 0;
	}
	.b {
		font-size: clamp(1.6rem, 1.2rem + 1.4vw, 2.4rem);
		color: var(--before);
	}
	.arr {
		color: var(--text-mute);
		font-size: var(--fs-lg);
	}
	.n {
		font-size: clamp(2.4rem, 1.6rem + 2.6vw, 3.8rem);
		font-weight: 560;
		letter-spacing: -0.04em;
		color: var(--text-hi);
	}
	.n.hot {
		color: var(--accent-ink);
	}
	.u {
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.gain {
		display: grid;
		justify-items: end;
		margin: 0;
	}
	.gv {
		font-size: clamp(2.8rem, 1.8rem + 3.6vw, 5rem);
		font-weight: 600;
		line-height: 1;
		letter-spacing: -0.05em;
		color: var(--text-hi);
	}
	.gv.hot {
		background: var(--heat-large);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 6px 26px rgb(255 122 26 / 0.3));
	}
	.gv.down {
		color: var(--danger-ink);
	}
	.gl {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		font-family: var(--font-mono);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	@media (max-width: 600px) {
		.gain {
			justify-items: start;
		}
	}
</style>
