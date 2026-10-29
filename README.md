# video-workbench

本地 AI 短视频创作工作台：把主题拆成口播文案和分镜，生成分镜图，配上 TTS、字幕和 BGM，最后用 FFmpeg 合成竖屏 MP4。

产品名是「短视频创作工作台」；仓库、镜像、容器和程序统一使用 `video-workbench`。

> 项目不内置第三方模型接口地址或商业素材。文本、图片、语音服务由使用者在「设置」或 `.env` 中自行接入。

## 功能

- **五步工作流**：输入主题 → 生成文案 → 拆分分镜 → 生成分镜图 → 生成视频；顶部步骤条可直接跳转对应页面。
- **自动流水线**：输入顶层要求，或留空让系统自动生成选题方向，后端依次完成主题、文案、分镜、图片、封面和成片。
- **创作模板**：内置 13 个模板、4 个分类，默认「通用 · 叙事口播」；新增题材只需添加一个 JSON 文件。
- **提示词可编辑**：文案、口播拆分镜、图片、图片优化、选题方向等提示词都可以在页面里修改，并按模板分别保存。
- **分镜图**：批量生成、并发控制、失败重试、单张重抽、封面选择；支持项目级参考图集合。
- **配音**：Edge TTS（无需密钥）、MiniMax T2A HTTP、豆包语音 / 火山引擎。
- **音频与字幕**：BGM、开头音效、开头模板、SRT/ASS 字幕。
- **成片与剪映**：FFmpeg 合成 MP4，默认 1080×1920 / 9:16；可导出剪映草稿并在剪映中继续编辑。
- **项目管理**：自动保存、历史项目切换、刷新恢复，生成物统一保存在本地 `workspace/`。

## 快速开始

### Docker Compose（推荐）

要求已安装 Docker Desktop 或 Docker Engine + Compose。

```bash
cp .env.example .env
# 编辑 .env，至少填写文本和图片接口；也可以先启动，再在页面「设置」里填写
docker compose up -d --build
```

打开：

```text
http://127.0.0.1:7860
```

常用命令：

```bash
docker compose ps                 # 查看状态
docker compose logs -f            # 查看日志
docker compose down               # 停止
curl http://127.0.0.1:7860/api/health
```

Compose 默认只监听 `127.0.0.1:7860`，不会把服务暴露到局域网。

### 本地运行

环境要求：

- Python 3.11+
- FFmpeg / FFprobe 已在 `PATH` 中
- `requirements.txt` 中的 Python 依赖

```bash
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 7860
```

后端启动时会读取项目根目录的 `.env`；如果 `.env` 不存在，仍然可以启动，并在页面「设置」里填写接口。

### Windows EXE

在 Windows 构建机上安装 Python 依赖后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1
```

生成：

```text
dist\video-workbench-windows-x64.zip
```

解压后双击 `video-workbench.exe` 即可启动。把 `.env` 放在 exe 同级目录可配置接口；项目数据、上传素材、生成图片和视频会写入 exe 同级的 `workspace/`，不会写到系统其他位置。

## 配置

有三种配置入口，优先级从高到低：

1. 页面「设置」中填写的接口地址、模型和密钥。
2. 项目根目录的 `.env`（Windows EXE 为 exe 同级目录的 `.env`）。
3. 代码中的 provider 默认值（仅用于非敏感默认项）。

页面里的 API Key 保存在浏览器 `sessionStorage`，关闭浏览器会话后需要重新填写；Base URL、模型等非敏感设置保存在 `localStorage`。

### 文本接口

```dotenv
TEXT_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-5.5
LLM_API_KEY=
LLM_TEMPERATURE=0.8
```

支持：

- `openai`：OpenAI-compatible Chat Completions
- `anthropic`：Anthropic Messages API
- `gemini`：Google Gemini
- 任何 OpenAI-compatible 网关（例如本地 gemini-web2api）使用 `openai` provider 接入，见下文

Base URL 建议填到 `/v1`，例如 `https://api.openai.com/v1`。工作台会自动拼接 `/chat/completions`；如果填的是完整 endpoint，也会直接使用。

### 图片接口

```dotenv
IMAGE_PROVIDER=openai
IMAGE_BASE_URL=https://api.openai.com/v1
IMAGE_MODEL=gpt-image-2
IMAGE_API_KEY=
IMAGE_SIZE=9:16
```

支持：

- `openai`：OpenAI-compatible Images API，返回 `data[0].url` 或 `data[0].b64_json`
- `gemini`：Google Gemini / Imagen

图片比例：

```text
9:16  竖屏，默认
1:1   正方形
16:9  横屏
```

注意：图片比例和成片画布是两个概念。当前成片画布固定为 1080×1920（9:16），横屏或方形图片会被适配进竖屏画布。

### 配音接口

