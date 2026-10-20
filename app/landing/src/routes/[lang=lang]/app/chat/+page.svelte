<script lang="ts">
	import { tick } from 'svelte';
	import { currentLang, href, num } from '$lib/i18n';
	import { findModel, TOK_PER_WORD, type Model } from '$lib/estimator';
	import { T } from '$lib/desktop/i18n';
	import { proto } from '$lib/desktop/state.svelte';
	import { ACTIVE, ACTIVE_MODEL_ID } from '$lib/desktop/demo';
	import Icon from '$lib/desktop/Icon.svelte';
	import Mark from '$lib/desktop/Mark.svelte';
	import Src from '$lib/desktop/Src.svelte';

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const c = $derived(t.chat);

	type Pick = 'S' | 'M' | 'L' | 'PL';
	const PICKS: { key: Pick; model: Model }[] = [
		{ key: 'S', model: findModel('qwen35-4b-q4km')! },
		{ key: 'M', model: findModel('gemma4-12b-q4kxl')! },
		{ key: 'L', model: findModel(ACTIVE_MODEL_ID)! },
		{ key: 'PL', model: findModel('bielik-11b-q8')! }
	];
	let pick = $state<Pick>('L');
	const model = $derived(PICKS.find((p) => p.key === pick)!.model);
	// Only the large model has a measured speed on this card (our engine, MTP).
	const measured = $derived(model.id === ACTIVE_MODEL_ID ? ACTIVE : null);
	const wps = $derived(measured ? Math.round(measured.value / TOK_PER_WORD[lang]) : null);

	type Msg = { role: 'user' | 'assistant' | 'proto'; text: string };
	let cleared = $state(false);
	let extra = $state<Msg[]>([]);
	const messages = $derived<Msg[]>([...(cleared ? [] : c.messages), ...extra]);
	let draft = $state('');
	let composer: HTMLTextAreaElement | undefined = $state();

	function send(e: SubmitEvent) {
		e.preventDefault();
		const text = draft.trim();
		if (!text) return;
		extra.push({ role: 'user', text }, { role: 'proto', text: '' });
		draft = '';
	}
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
			e.preventDefault();
			(e.currentTarget as HTMLTextAreaElement).form?.requestSubmit();
		}
	}
	function newChat() {
		cleared = true;
		extra = [];
		composer?.focus();
	}
	async function dismissNotice() {
		proto.aiNoticeDismissed = true;
		await tick();
		composer?.focus();
	}
</script>

<svelte:head>
	<title>{t.shell.title(c.title)}</title>
</svelte:head>

