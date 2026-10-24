<script lang="ts">
	import Chat from '../components/Chat.svelte';
	import CopyButton from '../components/CopyButton.svelte';
	import Headline from '../components/Headline.svelte';
	import ScreenHead from '../components/ScreenHead.svelte';
	import { api } from '../lib/api';
	import { int } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	const t = $derived(store.t.ready);
	const lang = $derived(store.lang);
	const s = $derived(store.state);
	const ready = $derived(s?.ready ?? null);
	const running = $derived(ready !== null);
	const endpoint = $derived(ready?.endpoint ?? `${location.origin}/v1`);
	const model = $derived(ready?.model ?? s?.chosen?.name ?? '');
	const ctx = $derived(ready?.ctx ?? s?.best?.config.ctx ?? s?.chosen?.ctx ?? 0);
	const windows = $derived(s?.hw?.os === 'windows');

	type Tab = 'omp' | 'sdk' | 'curl';
	const TABS: Tab[] = ['omp', 'sdk', 'curl'];
	const TAB_LABEL: Record<Tab, string> = { omp: 'omp', sdk: 'OpenAI SDK', curl: 'curl' };
	let tab = $state<Tab>('omp');
	const hello = $derived(lang === 'pl' ? 'Cześć!' : 'Hello!');
	const snippet = $derived.by(() => {
		if (tab === 'omp') return windows ? `$env:LLAMA_CPP_BASE_URL = "${endpoint}"\nomp` : `export LLAMA_CPP_BASE_URL=${endpoint}\nomp`;
		if (tab === 'sdk')
			return [
				'from openai import OpenAI',
				'',
				`client = OpenAI(base_url="${endpoint}", api_key="local")`,
				'reply = client.chat.completions.create(',
				`    model="${model}",`,
				`    messages=[{"role": "user", "content": "${hello}"}],`,
				')',
				'print(reply.choices[0].message.content)'
			].join('\n');
		return [
			`curl ${endpoint}/chat/completions \\`,
			`  -H "Content-Type: application/json" \\`,
			`  -d '{"model": "${model}", "messages": [{"role": "user", "content": "${hello}"}], "stream": true}'`
		].join('\n');
	});

	function onTabKey(e: KeyboardEvent) {
		const i = TABS.indexOf(tab);
		let n = i;
		if (e.key === 'ArrowRight') n = (i + 1) % TABS.length;
		else if (e.key === 'ArrowLeft') n = (i - 1 + TABS.length) % TABS.length;
		else if (e.key === 'Home') n = 0;
		else if (e.key === 'End') n = TABS.length - 1;
		else return;
		e.preventDefault();
		tab = TABS[n]!;
		document.getElementById(`tab-${tab}`)?.focus();
	}

	let toggling = $state(false);
	let error = $state('');
	async function toggle() {
		toggling = true;
		error = '';
		try {
			await (running ? api.engineStop() : api.engineStart());
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			toggling = false;
		}
	}
</script>

<section class="screen" aria-labelledby="ready-title">
	<ScreenHead id="ready-title" overline={t.overline} title={t.title} accent={t.titleAccent} lead={t.lead} />

	<div class="panel panel--heat ep">
		<div class="ep-top">
			<p class="state" class:on={running}>
				<span class="dot" aria-hidden="true"></span>{running ? t.running : t.stopped}
			</p>
			<button class="btn btn--secondary btn--sm" type="button" onclick={toggle} disabled={toggling}>
				{#if toggling}<span class="ring" aria-hidden="true"></span>{/if}{running ? t.stop : t.start}
			</button>
		</div>
		<div class="ep-row">
			<p class="eyebrow">{t.endpoint}</p>
			<div class="ep-url">
				<code class="url">{endpoint}</code>
				<CopyButton text={endpoint} label={t.endpoint} />
			</div>
		</div>
		<dl class="facts meta">
			<div><dt>{t.model}</dt><dd><code>{model}</code></dd></div>
			<div><dt>{t.ctx}</dt><dd class="num">{int(ctx, lang)} tok</dd></div>
		</dl>
		{#if error}<p class="error-text" role="alert">{error}</p>{/if}
	</div>

	{#if s?.baseline && (s.best ?? s.baseline)}
		<div class="block">
			<h2 class="panel-title">{t.gains}</h2>
			<Headline base={s.baseline} now={s.best ?? s.baseline} />
		</div>
	{/if}

	<div class="grid-2">
		<div class="panel block">
			<h2 class="panel-title" id="snip-title">{t.snippets}</h2>
			<div class="codeblock">
				<div class="codeblock__head">
					<div class="tablist" role="tablist" aria-label={t.snippetsLabel}>
						{#each TABS as k (k)}
							<button
								type="button"
								role="tab"
								id="tab-{k}"
								aria-selected={tab === k}
								aria-controls="snip-panel"
								tabindex={tab === k ? 0 : -1}
								onclick={() => (tab = k)}
								onkeydown={onTabKey}>{TAB_LABEL[k]}</button
							>
						{/each}
					</div>
					<CopyButton text={snippet} label={TAB_LABEL[tab]} />
				</div>
				<div id="snip-panel" role="tabpanel" aria-labelledby="tab-{tab}" tabindex="0"><pre><code>{snippet}</code></pre></div>
			</div>
		</div>

		<div class="panel block">
			<h2 class="panel-title">{t.chat}</h2>
			<Chat {model} enabled={running} />
		</div>
	</div>
</section>

<style>
	.ep {
		display: grid;
		gap: var(--sp-6);
	}
	.ep-top {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
	}
	.state {
		display: inline-flex;
		align-items: center;
		gap: 0.6rem;
		margin: 0;
		color: var(--text);
		font-weight: 600;
	}
	.state .dot {
		width: 0.6rem;
		height: 0.6rem;
		border-radius: 50%;
		border: 1px solid var(--text-mute);
	}
	.state.on {
		color: var(--ok-ink);
	}
	.state.on .dot {
		background: var(--ok-ink);
		border-color: var(--ok-ink);
	}
	.ep-row {
		display: grid;
		gap: var(--sp-2);
	}
	.ep-url {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3) var(--sp-4);
	}
	.url {
		font-family: var(--font-mono);
		font-size: clamp(1.1rem, 0.8rem + 1.6vw, 2rem);
		letter-spacing: -0.03em;
		color: var(--text-hi);
		overflow-wrap: anywhere;
	}
	.meta code {
		font-size: var(--fs-sm);
		font-weight: 400;
	}
	.block {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
	}
	.codeblock__head {
		padding-left: var(--sp-2);
	}
	.tablist {
		display: flex;
		gap: 2px;
		min-width: 0;
		overflow-x: auto;
	}
	[role='tab'] {
		padding: 0.45rem 0.7rem;
		border: 0;
		border-radius: var(--r-pill);
		background: none;
		color: var(--text-mute);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: none;
		white-space: nowrap;
		cursor: pointer;
	}
	[role='tab']:hover {
		color: var(--text-hi);
	}
	[role='tab'][aria-selected='true'] {
		background: var(--text-hi);
		color: var(--text-inv);
	}
	pre {
		min-height: 9.5rem;
	}
</style>
