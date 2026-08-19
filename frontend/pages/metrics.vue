<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <aside class="flex w-60 flex-col border-r bg-card/30 backdrop-blur-sm">
      <div class="flex h-14 items-center border-b px-4">
        <NuxtLink to="/" class="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft class="h-3 w-3" />
          Back to Workspace
        </NuxtLink>
      </div>
      <div class="flex-1 p-4 space-y-4">
        <div class="space-y-2">
          <span class="text-[10px] text-muted-foreground uppercase tracking-wider">Time Range</span>
          <div class="grid grid-cols-2 gap-1">
            <button
              v-for="opt in timeOptions"
              :key="opt.value"
              class="rounded-lg px-2 py-1.5 text-[10px] font-medium transition-all"
              :class="bucketMinutes === opt.value ? 'bg-primary text-primary-foreground' : 'bg-secondary text-muted-foreground hover:text-foreground'"
              @click="bucketMinutes = opt.value; refresh()"
            >{{ opt.label }}</button>
          </div>
        </div>

        <!-- Session Filter -->
        <div class="space-y-2">
          <span class="text-[10px] text-muted-foreground uppercase tracking-wider">Session</span>
          <select
            v-model="sessionFilter"
            class="w-full rounded-lg border bg-background px-2 py-1.5 text-[10px] focus:outline-none focus:ring-1 focus:ring-ring"
            @change="refresh()"
          >
            <option value="">All Sessions</option>
            <option v-for="s in sessionIds" :key="s" :value="s">{{ s.slice(0, 8) }}</option>
          </select>
        </div>

        <!-- Budget Config -->
        <div class="space-y-2">
          <span class="text-[10px] text-muted-foreground uppercase tracking-wider">Budget</span>
          <div class="space-y-2">
            <div class="relative">
              <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
              <input
                v-model.number="budgetInput"
                type="number"
                step="0.5"
                min="0"
                class="w-full rounded-lg border bg-background pl-6 pr-2 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="Set limit"
                @keydown.enter="applyBudget"
              />
            </div>
            <input
              v-model.number="budgetInput"
              type="range"
              min="0"
              max="50"
              step="0.5"
              class="w-full h-1.5 rounded-full accent-primary cursor-pointer"
            />
            <button
              class="w-full rounded-lg bg-primary/10 text-primary px-2 py-1.5 text-[10px] font-medium hover:bg-primary/20 transition-colors"
              @click="applyBudget"
            >Apply</button>
          </div>
        </div>

        <!-- Budget Status -->
        <div v-if="metrics?.budget?.budget_usd" class="rounded-lg border p-2.5 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="text-muted-foreground">Spent</span>
            <span class="font-medium">${{ formatCost(metrics.budget.spent_usd) }}</span>
          </div>
          <div class="h-2 rounded-full bg-accent overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="budgetBarColor"
              :style="{ width: `${Math.min(metrics.budget.percent_used ?? 0, 100)}%` }"
            />
          </div>
          <div class="flex items-center justify-between text-[10px] text-muted-foreground">
            <span>{{ metrics.budget.percent_used?.toFixed(1) }}% used</span>
            <span>${{ formatCost(metrics.budget.remaining_usd ?? 0) }} left</span>
          </div>
          <div v-if="metrics.budget.exceeded" class="flex items-center gap-1 text-[10px] text-red-400 font-medium">
            <AlertTriangle class="h-3 w-3" />
            Budget exceeded
          </div>
        </div>

        <!-- Auto-refresh -->
        <div class="space-y-2">
          <span class="text-[10px] text-muted-foreground uppercase tracking-wider">Auto-Refresh</span>
          <button
            class="w-full flex items-center justify-between rounded-lg border px-3 py-2 text-xs transition-colors"
            :class="autoRefresh ? 'border-primary/50 bg-primary/5' : 'hover:bg-accent'"
            @click="toggleAutoRefresh"
          >
            <span>{{ autoRefresh ? 'On (30s)' : 'Off' }}</span>
            <span class="h-2 w-2 rounded-full" :class="autoRefresh ? 'bg-green-400 animate-pulse' : 'bg-muted-foreground/30'" />
          </button>
        </div>

        <NuxtLink to="/settings" class="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors mt-4">
          <Settings class="h-3 w-3" />
          Settings
        </NuxtLink>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <div class="mx-auto max-w-5xl space-y-6">
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <h2 class="text-xl font-bold">Metrics Dashboard</h2>
            <p class="text-sm text-muted-foreground">LLM usage, cost breakdown, and performance metrics.</p>
          </div>
          <button
            class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
            @click="refresh"
          >
            <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': loading }" />
            Refresh
          </button>
        </div>

        <!-- Summary Cards -->
        <div class="grid grid-cols-4 gap-3">
          <div class="rounded-xl border bg-card p-4 space-y-1">
            <div class="text-[10px] text-muted-foreground uppercase tracking-wider">Total Cost</div>
            <div class="text-2xl font-bold">${{ formatCost(globalSummary?.total_cost_usd ?? 0) }}</div>
          </div>
          <div class="rounded-xl border bg-card p-4 space-y-1">
            <div class="text-[10px] text-muted-foreground uppercase tracking-wider">LLM Calls</div>
            <div class="text-2xl font-bold">{{ globalSummary?.total_calls ?? 0 }}</div>
          </div>
          <div class="rounded-xl border bg-card p-4 space-y-1">
            <div class="text-[10px] text-muted-foreground uppercase tracking-wider">Total Tokens</div>
            <div class="text-2xl font-bold">{{ formatTokensShort((globalSummary?.total_input_tokens ?? 0) + (globalSummary?.total_output_tokens ?? 0)) }}</div>
          </div>
          <div class="rounded-xl border bg-card p-4 space-y-1">
            <div class="text-[10px] text-muted-foreground uppercase tracking-wider">Sessions</div>
            <div class="text-2xl font-bold">{{ globalSummary?.session_count ?? 0 }}</div>
          </div>
        </div>

        <!-- Cost Over Time -->
        <div class="rounded-xl border bg-card p-4">
          <div class="text-xs font-medium mb-3">Cost Over Time</div>
          <div v-if="timeSeries.length" class="flex items-end gap-px h-40">
            <div
              v-for="(bucket, i) in timeSeries"
              :key="i"
              class="flex-1 flex flex-col items-center gap-1 group relative"
            >
              <div
                class="w-full rounded-t bg-primary/80 hover:bg-primary transition-colors cursor-default min-h-[2px]"
                :style="{ height: `${barHeight(bucket.cost_usd)}%` }"
              />
              <span class="text-[9px] text-muted-foreground truncate max-w-full">{{ bucket.label }}</span>
              <!-- Tooltip -->
              <div class="absolute bottom-full mb-2 hidden group-hover:block z-10 rounded-lg border bg-popover px-2.5 py-1.5 text-[10px] shadow-md whitespace-nowrap">
                <div class="font-medium">${{ formatCost(bucket.cost_usd) }}</div>
                <div class="text-muted-foreground">{{ bucket.calls }} calls · {{ formatTokensShort(bucket.input_tokens + bucket.output_tokens) }} tok</div>
              </div>
            </div>
          </div>
          <div v-else class="h-40 flex items-center justify-center text-xs text-muted-foreground">
            No data yet — run a workflow to see cost trends
          </div>
        </div>

        <!-- Stage Breakdown -->
        <div class="grid grid-cols-2 gap-4">
          <!-- Cost per Stage -->
          <div class="rounded-xl border bg-card p-4">
            <div class="text-xs font-medium mb-3">Cost by Stage</div>
            <div v-if="stageTotals.length" class="space-y-2">
              <div v-for="s in filteredStageTotals" :key="s.stage" class="space-y-1">
                <div class="flex items-center justify-between text-xs">
                  <div class="flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full" :class="stageColor(s.stage)" />
                    <span class="capitalize">{{ formatStage(s.stage) }}</span>
                  </div>
                  <span class="font-medium">${{ formatCost(s.cost_usd) }}</span>
                </div>
                <div class="h-1.5 rounded-full bg-accent overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="stageColor(s.stage)"
                    :style="{ width: `${stagePct(s.cost_usd)}%` }"
                  />
                </div>
              </div>
            </div>
            <div v-else class="py-6 text-center text-xs text-muted-foreground">No stage data</div>
          </div>

          <!-- Performance per Stage -->
          <div class="rounded-xl border bg-card p-4">
            <div class="text-xs font-medium mb-3">Performance by Stage</div>
            <div v-if="stageTotals.length" class="space-y-1.5">
              <div class="grid grid-cols-4 gap-2 text-[10px] text-muted-foreground uppercase tracking-wider pb-1 border-b">
                <span>Stage</span>
                <span class="text-right">Calls</span>
                <span class="text-right">Avg Latency</span>
                <span class="text-right">Tokens</span>
              </div>
              <div v-for="s in filteredStageTotals" :key="s.stage" class="grid grid-cols-4 gap-2 text-xs py-1">
                <div class="flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full" :class="stageColor(s.stage)" />
                  <span class="capitalize truncate">{{ formatStage(s.stage) }}</span>
                </div>
                <span class="text-right text-muted-foreground">{{ s.calls }}</span>
                <span class="text-right" :class="latencyColor(s.avg_duration_ms)">{{ formatDuration(s.avg_duration_ms) }}</span>
                <span class="text-right text-muted-foreground">{{ formatTokensShort(s.input_tokens + s.output_tokens) }}</span>
              </div>
            </div>
            <div v-else class="py-6 text-center text-xs text-muted-foreground">No data</div>
          </div>
        </div>

        <!-- Recent Calls Table -->
        <div class="rounded-xl border bg-card p-4">
          <div class="text-xs font-medium mb-3">Recent LLM Calls</div>
          <div v-if="recentCalls.length" class="space-y-0.5 max-h-64 overflow-y-auto">
            <div class="grid grid-cols-6 gap-2 text-[10px] text-muted-foreground uppercase tracking-wider pb-1 border-b sticky top-0 bg-card">
              <span>Time</span>
              <span>Stage</span>
              <span>Model</span>
              <span class="text-right">Tokens</span>
              <span class="text-right">Latency</span>
              <span class="text-right">Cost</span>
            </div>
            <div
              v-for="(call, i) in [...filteredCalls].reverse()"
              :key="i"
              class="grid grid-cols-6 gap-2 text-xs py-1 hover:bg-accent/20 rounded transition-colors"
            >
              <span class="text-muted-foreground">{{ formatTime(call.timestamp) }}</span>
              <span class="capitalize">{{ formatStage(call.stage) }}</span>
              <span class="text-muted-foreground truncate">{{ call.model || '—' }}</span>
              <span class="text-right">{{ (call.input_tokens + call.output_tokens).toLocaleString() }}</span>
              <span class="text-right" :class="latencyColor(call.duration_ms)">{{ formatDuration(call.duration_ms) }}</span>
              <span class="text-right font-medium" :class="costSeverity(call.cost_usd)">${{ formatCost(call.cost_usd) }}</span>
            </div>
          </div>
          <div v-else class="py-6 text-center text-xs text-muted-foreground">No calls recorded</div>
        </div>

        <!-- LLM Cache Stats -->
        <div class="rounded-xl border bg-card p-4">
          <div class="flex items-center justify-between mb-3">
            <div>
              <div class="text-xs font-medium">Response Cache</div>
              <div class="text-[10px] text-muted-foreground">Identical prompts served from cache to save cost</div>
            </div>
            <button
              class="flex items-center gap-1 rounded-lg border px-2.5 py-1 text-[10px] hover:bg-accent transition-colors"
              @click="clearCache"
            >
              <Trash2 class="h-3 w-3" />
              Clear
            </button>
          </div>
          <div v-if="cacheStats" class="grid grid-cols-4 gap-3">
            <div class="rounded-lg bg-accent/50 px-2.5 py-2 text-center">
              <div class="text-[10px] text-muted-foreground uppercase tracking-wide">Entries</div>
              <div class="text-sm font-semibold">{{ cacheStats.size }} / {{ cacheStats.max_size }}</div>
            </div>
            <div class="rounded-lg bg-accent/50 px-2.5 py-2 text-center">
              <div class="text-[10px] text-muted-foreground uppercase tracking-wide">Hit Rate</div>
              <div class="text-sm font-semibold" :class="cacheStats.hit_rate > 0.3 ? 'text-emerald-400' : ''">
                {{ (cacheStats.hit_rate * 100).toFixed(1) }}%
              </div>
            </div>
            <div class="rounded-lg bg-accent/50 px-2.5 py-2 text-center">
              <div class="text-[10px] text-muted-foreground uppercase tracking-wide">Hits</div>
              <div class="text-sm font-semibold text-emerald-400">{{ cacheStats.hits }}</div>
            </div>
            <div class="rounded-lg bg-accent/50 px-2.5 py-2 text-center">
              <div class="text-[10px] text-muted-foreground uppercase tracking-wide">Misses</div>
              <div class="text-sm font-semibold">{{ cacheStats.misses }}</div>
            </div>
          </div>
          <div v-else class="py-4 text-center text-xs text-muted-foreground">Cache stats unavailable</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ArrowLeft, RefreshCw, AlertTriangle, Settings, Trash2 } from "@lucide/vue";
