#!/usr/bin/env python3
"""End-to-end HTTP server test for Enigma Turbo (/health, /v1/chat/completions non-stream, SSE stream,
--compare-spec, --compare-coupled, --bench, --bench-sweep, --bench-long, --bench-copy, and --multiturn).
Usage:
  1) Standard 3-question test (SSE == non-stream, 'Paris' check, timings):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu]
  2) Speculative vs Non-Speculative comparison (--compare-spec: 3 Q&A + 2 40-line code copy-edit tasks, T=0):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu] --compare-spec
  3) Coupled Gumbel-Max T>0 bit-exact spec == no-spec comparison (--compare-coupled):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu] --compare-coupled [--temp 0.7] [--seed 42]
  4) Benchmark mode (--bench: 5 tasks, 3 repetitions each, median t/s spec vs no-spec + bit-exact check):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu] --bench [--repeats 3] [--draft-n-max 3] [--draft-p-min 0.5]
  5) Parameter sweep (--bench-sweep: T=0 greedy, coupled T=0.7 K in {3,4,5} x p_min in {0.2,0.0}, & lookup policy):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu] --bench-sweep [--sweep-only all|coupled|greedy|lookup] [--repeats 3]
  6) Lookup policy sweep (--bench-lookup: Q4/Q5/C2 across lookup_min_match x lookup_tail_min vs no-tail):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu] --bench-lookup [--repeats 1]
  7) Long-context benchmark (--bench-long: deterministic ~2k & ~8k prompts, prefill t/s, TTFT, decode no-spec / no-tail / tail):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu] --bench-long [--long-sizes 2048,8192] [--max-tokens 64]
  8) Copy-edit benchmark (--bench-copy: 3 ~150-line files with 1 edit, ~1500 tok output, lookup_tail=true vs false):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu] --bench-copy [--temp 0.0] [--max-tokens 2048] [--repeats 1]
  9) Multi-turn prefix reuse test (--multiturn: 3 turns with ~2k context + follow-ups, cached == replay bit-exact, vs reset info):
       python3 tests/test_serve.py <port> [<enigma-turbo-bin> <model.gguf> --gpu] --multiturn [--multiturn-tokens 2048] [--max-tokens 32]
"""
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request


COPY_TASK_1 = """Rewrite the following Python code verbatim, changing only the identifier `data_buf` to `sample_buf` everywhere it appears. Output only the code block without any explanation:

```python
class TelemetryWindow:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.data_buf = []
        self.total_seen = 0

    def reset(self) -> None:
        self.data_buf.clear()
        self.total_seen = 0

    def push(self, value: float) -> None:
        if len(self.data_buf) >= self.capacity:
            self.data_buf.pop(0)
        self.data_buf.append(float(value))
        self.total_seen += 1

    def extend(self, values: list[float]) -> None:
        for v in values:
            self.push(v)

    def count(self) -> int:
        return len(self.data_buf)

    def mean(self) -> float:
        if not self.data_buf:
            return 0.0
        return sum(self.data_buf) / len(self.data_buf)

    def minimum(self) -> float:
        if not self.data_buf:
            return 0.0
        return min(self.data_buf)

    def maximum(self) -> float:
        if not self.data_buf:
            return 0.0
        return max(self.data_buf)

    def scale_all(self, factor: float) -> list[float]:
        self.data_buf = [x * factor for x in self.data_buf]
        return list(self.data_buf)
```"""

COPY_TASK_2 = """Rewrite the following C++ code verbatim, changing only the member name `items_arr` to `slots_arr` everywhere it appears. Output only the code block without any explanation:

```cpp
struct FixedRingBuffer {
    int items_arr[64];
    int head = 0;
    int tail = 0;
    int count = 0;

    void clear() noexcept {
        for (int i = 0; i < 64; ++i) {
            items_arr[i] = 0;
        }
        head = 0;
        tail = 0;
        count = 0;
    }

    bool push(int val) noexcept {
        if (count >= 64) {
            return false;
        }
        items_arr[tail] = val;
        tail = (tail + 1) & 63;
        ++count;
        return true;
    }

    bool pop(int& out) noexcept {
        if (count <= 0) {
            return false;
        }
        out = items_arr[head];
        head = (head + 1) & 63;
        --count;
        return true;
    }

    int sum() const noexcept {
        int s = 0;
        for (int i = 0; i < count; ++i) {
            s += items_arr[(head + i) & 63];
        }
        return s;
    }
};
```"""


BENCH_COPY_PY_150 = '''from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple


DEFAULT_RETRY_LIMIT = 3
DEFAULT_BACKOFF_BASE_MS = 125.0
DEFAULT_BACKOFF_CAP_MS = 8000.0
DEFAULT_QUEUE_HIGH_WATER = 1024


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    tenant: str
    payload_bytes: bytes
    priority: int = 10
    timeout_ms: int = 5000
    max_retries: int = DEFAULT_RETRY_LIMIT

    def checksum(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.tenant.encode("utf-8"))
        digest.update(b":")
        digest.update(self.job_id.encode("utf-8"))
        digest.update(b":")
        digest.update(self.payload_bytes)
        return digest.hexdigest()[:16]


@dataclass
class JobState:
    spec: JobSpec
    enqueued_at_ms: float
    attempts: int = 0
    last_error: str = ""
    next_eligible_ms: float = 0.0
    finished_at_ms: Optional[float] = None
    succeeded: bool = False


@dataclass
class TenantQuota:
    max_inflight: int = 16
    max_queued: int = 256
    inflight: int = 0
    queued: int = 0
    completed: int = 0
    failed: int = 0


@dataclass
class SchedulerSnapshot:
    queued_total: int
    inflight_total: int
    completed_total: int
    failed_total: int
    dead_letter_total: int
    p95_wait_ms: float
    tenants: Dict[str, Tuple[int, int, int, int]] = field(default_factory=dict)


class DeterministicJobScheduler:
    """In-memory multi-tenant job scheduler with bounded retries, backoff, and latency tracking."""

    def __init__(self, clock_ms: Optional[Callable[[], float]] = None, high_water: int = DEFAULT_QUEUE_HIGH_WATER):
        self._clock_ms = clock_ms or (lambda: time.monotonic() * 1000.0)
        self._high_water = max(1, int(high_water))
        self._pending: Dict[str, JobState] = {}
        self._inflight: Dict[str, JobState] = {}
        self._dead_letters: List[JobState] = []
        self._quotas: Dict[str, TenantQuota] = {}
        self._wait_samples_ms: List[float] = []
        self._completed_total = 0
        self._failed_total = 0

    def configure_tenant(self, tenant: str, max_inflight: int, max_queued: int) -> None:
        if max_inflight <= 0 or max_queued <= 0:
            raise ValueError(f"Invalid tenant limits for {tenant!r}: inflight={max_inflight}, queued={max_queued}")
        q = self._quotas.setdefault(tenant, TenantQuota())
        q.max_inflight = int(max_inflight)
        q.max_queued = int(max_queued)

    def _quota_for(self, tenant: str) -> TenantQuota:
        q = self._quotas.get(tenant)
        if q is None:
            q = TenantQuota()
            self._quotas[tenant] = q
        return q

    def submit(self, spec: JobSpec) -> bool:
        if not spec.job_id or not spec.tenant:
            raise ValueError("JobSpec requires non-empty job_id and tenant")
        if spec.job_id in self._pending or spec.job_id in self._inflight:
            return False
        if len(self._pending) >= self._high_water:
            return False
        quota = self._quota_for(spec.tenant)
        if quota.queued >= quota.max_queued:
            return False
        now = self._clock_ms()
        self._pending[spec.job_id] = JobState(spec=spec, enqueued_at_ms=now, next_eligible_ms=now)
        quota.queued += 1
        return True

    def _backoff_ms(self, attempts: int) -> float:
        exponent = max(0, attempts - 1)
        raw = DEFAULT_BACKOFF_BASE_MS * math.pow(2.0, float(exponent))
        return min(DEFAULT_BACKOFF_CAP_MS, raw)

    def lease_next(self) -> Optional[JobState]:
        now = self._clock_ms()
        best_state: Optional[JobState] = None
        best_key: Optional[Tuple[int, float, str]] = None
        for job_id, state in self._pending.items():
            if state.next_eligible_ms > now:
                continue
            quota = self._quota_for(state.spec.tenant)
            if quota.inflight >= quota.max_inflight:
                continue
            key = (state.spec.priority, state.enqueued_at_ms, job_id)
            if best_key is None or key < best_key:
                best_key = key
                best_state = state
        if best_state is None:
            return None
        del self._pending[best_state.spec.job_id]
        quota = self._quota_for(best_state.spec.tenant)
        quota.queued -= 1
        quota.inflight += 1
        best_state.attempts += 1
        self._inflight[best_state.spec.job_id] = best_state
        wait_ms = max(0.0, now - best_state.enqueued_at_ms)
        self._wait_samples_ms.append(wait_ms)
        if len(self._wait_samples_ms) > 2048:
            del self._wait_samples_ms[:1024]
        return best_state

    def ack(self, job_id: str) -> bool:
        state = self._inflight.pop(job_id, None)
        if state is None:
            return False
        quota = self._quota_for(state.spec.tenant)
        quota.inflight -= 1
        quota.completed += 1
        state.succeeded = True
        state.finished_at_ms = self._clock_ms()
        self._completed_total += 1
        return True

    def nack(self, job_id: str, error_message: str) -> str:
        state = self._inflight.pop(job_id, None)
        if state is None:
            return "missing"
        quota = self._quota_for(state.spec.tenant)
        quota.inflight -= 1
        state.last_error = error_message
        now = self._clock_ms()
        if state.attempts <= state.spec.max_retries:
            state.next_eligible_ms = now + self._backoff_ms(state.attempts)
            self._pending[job_id] = state
            quota.queued += 1
            return "requeued"
        state.finished_at_ms = now
        quota.failed += 1
        self._failed_total += 1
        self._dead_letters.append(state)
        return "dead_letter"
'''

