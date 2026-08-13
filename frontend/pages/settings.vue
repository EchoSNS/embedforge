<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar with back link -->
    <aside class="flex w-60 flex-col border-r bg-card/30 backdrop-blur-sm">
      <div class="flex h-14 items-center border-b px-4">
        <NuxtLink to="/" class="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft class="h-3 w-3" />
          Back to Workspace
        </NuxtLink>
      </div>
      <nav class="flex-1 p-3 space-y-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs transition-all duration-200"
          :class="activeTab === tab.id ? 'bg-primary/10 text-primary font-medium' : 'text-muted-foreground hover:bg-accent hover:text-foreground'"
          @click="activeTab = tab.id"
        >
          <component :is="tab.icon" class="h-3.5 w-3.5" />
          {{ tab.label }}
        </button>
      </nav>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <div class="mx-auto max-w-3xl space-y-6">

        <!-- SDK Scanner Tab -->
        <template v-if="activeTab === 'scan'">
          <div class="space-y-1">
            <h2 class="text-xl font-bold">SDK Scanner</h2>
            <p class="text-sm text-muted-foreground">Point to a vendor SDK directory to extract API metadata automatically.</p>
          </div>

          <div class="rounded-xl border bg-card p-4 space-y-4">
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">SDK Path (local directory)</label>
              <div class="flex gap-2">
                <input
                  v-model="sdkPath"
                  class="flex-1 rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="C:/STM32CubeF4/Drivers/STM32F4xx_HAL_Driver/Inc"
                />
                <button
                  class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all active:scale-[0.97]"
                  :disabled="!sdkPath.trim() || scanning"
                  @click="runScan"
                >
                  <Search v-if="!scanning" class="h-3.5 w-3.5" />
                  <Loader2 v-else class="h-3.5 w-3.5 animate-spin" />
                  {{ scanning ? 'Scanning…' : 'Scan' }}
                </button>
              </div>
            </div>

            <!-- Scan Results -->
            <Transition name="fade-slide">
              <div v-if="scanResult" class="space-y-3 pt-2">
                <div class="flex flex-wrap gap-2">
                  <div class="rounded-lg bg-secondary px-3 py-1.5 text-xs">
                    <span class="text-muted-foreground">Headers:</span>
                    <span class="ml-1 font-medium">{{ scanResult.headers_scanned }}</span>
                  </div>
                  <div class="rounded-lg bg-secondary px-3 py-1.5 text-xs">
                    <span class="text-muted-foreground">Functions:</span>
                    <span class="ml-1 font-medium">{{ scanResult.functions_count }}</span>
                  </div>
                  <div class="rounded-lg bg-secondary px-3 py-1.5 text-xs">
                    <span class="text-muted-foreground">Types:</span>
                    <span class="ml-1 font-medium">{{ scanResult.types_count }}</span>
                  </div>
                </div>

                <!-- Detected Peripherals -->
                <div v-if="scanResult.peripherals_detected?.length" class="space-y-1.5">
                  <p class="text-xs font-medium text-muted-foreground">Detected Peripherals</p>
                  <div class="flex flex-wrap gap-1.5">
                    <span
                      v-for="p in scanResult.peripherals_detected"
                      :key="p"
                      class="rounded-full bg-primary/10 text-primary px-2.5 py-0.5 text-xs font-medium"
                    >{{ p }}</span>
                  </div>
                </div>

                <!-- Generate Profile Button -->
                <div class="pt-2 border-t">
                  <div class="flex gap-2 items-end">
                    <div class="flex-1 space-y-1">
                      <label class="text-xs text-muted-foreground">Vendor Name</label>
                      <input v-model="vendorName" class="w-full rounded-lg border bg-background px-3 py-1.5 text-xs" placeholder="e.g. STMicroelectronics" />
                    </div>
                    <div class="flex-1 space-y-1">
                      <label class="text-xs text-muted-foreground">SDK Name</label>
                      <input v-model="sdkName" class="w-full rounded-lg border bg-background px-3 py-1.5 text-xs" placeholder="e.g. STM32 HAL" />
                    </div>
                    <button
                      class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all"
                      :disabled="generating"
                      @click="runGenerate"
                    >
                      <Sparkles v-if="!generating" class="h-3 w-3" />
                      <Loader2 v-else class="h-3 w-3 animate-spin" />
                      {{ generating ? 'Generating…' : 'Generate Profile' }}
                    </button>
                  </div>
                </div>
              </div>
            </Transition>
          </div>
        </template>

        <!-- Profile Viewer/Editor Tab -->
        <template v-if="activeTab === 'profile'">
          <div class="space-y-1">
            <h2 class="text-xl font-bold">Capability Profile</h2>
            <p class="text-sm text-muted-foreground">View and edit the active SDK capability profile used by the AI pipeline.</p>
          </div>

          <div v-if="!profile" class="rounded-xl border border-dashed bg-card p-8 text-center space-y-2">
            <Database class="h-8 w-8 mx-auto text-muted-foreground" />
            <p class="text-sm text-muted-foreground">No profile loaded. Scan an SDK first or load the active plugin's profile.</p>
            <button class="rounded-lg bg-primary px-4 py-2 text-xs text-primary-foreground" @click="loadProfile">Load Active Profile</button>
          </div>

          <div v-else class="rounded-xl border bg-card overflow-hidden">
            <div class="flex items-center justify-between border-b px-4 py-3">
              <div>
                <p class="text-sm font-medium">{{ profile.vendor }} — {{ profile.sdk }}</p>
                <p class="text-xs text-muted-foreground">v{{ profile.sdk_version }}</p>
              </div>
              <div class="flex gap-2">
                <button
                  class="rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
                  @click="saveProfile"
                >
                  Save Changes
                </button>
                <button
                  class="rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
                  @click="saveToLibrary"
                >
                  Save to Library
                </button>
              </div>
            </div>
            <div class="p-4">
              <textarea
                v-model="profileJson"
                class="w-full h-96 rounded-lg border bg-background p-3 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                spellcheck="false"
              />
            </div>
          </div>
        </template>

        <!-- Profile Library Tab -->
        <template v-if="activeTab === 'library'">
          <div class="space-y-1">
            <h2 class="text-xl font-bold">Profile Library</h2>
            <p class="text-sm text-muted-foreground">Manage saved profiles from different vendor SDKs. Activate the one you want to use.</p>
          </div>

          <div v-if="!profilesList.length" class="rounded-xl border border-dashed bg-card p-8 text-center space-y-2">
            <Library class="h-8 w-8 mx-auto text-muted-foreground" />
            <p class="text-sm text-muted-foreground">No profiles saved yet. Scan an SDK and generate a profile first.</p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="p in profilesList"
              :key="p.filename"
              class="rounded-xl border bg-card p-4 flex items-center justify-between hover:border-primary/30 transition-colors"
            >
              <div class="flex-1">
                <p class="text-sm font-medium">{{ p.vendor }} — {{ p.sdk }}</p>
                <div class="flex gap-3 mt-1">
                  <span class="text-xs text-muted-foreground">{{ p.sdk_version }}</span>
                  <span class="text-xs text-muted-foreground">{{ p.peripherals_count }} peripherals</span>
                  <span class="text-xs text-muted-foreground">{{ p.references_count || 0 }} references</span>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <button
                  class="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 transition-all"
                  @click="doActivateProfile(p.filename)"
                >
                  Activate
                </button>
                <button
                  class="rounded-lg border px-3 py-1.5 text-xs text-destructive hover:bg-destructive/5 transition-colors"
                  @click="doDeleteProfile(p.filename)"
                >
                  <Trash2 class="h-3 w-3" />
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- Reference Analyzer Tab -->
        <template v-if="activeTab === 'reference'">
          <div class="space-y-1">
            <h2 class="text-xl font-bold">Reference Analyzer</h2>
            <p class="text-sm text-muted-foreground">Upload or point to existing C projects. References are tied to a profile to avoid cross-vendor contamination.</p>
          </div>

          <div class="rounded-xl border bg-card p-4 space-y-4">
            <!-- Profile selector for scoping -->
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">Attach to Profile (optional)</label>
              <select
                v-model="refProfileName"
                class="w-full rounded-lg border bg-background p-2 text-xs focus:ring-2 focus:ring-ring focus:outline-none"
              >
                <option value="">None (unscoped)</option>
                <option v-for="p in profilesList" :key="p.filename" :value="p.filename.replace('.yaml', '')">
                  {{ p.vendor }} — {{ p.sdk }}
                </option>
              </select>
            </div>

            <!-- Path-based analysis -->
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">Project Path</label>
              <div class="flex gap-2">
                <input
                  v-model="refPath"
                  class="flex-1 rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="C:/Projects/my-stm32-project/Src"
                />
                <button
                  class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all"
                  :disabled="!refPath.trim()"
                  @click="runRefAnalysis"
                >
                  Analyze
                </button>
              </div>
            </div>

            <!-- File Upload -->
            <div class="border-t pt-4 space-y-2">
              <label class="text-xs font-medium text-muted-foreground">Or upload .c/.h files</label>
              <div
                class="flex items-center justify-center rounded-lg border-2 border-dashed p-6 cursor-pointer hover:border-primary/40 transition-colors"
                @click="fileInput?.click()"
                @dragover.prevent
                @drop.prevent="handleDrop"
              >
                <div class="text-center space-y-1">
                  <Upload class="h-6 w-6 mx-auto text-muted-foreground" />
                  <p class="text-xs text-muted-foreground">Drop .c/.h files here or click to browse</p>
                </div>
              </div>
              <input ref="fileInput" type="file" multiple accept=".c,.h" class="hidden" @change="handleFileSelect" />
            </div>

            <!-- Saved references for selected profile -->
            <Transition name="fade-slide">
              <div v-if="refProfileName && profileRefs.length" class="border-t pt-4 space-y-2">
                <p class="text-xs font-medium text-muted-foreground">Saved References for this Profile</p>
                <div v-for="r in profileRefs" :key="r.filename" class="flex items-center justify-between rounded-lg bg-secondary/50 px-3 py-2 text-xs">
                  <div>
                    <span class="font-medium">{{ r.filename }}</span>
                    <span class="text-muted-foreground ml-2">{{ r.files_analyzed }} files · {{ r.functions_count }} functions</span>
                  </div>
                  <button class="text-destructive hover:text-destructive/80" @click="doDeleteRef(r.filename)">
                    <Trash2 class="h-3 w-3" />
                  </button>
                </div>
              </div>
            </Transition>

            <!-- Results -->
            <Transition name="fade-slide">
              <div v-if="refResult" class="border-t pt-4 space-y-2">
                <p class="text-xs font-medium">Analysis Results</p>
                <div class="flex flex-wrap gap-2">
                  <div class="rounded-lg bg-secondary px-3 py-1.5 text-xs">{{ refResult.files_analyzed }} files</div>
                  <div class="rounded-lg bg-secondary px-3 py-1.5 text-xs">{{ refResult.functions_defined?.length || 0 }} functions</div>
                  <div class="rounded-lg bg-secondary px-3 py-1.5 text-xs">{{ refResult.functions_called?.length || 0 }} SDK calls</div>
                </div>
                <div v-if="refResult.saved_to" class="text-xs text-primary">Saved to: {{ refResult.saved_to }}</div>
                <pre class="rounded-lg bg-secondary/50 p-3 text-xs font-mono max-h-48 overflow-auto">{{ JSON.stringify(refResult.patterns, null, 2) }}</pre>
              </div>
            </Transition>
          </div>
        </template>

        <!-- Activity Log (always visible) -->
        <ActivityLog />

        <!-- Error display -->
        <div v-if="error" class="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {{ error }}
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { ArrowLeft, Search, Loader2, Sparkles, Database, Upload, FolderSearch, FileCode, Settings2, Library, Trash2 } from "lucide-vue-next";
import { useSdkManager } from "~/composables/useSdkManager";

