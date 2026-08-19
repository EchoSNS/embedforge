<template>
  <div class="space-y-4">
    <!-- Progress Bar -->
    <div class="flex items-center gap-3">
      <div class="h-1.5 flex-1 rounded-full bg-secondary overflow-hidden">
        <div
          class="h-full rounded-full bg-gradient-to-r from-primary to-primary/70 transition-all duration-700 ease-out"
          :class="{ 'animate-shimmer': loading }"
          :style="{ width: `${progress}%` }"
        />
      </div>
      <span class="text-xs font-medium text-muted-foreground whitespace-nowrap">{{ currentStageLabel }}</span>
    </div>

    <!-- Stage Cards with vertical connector -->
    <div class="relative">
      <!-- Vertical connector line -->
      <div class="absolute left-[19px] top-8 bottom-8 w-px bg-border" />

      <div class="space-y-3 relative">
        <TransitionGroup name="stagger">
          <div
            v-for="(stage, idx) in stages"
            :key="stage.key"
            :style="{ transitionDelay: `${idx * 50}ms` }"
            class="rounded-xl border p-4 pl-12 relative transition-all duration-300"
            :class="{
              'border-primary/50 bg-card shadow-lg shadow-primary/5 ring-1 ring-primary/20': idx === activeIndex,
              'opacity-40 hover:opacity-60': idx > activeIndex,
              'border-green-500/20 bg-green-500/5': idx < activeIndex,
            }"
          >
            <!-- Step indicator (overlaps connector line) -->
            <span
              class="absolute left-3 top-4 flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium transition-all duration-300 z-10"
              :class="{
                'bg-green-500 text-white shadow-sm shadow-green-500/30': idx < activeIndex,
                'bg-primary text-primary-foreground shadow-sm shadow-primary/30': idx === activeIndex,
                'bg-secondary text-muted-foreground': idx > activeIndex,
              }"
            >
              <Transition name="theme-toggle" mode="out-in">
                <Check v-if="idx < activeIndex" key="check" class="h-3.5 w-3.5" />
                <component :is="stage.icon" v-else :key="idx" class="h-3.5 w-3.5" />
              </Transition>
            </span>

            <div class="flex items-center justify-between">
              <div>
                <h3 class="font-medium">{{ stage.label }}</h3>
                <p v-if="idx === activeIndex" class="text-xs text-muted-foreground mt-0.5">{{ stage.description }}</p>
              </div>
              <span v-if="loading && idx === activeIndex" class="flex items-center gap-1.5 text-xs text-primary">
                <Loader2 class="h-3 w-3 animate-spin" />
                Processing
              </span>
            </div>

            <!-- Expanded content for active stage -->
            <Transition name="fade-slide">
              <div v-if="idx === activeIndex && stageData" class="mt-4 space-y-3">
                <!-- Build stage: structured results view -->
                <BuildResults v-if="stage.key === 'build'" :results="stageData" />
                <!-- Other stages: editable JSON -->
                <textarea
                  v-else
                  v-model="editableJson"
                  class="min-h-[16rem] max-h-[28rem] w-full rounded-lg border bg-background/50 p-3 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-ring/50 transition-all duration-200"
                  spellcheck="false"
                />
                <div class="flex gap-2">
                  <button
                    v-if="stage.key !== 'build' && stage.key !== 'review'"
                    class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-all duration-200 active:scale-[0.98] disabled:opacity-50"
                    :disabled="loading"
                    @click="$emit('approve', nextStageKey)"
                  >
                    <CheckCircle2 class="h-3.5 w-3.5" />
                    Approve & Continue
                  </button>
                  <button
                    v-if="stage.key !== 'build' && stage.key !== 'review'"
                    class="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm hover:bg-accent transition-all duration-200 active:scale-[0.98] disabled:opacity-50"
                    :disabled="loading"
                    @click="saveEdit"
                  >
                    <Save class="h-3.5 w-3.5" />
                    Save Edit
                  </button>
                  <button
                    class="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm hover:bg-accent transition-all duration-200 active:scale-[0.98]"
                    @click="downloadStage(stage.dataKey)"
                  >
                    <Download class="h-3.5 w-3.5" />
                    Download
                  </button>
                </div>

                <!-- Build stage actions -->
                <div v-if="stage.key === 'build'" class="flex flex-wrap gap-2">
                  <button
                    class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-all duration-200 active:scale-[0.98] disabled:opacity-50"
                    :disabled="loading"
                    @click="$emit('validate')"
                  >
                    <ShieldCheck class="h-3.5 w-3.5" />
                    Validate
                  </button>
                  <button
                    class="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm hover:bg-accent transition-all duration-200 active:scale-[0.98] disabled:opacity-50"
                    :disabled="loading"
                    @click="$emit('analyze')"
                  >
                    <FlaskConical class="h-3.5 w-3.5" />
                    Static Analysis
                  </button>
                  <button
                    class="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm hover:bg-accent transition-all duration-200 active:scale-[0.98] disabled:opacity-50"
                    :disabled="loading"
                    @click="$emit('build')"
                  >
                    <Hammer class="h-3.5 w-3.5" />
                    Compile
                  </button>
                </div>
              </div>
            </Transition>

            <!-- Collapsed preview for completed stages -->
            <Transition name="fade-slide">
              <div v-if="idx < activeIndex && stage.dataKey" class="mt-3">
                <pre class="max-h-20 overflow-hidden rounded-lg bg-secondary/50 p-2.5 text-xs text-muted-foreground font-mono">{{ JSON.stringify(state[stage.dataKey], null, 2)?.slice(0, 200) }}...</pre>
                <button
                  class="inline-flex items-center gap-1.5 mt-2 rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-all duration-200 active:scale-[0.98]"
                  @click="downloadStage(stage.dataKey)"
                >
                  <Download class="h-3 w-3" />
                  Download
                </button>
              </div>
            </Transition>

            <!-- Inline error display with retry -->
            <Transition name="fade-slide">
              <div v-if="idx === activeIndex && hasErrors" class="mt-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 space-y-2">
                <p class="text-xs font-semibold text-destructive flex items-center gap-1.5">
                  <AlertCircle class="h-3.5 w-3.5" />
                  Stage failed
                </p>
                <ul class="space-y-1">
                  <li v-for="(err, i) in state.errors" :key="i" class="text-xs text-muted-foreground leading-relaxed">• {{ err }}</li>
                </ul>
                <button
                  class="flex items-center gap-1.5 rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/20 transition-all duration-200 active:scale-[0.98] disabled:opacity-50"
                  :disabled="loading"
                  @click="$emit('retry', stages[activeIndex].nextApprove || stages[activeIndex].key)"
                >
                  <RotateCcw class="h-3 w-3" />
                  Retry this stage
                </button>
              </div>
            </Transition>
          </div>
        </TransitionGroup>
      </div>
    </div>

    <!-- Full Package Download -->
    <div v-if="activeIndex > 0" class="pt-4 border-t">
      <button
        class="inline-flex items-center gap-2 rounded-lg bg-secondary px-4 py-2.5 text-sm font-medium hover:bg-accent transition-all duration-200 active:scale-[0.98]"
        @click="downloadFullPackage"
      >
        <Package class="h-4 w-4" />
        Download Full Package
      </button>
      <p class="text-xs text-muted-foreground mt-1.5">Includes all stage data, generated code, and logs</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRuntimeConfig } from "#app";
