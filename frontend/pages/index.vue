<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <Sidebar
      :boards="boards"
      :active-board="activeBoard"
      :sessions="sessions"
      @select-board="activeBoard = $event"
      @new-session="startNewSession"
    />

    <!-- Main Content -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <!-- Header -->
      <header class="flex h-14 items-center justify-between border-b backdrop-blur-sm bg-card/80 px-6 sticky top-0 z-10">
        <div class="flex items-center gap-2.5">
          <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <Zap class="h-4 w-4 text-primary" />
          </div>
          <h1 class="text-lg font-semibold tracking-tight">EmbedForge</h1>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="activeBoard" class="rounded-full bg-primary/10 text-primary px-3 py-1 text-xs font-medium border border-primary/20 animate-fade-in">
            <Cpu class="inline h-3 w-3 mr-1" />{{ activeBoard }}
          </span>
          <button
            class="relative rounded-full p-2 hover:bg-accent transition-all duration-200 hover:scale-110 active:scale-95"
            @click="toggleTheme()"
            aria-label="Toggle dark mode"
          >
            <Transition name="theme-toggle" mode="out-in">
              <Sun v-if="isDark" key="sun" class="h-4 w-4" />
              <Moon v-else key="moon" class="h-4 w-4" />
            </Transition>
          </button>
        </div>
      </header>

      <!-- Body: Pipeline + Code Viewer -->
      <div class="flex flex-1 overflow-hidden">
        <!-- Pipeline Stages -->
        <div class="flex-1 overflow-y-auto border-r p-6 scroll-smooth">

          <!-- Input Form (no active session, not loading) -->
          <Transition name="fade-slide" appear>
            <div v-if="!currentSession && !loading" class="mx-auto max-w-2xl space-y-6">
              <!-- Hero text -->
              <div class="space-y-2">
                <h2 class="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary via-foreground to-muted-foreground bg-clip-text text-transparent">
                  What firmware do you need?
                </h2>
                <p class="text-muted-foreground text-sm leading-relaxed">
                  Describe your embedded requirement in plain English. Be specific about
                  <span class="text-foreground font-medium">peripherals</span>,
                  <span class="text-foreground font-medium">frequencies</span>, and
                  <span class="text-foreground font-medium">behavior</span>.
                  The AI will refine it into a structured spec, then generate production C code.
                </p>
              </div>

              <!-- Input card -->
              <div class="rounded-xl border bg-card p-1 shadow-sm">
                <textarea
                  v-model="userInput"
                  class="h-36 w-full rounded-lg bg-transparent p-3 text-sm focus:outline-none resize-none placeholder:text-muted-foreground/50"
                  placeholder="Example: Generate a 3-phase PWM driver at 20kHz with complementary outputs and 1µs dead-time for BLDC motor control on STM32F4"
                  @keydown.ctrl.enter="startWorkflow"
                />
                <div class="flex items-center justify-between px-3 pb-2">
                  <span class="text-xs text-muted-foreground">{{ userInput.length }} chars · Ctrl+Enter to submit</span>
                  <button
                    class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40 transition-all duration-200 active:scale-[0.97]"
                    :disabled="!userInput.trim() || !activeBoard"
                    @click="startWorkflow"
                  >
                    <Sparkles class="h-3.5 w-3.5" />
                    Generate
                  </button>
                </div>
              </div>

              <!-- How it works -->
              <div class="rounded-xl border bg-card/50 p-4 space-y-3">
                <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">How it works</p>
                <div class="grid grid-cols-3 gap-3">
                  <div class="space-y-1">
                    <div class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">1</div>
                    <p class="text-xs text-muted-foreground">Describe your requirement in natural language</p>
                  </div>
                  <div class="space-y-1">
                    <div class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">2</div>
                    <p class="text-xs text-muted-foreground">Review & approve each stage of the pipeline</p>
                  </div>
                  <div class="space-y-1">
                    <div class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">3</div>
                    <p class="text-xs text-muted-foreground">Get production-ready C code with tests</p>
                  </div>
                </div>
              </div>

              <!-- Quick examples -->
              <div class="space-y-2">
                <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Lightbulb class="h-3 w-3" /> Try an example
                </p>
                <div class="grid grid-cols-2 gap-2">
                  <button
                    v-for="ex in examples"
                    :key="ex"
                    class="rounded-lg border p-2.5 text-left text-xs hover:bg-accent hover:border-primary/30 transition-all duration-200"
                    @click="userInput = ex"
                  >
                    {{ ex }}
                  </button>
                </div>
              </div>
            </div>
          </Transition>

          <!-- Thinking state (during initial generation) -->
          <ThinkingState
            :visible="loading && !currentSession"
            title="Refining your requirements…"
            subtitle="The AI is analyzing your input and generating a structured specification"
            :stages="['Parsing', 'Analyzing MCU', 'Structuring']"
            :active-stage-index="thinkingStage"
          />

          <!-- Active Pipeline -->
          <Transition name="fade-slide" appear>
            <div v-if="currentSession && !loading">
              <PipelineStages
                :state="currentSession"
                :loading="stageLoading"
                @approve="approveStage"
                @edit="editStage"
                @validate="runValidate"
                @analyze="runAnalyze"
                @build="runBuild"
                @retry="retryStage"
              />
            </div>
          </Transition>

          <!-- Thinking state (during stage advancement) -->
          <ThinkingState
            :visible="stageLoading && !!currentSession"
            title="Processing next stage…"
            subtitle="The AI is working through the pipeline"
            :stages="['Generating', 'Validating', 'Structuring']"
            :active-stage-index="thinkingStage"
          />

          <!-- Error display -->
          <div v-if="currentSession?.errors?.length" class="mt-4 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
            <p class="text-sm font-medium text-destructive">Generation encountered errors:</p>
            <ul class="mt-2 space-y-1">
              <li v-for="(err, i) in currentSession.errors" :key="i" class="text-xs text-muted-foreground">• {{ err }}</li>
            </ul>
          </div>

          <!-- Activity Log (visible when session active or loading) -->
          <div v-if="currentSession || loading" class="mt-4">
            <ActivityLog />
          </div>
        </div>

        <!-- Code Viewer Panel -->
        <Transition name="slide-in-right">
          <div v-if="currentSession?.generated_code && Object.keys(currentSession.generated_code).length" class="w-[40%] overflow-hidden">
            <CodeViewer :files="currentSession.generated_code" />
          </div>
        </Transition>
      </div>

      <!-- Chat Panel -->
      <ChatPanel v-if="currentSession" :session-id="currentSession.session_id" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, inject, onMounted, type Ref } from "vue";
