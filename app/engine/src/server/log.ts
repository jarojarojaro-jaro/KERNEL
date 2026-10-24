// App log: in-memory listeners (SSE, headless console) + a file in <home>/logs/enigma.log.
import { appendFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { paths } from './paths.ts';

export type Level = 'info' | 'warn' | 'error';
export interface LogLine { t: number; level: Level; msg: string }
type Listener = (line: LogLine) => void;

const listeners = new Set<Listener>();
let logFile: string | null = null;

export function onLog(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit(level: Level, msg: string): void {
  const line: LogLine = { t: Date.now(), level, msg };
  if (logFile === null) {
    const dir = paths().logs;
    mkdirSync(dir, { recursive: true });
    logFile = join(dir, 'enigma.log');
  }
  try {
    appendFileSync(logFile, `${new Date(line.t).toISOString()} ${level.toUpperCase()} ${msg}\n`);
  } catch {
    // the log file is best effort; the listeners still get the line
  }
  for (const fn of listeners) fn(line);
}

export const log = {
  info: (msg: string): void => emit('info', msg),
  warn: (msg: string): void => emit('warn', msg),
  error: (msg: string): void => emit('error', msg),
};

export function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}