```dotenv
TTS_PROVIDER=edge
```

- `edge`：Edge TTS，默认，无需密钥。
- `minimax`：MiniMax T2A HTTP，需填写 `MINIMAX_TTS_BASE_URL`、`MINIMAX_TTS_API_KEY`、模型和音色 ID。
- `doubao`：豆包语音 / 火山引擎，需填写 `DOUBAO_TTS_BASE_URL`、`DOUBAO_TTS_API_KEY` 和 Resource ID / 音色。

完整变量见 [`.env.example`](.env.example)。

### 可选：Gemini Web2API

Gemini Web2API 是第三方项目，不随本仓库分发。需要时先单独启动它：

```bash
pip install httpx
python gemini_web2api.py
```

然后按 OpenAI-compatible 方式配置：

```dotenv
TEXT_PROVIDER=openai
LLM_BASE_URL=http://127.0.0.1:8081/v1
LLM_MODEL=gemini-3.5-flash-thinking
LLM_API_KEY=sk-local
```

在页面「设置」里选择 `OpenAI Compatible`，填写同样的地址和模型即可。第三方项目的可用性、模型和使用条款由该项目及其服务提供方决定。

## 使用流程

页面顶部是五个创作步骤，点击任意步骤可跳转：

```text
1 输入主题 -> 2 生成文案 -> 3 拆分分镜 -> 4 生成分镜图 -> 5 生成视频
```

1. **主题策划**：填写主题和主题介绍，或用 AI 生成选题方向。主题和介绍都填写后，才允许进入文案生成。
2. **文案**：生成口播文案并拆分镜，可编辑文案提示词和分镜粒度。
3. **分镜**：检查分镜卡片、镜头文案、画面描述和图片提示词；可选择参考图集合。
4. **分镜图**：批量生成、失败重试、单张重抽，并选择封面。
5. **成片**：选择 TTS、BGM、开头音效和开头模板，生成字幕并渲染 MP4；也可以导出剪映草稿。

其他页面：

- **项目**：查看、切换和删除历史项目。
- **自动流水线**：不进入五步流程，直接让后端跑完整条链路。
- **参考图资产库**：创建图片集合，给参考图命名并绑定到项目。
- **设置**：配置文本、图片、TTS 接口和密钥。

## 自动流水线

自动流水线由后端任务执行，前端只负责创建任务和轮询状态，因此刷新页面或关闭浏览器不会中断任务。

输入可以是空，也可以是顶层要求，例如：

```text
猎奇
温馨
现代都市，反转强一点
县城，宝妈，压抑但结尾温暖
```

流程：

```text
顶层要求或空输入
-> 生成候选选题方向
-> 自动选择方向
-> 生成主题和主题介绍
-> 生成口播文案
-> 拆分镜
-> 优化图片提示词
-> 生成分镜图片
-> 选择封面
-> 渲染 MP4
-> 保存项目和产物
```

任务状态保存在：

```text
workspace/projects/{项目ID}/jobs/{job_id}.json
```

支持创建、查询、取消和恢复。每一步都会先检查已有产物，恢复时跳过已经完成的步骤，避免重复消耗接口额度。

接口：

```text
POST /api/auto-pipeline/jobs
GET  /api/auto-pipeline/jobs
GET  /api/auto-pipeline/jobs/{project_id}/{job_id}
POST /api/auto-pipeline/jobs/{project_id}/{job_id}/cancel
POST /api/auto-pipeline/jobs/{project_id}/{job_id}/resume
```

更细的流程设计见 [`docs/auto_pipeline_implementation.md`](docs/auto_pipeline_implementation.md)。

## 创作模板

模板放在 `templates/<id>.json`，文件名必须与 `id` 一致。当前内置 13 个模板，分为：

- 通用：叙事口播、知识科普
- 商业：带货种草
- 人生副本 · 现实：理智破局、燃尽托举、反转压迫、止损断舍离
- 人生副本 · 超现实：赛博异化、异世界、规则怪谈、武侠江湖、丧尸末日、修仙

“人生副本”只是内置的剧情类创作模板，不是产品名；口播、科普、带货等通用题材使用「通用」分类即可。

模板 JSON 的主要字段：

- `id` / `label` / `short_label` / `category` / `order`：标识、展示名、分类和排序
- `description`：下拉框下方的说明
- `theme`：选题阶段使用的领域、方向、示例和追加指令
- `defaults`：默认图片比例、分镜粒度、开头模板和 TTS 预设
- `prompts`：该模板的 `copy`、`copy_to_story`、`image_style`、`story_shots` 提示词文件路径

提示词留空时回落到共享文件：

```text
prompt.txt
prompts/image_style.md
prompts/copy_to_story.md
prompts/story_shots.md
```

新增模板不需要改前端或后端代码，新增 JSON 后重启服务即可。

