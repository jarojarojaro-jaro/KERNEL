<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { currentLang, href } from '$lib/i18n';
	import CopyButton from '$lib/ui/CopyButton.svelte';
	import { ob } from '$lib/onboarding/copy';
	import Shell from '$lib/onboarding/Shell.svelte';
	import tuiEn from '$lib/data/tui-result-en.txt?raw';
	import tuiPl from '$lib/data/tui-result-pl.txt?raw';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].terminal);
	const s = $derived(ob[lang].scan);
	const cli = BRAND.cli;
	const installs = [
		{ os: 'Windows', shell: 'PowerShell', cmd: `winget install ${BRAND.ascii}` },
		{ os: 'macOS', shell: 'Terminal', cmd: `brew install --cask ${BRAND.ascii}` },
		{ os: 'Linux', shell: 'bash', cmd: `curl -fsSL https://${BRAND.domain ?? '<domain>'}/install.sh | sh` }
	];
	const then = $derived([
		[`${cli} login`, t.login],
		[`${cli}`, t.tui],
		[`${cli} tune --overnight --resume`, t.tune],
		[`${cli} tune status`, t.status]
	]);
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell step={3} title={t.title} lead={t.lead}>
	<div class="stack" style="--stack: var(--sp-4)">
		{#each installs as i (i.os)}
			<div class="codeblock">
				<div class="codeblock__head">
					<span>{i.os} · {i.shell} · <span class="badge badge--soon">{t.notYet}</span></span>
					<CopyButton text={i.cmd} label={i.os} />
				</div>
				<pre><code><span class="prompt">$ </span>{i.cmd}</code></pre>
			</div>
		{/each}
	</div>
	<section class="stack" aria-labelledby="then-title" style="--stack: var(--sp-3)">
		<h2 id="then-title" class="h3">{t.then}</h2>
		<dl class="then">
			{#each then as [c, d] (c)}<dt><code>{c}</code></dt><dd>{d}</dd>{/each}
		</dl>
	</section>
	<section class="stack" aria-labelledby="tui-title" style="--stack: var(--sp-3)">
		<h2 id="tui-title" class="h3">{t.preview}</h2>
		<!-- svelte-ignore a11y_no_noninteractive_tabindex (scrollable region must be keyboard-focusable, WCAG 2.1.1) -->
		<pre class="tui" tabindex="0" aria-label={t.previewNote}><code>{lang === 'pl' ? tuiPl : tuiEn}</code></pre>
		<p class="source">{t.previewNote} <a href={href(lang, '/methodology')}>{ob[lang].result.howTitle} →</a></p>
	</section>
</Shell>

<style>
	.codeblock pre {
		white-space: pre-wrap;
		word-break: break-all;
	}
	.then {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-3) var(--sp-6);
		margin: 0;
	}
	.then dt code {
		color: var(--text-hi);
	}
	.then dd {
		margin: 0;
		color: var(--text);
	}
	.tui {
		margin: 0;
		max-width: 100%;
		padding: var(--sp-5);
		background: var(--bg-1);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		color: var(--text);
		font-size: var(--fs-xs);
		line-height: 1.45;
		overflow-x: auto;
	}
	@media (max-width: 560px) {
		.then {
			grid-template-columns: 1fr;
		}
	}
</style>
