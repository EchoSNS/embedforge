/**
 * SDK Management API composable.
 */

import { ref } from "vue";
import { useRuntimeConfig } from "#app";

export function useSdkManager() {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;

  const scanning = ref(false);
  const generating = ref(false);
  const scanResult = ref<any>(null);
  const profile = ref<any>(null);
  const error = ref<string | null>(null);

  async function scanSdk(path: string) {
    scanning.value = true;
    error.value = null;
    try {
      const res = await fetch(`${apiBase}/api/sdk/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      if (!res.ok) throw new Error(await res.text());
      scanResult.value = await res.json();
    } catch (e: any) {
      error.value = e.message;
    } finally {
      scanning.value = false;
    }
  }

  async function generateProfile(sdkPath: string, vendorName: string, sdkName: string) {
    generating.value = true;
    error.value = null;
    try {
      const res = await fetch(`${apiBase}/api/sdk/generate-profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sdk_path: sdkPath, vendor_name: vendorName, sdk_name: sdkName }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      profile.value = data.profile;
    } catch (e: any) {
      error.value = e.message;
    } finally {
      generating.value = false;
    }
  }

  async function fetchProfile() {
    try {
      const res = await fetch(`${apiBase}/api/sdk/profile`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      profile.value = data.profile;
      return data;
    } catch (e: any) {
      error.value = e.message;
    }
  }

  async function updateProfile(profileData: any) {
    try {
      const res = await fetch(`${apiBase}/api/sdk/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: profileData }),
      });
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
    }
  }

  async function analyzeReference(path: string, profileName: string = "") {
    error.value = null;
    try {
      const res = await fetch(`${apiBase}/api/sdk/reference/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, profile_name: profileName }),
      });
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
    }
  }

  async function uploadReferenceFiles(files: FileList, profileName: string = "") {
    error.value = null;
    const formData = new FormData();
    for (const f of files) {
      formData.append("files", f);
    }
    const url = profileName
      ? `${apiBase}/api/sdk/reference/upload?profile_name=${encodeURIComponent(profileName)}`
      : `${apiBase}/api/sdk/reference/upload`;
    try {
      const res = await fetch(url, { method: "POST", body: formData });
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
    }
  }

  // ─── Profile Library ──────────────────────────────────────────────────

  async function listProfiles() {
    try {
      const res = await fetch(`${apiBase}/api/sdk/profiles`);
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
      return [];
    }
  }

  async function saveProfileToLibrary(name: string, profileData: any) {
    try {
      const res = await fetch(`${apiBase}/api/sdk/profiles/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, profile: profileData }),
      });
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
    }
  }

  async function activateProfile(filename: string) {
    try {
      const res = await fetch(`${apiBase}/api/sdk/profiles/activate/${encodeURIComponent(filename)}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
    }
  }

  async function deleteProfile(filename: string) {
    try {
      const res = await fetch(`${apiBase}/api/sdk/profiles/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
    }
  }

  async function listProfileReferences(profileName: string) {
    try {
      const res = await fetch(`${apiBase}/api/sdk/reference/${encodeURIComponent(profileName)}`);
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
      return [];
    }
  }

  async function deleteProfileReference(profileName: string, filename: string) {
    try {
      const res = await fetch(`${apiBase}/api/sdk/reference/${encodeURIComponent(profileName)}/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } catch (e: any) {
      error.value = e.message;
    }
  }

  return {
    scanning,
    generating,
    scanResult,
    profile,
    error,
    scanSdk,
    generateProfile,
    fetchProfile,
    updateProfile,
    analyzeReference,
    uploadReferenceFiles,
    listProfiles,
    saveProfileToLibrary,
    activateProfile,
    deleteProfile,
    listProfileReferences,
    deleteProfileReference,
  };
}
