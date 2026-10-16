<script lang="ts">
	import { currentLang } from '$lib/i18n';
	import { T } from './i18n';
	import { proto } from './state.svelte';
	import { telemetryPayload } from './demo';
	import Icon from './Icon.svelte';
	import CopyButton from '$lib/ui/CopyButton.svelte';

	/** "Show what we would send" (report 06 §2.2.1): the exact JSON, `{}` while telemetry is off. */
	const t = $derived(T[currentLang()]);
	const id = $props.id();
	let open = $state(false);
	const json = $derived(proto.telemetry ? JSON.stringify(telemetryPayload(), null, 2) : '{}');
</script>

<div class="send">
	<button
		type="button"
		class="btn btn--secondary btn--sm"
		aria-expanded={open}
		aria-controls="{id}-preview"
		onclick={() => (open = !open)}
	>
		<Icon name={open ? 'eyeOff' : 'eye'} size={16} />
		{open ? t.send.hide : t.send.show}
	</button>
	<div id="{id}-preview" class="preview" hidden={!open}>
		<div class="codeblock">
			<div class="codeblock__head">
				<span>{t.send.title} · JSON</span>
				<CopyButton text={json} label="JSON" />
			</div>
			<!-- svelte-ignore a11y_no_noninteractive_tabindex (scrollable region must be keyboard-reachable, WCAG 2.1.1) -->
			<pre tabindex="0" aria-label="{t.send.title} (JSON)"><code>{json}</code></pre>
		</div>
		<p class="small note">{proto.telemetry ? t.send.full : t.send.empty}</p>
		{#if proto.telemetry}<p class="small mute">{t.send.resultsNote}</p>{/if}
	</div>
</div>

<style>
	.send {
		display: grid;
		gap: var(--sp-3);
		justify-items: start;
	}
	.preview {
		width: 100%;
		display: grid;
		gap: var(--sp-2);
	}
	pre {
		max-height: 22rem;
	}
	.note {
		color: var(--text);
	}
</style>
