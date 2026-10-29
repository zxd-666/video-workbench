export const SETTINGS_KEY = "video-workbench-settings-v1";
// 不内置第三方接口地址，必须由用户在自己的「设置」里填写。
export const DEFAULT_LLM_BASE_URL = "";
export const DEFAULT_TEXT_MODEL = "gpt-5.5";
export const DEFAULT_IMAGE_MODEL = "gpt-image-2";
export const ANTHROPIC_DEFAULT_BASE_URL = "https://api.anthropic.com";
export const ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-5";
export const GEMINI_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta";
export const GEMINI_DEFAULT_MODEL = "gemini-2.0-flash";
export const GEMINI_IMAGE_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta";
export const GEMINI_IMAGE_DEFAULT_MODEL = "imagen-3.0-generate-002";
export const MINIMAX_TTS_DEFAULT_BASE_URL = "https://api.minimaxi.com/v1/t2a_v2";
export const MINIMAX_TTS_DEFAULT_MODEL = "speech-2.8-hd";
export const MINIMAX_TTS_DEFAULT_VOICE_ID = "male-qn-qingse";
export const MINIMAX_TTS_MODELS = [
  "speech-2.8-hd",
  "speech-2.8-turbo",
  "speech-2.6-hd",
  "speech-2.6-turbo",
  "speech-02-hd",
  "speech-02-turbo",
  "speech-01-hd",
  "speech-01-turbo",
];
export const DOUBAO_TTS_DEFAULT_BASE_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional";
export const DOUBAO_TTS_DEFAULT_MODEL = "volc.service_type.10029";
export const DOUBAO_TTS_DEFAULT_VOICE_ID = "zh_male_beijingxiaoye_emo_v2_mars_bigtts";
export const DOUBAO_TTS_MODELS = [
  { value: "volc.service_type.10029", label: "volc.service_type.10029 (legacy 1.0)" },
  { value: "seed-tts-2.0", label: "seed-tts-2.0 (2.0)" },
  { value: "seed-tts-1.0", label: "seed-tts-1.0 (1.0)" },
  { value: "seed-tts-1.0-concurr", label: "seed-tts-1.0-concurr (1.0 concurrent)" },
];
export const PROJECT_SAVE_DELAY_MS = 1600;
export const PROJECT_PROGRESS_SAVE_INTERVAL_MS = 2000;
export const IMAGE_RETRY_LIMIT = 2;
// 并发生图直接打上游：100 路同时打过去极容易被限流甚至判为滥用，
// 默认收敛到 8 路（后端默认值一致，显式调大时上限仍是 100）。
export const IMAGE_CONCURRENCY_LIMIT = 8;

export const COPY_PROMPT_VERSION = 8;
export const COPY_TO_STORY_PROMPT_VERSION = 4;
export const IMPROVE_IMAGE_PROMPT_VERSION = 1;
export const THEME_IDEA_PROMPT_VERSION = 1;

// 创作模板（文案类型/品类）统一由 GET /api/templates 提供，
// 见 templates/<id>.json 和 static/js/templates.js，不再在这里维护常量。
export const STORYBOARD_GRANULARITIES = ["coarse", "balanced", "fine"];
export const IMAGE_SIZES = ["9:16", "1:1", "16:9"];
export const INTRO_TEMPLATES = [
  "none",
  "life_copy_fast_cut",
  "life_copy_expand_cut",
  "life_copy_flash_horizontal",
  "life_copy_flash_vertical",
  "life_copy_staggered_mask",
  "life_copy_mosaic_collage",
];

export const DEFAULT_STORYBOARD_GRANULARITY = "balanced";
export const DEFAULT_IMAGE_SIZE = "9:16";
export const DEFAULT_INTRO_TEMPLATE = "life_copy_fast_cut";

export const IMAGE_STATUS = {
  pending: "pending",
  done: "done",
  error: "error",
  policyError: "policy_error",
};

export const IMAGE_JOB_STATUS = {
  generating: "generating",
  redrawing: "redrawing",
  retrying: "retrying",
};
