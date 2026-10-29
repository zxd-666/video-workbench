/**
 * 创作模板（品类）客户端。
 *
 * 页面启动时从 GET /api/templates 拉一次清单，里面已经包含每个品类的
 * 展示信息、选题约束和解析好的提示词全文。新增品类只需要在后端
 * templates/ 目录加一个 JSON 文件，前端不用改。
 */

const TEMPLATES_URL = "/api/templates";
const OVERRIDES_KEY = "video-workbench-template-overrides";
const SELECTED_KEY = "video-workbench-template-selected";

const RANDOM_LABEL = "随机模板";
const FALLBACK_TEMPLATE = {
  id: "general_oral",
  label: "通用 · 叙事口播",
  short_label: "叙事口播",
  category: "通用",
  description: "适合生活观察、职场、人物故事和情感观点，不依赖固定世界观。",
  order: 200,
  opening: "",
  theme: { label: "通用 · 叙事口播", domain: "", direction: "", examples: "", avoid: "", instruction: "" },
  defaults: { image_size: "9:16", storyboard_granularity: "balanced", intro_template: "none", tts_preset: "male_steady" },
  prompts: { copy: "", copy_to_story: "", image_style: "", story_shots: "" },
};

let payload = null;
let pending = null;
let overrides = readOverrides();

function readJson(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "{}");
  } catch {
    return {};
  }
}

function readOverrides() {
  const data = readJson(OVERRIDES_KEY);
  return data && typeof data === "object" && !Array.isArray(data) ? data : {};
}

function writeOverrides() {
  try {
    localStorage.setItem(OVERRIDES_KEY, JSON.stringify(overrides));
  } catch {}
}

function normalize(data) {
  const list = Array.isArray(data?.templates) ? data.templates.filter((item) => item?.id) : [];
  if (!list.length) return null;
  const templates = list
    .map((item) => ({
      ...FALLBACK_TEMPLATE,
      ...item,
      theme: { ...FALLBACK_TEMPLATE.theme, ...(item.theme || {}) },
      defaults: { ...FALLBACK_TEMPLATE.defaults, ...(item.defaults || {}) },
      prompts: { ...FALLBACK_TEMPLATE.prompts, ...(item.prompts || {}) },
    }))
    .sort((a, b) => Number(a.order || 0) - Number(b.order || 0) || String(a.id).localeCompare(String(b.id)));
  const categories = Array.isArray(data.categories) && data.categories.length
    ? data.categories
    : Array.from(new Set(templates.map((item) => item.category)));
  return {
    default_template: data.default_template || templates[0].id,
    random_value: data.random_value || "random",
    categories,
    templates,
    shared: data.shared || {},
  };
}

export async function loadTemplates(fetchJson) {
  if (payload) return payload;
  if (!pending) {
    pending = Promise.resolve()
      .then(() => fetchJson(TEMPLATES_URL))
      .then((data) => {
        const normalized = normalize(data);
        if (!normalized) throw new Error("模板清单为空");
        payload = normalized;
        return payload;
      })
      .catch((error) => {
        pending = null;
        payload = {
          default_template: FALLBACK_TEMPLATE.id,
          random_value: "random",
          categories: [FALLBACK_TEMPLATE.category],
          templates: [FALLBACK_TEMPLATE],
          shared: {},
        };
        console.warn("加载创作模板失败，使用内置默认模板", error);
        return payload;
      });
  }
  return pending;
}

export function hasTemplates() {
  return Boolean(payload);
}

export function templates() {
  return payload?.templates || [FALLBACK_TEMPLATE];
}

export function templateIds() {
  return templates().map((item) => item.id);
}

export function defaultTemplateId() {
  return payload?.default_template || FALLBACK_TEMPLATE.id;
}

export function randomTemplateValue() {
  return payload?.random_value || "random";
}

export function isRandomTemplate(value) {
  return String(value || "") === randomTemplateValue();
}

export function getTemplate(templateId) {
  const key = String(templateId || "").trim();
  return templates().find((item) => item.id === key) || null;
}

export function isKnownTemplate(value) {
  return Boolean(getTemplate(value));
}

export function resolveTemplateId(value, { allowRandom = true } = {}) {
  const key = String(value || "").trim();
  if (allowRandom && isRandomTemplate(key)) return key;
  if (getTemplate(key)) return key;
  if (key === "default" || key === "reality") return defaultTemplateId();
  return defaultTemplateId();
}

