<script lang="ts">
	/**
	 * Provider tiles (Google · GitHub · Hugging Face), the implied-consent line and the "albo" divider,
	 * shared by sign-in and sign-up. Brand marks: the Google "G" is Google's own asset
	 * (static/brand/google-g.svg, unaltered); GitHub is the Primer mark-github in pure white / black;
	 * Hugging Face is the official hf-logo (static/brand/huggingface.svg). Every tile keeps Google's
	 * neutral fill (#131314 / #FFFFFF) under its mark; the brand tint lives only in the hover ring and
	 * glow, and all three tiles are the same size (equal prominence).
	 *
	 * `layout="stack"`: mark above the text (sign-in); `layout="row"`: mark beside the text, a lower
	 * tile (sign-up, where the form below is taller). Under 600 px both stack.
	 */
	import type { OAuthProvider } from '$lib/auth';
	import { href, type Lang } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';

	interface Props {
		lang: Lang;
		/** "Kontynuuj z" / "Załóż konto przez" */
		via: string;
		busy: OAuthProvider | 'password' | null;
		layout?: 'stack' | 'row';
		/** entrance delay of the first tile, ms */
		delay?: number;
		onpick: (id: OAuthProvider) => void;
	}
	let { lang, via, busy, layout = 'stack', delay = 60, onpick }: Props = $props();
	const t = $derived(ob[lang].account);

	const PROVIDERS: { id: OAuthProvider; name: string }[] = [
		{ id: 'google', name: 'Google' },
		{ id: 'github', name: 'GitHub' },
		{ id: 'huggingface', name: 'Hugging Face' }
	];
</script>