import { Check, CheckCircle2, Save, Loader2, FileText, Cpu, Layers, Code2, Braces, ShieldCheck, Hammer, FlaskConical, Zap, AlertCircle, RotateCcw, Download, Package } from "@lucide/vue";

const config = useRuntimeConfig();
const apiBase = config.public.apiBase as string;

const props = defineProps<{
  state: any;
  loading: boolean;
}>();

const emit = defineEmits<{
  approve: [stage: string];
  edit: [stage: string, data: any];
  validate: [];
  analyze: [];
  build: [];
  retry: [stage: string];
}>();

function getStageDownloadUrl(stage: string) {
  const sid = props.state?.session_id;
  if (!sid) return "#";
  return `${apiBase}/api/workflow/${sid}/download/stage/${stage}`;
}

function getFullPackageDownloadUrl() {
  const sid = props.state?.session_id;
  if (!sid) return "#";
  return `${apiBase}/api/workflow/${sid}/download/full`;
}

function downloadStage(stage: string) {
  const url = getStageDownloadUrl(stage);
  if (url === "#") return;
  window.open(url, "_blank");
}

function downloadFullPackage() {
  const url = getFullPackageDownloadUrl();
  if (url === "#") return;
  window.open(url, "_blank");
}

const stages = [
  { key: "requirements", label: "Requirements", description: "Review the AI-refined requirements before proceeding", dataKey: "requirements", nextApprove: "hardware", icon: FileText },
  { key: "hardware", label: "Hardware Design", description: "Assigning peripherals, pins, and clocks", dataKey: "hardware_spec", nextApprove: "system_design", icon: Cpu },
  { key: "system_design", label: "System Design", description: "Resource allocation, data flows, and timing constraints", dataKey: "system_design", nextApprove: "software_arch", icon: Layers },
  { key: "software_architecture", label: "Software Architecture", description: "Selecting SDK drivers and defining structure", dataKey: "software_arch", nextApprove: "software_detailed", icon: Layers },
  { key: "software_detailed", label: "Detailed Design", description: "Function-level design with SDK calls", dataKey: "software_detailed", nextApprove: "codegen", icon: Braces },
  { key: "codegen", label: "Code Generation", description: "Generating production C code via TDD", dataKey: "generated_code", nextApprove: "review", icon: Code2 },
  { key: "review", label: "AI Review", description: "Reviewing code for correctness and safety", dataKey: "review_result", nextApprove: "", icon: ShieldCheck },
  { key: "build", label: "Build & Validate", description: "Static analysis, compilation, and firmware flashing", dataKey: "build_result", nextApprove: "", icon: Hammer },
];

const activeIndex = computed(() => {
  for (let i = stages.length - 1; i >= 0; i--) {
    const data = props.state?.[stages[i].dataKey];
    if (data && Object.keys(data).length) {
      // Auto-advance past review to build when review is done with no errors
      if (stages[i].key === "review" && !props.state?.errors?.length) {
        return Math.min(i + 1, stages.length - 1);
      }
      return i;
    }
  }
  return 0;
});

const activeStage = computed(() => stages[activeIndex.value]?.key || "requirements");
const currentStageLabel = computed(() => stages[activeIndex.value]?.label || "");
const progress = computed(() => ((activeIndex.value + 1) / stages.length) * 100);
const nextStageKey = computed(() => stages[activeIndex.value]?.nextApprove || "");

const stageData = computed(() => {
  const dataKey = stages[activeIndex.value]?.dataKey;
  return dataKey ? props.state?.[dataKey] : null;
});

const hasErrors = computed(() => props.state?.errors?.length > 0);

const editableJson = ref("");

watch(stageData, (val) => {
  if (val && Object.keys(val).length) editableJson.value = JSON.stringify(val, null, 2);
}, { immediate: true });

function saveEdit() {
  try {
    const parsed = JSON.parse(editableJson.value);
    const dataKey = stages[activeIndex.value]?.dataKey;
    if (dataKey) emit("edit", dataKey, parsed);
  } catch {
    // Invalid JSON
  }
}
</script>
