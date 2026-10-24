<script lang="ts">
	/**
	 * Small live test of the local endpoint: streams /v1/chat/completions and shows the measured speed
	 * from llama-server's `timings` (reasoning text, when the model emits it, is shown muted above the answer).
	 */
	import { tick } from 'svelte';
	import { num } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	let { model, enabled }: { model: string; enabled: boolean } = $props();
	const t = $derived(store.t.ready);
	const lang = $derived(store.lang);

	interface Msg {
		role: 'user' | 'assistant';
		content: string;
		reasoning: string;
		tps?: number;
		error?: string;
	}
	let msgs = $state<Msg[]>([]);
	let draft = $state('');
	let busy = $state(false);
	let ctrl: AbortController | null = null;
	let log: HTMLDivElement | undefined = $state();

	interface Chunk {
		choices?: { delta?: { content?: string | null; reasoning_content?: string | null } }[];
		timings?: { predicted_per_second?: number };
	}

	async function send(e: SubmitEvent) {
		e.preventDefault();
		const text = draft.trim();
		if (!text || busy || !enabled) return;
		draft = '';
		msgs.push({ role: 'user', content: text, reasoning: '' });
		msgs.push({ role: 'assistant', content: '', reasoning: '' });
		const out = msgs[msgs.length - 1]!;
		const history = msgs.slice(0, -1).map((m) => ({ role: m.role, content: m.content }));
		busy = true;
		ctrl = new AbortController();
		try {
			const res = await fetch('/v1/chat/completions', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ model, messages: history, stream: true, max_tokens: 1024 }),
				signal: ctrl.signal
			});
			if (!res.ok || !res.body) throw new Error(`${res.status} ${(await res.text()).slice(0, 200)}`);
			const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
			let buf = '';
			for (;;) {
				const { value, done } = await reader.read();
				if (done) break;
				buf += value;
				let nl: number;
				while ((nl = buf.indexOf('\n')) >= 0) {
					const line = buf.slice(0, nl).trim();
					buf = buf.slice(nl + 1);
					if (!line.startsWith('data:')) continue;
					const data = line.slice(5).trim();
					if (data === '[DONE]') continue;
					let c: Chunk;
					try {
						c = JSON.parse(data) as Chunk;
					} catch {
						continue;
					}
					const d = c.choices?.[0]?.delta;
					if (d?.content) out.content += d.content;
					if (d?.reasoning_content) out.reasoning += d.reasoning_content;
					if (c.timings?.predicted_per_second) out.tps = c.timings.predicted_per_second;
				}
				await scrollDown();
			}
		} catch (err) {
			if (!(err instanceof DOMException && err.name === 'AbortError')) out.error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = false;
			ctrl = null;
		}
	}

	async function scrollDown() {
		await tick();
		if (log) log.scrollTop = log.scrollHeight;
	}
</script>

<div class="chat">
	{#if msgs.length}
		<!-- Focusable so keyboard users can scroll the conversation (WCAG 2.1.1). -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div class="msgs" bind:this={log} tabindex="0" role="log" aria-label={t.chat}>
			{#each msgs as m, i (i)}
				<div class="msg {m.role}">
					<p class="who">{m.role === 'user' ? t.you : t.assistant}{#if m.tps}<span class="tps num"> · <span class="speed">{num(m.tps, lang, 1)}</span> t/s</span>{/if}</p>
					{#if m.reasoning}
						<details class="reasoning" open={!m.content}>
							<summary>{t.reasoning}</summary>
							<p>{m.reasoning}</p>
						</details>
					{/if}
					{#if m.content}<p class="text">{m.content}</p>{:else if m.role === 'assistant' && busy && i === msgs.length - 1}<p class="text"><span class="ring" aria-hidden="true"></span></p>{/if}
					{#if m.error}<p class="error-text">{m.error}</p>{/if}
				</div>
			{/each}
		</div>
	{/if}
	<form class="compose" onsubmit={send}>
		<label class="sr-only" for="chat-in">{t.chatLabel}</label>
		<textarea
			id="chat-in"
			class="textarea"
			rows="2"
			placeholder={enabled ? t.chatPlaceholder : t.chatOff}
			bind:value={draft}
			disabled={!enabled}
			onkeydown={(e) => {
				if (e.key === 'Enter' && !e.shiftKey) {
					e.preventDefault();
					(e.currentTarget as HTMLTextAreaElement).form?.requestSubmit();
				}
			}}
		></textarea>
		<div class="row">
			{#if !msgs.length && enabled}
				<button type="button" class="btn btn--ghost btn--sm sample" onclick={() => (draft = t.chatSample)}>{t.chatSample}</button>
			{/if}
			{#if busy}
				<button type="button" class="btn btn--secondary" onclick={() => ctrl?.abort()}>{t.stopGen}</button>
			{:else}
				<button type="submit" class="btn btn--primary" disabled={!enabled || !draft.trim()}>{t.send} <span class="arrow" aria-hidden="true">→</span></button>
			{/if}
		</div>
	</form>
</div>

<style>
	.chat {
		display: grid;
		gap: var(--sp-4);
	}
	.msgs {
		display: grid;
		gap: var(--sp-4);
		max-height: 24rem;
		overflow: auto;
		padding: var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background: var(--bg-1);
	}
	.msg {
		display: grid;
		gap: 0.3rem;
	}
	.who {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.tps {
		text-transform: none;
		letter-spacing: 0;
	}
	.text {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		color: var(--text-hi);
	}
	.user .text {
		color: var(--text);
	}
	.reasoning {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		border-left: 2px solid var(--line-strong);
		padding-left: var(--sp-3);
	}
	.reasoning summary {
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	.reasoning p {
		margin-top: 0.3rem;
		white-space: pre-wrap;
	}
	.compose {
		display: grid;
		gap: var(--sp-3);
	}
	.compose textarea {
		resize: vertical;
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
		justify-content: flex-end;
		align-items: center;
	}
	.sample {
		margin-right: auto;
		text-align: left;
		line-height: 1.3;
		padding-block: 0.4rem;
		max-width: 100%;
		white-space: normal;
		color: var(--text);
	}
</style>
