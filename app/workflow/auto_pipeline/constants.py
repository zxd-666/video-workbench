from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any


from app.content import templates as _template_registry

AUTO_ACTIVE_STATUSES = {"queued", "running", "waiting_child_job"}

RENDER_STALL_SECONDS = 30 * 60

_RENDER_STALL_MSG = "渲染任务长时间无进展，疑似后台渲染已停止，请重试"

STEP_KEYS = [
    ("theme_ideas", "生成选题方向"),
    ("select_idea", "选择方向"),
    ("theme", "生成主题"),
    ("copy", "生成口播"),
    ("storyboard", "拆分镜"),
    ("improve_prompts", "优化图片提示词"),
    ("images", "生成图片"),
    ("cover", "选择封面"),
    ("render", "渲染视频"),
]

_runner = ThreadPoolExecutor(max_workers=2)

_lock = threading.RLock()

_cancelled: set[str] = set()

_runtime_secrets: dict[str, dict[str, Any]] = {}

_ACTIVE_AUTO_IDS: set[str] = set()

IMAGE_REPAIR_SINGLE_RETRY_SIZE = 1

IMAGE_REPAIR_BURST_SIZE = 9

IMAGE_REPAIR_INFINITE_BURST_SIZE = 4

# 模板清单来自 templates/*.json，新增品类不需要改这里。
COPY_PROMPT_PRESETS: tuple[str, ...] = _template_registry.template_ids()

COPY_PRESET_THEME_PROFILES: dict[str, dict[str, str]] = {
    template.id: dict(template.theme) for template in _template_registry.load_templates()
}

class AutoPipelineError(RuntimeError):
    pass

class AutoPipelineCancelled(AutoPipelineError):
    pass

