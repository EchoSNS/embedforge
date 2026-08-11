/**
 * Workflow API composable — manages session state and API calls.
 */

import { ref } from "vue";

const API_BASE = "http://localhost:8000";

export interface WorkflowState {
  session_id: string;
  stage: string;
  user_input: string;
  board_name: string;
  requirements: Record<string, any>;
  hardware_spec: Record<string, any>;
  software_arch: Record<string, any>;
  software_detailed: Record<string, any>;
  generated_code: Record<string, string>;
  review_result: Record<string, any>;
  errors: string[];
  history: any[];
}

export function useWorkflow() {
  const currentSession = ref<WorkflowState | null>(null);

  async function fetchBoards() {
    const res = await fetch(`${API_BASE}/api/plugins/boards`);
    return res.json();
  }

  async function startSession(userInput: string, boardName: string) {
    const res = await fetch(`${API_BASE}/api/workflow/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: userInput, board_name: boardName }),
    });
    const data = await res.json();

    // Immediately fetch full state
    const stateRes = await fetch(`${API_BASE}/api/workflow/${data.session_id}/state`);
    currentSession.value = await stateRes.json();
  }

  async function approve(stage: string) {
    if (!currentSession.value) return;
    const sid = currentSession.value.session_id;

    const res = await fetch(`${API_BASE}/api/workflow/${sid}/approve/${stage}`, {
      method: "POST",
    });
    currentSession.value = await res.json();
  }

  async function edit(stage: string, data: Record<string, any>) {
    if (!currentSession.value) return;
    const sid = currentSession.value.session_id;

    await fetch(`${API_BASE}/api/workflow/${sid}/edit/${stage}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data }),
    });

    // Refresh state
    const stateRes = await fetch(`${API_BASE}/api/workflow/${sid}/state`);
    currentSession.value = await stateRes.json();
  }

  return { currentSession, startSession, approve, edit, fetchBoards };
}
