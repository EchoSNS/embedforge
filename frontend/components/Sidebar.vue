<template>
  <aside class="flex w-64 flex-col border-r bg-card/50 backdrop-blur-sm">
    <div class="flex h-14 items-center border-b px-4">
      <h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sessions</h2>
    </div>

    <div class="flex-1 overflow-y-auto p-3 space-y-2">
      <button
        class="flex w-full items-center gap-2 rounded-xl border border-dashed border-primary/30 p-3 text-sm text-primary hover:bg-primary/5 hover:border-primary/60 transition-all duration-200 active:scale-[0.98]"
        @click="$emit('new-session')"
      >
        <span class="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-xs">+</span>
        New Session
      </button>

      <TransitionGroup name="stagger">
        <div
          v-for="session in sessions"
          :key="session"
          class="rounded-xl bg-secondary/50 p-3 text-sm border border-transparent hover:border-primary/20 transition-all duration-200 cursor-pointer hover:bg-secondary"
        >
          <div class="flex items-center gap-2">
            <span class="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <span class="font-mono text-xs">{{ session.slice(0, 8) }}...</span>
          </div>
        </div>
      </TransitionGroup>
    </div>

    <!-- Board Selector -->
    <div class="border-t p-4 space-y-2">
      <label class="text-xs font-medium uppercase tracking-wider text-muted-foreground">Target Board</label>
      <select
        :value="activeBoard"
        class="w-full rounded-lg border bg-background p-2.5 text-sm transition-all duration-200 focus:ring-2 focus:ring-ring focus:outline-none appearance-none cursor-pointer"
        @change="$emit('select-board', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="board in boards" :key="board" :value="board">
          {{ board }}
        </option>
      </select>
    </div>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  boards: string[];
  activeBoard: string;
  sessions: string[];
}>();

defineEmits<{
  "select-board": [board: string];
  "new-session": [];
}>();
</script>
