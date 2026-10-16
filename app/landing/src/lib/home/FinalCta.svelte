<script lang="ts">
	/** Final CTA: the needle sweeps into the redline (our engine on the hero run) when it scrolls in. */
	import { magnetic, reveal } from '$lib/fx/actions';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import Tacho from '$lib/fx/Tacho.svelte';
	import Odometer from '$lib/fx/Odometer.svelte';
	import { cardsHref, href, num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { DIAL_MAX, fill, HERO_CARD, HERO_MODEL, HERO_RUN, HERO_V, REDLINE } from './data';
	import Duo from './Duo.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].final);
	const v = HERO_V.a2.decode!;
	let on = $state(false);
	const label = $derived(fill(c.tacho, { card: HERO_CARD.name, v: num(v.v, lang) }));
</script>

<section class="final" aria-labelledby="final-title">
	<div class="heat" class:on aria-hidden="true"></div>
	<div class="inner">
		<div class="dial" use:reveal={{ threshold: 0.4, onin: () => (on = true) }}>
			<Tacho value={on ? v.v : 0} max={DIAL_MAX} redline={REDLINE} {label}>
				<span class="ro">
					<span class="big"><Odometer value={on ? v.v : 0} decimals={1} {lang} duration={1600} minInt={2} /></span>
					<span class="u">t/s</span>
				</span>
			</Tacho>
			<p class="cap">
				{HERO_CARD.name} · {HERO_MODEL} {HERO_RUN.quant}
				<SourceTip {lang} src={v.src} note="{HERO_RUN.metric[lang]}. {HERO_RUN.conditions[lang]}." />
			</p>
		</div>
		<div class="copy">
			<Duo text={c.title} id="final-title" />
			<p class="lede">{c.lede}</p>
			<div class="ctas">
				<a class="cta cta--bone" href={cardsHref(lang)} use:magnetic>{c.cards} <span class="arrow" aria-hidden="true">→</span></a>
				<a class="cta cta--line" href={href(lang, '/methodology')} use:magnetic>{c.method}</a>
			</div>
		</div>
	</div>
</section>

<style>
	.final {
		position: relative;
		overflow: clip;
		padding-block: clamp(4rem, 3rem + 4vw, 7rem);
		border-top: 1px solid var(--line);
		background: var(--bg-0);
		isolation: isolate;
	}
	.heat {
		position: absolute;
		inset: auto -20% -40% -20%;
		height: 100%;
		z-index: -1;
		background:
			radial-gradient(35% 45% at 25% 85%, rgb(255 122 26 / 0.32), transparent 70%),
			radial-gradient(60% 60% at 30% 100%, rgb(226 64 28 / 0.45), rgb(122 46 31 / 0.15) 50%, transparent 75%);
		opacity: 0;
		transition: opacity 2s var(--ease-out) 0.6s;
	}
	.heat.on {
		opacity: 1;
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
		gap: clamp(2rem, 6vw, 6rem);
		align-items: center;
	}
	.dial {
		display: grid;
		justify-items: center;
		gap: var(--sp-4);
	}
	.dial :global(.tacho) {
		width: min(100%, 30rem);
	}
	.ro {
		display: grid;
		justify-items: center;
		gap: 0.2rem;
	}
	.big {
		font-size: clamp(2.6rem, 1.5rem + 3vw, 4.5rem);
		font-weight: 400;
		letter-spacing: -0.05em;
		color: var(--heat-5);
		filter: drop-shadow(0 0 16px rgb(255 122 26 / 0.5));
	}
	.u {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		letter-spacing: 0.12em;
	}
	.cap {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: center;
		gap: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.copy {
		display: grid;
		gap: var(--sp-6);
	}
	.ctas {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
	}
	@media (max-width: 900px) {
		.inner {
			grid-template-columns: minmax(0, 1fr);
		}
		.dial {
			order: 2;
		}
	}
</style>
