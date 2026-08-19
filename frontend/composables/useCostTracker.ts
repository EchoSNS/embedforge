/**
 * Cost tracking composable — polls backend for LLM usage data.
 */

import { ref, onMounted, onUnmounted } from "vue";
import { useRuntimeConfig } from "#app";

export interface StageCost {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  calls: number;
}

export interface SessionCost {
  session_id: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  call_count: number;
  by_stage: Record<string, StageCost>;
}

export interface RecentCall {
  session_id: string;
  stage: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  duration_ms: number;
  timestamp: number;
}

export interface GlobalCostSummary {
  total_cost_usd: number;
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  session_count: number;
  recent_calls: RecentCall[];
}

export interface TimeBucket {
  timestamp: number;
  label: string;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  calls: number;
  by_stage: Record<string, number>;
}

export interface StageTotal {
  stage: string;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  calls: number;
  avg_duration_ms: number;
}

export interface BudgetStatus {
  budget_usd: number | null;
  spent_usd: number;
  remaining_usd: number | null;
  percent_used: number | null;
  exceeded: boolean;
}

export interface MetricsData {
  time_series: TimeBucket[];
  stage_totals: StageTotal[];
  budget: BudgetStatus;
}

export function useCostTracker(sessionId?: string) {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;

  const globalSummary = ref<GlobalCostSummary | null>(null);
  const sessionCost = ref<SessionCost | null>(null);
  const recentCalls = ref<RecentCall[]>([]);
  const metrics = ref<MetricsData | null>(null);
  const loading = ref(false);

  let pollInterval: ReturnType<typeof setInterval> | null = null;

  async function fetchGlobal() {
    try {
      const res = await fetch(`${apiBase}/api/cost/summary`);
      if (res.ok) globalSummary.value = await res.json();
    } catch {}
  }

  async function fetchSession() {
    if (!sessionId) return;
    try {
      const res = await fetch(`${apiBase}/api/cost/session/${sessionId}`);
      if (res.ok) sessionCost.value = await res.json();
    } catch {}
  }

  async function fetchRecent() {
    try {
      const res = await fetch(`${apiBase}/api/cost/recent?limit=20`);
      if (res.ok) recentCalls.value = await res.json();
    } catch {}
  }

  async function fetchMetrics(bucketMinutes = 60) {
    try {
      const res = await fetch(`${apiBase}/api/cost/metrics?bucket_minutes=${bucketMinutes}`);
      if (res.ok) metrics.value = await res.json();
    } catch {}
  }

  async function setBudget(budgetUsd: number | null) {
    try {
      const res = await fetch(`${apiBase}/api/cost/budget`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ budget_usd: budgetUsd }),
      });
      if (res.ok && metrics.value) {
        metrics.value.budget = await res.json();
      }
    } catch {}
  }

  async function refresh() {
    loading.value = true;
    await Promise.all([fetchGlobal(), fetchSession(), fetchRecent(), fetchMetrics()]);
    loading.value = false;
  }

  function startPolling(intervalMs = 5000) {
    refresh();
    pollInterval = setInterval(refresh, intervalMs);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  onMounted(() => startPolling());
  onUnmounted(() => stopPolling());

  return {
    globalSummary,
    sessionCost,
    recentCalls,
    metrics,
    loading,
    refresh,
    setBudget,
    startPolling,
    stopPolling,
  };
}