import { useCostTracker, type TimeBucket, type StageTotal } from "~/composables/useCostTracker";

const bucketMinutes = ref(60);
const budgetInput = ref<number | undefined>(undefined);
const sessionFilter = ref("");

const timeOptions = [
  { label: "5 min", value: 5 },
  { label: "15 min", value: 15 },
  { label: "Hourly", value: 60 },
  { label: "Daily", value: 1440 },
];

const { globalSummary, recentCalls, metrics, cacheStats, loading, refresh, setBudget, clearCache } = useCostTracker();

const sessionIds = computed(() => {
  const ids = new Set(recentCalls.value.map(c => c.session_id));
  return [...ids];
});

const filteredCalls = computed(() => {
  if (!sessionFilter.value) return recentCalls.value;
  return recentCalls.value.filter(c => c.session_id === sessionFilter.value);
});

const filteredStageTotals = computed(() => {
  if (!sessionFilter.value) return stageTotals.value;
  // Recompute from filtered calls
  const agg: Record<string, any> = {};
  for (const c of filteredCalls.value) {
    if (!agg[c.stage]) agg[c.stage] = { stage: c.stage, cost_usd: 0, input_tokens: 0, output_tokens: 0, calls: 0, avg_duration_ms: 0, _durations: [] };
    const s = agg[c.stage];
    s.cost_usd += c.cost_usd;
    s.input_tokens += c.input_tokens;
    s.output_tokens += c.output_tokens;
    s.calls++;
    s._durations.push(c.duration_ms);
  }
  return Object.values(agg).map((s: any) => {
    s.avg_duration_ms = s._durations.length ? s._durations.reduce((a: number, b: number) => a + b, 0) / s._durations.length : 0;
    delete s._durations;
    return s;
  }).sort((a: any, b: any) => b.cost_usd - a.cost_usd);
});

