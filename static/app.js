import * as api from "./js/api.js";
import { $ , createUi } from "./js/ui.js?v=20261029_flow_steps";
import { createSettings } from "./js/settings.js?v=20261030_defaults";
import { createStoryView } from "./js/story-view.js?v=20261029_flow_steps";
import { createProjectStore } from "./js/project-store.js?v=20261029_theme_gate";
import { createReferenceAssets } from "./js/reference-assets.js";
import { createWorkflow } from "./js/workflow.js?v=20261029_ux_pass4";
import { createThemeWorkflow } from "./js/workflow-theme.js?v=20260702_theme_direction_fix";
import { hasShotImage } from "./js/workflow-utils.js?v=20261029_ux_pass4";

const ui = createUi();
const { els } = ui;

const state = {
  activeTab: "theme",
  selectedShots: new Set(),
  saveTimer: 0,
  restoringProject: false,
  currentProjectId: "",
  imageGenerationActive: false,
  activeImageJobs: new Map(),
  imageJobPollers: new Map(),
  imageJobPollingToken: 0,
  activeAutoPipelineJob: null,
  autoPipelineContinuous: false,
  autoPipelineLoopRunning: false,
  autoPipelinePlaybackToken: 0,
  projectSaveQueue: Promise.resolve(),
  referenceCollectionId: "",
  autoReferenceEnabled: false,
};

let projectStore;
let shotClickTimer = 0;

const layoutKeys = {
  sidebar: "video-workbench.sidebarCollapsed",
  imagePrompt: "video-workbench.imagePromptExpanded",
};

function on(target, type, handler, options) {
  const element = typeof target === "string" ? $(target) : target;
  element?.addEventListener(type, handler, options);
  return element;
}

function onEach(ids, type, handler, options) {
  for (const id of ids) on(id, type, handler, options);
}

function readLayoutFlag(key, fallback = false) {
  try {
    const value = window.localStorage.getItem(key);
    return value === null ? fallback : value === "1";
  } catch {
    return fallback;
  }
}

function writeLayoutFlag(key, value) {
  try {
    window.localStorage.setItem(key, value ? "1" : "0");
  } catch {
    // Local storage can be unavailable in restricted browser modes.
  }
}

function setSidebarCollapsed(collapsed, persist = true) {
  document.querySelector(".app-frame")?.classList.toggle("sidebar-collapsed", collapsed);
  $("sidebarToggle")?.setAttribute("aria-pressed", String(collapsed));
  $("sidebarToggle")?.setAttribute("aria-label", collapsed ? "展开侧边栏" : "收起侧边栏");
  if (persist) writeLayoutFlag(layoutKeys.sidebar, collapsed);
}

function setImagePromptExpanded(expanded, persist = true) {
  const panel = $("imagePromptPanel");
  $("tab-image")?.classList.toggle("image-prompt-collapsed", !expanded);
  panel?.classList.toggle("is-collapsed", !expanded);
  panel?.setAttribute("aria-hidden", String(!expanded));
  const button = $("toggleImagePrompt");
  if (button) {
    button.setAttribute("aria-expanded", String(expanded));
    button.textContent = expanded ? "收起提示词" : "图片提示词";
  }
  if (persist) writeLayoutFlag(layoutKeys.imagePrompt, expanded);
}

function restoreLayoutPrefs() {
  setSidebarCollapsed(readLayoutFlag(layoutKeys.sidebar), false);
  setImagePromptExpanded(readLayoutFlag(layoutKeys.imagePrompt, false), false);
}

function updatePreviewAspect() {
  const panel = els.preview?.closest(".preview-panel");
  if (!panel) return;
  panel.classList.remove("landscape", "portrait", "square");
  const width = Number(els.preview.videoWidth || 0);
  const height = Number(els.preview.videoHeight || 0);
  if (!width || !height) return;
  const diff = Math.abs(width - height) / Math.max(width, height);
  if (diff < 0.08) {
    panel.classList.add("square");
  } else if (width > height) {
    panel.classList.add("landscape");
  } else {
    panel.classList.add("portrait");
  }
}

function selectedShotIndexes() {
  return Array.from(state.selectedShots).sort((a, b) => a - b);
}

