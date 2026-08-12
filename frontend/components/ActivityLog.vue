<template>
  <div class="rounded-xl border bg-card overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between border-b px-4 py-2.5">
      <div class="flex items-center gap-2">
        <Terminal class="h-3.5 w-3.5 text-muted-foreground" />
        <span class="text-xs font-medium">Activity Log</span>
        <span
          class="h-1.5 w-1.5 rounded-full"
          :class="connected ? 'bg-[hsl(var(--success))]' : 'bg-muted-foreground'"
        />
      </div>
      <div class="flex items-center gap-1">
        <button
          class="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          @click="clear"
          title="Clear"
        >
          <Trash2 class="h-3 w-3" />
        </button>
        <button
          class="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          @click="autoScroll = !autoScroll"
          :title="autoScroll ? 'Auto-scroll on' : 'Auto-scroll off'"
        >
          <ChevronsDown class="h-3 w-3" :class="{ 'text-primary': autoScroll }" />
        </button>
      </div>
    </div>

    <!-- Log entries -->
    <div ref="logContainer" class="h-64 overflow-y-auto bg-[hsl(260,25%,5%)] p-2 font-mono text-[11px] leading-relaxed space-y-0.5">
      <div v-if="!entries.length" class="flex items-center justify-center h-full text-white/20 text-xs">
        Waiting for activity…
      </div>
      <div
        v-for="(entry, i) in entries"
        :key="i"
        class="flex gap-2 px-1.5 py-0.5 rounded"
        :class="rowClass(entry.level)"
      >
        <span class="shrink-0 w-16 text-white/25">{{ formatTime(entry.timestamp) }}</span>
        <component :is="levelIcon(entry.level)" class="h-3 w-3 shrink-0 mt-0.5" :class="iconClass(entry.level)" />
        <div class="flex-1 min-w-0">
          <span :class="textClass(entry.level)">{{ entry.message }}</span>
          <span v-if="entry.detail" class="text-white/30 ml-1.5">{{ entry.detail }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, ref, nextTick, onMounted } from "vue";
import { Terminal, Trash2, ChevronsDown, Info, CheckCircle2, AlertTriangle, XCircle, Brain, ChevronRight } from "lucide-vue-next";
import { useActivityLog, type LogEntry } from "~/composables/useActivityLog";

const { entries, connected, connect, clear } = useActivityLog();
const logContainer = ref<HTMLElement | null>(null);
const autoScroll = ref(true);

onMounted(() => connect());

watch(() => entries.value.length, () => {
  if (!autoScroll.value) return;
  nextTick(() => {
    logContainer.value?.scrollTo({ top: logContainer.value.scrollHeight, behavior: "smooth" });
  });
});

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function levelIcon(level: string) {
  switch (level) {
    case "step": return ChevronRight;
    case "success": return CheckCircle2;
    case "warn": return AlertTriangle;
    case "error": return XCircle;
    case "ai": return Brain;
    default: return Info;
  }
}

function iconClass(level: string): string {
  switch (level) {
    case "step": return "text-violet-400";
    case "success": return "text-emerald-400";
    case "warn": return "text-amber-400";
    case "error": return "text-red-400";
    case "ai": return "text-sky-400";
    default: return "text-white/40";
  }
}

function textClass(level: string): string {
  switch (level) {
    case "step": return "text-violet-300 font-medium";
    case "success": return "text-emerald-300";
    case "warn": return "text-amber-300";
    case "error": return "text-red-300";
    case "ai": return "text-sky-300";
    default: return "text-white/60";
  }
}

function rowClass(level: string): string {
  switch (level) {
    case "error": return "bg-red-500/5";
    case "ai": return "bg-sky-500/5";
    case "step": return "bg-violet-500/5";
    default: return "";
  }
}
</script>
