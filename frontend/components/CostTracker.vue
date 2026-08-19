<template>
  <div class="rounded-xl border bg-card overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between border-b px-4 py-2.5">
      <div class="flex items-center gap-2">
        <DollarSign class="h-3.5 w-3.5 text-muted-foreground" />
        <span class="text-xs font-medium">Cost Tracker</span>
      </div>
      <button
        class="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        @click="refresh"
        title="Refresh"
      >
        <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': loading }" />
      </button>
    </div>

    <!-- Summary Cards -->
    <div class="p-3 space-y-3">
      <!-- Global Stats -->
      <div class="grid grid-cols-3 gap-2">
        <div class="rounded-lg bg-accent/50 px-2.5 py-2 text-center">
          <div class="text-[10px] text-muted-foreground uppercase tracking-wide">Cost</div>
          <div class="text-sm font-semibold text-foreground">
            ${{ formatCost(globalSummary?.total_cost_usd ?? 0) }}
          </div>
        </div>
        <div class="rounded-lg bg-accent/50 px-2.5 py-2 text-center">
          <div class="text-[10px] text-muted-foreground uppercase tracking-wide">Calls</div>
          <div class="text-sm font-semibold text-foreground">
            {{ globalSummary?.total_calls ?? 0 }}
          </div>
        </div>
        <div class="rounded-lg bg-accent/50 px-2.5 py-2 text-center">
          <div class="text-[10px] text-muted-foreground uppercase tracking-wide">Tokens</div>
          <div class="text-sm font-semibold text-foreground">
            {{ formatTokens(globalSummary?.total_input_tokens ?? 0, globalSummary?.total_output_tokens ?? 0) }}
          </div>
        </div>
      </div>

      <!-- Session Breakdown -->
      <div v-if="sessionCost && sessionCost.call_count > 0">
        <div class="text-[10px] text-muted-foreground uppercase tracking-wide mb-1.5">
          Session Breakdown
        </div>
        <div class="space-y-1">
          <div
            v-for="(data, stage) in sessionCost.by_stage"
            :key="stage"
            class="flex items-center justify-between rounded px-2 py-1 bg-accent/30 text-xs"
          >
            <div class="flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full" :class="stageColor(stage as string)" />
              <span class="text-foreground capitalize">{{ formatStage(stage as string) }}</span>
            </div>
            <div class="flex items-center gap-3 text-muted-foreground">
              <span>{{ (data.input_tokens + data.output_tokens).toLocaleString() }} tok</span>
              <span class="font-medium text-foreground">${{ formatCost(data.cost_usd) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Calls -->
      <div v-if="recentCalls.length">
        <div class="text-[10px] text-muted-foreground uppercase tracking-wide mb-1.5">
          Recent Calls
        </div>
        <div class="max-h-32 overflow-y-auto space-y-0.5">
          <div
            v-for="(call, i) in recentCalls.slice().reverse()"
            :key="i"
            class="flex items-center justify-between rounded px-2 py-1 text-[11px] hover:bg-accent/20 transition-colors"
          >
            <div class="flex items-center gap-1.5 min-w-0">
              <span class="text-muted-foreground capitalize truncate">{{ formatStage(call.stage) }}</span>
            </div>
            <div class="flex items-center gap-2 text-muted-foreground shrink-0">
              <span>{{ call.duration_ms.toFixed(0) }}ms</span>
              <span>{{ (call.input_tokens + call.output_tokens).toLocaleString() }}</span>
              <span class="font-medium" :class="costSeverity(call.cost_usd)">
                ${{ formatCost(call.cost_usd) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="!globalSummary || globalSummary.total_calls === 0" class="text-center py-4 text-xs text-muted-foreground">
        No LLM calls recorded yet
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { DollarSign, RefreshCw } from "@lucide/vue";
import { useCostTracker } from "~/composables/useCostTracker";

const props = defineProps<{
  sessionId?: string;
}>();

const { globalSummary, sessionCost, recentCalls, loading, refresh } = useCostTracker(props.sessionId);

function formatCost(usd: number): string {
  if (usd < 0.001) return usd.toFixed(6);
  if (usd < 0.01) return usd.toFixed(4);
  if (usd < 1) return usd.toFixed(3);
  return usd.toFixed(2);
}

function formatTokens(input: number, output: number): string {
  const total = input + output;
  if (total > 1_000_000) return `${(total / 1_000_000).toFixed(1)}M`;
  if (total > 1_000) return `${(total / 1_000).toFixed(1)}K`;
  return total.toString();
}

function formatStage(stage: string): string {
  return stage.replace(/_/g, " ").replace("software ", "sw ");
}

function stageColor(stage: string): string {
  const colors: Record<string, string> = {
    refiner: "bg-blue-500",
    hardware: "bg-amber-500",
    software_arch: "bg-violet-500",
    software_detailed: "bg-purple-500",
    codegen: "bg-emerald-500",
    review: "bg-cyan-500",
    fix_loop: "bg-red-400",
    chat: "bg-gray-400",
  };
  return colors[stage] ?? "bg-gray-400";
}

function costSeverity(usd: number): string {
  if (usd > 0.05) return "text-red-400";
  if (usd > 0.01) return "text-amber-400";
  return "text-emerald-400";
}
</script>
