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

        <!-- Device Data Tab -->
        <template v-if="activeTab === 'device'">
          <div class="space-y-1">
            <h2 class="text-xl font-bold">Device Data Import</h2>
            <p class="text-sm text-muted-foreground">Import pin-mux tables and peripheral data from vendor tools (CubeMX, SVD, CMSIS-Pack, ATDF).</p>
          </div>

          <!-- Auto-Discovery -->
          <div class="rounded-xl border bg-card p-4 space-y-3">
            <div class="flex items-center justify-between">
              <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Auto-Detect Installed SDKs</p>
              <button
                class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-all"
                @click="runAutoDiscovery"
              >
                <Search class="h-3 w-3" />
                Scan System
              </button>
            </div>
            <div v-if="discoveredTools.length" class="space-y-1">
              <div
                v-for="tool in discoveredTools"
                :key="tool.path"
                class="flex items-center justify-between rounded-lg bg-secondary/50 px-3 py-2"
              >
                <div class="flex items-center gap-2">
                  <span class="text-[10px] rounded-full bg-primary/10 text-primary px-2 py-0.5 font-medium">{{ tool.kind }}</span>
                  <span class="text-xs font-medium">{{ tool.name }}</span>
                  <span v-if="tool.vendor" class="text-[10px] text-muted-foreground">{{ tool.vendor }}</span>
                </div>
                <button
                  v-if="tool.importable"
                  class="rounded px-2 py-1 text-[10px] bg-primary text-primary-foreground hover:opacity-90 transition-all"
                  @click="devicePath = tool.path; listDevicesAtPath()"
                >
                  Use
                </button>
                <span v-else class="text-[10px] text-muted-foreground truncate max-w-[200px]">{{ tool.path }}</span>
              </div>
            </div>
            <p v-else class="text-xs text-muted-foreground">Click "Scan System" to detect installed SDKs and toolchains.</p>
          </div>

          <!-- Path Input + File Browser -->
          <div class="rounded-xl border bg-card p-4 space-y-4">
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">Source Path</label>
              <div class="flex gap-2">
                <input
                  v-model="devicePath"
                  class="flex-1 rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="C:/STM32CubeMX or path/to/device.svd"
                  @keydown.enter="listDevicesAtPath"
                />
                <button
                  class="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm hover:bg-accent transition-all"
                  @click="browseDir(devicePath || '')"
                >
                  <FolderSearch class="h-3.5 w-3.5" />
                  Browse
                </button>
                <button
                  class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all"
                  :disabled="!devicePath.trim() || deviceImporting"
                  @click="listDevicesAtPath"
                >
                  <Search v-if="!deviceImporting" class="h-3.5 w-3.5" />
                  <Loader2 v-else class="h-3.5 w-3.5 animate-spin" />
                  Scan
                </button>
              </div>
            </div>

            <!-- Directory Browser -->
            <Transition name="fade-slide">
              <div v-if="browseEntries.length" class="space-y-2">
                <div class="flex items-center justify-between">
                  <p class="text-[10px] text-muted-foreground font-mono truncate max-w-[400px]">{{ browsePath }}</p>
                  <button class="text-[10px] text-muted-foreground hover:text-foreground" @click="browseEntries = []">Close</button>
                </div>
                <div class="max-h-48 overflow-y-auto rounded-lg border bg-background p-1 space-y-0.5">
                  <button
                    v-for="entry in browseEntries"
                    :key="entry.path"
                    class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs hover:bg-accent transition-colors text-left"
                    @click="onBrowseClick(entry)"
                  >
                    <FolderSearch v-if="entry.type === 'directory' || entry.type === 'drive'" class="h-3 w-3 text-amber-500 shrink-0" />
                    <FileCode v-else class="h-3 w-3 text-sky-500 shrink-0" />
                    <span class="flex-1 truncate">{{ entry.name }}</span>
                    <span v-if="entry.size" class="text-[10px] text-muted-foreground">{{ (entry.size / 1024).toFixed(0) }}KB</span>
                  </button>
                </div>
              </div>
            </Transition>

            <!-- Available Devices -->
            <Transition name="fade-slide">
              <div v-if="deviceAvailable.length" class="space-y-2">
                <p class="text-xs font-medium text-muted-foreground">Available Devices ({{ deviceAvailable.length }})</p>
                <input
                  v-model="deviceFilter"
                  class="w-full rounded-lg border bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Filter devices…"
                />
                <div class="max-h-48 overflow-y-auto rounded-lg border bg-background p-2 space-y-1">
                  <button
                    v-for="dev in filteredDevices"
                    :key="dev"
                    class="flex w-full items-center gap-2 rounded px-2 py-1 text-xs hover:bg-accent transition-colors text-left"
                    :class="{ 'bg-primary/10 text-primary': deviceSelectedName === dev }"
                    @click="deviceSelectedName = dev"
                  >
                    <Cpu class="h-3 w-3 shrink-0" />
                    {{ dev }}
                  </button>
                </div>
                <button
                  class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all"
                  :disabled="!deviceSelectedName || deviceImporting"
                  @click="importDevice(deviceSelectedName)"
                >
                  <HardDrive v-if="!deviceImporting" class="h-3 w-3" />
                  <Loader2 v-else class="h-3 w-3 animate-spin" />
                  Import Selected
                </button>
              </div>
            </Transition>

            <!-- Import Result -->
            <Transition name="fade-slide">
              <div v-if="deviceImportResult" class="rounded-lg border border-green-500/30 bg-green-500/5 p-3 space-y-1">
                <p class="text-xs font-medium text-green-600 flex items-center gap-1.5">
                  <Check class="h-3.5 w-3.5" /> Import successful
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ deviceImportResult.device }} ({{ deviceImportResult.package || 'unknown package' }}) —
                  {{ deviceImportResult.pin_mux_count }} pin-mux entries,
                  {{ deviceImportResult.peripheral_count }} peripherals
                </p>
              </div>
            </Transition>
          </div>

          <!-- Imported Devices Table -->
          <div v-if="deviceImported.length" class="rounded-xl border bg-card overflow-hidden">
            <div class="border-b px-4 py-3">
              <p class="text-sm font-medium">Imported Devices ({{ deviceImported.length }})</p>
            </div>
            <div class="divide-y max-h-64 overflow-y-auto">
              <div v-for="dev in deviceImported" :key="dev.device" class="flex items-center justify-between px-4 py-2.5">
                <div>
                  <p class="text-xs font-medium">{{ dev.device }}</p>
                  <p class="text-[10px] text-muted-foreground">{{ dev.vendor }} · {{ dev.family }} · {{ dev.source_format }}</p>
                </div>
                <span class="text-[10px] text-muted-foreground rounded-full bg-secondary px-2 py-0.5">{{ dev.package || '—' }}</span>
              </div>
            </div>
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
                  v-if="isProfileActive(p)"
                  class="rounded-lg bg-green-500/10 text-green-600 border border-green-500/20 px-3 py-1.5 text-xs font-medium cursor-default"
                  disabled
                >
                  ✓ Active
                </button>
                <button
                  v-else
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

        <!-- Model Routing Tab -->
        <template v-if="activeTab === 'models'">
          <div class="space-y-1">
            <h2 class="text-xl font-bold">Model Routing</h2>
            <p class="text-sm text-muted-foreground">
              Route pipeline stages to different models. Leave blank to use the default deployment.
            </p>
          </div>

          <div v-if="stageModelConfig" class="space-y-4">
            <!-- Default model info -->
            <div class="rounded-xl border bg-card/50 p-4">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-xs font-medium">Default Model</div>
                  <div class="text-sm text-muted-foreground mt-0.5">
                    <span class="font-mono bg-accent rounded px-1.5 py-0.5 text-foreground">{{ stageModelConfig.default_model }}</span>
                    via <span class="capitalize">{{ stageModelConfig.provider }}</span>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <Transition name="fade">
                    <span v-if="modelSaved" class="flex items-center gap-1 text-xs text-emerald-400">
                      <Check class="h-3 w-3" /> Saved
                    </span>
                  </Transition>
                  <button
                    class="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all active:scale-[0.97]"
                    :disabled="modelSaving"
                    @click="saveStageModels"
                  >
                    <Loader2 v-if="modelSaving" class="h-3 w-3 animate-spin" />
                    Save
                  </button>
                </div>
              </div>
            </div>

            <!-- Stage grid -->
            <div class="rounded-xl border bg-card overflow-hidden">
              <div class="grid grid-cols-3 gap-0 text-[10px] text-muted-foreground uppercase tracking-wider px-4 py-2 border-b bg-accent/30">
                <span>Stage</span>
                <span>Model Override</span>
                <span>Effective Model</span>
              </div>
              <div class="divide-y">
                <div
                  v-for="stage in Object.keys(stageModelConfig.stages)"
                  :key="stage"
                  class="grid grid-cols-3 gap-0 items-center px-4 py-2 hover:bg-accent/10 transition-colors"
                >
                  <div>
                    <div class="text-xs font-medium">{{ stageLabels[stage] || stage }}</div>
                    <div class="text-[10px] text-muted-foreground font-mono">{{ stage }}</div>
                  </div>
                  <div>
                    <input
                      v-model="stageEdits[stage]"
                      class="w-full rounded border bg-background px-2 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-ring"
                      :placeholder="stageModelConfig.default_model"
                    />
                  </div>
                  <div class="text-xs font-mono text-muted-foreground pl-2">
                    {{ stageEdits[stage] || stageModelConfig.default_model }}
                  </div>
                </div>
              </div>
            </div>

            <div class="rounded-xl border bg-accent/20 p-3 text-xs text-muted-foreground space-y-1">
              <p><strong>Tip:</strong> Use cheaper models for simple stages to reduce cost.</p>
              <p>Example: Set <span class="font-mono">refiner</span>, <span class="font-mono">chat</span>, <span class="font-mono">review</span> to <span class="font-mono">gpt-4o-mini</span> and keep <span class="font-mono">codegen</span> on the default model.</p>
            </div>
          </div>
          <div v-else class="py-8 text-center text-xs text-muted-foreground">Loading model configuration…</div>
        </template>

        <!-- Cost Monitor Tab -->
        <template v-if="activeTab === 'cost'">
          <div class="space-y-1">
            <h2 class="text-xl font-bold">Cost Monitor</h2>
            <p class="text-sm text-muted-foreground">Track LLM token usage and estimated spend across sessions.</p>
          </div>
          <CostTracker />
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
import { ref, watch, onMounted, computed } from "vue";
import { ArrowLeft, Search, Loader2, Sparkles, Database, Upload, FolderSearch, FileCode, Settings2, Library, Trash2, Cpu, HardDrive, Check, DollarSign, Layers } from "@lucide/vue";
import { useSdkManager } from "~/composables/useSdkManager";
import { useRuntimeConfig } from "#app";

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

