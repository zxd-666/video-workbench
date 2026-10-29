"""创作模板加载器。

每个 ``templates/<id>.json`` 描述一种视频类型：选题范围、文案提示词、
图片风格提示词、默认渲染参数。后端和前端都只读这一份清单，
新增一个品类只需要加一个 JSON 文件，不需要改 Python 分支或前端下拉框。

字段说明（完整示例见 templates/ 目录）：

- id：稳定标识，只允许小写字母、数字、下划线，写进项目 state 后不要再改。
- label / short_label / category / description / order：前端下拉框展示用，
  同一个 category 会合并成一个 optgroup。
- opening：口播开场白，写进 prompt 里做风格锚点，也用于页面提示。
- theme：选题方向约束（label/domain/direction/examples/avoid），
  自动流水线和「AI 出方向」都用它拼约束。
- prompts：相对项目根目录的提示词文件路径；留空表示用共享默认。
- defaults：选中模板时带出的默认渲染参数，用户仍可手动改。
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.paths import ROOT

logger = logging.getLogger("video-workbench.templates")

TEMPLATES_DIR = ROOT / "templates"

DEFAULT_TEMPLATE_ID = "general_oral"

RANDOM_TEMPLATE_VALUE = "random"

# 兼容旧客户端/旧项目里出现过的文案类型别名。
LEGACY_TEMPLATE_ALIASES = {
    "": DEFAULT_TEMPLATE_ID,
    "default": DEFAULT_TEMPLATE_ID,
    "reality": "reality_reverse",
}

# 模板可以单独覆盖的提示词；没有覆盖时回落到共享默认。
TEMPLATE_PROMPT_KINDS = ("copy", "copy_to_story", "image_style", "story_shots")

# 所有模板共用的提示词文件。
SHARED_PROMPT_PATHS = {
    "copy": "prompt.txt",
    "copy_to_story": "prompts/copy_to_story.md",
    "image_style": "prompts/image_style.md",
    "story_shots": "prompts/story_shots.md",
    "improve_image": "prompts/image_prompt_improve.md",
    "theme_ideas": "prompts/theme_ideas.md",
    "theme_plan": "prompts/theme_plan.md",
}

DEFAULT_TEMPLATE_DEFAULTS = {
    "image_size": "9:16",
    "storyboard_granularity": "balanced",
    "intro_template": "none",
    "tts_preset": "male_steady",
}

_VALID_IMAGE_SIZES = {"9:16", "1:1", "16:9"}
_VALID_GRANULARITIES = {"coarse", "balanced", "fine"}
_VALID_TTS_PRESETS = {"male_fast", "female_clear", "male_steady", "female_soft", "custom"}

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,39}$")

_THEME_KEYS = ("label", "domain", "direction", "examples", "avoid")


class TemplateError(RuntimeError):
    """模板清单不合法。"""


@dataclass(frozen=True)
class Template:
    id: str
    label: str
    short_label: str
    category: str
    description: str
    order: int
    opening: str
    theme: dict[str, str]
    prompts: dict[str, str | None]
    defaults: dict[str, Any]
    steps: tuple[str, ...] = field(default_factory=tuple)
    source: str = ""

    def prompt_path(self, kind: str) -> Path | None:
        value = self.prompts.get(kind)
        return (ROOT / value) if value else None

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "short_label": self.short_label,
            "category": self.category,
            "description": self.description,
            "order": self.order,
            "opening": self.opening,
            "theme": {**self.theme, "instruction": theme_instruction(self.id)},
            "defaults": dict(self.defaults),
            "prompts": {kind: template_prompt(self.id, kind) for kind in TEMPLATE_PROMPT_KINDS},
        }


_cache: tuple[tuple[tuple[str, int], ...], tuple[Template, ...]] | None = None


def _read_text(relative: str) -> str:
    path = ROOT / relative
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TemplateError(f"提示词文件不存在：{relative}") from exc


def _as_text(value: Any, *, field_name: str, template_id: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise TemplateError(f"模板 {template_id} 缺少字段 {field_name}")
    return text


def _parse_template(path: Path) -> Template:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TemplateError(f"模板文件不是合法 JSON：{path.name}（{exc}）") from exc
    if not isinstance(raw, dict):
        raise TemplateError(f"模板文件顶层必须是对象：{path.name}")

    template_id = str(raw.get("id") or "").strip()
    if not _ID_PATTERN.match(template_id):
        raise TemplateError(f"模板 id 不合法：{template_id or path.name}")
    if path.stem != template_id:
        raise TemplateError(f"模板文件名必须与 id 一致：{path.name}（id={template_id}）")

    theme_raw = raw.get("theme")
    if not isinstance(theme_raw, dict):
        raise TemplateError(f"模板 {template_id} 缺少 theme 对象")
    theme = {key: _as_text(theme_raw.get(key), field_name=f"theme.{key}", template_id=template_id) for key in _THEME_KEYS}

    prompts_raw = raw.get("prompts") or {}
    if not isinstance(prompts_raw, dict):
        raise TemplateError(f"模板 {template_id} 的 prompts 必须是对象")
    prompts: dict[str, str | None] = {}
    for kind in TEMPLATE_PROMPT_KINDS:
        value = prompts_raw.get(kind)
        if value in (None, "", False):
            prompts[kind] = None
            continue
        relative = str(value).strip()
        # 只允许指向项目内的提示词文件，拒绝绝对路径和 ../ 越界。
        candidate = (ROOT / relative).resolve()
        if not str(candidate).startswith(str(ROOT.resolve())) or not candidate.is_file():
            raise TemplateError(f"模板 {template_id} 的 prompts.{kind} 指向了不存在的文件：{relative}")
        prompts[kind] = relative

    defaults = dict(DEFAULT_TEMPLATE_DEFAULTS)
    defaults_raw = raw.get("defaults") or {}
    if not isinstance(defaults_raw, dict):
        raise TemplateError(f"模板 {template_id} 的 defaults 必须是对象")
    defaults.update({key: value for key, value in defaults_raw.items() if value not in (None, "")})
    if defaults["image_size"] not in _VALID_IMAGE_SIZES:
        raise TemplateError(f"模板 {template_id} 的 image_size 不合法：{defaults['image_size']}")
    if defaults["storyboard_granularity"] not in _VALID_GRANULARITIES:
        raise TemplateError(f"模板 {template_id} 的 storyboard_granularity 不合法：{defaults['storyboard_granularity']}")
    if defaults["tts_preset"] not in _VALID_TTS_PRESETS:
        raise TemplateError(f"模板 {template_id} 的 tts_preset 不合法：{defaults['tts_preset']}")

    steps_raw = raw.get("steps") or []
    if not isinstance(steps_raw, list):
        raise TemplateError(f"模板 {template_id} 的 steps 必须是数组")

    try:
        order = int(raw.get("order") or 0)
    except (TypeError, ValueError) as exc:
        raise TemplateError(f"模板 {template_id} 的 order 必须是整数") from exc

    return Template(
        id=template_id,
        label=_as_text(raw.get("label"), field_name="label", template_id=template_id),
        short_label=str(raw.get("short_label") or raw.get("label") or "").strip(),
        category=_as_text(raw.get("category"), field_name="category", template_id=template_id),
        description=str(raw.get("description") or "").strip(),
        order=order,
        opening=str(raw.get("opening") or "").strip(),
        theme=theme,
        prompts=prompts,
        defaults=defaults,
        steps=tuple(str(item) for item in steps_raw),
        source=path.name,
    )


def _stamp() -> tuple[tuple[str, int], ...]:
    if not TEMPLATES_DIR.is_dir():
        return ()
    return tuple(sorted((path.name, path.stat().st_mtime_ns) for path in TEMPLATES_DIR.glob("*.json")))


def validate_templates() -> tuple[Template, ...]:
    """严格校验并返回全部模板；有任何问题直接抛 TemplateError。

    测试和 ``GET /api/templates`` 的健康检查用它；运行时加载会跳过坏文件，
    避免一个手滑的 JSON 让整个服务起不来。
    """
    if not TEMPLATES_DIR.is_dir():
        raise TemplateError(f"模板目录不存在：{TEMPLATES_DIR}")
    templates = [_parse_template(path) for path in sorted(TEMPLATES_DIR.glob("*.json"))]
    if not templates:
        raise TemplateError("模板目录为空")
    seen: set[str] = set()
    for template in templates:
        if template.id in seen:
            raise TemplateError(f"模板 id 重复：{template.id}")
        seen.add(template.id)
    if DEFAULT_TEMPLATE_ID not in seen:
        raise TemplateError(f"缺少默认模板：{DEFAULT_TEMPLATE_ID}")
    return tuple(sorted(templates, key=lambda item: (item.order, item.id)))


def load_templates(refresh: bool = False) -> tuple[Template, ...]:
    """读取并缓存模板清单；模板文件变化后自动失效。"""
    global _cache
    stamp = _stamp()
    if not refresh and _cache is not None and _cache[0] == stamp:
        return _cache[1]
    loaded: list[Template] = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")) if TEMPLATES_DIR.is_dir() else []:
        try:
            loaded.append(_parse_template(path))
        except TemplateError as exc:
            logger.warning("跳过不合法的模板文件 %s：%s", path.name, exc)
    if not loaded:
        raise TemplateError("没有可用的创作模板，请检查 templates/ 目录")
    seen: set[str] = set()
    unique: list[Template] = []
    for template in loaded:
        if template.id in seen:
            logger.warning("模板 id 重复，已跳过：%s", template.id)
            continue
        seen.add(template.id)
        unique.append(template)
    templates = tuple(sorted(unique, key=lambda item: (item.order, item.id)))
    _cache = (stamp, templates)
    return templates


def list_templates() -> tuple[Template, ...]:
    return load_templates()


def template_ids() -> tuple[str, ...]:
    return tuple(template.id for template in load_templates())


def get_template(template_id: str) -> Template | None:
    key = str(template_id or "").strip()
    for template in load_templates():
        if template.id == key:
            return template
    return None


def resolve_template_id(value: Any) -> str:
    """把任意输入（random、旧别名、未知 id）解析成一个真实存在的模板 id。"""
    key = str(value or "").strip()
    if key == RANDOM_TEMPLATE_VALUE:
        return random.choice(template_ids())
    key = LEGACY_TEMPLATE_ALIASES.get(key, key)
    if get_template(key):
        return key
    return DEFAULT_TEMPLATE_ID


def template_prompt(template_id: str, kind: str) -> str:
    """读取模板提示词；模板没覆盖时回落到共享默认。"""
    template = get_template(resolve_template_id(template_id))
    if template is None:
        return _read_text(SHARED_PROMPT_PATHS.get(kind, "prompt.txt"))
    path = template.prompt_path(kind)
    if path is not None:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("模板 %s 的 %s 提示词文件丢失，回落到默认", template.id, kind)
    if kind in SHARED_PROMPT_PATHS:
        return _read_text(SHARED_PROMPT_PATHS[kind])
    raise TemplateError(f"未知的提示词类型：{kind}")


def shared_prompt(kind: str) -> str:
    if kind not in SHARED_PROMPT_PATHS:
        raise TemplateError(f"未知的提示词类型：{kind}")
    return _read_text(SHARED_PROMPT_PATHS[kind])


def template_defaults(template_id: str) -> dict[str, Any]:
    template = get_template(resolve_template_id(template_id))
    if template is None:
        return dict(DEFAULT_TEMPLATE_DEFAULTS)
    return dict(template.defaults)


def theme_profile(template_id: str) -> dict[str, str]:
    template = get_template(resolve_template_id(template_id))
    if template is None:
        template = get_template(DEFAULT_TEMPLATE_ID)
    return dict(template.theme) if template else {}


def theme_instruction(template_id: str) -> str:
    """自动流水线 / AI 出方向共用的选题约束文本。"""
    profile = theme_profile(template_id)
    if not profile:
        return ""
    return "\n".join([
        f"本次创作模板已选定：{profile['label']}。",
        f"选题必须适配这个模板，只能从这个范围中抽取：{profile['domain']}。",
        f"选题方向和情绪/结构走向：{profile['direction']}",
        f"可参考的选题形态：{profile['examples']}",
        f"必须避开：{profile['avoid']}",
        "如果用户提供了顶层要求，例如“猎奇”“温馨”“斗罗大陆世界观”，只能在上述范围内吸收这些要求，不要改变创作模板。",
        "输出的 title、direction、topic、intro 都要能直接支撑后续对应模板的口播文案生成。",
    ])


def templates_payload() -> dict[str, Any]:
    """给前端一次性下发的模板清单，包含已解析好的提示词全文。"""
    templates = load_templates()
    categories: list[str] = []
    for template in templates:
        if template.category not in categories:
            categories.append(template.category)
    return {
        "default_template": DEFAULT_TEMPLATE_ID,
        "random_value": RANDOM_TEMPLATE_VALUE,
        "categories": categories,
        "templates": [template.to_payload() for template in templates],
        "shared": {kind: shared_prompt(kind) for kind in ("theme_ideas", "theme_plan", "improve_image", "copy_to_story", "image_style", "story_shots")},
    }