## 项目与产物

项目数据默认保存在：

```text
workspace/
├── active_project.json
├── projects/
│   └── {项目ID}/
│       ├── state.json
│       ├── metadata.json
│       ├── copy.txt
│       ├── story.json
│       ├── result.txt
│       ├── images/
│       ├── voice.mp3
│       ├── subtitle.srt
│       ├── final.mp4
│       └── jobs/
├── reference_collections/
│   └── {集合ID}/
├── bgm/
└── sfx/
```

`workspace/` 已在 `.gitignore` 中忽略，生成物和上传素材不会进入 Git。切换项目、刷新页面都会优先恢复当前项目。

## API 概览

```text
# 健康检查与示例
GET  /api/health
GET  /api/example

# 项目
GET  /api/projects
GET  /api/project/current
POST /api/project/current
POST /api/project/activate
POST /api/project/delete

# 模板与提示词
GET  /api/templates
GET  /api/templates/{template_id}
GET  /api/templates/{template_id}/prompt/{kind}
GET  /api/prompt/default
GET  /api/prompt/image
GET  /api/prompt/theme
POST /api/text/generate-copy
POST /api/text/generate-theme
POST /api/text/generate-theme-ideas
POST /api/text/revise-theme
POST /api/text/copy-to-story
POST /api/text/generate
POST /api/text/improve-image-prompt
POST /api/llm/generate
POST /api/settings/test-text
POST /api/settings/test-image

# 图片
POST /api/image/generate-story
POST /api/image/regenerate-shot
POST /api/image/jobs
GET  /api/image/jobs
GET  /api/image/jobs/{project_id}/{job_id}
POST /api/image/jobs/{project_id}/{job_id}/cancel

# 音频、渲染与剪映
GET  /api/bgm
POST /api/bgm/upload
GET  /api/intro-sfx
POST /api/intro-sfx/upload
POST /api/tts/preview
GET  /api/tts/doubao/voices
POST /api/render
POST /api/render/jobs
GET  /api/render/jobs/{job_id}
POST /api/render/intro-previews
POST /api/jianying/drafts
POST /api/jianying/drafts/jobs
GET  /api/jianying/drafts/jobs/{job_id}
POST /api/jianying/drafts/open

# 参考图资产
GET    /api/reference-collections
POST   /api/reference-collections
GET    /api/reference-collections/{collection_id}
DELETE /api/reference-collections/{collection_id}
POST   /api/reference-collections/{collection_id}/assets
DELETE /api/reference-collections/{collection_id}/assets/{asset_id}

# 自动流水线
POST /api/auto-pipeline/jobs
GET  /api/auto-pipeline/jobs
GET  /api/auto-pipeline/jobs/{project_id}/{job_id}
POST /api/auto-pipeline/jobs/{project_id}/{job_id}/cancel
POST /api/auto-pipeline/jobs/{project_id}/{job_id}/resume
```

## 开发与自检

安装开发依赖：

```bash
pip install -r requirements-dev.txt
```

运行测试：

```bash
pytest -q
```

启动服务后运行 smoke check：

```bash
python scripts/smoke_check.py
```

如果 `.env` 已经配置好文本和图片接口，可以同时测试外部连接：

```bash
python scripts/smoke_check.py --external
```

前端入口是 `static/app.js`，其余模块按职责拆分在 `static/js/`：

- `api.js`：HTTP 请求封装
- `ui.js`：DOM 查询、状态、设置抽屉、标签切换
- `settings.js`：本地设置、接口配置和请求 payload
- `story-view.js`：分镜 JSON、字数统计、分镜卡片渲染
- `project-store.js`：项目保存、恢复、切换和自动保存
- `workflow-*.js`：主题、文案、图片、媒体、渲染和连接测试等流程

## 安全与隐私

- `.env` 已被 `.gitignore` 忽略，不要提交真实密钥。
- 页面里的 API Key 只保存在浏览器会话存储；`.env` 中的密钥由本地后端读取。
- 如果密钥曾经提交、截图或分享，请立即在服务商处轮换。
- 上传素材、生成图片、字幕、音频和成片都在本地 `workspace/`，默认不进入 Git。
- 更多说明见 [`SECURITY.md`](SECURITY.md)。

## 使用声明与许可证

本项目主要用于学习交流、技术研究与个人本地测试。用于商业场景时，请自行确认所接入的模型/API、生成内容、音乐、音效、图片、字体和平台规则具备相应授权；禁止用于任何违法违规场景。

项目代码不包含、也不授权任何第三方音乐、音效、图片、字体、视频、模型服务或平台接口资源。使用者接入的 API、模型、提示词、生成内容及本地素材，均需自行确认来源合法。

本仓库以 MIT 许可证分发，详见 [`LICENSE`](LICENSE)。再分发时请保留许可证中的版权声明。