export function templateLabel(templateId) {
  return getTemplate(templateId)?.label || getTemplate(defaultTemplateId())?.label || "默认模板";
}

export function templateDefaults(templateId) {
  return { ...(getTemplate(templateId)?.defaults || FALLBACK_TEMPLATE.defaults) };
}

export function themeInstruction(templateId) {
  const item = getTemplate(templateId) || getTemplate(defaultTemplateId());
  return String(item?.theme?.instruction || "").trim();
}

export function getOverride(templateId, kind) {
  const value = overrides?.[templateId]?.[kind];
  return typeof value === "string" && value.trim() ? value : "";
}

export function setOverride(templateId, kind, text) {
  const id = String(templateId || "").trim();
  if (!id || !kind) return;
  const value = String(text || "");
  const current = overrides[id] || {};
  const base = templatePrompt(id, kind);
  if (!value.trim() || value === base) {
    if (!current[kind]) return;
    delete current[kind];
  } else {
    current[kind] = value;
  }
  if (Object.keys(current).length) overrides[id] = current;
  else delete overrides[id];
  writeOverrides();
}

export function clearOverrides(templateId) {
  const id = String(templateId || "").trim();
  if (!id || !overrides[id]) return false;
  delete overrides[id];
  writeOverrides();
  return true;
}

export function hasOverride(templateId, kind = "") {
  const entry = overrides?.[String(templateId || "").trim()];
  if (!entry) return false;
  return kind ? Boolean(entry[kind]) : Object.keys(entry).length > 0;
}

/** 模板自带的默认提示词（不含用户覆盖）。 */
export function templatePrompt(templateId, kind) {
  const item = getTemplate(templateId) || getTemplate(defaultTemplateId());
  const value = item?.prompts?.[kind];
  if (typeof value === "string" && value.trim()) return value;
  const shared = payload?.shared?.[kind];
  return typeof shared === "string" ? shared : "";
}

/** 实际生效的提示词：用户按模板保存的覆盖优先。 */
export function promptText(templateId, kind) {
  return getOverride(templateId, kind) || templatePrompt(templateId, kind);
}

export function copyPromptText(templateId) {
  return promptText(templateId, "copy");
}

export function copyToStoryPromptText(templateId) {
  return promptText(templateId, "copy_to_story");
}

export function imageStylePromptText(templateId) {
  return promptText(templateId, "image_style");
}

export function storyShotsPromptText(templateId) {
  return promptText(templateId, "story_shots");
}

export function sharedPrompt(kind) {
  return String(payload?.shared?.[kind] || "");
}

export function rememberSelectedTemplate(templateId) {
  try {
    localStorage.setItem(SELECTED_KEY, String(templateId || ""));
  } catch {}
}

export function rememberedTemplate() {
  try {
    return localStorage.getItem(SELECTED_KEY) || "";
  } catch {
    return "";
  }
}

function optionElement(value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  return option;
}

/**
 * 用「随机 + 按 category 分组的 optgroup」填满下拉框。
 * 返回最终选中的值。
 */
export function fillTemplateSelect(select, { includeRandom = false, randomLabel = RANDOM_LABEL, preferred = "" } = {}) {
  if (!select) return "";
  const current = preferred || select.value || "";
  const nodes = [];
  if (includeRandom) nodes.push(optionElement(randomTemplateValue(), randomLabel));
  const groups = new Map();
  for (const item of templates()) {
    const key = item.category || "其他";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  for (const [category, items] of groups) {
    const group = document.createElement("optgroup");
    group.label = category;
    for (const item of items) group.append(optionElement(item.id, item.label || item.id));
    nodes.push(group);
  }
  select.replaceChildren(...nodes);
  const values = new Set(Array.from(select.options).map((option) => option.value));
  const fallback = includeRandom ? randomTemplateValue() : defaultTemplateId();
  select.value = values.has(current) ? current : fallback;
  return select.value;
}

export function templateHintText(templateId) {
  const item = getTemplate(templateId) || getTemplate(defaultTemplateId());
  if (!item) return "";
  if (isRandomTemplate(templateId)) return "每次运行随机选一个模板，运行结果里会写明实际使用的模板。";
  return [item.category, item.description].filter(Boolean).join(" · ");
}