// Device Data tab state
const config = useRuntimeConfig();
const apiBase = config.public.apiBase as string;
const devicePath = ref("");
const deviceImporting = ref(false);
const deviceAvailable = ref<string[]>([]);
const deviceImported = ref<any[]>([]);
const deviceImportResult = ref<any>(null);
const deviceSelectedName = ref("");
const deviceFilter = ref("");
const browseEntries = ref<any[]>([]);
const browsePath = ref("");
const discoveredTools = ref<any[]>([]);

const filteredDevices = computed(() => {
  if (!deviceFilter.value) return deviceAvailable.value.slice(0, 100);
  const q = deviceFilter.value.toUpperCase();
  return deviceAvailable.value.filter(d => d.toUpperCase().includes(q)).slice(0, 100);
});

const tabs = [
  { id: "scan", label: "SDK Scanner", icon: FolderSearch },
  { id: "device", label: "Device Data", icon: Database },
  { id: "profile", label: "Active Profile", icon: FileCode },
  { id: "library", label: "Profile Library", icon: Library },
  { id: "reference", label: "Reference Analyzer", icon: Settings2 },
  { id: "models", label: "Model Routing", icon: Layers },
  { id: "cost", label: "Cost Monitor", icon: DollarSign },
];

// ─── Model-per-stage config ─────────────────────────────────────
interface StageModelConfig {
  default_model: string;
  provider: string;
  stages: Record<string, string | null>;
}