<div class="wrap">
	<section class="chat" aria-labelledby="chat-h">
		<header class="chat-bar">
			<h1 id="chat-h" class="h3">{c.title}</h1>
			<div class="segmented" role="radiogroup" aria-label={c.picker}>
				{#each PICKS as p (p.key)}
					<label title="{p.model.name} {p.model.quant}">
						<input type="radio" name="brain" value={p.key} bind:group={pick} />
						<span>{c.pick[p.key]}</span>
					</label>
				{/each}
			</div>
			<button type="button" class="btn btn--ghost btn--sm new" onclick={newChat}>
				<Icon name="plus" size={16} />{c.newChat}
			</button>
		</header>

		<div class="chips">
			<span class="chip model">{model.name} <span class="mute">{model.quant}</span></span>
			<span class="chip ok"><span class="led" aria-hidden="true"></span>{t.shell.gpuOk}</span>
			{#if wps !== null}
				<span class="chip speed num">{c.speed(String(wps), wps)}</span>
			{:else}
				<span class="chip none">{c.speedNone}</span>
			{/if}
		</div>
		{#if measured}
			<Src m={measured} src={c.speedSrc(num(measured.value, lang), num(TOK_PER_WORD[lang], lang, 2))} />
		{/if}

		{#if !proto.aiNoticeDismissed}
			<section class="notice notice--info ai" aria-labelledby="ai-h">
				<span class="notice__icon" aria-hidden="true">AI</span>
				<div class="ai-body">
					<h2 id="ai-h" class="ai-title">{c.aiTitle}</h2>
					<p>{c.aiBody}</p>
					<p class="source">{c.aiLaw}</p>
				</div>
				<button type="button" class="btn btn--secondary btn--sm dismiss" onclick={dismissNotice}>{c.aiDismiss}</button>
			</section>
		{/if}

		{#if !cleared}
			<p class="sample small"><span class="badge badge--prototype">{t.common.example}</span>{c.sample}</p>
		{/if}

		<ol class="msgs" aria-label={c.messagesLabel} aria-live="polite">
			{#each messages as m, i (i)}
				{#if m.role === 'user'}
					<li class="msg user">
						<span class="sr-only">{c.you}:</span>
						<p class="bubble">{m.text}</p>
					</li>
				{:else}
					<li class="msg ai-msg">
						<span class="who"><Mark size={18} /><span>{model.name}</span>{#if m.role === 'proto'}<span class="badge badge--prototype">{c.protoLabel}</span>{/if}</span>
						<p class="text">{m.role === 'proto' ? c.protoReply : m.text}</p>
					</li>
				{/if}
			{:else}
				<li class="empty mute">{c.empty}</li>
			{/each}
		</ol>

		<form class="composer" onsubmit={send}>
			<label class="sr-only" for="msg">{c.composer}</label>
			<textarea
				id="msg"
				class="textarea"
				rows="2"
				placeholder={c.placeholder}
				bind:value={draft}
				bind:this={composer}
				onkeydown={onKey}
			></textarea>
			<button type="submit" class="btn btn--primary send" disabled={!draft.trim()}>
				<Icon name="send" size={16} /><span>{c.send}</span>
			</button>
		</form>
		<p class="footer small mute">{c.footer}</p>
	</section>

	<aside class="card ui-panel" aria-labelledby="ui-h">
		<h2 id="ui-h" class="h3">{c.panelTitle}</h2>
		<ol class="steps-list">
			{#each c.panel as p, i (p)}
				<li><span class="step-index">{String(i + 1).padStart(2, '0')}</span><span>{p}</span></li>
			{/each}
		</ol>
		<Src src={c.panelSrc} />
		<a class="small" href={href(lang, '/app/developers')}>{t.nav.developers} →</a>
	</aside>
</div>

<style>
	.wrap {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(16rem, 20rem);
		gap: var(--sp-5);
		align-items: start;
	}
	.chat {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--sp-3);
		min-width: 0;
		padding: var(--sp-5);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background: var(--bg-1);
	}
	.chat-bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3);
		padding-bottom: var(--sp-3);
		border-bottom: 1px solid var(--line);
	}
	.new {
		margin-left: auto;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
		padding: 0.25rem 0.7rem;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		background: var(--bg-2);
		font-size: var(--fs-xs);
		color: var(--text-hi);
	}
	.chip.ok {
		color: var(--text-hi);
		border-color: var(--ok);
		background: var(--ok-soft);
	}
	.chip.speed {
		color: var(--accent-ink);
		border-color: var(--accent-ink);
		background: var(--accent-soft);
	}
	.chip.none {
		color: var(--text-mute);
		border-style: dashed;
	}
	.led {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 50%;
		background: var(--ok);
	}
	.ai {
		grid-template-columns: auto 1fr auto;
		align-items: start;
	}
	.ai-title {
		font-size: var(--fs-sm);
		color: var(--text-hi);
	}
	.ai-body {
		display: grid;
		gap: var(--sp-1);
	}
	.sample {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
		color: var(--text-mute);
	}
	.msgs {
		list-style: none;
		margin: 0;
		padding: var(--sp-4) 0;
		display: grid;
		gap: var(--sp-6);
		min-height: 16rem;
		align-content: start;
	}
	.msg.user {
		justify-self: end;
		max-width: min(36rem, 85%);
	}
	.bubble {
		padding: var(--sp-3) var(--sp-4);
		border-radius: var(--r-lg) var(--r-lg) var(--r-xs) var(--r-lg);
		background: var(--bg-3);
		color: var(--text-hi);
	}
	.ai-msg {
		display: grid;
		gap: var(--sp-2);
		max-width: 46rem;
	}
	.who {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.text {
		color: var(--text);
		line-height: var(--lh-body);
	}
	.empty {
		padding: var(--sp-8) 0;
		text-align: center;
	}
	.composer {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: var(--sp-2);
		align-items: end;
		padding: var(--sp-2);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-lg);
		background: var(--bg-2);
	}
	.composer:focus-within {
		border-color: var(--focus);
	}
	.composer .textarea {
		border: 0;
		background: transparent;
		resize: vertical;
		min-height: 3rem;
		box-shadow: none;
	}
	.send:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
	.footer {
		text-align: center;
	}
	.ui-panel {
		display: grid;
		gap: var(--sp-4);
	}
	.steps-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-3);
		font-size: var(--fs-sm);
	}
	.steps-list li {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-3);
	}

	@media (max-width: 1100px) {
		.wrap {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 520px) {
		.ai {
			grid-template-columns: auto 1fr;
		}
		.chat {
			padding: var(--sp-4);
		}
		.chat-bar .segmented {
			display: flex;
			width: 100%;
		}
		.chat-bar .segmented label {
			flex: 1 1 auto;
		}
		.chat-bar .segmented span {
			padding-inline: 0.5rem;
			text-align: center;
		}
		.dismiss {
			grid-column: 2;
			justify-self: start;
		}
		.send span {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip: rect(0, 0, 0, 0);
		}
	}
</style>