function setSelectedShots(indexes) {
  const values = indexes instanceof Set ? Array.from(indexes) : Array.isArray(indexes) ? indexes : [];
  state.selectedShots = new Set(values.map(Number).filter((index) => Number.isInteger(index) && index >= 0));
}

function toggleSelectedShot(index) {
  const shotIndex = Number(index);
  if (!Number.isInteger(shotIndex) || shotIndex < 0) return;
  if (state.selectedShots.has(shotIndex)) {
    state.selectedShots.delete(shotIndex);
  } else {
    state.selectedShots.add(shotIndex);
  }
  storyView.updateSelection({ persist: true });
}

function openImagePreviewFromThumb(thumb) {
  const img = thumb?.querySelector?.("img");
  const modal = $("imagePreviewModal");
  const preview = $("imagePreviewFull");
  if (!img?.src || !modal || !preview) return;
  preview.src = img.src;
  modal.hidden = false;
}

function closeImagePreview() {
  const modal = $("imagePreviewModal");
  const preview = $("imagePreviewFull");
  if (!modal) return;
  modal.hidden = true;
  if (preview) preview.removeAttribute("src");
}

function escapeTextareaValue(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function closeShotPromptEditor(editor, save = true) {
  if (!editor?.isConnected) return;
  const index = Number(editor.dataset.shotPromptEditor);
  if (save && Number.isInteger(index)) {
    storyView.updateShotImagePrompt(index, editor.value);
  } else {
    storyView.renderShotGrid();
  }
}

function openShotPromptEditor(promptNode) {
  const index = Number(promptNode?.dataset.editShotPrompt);
  if (!Number.isInteger(index)) return;
  const value = storyView.getShotImagePrompt(index);
  promptNode.innerHTML = `<textarea class="shot-prompt-editor" data-shot-prompt-editor="${index}" aria-label="镜头 ${index + 1} 图片提示词">${escapeTextareaValue(value)}</textarea>`;
  const editor = promptNode.querySelector("textarea");
  if (!editor) return;
  editor.focus();
  editor.setSelectionRange(editor.value.length, editor.value.length);
}

function applyTtsPreset() {
  if (els.ttsProvider?.value !== "edge") return;
  const option = els.ttsPreset?.selectedOptions?.[0];
  if (!option?.dataset?.voice || !option?.dataset?.rate) return;
  els.voice.value = option.dataset.voice;
  els.rate.value = option.dataset.rate;
}

// 没有分镜、或者所有镜头都已经有图时，批量生图只会弹出一条红色报错，
// 不如直接置灰并把原因写在 title 里。
function syncContentButtons({ shotCount, missingCount }) {
  const busy = typeof ui.isBusy === "function" && ui.isBusy();
  // 主题策划底部的「进入文案生成」：主题和主题介绍都填了才算准备好，
  // 否则进到文案工作台只有空白字段，按钮先置灰并说明缺哪一项。
  const topic = String(els.topic?.value || "").trim();
  const themeIntro = String(els.themeIntro?.value || "").trim();
  const goCopyButton = $("goCopyFromTheme");
  if (goCopyButton) {
    goCopyButton.disabled = busy || !topic || !themeIntro;
    goCopyButton.title = !topic
      ? "请先填写或生成主题"
      : !themeIntro
        ? "请先填写或生成主题介绍"
        : `以「${topic}」进入文案生成`;
  }
  const hasShots = shotCount > 0;
  const generateButton = $("generateImages");
  if (generateButton) {
    generateButton.disabled = busy || !hasShots || missingCount === 0;
    generateButton.title = !hasShots
      ? "还没有分镜，先去「文案工作台」拆分分镜"
      : missingCount === 0
        ? "所有镜头都已有图片，可在分镜图上选中后重抽"
        : `为 ${missingCount} 个还没有图的镜头批量生成图片`;
  }
  const redrawButton = $("redrawSelected");
  if (redrawButton) {
    const selected = state.selectedShots.size;
    redrawButton.disabled = busy || !hasShots || !selected;
    redrawButton.title = !hasShots
      ? "还没有分镜，先去「文案工作台」拆分分镜"
      : selected
        ? `重抽已选的 ${selected} 个镜头`
        : "先在分镜图上点选要重抽的镜头";
  }
  // 文案工作台底部的「去生成分镜图」：没有分镜时点进去只会看到空列表，直接置灰。
  const goImagesButton = $("goStoryboardImages");
  if (goImagesButton) {
    goImagesButton.disabled = busy || !hasShots;
    goImagesButton.title = hasShots
      ? `前往分镜工作台，为 ${shotCount} 个镜头生成分镜图`
      : "还没有分镜，先完成第 3 步「拆分分镜」";
  }
}

// 顶部步骤条按实际进度点亮：有文案才算「生成文案」完成，有分镜才算「拆分分镜」完成，
// 所有镜头都有图才算「生成分镜图」完成，出片后才算「生成视频」完成。
// 之前是写死在 HTML 里的，所以打开已有项目也一直停在第二步。
function syncWorkflowSteps() {
  const topic = String(els.topic?.value || "").trim();
  const copy = String(els.copyOutput?.value || "").trim();
  const shots = storyView.readOrNull()?.shots || [];
  const shotCount = shots.length;
  const missingCount = shots.filter((shot) => !hasShotImage(shot)).length;
  syncContentButtons({ shotCount, missingCount });
  const items = document.querySelectorAll("#tab-copy .workflow-steps li");
  if (!items.length) return;
  const imagesReady = shotCount > 0 && missingCount === 0;
  const hasVideo = Boolean(els.preview?.getAttribute("src"));
  const states = [
    topic || copy ? "done" : "active",
    copy ? "done" : topic ? "active" : "",
    shotCount ? "done" : copy ? "active" : "",
    imagesReady ? "done" : shotCount ? "active" : "",
    hasVideo ? "done" : imagesReady ? "active" : "",
  ];
  items.forEach((item, index) => {
    const state = states[index] || "";
    item.classList.toggle("done", state === "done");
    item.classList.toggle("active", state === "active");
    if (state === "active") item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
}

// 步骤条点击跳转：前 3 步都在文案工作台内部，滚到对应区块；第 4、5 步切到其它页面。
function scrollToStageAnchor(id) {
  const target = document.getElementById(id);
  if (!target) return;
  const stage = document.querySelector(".stage");
  if (!stage) {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  const offset = target.getBoundingClientRect().top - stage.getBoundingClientRect().top - 16;
  stage.scrollTo({ top: stage.scrollTop + offset, behavior: "smooth" });
}

function navigateToStep(item) {
  if (!item) return;
  const tab = item.dataset.stepTab || "copy";
  setActiveTab(tab);
  const target = item.dataset.stepTarget;
  // setActiveTab 会把 stage 滚回顶部，等新标签页布局生效后再定位区块。
  if (tab === "copy" && target) {
    requestAnimationFrame(() => scrollToStageAnchor(target));
  }
}

function setActiveTab(tab) {
  state.activeTab = tab;
  ui.setTab(tab);
  if (tab === "image") storyView.renderShotGrid();
  // 上一个标签页可能已经滚到很下面，不归零的话新页面会停在中间
  const stage = document.querySelector(".stage");
  if (stage) stage.scrollTop = 0;
  syncWorkflowSteps();
}

function syncThemeMirrors() {
  if (els.topicMirror) els.topicMirror.textContent = els.topic.value || "未填写主题";
  if (els.themeIntroMirror) els.themeIntroMirror.textContent = els.themeIntro?.value.trim() || "未填写主题介绍";
}

function activeImageJobForShot(index) {
  const shotIndex = Number(index);
  if (!Number.isInteger(shotIndex) || !(state.activeImageJobs instanceof Map)) return null;
  const job = state.activeImageJobs.get(shotIndex);
  if (!job) return null;
  if (state.currentProjectId && job.projectId && job.projectId !== state.currentProjectId) return null;
  return job;
}

function persistAndSave({ promptMeta = false, themeMirror = false } = {}) {
  if (themeMirror) syncThemeMirrors();
  settings.persist();
  if (promptMeta) storyView.updatePromptMeta();
  projectStore.scheduleSave();
}

function promptMetaAndSave() {
  storyView.updatePromptMeta();
  projectStore.scheduleSave();
}

const settings = createSettings({ els });

const storyView = createStoryView({
  els,
  getSelectedShots: () => state.selectedShots,
  setSelectedShots,
  getActiveTab: () => state.activeTab,
  getActiveImageJob: activeImageJobForShot,
  getActiveImageStatus: (index) => activeImageJobForShot(index)?.status || "",
  onStoryChanged: () => {
    projectStore?.scheduleSave();
    syncWorkflowSteps();
  },
});

projectStore = createProjectStore({
  els,
  ui,
  api,
  storyView,
  state,
  settings,
  setActiveTab,
  onStateApplied: () => syncWorkflowSteps(),
});

state.referenceAssets = createReferenceAssets({
  els,
  ui,
  api,
  state,
  projectStore,
  storyView,
});

const workflowContext = {
  els,
  ui,
  api,
  settings,
  storyView,
  projectStore,
  state,
  setActiveTab,
};

const workflow = createWorkflow(workflowContext);

if (typeof workflow.generateThemeIdeas !== "function") {
  Object.assign(workflow, createThemeWorkflow(workflowContext));
}

// setBusy(false) 只负责把按钮恢复成可点；可用性取决于内容的那几个（继续拆分镜、
// 步骤条）在这里统一重算，免得某个操作忘了同步。
ui.onIdle(() => {
  workflow.syncContinueButton?.();
  syncWorkflowSteps();
});

function runThemeIdeas(options = {}) {
  if (typeof workflow.generateThemeIdeas !== "function") {
    ui.setStatus("AI 出方向模块未加载，请刷新页面", "error");
    if (els.result) els.result.textContent = "AI 出方向模块未加载：workflow.generateThemeIdeas 不存在。";
    return;
  }
  workflow.generateThemeIdeas(options);
}

function bindEvents() {
  document.addEventListener("click", (event) => {
    const tabButton = event.target.closest("[data-tab]");
    if (tabButton) setActiveTab(tabButton.dataset.tab);

    const gotoButton = event.target.closest("[data-goto-tab]");
    if (gotoButton) {
      setActiveTab(gotoButton.dataset.gotoTab);
      return;
    }

    const stepItem = event.target.closest("#tab-copy .workflow-steps li[data-step]");
    if (stepItem) {
      navigateToStep(stepItem);
      return;
    }

    const openProjectButton = event.target.closest("[data-open-project]");
    if (openProjectButton) {
      workflow.clearThemeIdeas?.();
      workflow.clearImageJobPollers?.();
      projectStore.activate(openProjectButton.dataset.openProject).then(() => {
        workflow.restoreActiveImageJobs?.();
        workflow.restoreActiveAutoPipelineJobs?.();
        workflow.syncContinueButton?.();
        syncWorkflowSteps();
      });
      return;
    }

    const deleteProjectButton = event.target.closest("[data-delete-project]");
    if (deleteProjectButton) {
      workflow.clearThemeIdeas?.();
      if (deleteProjectButton.dataset.deleteProject === state.currentProjectId) {
        workflow.clearImageJobPollers?.();
      }
      projectStore.remove(deleteProjectButton.dataset.deleteProject);
      return;
    }

    const aiPromptButton = event.target.closest("[data-ai-shot-prompt]");
    if (aiPromptButton) {
      workflow.improveShotImagePrompt(Number(aiPromptButton.dataset.aiShotPrompt));
      return;
    }

    const themeIdeaButton = event.target.closest("[data-theme-idea-action]");
    if (themeIdeaButton) {
      const index = Number(themeIdeaButton.dataset.themeIdeaIndex);
      const action = themeIdeaButton.dataset.themeIdeaAction;
      if (action === "adopt") workflow.adoptThemeIdea(index);
      if (action === "refine") runThemeIdeas({ refineIndex: index });
      if (action === "reroll") runThemeIdeas({ rerollIndex: index });
      return;
    }

    const redrawButton = event.target.closest("[data-redraw-shot]");
    if (redrawButton) {
      if (redrawButton.disabled) return;
      workflow.redrawShot(Number(redrawButton.dataset.redrawShot));
      return;
    }

    const setCoverButton = event.target.closest("[data-set-cover-shot]");
    if (setCoverButton) {
      workflow.setShotAsCover(Number(setCoverButton.dataset.setCoverShot));
      return;
    }

    const selectButton = event.target.closest("[data-select-shot]");
    if (selectButton) {
      clearTimeout(shotClickTimer);
      shotClickTimer = window.setTimeout(() => {
        toggleSelectedShot(selectButton.dataset.selectShot);
        shotClickTimer = 0;
      }, 180);
    }
  });

  document.addEventListener("dblclick", (event) => {
    if (event.target.closest("[data-ai-shot-prompt]")) return;
    const promptNode = event.target.closest("[data-edit-shot-prompt]");
    if (promptNode) {
      event.preventDefault();
      event.stopPropagation();
      openShotPromptEditor(promptNode);
      return;
    }
    if (event.target.closest("[data-redraw-shot]")) return;
    const thumb = event.target.closest("[data-select-shot]");
    if (!thumb) return;
    clearTimeout(shotClickTimer);
    shotClickTimer = 0;
    openImagePreviewFromThumb(thumb);
  });

  on("loadExample", "click", () => {
    workflow.clearImageJobPollers?.();
    workflow.loadExample();
  });
  on("startAutoPipeline", "click", workflow.startAutoPipeline);
  on("cancelAutoPipeline", "click", workflow.cancelAutoPipeline);
  on("generateThemeIdeas", "click", () => runThemeIdeas());
  on("rerollThemeIdeas", "click", () => runThemeIdeas({ reroll: true }));
  on("generateTheme", "click", workflow.generateTheme);
  on("rerollTheme", "click", () => workflow.generateTheme({ reroll: true }));
  on("reviseTheme", "click", workflow.reviseTheme);
  on("goCopyFromTheme", "click", () => setActiveTab("copy"));
  on("goStoryboardImages", "click", () => setActiveTab("image"));
  on("goVideoFromImage", "click", () => setActiveTab("video"));
  on("generate", "click", workflow.generateStory);
  on("generateCopy", "click", workflow.generateCopy);
  on("continueToStoryboard", "click", workflow.buildStoryboardFromCopy);
  on("generateImages", "click", workflow.generateImagesParallel);
  on("redrawSelected", "click", () => workflow.redrawSelectedShots(selectedShotIndexes()));
  on("refreshGallery", "click", storyView.renderShotGrid);
  on("validate", "click", () => storyView.validate(els.result, ui.setStatus));
  on("render", "click", workflow.renderVideo);
  on("exportJianying", "click", workflow.exportJianyingDraft);
  on("editJianying", "click", workflow.editJianyingDraft);
  on("previewIntroTemplates", "click", workflow.previewIntroTemplates);
  on("uploadBgm", "click", workflow.uploadBgm);
  on("uploadIntroSfx", "click", workflow.uploadIntroSfx);
  on("closeIntroPreview", "click", workflow.closeIntroPreviewModal);
  on("introPreviewBackdrop", "click", workflow.closeIntroPreviewModal);
  on("closeImagePreview", "click", closeImagePreview);
  on("imagePreviewBackdrop", "click", closeImagePreview);
  on(els.preview, "loadedmetadata", updatePreviewAspect);
  on(els.preview, "emptied", updatePreviewAspect);
  on("sidebarToggle", "click", () => {
    setSidebarCollapsed(!document.querySelector(".app-frame")?.classList.contains("sidebar-collapsed"));
  });
  on("toggleImagePrompt", "click", () => {
    setImagePromptExpanded($("tab-image")?.classList.contains("image-prompt-collapsed"));
  });
  on("saveProject", "click", async () => {
    ui.setStatus("保存中", "busy");
    await projectStore.saveNow();
    ui.setStatus("就绪");
  });
  on("newProject", "click", () => {
    workflow.clearThemeIdeas?.();
    workflow.clearImageJobPollers?.();
    projectStore.createNew();
  });
  on(els.projectPicker, "change", () => {
    if (els.projectPicker.value) {
      workflow.clearThemeIdeas?.();
      workflow.clearImageJobPollers?.();
      projectStore.activate(els.projectPicker.value).then(() => {
        workflow.restoreActiveImageJobs?.();
        workflow.restoreActiveAutoPipelineJobs?.();
        workflow.syncContinueButton?.();
        syncWorkflowSteps();
      });
    }
  });

  on("openSettings", "click", ui.openSettings);
  on("closeSettings", "click", ui.closeSettings);
  on("settingsBackdrop", "click", ui.closeSettings);
  on("testTextConnection", "click", workflow.testTextConnection);
  on("testImageConnection", "click", workflow.testImageConnection);
  on("previewTts", "click", workflow.previewTts);
  on("resetCopyPrompt", "click", () => {
    settings.resetCopyPrompt(storyView.updatePromptMeta, projectStore.scheduleSave);
  });
  on("copyPromptPreset", "change", () => {
    settings.applyCopyPromptPreset(storyView.updatePromptMeta, projectStore.scheduleSave);
  });
  on("themeCopyPreset", "change", () => {
    settings.applyCopyPromptPreset(storyView.updatePromptMeta, projectStore.scheduleSave, els.themeCopyPreset.value);
  });
  on("resetCopyToStoryPrompt", "click", () => {
    settings.resetCopyToStoryPrompt(storyView.updatePromptMeta, projectStore.scheduleSave);
  });
  on("resetImagePrompt", "click", () => {
    settings.resetImagePrompt(storyView.updatePromptMeta, projectStore.scheduleSave);
  });
  on(els.imageStylePreset, "change", () => {
    settings.applyImageStylePreset(storyView.updatePromptMeta, projectStore.scheduleSave);
  });
  on("resetImproveImagePrompt", "click", () => {
    settings.resetImproveImagePrompt(storyView.updatePromptMeta, projectStore.scheduleSave);
  });
  on("resetThemeIdeaPrompt", "click", () => {
    settings.resetThemeIdeaPrompt(storyView.updatePromptMeta, projectStore.scheduleSave);
  });

  document.addEventListener("focusout", (event) => {
    const editor = event.target.closest?.("[data-shot-prompt-editor]");
    if (editor) closeShotPromptEditor(editor, true);
  });

  on(els.editor, "input", storyView.onEditorInput);
  on(els.copyPrompt, "input", () => {
    persistAndSave({ promptMeta: true });
  });
  on(els.copyOutput, "input", () => {
    promptMetaAndSave();
    workflow.syncContinueButton?.();
    syncWorkflowSteps();
  });
  on(els.copyToStoryPrompt, "input", () => {
    persistAndSave({ promptMeta: true });
  });
  on(els.imagePrompt, "input", () => {
    persistAndSave({ promptMeta: true });
  });
  on(els.improveImagePrompt, "input", () => {
    persistAndSave({ promptMeta: true });
  });
  on(els.themeIdeaPrompt, "input", () => {
    persistAndSave({ promptMeta: true });
  });
  on(els.themeBrief, "input", () => {
    persistAndSave();
  });
  on(els.themeIntro, "input", () => {
    persistAndSave({ promptMeta: true, themeMirror: true });
    syncWorkflowSteps();
  });
  on(els.themeRevision, "input", () => {
    persistAndSave();
  });
  for (const id of ["autoBrief", "autoCopyPreset", "autoStoryboardGranularity", "autoImageSize", "autoIntroTemplate", "autoTtsPreset"]) {
    onEach([id], "input", settings.persist);
    onEach([id], "change", settings.persist);
  }
  on("autoCopyPreset", "change", () => settings.updateTemplateHints());
  on(els.storyboardGranularity, "change", () => {
    persistAndSave();
  });
  for (const id of ["autoOptimizeImagePrompts", "autoInfiniteImageRetry", "autoRenderAfterImages"]) {
    on(id, "change", settings.persist);
  }
  on(els.topic, "input", () => {
    syncThemeMirrors();
    persistAndSave();
    syncWorkflowSteps();
  });

  for (const id of [
    "textProvider",
    "baseUrl",
    "model",
    "apiKey",
    "imageProvider",
    "imageBaseUrl",
    "imageModel",
    "imageApiKey",
    "ttsBaseUrl",
    "ttsGroupId",
    "ttsModel",
    "ttsVoiceId",
    "ttsSpeed",
    "ttsEmotion",
    "ttsLanguageBoost",
    "voice",
    "rate",
  ]) {
    on(id, "change", settings.persist);
  }
  on("imageSize", "change", () => {
    settings.persist();
    storyView.applyImageSize(els.imageSize.value, { scheduleSave: false });
    projectStore.scheduleSave();
  });
  for (const id of ["introTemplate", "introImageSeconds", "bgmSelect", "introSfxSelect"]) {
    on(id, "change", () => {
      settings.persist();
      projectStore.scheduleSave();
      if (id === "introTemplate" && els.introPreviewGrid) {
        for (const node of els.introPreviewGrid.querySelectorAll(".intro-preview-card")) {
          node.classList.toggle("active", node.dataset.template === els.introTemplate.value);
        }
      }
    });
  }
  on("ttsPreset", "change", () => {
    applyTtsPreset();
    persistAndSave();
  });
  for (const id of ["apiKey", "imageApiKey"]) {
    on(id, "input", settings.persist);
  }
  on("ttsProvider", "change", () => {
    settings.updateTtsProviderVisibility();
    persistAndSave();
  });
  on("ttsModel", "change", () => {
    settings.syncTtsVoiceOptions();
    settings.persist();
  });
  for (const id of ["ttsApiKey", "ttsBaseUrl", "ttsGroupId", "ttsModel", "ttsVoiceId", "ttsSpeed", "ttsEmotion", "ttsLanguageBoost"]) {
    on(id, "input", settings.persist);
  }
  on("textProvider", "change", () => {
    settings.applyTextProviderDefaults();
    settings.persist();
  });
  on("imageProvider", "change", () => {
    settings.applyImageProviderDefaults();
    settings.persist();
  });
  state.referenceAssets?.bindEvents();
  // tab 按钮是 roving tabindex：只有当前项能被 Tab 聚焦，因此必须支持方向键切换，
  // 否则键盘用户进不了其它页面。
  document.addEventListener("keydown", (event) => {
    const tab = event.target.closest?.(".tab-button[role='tab']");
    if (!tab) return;
    const tabs = Array.from(document.querySelectorAll(".sidebar-nav .tab-button"));
    const index = tabs.indexOf(tab);
    if (index < 0) return;
    let next = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      next = tabs[(index + 1) % tabs.length];
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      next = tabs[(index - 1 + tabs.length) % tabs.length];
    } else if (event.key === "Home") {
      next = tabs[0];
    } else if (event.key === "End") {
      next = tabs[tabs.length - 1];
    }
    if (!next) return;
    event.preventDefault();
    setActiveTab(next.dataset.tab);
    next.focus();
  });
  document.addEventListener("keydown", (event) => {
    const step = event.target.closest?.("#tab-copy .workflow-steps li[data-step]");
    if (!step) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    navigateToStep(step);
  });
  document.addEventListener("keydown", (event) => {
    const promptEditor = event.target.closest?.("[data-shot-prompt-editor]");
    if (promptEditor) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeShotPromptEditor(promptEditor, false);
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        closeShotPromptEditor(promptEditor, true);
      }
      return;
    }
    if ((event.key === "Enter" || event.key === " ") && event.target.matches?.("[data-select-shot]")) {
      event.preventDefault();
      toggleSelectedShot(event.target.dataset.selectShot);
      return;
    }
    if (event.key === "Escape") {
      closeImagePreview();
      workflow.closeIntroPreviewModal();
      ui.closeSettings();
    }
  });
}

async function boot() {
  bindEvents();
  restoreLayoutPrefs();
  await workflow.loadBgmOptions().catch(() => null);
  await workflow.loadIntroSfxOptions().catch(() => null);
  await state.referenceAssets?.loadCollections?.().catch(() => null);
  await settings.loadTemplates(api.fetchJson).catch(() => null);
  settings.load();
  applyTtsPreset();
  settings.updateTtsProviderVisibility();
  if (els.topicMirror) els.topicMirror.textContent = els.topic.value || "未填写主题";
  await settings.loadPromptDefaults(api.fetchJson, storyView.updatePromptMeta).catch(() => storyView.updatePromptMeta());
  const restored = await projectStore.loadState();
  if (!restored) await workflow.loadExample();
  await projectStore.loadList();
  await workflow.restoreActiveImageJobs?.();
  await workflow.restoreActiveAutoPipelineJobs?.();
  workflow.syncContinueButton?.();
  syncWorkflowSteps();
  if (!state.activeAutoPipelineJob) ui.setStatus("就绪");
}

boot().catch((err) => {
  ui.setStatus("出错", "error");
  els.result.textContent = String(err.message || err);
});
