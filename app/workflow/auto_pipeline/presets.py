"""旧版「文案类型 preset」接口，现在全部转发到创作模板（templates/<id>.json）。

保留这些函数名和签名，是因为自动流水线的步骤、项目状态和测试都在用；
新增品类只需要加一个模板 JSON，不用再改这里的任何分支。
"""

from __future__ import annotations

from typing import Any

from app.content.templates import (
    DEFAULT_TEMPLATE_ID,
    RANDOM_TEMPLATE_VALUE,
    shared_prompt,
    template_prompt,
    theme_profile,
    resolve_template_id,
)


def _default_copy_prompt(preset: Any = DEFAULT_TEMPLATE_ID) -> str:
    return template_prompt(preset, "copy")


def _resolve_copy_preset(value: Any) -> str:
    return resolve_template_id(value)


def _copy_preset_theme_profile(preset: Any) -> dict[str, str]:
    return theme_profile(preset)


def _copy_preset_theme_instruction(preset: Any) -> str:
    """自动流水线使用的选题约束文本，措辞与旧版保持一致。"""
    profile = _copy_preset_theme_profile(preset)
    return "\n".join([
        f"本次自动流水线已经选定文案类型：{profile['label']}。",
        f"选题必须适配这个文案类型，只能从这个范围中抽取：{profile['domain']}。",
        f"主题和主题介绍的情绪/结构方向：{profile['direction']}",
        f"可参考的选题形态：{profile['examples']}",
        f"必须避开：{profile['avoid']}",
        "如果用户提供了顶层要求，例如“猎奇”“温馨”“斗罗大陆世界观”，只能在上述文案类型范围内吸收这些要求，不要改变文案类型。",
        "输出的 title、direction、topic、intro 都要能直接支撑后续对应类型的口播文案生成。",
    ])


def _job_template_id(job: dict[str, Any]) -> str:
    """解析任务实际使用的模板，并把 template_id / 旧字段 copy_preset 都写回。"""
    input_data = job.get("input") or {}
    raw = input_data.get("template_id") or input_data.get("copy_preset") or RANDOM_TEMPLATE_VALUE
    template_id = _resolve_copy_preset(raw)
    if input_data.get("template_id") != template_id or input_data.get("copy_preset") != template_id:
        input_data["template_id"] = template_id
        input_data["copy_preset"] = template_id
        job["input"] = input_data
    return template_id


def _job_copy_preset(job: dict[str, Any]) -> str:
    """兼容旧调用：返回值与 _job_template_id 相同。"""
    return _job_template_id(job)


def _default_copy_to_story_prompt(template_id: Any = DEFAULT_TEMPLATE_ID) -> str:
    return template_prompt(template_id, "copy_to_story")


def _default_image_prompt(template_id: Any = DEFAULT_TEMPLATE_ID) -> str:
    return template_prompt(template_id, "image_style")


def _default_improve_prompt() -> str:
    return shared_prompt("improve_image")
