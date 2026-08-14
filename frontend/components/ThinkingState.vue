<template>
  <Transition name="fade-slide">
    <div v-if="visible" class="flex flex-col items-center justify-center py-16 space-y-6">
      <!-- Animated orbital ring -->
      <div class="relative h-20 w-20">
        <div class="absolute inset-0 rounded-full border-2 border-primary/20" />
        <div class="absolute inset-0 rounded-full border-2 border-transparent border-t-primary animate-orbit" />
        <div class="absolute inset-2 rounded-full border-2 border-transparent border-b-primary/60 animate-orbit [animation-direction:reverse] [animation-duration:2s]" />
        <div class="absolute inset-0 flex items-center justify-center">
          <Brain class="h-6 w-6 text-primary animate-thinking" />
        </div>
      </div>

      <!-- Status text -->
      <div class="text-center space-y-1.5">
        <p class="text-sm font-medium text-foreground">{{ title }}</p>
        <p class="text-xs text-muted-foreground">{{ subtitle }}</p>
      </div>

      <!-- Stage dots -->
      <div v-if="stages.length" class="flex items-center gap-3">
        <div
          v-for="(s, i) in stages"
          :key="i"
          class="flex items-center gap-1.5"
        >
          <span
            class="h-2 w-2 rounded-full transition-all duration-500"
            :class="i <= activeStageIndex ? 'bg-primary scale-110' : 'bg-border'"
          />
          <span class="text-xs" :class="i <= activeStageIndex ? 'text-foreground' : 'text-muted-foreground'">
            {{ s }}
          </span>
        </div>
      </div>

      <!-- Elapsed time -->
      <p v-if="elapsed > 0" class="text-xs text-muted-foreground">
        {{ formatElapsed(elapsed) }} elapsed
      </p>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { Brain } from "@lucide/vue";

const props = withDefaults(defineProps<{
  visible: boolean;
  title?: string;
  subtitle?: string;
  stages?: string[];
  activeStageIndex?: number;
}>(), {
  title: "AI is thinking…",
  subtitle: "Analyzing your requirements and generating structured output",
  stages: () => [],
  activeStageIndex: 0,
});

const elapsed = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  timer = setInterval(() => {
    if (props.visible) elapsed.value++;
    else elapsed.value = 0;
  }, 1000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});

function formatElapsed(s: number): string {
  return s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
}
</script>
