<template>
  <div class="h-full flex flex-col bg-card">
    <div class="flex items-center justify-between border-b px-4 py-2.5">
      <span class="text-xs font-medium">Architecture Graph</span>
      <div class="flex gap-1">
        <button
          class="rounded px-2 py-1 text-[10px] transition-colors"
          :class="layout === 'TB' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent'"
          @click="layout = 'TB'; layoutGraph()"
        >Vertical</button>
        <button
          class="rounded px-2 py-1 text-[10px] transition-colors"
          :class="layout === 'LR' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent'"
          @click="layout = 'LR'; layoutGraph()"
        >Horizontal</button>
      </div>
    </div>

    <!-- Legend -->
    <div class="flex items-center gap-3 px-4 py-1.5 border-b text-[9px] text-muted-foreground">
      <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-green-400" />Init</span>
      <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-red-400" />ISR</span>
      <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-amber-400" />Callback</span>
      <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-sky-400" />Runtime</span>
      <span class="flex items-center gap-1"><span class="h-2 w-2 rounded border border-dashed border-muted-foreground" />SDK API</span>
    </div>

    <div class="flex-1 relative">
      <VueFlow
        v-if="nodes.length"
        :nodes="nodes"
        :edges="edges"
        :default-viewport="{ zoom: 0.75, x: 30, y: 30 }"
        fit-view-on-init
        class="h-full"
      >
        <template #node-function="{ data }">
          <div
            class="rounded-lg border px-3 py-2 shadow-sm text-[10px] min-w-[130px] cursor-pointer transition-all hover:shadow-md hover:scale-105"
            :class="nodeStyle(data)"
            @click="selectNode(data)"
            @dblclick="$emit('navigate', data.file, data.name)"
          >
            <div class="font-medium truncate">{{ data.name }}</div>
            <div class="text-muted-foreground truncate mt-0.5">{{ data.file }}</div>
            <div v-if="data.callCount" class="text-[8px] text-muted-foreground mt-0.5">→ {{ data.callCount }} calls</div>
          </div>
        </template>
        <template #node-external="{ data }">
          <div class="rounded border border-dashed border-muted-foreground/50 px-2 py-1 text-[9px] text-muted-foreground bg-muted/30">
            {{ data.name }}
          </div>
        </template>
        <MiniMap position="bottom-right" />
        <Controls position="bottom-left" />
      </VueFlow>
      <div v-else class="h-full flex items-center justify-center text-xs text-muted-foreground">
        No function data — complete the Detailed Design stage first
      </div>

      <!-- Detail Panel -->
      <Transition name="fade-slide">
        <div v-if="selectedNode" class="absolute top-3 right-3 w-56 rounded-lg border bg-card shadow-lg p-3 space-y-2 z-10">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium">{{ selectedNode.name }}</span>
            <button class="text-muted-foreground hover:text-foreground" @click="selectedNode = null">✕</button>
          </div>
          <p v-if="selectedNode.signature" class="text-[9px] font-mono text-muted-foreground break-all">{{ selectedNode.signature }}</p>
          <p v-if="selectedNode.description" class="text-[10px] text-muted-foreground">{{ selectedNode.description }}</p>
          <div v-if="selectedNode.calls?.length" class="text-[9px]">
            <span class="text-muted-foreground">Calls:</span>
            <span v-for="c in selectedNode.calls" :key="c" class="ml-1 inline-block rounded bg-muted px-1">{{ c }}</span>
          </div>
          <p class="text-[9px] text-muted-foreground">File: {{ selectedNode.file }}</p>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { VueFlow } from "@vue-flow/core";
import { MiniMap } from "@vue-flow/minimap";
import { Controls } from "@vue-flow/controls";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import "@vue-flow/minimap/dist/style.css";
import "@vue-flow/controls/dist/style.css";

interface FuncDef {
  name: string;
  signature?: string;
  description?: string;
  calls?: string[];
  file?: string;
}

const props = defineProps<{
  functions: FuncDef[];
}>();

defineEmits<{ navigate: [file: string, func: string] }>();