const stageModelConfig = ref<StageModelConfig | null>(null);
const stageEdits = ref<Record<string, string>>({});
const modelSaving = ref(false);
const modelSaved = ref(false);

const stageLabels: Record<string, string> = {
  refiner: "Requirements Refiner",
  hardware: "Hardware Assignment",
  software_arch: "Software Architecture",
  software_detailed: "Detailed Design",
  codegen: "Code Generation (main)",
  codegen_mock: "Code Generation (mocks)",
  codegen_test: "Code Generation (tests)",
  codegen_prod: "Code Generation (production)",
  review: "AI Review",
  fix_loop: "Compiler Fix Loop",
  chat: "Chat Assistant",
  profile_generation: "Profile Generator",
};

async function loadStageModels() {
  try {
    const res = await fetch(`${apiBase}/api/cost/stage-models`);
    if (res.ok) {
      stageModelConfig.value = await res.json();
      stageEdits.value = {};
      for (const [stage, model] of Object.entries(stageModelConfig.value!.stages)) {
        stageEdits.value[stage] = (model as string) || "";
      }
    }
  } catch {}
}

async function saveStageModels() {
  modelSaving.value = true;
  modelSaved.value = false;
  try {
    const res = await fetch(`${apiBase}/api/cost/stage-models`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stages: stageEdits.value }),
    });
    if (res.ok) {
      stageModelConfig.value = await res.json();
      modelSaved.value = true;
      setTimeout(() => { modelSaved.value = false; }, 2000);
    }
  } catch {}
  modelSaving.value = false;
}

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
  await refreshImportedDevices();
  await loadStageModels();
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

