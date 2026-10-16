<script lang="ts">
	import { currentLang } from '$lib/i18n';
	import type { Measurement } from '$lib/data/measurements';
	import { T } from './i18n';

	/**
	 * Source footnote: registry entries (file:line + harness) and/or free-form sources.
	 * `as="span"` for places where only phrasing content is allowed (inside <label>).
	 */
	let {
		m,
		src,
		as = 'p'
	}: { m?: Measurement | Measurement[]; src?: string | string[]; as?: 'p' | 'span' } = $props();

	const t = $derived(T[currentLang()]);
	const parts = $derived([
		...(m ? (Array.isArray(m) ? m : [m]) : []).map((x) => `${x.source} (${t.common.harness}: ${x.harness})`),
		...(src ? (Array.isArray(src) ? src : [src]) : [])
	]);
</script>

<svelte:element this={as} class="source"><span class="k">{t.common.source}:</span> {parts.join(' · ')}</svelte:element>

<style>
	.source {
		display: block;
		margin-top: var(--sp-2);
		overflow-wrap: anywhere;
	}
	.k {
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}
</style>
