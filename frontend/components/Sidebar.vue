<template>
  <aside class="flex w-64 flex-col border-r bg-card/30 backdrop-blur-sm">
    <div class="flex h-14 items-center justify-between border-b px-4">
      <h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sessions</h2>
      <span v-if="sessions.length" class="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-[10px] font-bold">{{ sessions.length }}</span>
    </div>

    <div class="flex-1 overflow-y-auto p-3 space-y-1.5">
      <button
        class="flex w-full items-center gap-2 rounded-lg border border-dashed border-primary/30 p-2.5 text-xs text-primary hover:bg-primary/5 hover:border-primary/50 transition-all duration-200 active:scale-[0.98]"
        @click="$emit('new-session')"
      >
        <Plus class="h-3.5 w-3.5" />
        New Session
      </button>

      <!-- Search -->
      <input
        v-if="sessions.length > 3"
        v-model="filterText"
        class="w-full rounded-lg border bg-background px-2.5 py-1.5 text-[10px] focus:outline-none focus:ring-1 focus:ring-ring"
        placeholder="Filter sessions…"
      />

      <!-- Session List -->
      <TransitionGroup name="stagger">
        <div
          v-for="session in filteredSessions"
          :key="session.session_id"
          class="rounded-lg bg-secondary/50 p-2.5 text-xs border transition-all duration-200 cursor-pointer hover:bg-accent group"
          :class="currentSessionId === session.session_id ? 'border-primary/40 bg-primary/5' : 'border-transparent hover:border-primary/20'"
          @click="$emit('select-session', session.session_id)"
        >
          <div class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full shrink-0" :class="stageColor(session.stage)" />
            <div class="flex-1 min-w-0">
              <div class="font-mono text-[10px] truncate">{{ session.session_id.slice(0, 8) }}</div>
              <div class="text-[9px] text-muted-foreground truncate">{{ session.board_name || 'No board' }} · {{ formatStage(session.stage) }}</div>
            </div>
            <button
              class="h-4 w-4 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-destructive/20 hover:text-destructive transition-all"
              title="Delete session"
              @click.stop="$emit('delete-session', session.session_id)"
            >
              <Trash2 class="h-2.5 w-2.5" />
            </button>
          </div>
          <div class="text-[9px] text-muted-foreground mt-1">{{ formatDate(session.created_at) }}</div>
        </div>
      </TransitionGroup>

      <p v-if="sessions.length && !filteredSessions.length" class="text-[10px] text-muted-foreground text-center py-2">No matches</p>
    </div>

    <!-- Board Selector -->
    <div class="border-t p-3 space-y-2">
      <label class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
        <CircuitBoard class="h-3 w-3" /> Target Board
      </label>
      <div class="relative">
        <button
          type="button"
          class="flex w-full items-center justify-between rounded-lg border bg-background px-3 py-2 text-xs transition-all duration-200 hover:border-primary/40 focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
          @click="dropdownOpen = !dropdownOpen"
        >
          <span class="flex items-center gap-1.5">
            <Cpu class="h-3 w-3 text-primary/70" />
            {{ activeBoard || 'Select board…' }}
          </span>
          <ChevronDown class="h-3 w-3 text-muted-foreground transition-transform duration-200" :class="{ 'rotate-180': dropdownOpen }" />
        </button>
        <Transition name="fade-slide">
          <div v-if="dropdownOpen" class="absolute bottom-full left-0 right-0 mb-1 rounded-lg border bg-card shadow-lg z-20 overflow-hidden">
            <div class="max-h-40 overflow-y-auto py-1">
              <button
                v-for="board in boards"
                :key="board"
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-xs transition-colors hover:bg-accent"
                :class="{ 'bg-primary/5 text-primary font-medium': board === activeBoard }"
                @click="selectBoard(board)"
              >
                <span class="h-1.5 w-1.5 rounded-full" :class="board === activeBoard ? 'bg-primary' : 'bg-border'" />
                {{ board }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <!-- Settings & Metrics links -->
    <div class="border-t p-3 space-y-1">
      <NuxtLink
        to="/metrics"
        class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-all duration-200"
      >
        <BarChart3 class="h-3.5 w-3.5" />
        Metrics & Cost
      </NuxtLink>
      <NuxtLink
        to="/settings"
        class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-all duration-200"
      >
        <Settings class="h-3.5 w-3.5" />
        SDK & Settings
      </NuxtLink>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Plus, ChevronRight, ChevronDown, CircuitBoard, Cpu, Settings, BarChart3, Trash2 } from "@lucide/vue";
import type { SessionMeta } from "~/composables/useWorkflow";

const props = defineProps<{
  boards: string[];
  activeBoard: string;
  sessions: SessionMeta[];
  currentSessionId?: string;
}>();

const emit = defineEmits<{
  "select-board": [board: string];
  "select-session": [sessionId: string];
  "delete-session": [sessionId: string];
  "new-session": [];
}>();

const dropdownOpen = ref(false);
const filterText = ref("");

const filteredSessions = computed(() => {
  if (!filterText.value) return props.sessions;
  const q = filterText.value.toLowerCase();
  return props.sessions.filter(s =>
    s.session_id.includes(q) || s.board_name?.toLowerCase().includes(q) || s.stage?.includes(q)
  );
});

function selectBoard(board: string) {
  emit("select-board", board);
  dropdownOpen.value = false;
}

function stageColor(stage: string): string {
  if (stage === "complete" || stage === "build") return "bg-green-400";
  if (stage === "review" || stage === "codegen") return "bg-amber-400";
  return "bg-sky-400";
}

function formatStage(stage: string): string {
  if (!stage) return "init";
  return stage.replace(/_/g, " ");
}

function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `${diffD}d ago`;
  return d.toLocaleDateString();
}
</script>