{#if layout === 'row'}<p class="lede in" style="--d:{delay}ms" aria-hidden="true">{via}</p>{/if}
<div class="tiles" class:inline={layout === 'row'}>
	{#each PROVIDERS as p, i (p.id)}
		<button class="tile in {p.id}" style="--d:{delay + i * 60}ms" type="button" disabled={busy !== null} onclick={() => onpick(p.id)}>
			<span class="sweep" aria-hidden="true"></span>
			<span class="mark" aria-hidden="true">
				{#if p.id === 'google'}
					<img src="/brand/google-g.svg" width="20" height="20" alt="" />
				{:else if p.id === 'huggingface'}
					<img src="/brand/huggingface.svg" width="20" height="20" alt="" />
				{:else}
					<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M10.226 17.284c-2.965-.36-5.054-2.493-5.054-5.256 0-1.123.404-2.336 1.078-3.144-.292-.741-.247-2.314.09-2.965.898-.112 2.111.36 2.83 1.01.853-.269 1.752-.404 2.853-.404 1.1 0 1.999.135 2.807.382.696-.629 1.932-1.1 2.83-.988.315.606.36 2.179.067 2.942.72.854 1.101 2 1.101 3.167 0 2.763-2.089 4.852-5.098 5.234.763.494 1.28 1.572 1.28 2.807v2.336c0 .674.561 1.056 1.235.786 4.066-1.55 7.255-5.615 7.255-10.646C23.5 6.188 18.334 1 11.978 1 5.62 1 .5 6.188.5 12.545c0 4.986 3.167 9.12 7.435 10.669.606.225 1.19-.18 1.19-.786V20.63a2.9 2.9 0 0 1-1.078.224c-1.483 0-2.359-.808-2.987-2.313-.247-.607-.517-.966-1.034-1.033-.27-.023-.359-.135-.359-.27 0-.27.45-.471.898-.471.652 0 1.213.404 1.797 1.235.45.651.921.943 1.483.943.561 0 .92-.202 1.437-.719.382-.381.674-.718.944-.943" /></svg>
				{/if}
			</span>
			<span class="tile-text">
				<span class="via">{busy === p.id ? t.busy : via}</span>
				<span class="name">{p.name}</span>
			</span>
		</button>
	{/each}
</div>
<p class="implied in" style="--d:{delay + 180}ms">{t.implied} <a href={href(lang, '/legal/terms')}>{t.termsLink}</a> {t.and} <a href={href(lang, '/legal/privacy')}>{t.privacyLink}</a>.</p>
<p class="or in" style="--d:{delay + 180}ms"><span>{t.or}</span></p>

<style>
	@media (prefers-reduced-motion: no-preference) {
		.in {
			animation: rise 0.32s var(--ease-out) var(--d) both;
		}
	}
	@keyframes rise {
		from {
			opacity: 0.01;
			transform: translate3d(0, 0.75rem, 0);
		}
	}
	.tiles {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-3);
	}
	.tile {
		--fill: #131314;
		--stroke: #8e918f;
		--ink: #e3e3e3;
		--mark: #ffffff;
		position: relative;
		display: grid;
		justify-items: center;
		align-content: center;
		gap: var(--sp-2);
		min-height: clamp(4.75rem, 10.5vh, 6.5rem);
		padding: var(--sp-3) var(--sp-2);
		border: 1px solid color-mix(in srgb, var(--stroke) 70%, transparent);
		border-radius: var(--r-lg);
		background: color-mix(in srgb, var(--fill) 88%, transparent);
		color: var(--ink);
		font: inherit;
		text-align: center;
		cursor: pointer;
		overflow: hidden;
		transition:
			transform 0.45s var(--ease-spring),
			box-shadow var(--dur-3) var(--ease-out),
			border-color var(--dur-3) var(--ease-out);
	}
	.inline .tile {
		grid-template-columns: auto minmax(0, 1fr);
		justify-items: start;
		align-items: center;
		gap: var(--sp-3);
		min-height: 3.5rem;
		padding: var(--sp-2) var(--sp-3);
		text-align: left;
	}
	.inline .mark {
		width: 1.6rem;
	}
	:global(:root[data-theme='light']) .tile {
		--fill: #ffffff;
		--stroke: #747775;
		--ink: #1f1f1f;
		--mark: #000000;
	}
	/* brand tint: a ring and a glow underneath, never on the mark's own background */
	.tile::before {
		content: '';
		position: absolute;
		inset: 0;
		padding: 1.5px;
		border-radius: inherit;
		background: var(--ring);
		opacity: 0;
		transition: opacity var(--dur-3) var(--ease-out);
		-webkit-mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		-webkit-mask-composite: xor;
		mask-composite: exclude;
		pointer-events: none;
	}
	.google {
		--ring: conic-gradient(from 200deg, #4285f4, #34a853, #fbbc05, #ea4335, #4285f4);
		--glow:
			-14px 18px 34px -20px #4285f4, 0 22px 34px -20px #fbbc05, 14px 18px 34px -20px #ea4335;
	}
	.github {
		--ring: linear-gradient(160deg, #ffffff, #6e7681 60%, #30363d);
		--glow: 0 22px 40px -20px rgb(255 255 255 / 0.55);
	}
	:global(:root[data-theme='light']) .github {
		--ring: linear-gradient(160deg, #24292f, #6e7681);
		--glow: 0 22px 40px -20px rgb(36 41 47 / 0.6);
	}
	.huggingface {
		--ring: linear-gradient(160deg, #ffd21e, #ff9d00);
		--glow: 0 22px 40px -18px rgb(255 210 30 / 0.75);
	}
	.sweep {
		position: absolute;
		inset: -20% -60%;
		background: linear-gradient(105deg, transparent 40%, rgb(255 255 255 / 0.16) 50%, transparent 60%);
		transform: translate3d(-60%, 0, 0);
		pointer-events: none;
	}
	.mark {
		display: grid;
		place-items: center;
		width: clamp(1.9rem, 1.5rem + 1.2vw, 2.4rem);
		aspect-ratio: 1;
		color: var(--mark);
		transition: transform 0.45s var(--ease-spring);
	}
	.mark img,
	.mark svg {
		width: 100%;
		height: 100%;
	}
	.tile-text {
		display: grid;
		line-height: 1.2;
	}
	.via {
		color: color-mix(in srgb, var(--ink) 62%, transparent);
		font-size: var(--fs-2xs);
		letter-spacing: 0.02em;
	}
	.name {
		font-family: 'Google Sans', Roboto, var(--font-sans);
		font-size: var(--fs-sm);
		font-weight: 600;
	}
	.tile:not(:disabled):hover {
		transform: translate3d(0, -3px, 0);
		border-color: transparent;
		box-shadow: var(--glow);
	}
	.tile:not(:disabled):hover::before {
		opacity: 1;
	}
	.tile:not(:disabled):hover .mark {
		transform: scale(1.12);
	}
	.tile:not(:disabled):hover .sweep {
		transform: translate3d(60%, 0, 0);
		transition: transform 0.7s var(--ease-out);
	}
	.tile:active:not(:disabled) {
		transform: scale(0.96);
		transition-duration: 0.12s;
	}
	.tile:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 3px;
	}
	.tile:focus-visible::before {
		opacity: 1;
	}
	.tile:disabled {
		cursor: progress;
	}

	.implied {
		margin-top: calc(-1 * var(--sp-1));
		color: var(--text-mute);
		font-size: var(--fs-xs);
		text-align: center;
		text-wrap: balance;
	}
	.implied a {
		color: var(--text);
	}
	.or {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		align-items: center;
		gap: var(--sp-3);
		color: var(--text-mute);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
	}
	.or::before,
	.or::after {
		content: '';
		height: 1px;
		background: linear-gradient(90deg, transparent, var(--line-strong));
	}
	.or::after {
		background: linear-gradient(90deg, var(--line-strong), transparent);
	}
	.lede {
		display: none;
	}

	@media (max-width: 600px) {
		.tiles {
			gap: var(--sp-2);
		}
		.tile,
		.inline .tile {
			grid-template-columns: none;
			justify-items: center;
			text-align: center;
			min-height: 4.25rem;
			padding: var(--sp-2) var(--sp-1);
			gap: 0.3rem;
		}
		.mark,
		.inline .mark {
			width: 1.75rem;
		}
		/* sign-up on phones: "Załóż konto przez" once above the row; each tile keeps it in its name */
		.lede {
			display: block;
			margin-bottom: calc(-1 * var(--sp-1));
			color: var(--text-mute);
			font-size: var(--fs-xs);
			text-align: center;
		}
		.inline .via {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip-path: inset(50%);
			white-space: nowrap;
		}
		.inline .tile {
			min-height: 3.75rem;
		}
		.name {
			font-size: var(--fs-xs);
		}
	}
</style>