BENCH_COPY_CPP_150 = '''#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace storage {

constexpr std::size_t kDefaultCacheCapacity = 128;
constexpr std::uint64_t kInvalidRevision = 0;

struct PageRecord {
    std::uint64_t page_id = 0;
    std::uint64_t revision = kInvalidRevision;
    std::uint32_t checksum = 0;
    bool dirty = false;
    std::vector<std::uint8_t> payload;
};

struct CacheMetrics {
    std::uint64_t hits = 0;
    std::uint64_t misses = 0;
    std::uint64_t insertions = 0;
    std::uint64_t updates = 0;
    std::uint64_t evictions = 0;
    std::uint64_t dirty_flushes = 0;
    std::size_t current_entries = 0;
    std::size_t current_bytes = 0;

    double hit_ratio() const noexcept {
        const std::uint64_t total = hits + misses;
        return total > 0 ? static_cast<double>(hits) / static_cast<double>(total) : 0.0;
    }
};

class LruPageCache {
public:
    explicit LruPageCache(std::size_t capacity = kDefaultCacheCapacity)
        : capacity_(std::max<std::size_t>(1, capacity)) {
        nodes_.reserve(capacity_);
        index_.reserve(capacity_ * 2);
    }

    std::size_t capacity() const noexcept { return capacity_; }
    std::size_t size() const noexcept { return index_.size(); }
    bool empty() const noexcept { return index_.empty(); }

    static std::uint32_t compute_checksum(const std::vector<std::uint8_t>& data) noexcept {
        std::uint32_t h = 2166136261u;
        for (std::uint8_t b : data) {
            h ^= static_cast<std::uint32_t>(b);
            h *= 16777619u;
        }
        return h;
    }

    const PageRecord* get(std::uint64_t page_id) noexcept {
        auto it = index_.find(page_id);
        if (it == index_.end()) {
            ++metrics_.misses;
            return nullptr;
        }
        ++metrics_.hits;
        move_to_front(it->second);
        return &nodes_[it->second].record;
    }

    std::optional<PageRecord> put(PageRecord record) {
        record.checksum = compute_checksum(record.payload);
        auto it = index_.find(record.page_id);
        if (it != index_.end()) {
            Node& node = nodes_[it->second];
            metrics_.current_bytes -= node.record.payload.size();
            metrics_.current_bytes += record.payload.size();
            node.record = std::move(record);
            ++metrics_.updates;
            move_to_front(it->second);
            return std::nullopt;
        }

        std::optional<PageRecord> evicted;
        std::size_t slot = 0;
        if (index_.size() >= capacity_) {
            slot = tail_;
            Node& victim = nodes_[slot];
            index_.erase(victim.record.page_id);
            metrics_.current_bytes -= victim.record.payload.size();
            ++metrics_.evictions;
            if (victim.record.dirty) {
                ++metrics_.dirty_flushes;
            }
            evicted = std::move(victim.record);
            detach(slot);
        } else if (!free_slots_.empty()) {
            slot = free_slots_.back();
            free_slots_.pop_back();
        } else {
            slot = nodes_.size();
            nodes_.push_back(Node{});
        }

        metrics_.current_bytes += record.payload.size();
        nodes_[slot].record = std::move(record);
        nodes_[slot].prev = kNullSlot;
        nodes_[slot].next = kNullSlot;
        attach_front(slot);
        index_.emplace(nodes_[slot].record.page_id, slot);
        ++metrics_.insertions;
        metrics_.current_entries = index_.size();
        return evicted;
    }

    bool erase(std::uint64_t page_id) {
        auto it = index_.find(page_id);
        if (it == index_.end()) {
            return false;
        }
        const std::size_t slot = it->second;
        metrics_.current_bytes -= nodes_[slot].record.payload.size();
        detach(slot);
        nodes_[slot].record.payload.clear();
        index_.erase(it);
        free_slots_.push_back(slot);
        metrics_.current_entries = index_.size();
        return true;
    }

    std::vector<std::uint64_t> flush_dirty_pages() {
        std::vector<std::uint64_t> flushed;
        for (std::size_t cur = head_; cur != kNullSlot; cur = nodes_[cur].next) {
            if (nodes_[cur].record.dirty) {
                nodes_[cur].record.dirty = false;
                flushed.push_back(nodes_[cur].record.page_id);
                ++metrics_.dirty_flushes;
            }
        }
        return flushed;
    }

    CacheMetrics metrics() const noexcept { return metrics_; }

private:
    static constexpr std::size_t kNullSlot = std::numeric_limits<std::size_t>::max();

    struct Node {
        PageRecord record;
        std::size_t prev = kNullSlot;
        std::size_t next = kNullSlot;
    };

    void detach(std::size_t slot) noexcept {
        Node& node = nodes_[slot];
        if (node.prev != kNullSlot) nodes_[node.prev].next = node.next;
        else head_ = node.next;
        if (node.next != kNullSlot) nodes_[node.next].prev = node.prev;
        else tail_ = node.prev;
        node.prev = kNullSlot;
        node.next = kNullSlot;
    }

    void attach_front(std::size_t slot) noexcept {
        Node& node = nodes_[slot];
        node.prev = kNullSlot;
        node.next = head_;
        if (head_ != kNullSlot) nodes_[head_].prev = slot;
        else tail_ = slot;
        head_ = slot;
    }

    void move_to_front(std::size_t slot) noexcept {
        if (slot == head_) return;
        detach(slot);
        attach_front(slot);
    }

    std::size_t capacity_ = kDefaultCacheCapacity;
    std::size_t head_ = kNullSlot;
    std::size_t tail_ = kNullSlot;
    std::vector<Node> nodes_;
    std::vector<std::size_t> free_slots_;
    std::unordered_map<std::uint64_t, std::size_t> index_;
    CacheMetrics metrics_{};
};

} // namespace storage
'''

BENCH_COPY_TS_150 = '''export type BreakerState = "closed" | "open" | "half_open";

export interface CircuitBreakerConfig {
  readonly serviceName: string;
  readonly failureThreshold: number;
  readonly successThreshold: number;
  readonly openTimeoutMs: number;
  readonly windowSizeMs: number;
  readonly maxHalfOpenCalls: number;
}

export interface CallOutcome {
  readonly timestampMs: number;
  readonly ok: boolean;
  readonly latencyMs: number;
  readonly errorCode?: string;
}

export interface BreakerTelemetry {
  readonly serviceName: string;
  readonly state: BreakerState;
  readonly totalRequests: number;
  readonly rejectedRequests: number;
  readonly recentFailures: number;
  readonly recentSuccesses: number;
  readonly averageLatencyMs: number;
  readonly stateTransitions: number;
}

export const DEFAULT_FAILURE_THRESHOLD = 5;
export const DEFAULT_SUCCESS_THRESHOLD = 2;
export const DEFAULT_OPEN_TIMEOUT_MS = 15000;
export const DEFAULT_WINDOW_SIZE_MS = 60000;
export const DEFAULT_MAX_HALF_OPEN_CALLS = 3;

export function createDefaultConfig(serviceName: string): CircuitBreakerConfig {
  return {
    serviceName,
    failureThreshold: DEFAULT_FAILURE_THRESHOLD,
    successThreshold: DEFAULT_SUCCESS_THRESHOLD,
    openTimeoutMs: DEFAULT_OPEN_TIMEOUT_MS,
    windowSizeMs: DEFAULT_WINDOW_SIZE_MS,
    maxHalfOpenCalls: DEFAULT_MAX_HALF_OPEN_CALLS,
  };
}

export class HttpCircuitBreaker {
  private readonly cfg: CircuitBreakerConfig;
  private readonly nowFn: () => number;
  private state: BreakerState = "closed";
  private openedAtMs = 0;
  private halfOpenInFlight = 0;
  private halfOpenSuccesses = 0;
  private totalRequests = 0;
  private rejectedRequests = 0;
  private stateTransitions = 0;
  private history: CallOutcome[] = [];

  constructor(config: CircuitBreakerConfig, nowFn: () => number = () => Date.now()) {
    if (!config.serviceName.trim()) {
      throw new Error("CircuitBreakerConfig.serviceName must be non-empty");
    }
    if (config.failureThreshold < 1 || config.successThreshold < 1) {
      throw new Error("Failure and success thresholds must be positive integers");
    }
    if (config.openTimeoutMs <= 0 || config.windowSizeMs <= 0) {
      throw new Error("Timeouts and rolling window durations must be positive");
    }
    this.cfg = { ...config };
    this.nowFn = nowFn;
  }

  public getState(): BreakerState {
    this.refreshState(this.nowFn());
    return this.state;
  }

  public tryAcquire(): boolean {
    const now = this.nowFn();
    this.refreshState(now);
    this.totalRequests += 1;

    if (this.state === "open") {
      this.rejectedRequests += 1;
      return false;
    }
    if (this.state === "half_open") {
      if (this.halfOpenInFlight >= this.cfg.maxHalfOpenCalls) {
        this.rejectedRequests += 1;
        return false;
      }
      this.halfOpenInFlight += 1;
      return true;
    }
    return true;
  }

  public recordSuccess(latencyMs: number): void {
    const now = this.nowFn();
    this.appendOutcome({ timestampMs: now, ok: true, latencyMs: Math.max(0, latencyMs) });
    if (this.state === "half_open") {
      this.halfOpenInFlight = Math.max(0, this.halfOpenInFlight - 1);
      this.halfOpenSuccesses += 1;
      if (this.halfOpenSuccesses >= this.cfg.successThreshold) {
        this.transitionTo("closed", now);
      }
    }
  }

  public recordFailure(latencyMs: number, errorCode?: string): void {
    const now = this.nowFn();
    this.appendOutcome({ timestampMs: now, ok: false, latencyMs: Math.max(0, latencyMs), errorCode });
    if (this.state === "half_open") {
      this.halfOpenInFlight = Math.max(0, this.halfOpenInFlight - 1);
      this.transitionTo("open", now);
      return;
    }
    if (this.state === "closed") {
      const failures = this.countRecentFailures(now);
      if (failures >= this.cfg.failureThreshold) {
        this.transitionTo("open", now);
      }
    }
  }

  public async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (!this.tryAcquire()) {
      throw new Error(`Circuit breaker '${this.cfg.serviceName}' is open`);
    }
    const started = this.nowFn();
    try {
      const result = await operation();
      this.recordSuccess(this.nowFn() - started);
      return result;
    } catch (err) {
      const code = err instanceof Error ? err.name : "UNKNOWN_ERROR";
      this.recordFailure(this.nowFn() - started, code);
      throw err;
    }
  }

  public telemetry(): BreakerTelemetry {
    const now = this.nowFn();
    this.refreshState(now);
    this.pruneWindow(now);
    let failures = 0;
    let successes = 0;
    let latencySum = 0;
    for (const item of this.history) {
      latencySum += item.latencyMs;
      if (item.ok) successes += 1;
      else failures += 1;
    }
    const avgLatency = this.history.length > 0 ? latencySum / this.history.length : 0;
    return {
      serviceName: this.cfg.serviceName,
      state: this.state,
      totalRequests: this.totalRequests,
      rejectedRequests: this.rejectedRequests,
      recentFailures: failures,
      recentSuccesses: successes,
      averageLatencyMs: avgLatency,
      stateTransitions: this.stateTransitions,
    };
  }

  private refreshState(now: number): void {
    if (this.state === "open" && now - this.openedAtMs >= this.cfg.openTimeoutMs) {
      this.transitionTo("half_open", now);
    }
  }

  private transitionTo(next: BreakerState, now: number): void {
    if (this.state === next) return;
    this.state = next;
    this.stateTransitions += 1;
    this.openedAtMs = next === "open" ? now : 0;
    this.halfOpenInFlight = 0;
    this.halfOpenSuccesses = 0;
  }

  private appendOutcome(outcome: CallOutcome): void {
    this.history.push(outcome);
    this.pruneWindow(outcome.timestampMs);
  }

  private pruneWindow(now: number): void {
    const cutoff = now - this.cfg.windowSizeMs;
    let dropCount = 0;
    while (dropCount < this.history.length && this.history[dropCount].timestampMs < cutoff) {
      dropCount += 1;
    }
    if (dropCount > 0) this.history.splice(0, dropCount);
  }

  private countRecentFailures(now: number): number {
    this.pruneWindow(now);
    return this.history.filter((item) => !item.ok).length;
  }
}
'''

