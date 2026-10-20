<script lang="ts">
	/**
	 * Top of a card page: back link, status, the card's name set huge and its render. The render and
	 * the name share `view-transition-name`s with the gallery tile, so the tile zooms into this.
	 */
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';
	import { cardsHref, currentLang } from '$lib/i18n';
	import { cardsCopy } from './copy';
	import GpuArt from './GpuArt.svelte';
	import { VENDOR, vendorOf } from './vendor';

	let {
		id,
		prefix,
		short,
		vendor,
		vram,
		heat,
		queued = false,
		spec,
		children,
		plate,
		charge = null,
		rpm = 0,
		kick = 0
	}: {
		id: string;
		prefix: string;
		short: string;
		vendor: string;
		vram: number | null;
		heat: number;
		queued?: boolean;
		spec: string;
		children?: Snippet;
		plate?: Snippet;
		/** Driven heat-up (measured cards): see GpuArt. Null = the plain power-on. */
		charge?: number | null;
		rpm?: number;
		/** Becomes > 0 when the driven heat-up lands: a short kick and settle of the card. */
		kick?: number;
	} = $props();

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].card);
	/** The maker's wordmark before the series ("NVIDIA GeForce RTX"), never doubled ("Apple M4"). */
	const maker = $derived(VENDOR[vendorOf(vendor)].name);
	const rest = $derived(maker && prefix.toLowerCase().startsWith(maker.toLowerCase()) ? prefix.slice(maker.length).trim() : prefix);

	// Undriven pages (queue): fans spin briefly when the page opens, then stop (no endless loop).
	let live = $state(false);
	onMount(() => {
		if (charge != null) return;
		live = true;
		const stop = setTimeout(() => (live = false), 4200);
		return () => clearTimeout(stop);
	});
</script>

<section class="head" class:queued aria-labelledby="card-title" style="--hh:{heat * (charge ?? 1)}; --cc:{charge == null ? 0 : 1 - charge}">
	<!-- the maker's band: its colour washes the top of the page and draws the line under the head -->
	<div class="band" aria-hidden="true"></div>
	<div class="wrap">
		<a class="back mono" href={cardsHref(lang)}><span aria-hidden="true">←</span> {t.back}</a>
	</div>
	<div class="wrap grid">
		<div class="copy">
			<p class="status"><span class="dot"></span>{queued ? t.queue : t.measured}</p>
			<h1 id="card-title" class="name" style="view-transition-name: name-{id}">
				<span class="pre">{#if maker}<span class="maker">{maker}</span>{/if} {rest}</span>
				<span class="short {queued ? 'hx-h' : 'hx-grad'}">{short}</span>
			</h1>
			<p class="spec mono">{spec}</p>
			{@render children?.()}
		</div>
		<div class="art-col">
			<div class="art" class:kicked={kick > 0} style="view-transition-name: art-{id}; view-transition-class: gpu">
				<GpuArt label={short} {vendor} {vram} {heat} {live} ignite {charge} {rpm} />
			</div>
			{@render plate?.()}
		</div>
	</div>
</section>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}
	.head {
		position: relative;
		padding: calc(4.25rem + clamp(0.5rem, 2.5vh, 1.75rem)) 0 clamp(1rem, 2.5vh, 2rem);
		isolation: isolate;
	}
	/* the maker's band: a wash of its colour from the top-left and a line under the head */
	.band {
		position: absolute;
		inset: 0;
		z-index: -2;
		pointer-events: none;
		background:
			radial-gradient(55% 75% at 16% 0%, rgb(var(--v, 125 135 148) / 0.24), transparent 72%),
			linear-gradient(180deg, rgb(var(--v, 125 135 148) / 0.09), transparent 78%);
	}
	.band::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 1px;
		background: var(--v-line, var(--line));
		opacity: 0.7;
	}
	/* The card's heat spills onto the page: a wide heat-ramp glow behind the render whose opacity is
	   the measured gain × the current charge (opacity only, so it composites); during the cold start
	   a steel cast takes its place. */
	.head::before,
	.head::after {
		content: '';
		position: absolute;
		inset: -10% 0 -35%;
		z-index: -1;
		pointer-events: none;
	}
	.head::before {
		background:
			radial-gradient(48% 46% at 72% 42%, rgb(255 193 90 / 0.22), transparent 60%),
			radial-gradient(75% 70% at 72% 45%, rgb(255 122 26 / 0.3), transparent 72%),
			radial-gradient(110% 90% at 70% 50%, rgb(226 64 28 / 0.14), transparent 80%);
		opacity: var(--hh);
	}
	.head::after {
		background: radial-gradient(60% 55% at 72% 45%, rgb(125 135 148 / 0.14), transparent 70%);
		opacity: var(--cc);
	}
	.queued::before {
		opacity: 0;
	}
	.queued::after {
		opacity: 0.6;
	}
	@media (prefers-reduced-motion: no-preference) {
		.art.kicked {
			animation: kick 0.6s var(--ease-out);
		}
	}
	@keyframes kick {
		15% {
			transform: translate3d(0, -6px, 0) rotate(-0.6deg);
		}
		35% {
			transform: translate3d(0, 3px, 0) rotate(0.35deg);
		}
		60% {
			transform: translate3d(0, -1px, 0);
		}
	}
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
		align-items: center;
		gap: var(--sp-6) clamp(1.5rem, 4vw, 4rem);
	}
	.copy {
		display: grid;
		gap: var(--sp-3);
		justify-items: start;
		min-width: 0;
	}
	.back {
		display: inline-flex;
		gap: 0.5rem;
		align-items: center;
		min-height: 2.75rem;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		text-decoration: none;
		letter-spacing: 0.04em;
	}
	.back:hover {
		color: var(--text-hi);
	}
	.back {
		transition: color 0.35s var(--ease-out);
	}
	.status {
		display: inline-flex;
		align-items: center;
		gap: 0.55rem;
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text);
	}
	.dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: var(--heat-3);
		box-shadow: 0 0 10px var(--heat-3);
	}
	.queued .dot {
		background: transparent;
		border: 1.5px solid var(--heat-3);
		box-shadow: none;
	}
	.name {
		margin: 0;
		display: grid;
		gap: 0.4rem;
		width: fit-content;
		color: var(--text-hi);
	}
	.pre {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		font-weight: 500;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.maker {
		margin-right: 0.35rem;
		font-family: var(--font-display);
		font-style: italic;
		font-weight: 850;
		letter-spacing: 0.06em;
		color: var(--v-hi, var(--text));
		text-shadow: 0 0 14px rgb(var(--v, 125 135 148) / 0.55);
	}
	:global(:root[data-theme='light']) .maker {
		color: color-mix(in srgb, rgb(var(--v, 125 135 148)) 62%, #000);
		text-shadow: none;
	}
	.short {
		font-family: var(--font-display);
		font-size: clamp(3.2rem, 1rem + 6.6vw, 8.25rem);
		font-weight: 850;
		font-stretch: 112%;
		line-height: 0.86;
		letter-spacing: -0.045em;
	}
	.queued .short {
		color: var(--text);
	}
	.spec {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		letter-spacing: 0.04em;
	}
	.art-col {
		min-width: 0;
		display: grid;
		gap: var(--sp-5);
	}
	@media (max-width: 56rem) {
		.grid {
			grid-template-columns: 1fr;
		}
		.art-col {
			display: contents;
		}
		.art {
			order: -1;
			margin-top: var(--sp-4);
		}
	}
</style>
