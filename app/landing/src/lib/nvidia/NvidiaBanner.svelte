<script lang="ts">
	/* One line to the NVIDIA results page: on the NVIDIA maker page and on the results page. */
	import { nvidiaHref, type Lang } from '$lib/i18n';
	import { nvidiaCopy } from '$lib/nvidia/copy';

	let { lang, id = 'nv-banner-t' }: { lang: Lang; id?: string } = $props();
	const nx = $derived(nvidiaCopy[lang].fromCards);
</script>

<section class="wrap nv-banner" aria-labelledby={id}>
	<div class="nv-card">
		<div class="nv-txt">
			<p class="nv-k mono">{nx.kicker}</p>
			<h2 {id} class="nv-h">{nx.text}</h2>
			<p class="nv-b">{nx.body}</p>
		</div>
		<a class="nv-cta" href={nvidiaHref(lang)}>{nx.cta} <span aria-hidden="true">→</span></a>
	</div>
</section>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}
	.mono {
		font-family: var(--font-mono);
	}
	.nv-banner {
		padding-top: clamp(2rem, 4vw, 3rem);
	}
	.nv-card {
		display: grid;
		gap: var(--sp-4);
		align-items: center;
		padding: var(--sp-5) var(--sp-6);
		border: 1px solid color-mix(in srgb, var(--heat-3) 45%, var(--line));
		border-radius: var(--r-xl);
		background: linear-gradient(120deg, color-mix(in srgb, var(--heat-3) 9%, var(--bg-2)), var(--bg-2) 62%);
	}
	@media (min-width: 48rem) {
		.nv-card {
			grid-template-columns: minmax(0, 1fr) auto;
			gap: var(--sp-6);
		}
	}
	.nv-k {
		margin: 0 0 var(--sp-1);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--accent-ink);
	}
	.nv-h {
		margin: 0;
		font-size: var(--fs-md);
		letter-spacing: -0.015em;
		color: var(--text-hi);
	}
	.nv-b {
		margin: var(--sp-1) 0 0;
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.nv-cta {
		display: inline-flex;
		align-items: center;
		gap: 0.4em;
		min-height: 2.75rem;
		padding: 0 var(--sp-5);
		border-radius: var(--r-pill);
		border: 1px solid var(--line-strong);
		background: var(--bg-3);
		color: var(--text-hi);
		font-size: var(--fs-sm);
		font-weight: 600;
		text-decoration: none;
		justify-self: start;
		transition:
			border-color var(--dur-2),
			background-color var(--dur-2);
	}
	.nv-cta:hover,
	.nv-cta:focus-visible {
		border-color: var(--heat-3);
		background: var(--bg-2);
	}
	.nv-cta span {
		color: var(--heat-3);
	}
</style>