BENCH_COPY_TASKS = [
    (
        "C1 (Python ~160L, 1 edit)",
        "Return the ENTIRE Python file below verbatim inside a ```python code block, changing ONLY "
        "`DEFAULT_RETRY_LIMIT = 3` to `DEFAULT_RETRY_LIMIT = 5`. Do not omit any lines and do not add "
        "any commentary:\n\n```python\n" + BENCH_COPY_PY_150 + "```",
    ),
    (
        "C2 (C++ ~180L, 1 edit)",
        "Return the ENTIRE C++ header below verbatim inside a ```cpp code block, changing ONLY "
        "`constexpr std::size_t kDefaultCacheCapacity = 128;` to `constexpr std::size_t kDefaultCacheCapacity = 256;`. "
        "Do not omit any lines and do not add any commentary:\n\n```cpp\n" + BENCH_COPY_CPP_150 + "```",
    ),
    (
        "C3 (TypeScript ~190L, 1 edit)",
        "Return the ENTIRE TypeScript file below verbatim inside a ```ts code block, changing ONLY "
        "`export const DEFAULT_FAILURE_THRESHOLD = 5;` to `export const DEFAULT_FAILURE_THRESHOLD = 8;`. "
        "Do not omit any lines and do not add any commentary:\n\n```ts\n" + BENCH_COPY_TS_150 + "```",
    ),
]