const timeSeries = computed<TimeBucket[]>(() => metrics.value?.time_series ?? []);
const stageTotals = computed<StageTotal[]>(() =>
  [...(metrics.value?.stage_totals ?? [])].sort((a, b) => b.cost_usd - a.cost_usd)
);

const maxCost = computed(() => Math.max(...timeSeries.value.map(b => b.cost_usd), 0.0001));
const maxStageCost = computed(() => Math.max(...stageTotals.value.map(s => s.cost_usd), 0.0001));

const budgetBarColor = computed(() => {
  const pct = metrics.value?.budget?.percent_used ?? 0;
  if (pct >= 100) return "bg-red-500";
  if (pct >= 80) return "bg-amber-500";
  return "bg-primary";
});

watch(bucketMinutes, () => refresh());

const autoRefresh = ref(false);
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null;

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value;
  if (autoRefresh.value) {
    autoRefreshTimer = setInterval(() => refresh(), 30_000);
  } else if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

function applyBudget() {
  setBudget(budgetInput.value && budgetInput.value > 0 ? budgetInput.value : null);
}

function barHeight(cost: number): number {
  return Math.max((cost / maxCost.value) * 100, 1);
}

function stagePct(cost: number): number {
  return Math.max((cost / maxStageCost.value) * 100, 2);
}

