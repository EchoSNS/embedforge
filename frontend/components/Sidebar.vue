<template>
  <aside class="flex w-64 flex-col border-r bg-card">
    <div class="flex h-14 items-center border-b px-4">
      <h2 class="text-sm font-semibold text-muted-foreground">Sessions</h2>
    </div>

    <div class="flex-1 overflow-y-auto p-3 space-y-2">
      <button
        class="flex w-full items-center gap-2 rounded-lg border border-dashed p-3 text-sm hover:bg-accent"
        @click="$emit('new-session')"
      >
        <span>+</span> New Session
      </button>

      <div
        v-for="session in sessions"
        :key="session"
        class="rounded-lg bg-secondary p-3 text-sm"
      >
        {{ session.slice(0, 8) }}...
      </div>
    </div>

    <!-- Board Selector -->
    <div class="border-t p-4 space-y-2">
      <label class="text-xs font-medium text-muted-foreground">Target Board</label>
      <select
        :value="activeBoard"
        class="w-full rounded-md border bg-background p-2 text-sm"
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
