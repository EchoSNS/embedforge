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
      <header class="flex h-14 items-center justify-between border-b px-6">
        <div class="flex items-center gap-2">
          <span class="text-xl font-bold">⚡</span>
          <h1 class="text-lg font-semibold">EmbedForge</h1>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="activeBoard" class="rounded-md bg-secondary px-3 py-1 text-sm">
            {{ activeBoard }}
          </span>
          <button
            class="rounded-md p-2 hover:bg-accent"
            @click="darkMode = !darkMode"
          >
            {{ darkMode ? '☀️' : '🌙' }}
          </button>
        </div>
      </header>

      <!-- Body: Pipeline + Code Viewer -->
      <div class="flex flex-1 overflow-hidden">
        <!-- Pipeline Stages -->
        <div class="flex-1 overflow-y-auto border-r p-6">
          <!-- Input Form (no active session) -->
          <div v-if="!currentSession" class="mx-auto max-w-2xl space-y-6">
            <h2 class="text-2xl font-bold">Describe Your Requirement</h2>
            <p class="text-muted-foreground">
              Tell us what embedded firmware you need. Be specific about peripherals, frequencies, and behavior.
            </p>
            <textarea
              v-model="userInput"
              class="h-40 w-full rounded-lg border bg-card p-4 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Example: Generate a 3-phase PWM driver at 20kHz with complementary outputs and 1µs dead-time for BLDC motor control"
            />
            <div class="flex gap-3">
              <button
                class="rounded-lg bg-primary px-6 py-2 text-primary-foreground hover:opacity-90 disabled:opacity-50"
                :disabled="!userInput.trim() || !activeBoard"
                @click="startWorkflow"
              >
                🚀 Start Generation
              </button>
            </div>

            <!-- Quick examples -->
            <div class="space-y-2 pt-4">
              <p class="text-sm font-medium text-muted-foreground">Quick examples:</p>
              <button
                v-for="ex in examples"
                :key="ex"
                class="block w-full rounded-md border p-3 text-left text-sm hover:bg-accent"
                @click="userInput = ex"
              >
                {{ ex }}
              </button>
            </div>
          </div>

          <!-- Active Pipeline -->
          <PipelineStages
            v-if="currentSession"
            :state="currentSession"
            :loading="loading"
            @approve="approveStage"
            @edit="editStage"
          />
        </div>

        <!-- Code Viewer Panel -->
        <div v-if="currentSession?.generated_code" class="w-[40%] overflow-hidden">
          <CodeViewer :files="currentSession.generated_code" />
        </div>
      </div>

      <!-- Chat Panel -->
      <ChatPanel v-if="currentSession" :session-id="currentSession.session_id" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useWorkflow } from "~/composables/useWorkflow";

const darkMode = ref(true);
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
