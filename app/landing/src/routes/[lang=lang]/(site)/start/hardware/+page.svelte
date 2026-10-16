<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount, tick } from 'svelte';
	import { findGpu, matchGpu, type Gpu, type Os } from '$lib/estimator';
	import { parseHwCode, type HwCode } from '$lib/hwcode';
	import { cardsCopy } from '$lib/cards/copy';
	import { cardsHref, currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import GpuCombobox from '$lib/onboarding/GpuCombobox.svelte';
	import ScanCommands from '$lib/onboarding/ScanCommands.svelte';
	import Shell from '$lib/onboarding/Shell.svelte';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].hw);

	const VRAM = [4, 6, 8, 10, 12, 16, 20, 24, 32, 48];
	const RAM = [8, 16, 24, 32, 48, 64, 96, 128, 192];
	const OSES: Os[] = ['windows', 'linux', 'macos'];

	let gpu = $state<Gpu | null>(null);
	let vram = $state(12);
	let ram = $state(32);
	let os = $state<Os>('windows');
	let tried = $state(false);
	let pasted = $state('');
	let pasteMsg = $state<{ kind: 'ok' | 'warn' | 'danger'; text: string }[]>([]);
	let decoded = $state<HwCode | null>(null);

	const unified = $derived(!!gpu?.unified);

	onMount(() => {
		const ua = navigator.userAgent;
		os = /Mac OS X/.test(ua) ? 'macos' : /Linux/.test(ua) && !/Android/.test(ua) ? 'linux' : 'windows';
		// Returning from the result page keeps the previous answers.
		const q = new URLSearchParams(location.search);
		const g = findGpu(q.get('gpu'));
		if (g) gpu = g;
		if (q.get('vram')) vram = Number(q.get('vram'));
		if (q.get('ram')) ram = Number(q.get('ram'));
		if (OSES.includes(q.get('os') as Os)) os = q.get('os') as Os;
		tick().then(() => (restoring = false));
	});

	// Defaults follow the chosen card only when the card changes (not when restoring saved answers).
	let lastGpu: string | null = null;
	let restoring = true;
	$effect(() => {
		const id = gpu?.id ?? null;
		if (id === lastGpu) return;
		lastGpu = id;
		if (restoring) return;
		if (gpu?.vram) vram = gpu.vram;
		if (gpu?.vendor === 'apple') os = 'macos';
	});

	const nearest = (list: number[], v: number) => list.reduce((a, b) => (Math.abs(b - v) < Math.abs(a - v) ? b : a));

	async function fromCode() {
		const r = parseHwCode(pasted);
		pasteMsg = [];
		decoded = null;
		if (!r.ok) {
			pasteMsg = [{ kind: 'danger', text: r.error === 'checksum' ? t.pasteErrSum : t.pasteErrFormat }];
			return;
		}
		const c = r.code;
		decoded = c;
		const vramGiB = c.vram ? Number(c.vram) : null;
		const g = (c.sub && matchGpu(c.sub, vramGiB)) || (c.gpu && matchGpu(c.gpu, vramGiB)) || null;
		if (c.os && OSES.includes(c.os as Os)) os = c.os as Os;
		if (c.ram) ram = nearest(RAM, Number(c.ram));
		if (g) {
			gpu = g;
			await tick();
		}
		if (vramGiB) vram = nearest(VRAM, vramGiB);
		pasteMsg = [{ kind: 'ok', text: t.pasteOk }];
		if (!g) pasteMsg.push({ kind: 'warn', text: t.pasteGpuUnknown });
		else if (!vramGiB && !g.unified && !g.cpuOnly) pasteMsg.push({ kind: 'warn', text: t.pasteVramUnknown });
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		tried = true;
		if (!gpu) {
			await tick();
			document.getElementById('gpu-input')?.focus();
			return;
		}
		const q = new URLSearchParams({ gpu: gpu.id, ram: String(ram), os });
		if (!gpu.unified && !gpu.cpuOnly) q.set('vram', String(vram));
		goto(`${href(lang, '/start/result')}?${q}`);
	}
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell step={2} title={t.title} lead={t.lead} wide>
	<div class="grid">
		<form class="card heat-card stack hw-form" novalidate onsubmit={submit}>
			<GpuCombobox bind:value={gpu} label={t.gpu} placeholder={t.gpuPh} hint={t.gpuHint} none={t.gpuNone} error={tried && !gpu ? t.errGpu : null} />
			<div class="row">
				<div class="field">
					<label for="vram">{t.vram}</label>
					{#if unified || gpu?.cpuOnly}
						<p class="input static" id="vram">{unified ? t.vramUnified : '—'}</p>
					{:else}
						<select id="vram" class="select" bind:value={vram}>
							{#each VRAM as v (v)}<option value={v}>{v} GB</option>{/each}
						</select>
					{/if}
				</div>
				<div class="field">
					<label for="ram">{t.ram}</label>
					<select id="ram" class="select" bind:value={ram}>
						{#each RAM as v (v)}<option value={v}>{v} GB</option>{/each}
					</select>
				</div>
			</div>
			<fieldset class="field os">
				<legend class="label">{t.os}</legend>
				<div class="segmented">
					{#each OSES as o (o)}
						<label><input type="radio" name="os" value={o} bind:group={os} /><span>{o === 'macos' ? 'macOS' : o === 'linux' ? 'Linux' : 'Windows'}</span></label>
					{/each}
				</div>
			</fieldset>
			<button class="btn btn--primary btn--lg btn--block" type="submit">{t.submit} <span class="arrow" aria-hidden="true">→</span></button>
			<a class="btn btn--secondary btn--lg btn--block" href={cardsHref(lang)}>{cardsCopy[lang].gallery.hwLink} <span class="arrow" aria-hidden="true">→</span></a>
		</form>

		<section class="card card--inset heat-wash stack scan" aria-labelledby="unknown-title">
			<p class="overline">{lang === 'pl' ? 'Skan' : 'Scan'}</p>
			<h2 id="unknown-title" class="h3">{t.unknownTitle}</h2>
			<p class="small">{t.unknownLead}</p>
			<ScanCommands initial={os} />
			<div class="field">
				<label for="paste">{t.paste}</label>
				<textarea id="paste" class="textarea input--mono" rows="3" placeholder={t.pastePh} bind:value={pasted} spellcheck="false"></textarea>
			</div>
			<button class="btn btn--secondary" type="button" onclick={fromCode} disabled={!pasted.trim()}>{t.pasteBtn}</button>
			<div role="status" class="stack msgs">
				{#each pasteMsg as m (m.text)}
					<div class="notice notice--{m.kind}"><span class="notice__icon">{m.kind === 'ok' ? '✓' : '!'}</span><p>{m.text}</p></div>
				{/each}
			</div>
			{#if decoded}
				<details class="disclosure">
					<summary>{t.decoded}</summary>
					<dl class="decoded disclosure__body">
						{#each Object.entries(decoded) as [k, v] (k)}<dt class="num">{k}</dt><dd>{v ?? '?'}</dd>{/each}
					</dl>
				</details>
			{/if}
		</section>
	</div>
</Shell>

<style>
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
		gap: var(--sp-6);
		align-items: start;
	}
	.hw-form {
		padding: clamp(1.25rem, 0.8rem + 2vw, 2.25rem);
	}
	.hw-form :global(.label),
	.hw-form label {
		font-size: var(--fs-sm);
	}
	.scan {
		overflow: hidden;
	}
	@media (max-width: 900px) {
		.grid {
			grid-template-columns: 1fr;
		}
	}
	form {
		--stack: var(--sp-5);
	}
	.row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-4);
	}
	.os {
		border: 0;
		padding: 0;
		margin: 0;
	}
	.os legend {
		margin-bottom: var(--sp-2);
	}
	.static {
		display: flex;
		align-items: center;
		margin: 0;
		color: var(--text-mute);
		font-size: var(--fs-sm);
		background: var(--bg-3);
	}
	.scan {
		--stack: var(--sp-4);
	}
	.msgs {
		--stack: var(--sp-2);
	}
	.decoded {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-1) var(--sp-4);
		font-size: var(--fs-sm);
		margin: 0;
	}
	.decoded dt {
		color: var(--text-mute);
	}
	.decoded dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
</style>
