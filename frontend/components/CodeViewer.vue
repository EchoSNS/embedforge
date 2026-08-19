<template>
  <div class="flex h-full flex-col bg-card">
    <!-- File Tabs -->
    <div class="flex border-b overflow-x-auto bg-secondary/30">
      <button
        v-for="name in fileNames"
        :key="name"
        class="relative whitespace-nowrap px-4 py-2.5 text-xs font-medium transition-all duration-200 flex items-center gap-1.5"
        :class="{
          'text-foreground': activeFile === name,
          'text-muted-foreground hover:text-foreground hover:bg-accent/50': activeFile !== name,
        }"
        @click="activeFile = name"
      >
        <FileCode class="h-3 w-3" />
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
        <pre class="flex-1 p-4 font-mono text-xs leading-relaxed overflow-x-auto"><code v-html="highlightedCode" /></pre>
      </div>
    </div>

    <!-- Actions -->
    <div class="border-t p-3 flex gap-2">
      <button
        class="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-primary py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-all duration-200 active:scale-[0.98]"
        @click="downloadAll"
      >
        <Download class="h-3.5 w-3.5" />
        Download All
      </button>
      <button
        class="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm hover:bg-accent transition-all duration-200 active:scale-[0.98]"
        @click="copyFile"
      >
        <component :is="copied ? CheckIcon : ClipboardCopy" class="h-3.5 w-3.5" />
        {{ copied ? 'Copied' : 'Copy' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { FileCode, Download, ClipboardCopy, Check as CheckIcon } from "@lucide/vue";
import { useRuntimeConfig } from "#app";

const props = defineProps<{
  files: Record<string, string>;
  sessionId?: string;
}>();

const config = useRuntimeConfig();
const fileNames = computed(() => Object.keys(props.files));
const activeFile = ref(fileNames.value[0] || "");
const copied = ref(false);

watch(fileNames, (names) => {
  if (!names.includes(activeFile.value) && names.length) {
    activeFile.value = names[0];
  }
});

const lineCount = computed(() => {
  const content = props.files[activeFile.value] || "";
  return content.split("\n").length;
});

const highlightedCode = computed(() => {
  const code = props.files[activeFile.value] || "";
  return highlightC(code);
});

function highlightC(code: string): string {
  const escaped = code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const lines = escaped.split("\n");
  return lines.map(line => {
    const tokens: string[] = [];
    const ph = (cls: string, text: string) => {
      const i = tokens.length;
      tokens.push(`<span class="${cls}">${text}</span>`);
      return `\uE000${i}\uE001`;
    };
    let r = line;
    r = r.replace(/(\/\/.*)/g, (_, m) => ph("text-white/30 italic", m));
    r = r.replace(/(#\w+)/g, (_, m) => ph("text-violet-400", m));
    r = r.replace(/("(?:[^"\\]|\\.)*")/g, (_, m) => ph("text-green-400", m));
    r = r.replace(/(&lt;[\w./]+&gt;)/g, (_, m) => ph("text-green-400", m));
    r = r.replace(/\b(HAL_\w+|__HAL_\w+)\b/g, (_, m) => ph("text-amber-400", m));
    r = r.replace(/\b(void|int|uint32_t|uint16_t|uint8_t|int32_t|int16_t|int8_t|size_t|bool|char|float|double|struct|enum|typedef|static|const|volatile|extern|return|if|else|while|for|switch|case|break|default|true|false|NULL)\b/g, (_, m) => ph("text-sky-400", m));
    r = r.replace(/\b(0[xX][0-9a-fA-F]+[UuLl]*|[0-9]+[UuLl]*)\b/g, (_, m) => ph("text-orange-300", m));
    // Restore tokens and strip any orphaned placeholders
    r = r.replace(/\uE000(\d+)\uE001/g, (_, idx) => tokens[parseInt(idx)] || "");
    r = r.replace(/[\uE000\uE001]/g, "");
    return r;
  }).join("\n");
}

function copyFile() {
  const content = props.files[activeFile.value] || "";
  navigator.clipboard.writeText(content);
  copied.value = true;
  setTimeout(() => { copied.value = false; }, 2000);
}

function downloadAll() {
  if (props.sessionId) {
    window.open(`${config.public.apiBase}/api/workflow/${props.sessionId}/download`);
  }
}
</script>
