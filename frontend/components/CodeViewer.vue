<template>
  <div class="flex h-full flex-col">
    <!-- File Tabs -->
    <div class="flex border-b overflow-x-auto">
      <button
        v-for="name in fileNames"
        :key="name"
        class="whitespace-nowrap border-r px-4 py-2 text-xs font-medium hover:bg-accent"
        :class="{ 'bg-accent text-foreground': activeFile === name, 'text-muted-foreground': activeFile !== name }"
        @click="activeFile = name"
      >
        {{ name }}
      </button>
    </div>

    <!-- Code Content -->
    <div class="flex-1 overflow-auto bg-[hsl(240,10%,5%)] p-4">
      <pre class="font-mono text-xs leading-relaxed text-green-400"><code>{{ files[activeFile] || '' }}</code></pre>
    </div>

    <!-- Download Button -->
    <div class="border-t p-3">
      <button
        class="w-full rounded-md bg-primary py-2 text-sm text-primary-foreground hover:opacity-90"
        @click="downloadAll"
      >
        ⬇️ Download All Files
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";

const props = defineProps<{
  files: Record<string, string>;
}>();

const fileNames = computed(() => Object.keys(props.files));
const activeFile = ref(fileNames.value[0] || "");

function downloadAll() {
  // Trigger zip download from backend
  const sessionId = new URLSearchParams(window.location.search).get("session");
  if (sessionId) {
    window.open(`http://localhost:8000/api/workflow/${sessionId}/download`);
  }
}
</script>
