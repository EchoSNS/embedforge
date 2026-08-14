<template>
  <div class="rounded-xl border border-primary/20 bg-primary/5 p-4 mb-4 animate-fade-in">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <div class="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <FileCheck class="h-3.5 w-3.5" />
        </div>
        <div>
          <h3 class="font-medium text-sm">Requirements Refined</h3>
          <p class="text-xs text-muted-foreground">AI-generated from your description</p>
        </div>
      </div>
      <button
        class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md px-2 py-1 hover:bg-accent"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'Collapse' : 'View JSON' }}
        <ChevronDown class="h-3 w-3 transition-transform duration-200" :class="{ 'rotate-180': expanded }" />
      </button>
    </div>

    <!-- Summary chips -->
    <div class="flex flex-wrap gap-1.5 mb-2">
      <span v-if="requirements.peripheral_type" class="rounded-full bg-primary/15 text-primary px-2.5 py-0.5 text-xs font-medium">
        {{ requirements.peripheral_type }}
      </span>
      <span v-if="requirements.frequency_hz" class="rounded-full bg-accent text-accent-foreground px-2.5 py-0.5 text-xs">
        {{ formatFreq(requirements.frequency_hz) }}
      </span>
      <span v-if="requirements.channel_count" class="rounded-full bg-accent text-accent-foreground px-2.5 py-0.5 text-xs">
        {{ requirements.channel_count }} ch
      </span>
      <span v-if="requirements.interrupt_required" class="rounded-full bg-accent text-accent-foreground px-2.5 py-0.5 text-xs">
        IRQ
      </span>
      <span v-if="requirements.dma_required" class="rounded-full bg-accent text-accent-foreground px-2.5 py-0.5 text-xs">
        DMA
      </span>
      <span v-for="feat in (requirements.features || []).slice(0, 4)" :key="feat" class="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-secondary-foreground">
        {{ feat }}
      </span>
    </div>

    <p v-if="requirements.description" class="text-sm text-muted-foreground leading-relaxed">
      {{ requirements.description }}
    </p>

    <!-- Full JSON -->
    <Transition name="fade-slide">
      <pre v-if="expanded" class="mt-3 rounded-lg bg-card border p-3 text-xs font-mono overflow-auto max-h-48 text-foreground/80">{{ JSON.stringify(requirements, null, 2) }}</pre>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { FileCheck, ChevronDown } from "@lucide/vue";

defineProps<{
  requirements: Record<string, any>;
}>();

const expanded = ref(false);

function formatFreq(hz: number): string {
  if (hz >= 1_000_000) return `${(hz / 1_000_000).toFixed(1)} MHz`;
  if (hz >= 1_000) return `${(hz / 1_000).toFixed(1)} kHz`;
  return `${hz} Hz`;
}
</script>
