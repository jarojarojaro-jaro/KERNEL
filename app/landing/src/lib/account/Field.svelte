<script lang="ts">
	/**
	 * One labelled input of the account forms. `secret` makes it a password box; `eye` adds the
	 * show/hide toggle (aria-pressed, aria-controls lists every box it reveals). The hint is visible
	 * (`hint`) or screen-reader only (`srHint`); an error replaces the visible hint and is wired through
	 * aria-describedby. Invalid is shown only after the first submit (`error` stays null until then).
	 */
	interface Props {
		id: string;
		name: string;
		label: string;
		/** muted text right of the label, e.g. "min. 10 znaków" */
		note?: string;
		hint?: string;
		srHint?: string;
		error?: string | null;
		value: string;
		autocomplete: 'username' | 'current-password' | 'new-password';
		secret?: boolean;
		reveal?: boolean;
		eye?: { label: string; controls: string };
		maxlength?: number;
		minlength?: number;
	}
	let { id, name, label, note, hint, srHint, error = null, value = $bindable(), autocomplete, secret = false, reveal = $bindable(false), eye, maxlength, minlength }: Props = $props();
	const describedby = $derived(error ? `${id}-err` : hint || srHint ? `${id}-hint` : undefined);
</script>

<div class="field">
	<label for={id}>{label}{#if note}<span class="note">{note}</span>{/if}</label>
	<div class="box" class:has-eye={!!eye}>
		<input
			{id}
			class="input"
			{name}
			type={secret && !reveal ? 'password' : 'text'}
			{autocomplete}
			autocapitalize="none"
			spellcheck="false"
			{maxlength}
			{minlength}
			bind:value
			aria-invalid={!!error}
			aria-describedby={describedby}
		/>
		{#if eye}
			<button class="eye" type="button" aria-label={eye.label} aria-pressed={reveal} aria-controls={eye.controls} onclick={() => (reveal = !reveal)}>
				<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" />
					{#if reveal}<path d="M4 4l16 16" />{/if}
				</svg>
			</button>
		{/if}
	</div>
	{#if error}
		<span class="error-text msg" id="{id}-err">{error}</span>
	{:else if hint}
		<span class="hint msg" id="{id}-hint">{hint}</span>
	{:else if srHint}
		<span class="sr-only" id="{id}-hint">{srHint}</span>
	{/if}
</div>

<style>
	.field {
		display: grid;
		gap: 0.3rem;
		min-width: 0;
	}
	label {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 0 var(--sp-2);
		color: var(--text-hi);
		font-size: var(--fs-xs);
		font-weight: 550;
	}
	.note {
		color: var(--text-mute);
		font-weight: 400;
	}
	.box {
		position: relative;
	}
	.input {
		min-height: 2.75rem;
		border-radius: var(--r-md);
		background: color-mix(in srgb, var(--bg-0) 60%, transparent);
		transition:
			border-color var(--dur-3) var(--ease-out),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.input:focus-visible {
		border-color: var(--heat-3);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--heat-3) 22%, transparent);
	}
	.has-eye .input {
		padding-right: 3rem;
	}
	.eye {
		position: absolute;
		top: 50%;
		right: 0.25rem;
		display: grid;
		place-items: center;
		width: 2.35rem;
		height: 2.35rem;
		transform: translateY(-50%);
		border: 0;
		border-radius: var(--r-sm);
		background: transparent;
		color: var(--text-mute);
		cursor: pointer;
	}
	.eye:hover,
	.eye[aria-pressed='true'] {
		color: var(--text-hi);
	}
	.eye:focus-visible {
		outline: 2px solid var(--heat-3);
		outline-offset: 0;
	}
	.msg {
		font-size: var(--fs-2xs);
		line-height: 1.35;
	}
	.hint {
		color: var(--text-mute);
	}
</style>
