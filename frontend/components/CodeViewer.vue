<template>
  <div class="flex h-full flex-col bg-card">
    <!-- File Tabs -->
    <div class="flex border-b overflow-x-auto bg-secondary/30">
      <button
        v-for="name in fileNames"
        :key="name"
        class="relative whitespace-nowrap px-4 py-2.5 text-xs font-medium transition-all duration-200"
        :class="{
          'text-foreground': activeFile === name,
          'text-muted-foreground hover:text-foreground hover:bg-accent/50': activeFile !== name,
        }"
        @click="activeFile = name"
      >
        <span class="relative z-10">{{ name }}</span>
        <span
          v-if="activeFile === name"
          class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full"
        />
      </button>
    </div>

    <!-- Code Content with line numbers -->
    <div class="flex-1 overflow-auto bg-[hsl(222,47%,4%)] p-0">
      <div class="flex">
        <div class="select-none border-r border-white/5 px-3 py-4 text-right font-mono text-xs leading-relaxed text-white/20">
          <div v-for="n in lineCount" :key="n">{{ n }}</div>
        </div>
        <pre class="flex-1 p-4 font-mono text-xs leading-relaxed text-emerald-400/90 overflow-x-auto"><code>{{ files[activeFile] || '' }}</code></pre>
      </div>
    </div>

    <!-- Actions -->
    <div class="border-t p-3 flex gap-2">
      <button
        class="flex-1 rounded-lg bg-primary py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-all duration-200 active:scale-[0.98]"
        @click="downloadAll"
      >
        ⬇️ Download All
      </button>
      <button
        class="rounded-lg border px-4 py-2 text-sm hover:bg-accent transition-all duration-200 active:scale-[0.98]"
        @click="copyFile"
      >
        📋 Copy
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRuntimeConfig } from "#app";

const props = defineProps<{
  files: Record<string, string>;
}>();

const config = useRuntimeConfig();
const fileNames = computed(() => Object.keys(props.files));
const activeFile = ref(fileNames.value[0] || "");

watch(fileNames, (names) => {
  if (!names.includes(activeFile.value) && names.length) {
    activeFile.value = names[0];
  }
});

const lineCount = computed(() => {
  const content = props.files[activeFile.value] || "";
  return content.split("\n").length;
});

function copyFile() {
  const content = props.files[activeFile.value] || "";
  navigator.clipboard.writeText(content);
}

function downloadAll() {
  const sessionId = new URLSearchParams(window.location.search).get("session");
  if (sessionId) {
    window.open(`${config.public.apiBase}/api/workflow/${sessionId}/download`);
  }
}
</script>