const layout = ref<"TB" | "LR">("TB");
const nodes = ref<any[]>([]);
const edges = ref<any[]>([]);
const selectedNode = ref<FuncDef | null>(null);

function selectNode(data: any) {
  const func = props.functions.find(f => f.name === data.name);
  selectedNode.value = func || { name: data.name, file: data.file };
}

const FILE_COLORS: Record<string, string> = {
  "main.c": "border-sky-400/50 bg-sky-50 dark:bg-sky-950/30",
  "stm32f4xx_hal_msp.c": "border-violet-400/50 bg-violet-50 dark:bg-violet-950/30",
  "stm32f4xx_it.c": "border-red-400/50 bg-red-50 dark:bg-red-950/30",
};

function nodeStyle(data: any): string {
  if (data.isIsr) return "border-red-400/50 bg-red-50 dark:bg-red-950/30";
  if (data.isCallback) return "border-amber-400/50 bg-amber-50 dark:bg-amber-950/30";
  if (data.isInit) return "border-green-400/50 bg-green-50 dark:bg-green-950/30";
  for (const [file, cls] of Object.entries(FILE_COLORS)) {
    if (data.file?.includes(file)) return cls;
  }
  return "border-border bg-card";
}

function layoutGraph() {
  const funcs = props.functions || [];
  if (!funcs.length) {
    nodes.value = [];
    edges.value = [];
    return;
  }

  const funcNames = new Set(funcs.map(f => f.name));
  const spacing = layout.value === "TB" ? { x: 200, y: 120 } : { x: 250, y: 80 };
  const externalAdded = new Set<string>();
  let extCol = 0;
  let extRow = 0;

  // Group by file for positioning
  const fileGroups: Record<string, typeof funcs> = {};
  for (const f of funcs) {
    const file = f.file || "unknown";
    if (!fileGroups[file]) fileGroups[file] = [];
    fileGroups[file].push(f);
  }

  const newNodes: any[] = [];
  const newEdges: any[] = [];
  let col = 0;

  for (const [file, fileFuncs] of Object.entries(fileGroups)) {
    let row = 0;
    for (const func of fileFuncs) {
      const isIsr = func.name.includes("IRQHandler") || func.name.includes("Handler");
      const isCallback = func.name.includes("Callback") || func.name.includes("Cplt");
      const isInit = func.name.includes("Init") || func.name.includes("Config") || func.name === "main";

      const x = layout.value === "TB" ? col * spacing.x : row * spacing.x;
      const y = layout.value === "TB" ? row * spacing.y : col * spacing.y;

      newNodes.push({
        id: func.name,
        type: "function",
        position: { x, y },
        data: { name: func.name, file: file.split("/").pop(), isIsr, isCallback, isInit, callCount: func.calls?.length || 0 },
      });

      // Create edges for calls
      for (const called of func.calls || []) {
        if (funcNames.has(called)) {
          newEdges.push({
            id: `${func.name}->${called}`,
            source: func.name,
            target: called,
            animated: isIsr || isCallback,
            style: { stroke: isCallback ? "#f59e0b" : "#6366f1" },
            label: called,
          });
        } else if (!externalAdded.has(called)) {
          // Add external SDK API as a ghost node
          externalAdded.add(called);
          newNodes.push({
            id: `ext_${called}`,
            type: "external",
            position: { x: extCol * spacing.x, y: extRow * spacing.y },
            data: { name: called },
          });
          extRow++;
          newEdges.push({
            id: `${func.name}->ext_${called}`,
            source: func.name,
            target: `ext_${called}`,
            style: { stroke: "#64748b", strokeDasharray: "4 2" },
          });
        } else {
          // Edge to existing external node
          newEdges.push({
            id: `${func.name}->ext_${called}`,
            source: func.name,
            target: `ext_${called}`,
            style: { stroke: "#64748b", strokeDasharray: "4 2" },
          });
        }
      }
      row++;
    }
    col++;
  }

  // Position external nodes in a separate column
  extCol = col;

  nodes.value = newNodes;
  edges.value = newEdges;
}

watch(() => props.functions, layoutGraph, { immediate: true, deep: true });
</script>
