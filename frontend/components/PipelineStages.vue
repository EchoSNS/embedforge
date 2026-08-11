<template>
  <div class="space-y-4">
    <!-- Progress Bar -->
    <div class="flex items-center gap-2">
      <div class="h-2 flex-1 rounded-full bg-secondary">
        <div
          class="h-full rounded-full bg-primary transition-all duration-500"
          :style="{ width: `${progress}%` }"
        />
      </div>
      <span class="text-xs text-muted-foreground">{{ currentStageLabel }}</span>
    </div>

    <!-- Stage Cards -->
    <div class="space-y-3">
      <div
        v-for="(stage, idx) in stages"
        :key="stage.key"
        class="rounded-lg border p-4 transition-all"
        :class="{
          'border-primary bg-card': stage.key === activeStage,
          'opacity-50': idx > activeIndex,
          'border-green-500/30 bg-green-500/5': idx < activeIndex,
        }"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="flex h-7 w-7 items-center justify-center rounded-full text-xs"
              :class="{
                'bg-green-500 text-white': idx < activeIndex,
                'bg-primary text-primary-foreground': idx === activeIndex,
                'bg-secondary text-muted-foreground': idx > activeIndex,
              }"
            >
              {{ idx < activeIndex ? '✓' : idx + 1 }}
            </span>
            <h3 class="font-medium">{{ stage.label }}</h3>
          </div>
          <span v-if="loading && idx === activeIndex" class="text-xs text-muted-foreground animate-pulse">
            Processing...
          </span>
        </div>

        <!-- Expanded content for active stage -->
        <div v-if="idx === activeIndex && stageData" class="mt-4 space-y-3">
          <textarea
            v-model="editableJson"
            class="h-64 w-full rounded-md border bg-background p-3 font-mono text-xs"
            spellcheck="false"
          />
          <div class="flex gap-2">
            <button
              class="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:opacity-90"
              :disabled="loading"
              @click="$emit('approve', nextStageKey)"
            >
              ✅ Approve & Continue
            </button>
            <button
              class="rounded-md border px-4 py-2 text-sm hover:bg-accent"
              :disabled="loading"
              @click="saveEdit"
            >
              💾 Save Edit
            </button>
          </div>
        </div>

        <!-- Collapsed preview for completed stages -->
        <div v-if="idx < activeIndex && stage.dataKey" class="mt-2">
          <pre class="max-h-20 overflow-hidden rounded bg-secondary p-2 text-xs text-muted-foreground">{{ JSON.stringify(state[stage.dataKey], null, 2)?.slice(0, 200) }}...</pre>
        </div>
      </div>
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