// Device Data functions
async function refreshImportedDevices() {
  try {
    const res = await fetch(`${apiBase}/api/sdk/device/imported`);
    const data = await res.json();
    deviceImported.value = data.devices || [];
  } catch { /* backend not reachable */ }
}

async function listDevicesAtPath() {
  if (!devicePath.value.trim()) return;
  deviceImporting.value = true;
  deviceAvailable.value = [];
  try {
    const res = await fetch(`${apiBase}/api/sdk/device/list-available`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: devicePath.value }),
    });
    const data = await res.json();
    deviceAvailable.value = data.devices || [];
  } catch { /* ignore */ }
  deviceImporting.value = false;
}

async function importDevice(deviceName: string = "") {
  deviceImporting.value = true;
  deviceImportResult.value = null;
  try {
    const res = await fetch(`${apiBase}/api/sdk/device/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: devicePath.value, device_name: deviceName || deviceSelectedName.value }),
    });
    deviceImportResult.value = await res.json();
    await refreshImportedDevices();
  } catch { /* ignore */ }
  deviceImporting.value = false;
}

async function browseDir(path: string) {
  try {
    const res = await fetch(`${apiBase}/api/sdk/browse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    const data = await res.json();
    browseEntries.value = data.entries || [];
    browsePath.value = data.path || "";
  } catch { /* ignore */ }
}

function onBrowseClick(entry: any) {
  if (entry.type === "directory" || entry.type === "drive") {
    browseDir(entry.path);
  } else {
    devicePath.value = entry.path;
    browseEntries.value = [];
    listDevicesAtPath();
  }
}

async function runAutoDiscovery() {
  try {
    const res = await fetch(`${apiBase}/api/sdk/discover`);
    const data = await res.json();
    discoveredTools.value = data.tools || [];
  } catch { /* ignore */ }
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
  await refreshProfiles();
}

async function doDeleteProfile(filename: string) {
  await deleteProfile(filename);
  await refreshProfiles();
}

function isProfileActive(p: any): boolean {
  if (!profile.value) return false;
  return profile.value.vendor === p.vendor && profile.value.sdk === p.sdk && profile.value.sdk_version === p.sdk_version;
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