def http_get_json(url, timeout=5.0):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def http_tokenize(base_url, content, timeout=30.0):
    req = urllib.request.Request(
        f"{base_url}/tokenize",
        data=json.dumps({"content": content, "parse_special": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")).get("tokens", [])


def make_long_prompt_blocks(n_blocks, target_tokens):
    """Deterministically build a structured code + telemetry log prompt with `n_blocks` entries."""
    header = (
        f"You are analyzing a deterministic diagnostic snapshot (target ~{target_tokens} tokens) "
        f"consisting of telemetry service worker modules and execution logs.\n"
        f"Read the modules and logs below, then summarize the final alert entry and list the exact "
        f"service name, checksum, and latency_ms of the last module.\n\n"
    )
    parts = [header]
    for i in range(n_blocks):
        mod_id = f"worker_{i:04d}"
        port = 7000 + (i % 997)
        lat_ms = 12.5 + ((i * 37) % 100) * 0.25
        csum = f"{(i * 2654435761) & 0xFFFFFFFF:08x}"
        status = "OK" if (i % 19) != 17 else "WARN_RETRY"
        parts.append(
            f"# Module {i:04d}: {mod_id} (port={port}, checksum={csum})\n"
            f"def run_{mod_id}(batch_size: int, scale: float) -> dict:\n"
            f"    acc = 0.0\n"
            f"    for k in range(batch_size):\n"
            f"        acc += ((k * {(i % 13) + 3}) % 29) * scale\n"
            f"    return {{\"module\": \"{mod_id}\", \"port\": {port}, \"checksum\": \"{csum}\", "
            f"\"latency_ms\": {lat_ms:.2f}, \"status\": \"{status}\", \"score\": round(acc, 4)}}\n"
            f"[2026-11-20T09:{(i // 60) % 60:02d}:{i % 60:02d}Z] INFO {mod_id} "
            f"step={i} processed={64 + (i % 8) * 16} latency_ms={lat_ms:.2f} "
            f"checksum={csum} status={status}\n\n"
        )
    last_i = max(n_blocks - 1, 0)
    parts.append(
        f"FINAL ALERT: module=worker_{last_i:04d} checksum={(last_i * 2654435761) & 0xFFFFFFFF:08x} "
        f"latency_ms={12.5 + ((last_i * 37) % 100) * 0.25:.2f}.\n"
        f"Provide a concise 3-sentence report referencing that exact module, checksum, and latency_ms."
    )
    return "".join(parts)


def calibrate_long_prompt(base_url, target_tokens):
    """Calibrate `n_blocks` via POST /tokenize so the chat-formatted prompt is close to `target_tokens`."""
    # Reserve ~24 tokens for Qwen chat template wrapper (<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n)
    goal = max(32, target_tokens - 24)
    lo, hi = 1, max(4, target_tokens // 40)
    while len(http_tokenize(base_url, make_long_prompt_blocks(hi, target_tokens))) < goal:
        lo = hi
        hi *= 2
        if hi > 4096:
            break
    best_n = hi
    best_diff = 10**9
    while lo <= hi:
        mid = (lo + hi) // 2
        toks = len(http_tokenize(base_url, make_long_prompt_blocks(mid, target_tokens)))
        diff = abs(toks - goal)
        if diff < best_diff:
            best_diff = diff
            best_n = mid
        if toks < goal:
            lo = mid + 1
        elif toks > goal:
            hi = mid - 1
        else:
            break
    return make_long_prompt_blocks(best_n, target_tokens)


def chat_non_stream(base_url, question_or_messages, max_tokens=32, extra_fields=None, timeout=600.0):
    msgs = (
        question_or_messages
        if isinstance(question_or_messages, list)
        else [{"role": "user", "content": question_or_messages}]
    )
    body = {
        "messages": msgs,
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if extra_fields:
        body.update(extra_fields)
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    timings = data.get("timings", {})
    return content, timings


def chat_stream(base_url, question_or_messages, max_tokens=32, extra_fields=None, return_ttft=False, timeout=600.0):
    msgs = (
        question_or_messages
        if isinstance(question_or_messages, list)
        else [{"role": "user", "content": question_or_messages}]
    )
    body = {
        "messages": msgs,
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if extra_fields:
        body.update(extra_fields)
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    pieces = []
    timings = {}
    saw_done = False
    t_req = time.perf_counter()
    ttft_ms = None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                saw_done = True
                break
            chunk = json.loads(payload)
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                if "content" in delta and delta["content"]:
                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - t_req) * 1000.0
                    pieces.append(delta["content"])
            if "timings" in chunk:
                timings = chunk["timings"]
    if not saw_done:
        raise RuntimeError("SSE stream ended without data: [DONE]")
    if ttft_ms is None:
        ttft_ms = (time.perf_counter() - t_req) * 1000.0
    if return_ttft:
        return "".join(pieces), timings, ttft_ms
    return "".join(pieces), timings


def parse_args(argv):
    port = 18794
    exe = None
    model = None
    use_gpu = None
    ctx = None
    compare_spec = False
    compare_coupled = False
    bench = False
    bench_sweep = False
    bench_lookup = False
    sweep_only = "all"
    bench_long = False
    bench_copy = False
    with_nospec = False
    multiturn = False
    repeats = None
    temp = None
    seed = 42
    max_tokens_opt = None
    long_sizes = [2048, 8192]
    multiturn_tokens = 2048
    draft_n_max = None
    draft_p_min = None
    lookup_max_w = None
    lookup_min_match = None
    lookup_tail_min = None

    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--port", "-p") and i + 1 < len(argv):
            port = int(argv[i + 1])
            i += 2
        elif a in ("--bin", "-b") and i + 1 < len(argv):
            exe = argv[i + 1]
            i += 2
        elif a in ("--model", "-m") and i + 1 < len(argv):
            model = argv[i + 1]
            i += 2
        elif a in ("--ctx", "-c") and i + 1 < len(argv):
            ctx = int(argv[i + 1])
            i += 2
        elif a in ("--repeats", "-r") and i + 1 < len(argv):
            repeats = max(1, int(argv[i + 1]))
            i += 2
        elif a == "--temp" and i + 1 < len(argv):
            temp = float(argv[i + 1])
            i += 2
        elif a == "--seed" and i + 1 < len(argv):
            seed = int(argv[i + 1])
            i += 2
        elif a == "--max-tokens" and i + 1 < len(argv):
            max_tokens_opt = max(1, int(argv[i + 1]))
            i += 2
        elif a == "--long-sizes" and i + 1 < len(argv):
            long_sizes = [int(x.strip()) for x in argv[i + 1].split(",") if x.strip()]
            i += 2
        elif a == "--multiturn-tokens" and i + 1 < len(argv):
            multiturn_tokens = max(64, int(argv[i + 1]))
            i += 2
        elif a == "--draft-n-max" and i + 1 < len(argv):
            draft_n_max = int(argv[i + 1])
            i += 2
        elif a == "--draft-p-min" and i + 1 < len(argv):
            draft_p_min = float(argv[i + 1])
            i += 2
        elif a == "--lookup-max-w" and i + 1 < len(argv):
            lookup_max_w = int(argv[i + 1])
            i += 2
        elif a == "--lookup-min-match" and i + 1 < len(argv):
            lookup_min_match = int(argv[i + 1])
            i += 2
        elif a == "--lookup-tail-min" and i + 1 < len(argv):
            lookup_tail_min = int(argv[i + 1])
            i += 2
        elif a == "--sweep-only" and i + 1 < len(argv):
            sweep_only = argv[i + 1].strip().lower()
            i += 2
        elif a == "--gpu":
            use_gpu = True
            i += 1
        elif a == "--cpu":
            use_gpu = False
            i += 1
        elif a == "--compare-spec":
            compare_spec = True
            i += 1
        elif a == "--compare-coupled":
            compare_coupled = True
            i += 1
        elif a == "--bench":
            bench = True
            i += 1
        elif a == "--bench-sweep":
            bench_sweep = True
            i += 1
        elif a == "--bench-lookup":
            bench_lookup = True
            i += 1
        elif a == "--bench-long":
            bench_long = True
            i += 1
        elif a == "--bench-copy":
            bench_copy = True
            i += 1
        elif a == "--with-nospec":
            with_nospec = True
            i += 1
        elif a == "--multiturn":
            multiturn = True
            i += 1
        elif a.isdigit():
            port = int(a)
            i += 1
        elif a.endswith(".gguf"):
            model = a
            i += 1
        else:
            exe = a
            i += 1

    if exe is None:
        exe = "build-hip/enigma-turbo" if os.path.exists("build-hip/enigma-turbo") else "build/enigma-turbo"
    if use_gpu is None:
        use_gpu = "hip" in exe
    if model is None:
        cand_27b = os.path.expanduser("~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf")
        cand_08b = os.path.expanduser("~/praca/turbo-test/q35-08b-Q4_K_M.gguf")
        model = cand_27b if os.path.exists(cand_27b) else cand_08b
    if bench_lookup:
        bench_sweep = True
        sweep_only = "lookup"
    if max_tokens_opt is not None:
        max_tokens_long = max_tokens_opt
    elif bench_copy:
        max_tokens_long = 2048
    elif multiturn:
        max_tokens_long = 32
    else:
        max_tokens_long = 64
    if temp is None:
        temp = 0.0 if (multiturn or bench_copy) else 0.7
    if ctx is None:
        if bench_long:
            ctx = max(10240, max(long_sizes) + max_tokens_long + 512)
        elif bench_copy or bench_lookup:
            ctx = max(6144, 2 * max_tokens_long + 2048)
        elif multiturn:
            ctx = max(4096, multiturn_tokens + 3 * max_tokens_long + 512)
        else:
            ctx = 4096
    if repeats is None:
        repeats = 1 if (bench_long or bench_copy or bench_lookup) else 3

    return {
        "port": port,
        "exe": exe,
        "model": model,
        "use_gpu": use_gpu,
        "ctx": ctx,
        "compare_spec": compare_spec,
        "compare_coupled": compare_coupled,
        "bench": bench,
        "bench_sweep": bench_sweep,
        "bench_lookup": bench_lookup,
        "sweep_only": sweep_only,
        "bench_long": bench_long,
        "bench_copy": bench_copy,
        "with_nospec": with_nospec,
        "multiturn": multiturn,
        "repeats": repeats,
        "temp": temp,
        "seed": seed,
        "max_tokens_long": max_tokens_long,
        "long_sizes": long_sizes,
        "multiturn_tokens": multiturn_tokens,
        "draft_n_max": draft_n_max,
        "draft_p_min": draft_p_min,
        "lookup_max_w": lookup_max_w,
        "lookup_min_match": lookup_min_match,
        "lookup_tail_min": lookup_tail_min,
    }


def is_server_up(base_url):
    try:
        st, body = http_get_json(f"{base_url}/health", timeout=0.5)
        return st == 200 and body.get("status") == "ok"
    except Exception:
        return False


REQUIRED_TIMING_KEYS = (
    "prompt_n",
    "cache_n",
    "prompt_ms",
    "prompt_per_second",
    "predicted_n",
    "predicted_ms",
    "predicted_per_second",
    "draft_n",
    "draft_n_accepted",
    "verify_steps",
    "ms_per_step",
    "tok_per_step",
    "lookup_tail_steps",
    "lookup_chain_steps",
    "lookup_draft_n",
    "lookup_draft_accepted",
)


def main():
    args = parse_args(sys.argv[1:])
    port = args["port"]
    exe = args["exe"]
    model = args["model"]
    use_gpu = args["use_gpu"]
    ctx = args["ctx"]
    compare_spec = args["compare_spec"]
    compare_coupled = args["compare_coupled"]
    bench = args["bench"]
    bench_sweep = args["bench_sweep"]
    sweep_only = args["sweep_only"]
    bench_long = args["bench_long"]
    bench_copy = args["bench_copy"]
    with_nospec = args["with_nospec"]
    multiturn = args["multiturn"]
    repeats = args["repeats"]
    temp = args["temp"]
    seed = args["seed"]
    max_tokens_long = args["max_tokens_long"]
    long_sizes = args["long_sizes"]
    multiturn_tokens = args["multiturn_tokens"]
    draft_n_max = args["draft_n_max"]
    draft_p_min = args["draft_p_min"]
    lookup_max_w = args["lookup_max_w"]
    lookup_min_match = args["lookup_min_match"]
    lookup_tail_min = args["lookup_tail_min"]

    base_url = f"http://127.0.0.1:{port}"
    proc = None

    try:
        if is_server_up(base_url):
            print(f"[test_serve] Using existing server at {base_url}")
        else:
            cmd = [exe, "serve", "-m", model, "--port", str(port), "--ctx", str(ctx)]
            if use_gpu:
                cmd.insert(2, "--gpu")
            print(f"[test_serve] Spawning: {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            t0 = time.time()
            while time.time() - t0 < 300.0:
                if proc.poll() is not None:
                    out = proc.stdout.read() if proc.stdout else ""
                    print(f"[test_serve] Server exited early (code {proc.returncode}):\n{out}")
                    sys.exit(2)
                if is_server_up(base_url):
                    break
                time.sleep(0.25)
            else:
                print("[test_serve] Timeout waiting for server /health")
                sys.exit(2)

        st, hbody = http_get_json(f"{base_url}/health")
        assert st == 200 and hbody.get("status") == "ok", f"/health failed: {st} {hbody}"
        hw_max_verify = 8
        try:
            pst, pbody = http_get_json(f"{base_url}/props")
            if pst == 200 and "max_verify" in pbody:
                hw_max_verify = int(pbody["max_verify"])
        except Exception:
            pass
        eff_w_label = min(16, hw_max_verify) if lookup_max_w is None else min(16, hw_max_verify, lookup_max_w)
        print(f"[test_serve] GET /health -> {hbody} (max_verify={hw_max_verify}, eff_W={eff_w_label})")

        questions = [
            ("Q1 (France)", "What is the capital of France? Answer in one sentence.", 24),
            ("Q2 (Math)", "What is 2 + 2? Answer in one short sentence.", 24),
            ("Q3 (Colors)", "Name three primary colors in one short sentence.", 24),
        ]

        tasks = questions + [
            ("Q4 (Copy-Edit Python 40L)", COPY_TASK_1, 160),
            ("Q5 (Copy-Edit C++ 40L)", COPY_TASK_2, 160),
        ]

        if multiturn:
            print(
                f"\n=== Multi-Turn Prefix Reuse Test (3 turns, context~{multiturn_tokens} tok, "
                f"max_tokens={max_tokens_long}, T={temp}, seed={seed}; criterion: cached == replay) ==="
            )
            ctx_doc = calibrate_long_prompt(base_url, multiturn_tokens)
            turn_prompts = [
                ctx_doc + "\n\nQuestion 1: State only the exact module name and checksum from FINAL ALERT in one short sentence.",
                "Question 2: What port number is assigned to worker_0000 in the snapshot above? Answer in one short sentence.",
                "Question 3: Summarize both worker_0000 and the FINAL ALERT module in one short sentence.",
            ]
            common_extra = {"temperature": temp, "seed": seed, "use_coupled": True}

            # Pass 1: cached multi-turn conversation (Turn 1 cold via cache_prompt=False so an existing server
            # starts cleanly, Turns 2-3 hit prefix cache via cache_prompt=True; SSE stream measures true TTFT).
            history_msgs = []
            turn_histories = []
            cached_results = []
            for t_idx, user_q in enumerate(turn_prompts, 1):
                history_msgs.append({"role": "user", "content": user_q})
                turn_histories.append(list(history_msgs))
                text_c, tim_c, ttft_c = chat_stream(
                    base_url,
                    turn_histories[-1],
                    max_tokens=max_tokens_long,
                    extra_fields={**common_extra, "cache_prompt": (t_idx > 1)},
                    return_ttft=True,
                )
                for req_key in REQUIRED_TIMING_KEYS:
                    assert req_key in tim_c, f"Missing timing key {req_key} in multiturn cached turn {t_idx}"
                cached_results.append((text_c, tim_c, ttft_c))
                history_msgs.append({"role": "assistant", "content": text_c})

            # Construct exact replay segment schedules matching Pass 1's prefill (+n) vs GEMV decode (-n) paths:
            #   Turn 1: [+L1]
            #   Turn 2: [+L1, -d1_fed, +p2_delta]
            #   Turn 3: [+L1, -d1_fed, +p2_delta, -d2_fed, +p3_delta]
            l1 = cached_results[0][1]["prompt_n"]
            d1_fed = cached_results[1][1]["cache_n"] - l1
            p2_delta = cached_results[1][1]["prompt_n"]
            full_2 = cached_results[1][1]["cache_n"] + p2_delta
            d2_fed = cached_results[2][1]["cache_n"] - full_2
            p3_delta = cached_results[2][1]["prompt_n"]
            assert d1_fed >= 0 and d2_fed >= 0, (
                f"Unexpected cache_n shrink between turns: l1={l1}, "
                f"t2_cache={cached_results[1][1]['cache_n']}, full_2={full_2}, t3_cache={cached_results[2][1]['cache_n']}"
            )
            replay_plans = [
                [l1],
                [s for s in (l1, -d1_fed, p2_delta) if s != 0],
                [s for s in (l1, -d1_fed, p2_delta, -d2_fed, p3_delta) if s != 0],
            ]

            # Pass 2: exact debug_replay (reset + same prefill/GEMV segments as Pass 1) -> ASSERT cached == replay.
            replay_results = []
            for t_idx, (msgs_snapshot, plan) in enumerate(zip(turn_histories, replay_plans), 1):
                text_p, tim_p, ttft_p = chat_stream(
                    base_url,
                    msgs_snapshot,
                    max_tokens=max_tokens_long,
                    extra_fields={**common_extra, "cache_prompt": False, "debug_replay": plan},
                    return_ttft=True,
                )
                for req_key in REQUIRED_TIMING_KEYS:
                    assert req_key in tim_p, f"Missing timing key {req_key} in multiturn replay turn {t_idx}"
                replay_results.append((text_p, tim_p, ttft_p))

            # Pass 3: forced full-prefill reset (cache_prompt=False) -> TTFT speedup baseline + informational match report.
            reset_results = []
            for t_idx, msgs_snapshot in enumerate(turn_histories, 1):
                text_r, tim_r, ttft_r = chat_stream(
                    base_url,
                    msgs_snapshot,
                    max_tokens=max_tokens_long,
                    extra_fields={**common_extra, "cache_prompt": False},
                    return_ttft=True,
                )
                for req_key in REQUIRED_TIMING_KEYS:
                    assert req_key in tim_r, f"Missing timing key {req_key} in multiturn reset turn {t_idx}"
                reset_results.append((text_r, tim_r, ttft_r))

            ttft_t1 = cached_results[0][2]
            prompt_ms_t1 = cached_results[0][1]["prompt_ms"]
            prev_cache_n = 0
            reset_exact_cnt = 0
            for t_idx in range(1, 4):
                text_c, tim_c, ttft_c = cached_results[t_idx - 1]
                text_p, tim_p, _ = replay_results[t_idx - 1]
                text_r, tim_r, ttft_r = reset_results[t_idx - 1]
                full_n = tim_r["prompt_n"]
                cache_n = tim_c["cache_n"]
                pref_n = tim_c["prompt_n"]
                ttft_speedup = (ttft_r / ttft_c) if ttft_c > 0 else 1.0
                if text_c == text_r:
                    reset_exact_cnt += 1
                print(
                    f"[Turn {t_idx}] full_prompt={full_n} tok | cache_n={cache_n} | prompt_n={pref_n} | "
                    f"replay_plan={replay_plans[t_idx - 1]}\n"
                    f"  prompt_ms cached={tim_c['prompt_ms']:7.1f} vs reset={tim_r['prompt_ms']:7.1f} | "
                    f"TTFT cached={ttft_c:7.1f} ms vs reset={ttft_r:7.1f} ms ({ttft_speedup:5.1f}x) | "
                    f"pred={tim_c['predicted_n']} tok ({tim_c['predicted_per_second']:5.2f} t/s)\n"
                    f"  cached==replay: {'EXACT' if text_c == text_p else 'MISMATCH'} | "
                    f"cached==reset (info): {'EXACT' if text_c == text_r else 'DIVERGED (WMMA vs GEMV)'} | "
                    f"reply={text_c[:80]!r}"
                )

                assert tim_p["cache_n"] == 0, f"Turn {t_idx}: expected cache_n == 0 in debug_replay, got {tim_p}"
                assert tim_p["prompt_n"] == full_n, (
                    f"Turn {t_idx}: debug_replay prompt_n ({tim_p['prompt_n']}) != full_prompt ({full_n})"
                )
                assert tim_r["cache_n"] == 0, f"Turn {t_idx}: expected cache_n == 0 with cache_prompt=False, got {tim_r}"
                assert pref_n + cache_n == full_n, (
                    f"Turn {t_idx}: prompt_n ({pref_n}) + cache_n ({cache_n}) != full_prompt ({full_n})"
                )
                assert text_c == text_p, (
                    f"MULTITURN BIT-EXACT FAIL (cached != replay) on Turn {t_idx}:\n"
                    f"  cached: {text_c!r}\n  replay: {text_p!r}"
                )
                if t_idx == 1:
                    assert cache_n == 0, f"Turn 1: expected cold cache_n == 0, got {cache_n}"
                else:
                    assert cache_n > prev_cache_n, (
                        f"Turn {t_idx}: expected prefix cache hit (cache_n > {prev_cache_n}), got {cache_n}"
                    )
                    assert pref_n < cache_n, (
                        f"Turn {t_idx}: expected incremental prompt_n ({pref_n}) < cache_n ({cache_n})"
                    )
                    assert ttft_c < ttft_t1 * 0.5, (
                        f"Turn {t_idx}: expected TTFT ({ttft_c:.1f} ms) << Turn 1 TTFT ({ttft_t1:.1f} ms)"
                    )
                    assert tim_c["prompt_ms"] < prompt_ms_t1 * 0.5, (
                        f"Turn {t_idx}: expected prompt_ms ({tim_c['prompt_ms']:.1f} ms) << Turn 1 ({prompt_ms_t1:.1f} ms)"
                    )
                prev_cache_n = cache_n

            print(
                f"MULTITURN PASS (3/3 turns bit-exact cached == replay; vs_reset={reset_exact_cnt}/3 info, "
                f"TTFT T1={ttft_t1:.1f} ms -> T2={cached_results[1][2]:.1f} ms -> T3={cached_results[2][2]:.1f} ms)"
            )
            return

        if bench_sweep:
            run_greedy = sweep_only in ("all", "greedy")
            run_coupled = sweep_only in ("all", "coupled")
            run_lookup = sweep_only in ("all", "lookup")
            print(f"\n=== Speculative Parameter Sweep (mode={sweep_only}, repeats={repeats}, W={eff_w_label}) ===")

            # Part 1: T=0 greedy sweep (draft_n_max 3 vs 5 x draft_p_min 0.5 vs 0.3)
            if run_greedy:
                greedy_configs = [
                    ("K=3 p_min=0.5", {"draft_n_max": 3, "draft_p_min": 0.5}),
                    ("K=3 p_min=0.3", {"draft_n_max": 3, "draft_p_min": 0.3}),
                    ("K=5 p_min=0.5", {"draft_n_max": 5, "draft_p_min": 0.5}),
                    ("K=5 p_min=0.3", {"draft_n_max": 5, "draft_p_min": 0.3}),
                ]
                print(f"\n--- Sweep A: Greedy T=0 (5 tasks x {repeats} repeats) ---")
                greedy_base = {}
                for label, q, max_tok in tasks:
                    ns_runs = []
                    ref_text = None
                    for rep in range(repeats):
                        txt, tim = chat_non_stream(
                            base_url, q, max_tokens=max_tok,
                            extra_fields={"temperature": 0.0, "no_spec": True, "cache_prompt": False},
                        )
                        if ref_text is None:
                            ref_text = txt
                        else:
                            assert txt == ref_text, f"Non-deterministic greedy baseline on {label}"
                        ns_runs.append(tim["predicted_per_second"])
                    greedy_base[label] = (ref_text, statistics.median(ns_runs))

                for cname, cextra in greedy_configs:
                    meds = []
                    ms_steps = []
                    tot_acc = 0
                    tot_dr = 0
                    for label, q, max_tok in tasks:
                        ref_text, med_ns = greedy_base[label]
                        sp_runs = []
                        step_runs = []
                        last_tim = {}
                        for rep in range(repeats):
                            txt, tim = chat_non_stream(
                                base_url, q, max_tokens=max_tok,
                                extra_fields={"temperature": 0.0, "no_spec": False, "cache_prompt": False, **cextra},
                            )
                            assert txt == ref_text, f"SWEEP T=0 BIT-EXACT FAIL ({cname}, {label}): {txt!r} != {ref_text!r}"
                            sp_runs.append(tim["predicted_per_second"])
                            step_runs.append(tim["ms_per_step"])
                            last_tim = tim
                        med_sp = statistics.median(sp_runs)
                        meds.append(med_sp)
                        ms_steps.append(statistics.median(step_runs))
                        tot_acc += last_tim.get("draft_n_accepted", 0)
                        tot_dr += last_tim.get("draft_n", 0)
                        print(
                            f"  [{cname} | {label}] med={med_sp:6.2f} t/s (no-spec={med_ns:5.2f}, "
                            f"{med_sp / med_ns if med_ns > 0 else 1.0:.2f}x, {statistics.median(step_runs):5.2f} ms/step, "
                            f"draft={last_tim.get('draft_n_accepted', 0)}/{last_tim.get('draft_n', 0)})"
                        )
                    base_med = statistics.median(v[1] for v in greedy_base.values())
                    cfg_med = statistics.median(meds)
                    cfg_mean = sum(meds) / len(meds)
                    acc_rate = (tot_acc / tot_dr) if tot_dr > 0 else 0.0
                    print(
                        f"  => SUMMARY [{cname}]: median-of-medians={cfg_med:6.2f} t/s ({cfg_med / base_med if base_med > 0 else 1.0:.2f}x) | "
                        f"mean={cfg_mean:6.2f} t/s | acc={tot_acc}/{tot_dr} ({acc_rate:.2f}) | bit-exact=5/5"
                    )

            # Part 2: Coupled Gumbel-Max T=0.7 sweep: baseline K=3 p_min=0.5 + full K in {3,4,5} x p_min in {0.2, 0.0}
            if run_coupled:
                coupled_tasks = tasks + [
                    (
                        "Q6 (Creative T=0.7, 200t)",
                        "Write a vivid short story (~180 words) about a lighthouse keeper watching a sudden winter storm approach across the sea.",
                        200,
                    ),
                ]
                coupled_temp = temp if temp > 0.0 else 0.7
                coupled_configs = [
                    (f"T={coupled_temp} K=3 p_min=0.5 (base)", {"draft_n_max": 3, "draft_p_min": 0.5}),
                    (f"T={coupled_temp} K=3 p_min=0.2", {"draft_n_max": 3, "draft_p_min": 0.2}),
                    (f"T={coupled_temp} K=3 p_min=0.0", {"draft_n_max": 3, "draft_p_min": 0.0}),
                    (f"T={coupled_temp} K=4 p_min=0.2", {"draft_n_max": 4, "draft_p_min": 0.2}),
                    (f"T={coupled_temp} K=4 p_min=0.0", {"draft_n_max": 4, "draft_p_min": 0.0}),
                    (f"T={coupled_temp} K=5 p_min=0.2", {"draft_n_max": 5, "draft_p_min": 0.2}),
                    (f"T={coupled_temp} K=5 p_min=0.0", {"draft_n_max": 5, "draft_p_min": 0.0}),
                ]
                print(
                    f"\n--- Sweep B: Coupled Gumbel-Max T={coupled_temp} seed={seed} "
                    f"(K in {{3,4,5}} x p_min in {{0.2,0.0}} + K=3 p_min=0.5 base; 6 tasks x {repeats} repeats) ---"
                )
                coupled_base_extra = {
                    "temperature": coupled_temp,
                    "seed": seed,
                    "top_k": 40,
                    "top_p": 0.95,
                    "min_p": 0.05,
                    "use_coupled": True,
                    "cache_prompt": False,
                }
                coupled_base = {}
                for label, q, max_tok in coupled_tasks:
                    ns_runs = []
                    ref_text = None
                    for rep in range(repeats):
                        txt, tim = chat_non_stream(
                            base_url, q, max_tokens=max_tok,
                            extra_fields={**coupled_base_extra, "no_spec": True},
                        )
                        if ref_text is None:
                            ref_text = txt
                        else:
                            assert txt == ref_text, f"Non-deterministic coupled baseline on {label}"
                        ns_runs.append(tim["predicted_per_second"])
                    coupled_base[label] = (ref_text, statistics.median(ns_runs))

                coupled_summary = []
                for cname, cextra in coupled_configs:
                    meds = []
                    q6_med = 0.0
                    q6_tok_step = 0.0
                    q6_ms_step = 0.0
                    q6_acc_str = "0/0"
                    tot_acc = 0
                    tot_dr = 0
                    for label, q, max_tok in coupled_tasks:
                        ref_text, med_ns = coupled_base[label]
                        sp_runs = []
                        step_runs = []
                        tok_step_runs = []
                        last_tim = {}
                        for rep in range(repeats):
                            txt, tim = chat_non_stream(
                                base_url, q, max_tokens=max_tok,
                                extra_fields={**coupled_base_extra, "no_spec": False, **cextra},
                            )
                            assert txt == ref_text, f"SWEEP COUPLED BIT-EXACT FAIL ({cname}, {label}): {txt!r} != {ref_text!r}"
                            sp_runs.append(tim["predicted_per_second"])
                            step_runs.append(tim["ms_per_step"])
                            tok_step_runs.append(tim["tok_per_step"])
                            last_tim = tim
                        med_sp = statistics.median(sp_runs)
                        med_ms = statistics.median(step_runs)
                        med_ts = statistics.median(tok_step_runs)
                        meds.append(med_sp)
                        tot_acc += last_tim.get("draft_n_accepted", 0)
                        tot_dr += last_tim.get("draft_n", 0)
                        if label.startswith("Q6"):
                            q6_med = med_sp
                            q6_tok_step = med_ts
                            q6_ms_step = med_ms
                            q6_acc_str = f"{last_tim.get('draft_n_accepted', 0)}/{last_tim.get('draft_n', 0)}"
                        print(
                            f"  [{cname} | {label}] med={med_sp:6.2f} t/s (no-spec={med_ns:5.2f}, "
                            f"{med_sp / med_ns if med_ns > 0 else 1.0:.2f}x, {med_ts:4.2f} tok/st, {med_ms:5.2f} ms/st, "
                            f"draft={last_tim.get('draft_n_accepted', 0)}/{last_tim.get('draft_n', 0)})"
                        )
                    base_med = statistics.median(v[1] for v in coupled_base.values())
                    cfg_med = statistics.median(meds)
                    cfg_mean = sum(meds) / len(meds)
                    acc_rate = (tot_acc / tot_dr) if tot_dr > 0 else 0.0
                    coupled_summary.append((cname, q6_med, q6_tok_step, q6_ms_step, q6_acc_str, cfg_med, cfg_mean, acc_rate))
                    print(
                        f"  => SUMMARY [{cname}]: Q6_creative={q6_med:6.2f} t/s ({q6_tok_step:.2f} tok/st, {q6_ms_step:.2f} ms/st) | "
                        f"all6_med={cfg_med:6.2f} t/s ({cfg_med / base_med if base_med > 0 else 1.0:.2f}x) | "
                        f"all6_mean={cfg_mean:6.2f} t/s | acc={tot_acc}/{tot_dr} ({acc_rate:.2f}) | bit-exact=6/6"
                    )

                print("\n  --- Sweep B Table (Coupled T={:.1f}) ---".format(coupled_temp))
                print("  config                          | Q6 creat t/s | Q6 tok/st | Q6 ms/st | Q6 draft  | all6 med | all6 mean | acc")
                for cname, q6_med, q6_ts, q6_ms, q6_acc, cfg_med, cfg_mean, acc_r in coupled_summary:
                    print(
                        f"  {cname:31s} | {q6_med:12.2f} | {q6_ts:9.2f} | {q6_ms:8.2f} | {q6_acc:9s} | "
                        f"{cfg_med:8.2f} | {cfg_mean:9.2f} | {acc_r:.3f}"
                    )

            # Part 3: Lookup policy sweep (Q4 40L, Q5 40L, and C2 ~180L) for lookup_min_match x lookup_tail_min
            if run_lookup:
                lookup_tasks = [
                    ("Q4 (Py 40L)", COPY_TASK_1, 160),
                    ("Q5 (C++ 40L)", COPY_TASK_2, 160),
                    ("C2 (C++ ~180L)", BENCH_COPY_TASKS[1][1], 2048),
                ]
                lookup_configs = [
                    ("no-tail (pure MTP)", {"lookup_tail": False}),
                    ("mmin=5 tail_min=1", {"lookup_tail": True, "lookup_min_match": 5, "lookup_tail_min": 1}),
                    ("mmin=6 tail_min=1", {"lookup_tail": True, "lookup_min_match": 6, "lookup_tail_min": 1}),
                    ("mmin=6 tail_min=2 (def)", {"lookup_tail": True, "lookup_min_match": 6, "lookup_tail_min": 2}),
                    ("mmin=7 tail_min=2", {"lookup_tail": True, "lookup_min_match": 7, "lookup_tail_min": 2}),
                    ("mmin=8 tail_min=2", {"lookup_tail": True, "lookup_min_match": 8, "lookup_tail_min": 2}),
                ]
                print(f"\n--- Sweep C: Lookup Policy (T=0, W={eff_w_label}, Q4/Q5/C2 x {repeats} repeats) ---")
                lk_ref = {}
                for cname, cextra in lookup_configs:
                    row_parts = []
                    for label, q, max_tok in lookup_tasks:
                        extra = {"temperature": 0.0, "no_spec": False, "cache_prompt": False, **cextra}
                        if lookup_max_w is not None:
                            extra["lookup_max_w"] = lookup_max_w
                        tps_runs = []
                        last_tim = {}
                        for rep in range(repeats):
                            txt, tim = chat_non_stream(base_url, q, max_tokens=max_tok, extra_fields=extra)
                            if label not in lk_ref:
                                lk_ref[label] = txt
                            else:
                                assert txt == lk_ref[label], (
                                    f"SWEEP LOOKUP BIT-EXACT FAIL ({cname}, {label}): len {len(txt)} != {len(lk_ref[label])}"
                                )
                            tps_runs.append(tim["predicted_per_second"])
                            last_tim = tim
                        med_tps = statistics.median(tps_runs)
                        st = last_tim.get("verify_steps", 0)
                        t_st = last_tim.get("lookup_tail_steps", 0)
                        c_st = last_tim.get("lookup_chain_steps", 0)
                        row_parts.append(f"{label}: {med_tps:6.1f} t/s ({st:3d} st, T={t_st}/C={c_st})")
                    print(f"  [{cname:23s}] " + " | ".join(row_parts))

            print(f"BENCH SWEEP PASS (mode={sweep_only}, all configs bit-exact)")
            return

        if bench_copy:
            copy_extra = {
                "temperature": temp,
                "seed": seed,
                "use_coupled": True,
                "cache_prompt": False,
            }
            if draft_n_max is not None:
                copy_extra["draft_n_max"] = draft_n_max
            if draft_p_min is not None:
                copy_extra["draft_p_min"] = draft_p_min
            if lookup_max_w is not None:
                copy_extra["lookup_max_w"] = lookup_max_w
            if lookup_min_match is not None:
                copy_extra["lookup_min_match"] = lookup_min_match
            if lookup_tail_min is not None:
                copy_extra["lookup_tail_min"] = lookup_tail_min

            print(
                f"\n=== Copy-Edit Benchmark ({len(BENCH_COPY_TASKS)} tasks ~150L x {repeats} repeats, "
                f"max_tokens={max_tokens_long}, T={temp}, seed={seed}, W={eff_w_label}, lookup_tail=true vs false) ==="
            )
            all_notail_tps = []
            all_tail_tps = []
            all_notail_toks = []
            all_tail_toks = []
            tot_nt_acc = 0
            tot_nt_dr = 0
            tot_tl_acc = 0
            tot_tl_dr = 0
            tot_lk_acc = 0
            tot_lk_dr = 0
            tot_tail_steps = 0
            tot_chain_steps = 0

            for label, prompt_text in BENCH_COPY_TASKS:
                nt_tps_runs = []
                tl_tps_runs = []
                ns_tps_runs = []
                nt_toks_runs = []
                tl_toks_runs = []
                nt_ms_runs = []
                tl_ms_runs = []
                ref_text = None
                last_tim_nt = {}
                last_tim_tl = {}

                for rep in range(repeats):
                    text_nt, tim_nt = chat_non_stream(
                        base_url,
                        prompt_text,
                        max_tokens=max_tokens_long,
                        extra_fields={**copy_extra, "no_spec": False, "lookup_tail": False},
                    )
                    text_tl, tim_tl = chat_non_stream(
                        base_url,
                        prompt_text,
                        max_tokens=max_tokens_long,
                        extra_fields={**copy_extra, "no_spec": False, "lookup_tail": True},
                    )
                    for req_key in REQUIRED_TIMING_KEYS:
                        assert req_key in tim_nt, f"Missing timing key {req_key} in bench-copy no-tail response"
                        assert req_key in tim_tl, f"Missing timing key {req_key} in bench-copy tail response"

                    assert tim_nt.get("lookup_tail_steps", 0) == 0 and tim_nt.get("lookup_chain_steps", 0) == 0, (
                        f"Expected 0 lookup tail/chain steps when lookup_tail=False, got {tim_nt}"
                    )
                    assert text_tl == text_nt, (
                        f"BENCH COPY BIT-EXACT FAIL on {label} rep {rep + 1} (T={temp}, seed={seed}):\n"
                        f"  no-tail len={len(text_nt)} vs tail len={len(text_tl)}"
                    )
                    if with_nospec:
                        text_ns, tim_ns = chat_non_stream(
                            base_url,
                            prompt_text,
                            max_tokens=max_tokens_long,
                            extra_fields={**copy_extra, "no_spec": True, "lookup_tail": False},
                        )
                        assert text_tl == text_ns, (
                            f"BENCH COPY BIT-EXACT FAIL vs no-spec on {label} rep {rep + 1} (T={temp}, seed={seed})"
                        )
                        ns_tps_runs.append(tim_ns["predicted_per_second"])
                    if ref_text is None:
                        ref_text = text_nt
                    else:
                        assert text_nt == ref_text, f"Non-deterministic output on {label} rep {rep + 1}"

                    nt_tps_runs.append(tim_nt["predicted_per_second"])
                    tl_tps_runs.append(tim_tl["predicted_per_second"])
                    nt_toks_runs.append(tim_nt["tok_per_step"])
                    tl_toks_runs.append(tim_tl["tok_per_step"])
                    nt_ms_runs.append(tim_nt["ms_per_step"])
                    tl_ms_runs.append(tim_tl["ms_per_step"])
                    last_tim_nt = tim_nt
                    last_tim_tl = tim_tl

                med_nt = statistics.median(nt_tps_runs)
                med_tl = statistics.median(tl_tps_runs)
                med_nt_toks = statistics.median(nt_toks_runs)
                med_tl_toks = statistics.median(tl_toks_runs)
                med_nt_ms = statistics.median(nt_ms_runs)
                med_tl_ms = statistics.median(tl_ms_runs)
                gain_x = (med_tl / med_nt) if med_nt > 0 else 1.0
                gain_pct = (gain_x - 1.0) * 100.0

                nt_acc = last_tim_nt.get("draft_n_accepted", 0)
                nt_dr = last_tim_nt.get("draft_n", 0)
                tl_acc = last_tim_tl.get("draft_n_accepted", 0)
                tl_dr = last_tim_tl.get("draft_n", 0)
                lk_acc = last_tim_tl.get("lookup_draft_accepted", 0)
                lk_dr = last_tim_tl.get("lookup_draft_n", 0)
                t_steps = last_tim_tl.get("lookup_tail_steps", 0)
                c_steps = last_tim_tl.get("lookup_chain_steps", 0)

                nt_rate = (nt_acc / nt_dr) if nt_dr > 0 else 0.0
                tl_rate = (tl_acc / tl_dr) if tl_dr > 0 else 0.0
                lk_rate = (lk_acc / lk_dr) if lk_dr > 0 else 0.0

                all_notail_tps.append(med_nt)
                all_tail_tps.append(med_tl)
                all_notail_toks.append(med_nt_toks)
                all_tail_toks.append(med_tl_toks)
                tot_nt_acc += nt_acc
                tot_nt_dr += nt_dr
                tot_tl_acc += tl_acc
                tot_tl_dr += tl_dr
                tot_lk_acc += lk_acc
                tot_lk_dr += lk_dr
                tot_tail_steps += t_steps
                tot_chain_steps += c_steps

                ns_str = f" | no-spec={statistics.median(ns_tps_runs):6.2f} t/s" if ns_tps_runs else ""
                print(
                    f"[{label}] prompt={last_tim_tl.get('prompt_n')} tok | pred={last_tim_tl.get('predicted_n')} tok{ns_str}\n"
                    f"  no-tail (MTP) : {med_nt:6.2f} t/s | {med_nt_toks:5.2f} tok/step | {med_nt_ms:5.2f} ms/step | "
                    f"acc={nt_acc}/{nt_dr} ({nt_rate:.3f})\n"
                    f"  tail+chain W{eff_w_label:<2d}: {med_tl:6.2f} t/s ({gain_x:.2f}x, {gain_pct:+.1f}%) | "
                    f"{med_tl_toks:5.2f} tok/step | {med_tl_ms:5.2f} ms/step | acc={tl_acc}/{tl_dr} ({tl_rate:.3f}) | "
                    f"tail={t_steps} chain={c_steps} lk_acc={lk_acc}/{lk_dr} ({lk_rate:.3f}) | match=EXACT"
                )

            med_nt_all = statistics.median(all_notail_tps)
            med_tl_all = statistics.median(all_tail_tps)
            avg_nt_all = sum(all_notail_tps) / len(all_notail_tps)
            avg_tl_all = sum(all_tail_tps) / len(all_tail_tps)
            avg_nt_toks = sum(all_notail_toks) / len(all_notail_toks)
            avg_tl_toks = sum(all_tail_toks) / len(all_tail_toks)
            nt_all_rate = (tot_nt_acc / tot_nt_dr) if tot_nt_dr > 0 else 0.0
            tl_all_rate = (tot_tl_acc / tot_tl_dr) if tot_tl_dr > 0 else 0.0
            lk_all_rate = (tot_lk_acc / tot_lk_dr) if tot_lk_dr > 0 else 0.0
            print(
                f"BENCH COPY SUMMARY ({len(BENCH_COPY_TASKS)} tasks x {repeats}, T={temp}):\n"
                f"  median t/s : no-tail={med_nt_all:6.2f} -> tail={med_tl_all:6.2f} "
                f"({(med_tl_all / med_nt_all) if med_nt_all > 0 else 1.0:.2f}x) | "
                f"mean t/s : no-tail={avg_nt_all:6.2f} -> tail={avg_tl_all:6.2f} "
                f"({(avg_tl_all / avg_nt_all) if avg_nt_all > 0 else 1.0:.2f}x)\n"
                f"  mean tok/step: {avg_nt_toks:.2f} -> {avg_tl_toks:.2f} | "
                f"draft acc: {tot_nt_acc}/{tot_nt_dr} ({nt_all_rate:.3f}) -> {tot_tl_acc}/{tot_tl_dr} ({tl_all_rate:.3f}) | "
                f"lookup: tail_steps={tot_tail_steps} chain_steps={tot_chain_steps} "
                f"acc={tot_lk_acc}/{tot_lk_dr} ({lk_all_rate:.3f})"
            )
            print(f"BENCH COPY PASS ({len(BENCH_COPY_TASKS)}/{len(BENCH_COPY_TASKS)} tasks bit-exact lookup_tail=true == false)")
            return

        if bench_long:
            long_tail_extra = {"no_spec": False, "lookup_tail": True, "cache_prompt": False}
            if lookup_max_w is not None:
                long_tail_extra["lookup_max_w"] = lookup_max_w
            if lookup_min_match is not None:
                long_tail_extra["lookup_min_match"] = lookup_min_match
            if lookup_tail_min is not None:
                long_tail_extra["lookup_tail_min"] = lookup_tail_min
            print(
                f"\n=== Long-Context Benchmark (sizes={long_sizes}, max_tokens={max_tokens_long}, "
                f"repeats={repeats}; no-spec vs no-tail vs lookup-tail W{eff_w_label}) ==="
            )
            for target_len in long_sizes:
                prompt_text = calibrate_long_prompt(base_url, target_len)
                pf_tps_list = []
                pf_ms_list = []
                ttft_list = []
                ns_tps_list = []
                nt_tps_list = []
                sp_tps_list = []
                last_tim_nt = {}
                last_tim_sp = {}
                ref_text = None

                for rep in range(repeats):
                    text_ns, tim_ns = chat_non_stream(
                        base_url, prompt_text, max_tokens=max_tokens_long,
                        extra_fields={"no_spec": True, "cache_prompt": False},
                    )
                    text_nt, tim_nt = chat_non_stream(
                        base_url, prompt_text, max_tokens=max_tokens_long,
                        extra_fields={"no_spec": False, "lookup_tail": False, "cache_prompt": False},
                    )
                    text_sp, tim_sp = chat_non_stream(
                        base_url, prompt_text, max_tokens=max_tokens_long,
                        extra_fields=long_tail_extra,
                    )
                    text_st, tim_st, ttft_ms = chat_stream(
                        base_url, prompt_text, max_tokens=max_tokens_long,
                        extra_fields=long_tail_extra,
                        return_ttft=True,
                    )

                    for req_key in REQUIRED_TIMING_KEYS:
                        assert req_key in tim_ns, f"Missing timing key {req_key} in long no-spec response"
                        assert req_key in tim_nt, f"Missing timing key {req_key} in long no-tail response"
                        assert req_key in tim_sp, f"Missing timing key {req_key} in long spec response"
                        assert req_key in tim_st, f"Missing timing key {req_key} in long stream response"

                    assert tim_ns.get("draft_n", 0) == 0, f"Expected draft_n == 0 for no-spec, got {tim_ns}"
                    assert tim_sp["prompt_n"] > 0 and tim_sp["prompt_ms"] > 0 and tim_sp["prompt_per_second"] > 0, (
                        f"Invalid prompt timings: {tim_sp}"
                    )
                    assert text_nt == text_ns, (
                        f"LOSSLESS LONG-CTX FAIL (no-tail) at ~{target_len} tok rep {rep + 1}:\n"
                        f"  no-spec: {text_ns!r}\n  no-tail: {text_nt!r}"
                    )
                    assert text_sp == text_ns, (
                        f"LOSSLESS LONG-CTX FAIL (tail) at ~{target_len} tok rep {rep + 1}:\n"
                        f"  no-spec: {text_ns!r}\n  spec   : {text_sp!r}"
                    )
                    assert text_st == text_sp, (
                        f"SSE != non-stream at ~{target_len} tok rep {rep + 1}:\n"
                        f"  stream : {text_st!r}\n  spec   : {text_sp!r}"
                    )
                    if ref_text is None:
                        ref_text = text_ns
                    else:
                        assert text_ns == ref_text, f"Non-deterministic output at ~{target_len} tok rep {rep + 1}"

                    pf_tps_list.append(tim_sp["prompt_per_second"])
                    pf_ms_list.append(tim_sp["prompt_ms"])
                    ttft_list.append(ttft_ms)
                    ns_tps_list.append(tim_ns["predicted_per_second"])
                    nt_tps_list.append(tim_nt["predicted_per_second"])
                    sp_tps_list.append(tim_sp["predicted_per_second"])
                    last_tim_nt = tim_nt
                    last_tim_sp = tim_sp

                med_pf = statistics.median(pf_tps_list)
                med_pf_ms = statistics.median(pf_ms_list)
                med_ttft = statistics.median(ttft_list)
                med_ns = statistics.median(ns_tps_list)
                med_nt = statistics.median(nt_tps_list)
                med_sp = statistics.median(sp_tps_list)
                speedup_ns = (med_sp / med_ns) if med_ns > 0 else 1.0
                speedup_nt = (med_sp / med_nt) if med_nt > 0 else 1.0
                nt_n = last_tim_nt.get("draft_n", 0)
                nt_acc = last_tim_nt.get("draft_n_accepted", 0)
                nt_rate = (nt_acc / nt_n) if nt_n > 0 else 0.0
                d_n = last_tim_sp.get("draft_n", 0)
                d_acc = last_tim_sp.get("draft_n_accepted", 0)
                acc_rate = (d_acc / d_n) if d_n > 0 else 0.0
                print(
                    f"[L~{target_len}] prompt={last_tim_sp.get('prompt_n')} tok | "
                    f"prefill={med_pf:6.1f} t/s ({med_pf_ms:7.1f} ms) | TTFT={med_ttft:7.1f} ms\n"
                    f"  no-spec : {med_ns:6.2f} t/s\n"
                    f"  no-tail : {med_nt:6.2f} t/s ({last_tim_nt.get('tok_per_step', 0):.2f} tok/step, "
                    f"draft={nt_acc}/{nt_n} [{nt_rate:.2f}], {last_tim_nt.get('ms_per_step', 0):.2f} ms/step)\n"
                    f"  tail W{eff_w_label:<2d}: {med_sp:6.2f} t/s ({speedup_ns:.2f}x vs no-spec, {speedup_nt:.2f}x vs no-tail, "
                    f"{last_tim_sp.get('tok_per_step', 0):.2f} tok/step, draft={d_acc}/{d_n} [{acc_rate:.2f}], "
                    f"tail={last_tim_sp.get('lookup_tail_steps', 0)} chain={last_tim_sp.get('lookup_chain_steps', 0)}, "
                    f"{last_tim_sp.get('ms_per_step', 0):.2f} ms/step) | match=EXACT"
                )
            print(f"BENCH LONG PASS ({len(long_sizes)}/{len(long_sizes)} sizes bit-exact no-spec == no-tail == tail == SSE)")
            return

        if compare_coupled:
            coupled_tasks = tasks + [
                (
                    "Q6 (Creative T>0)",
                    "Write a short paragraph (3-4 sentences) about a lighthouse keeper watching a storm approach.",
                    96,
                ),
            ]
            print(f"\n=== Coupled Gumbel-Max T>0 Bit-Exact Comparison (T={temp}, seed={seed}, use_coupled=True) ===")
            for idx, (label, q, max_tok) in enumerate(coupled_tasks, 1):
                base_extra = {
                    "temperature": temp,
                    "seed": seed,
                    "top_k": 40,
                    "top_p": 0.95,
                    "min_p": 0.05,
                    "use_coupled": True,
                }
                text_ns, tim_ns = chat_non_stream(
                    base_url, q, max_tokens=max_tok, extra_fields={**base_extra, "no_spec": True}
                )
                text_sp, tim_sp = chat_non_stream(
                    base_url, q, max_tokens=max_tok, extra_fields={**base_extra, "no_spec": False}
                )
                text_st, _ = chat_stream(
                    base_url, q, max_tokens=max_tok, extra_fields={**base_extra, "no_spec": False}
                )

                for req_key in REQUIRED_TIMING_KEYS:
                    assert req_key in tim_ns, f"Missing timing key {req_key} in coupled no-spec response"
                    assert req_key in tim_sp, f"Missing timing key {req_key} in coupled spec response"

                tps_ns = tim_ns.get("predicted_per_second", 0.0)
                tps_sp = tim_sp.get("predicted_per_second", 0.0)
                d_n = tim_sp.get("draft_n", 0)
                d_acc = tim_sp.get("draft_n_accepted", 0)
                acc_rate = (d_acc / d_n) if d_n > 0 else 0.0
                speedup = (tps_sp / tps_ns) if tps_ns > 0 else 1.0

                print(
                    f"[{label}] prompt={tim_sp.get('prompt_n')} tok | pred={tim_sp.get('predicted_n')} tok\n"
                    f"  no-spec : {tps_ns:6.2f} t/s ({tim_ns.get('predicted_ms', 0):7.1f} ms, steps={tim_ns.get('verify_steps')})\n"
                    f"  spec    : {tps_sp:6.2f} t/s ({tim_sp.get('predicted_ms', 0):7.1f} ms, steps={tim_sp.get('verify_steps')}, "
                    f"{tim_sp.get('ms_per_step', 0):.2f} ms/step, draft={d_acc}/{d_n} [{acc_rate:.2f}], speedup={speedup:.2f}x)\n"
                    f"  match   : {'EXACT' if text_sp == text_ns else 'MISMATCH'} | preview: {text_sp[:70]!r}"
                )

                assert tim_ns.get("draft_n", 0) == 0, f"Expected draft_n == 0 for no-spec, got {tim_ns}"
                assert text_sp == text_ns, (
                    f"COUPLED T>0 BIT-EXACT FAIL on {label} (T={temp}, seed={seed}):\n"
                    f"  no-spec: {text_ns!r}\n  spec   : {text_sp!r}"
                )
                assert text_st == text_sp, f"Coupled T>0 SSE stream != non-stream on {label}"

            print(f"COMPARE COUPLED PASS ({len(coupled_tasks)}/{len(coupled_tasks)} tasks bit-exact at T={temp}, seed={seed})")
            return

        if not compare_spec and not bench:
            for idx, (label, q, max_tok) in enumerate(questions, 1):
                text_ns, tim_ns = chat_non_stream(base_url, q, max_tokens=max_tok)
                text_st, tim_st = chat_stream(base_url, q, max_tokens=max_tok)

                print(
                    f"[{label}] {q!r}\n"
                    f"  non-stream: {text_ns!r} (prompt={tim_ns.get('prompt_n')} tok / {tim_ns.get('prompt_ms', 0):.1f} ms, "
                    f"pred={tim_ns.get('predicted_n')} tok / {tim_ns.get('predicted_ms', 0):.1f} ms, "
                    f"{tim_ns.get('predicted_per_second', 0):.2f} t/s, "
                    f"steps={tim_ns.get('verify_steps', 0)}, {tim_ns.get('ms_per_step', 0):.2f} ms/step, "
                    f"draft={tim_ns.get('draft_n_accepted', 0)}/{tim_ns.get('draft_n', 0)})\n"
                    f"  stream    : {text_st!r}"
                )

                for req_key in REQUIRED_TIMING_KEYS:
                    assert req_key in tim_ns, f"Missing timing key {req_key} in non-stream response"

                assert text_ns.strip(), f"Empty response for {label}"
                assert text_st == text_ns, f"SSE stream != non-stream for {label}: {text_st!r} vs {text_ns!r}"

                if idx == 1:
                    assert "Paris" in text_ns, f"Expected 'Paris' in Q1 answer, got: {text_ns!r}"

            print("TEST SERVE PASS (3/3 questions, 'Paris' verified, SSE stream == non-stream 3/3)")
            return

        if bench:
            bench_extra = {}
            if draft_n_max is not None:
                bench_extra["draft_n_max"] = draft_n_max
            if draft_p_min is not None:
                bench_extra["draft_p_min"] = draft_p_min
            cfg_tag = f", extra={bench_extra}" if bench_extra else ""
            print(f"\n=== Server Benchmark ({len(tasks)} tasks x {repeats} repeats, T=0{cfg_tag}, median t/s spec vs no-spec) ===")
            all_med_nospec = []
            all_med_spec = []
            for idx, (label, q, max_tok) in enumerate(tasks, 1):
                nospec_tps = []
                spec_tps = []
                nospec_ms_step = []
                spec_ms_step = []
                ref_text = None
                last_tim_spec = {}

                for rep in range(repeats):
                    text_ns, tim_ns = chat_non_stream(base_url, q, max_tokens=max_tok, extra_fields={"no_spec": True})
                    text_sp, tim_sp = chat_non_stream(
                        base_url, q, max_tokens=max_tok, extra_fields={"no_spec": False, **bench_extra}
                    )

                    for req_key in REQUIRED_TIMING_KEYS:
                        assert req_key in tim_ns, f"Missing timing key {req_key} in no-spec response"
                        assert req_key in tim_sp, f"Missing timing key {req_key} in spec response"

                    assert tim_ns.get("draft_n", 0) == 0, f"Expected draft_n == 0 for no-spec, got {tim_ns}"
                    assert text_sp == text_ns, (
                        f"LOSSLESS BENCH FAIL on {label} rep {rep + 1}:\n  no-spec: {text_ns!r}\n  spec   : {text_sp!r}"
                    )
                    if ref_text is None:
                        ref_text = text_ns
                    else:
                        assert text_ns == ref_text, f"Non-deterministic T=0 output on {label} rep {rep + 1}"

                    nospec_tps.append(tim_ns["predicted_per_second"])
                    spec_tps.append(tim_sp["predicted_per_second"])
                    nospec_ms_step.append(tim_ns["ms_per_step"])
                    spec_ms_step.append(tim_sp["ms_per_step"])
                    last_tim_spec = tim_sp

                if idx == 1:
                    assert "Paris" in ref_text, f"Expected 'Paris' in Q1 answer, got: {ref_text!r}"

                med_ns = statistics.median(nospec_tps)
                med_sp = statistics.median(spec_tps)
                med_ms_ns = statistics.median(nospec_ms_step)
                med_ms_sp = statistics.median(spec_ms_step)
                speedup = (med_sp / med_ns) if med_ns > 0 else 1.0
                d_n = last_tim_spec.get("draft_n", 0)
                d_acc = last_tim_spec.get("draft_n_accepted", 0)
                acc_rate = (d_acc / d_n) if d_n > 0 else 0.0
                all_med_nospec.append(med_ns)
                all_med_spec.append(med_sp)

                print(
                    f"[{label}] pred={last_tim_spec.get('predicted_n')} tok | "
                    f"no-spec med={med_ns:6.2f} t/s ({med_ms_ns:5.2f} ms/step) | "
                    f"spec med={med_sp:6.2f} t/s ({med_ms_sp:5.2f} ms/step) | "
                    f"speedup={speedup:.2f}x | draft={d_acc}/{d_n} ({acc_rate:.2f}) | "
                    f"runs_spec=[{', '.join(f'{x:.1f}' for x in spec_tps)}]"
                )

            med_all_ns = statistics.median(all_med_nospec)
            med_all_sp = statistics.median(all_med_spec)
            avg_all_ns = sum(all_med_nospec) / len(all_med_nospec)
            avg_all_sp = sum(all_med_spec) / len(all_med_spec)
            med_ratio = (med_all_sp / med_all_ns) if med_all_ns > 0 else 1.0
            avg_ratio = (avg_all_sp / avg_all_ns) if avg_all_ns > 0 else 1.0
            print(
                f"BENCH SUMMARY (5 tasks x {repeats}): "
                f"median-of-medians no-spec={med_all_ns:.2f} t/s, spec={med_all_sp:.2f} t/s ({med_ratio:.2f}x) | "
                f"mean-of-medians no-spec={avg_all_ns:.2f} t/s, spec={avg_all_sp:.2f} t/s ({avg_ratio:.2f}x)"
            )
            print("BENCH PASS (5/5 tasks bit-exact across all repeats)")
            return

        # --compare-spec mode: 3 Q&A + 2 40-line code copy-edit tasks
        spec_extra = {"no_spec": False}
        if draft_n_max is not None:
            spec_extra["draft_n_max"] = draft_n_max
        if draft_p_min is not None:
            spec_extra["draft_p_min"] = draft_p_min
        if lookup_max_w is not None:
            spec_extra["lookup_max_w"] = lookup_max_w
        if lookup_min_match is not None:
            spec_extra["lookup_min_match"] = lookup_min_match
        if lookup_tail_min is not None:
            spec_extra["lookup_tail_min"] = lookup_tail_min
        print(f"\n=== Speculative (Lookup + MTP, W={eff_w_label}) vs Non-Speculative (--no-spec) Comparison (T=0) ===")
        for idx, (label, q, max_tok) in enumerate(tasks, 1):
            text_nospec, tim_nospec = chat_non_stream(base_url, q, max_tokens=max_tok, extra_fields={"no_spec": True})
            text_spec, tim_spec = chat_non_stream(base_url, q, max_tokens=max_tok, extra_fields=spec_extra)
            text_stream, _ = chat_stream(base_url, q, max_tokens=max_tok, extra_fields=spec_extra)

            for req_key in REQUIRED_TIMING_KEYS:
                assert req_key in tim_spec, f"Missing timing key {req_key} in spec response"
                assert req_key in tim_nospec, f"Missing timing key {req_key} in no-spec response"

            tps_nospec = tim_nospec.get("predicted_per_second", 0.0)
            tps_spec = tim_spec.get("predicted_per_second", 0.0)
            d_n = tim_spec.get("draft_n", 0)
            d_acc = tim_spec.get("draft_n_accepted", 0)
            lk_n = tim_spec.get("lookup_draft_n", 0)
            lk_acc = tim_spec.get("lookup_draft_accepted", 0)
            speedup = (tps_spec / tps_nospec) if tps_nospec > 0 else 1.0

            print(
                f"[{label}] prompt={tim_spec.get('prompt_n')} tok | pred={tim_spec.get('predicted_n')} tok\n"
                f"  no-spec : {tps_nospec:6.2f} t/s ({tim_nospec.get('predicted_ms', 0):7.1f} ms, "
                f"steps={tim_nospec.get('verify_steps')}, {tim_nospec.get('ms_per_step', 0):.2f} ms/step, "
                f"draft {tim_nospec.get('draft_n_accepted')}/{tim_nospec.get('draft_n')})\n"
                f"  spec    : {tps_spec:6.2f} t/s ({tim_spec.get('predicted_ms', 0):7.1f} ms, "
                f"steps={tim_spec.get('verify_steps')}, {tim_spec.get('ms_per_step', 0):.2f} ms/step, "
                f"draft {d_acc}/{d_n}, tail={tim_spec.get('lookup_tail_steps', 0)} "
                f"chain={tim_spec.get('lookup_chain_steps', 0)} lk={lk_acc}/{lk_n}, speedup {speedup:.2f}x)\n"
                f"  match   : {'EXACT' if text_spec == text_nospec else 'MISMATCH'} | preview: {text_spec[:70]!r}"
            )

            assert tim_nospec.get("draft_n", 0) == 0, f"Expected draft_n == 0 for no-spec, got {tim_nospec}"
            assert text_spec == text_nospec, (
                f"LOSSLESS SPEC FAIL on {label}:\n  no-spec: {text_nospec!r}\n  spec   : {text_spec!r}"
            )
            assert text_stream == text_spec, f"SSE stream != spec non-stream on {label}"
            if idx == 1:
                assert "Paris" in text_spec, f"Expected 'Paris' in Q1 answer, got: {text_spec!r}"

        print("COMPARE SPEC PASS (5/5 tasks bit-exact spec == no-spec == SSE stream)")
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
