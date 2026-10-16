<script lang="ts">
	import { currentLang } from '$lib/i18n';

	/** Copies `text`; `label` names what is copied for screen readers (e.g. "curl"). Shared by site and app. */
	let { text, label = '' }: { text: string; label?: string } = $props();

	const T = {
		pl: { copy: 'Kopiuj', copied: 'Skopiowano', failed: 'Nie udało się skopiować' },
		en: { copy: 'Copy', copied: 'Copied', failed: 'Copy failed' }
	};
	const t = $derived(T[currentLang()]);
	let status = $state<'idle' | 'ok' | 'fail'>('idle');
	let timer: ReturnType<typeof setTimeout> | undefined;

	async function copy() {
		try {
			await navigator.clipboard.writeText(text);
			status = 'ok';
		} catch {
			// Clipboard API unavailable (non-secure origin): fall back to a selection copy.
			const ta = Object.assign(document.createElement('textarea'), { value: text });
			document.body.append(ta);
			ta.select();
			status = document.execCommand('copy') ? 'ok' : 'fail';
			ta.remove();
		}
		clearTimeout(timer);
		timer = setTimeout(() => (status = 'idle'), 2000);
	}
</script>

<button type="button" class="btn btn--ghost btn--sm copy" onclick={copy}>
	<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
		{#if status === 'ok'}<path d="M5 12.5 10 17l9-10" />{:else}<rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h9" />{/if}
	</svg>
	<span>{status === 'ok' ? t.copied : status === 'fail' ? t.failed : t.copy}</span>
	{#if label}<span class="sr-only">{label}</span>{/if}
</button>
<span class="sr-only" role="status">{status === 'ok' ? t.copied : status === 'fail' ? t.failed : ''}</span>

<style>
	.copy {
		--btn-h: 2rem;
		padding-inline: var(--sp-3);
		text-transform: none;
		letter-spacing: 0;
		font-family: var(--font-sans);
	}
</style>