function formatCost(usd: number): string {
  if (usd < 0.001) return usd.toFixed(6);
  if (usd < 0.01) return usd.toFixed(4);
  if (usd < 1) return usd.toFixed(3);
  return usd.toFixed(2);
}

function formatTokensShort(n: number): string {
  if (n > 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n > 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function formatStage(stage: string): string {
  return stage.replace(/_/g, " ").replace("software ", "sw ").replace("codegen_", "");
}

function formatDuration(ms: number): string {
  if (ms > 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  if (ms > 1_000) return `${(ms / 1_000).toFixed(1)}s`;
  return `${ms.toFixed(0)}ms`;
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function stageColor(stage: string): string {
  const colors: Record<string, string> = {
    refiner: "bg-blue-500",
    hardware: "bg-amber-500",
    software_arch: "bg-violet-500",
    software_detailed: "bg-purple-500",
    codegen: "bg-emerald-500",
    codegen_mock: "bg-emerald-400",
    codegen_test: "bg-emerald-300",
    codegen_prod: "bg-emerald-600",
    review: "bg-cyan-500",
    fix_loop: "bg-red-400",
    chat: "bg-gray-400",
    profile_generation: "bg-indigo-400",
  };
  return colors[stage] ?? "bg-gray-400";
}

function latencyColor(ms: number): string {
  if (ms > 30_000) return "text-red-400";
  if (ms > 10_000) return "text-amber-400";
  return "text-muted-foreground";
}

function costSeverity(usd: number): string {
  if (usd > 0.05) return "text-red-400";
  if (usd > 0.01) return "text-amber-400";
  return "text-emerald-400";
}
</script>