const {
  scanning, generating, scanResult, profile, error,
  scanSdk, generateProfile, fetchProfile, updateProfile, analyzeReference, uploadReferenceFiles,
  listProfiles, saveProfileToLibrary, activateProfile, deleteProfile,
  listProfileReferences, deleteProfileReference,
} = useSdkManager();

const activeTab = ref("scan");
const sdkPath = ref("");
const vendorName = ref("");
const sdkName = ref("");
const refPath = ref("");
const refProfileName = ref("");
const refResult = ref<any>(null);
const profileJson = ref("");
const profilesList = ref<any[]>([]);
const profileRefs = ref<any[]>([]);
const fileInput = ref<HTMLInputElement | null>(null);

const tabs = [
  { id: "scan", label: "SDK Scanner", icon: FolderSearch },
  { id: "profile", label: "Active Profile", icon: FileCode },
  { id: "library", label: "Profile Library", icon: Library },
  { id: "reference", label: "Reference Analyzer", icon: Settings2 },
];

watch(profile, (p) => {
  if (p) profileJson.value = JSON.stringify(p, null, 2);
});

watch(refProfileName, async (name) => {
  if (name) profileRefs.value = await listProfileReferences(name);
  else profileRefs.value = [];
});

onMounted(async () => {
  await loadProfile();
  await refreshProfiles();
});