import { Sun, Moon, Zap, Cpu, Sparkles, Lightbulb } from "@lucide/vue";
import { useWorkflow } from "~/composables/useWorkflow";

const isDark = inject<Ref<boolean>>("isDark")!;
const toggleTheme = inject<() => void>("toggleDark")!;

const userInput = ref("");
const activeBoard = ref("");
const boards = ref<string[]>([]);
const sessions = ref<string[]>([]);
const loading = ref(false);
const stageLoading = ref(false);
const thinkingStage = ref(0);
let thinkingTimer: ReturnType<typeof setInterval> | null = null;

const { currentSession, startSession, approve, edit, validate, analyze, build, getDownloadUrl, fetchBoards } = useWorkflow();

const examples = [
  "LED blink on PA5 at 1Hz using TIM2",
  "PWM output at 10kHz on TIM3 CH1, duty cycle controllable via ADC",
  "UART2 echo server at 115200 baud with interrupt-driven receive",
  "3-phase complementary PWM at 20kHz with 500ns dead-time using TIM1",
];

function startThinkingAnimation() {
  thinkingStage.value = 0;
  thinkingTimer = setInterval(() => {
    thinkingStage.value = Math.min(thinkingStage.value + 1, 2);
  }, 3000);
}

function stopThinkingAnimation() {
  if (thinkingTimer) { clearInterval(thinkingTimer); thinkingTimer = null; }
  thinkingStage.value = 0;
}

onMounted(async () => {
  try {
    const data = await fetchBoards();
    boards.value = data.map((b: any) => b.name);
    if (boards.value.length) activeBoard.value = boards.value[0];
  } catch {
    // Backend not reachable
  }
});

async function startWorkflow() {
  if (!userInput.value.trim() || !activeBoard.value) return;
  loading.value = true;
  startThinkingAnimation();
  try {
    await startSession(userInput.value, activeBoard.value);
    if (currentSession.value) {
      sessions.value.push(currentSession.value.session_id);
    }
  } finally {
    loading.value = false;
    stopThinkingAnimation();
  }
}

function startNewSession() {
  userInput.value = "";
  currentSession.value = null;
}

async function approveStage(stage: string) {
  stageLoading.value = true;
  startThinkingAnimation();
  try {
    await approve(stage);
  } finally {
    stageLoading.value = false;
    stopThinkingAnimation();
  }
}

async function editStage(stage: string, data: any) {
  await edit(stage, data);
}

async function retryStage(stage: string) {
  await approveStage(stage);
}

async function runValidate() {
  stageLoading.value = true;
  try {
    const result = await validate();
    if (currentSession.value) {
      currentSession.value.build_result = { ...currentSession.value.build_result, validation: result };
    }
  } finally {
    stageLoading.value = false;
  }
}

async function runAnalyze() {
  stageLoading.value = true;
  try {
    const result = await analyze();
    if (currentSession.value) {
      currentSession.value.build_result = { ...currentSession.value.build_result, analysis: result };
    }
  } finally {
    stageLoading.value = false;
  }
}

async function runBuild() {
  stageLoading.value = true;
  startThinkingAnimation();
  try {
    const result = await build();
    if (currentSession.value) {
      currentSession.value.build_result = { ...currentSession.value.build_result, ...result };
    }
  } finally {
    stageLoading.value = false;
    stopThinkingAnimation();
  }
}
</script>
