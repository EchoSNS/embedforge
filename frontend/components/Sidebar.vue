<template>
  <aside class="flex w-60 flex-col border-r bg-card/30 backdrop-blur-sm">
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

      <TransitionGroup name="stagger">
        <div
          v-for="session in sessions"
          :key="session"
          class="rounded-lg bg-secondary/50 p-2.5 text-xs border border-transparent hover:border-primary/20 transition-all duration-200 cursor-pointer hover:bg-accent group"
          @click="$emit('select-session', session)"
        >
          <div class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-[hsl(var(--success))]" />
            <span class="font-mono flex-1">{{ session.slice(0, 8) }}</span>
            <ChevronRight class="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
      </TransitionGroup>
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
import { ref } from "vue";
import { Plus, ChevronRight, ChevronDown, CircuitBoard, Cpu, Settings, BarChart3 } from "@lucide/vue";

defineProps<{
  boards: string[];
  activeBoard: string;
  sessions: string[];
}>();

const emit = defineEmits<{
  "select-board": [board: string];
  "select-session": [sessionId: string];
  "new-session": [];
}>();

const dropdownOpen = ref(false);

function selectBoard(board: string) {
  emit("select-board", board);
  dropdownOpen.value = false;
}
</script>
