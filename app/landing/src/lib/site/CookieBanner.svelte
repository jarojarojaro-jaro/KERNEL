<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { currentLang, href } from '$lib/i18n';
	import { consent, initConsent, saveConsent } from './consent.svelte';
	import { copy } from './copy';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang].cookies);
	let panel: HTMLElement | undefined = $state();

	onMount(initConsent);

	$effect(() => {
		// Reopened from the footer: move focus to the bar. On the first visit we do not steal focus.
		if (consent.open && consent.record) tick().then(() => panel?.focus());
	});
</script>

{#if consent.ready && consent.open}
	<section class="cookie" aria-labelledby="cookie-title" tabindex="-1" bind:this={panel}>
		<h2 id="cookie-title" class="sr-only">{t.title}</h2>
		<p class="text">
			<span class="dot" aria-hidden="true"></span>
			<span>{t.body} <a href={href(lang, '/legal/cookies')}>{t.policy}</a></span>
		</p>
		<div class="buttons">
			<button class="btn btn--secondary btn--sm" type="button" onclick={() => saveConsent(false)}>{t.necessaryOnly}</button>
			<button class="accept" type="button" onclick={() => saveConsent(true)}>{t.accept}</button>
		</div>
	</section>
{/if}

<style>
	@property --ck {
		syntax: '<angle>';
		inherits: false;
		initial-value: 0deg;
	}
	/* One line at the bottom: glass bar with a heat-gradient hairline on top. */
	.cookie {
		position: fixed;
		z-index: var(--z-banner);
		inset: auto var(--sp-4) var(--sp-4) var(--sp-4);
		max-width: 68rem;
		margin-inline: auto;
		display: flex;
		align-items: center;
		gap: var(--sp-5);
		padding: var(--sp-3) var(--sp-3) var(--sp-3) var(--sp-5);
		border-radius: var(--r-pill);
		border: 1px solid transparent;
		background:
			linear-gradient(90deg, color-mix(in srgb, var(--bg-2) 92%, transparent), color-mix(in srgb, var(--bg-1) 88%, transparent)) padding-box,
			linear-gradient(90deg, color-mix(in srgb, var(--heat-2) 70%, transparent), var(--heat-3) 35%, var(--heat-4) 65%, color-mix(in srgb, var(--line-strong) 60%, transparent)) border-box;
		backdrop-filter: blur(14px) saturate(1.2);
		-webkit-backdrop-filter: blur(14px) saturate(1.2);
		box-shadow:
			var(--shadow-2),
			0 18px 60px -30px color-mix(in srgb, var(--heat-3) 70%, transparent);
		animation: ck-in 0.5s var(--ease-out) both;
	}
	.cookie:focus {
		outline: none;
	}
	.cookie:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	.text {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		margin: 0;
		font-size: var(--fs-sm);
		color: var(--text-hi);
		line-height: 1.4;
	}
	.text a {
		color: var(--heat-4);
		white-space: nowrap;
	}
	.dot {
		flex: none;
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: var(--heat-3);
		box-shadow: 0 0 10px 2px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	.buttons {
		flex: none;
		display: flex;
		align-items: center;
		gap: var(--sp-2);
	}
	/* Accept: heat gradient with a slowly turning glowing edge (same language as the hero CTA). */
	.accept {
		position: relative;
		isolation: isolate;
		min-height: 2.25rem;
		padding: 0 var(--sp-5);
		border: 0;
		border-radius: var(--r-pill);
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 45%, var(--heat-4));
		color: #140b05;
		font: inherit;
		font-size: var(--fs-xs);
		font-weight: 720;
		letter-spacing: 0.01em;
		cursor: pointer;
		box-shadow:
			inset 0 1px 0 rgb(255 255 255 / 0.35),
			0 10px 30px -10px color-mix(in srgb, var(--heat-3) 90%, transparent);
		transition:
			transform var(--dur-2) var(--ease-out),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.accept::after {
		content: '';
		position: absolute;
		inset: -4px;
		z-index: -1;
		border-radius: inherit;
		background: conic-gradient(from var(--ck), var(--heat-2), var(--heat-4) 20%, var(--heat-5) 28%, var(--heat-3) 45%, transparent 60%, var(--heat-2));
		filter: blur(10px);
		opacity: 0.55;
		animation: ck-turn 4.5s linear infinite;
		transition: opacity var(--dur-3) var(--ease-out);
		pointer-events: none;
	}
	.accept:hover {
		box-shadow:
			inset 0 1px 0 rgb(255 255 255 / 0.45),
			0 14px 40px -10px var(--heat-3);
	}
	.accept:hover::after,
	.accept:focus-visible::after {
		opacity: 0.95;
	}
	.accept:active {
		transform: scale(0.97);
	}
	.accept:focus-visible {
		outline: 2px solid var(--heat-4);
		outline-offset: 3px;
	}
	@keyframes ck-turn {
		to {
			--ck: 360deg;
		}
	}
	@keyframes ck-in {
		from {
			opacity: 0;
			transform: translate3d(0, 16px, 0);
		}
	}
	/* Narrow screens: text above, the two buttons side by side, full width. */
	@media (max-width: 760px) {
		.cookie {
			inset: auto var(--sp-3) var(--sp-3) var(--sp-3);
			flex-direction: column;
			align-items: stretch;
			gap: var(--sp-3);
			padding: var(--sp-4);
			border-radius: var(--r-xl);
		}
		.text {
			align-items: flex-start;
		}
		.dot {
			margin-top: 0.45em;
		}
		.buttons > * {
			flex: 1;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.cookie,
		.accept::after {
			animation: none;
		}
	}
</style>
