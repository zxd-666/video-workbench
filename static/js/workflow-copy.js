export function createCopyWorkflow({ els, ui, api, settings, storyView, projectStore, setActiveTab, withCurrentImageSize }) {
  // 长任务期间每秒刷新一次“已等待 xx 秒”，避免界面看起来像卡死。
  function startElapsed(label) {
    const started = Date.now();
    ui.setStatus(`${label} 0s`, "busy");
    const timer = window.setInterval(() => {
      ui.setStatus(`${label} ${Math.round((Date.now() - started) / 1000)}s`, "busy");
    }, 1000);
    return () => window.clearInterval(timer);
  }

  // 「继续：拆分分镜」只在有口播文案时可用
  function syncContinueButton() {
    const button = els.continueToStoryboard;
    if (!button) return;
    const text = String(els.copyOutput?.value || "").trim();
    button.disabled = !text;
    button.title = text ? "把口播文案拆分成可生成图片的分镜" : "先在上面点「生成文案」，或直接把口播文案粘进来";
  }

  async function generateStory() {
    settings.persist();
    ui.setBusy(true);
    const stopElapsed = startElapsed("生成分镜");
    try {
      settings.requireTextApiKey();
      const data = withCurrentImageSize(await api.postJson("/api/text/generate", settings.storyPayload()));
      storyView.write(data);
      els.result.textContent = JSON.stringify({ "分镜生成": "完成", "镜头数": data.shots?.length || 0 }, null, 2);
      await projectStore.saveNow();
      ui.setStatus("就绪");
      setActiveTab("image");
    } catch (err) {
      ui.setStatus("出错", "error");
      els.result.textContent = String(err.message || err);
    } finally {
      stopElapsed();
      ui.setBusy(false);
      syncContinueButton();
    }
  }

  async function generateCopy() {
    settings.persist();
    ui.setBusy(true);
    const stopElapsed = startElapsed("写口播");
    let focusContinue = false;
    try {
      settings.requireTextApiKey();
      const data = await api.postJson("/api/text/generate-copy", settings.textPayload());
      els.copyOutput.value = data.text || "";
      storyView.updatePromptMeta();
      els.result.textContent = JSON.stringify({
        "口播生成": "完成",
        "主题": data.topic,
        "字数": els.copyOutput.value.length,
        "下一步": "点「继续：拆分分镜」把口播拆成分镜",
      }, null, 2);
      await projectStore.saveNow();
      ui.setStatus("文案已生成，可继续拆分镜");
      // 拆分镜可能要几分钟，不自动串在后面，而是把焦点交给下一步的按钮
      focusContinue = true;
    } catch (err) {
      ui.setStatus("出错", "error");
      els.result.textContent = String(err.message || err);
    } finally {
      stopElapsed();
      ui.setBusy(false);
      syncContinueButton();
      // 按钮在忙碌期间是 disabled 的，必须等恢复可点之后再聚焦
      if (focusContinue) els.continueToStoryboard?.focus?.();
    }
  }

  async function buildStoryboardFromCopy() {
    const text = String(els.copyOutput?.value || "").trim();
    if (!text) {
      ui.setStatus("请先生成或填写口播文案", "error");
      return;
    }
    settings.persist();
    ui.setBusy(true);
    const stopElapsed = startElapsed("拆分镜");
    try {
      settings.requireTextApiKey();
      const story = withCurrentImageSize(await api.postJson("/api/text/copy-to-story", settings.copyToStoryPayload(text)));
      storyView.write(story);
      els.result.textContent = JSON.stringify({
        "分镜拆分": "完成",
        "镜头数": story.shots?.length || 0,
      }, null, 2);
      await projectStore.saveNow();
      ui.setStatus("就绪");
      setActiveTab("image");
    } catch (err) {
      ui.setStatus("出错", "error");
      els.result.textContent = String(err.message || err);
    } finally {
      stopElapsed();
      ui.setBusy(false);
      syncContinueButton();
    }
  }

  return {
    generateStory,
    generateCopy,
    buildStoryboardFromCopy,
    syncContinueButton,
  };
}
