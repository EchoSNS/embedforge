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

    <!-- Stage Cards -->
    <div class="space-y-3">
      <TransitionGroup name="stagger">
        <div
          v-for="(stage, idx) in stages"
          :key="stage.key"
          :style="{ transitionDelay: `${idx * 50}ms` }"
          class="rounded-xl border p-4 transition-all duration-300"
          :class="{
            'border-primary/50 bg-card shadow-lg shadow-primary/5 ring-1 ring-primary/20': stage.key === activeStage,
            'opacity-40 hover:opacity-60': idx > activeIndex,
            'border-green-500/20 bg-green-500/5': idx < activeIndex,
          }"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span
                class="flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium transition-all duration-300"
                :class="{
                  'bg-green-500 text-white shadow-sm shadow-green-500/30': idx < activeIndex,
                  'bg-primary text-primary-foreground shadow-sm shadow-primary/30': idx === activeIndex,
                  'bg-secondary text-muted-foreground': idx > activeIndex,
                }"
              >
                <Transition name="theme-toggle" mode="out-in">
                  <span v-if="idx < activeIndex" key="check">✓</span>
                  <span v-else :key="idx">{{ idx + 1 }}</span>
                </Transition>
              </span>
              <h3 class="font-medium">{{ stage.label }}</h3>
            </div>
            <span v-if="loading && idx === activeIndex" class="flex items-center gap-1.5 text-xs text-primary">
              <span class="flex gap-0.5">
                <span class="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
                <span class="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
                <span class="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
              </span>
              Processing
            </span>
          </div>

          <!-- Expanded content for active stage -->
          <Transition name="fade-slide">
            <div v-if="idx === activeIndex && stageData" class="mt-4 space-y-3">
              <textarea
                v-model="editableJson"
                class="h-64 w-full rounded-lg border bg-background/50 p-3 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-ring/50 transition-all duration-200 resize-none"
                spellcheck="false"
              />
              <div class="flex gap-2">
                <button
                  class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-all duration-200 active:scale-[0.98] disabled:opacity-50"
                  :disabled="loading"
                  @click="$emit('approve', nextStageKey)"
                >
                  ✅ Approve & Continue
                </button>
                <button
                  class="rounded-lg border px-4 py-2 text-sm hover:bg-accent transition-all duration-200 active:scale-[0.98] disabled:opacity-50"
                  :disabled="loading"
                  @click="saveEdit"
                >
                  💾 Save Edit
                </button>
              </div>
            </div>
          </Transition>

          <!-- Collapsed preview for completed stages -->
          <Transition name="fade-slide">
            <div v-if="idx < activeIndex && stage.dataKey" class="mt-3">
              <pre class="max-h-20 overflow-hidden rounded-lg bg-secondary/50 p-2.5 text-xs text-muted-foreground font-mono">{{ JSON.stringify(state[stage.dataKey], null, 2)?.slice(0, 200) }}...</pre>
            </div>
          </Transition>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";

const props = defineProps<{
  state: any;
  loading: boolean;
}>();

const emit = defineEmits<{
  approve: [stage: string];
  edit: [stage: string, data: any];
}>();

const stages = [
  { key: "clarifier", label: "Requirements", dataKey: "requirements", nextApprove: "hardware" },
  { key: "hardware", label: "Hardware Design", dataKey: "hardware_spec", nextApprove: "software_arch" },
  { key: "software_architecture", label: "Software Architecture", dataKey: "software_arch", nextApprove: "software_detailed" },
  { key: "software_detailed", label: "Detailed Design", dataKey: "software_detailed", nextApprove: "codegen" },
  { key: "codegen", label: "Code Generation", dataKey: "generated_code", nextApprove: "review" },
  { key: "review", label: "AI Review", dataKey: "review_result", nextApprove: "" },
];

const activeIndex = computed(() => {
  const idx = stages.findIndex((s) => s.key === props.state?.stage);
  return idx >= 0 ? idx : 0;
});

const activeStage = computed(() => props.state?.stage || "clarifier");
const currentStageLabel = computed(() => stages[activeIndex.value]?.label || "");
const progress = computed(() => ((activeIndex.value + 1) / stages.length) * 100);
const nextStageKey = computed(() => stages[activeIndex.value]?.nextApprove || "");

const stageData = computed(() => {
  const dataKey = stages[activeIndex.value]?.dataKey;
  return dataKey ? props.state?.[dataKey] : null;
});

const editableJson = ref("");

watch(stageData, (val) => {
  if (val) editableJson.value = JSON.stringify(val, null, 2);
}, { immediate: true });

function saveEdit() {
  try {
    const parsed = JSON.parse(editableJson.value);
    const dataKey = stages[activeIndex.value]?.dataKey;
    if (dataKey) emit("edit", dataKey, parsed);
  } catch {
    // Invalid JSON — ignore
  }
}
</script>
