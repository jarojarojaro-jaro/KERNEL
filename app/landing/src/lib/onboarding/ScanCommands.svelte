<script lang="ts">
	import { onMount } from 'svelte';
	import { currentLang } from '$lib/i18n';
	import CopyButton from '$lib/ui/CopyButton.svelte';
	import { ob } from './copy';

	type Os = 'linux' | 'windows' | 'macos';
	let { initial = 'linux' as Os }: { initial?: Os } = $props();
	const lang = $derived(currentLang());
	const t = $derived(ob[lang].scan);

	let os = $state<Os>('linux');
	let origin = $state('');
	let source = $state<string | null>(null);
	let showSource = $state(false);
	const tabs: Os[] = ['linux', 'windows', 'macos'];
	const file: Record<Os, string> = { linux: 'scan.sh', windows: 'scan.ps1', macos: 'scan-macos.sh' };

	onMount(() => {
		origin = location.origin;
	});
	// Follow the OS chosen in the surrounding form (the user can still switch tabs freely).
	$effect(() => {
		select(initial);
	});

	const cmd = $derived(
		os === 'windows'
			? `irm ${origin}/scan/scan.ps1 | iex`
			: `curl -fsSL ${origin}/scan/${file[os]} | ${os === 'linux' ? 'sh' : 'bash'}`
	);
	const runLocal = $derived(os === 'windows' ? `powershell -ExecutionPolicy Bypass -File .\\scan.ps1` : `${os === 'linux' ? 'sh' : 'bash'} ${file[os]}`);

	function onKey(e: KeyboardEvent) {
		const i = tabs.indexOf(os);
		const next = e.key === 'ArrowRight' ? (i + 1) % 3 : e.key === 'ArrowLeft' ? (i + 2) % 3 : e.key === 'Home' ? 0 : e.key === 'End' ? 2 : -1;
		if (next < 0) return;
		e.preventDefault();
		select(tabs[next]);
		document.getElementById(`scan-tab-${tabs[next]}`)?.focus();
	}

	function select(o: Os) {
		os = o;
		source = null;
		showSource = false;
	}

	async function toggleSource() {
		showSource = !showSource;
		if (showSource && source === null) source = await fetch(`/scan/${file[os]}`).then((r) => r.text());
	}
</script>

<div class="scan">
	<div class="tabs" role="tablist" aria-label={t.title} tabindex="-1" onkeydown={onKey}>
		{#each tabs as o (o)}
			<button
				id="scan-tab-{o}"
				role="tab"
				type="button"
				aria-selected={os === o}
				aria-controls="scan-panel"
				tabindex={os === o ? 0 : -1}
				onclick={() => select(o)}>{t.tabs[o]}</button
			>
		{/each}
	</div>
	<div id="scan-panel" role="tabpanel" aria-labelledby="scan-tab-{os}" class="tabpanel stack">
		<div class="codeblock">
			<div class="codeblock__head">
				<span>{t.oneLiner} · {t.shell[os]}</span>
				<CopyButton text={cmd} label={t.shell[os]} />
			</div>
			<pre><code><span class="prompt">{os === 'windows' ? 'PS> ' : '$ '}</span>{cmd}</code></pre>
		</div>
		<p class="small mute">{t.originNote}</p>
		<div class="cluster">
			<span class="small">{t.download}:</span>
			<a class="btn btn--secondary btn--sm" href="/scan/{file[os]}" download>{file[os]}</a>
			<code class="small mute">{runLocal}</code>
		</div>
		<p class="small"><strong>{t.reads}:</strong> {t.readsBy[os]}</p>
		<div>
			<button class="btn btn--ghost btn--sm" type="button" aria-expanded={showSource} aria-controls="scan-src" onclick={toggleSource}>
				{showSource ? t.hide : t.view}
			</button>
			{#if showSource}
				<div class="codeblock src" id="scan-src">
					<div class="codeblock__head"><span>{file[os]}</span></div>
					<!-- svelte-ignore a11y_no_noninteractive_tabindex (scrollable region must be keyboard-focusable, WCAG 2.1.1) -->
					<pre tabindex="0"><code>{source ?? t.loading}</code></pre>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.scan {
		display: grid;
		gap: var(--sp-4);
	}
	.tabpanel {
		--stack: var(--sp-4);
	}
	.tabpanel pre {
		white-space: pre-wrap;
		word-break: break-all;
	}
	.src pre {
		max-height: 24rem;
		overflow: auto;
		white-space: pre;
		word-break: normal;
		font-size: var(--fs-xs);
	}
</style>