async function loadProfile() {
  await fetchProfile();
}

async function refreshProfiles() {
  profilesList.value = await listProfiles();
}

async function runScan() {
  await scanSdk(sdkPath.value);
}

async function runGenerate() {
  await generateProfile(sdkPath.value, vendorName.value, sdkName.value);
  await refreshProfiles();
}

async function saveProfile() {
  try {
    const data = JSON.parse(profileJson.value);
    await updateProfile(data);
  } catch { /* invalid JSON */ }
}

async function saveToLibrary() {
  try {
    const data = JSON.parse(profileJson.value);
    const name = `${data.vendor || "unknown"}_${data.sdk || "sdk"}`.toLowerCase().replace(/\s+/g, "_");
    await saveProfileToLibrary(name, data);
    await refreshProfiles();
  } catch { /* invalid JSON */ }
}

async function doActivateProfile(filename: string) {
  await activateProfile(filename);
  await loadProfile();
}

async function doDeleteProfile(filename: string) {
  await deleteProfile(filename);
  await refreshProfiles();
}

async function runRefAnalysis() {
  refResult.value = await analyzeReference(refPath.value, refProfileName.value);
  if (refProfileName.value) profileRefs.value = await listProfileReferences(refProfileName.value);
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement;
  if (input.files?.length) uploadFiles(input.files);
}

function handleDrop(e: DragEvent) {
  if (e.dataTransfer?.files.length) uploadFiles(e.dataTransfer.files);
}

async function uploadFiles(files: FileList) {
  refResult.value = await uploadReferenceFiles(files, refProfileName.value);
  if (refProfileName.value) profileRefs.value = await listProfileReferences(refProfileName.value);
}

async function doDeleteRef(filename: string) {
  await deleteProfileReference(refProfileName.value, filename);
  profileRefs.value = await listProfileReferences(refProfileName.value);
}
</script>
