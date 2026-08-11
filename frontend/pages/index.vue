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
        <div class="flex items-center gap-2">
          <span class="text-xl font-bold animate-pulse-slow">⚡</span>
          <h1 class="text-lg font-semibold tracking-tight">EmbedForge</h1>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="activeBoard" class="rounded-full bg-primary/10 text-primary px-3 py-1 text-xs font-medium border border-primary/20 animate-fade-in">
            {{ activeBoard }}
          </span>
          <button
            class="relative rounded-full p-2 hover:bg-accent transition-all duration-200 hover:scale-110 active:scale-95"
            @click="toggleTheme"
            aria-label="Toggle dark mode"
          >
            <Transition name="theme-toggle" mode="out-in">
              <span v-if="isDark === 'dark'" key="sun" class="block">☀️</span>
              <span v-else key="moon" class="block">🌙</span>
            </Transition>
          </button>
        </div>
      </header>

      <!-- Body: Pipeline + Code Viewer -->
      <div class="flex flex-1 overflow-hidden">
        <!-- Pipeline Stages -->
        <div class="flex-1 overflow-y-auto border-r p-6 scroll-smooth">
          <!-- Input Form (no active session) -->
          <Transition name="fade-slide" appear>
            <div v-if="!currentSession" class="mx-auto max-w-2xl space-y-6">
              <div class="space-y-2">
                <h2 class="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                  Describe Your Requirement
                </h2>
                <p class="text-muted-foreground">
                  Tell us what embedded firmware you need. Be specific about peripherals, frequencies, and behavior.
                </p>
              </div>
              <div class="relative group">
                <textarea
                  v-model="userInput"
                  class="h-40 w-full rounded-xl border bg-card p-4 text-sm focus:outline-none focus:ring-2 focus:ring-ring transition-shadow duration-200 resize-none shadow-sm group-hover:shadow-md"
                  placeholder="Example: Generate a 3-phase PWM driver at 20kHz with complementary outputs and 1µs dead-time for BLDC motor control"
                />
                <div class="absolute bottom-3 right-3 text-xs text-muted-foreground">
                  {{ userInput.length }} chars
                </div>
              </div>
              <div class="flex gap-3">
                <button
                  class="relative rounded-xl bg-primary px-6 py-2.5 text-primary-foreground font-medium hover:opacity-90 disabled:opacity-50 transition-all duration-200 hover:shadow-lg hover:shadow-primary/25 active:scale-[0.98] overflow-hidden group"
                  :disabled="!userInput.trim() || !activeBoard"
                  @click="startWorkflow"
                >
                  <span class="relative z-10 flex items-center gap-2">
                    🚀 Start Generation
                  </span>
                  <span class="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                </button>
              </div>

              <!-- Quick examples -->
              <div class="space-y-2 pt-4">
                <p class="text-sm font-medium text-muted-foreground">Quick examples:</p>
                <TransitionGroup name="stagger" appear>
                  <button
                    v-for="(ex, i) in examples"
                    :key="ex"
                    :style="{ transitionDelay: `${i * 75}ms` }"
                    class="block w-full rounded-xl border p-3 text-left text-sm hover:bg-accent hover:border-primary/30 transition-all duration-200 hover:translate-x-1 hover:shadow-sm"
                    @click="userInput = ex"
                  >
                    <span class="text-muted-foreground mr-2">→</span>{{ ex }}
                  </button>
                </TransitionGroup>
              </div>
            </div>
          </Transition>

          <!-- Active Pipeline -->
          <Transition name="fade-slide" appear>
            <PipelineStages
              v-if="currentSession"
              :state="currentSession"
              :loading="loading"
              @approve="approveStage"
              @edit="editStage"
            />
          </Transition>
        </div>

        <!-- Code Viewer Panel -->
        <Transition name="slide-in-right">
          <div v-if="currentSession?.generated_code" class="w-[40%] overflow-hidden">
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
import { ref, inject, onMounted } from "vue";
import { useWorkflow } from "~/composables/useWorkflow";

const isDark = inject<any>("isDark");
const toggleTheme = inject<() => void>("toggleDark")!;

const userInput = ref("");
const activeBoard = ref("");
const boards = ref<string[]>([]);
const sessions = ref<string[]>([]);
const loading = ref(false);

const { currentSession, startSession, approve, edit, fetchBoards } = useWorkflow();

const examples = [
  "LED blink on PA5 at 1Hz using TIM2",
  "PWM output at 10kHz on TIM3 CH1, duty cycle controllable via ADC",
  "UART2 echo server at 115200 baud with interrupt-driven receive",
  "3-phase complementary PWM at 20kHz with 500ns dead-time using TIM1",
];

onMounted(async () => {
  const data = await fetchBoards();
  boards.value = data.map((b: any) => b.name);
  if (boards.value.length) activeBoard.value = boards.value[0];
});

async function startWorkflow() {
  loading.value = true;
  await startSession(userInput.value, activeBoard.value);
  sessions.value.push(currentSession.value!.session_id);
  loading.value = false;
}

function startNewSession() {
  userInput.value = "";
  currentSession.value = null;
}

async function approveStage(stage: string) {
  loading.value = true;
  await approve(stage);
  loading.value = false;
}

async function editStage(stage: string, data: any) {
  await edit(stage, data);
}
</script>
