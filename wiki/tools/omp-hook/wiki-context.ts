// Opcjonalny hook omp: przed turą wstrzykuje skrót decyzji z wiki/decyzje i tytuły 3–5 notatek pasujących do promptu.
// NIE jest zainstalowany. Instalacja: skopiuj ten plik do ~/.omp/agent/hooks/pre/wiki-context.ts (albo do
// <projekt>/.omp/hooks/pre/) i zacznij nową sesję. Brak katalogu wiki = brak efektu. Limit ~1600 znaków (~400 tokenów).
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const WIKI = process.env.KERNEL_WIKI_DIR ?? join(homedir(), "KERNEL", "wiki");
const MAX_CHARS = 1600;

interface Entry {
	rel: string;
	title: string;
	summary: string;
}

interface InjectedMessage {
	message: { customType: string; content: string; display: boolean };
}

// Minimalny kształt API hooków omp, którego używamy (omp://hooks.md: pi.on + before_agent_start → { message }).
interface HookApi {
	on(event: "before_agent_start", handler: (event: { prompt?: string }) => Promise<InjectedMessage | undefined>): void;
}

function readEntry(path: string, rel: string): Entry | null {
	const text = readFileSync(path, "utf8");
	const title = /^# (.+)$/m.exec(text)?.[1]?.trim();
	if (!title) return null;
	const summary = /^# .+\n+\*\*(.+)\*\*/m.exec(text)?.[1]?.trim() ?? "";
	return { rel, title, summary };
}

function loadEntries(): Entry[] {
	const out: Entry[] = [];
	for (const dir of readdirSync(WIKI, { withFileTypes: true })) {
		if (!dir.isDirectory() || dir.name.startsWith(".") || dir.name === "tools") continue;
		for (const f of readdirSync(join(WIKI, dir.name))) {
			if (!f.endsWith(".md") || f === "_hub.md") continue;
			const e = readEntry(join(WIKI, dir.name, f), `${dir.name}/${f}`);
			if (e) out.push(e);
		}
	}
	return out;
}

export default function (pi: HookApi): void {
	pi.on("before_agent_start", async event => {
		if (!existsSync(WIKI)) return undefined;
		const entries = loadEntries();
		const decisions = entries.filter(e => e.rel.startsWith("decyzje/")).map(e => `- ${e.title}`);
		const words = (event.prompt ?? "").toLowerCase().split(/[^\p{L}\p{N}.-]+/u).filter(w => w.length >= 4);
		const matches = entries
			.filter(e => !e.rel.startsWith("decyzje/"))
			.map(e => {
				const hay = `${e.rel} ${e.title} ${e.summary}`.toLowerCase();
				return { e, score: words.reduce((s, w) => s + (hay.includes(w) ? 1 : 0), 0) };
			})
			.filter(x => x.score > 0)
			.sort((a, b) => b.score - a.score)
			.slice(0, 5)
			.map(x => `- wiki/${x.e.rel}: ${x.e.title}`);
		let content = `Baza wiedzy: ${WIKI} (zacznij od index.md).\nDecyzje użytkownika (wiążące):\n${decisions.join("\n")}`;
		if (matches.length) content += `\nPasujące notatki:\n${matches.join("\n")}`;
		if (content.length > MAX_CHARS) content = `${content.slice(0, MAX_CHARS - 1)}…`;
		return { message: { customType: "wiki-context", content, display: false } };
	});
}
