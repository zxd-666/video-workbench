# 短视频创作工作台

一个本地 AI 短视频工作台，用于把主题拆成分镜脚本，再生成图片、配音、字幕和 MP4 成片。“人生副本”只是内置的剧情类创作模板之一，产品本身适用于口播、科普、带货等通用题材。

项目不绑定具体模型服务，不内置商业生图能力，只提供可替换的接口层。

## 使用声明

本项目主要用于学习交流、技术研究与个人本地测试。使用者如将本项目用于商业场景，需自行确认所接入的模型/API、生成内容及本地素材具备相应商业使用授权；禁止用于任何违法违规场景。

项目代码不包含、也不授权任何第三方音乐、音效、图片、字体、视频、模型服务或平台接口资源。使用者接入的 API、模型、提示词、生成内容及本地素材，均需自行确认来源合法并取得相应授权。

本仓库仅分发项目代码；示例、用户本地上传或自行接入生成的素材不随本项目授权。使用者在接入服务、生成内容或发布作品时，应自行确认授权、服务条款和平台规则。

如本项目内容无意中侵犯了你的合法权益，请联系处理。

## 功能

- 口播文案生成：OpenAI-compatible API
- 文案生成：可选 [Sophomoresty/gemini-web2api](https://github.com/Sophomoresty/gemini-web2api)
- 图片生成：OpenAI-compatible Images API
- 可编辑文案提示词：默认由当前创作模板提供，未覆盖时回落到通用的 `prompt.txt`
- 创作模板：内置 13 个模板 / 4 个分类（人生副本、通用、商业），默认选中“通用 · 叙事口播”，新增题材只需加一个 `templates/<id>.json`
- 可编辑图片提示词：默认由当前创作模板提供，未覆盖时回落到通用的 `prompts/image_style.md`
- 口播转分镜：默认读取 `prompts/copy_to_story.md`
- 高级分镜数据：默认示例读取 `examples/buffet_story.json`
- 仅用主题生成分镜：默认由当前创作模板提供，未覆盖时回落到通用的 `prompts/story_shots.md`
- 图片批量生成和单张重抽
- 图片失败自动重试，并在分镜卡片显示生成中、重试中、失败状态
- TTS 配音：Edge TTS / MiniMax T2A HTTP / 豆包语音（火山引擎）
- BGM 与开头音效：内置本地素材选择，支持上传自定义音频到 `workspace/`
- 开头模板：翻页快切、展开快切、横向/纵向羽化快闪、阶梯遮罩接力，模板预览使用固定静态 MP4
- SRT/ASS 字幕
- FFmpeg 合成 MP4（当前默认 1080x1920 / 9:16 画布）

## 快速开始

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 7860
```

打开：

```text
http://127.0.0.1:7860
```

## Windows EXE

发布版下载 `video-workbench-windows-x64.zip` 后解压，双击 `video-workbench.exe` 即可启动，默认访问：

```text
http://127.0.0.1:7860
```

如需填写 API Key，可以把 `.env.example` 复制为 `.env`，并放在 `video-workbench.exe` 同级目录。项目数据、上传素材、生成图片和视频会保存在 exe 同级的 `workspace/` 目录，不会写入安装目录外的系统位置。

## 本地自检

启动服务后可以跑 smoke check，确认接口、项目恢复、前端模块加载、分镜渲染和已有图片 URL 是否正常：

```bash
python scripts/smoke_check.py
```

如果 `.env` 里已经配置好文案和图片模型，也可以同时测试外部连接：

```bash
python scripts/smoke_check.py --external
```

## 环境要求

- Python 3.11+
- FFmpeg / FFprobe in PATH
- Python packages in `requirements.txt`

## 文案接口

普通 OpenAI-compatible 文本接口：

```text
POST {LLM_BASE_URL}/v1/chat/completions
Authorization: Bearer {LLM_API_KEY}
```

网页里填写：

- Provider: `OpenAI-compatible`
- Base URL
- Model
- API Key

也可以复制 `.env.example` 为 `.env` 后填写本地配置。后端启动时会自动读取项目根目录下的 `.env`。

## 提示词

7860 页面里的主流程是：

```text
主题 + 文案提示词 -> 口播文案 -> 自动拆分镜 -> 图片提示词生成分镜图 -> 合成视频
```

页面里可以直接编辑两类提示词，内容随“创作模板”切换：

- 文案提示词：用于“生成口播并拆分镜”，默认来自当前模板的 `copy` 提示词；模板没配时回落到通用的 `prompt.txt`。
- 图片提示词：用于“批量生成”和“重抽选中图片”，默认来自当前模板的 `image_style` 提示词；模板没配时回落到通用的 `prompts/image_style.md`。

共享默认提示词（`prompt.txt`、`prompts/image_style.md`、`prompts/story_shots.md`）保持题材中立，不预设固定开场白或角色风格；“人生副本”类模板各自的剧情化提示词放在 `prompts/copy_*.md`、`prompts/story_shots_life_copy.md` 和 `prompts/image_style_life_copy.md` 里。

高级区里的“分镜数据”是内部中间数据，用于承接图片和视频流程。通常不需要手写；如果要重新拆分已有口播，可以点“由口播拆分镜”。

## 创作模板

除了“人生副本”这类剧情短片，项目也支持通用题材（口播、科普、带货等），默认模板是“通用 · 叙事口播”。不同题材的差异集中在 `templates/<id>.json` 里，前端通过 `GET /api/templates` 读取，不再在 JS 里维护硬编码列表。

一个模板 JSON 包含：

- `id` / `label` / `short_label` / `category` / `order`：模板标识、展示名、分组（下拉框按分类分组）、排序。
- `description`：下拉框下方的一行说明，写清楚适用题材。
- `theme`：选题阶段使用的领域、方向、示例、避坑和 `instruction`（追加到选题提示词里的风格要求）。
- `defaults`：选中该模板后自动带上的 `image_size`、`storyboard_granularity`、`intro_template`、`tts_preset`。
- `prompts`：该题材的 `copy`、`copy_to_story`、`image_style`、`story_shots` 四个提示词文件路径；留空则回落到共享的 `prompt.txt` 和 `prompts/*.md`。共享默认全部题材中立，剧情模板各自指向 `prompts/copy_reality.md` 这类专属文件。

现有分类：人生副本 · 现实、人生副本 · 超现实、通用、商业。新增一个题材只需要新增一个 JSON 文件（文件名必须与 `id` 一致），重启后即可在三个模板下拉框里出现，无需改动前端或后端代码。

页面上的模板下拉框各有分工：

- “创作模板”（文案 / 分镜页）：决定手写流程用哪套提示词。
- “主题模板”：决定“生成主题”时套用哪套选题风格。
- “自动模板”：自动流水线使用，可选“随机模板”，由后端在每次任务开始时抽取。

在模板提示词上做的修改会按模板分别保存在浏览器本地；点“使用该模板默认提示词”即可清除该模板的自定义内容，切回模板自带的提示词。

## 全自动流水线设计

后续会在现有手动工作台外层增加“自动流水线”模式。它不是让前端连续点击现有按钮，而是由后端创建可恢复任务，自动完成从选题到成片的完整流程。

详细落地方案见：[`docs/auto_pipeline_implementation.md`](docs/auto_pipeline_implementation.md)。

### 用户输入

流水线必须支持用户什么都不输入，直接点击开始。此时系统自动生成候选选题方向，并自动选择一个方向继续往下跑。

用户也可以只输入很抽象的顶层要求，例如：

```text
猎奇
温馨
猎奇，温馨
斗罗大陆世界观
现代都市，反转强一点
县城，宝妈，压抑但结尾温暖
```

这些输入不是最终主题，而是“顶层约束”。系统需要把它们逐步收敛为可生成口播的明确主题和主题介绍。

### 自动流程

```text
顶层要求或空输入
-> 生成候选选题方向
-> 自动选择方向
-> 生成主题和主题介绍
-> 生成口播文案
-> 拆分镜
-> AI 优化图片提示词
-> 生成分镜图片
-> 自动选择封面
-> 渲染 MP4
-> 保存项目和产物
```

第一版默认策略：

- 用户无输入时，自动生成 6 条适合当前创作模板、现实感强、可直接口播的候选方向。
- 用户有输入时，把输入当作风格、世界观、情绪或题材约束，而不是当作完整主题。
- 自动采用第 1 条候选方向；后续可以升级为“AI 评分后选择最佳方向”。
- 图片提示词全部自动优化一次。
- 图片生成失败自动重试；如果是提示词合规问题，先重新优化提示词再重试。
- 默认选择第一张成功生成的分镜图作为视频封面。
- 图片成功率足够时才进入渲染；失败镜头需要记录原因。

### 后端任务化

全自动流水线必须由后端执行，前端只负责创建任务和轮询状态。这样刷新页面、关闭浏览器或网络波动时，任务状态仍然保存在项目目录里。

建议新增：

```text
app/auto_pipeline_jobs.py
```

任务状态保存到：

```text
workspace/projects/{项目ID}/jobs/auto_pipeline_{任务ID}.json
```

状态结构示例：

```json
{
  "job_id": "auto_20260702_153000_ab12",
  "project_id": "20260702_153000_人生副本_ab12",
  "status": "running",
  "current_step": "generate_images",
  "input": {
    "brief": "猎奇，温馨",
    "copy_preset": "reality",
    "image_size": "9:16",
    "intro_template": "life_copy_fast_cut",
    "tts_preset": "male_fast",
    "bgm_id": "none"
  },
  "steps": [
    { "key": "theme_ideas", "name": "生成选题方向", "status": "done" },
    { "key": "select_idea", "name": "选择方向", "status": "done" },
    { "key": "theme", "name": "生成主题", "status": "done" },
    { "key": "copy", "name": "生成口播", "status": "done" },
    { "key": "storyboard", "name": "拆分镜", "status": "done" },
    { "key": "improve_prompts", "name": "优化图片提示词", "status": "done" },
    { "key": "images", "name": "生成图片", "status": "running" },
    { "key": "cover", "name": "选择封面", "status": "pending" },
    { "key": "render", "name": "渲染视频", "status": "pending" }
  ],
  "result": {
    "topic": "",
    "video_url": "",
    "project_url": ""
  },
  "error": ""
}
```

每一步都要做成幂等：任务恢复时先检查已有产物，已有主题、口播、分镜、图片或 MP4 时直接跳过对应步骤，避免中断后从头消耗 API。

### API 草案

```text
POST /api/auto-pipeline/jobs
GET  /api/auto-pipeline/jobs
GET  /api/auto-pipeline/jobs/{project_id}/{job_id}
POST /api/auto-pipeline/jobs/{project_id}/{job_id}/cancel
POST /api/auto-pipeline/jobs/{project_id}/{job_id}/resume
```

## 项目保存

工作台会在外层维护一个当前项目。点击“保存项目”或生成口播、分镜、图片、视频后，会写入：

```text
workspace/projects/{项目ID}/
```

常用文件包括：

```text
state.json
metadata.json
copy.txt
story.json
result.txt
prompts/copy_prompt.txt
prompts/image_prompt.txt
images/
final.mp4
voice.mp3
subtitle.srt
```

刷新页面后会优先恢复当前项目。
顶部项目选择器可以切换已有项目，“新建项目”会创建一个新的当前项目。
图片生成完成后会回填到当前项目的 `story.json` 和 `images/` 目录。

## 前端结构

前端使用原生 ES Modules，入口是 `static/app.js`，其余代码按职责拆到 `static/js/`：

- `api.js`：HTTP 请求封装
- `ui.js`：DOM 查询、状态、设置抽屉、标签切换
- `settings.js`：本地设置、接口配置和请求 payload
- `story-view.js`：分镜 JSON、字数统计、分镜卡片渲染
- `project-store.js`：项目保存、恢复、切换和自动保存
- `workflow.js`：组合各 workflow 子模块
- `workflow-theme.js`：主题策划和主题修订
- `workflow-copy.js`：口播生成和口播拆分镜
- `workflow-image.js`：图片批量生成、并发、重试、重抽
- `workflow-media.js`：BGM/音效上传和开头模板预览
- `workflow-render.js`：异步渲染任务提交、轮询和视频预览
- `workflow-connection.js`：文本/图片接口连通性测试
- `workflow-utils.js`：流程工具函数

## Gemini Web2API

Gemini 文本走 `gemini-web2api`，它本身提供 OpenAI-compatible API。

先单独启动 `gemini-web2api`：

```bash
pip install httpx
python gemini_web2api.py
```

默认服务地址：

```text
http://127.0.0.1:8081/v1
```

工作台里选择：

```text
Provider: Gemini Web2API
Base URL: http://127.0.0.1:8081/v1
Model: gemini-3.5-flash-thinking
API Key: sk-local
```

`.env` 示例：

```text
TEXT_PROVIDER=gemini_web2api
LLM_BASE_URL=http://127.0.0.1:8081/v1
LLM_MODEL=gemini-3.5-flash-thinking
LLM_API_KEY=sk-local
```

`gemini-web2api` 支持的常用模型包括：

```text
gemini-3.5-flash
gemini-3.5-flash-thinking
gemini-3.5-flash-thinking-lite
gemini-3.1-pro
gemini-auto
gemini-flash-lite
```

## 图片接口

图片接口目前只保留 OpenAI-compatible Images：

```text
POST {IMAGE_BASE_URL}/v1/images/generations
Authorization: Bearer {IMAGE_API_KEY}
```

支持响应：

- `data[0].url`
- `data[0].b64_json`

图片尺寸使用比例字符串，不固定写像素：

```text
9:16  竖屏，默认，适合短视频
1:1   正方形
16:9  横屏
```

注意：图片生成比例和成片画布是两个概念。当前成片合成画布仍固定为 `1080x1920`（9:16），横屏或方形图片会被适配进竖屏视频画布。后续如果需要完整横屏成片，需要在渲染配置里新增成片比例/分辨率参数。

生成图片后，工作台会把每个 shot 更新为：

```json
{
  "image_path": "D:\\path\\to\\shot_01.png",
  "image_url": "/workspace/project_id/images/shot_01.png",
  "resolved_image_prompt": "实际发送给图片模型的提示词"
}
```

## 配音接口

默认使用 Edge TTS，无需密钥。需要使用 MiniMax 时，在设置页选择 `MiniMax T2A HTTP` 并填写：

```text
接口地址：https://api.minimaxi.com/v1/t2a_v2
API Key：MiniMax 平台接口密钥
模型：speech-2.8-hd
音色 ID：male-qn-qingse 或其他系统/复刻音色 ID
Group ID：新接口通常留空，旧网关需要时再填
```

MiniMax 使用官方同步语音合成接口 `POST /v1/t2a_v2`，工作台请求非流式 `hex` 音频并写入本地 MP3，再进入后续视频合成流程。

需要使用豆包语音/火山引擎时，在设置页选择 `豆包语音 / 火山 TTS` 并填写：

```text
接口地址：https://openspeech.bytedance.com/api/v3/tts/unidirectional
API Key：当前用户自己的火山引擎豆包语音 API Key
模型 / Resource ID：volc.service_type.10029
音色 ID：火山音色列表或声音复刻得到的 speaker ID
```

豆包语音使用 V3 HTTP Chunked 单向流式接口。工作台会读取返回 JSON 中的 base64 音频片段，拼接写入本地 MP3。设置页的“试听配音”会用当前配置生成一段短音频预览。

## 音频素材

成片合成支持两类音频素材：

- 背景 BGM：内置目录 `assets/bgm/`，用户上传目录 `workspace/bgm/`
- 开头音效：默认使用 `assets/sfx/gear.mp3`，用户上传目录 `workspace/sfx/`

用户上传音频支持 `mp3`、`wav`、`m4a`、`aac`、`flac`、`ogg`，单个文件上限为 `100MB`。`workspace/` 已在 `.gitignore` 中忽略，上传素材会保留在本地工作区。

## 分镜数据格式

分镜数据是工作台内部承接生图和视频合成的结构。普通使用时不需要手写；页面会在“生成口播并拆分镜”后自动生成。

```json
{
  "title": "自助餐成瘾者回本哥的人生",
  "style_preset": "人生副本视觉风格",
  "shots": [
    {
      "id": 1,
      "voiceover": "今天体验的人生副本是：自助餐成瘾者回本哥的人生。",
      "visual": "他站在自助餐门口，像要参加一场命运审判。",
      "punch": "副本开启",
      "image_prompt": "中文生图提示词",
      "video_prompt": "中文镜头运动提示词",
      "image_path": "可选的本地图片路径",
      "image_url": "可选的浏览器访问地址"
    }
  ]
}
```

## API

```text
GET  /api/example
GET  /api/projects
GET  /api/project/current
POST /api/project/current
POST /api/project/activate
POST /api/project/delete
GET  /api/prompt/default
GET  /api/prompt/copy-xianxia
GET  /api/prompt/copy-to-story
GET  /api/prompt/image
GET  /api/prompt/theme
GET  /api/templates
GET  /api/templates/{template_id}
GET  /api/templates/{template_id}/prompt/{kind}
POST /api/text/generate-copy
POST /api/text/generate-theme
POST /api/text/revise-theme
POST /api/text/copy-to-story
POST /api/text/generate
POST /api/llm/generate
POST /api/settings/test-text
POST /api/settings/test-image
POST /api/image/generate-story
POST /api/image/regenerate-shot
GET  /api/bgm
POST /api/bgm/upload
GET  /api/intro-sfx
POST /api/intro-sfx/upload
POST /api/render
POST /api/render/jobs
GET  /api/render/jobs/{job_id}
```

`/api/render` 会输出到：

```text
workspace/{project_id}/final.mp4
```

## 开源注意事项

仓库默认只分发源码、提示词模板和必要的示例文件。`.env`、API Key、本地生成的 `workspace/`、音频、字幕、视频及其他私有凭据均不属于公开分发内容。

## 许可证

MIT
