export const $ = (id) => document.getElementById(id);

export function createUi() {
  const els = {
    editor: $("jsonEditor"),
    status: $("status"),
    result: $("result"),
    preview: $("preview"),
    openVideo: $("openVideo"),
    editJianying: $("editJianying"),
    renderProgress: $("renderProgress"),
    renderProgressBar: $("renderProgressBar"),
    renderProgressText: $("renderProgressText"),
    renderProgressPercent: $("renderProgressPercent"),
    autoBrief: $("autoBrief"),
    autoCopyPreset: $("autoCopyPreset"),
    autoTemplateHint: $("autoTemplateHint"),
    autoStoryboardGranularity: $("autoStoryboardGranularity"),
    autoImageSize: $("autoImageSize"),
    autoIntroTemplate: $("autoIntroTemplate"),
    autoTtsPreset: $("autoTtsPreset"),
    autoOptimizeImagePrompts: $("autoOptimizeImagePrompts"),
    autoInfiniteImageRetry: $("autoInfiniteImageRetry"),
    autoRenderAfterImages: $("autoRenderAfterImages"),
    autoPipelineStatus: $("autoPipelineStatus"),
    autoPipelineCurrent: $("autoPipelineCurrent"),
    autoPipelinePercent: $("autoPipelinePercent"),
    autoPipelineProgressBar: $("autoPipelineProgressBar"),
    autoPipelineSteps: $("autoPipelineSteps"),
    autoPipelineResult: $("autoPipelineResult"),
    introPreviewModal: $("introPreviewModal"),
    introPreviewBackdrop: $("introPreviewBackdrop"),
    introPreviewGrid: $("introPreviewGrid"),
    jsonMeta: $("jsonMeta"),
    shotGrid: $("shotGrid"),
    selectedShotLabel: $("selectedShotLabel"),
    copyPromptPreset: $("copyPromptPreset"),
    copyTemplateHint: $("copyTemplateHint"),
    copyPrompt: $("copyPrompt"),
    copyOutput: $("copyOutput"),
    continueToStoryboard: $("continueToStoryboard"),
    copyPromptMeta: $("copyPromptMeta"),
    copyMeta: $("copyMeta"),
    storyboardGranularity: $("storyboardGranularity"),
    copyToStoryPrompt: $("copyToStoryPrompt"),
    copyToStoryPromptMeta: $("copyToStoryPromptMeta"),
    imageStylePreset: $("imageStylePreset"),
    imagePrompt: $("imagePrompt"),
    imagePromptMeta: $("imagePromptMeta"),
    improveImagePrompt: $("improveImagePrompt"),
    improveImagePromptMeta: $("improveImagePromptMeta"),
    settingsDrawer: $("settingsDrawer"),
    settingsBackdrop: $("settingsBackdrop"),
    textConnectionResult: $("textConnectionResult"),
    imageConnectionResult: $("imageConnectionResult"),
    projectPicker: $("projectPicker"),
    projectSaveMeta: $("projectSaveMeta"),
    projectPicker: $("projectPicker"),
    projectGrid: $("projectGrid"),
    assetCollectionName: $("assetCollectionName"),
    assetCollectionDescription: $("assetCollectionDescription"),
    createAssetCollection: $("createAssetCollection"),
    assetCollectionPicker: $("assetCollectionPicker"),
    assetCollectionMeta: $("assetCollectionMeta"),
    assetUploadFile: $("assetUploadFile"),
    assetName: $("assetName"),
    assetType: $("assetType"),
    assetDescription: $("assetDescription"),
    assetTags: $("assetTags"),
    uploadReferenceAsset: $("uploadReferenceAsset"),
    assetGrid: $("assetGrid"),
    projectReferenceCollection: $("projectReferenceCollection"),
    autoReferenceEnabled: $("autoReferenceEnabled"),
    themeCopyPreset: $("themeCopyPreset"),
    themeTemplateHint: $("themeTemplateHint"),
    themeBrief: $("themeBrief"),
    themeIdeaCandidates: $("themeIdeaCandidates"),
    themeIdeaPrompt: $("themeIdeaPrompt"),
    themeIdeaPromptMeta: $("themeIdeaPromptMeta"),
    themeIntro: $("themeIntro"),
    themeIntroMeta: $("themeIntroMeta"),
    themeIntroMirror: $("themeIntroMirror"),
    themeRevision: $("themeRevision"),
    topic: $("topic"),
    topicMirror: $("topicMirror"),
    textProvider: $("textProvider"),
    baseUrl: $("baseUrl"),
    model: $("model"),
    apiKey: $("apiKey"),
    imageProvider: $("imageProvider"),
    imageBaseUrl: $("imageBaseUrl"),
    imageModel: $("imageModel"),
    imageApiKey: $("imageApiKey"),
    imageSize: $("imageSize"),
    introTemplate: $("introTemplate"),
    introImageSeconds: $("introImageSeconds"),
    ttsPreset: $("ttsPreset"),
    bgmSelect: $("bgmSelect"),
    bgmUploadFile: $("bgmUploadFile"),
    introSfxSelect: $("introSfxSelect"),
    introSfxUploadFile: $("introSfxUploadFile"),
    ttsProvider: $("ttsProvider"),
    ttsBaseUrl: $("ttsBaseUrl"),
    ttsApiKey: $("ttsApiKey"),
    ttsGroupId: $("ttsGroupId"),
    ttsModel: $("ttsModel"),
    ttsVoiceId: $("ttsVoiceId"),
    ttsSpeed: $("ttsSpeed"),
    ttsEmotion: $("ttsEmotion"),
    ttsLanguageBoost: $("ttsLanguageBoost"),
    ttsPreviewResult: $("ttsPreviewResult"),
    ttsPreviewAudio: $("ttsPreviewAudio"),
    voice: $("voice"),
    rate: $("rate"),
  };

  // setBusy(false) 会把所有按钮恢复成可点，但「继续：拆分分镜」这类按钮的可用性
  // 取决于内容而不是忙碌状态。注册在这里的回调会在每次解除忙碌后重新算一遍。
  const idleHooks = new Set();
  let busy = false;

  function onIdle(hook) {
    idleHooks.add(hook);
    return () => idleHooks.delete(hook);
  }

  function isBusy() {
    return busy;
  }

  function setStatus(text, kind = "") {
    els.status.textContent = text;
    els.status.className = `status-pill ${kind}`.trim();
  }

  function setBusy(next) {
    busy = next;
    for (const id of [
      "loadExample",
      "startAutoPipeline",
      "cancelAutoPipeline",
      "generateTheme",
      "generateThemeIdeas",
      "rerollThemeIdeas",
      "rerollTheme",
      "reviseTheme",
      "goCopyFromTheme",
      "goStoryboardImages",
      "themeCopyPreset",
      "generate",
      "generateCopy",
      "continueToStoryboard",
      "generateImages",
      "redrawSelected",
      "validate",
      "render",
      "exportJianying",
      "editJianying",
      "previewIntroTemplates",
      "refreshGallery",
      "copyPromptPreset",
      "resetCopyPrompt",
      "resetCopyToStoryPrompt",
      "imageStylePreset",
      "resetImagePrompt",
      "resetImproveImagePrompt",
      "resetThemeIdeaPrompt",
      "testTextConnection",
      "testImageConnection",
      "saveProject",
      "newProject",
      "projectPicker",
      "createAssetCollection",
      "assetCollectionPicker",
      "assetUploadFile",
      "assetName",
      "assetType",
      "assetDescription",
      "assetTags",
      "uploadReferenceAsset",
      "projectReferenceCollection",
      "autoReferenceEnabled",
      "introTemplate",
      "introImageSeconds",
      "ttsPreset",
      "bgmSelect",
      "bgmUploadFile",
      "uploadBgm",
      "introSfxSelect",
      "introSfxUploadFile",
      "uploadIntroSfx",
      "ttsProvider",
      "ttsBaseUrl",
      "ttsApiKey",
      "ttsGroupId",
      "ttsModel",
      "ttsVoiceId",
      "ttsSpeed",
      "ttsEmotion",
      "ttsLanguageBoost",
      "previewTts",
    ]) {
      const el = $(id);
      if (el) el.disabled = next;
    }
    if (!next) {
      for (const hook of idleHooks) {
        try {
          hook();
        } catch {
          // 单个回调出错不影响其它状态的恢复
        }
      }
    }
  }

  function setTestResult(el, text, kind = "") {
    if (!el) return;
    el.textContent = text;
    el.className = `test-result ${kind}`.trim();
  }

  function setProjectMeta(label, detail = "") {
    // 当前项目名已经由顶部下拉框显示，这里只保留自动保存状态；
    // 完整项目 id 放进下拉框的 title，需要时悬停就能看到。
    if (els.projectSaveMeta) els.projectSaveMeta.textContent = detail || "自动保存开启";
    if (els.projectPicker) {
      els.projectPicker.title = [label, detail].filter(Boolean).join(" · ") || "切换项目";
    }
  }

  function openSettings() {
    if (!els.settingsBackdrop || !els.settingsDrawer) {
      setTab("settings");
      return;
    }
    els.settingsBackdrop.hidden = false;
    els.settingsDrawer.classList.add("open");
    els.settingsDrawer.setAttribute("aria-hidden", "false");
  }

  function closeSettings() {
    if (!els.settingsBackdrop || !els.settingsDrawer) return;
    els.settingsDrawer.classList.remove("open");
    els.settingsDrawer.setAttribute("aria-hidden", "true");
    els.settingsBackdrop.hidden = true;
  }

  function setTab(tab) {
    for (const button of document.querySelectorAll(".tab-button")) {
      const active = button.dataset.tab === tab;
      if (!button.id) button.id = `tab-button-${button.dataset.tab}`;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-controls", `tab-${button.dataset.tab}`);
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    }
    for (const panel of document.querySelectorAll(".tab-view")) {
      const active = panel.id === `tab-${tab}`;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", `tab-button-${panel.id.replace(/^tab-/, "")}`);
      panel.classList.toggle("active", active);
    }
  }

  return {
    els,
    setStatus,
    setBusy,
    isBusy,
    onIdle,
    setTestResult,
    setProjectMeta,
    openSettings,
    closeSettings,
    setTab,
  };
}
