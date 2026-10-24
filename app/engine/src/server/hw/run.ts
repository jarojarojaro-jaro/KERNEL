// Runs a helper program and returns its stdout, or null when it is missing, fails or times out.
import type { Subprocess } from 'bun';

export async function runText(cmd: string[], timeoutMs = 15_000): Promise<string | null> {
  let proc: Subprocess<'ignore', 'pipe', 'ignore'>;
  try {
    proc = Bun.spawn(cmd, { stdout: 'pipe', stderr: 'ignore', stdin: 'ignore' });
  } catch {
    return null;
  }
  const timer = setTimeout(() => proc.kill(), timeoutMs);
  try {
    const out = await new Response(proc.stdout).text();
    const code = await proc.exited;
    return code === 0 ? out : null;
  } finally {
    clearTimeout(timer);
  }
}
