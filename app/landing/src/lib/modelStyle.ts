/**
 * Visual identity of each model, used everywhere a model appears (VRAM blocks, legends, chips,
 * charts). Colours are a categorical palette separate from the heat ramp (heat = speed only);
 * each model also has a shape glyph so colour is never the only cue.
 * Tokens: design/tokens.css `--model-*` (AA on both themes).
 */
import type { ModelKey } from '$lib/data/measurements';

export const MODEL_STYLE: Record<ModelKey, { color: string; shape: 'circle' | 'triangle' | 'square' | 'diamond' | 'hexagon'; short: string }> = {
	qwen38: { color: 'var(--model-qwen38)', shape: 'circle', short: 'Qwen3.8-27B' },
	qwen35: { color: 'var(--model-qwen35)', shape: 'diamond', short: 'Qwen3.5-9B' },
	lfm25: { color: 'var(--model-lfm25)', shape: 'triangle', short: 'LFM2.5-24B' },
	nemotron: { color: 'var(--model-nemotron)', shape: 'hexagon', short: 'Nemotron 74B' },
	bonsai: { color: 'var(--model-bonsai)', shape: 'square', short: 'Bonsai 2 27B' }
};
