/**
 * Workflow API composable — manages session state and API calls.
 * Uses useState for cross-page persistence within the SPA.
 */

import { useState } from "#app";
import { useRuntimeConfig } from "#app";

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
  build_result: Record<string, any>;
  errors: string[];
  history: any[];
}

export function useWorkflow() {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;
  // useState persists across client-side page navigations
  const currentSession = useState<WorkflowState | null>("workflow-session", () => null);
  const sessionList = useState<string[]>("workflow-sessions", () => []);

  async function fetchBoards() {
    const res = await fetch(`${apiBase}/api/plugins/boards`);
    return res.json();
  }

  async function startSession(userInput: string, boardName: string) {
    const res = await fetch(`${apiBase}/api/workflow/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: userInput, board_name: boardName }),
    });
    const data = await res.json();

    const stateRes = await fetch(`${apiBase}/api/workflow/${data.session_id}/state`);
    currentSession.value = await stateRes.json();
    if (currentSession.value && !sessionList.value.includes(currentSession.value.session_id)) {
      sessionList.value.push(currentSession.value.session_id);
    }
  }

  async function loadSession(sessionId: string) {
    const stateRes = await fetch(`${apiBase}/api/workflow/${sessionId}/state`);
    if (!stateRes.ok) return;
    currentSession.value = await stateRes.json();
  }

  async function approve(stage: string) {
    if (!currentSession.value) return;
    const sid = currentSession.value.session_id;

    const res = await fetch(`${apiBase}/api/workflow/${sid}/approve/${stage}`, {
      method: "POST",
    });
    currentSession.value = await res.json();
  }

  async function edit(stage: string, data: Record<string, any>) {
    if (!currentSession.value) return;
    const sid = currentSession.value.session_id;

    await fetch(`${apiBase}/api/workflow/${sid}/edit/${stage}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data }),
    });

    const stateRes = await fetch(`${apiBase}/api/workflow/${sid}/state`);
    currentSession.value = await stateRes.json();
  }

  async function validate() {
    if (!currentSession.value) return null;
    const sid = currentSession.value.session_id;
    const res = await fetch(`${apiBase}/api/workflow/${sid}/validate`, { method: "POST" });
    return res.json();
  }

  async function analyze() {
    if (!currentSession.value) return null;
    const sid = currentSession.value.session_id;
    const res = await fetch(`${apiBase}/api/workflow/${sid}/analyze`, { method: "POST" });
    return res.json();
  }

  async function build() {
    if (!currentSession.value) return null;
    const sid = currentSession.value.session_id;
    const res = await fetch(`${apiBase}/api/workflow/${sid}/build`, { method: "POST" });
    return res.json();
  }

  async function rollback(targetStage: string) {
    if (!currentSession.value) return null;
    const sid = currentSession.value.session_id;
    const res = await fetch(`${apiBase}/api/workflow/${sid}/rollback/${targetStage}`, { method: "POST" });
    if (res.ok) {
      currentSession.value = await res.json();
    }
    return currentSession.value;
  }

  function getDownloadUrl() {
    if (!currentSession.value) return "";
    return `${apiBase}/api/workflow/${currentSession.value.session_id}/download`;
  }

  function getStageDownloadUrl(stage: string) {
    if (!currentSession.value) return "";
    return `${apiBase}/api/workflow/${currentSession.value.session_id}/download/stage/${stage}`;
  }

  function getFullPackageDownloadUrl() {
    if (!currentSession.value) return "";
    return `${apiBase}/api/workflow/${currentSession.value.session_id}/download/full`;
  }

  return { currentSession, sessionList, startSession, loadSession, approve, edit, validate, analyze, build, rollback, getDownloadUrl, getStageDownloadUrl, getFullPackageDownloadUrl, fetchBoards };
}
