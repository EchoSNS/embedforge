<template>
  <div class="space-y-3">
    <!-- Summary Badges -->
    <div class="flex flex-wrap gap-2">
      <span v-if="validation" class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-medium"
        :class="validation.passed ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'">
        <component :is="validation.passed ? CheckCircle2 : XCircle" class="h-3 w-3" />
        Validation {{ validation.passed ? 'Passed' : 'Failed' }}
      </span>
      <span v-if="analysis" class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-medium"
        :class="analysis.available === false ? 'bg-muted text-muted-foreground' : analysis.total_issues === 0 ? 'bg-green-500/10 text-green-600' : 'bg-amber-500/10 text-amber-600'">
        <FlaskConical class="h-3 w-3" />
        {{ analysis.available === false ? 'cppcheck N/A' : `${analysis.total_issues || 0} issues` }}
      </span>
      <span v-if="build" class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-medium"
        :class="build.success ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'">
        <Hammer class="h-3 w-3" />
        {{ build.success ? 'Build OK' : 'Build Failed' }}
      </span>
    </div>

    <!-- Tabs -->
    <div class="flex border-b">
      <button v-for="tab in availableTabs" :key="tab.id"
        class="px-3 py-1.5 text-[10px] font-medium border-b-2 transition-colors"
        :class="activeTab === tab.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'"
        @click="activeTab = tab.id">
        {{ tab.label }}
        <span v-if="tab.count" class="ml-1 rounded-full bg-muted px-1.5 text-[9px]">{{ tab.count }}</span>
      </button>
    </div>

    <!-- Validation Tab -->
    <div v-if="activeTab === 'validation' && validation" class="space-y-2 max-h-64 overflow-y-auto">
      <!-- Pin Issues -->
      <div v-if="validation.pin_issues?.length" class="space-y-1">
        <p class="text-[10px] font-medium text-red-500">Pin Issues ({{ validation.pin_issues.length }})</p>
        <div v-for="(issue, i) in validation.pin_issues" :key="i"
          class="flex items-center gap-2 rounded bg-red-500/5 px-2 py-1 text-[10px]">
          <XCircle class="h-3 w-3 text-red-400 shrink-0" />
          <span>{{ issue }}</span>
        </div>
      </div>
      <!-- Missing Headers -->
      <div v-if="validation.missing_headers?.length" class="space-y-1">
        <p class="text-[10px] font-medium text-amber-500">Missing Headers ({{ validation.missing_headers.length }})</p>
        <div v-for="(h, i) in validation.missing_headers.slice(0, 20)" :key="i"
          class="flex items-center gap-2 rounded bg-amber-500/5 px-2 py-1 text-[10px] font-mono">
          <AlertTriangle class="h-3 w-3 text-amber-400 shrink-0" />
          <span class="truncate">{{ h }}</span>
        </div>
        <p v-if="validation.missing_headers.length > 20" class="text-[9px] text-muted-foreground">
          ... and {{ validation.missing_headers.length - 20 }} more
        </p>
      </div>
      <!-- Rule Violations -->
      <div v-if="validation.rule_violations?.length" class="space-y-1">
        <p class="text-[10px] font-medium text-violet-500">Rule Violations</p>
        <div v-for="(v, i) in validation.rule_violations" :key="i"
          class="rounded bg-violet-500/5 px-2 py-1 text-[10px]">{{ v }}</div>
      </div>
      <p v-if="validation.passed && !validation.pin_issues?.length && !validation.missing_headers?.length"
        class="text-xs text-green-600 flex items-center gap-1.5">
        <CheckCircle2 class="h-3.5 w-3.5" /> All checks passed
      </p>
    </div>

    <!-- Analysis Tab -->
    <div v-if="activeTab === 'analysis' && analysis" class="space-y-1 max-h-64 overflow-y-auto">
      <div v-if="analysis.available === false" class="text-xs text-muted-foreground py-4 text-center">
        {{ analysis.message || 'Static analysis tool not available' }}
      </div>
      <div v-else-if="analysis.issues?.length">
        <div v-for="(issue, i) in analysis.issues" :key="i"
          class="flex items-start gap-2 rounded px-2 py-1.5 text-[10px]"
          :class="severityBg(issue.severity)">
          <span class="shrink-0 rounded px-1 py-0.5 text-[9px] font-bold uppercase"
            :class="severityBadge(issue.severity)">{{ issue.severity }}</span>
          <div class="min-w-0">
            <span class="font-mono text-muted-foreground">{{ issue.file }}:{{ issue.line }}</span>
            <span class="ml-1.5">{{ issue.message }}</span>
          </div>
        </div>
      </div>
      <p v-else class="text-xs text-green-600 flex items-center gap-1.5 py-2">
        <CheckCircle2 class="h-3.5 w-3.5" /> No issues found
      </p>
    </div>

    <!-- Build Tab -->
    <div v-if="activeTab === 'build' && build" class="max-h-64 overflow-y-auto">
      <pre class="rounded-lg bg-[hsl(222,47%,4%)] p-3 text-[10px] font-mono leading-relaxed text-white/80 whitespace-pre-wrap">{{ build.log || (build.success ? 'Build successful' : 'No log available') }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { CheckCircle2, XCircle, AlertTriangle, FlaskConical, Hammer } from "@lucide/vue";

const props = defineProps<{
  results: Record<string, any>;
}>();

const activeTab = ref("validation");

const validation = computed(() => props.results?.validation);
const analysis = computed(() => props.results?.analysis);
const build = computed(() => {
  const r = props.results;
  if (r?.success !== undefined || r?.log) return r;
  return null;
});

const availableTabs = computed(() => {
  const tabs = [];
  if (validation.value) tabs.push({ id: "validation", label: "Validation", count: (validation.value.pin_issues?.length || 0) + (validation.value.missing_headers?.length || 0) });
  if (analysis.value) tabs.push({ id: "analysis", label: "Analysis", count: analysis.value.total_issues || 0 });
  if (build.value) tabs.push({ id: "build", label: "Build", count: 0 });
  if (!tabs.length) tabs.push({ id: "validation", label: "Validation", count: 0 });
  return tabs;
});

function severityBg(s: string): string {
  if (s === "error") return "bg-red-500/5";
  if (s === "warning") return "bg-amber-500/5";
  return "bg-sky-500/5";
}

function severityBadge(s: string): string {
  if (s === "error") return "bg-red-500/20 text-red-600";
  if (s === "warning") return "bg-amber-500/20 text-amber-600";
  return "bg-sky-500/20 text-sky-600";
}
</script>
