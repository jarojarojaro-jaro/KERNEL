<script lang="ts">
	import { currentLang, num } from '$lib/i18n';
	import { T } from './i18n';
	import { DEMO, SCAN_SOURCE } from './demo';
	import Src from './Src.svelte';

	/** What the local scan read on the demo machine. */
	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const rows = $derived([
		{ k: t.spec.gpu, v: DEMO.gpu, sub: DEMO.gpuDetail },
		{ k: t.spec.vram, v: `${num(DEMO.vramGiB, lang)} GiB`, big: true },
		{ k: t.spec.ram, v: `${num(DEMO.ramGiB, lang)} GiB`, big: true },
		{ k: t.spec.cpu, v: DEMO.cpu, sub: `${t.spec.threads(DEMO.threads)} · ${DEMO.isa}` },
		{ k: t.spec.driver, v: t.spec.driverValue(DEMO.kernel) },
		{ k: t.spec.pcie, v: `PCIe ${DEMO.pcie.gen}.0 ×${DEMO.pcie.width}` },
		{ k: t.spec.os, v: 'Linux' },
		{ k: t.spec.power, v: t.spec.powerValue }
	]);
</script>

<div class="spec">
	<dl class="grid">
		{#each rows as r (r.k)}
			<div class="cell" class:big={r.big}>
				<dt>{r.k}</dt>
				<dd class:num={r.big}>{r.v}</dd>
				{#if r.sub}<dd class="sub">{r.sub}</dd>{/if}
			</div>
		{/each}
	</dl>
	<Src src={`${SCAN_SOURCE} (${T[lang].computer.srcScan})`} />
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(13.5rem, 1fr));
		gap: 1px;
		margin: 0;
		background: var(--line);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		overflow: hidden;
	}
	.cell {
		background: var(--bg-2);
		padding: var(--sp-4);
		display: grid;
		align-content: start;
		gap: var(--sp-1);
		min-width: 0;
	}
	dt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: var(--tracking-overline);
		text-transform: uppercase;
		color: var(--text-mute);
	}
	dd {
		margin: 0;
		color: var(--text-hi);
		font-weight: var(--fw-medium);
		overflow-wrap: anywhere;
	}
	.big dd.num {
		font-size: var(--fs-xl);
		letter-spacing: -0.02em;
	}
	.sub {
		color: var(--text-mute);
		font-weight: var(--fw-regular);
		font-size: var(--fs-sm);
	}
</style>
