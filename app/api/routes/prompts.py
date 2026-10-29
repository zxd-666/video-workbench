from fastapi import APIRouter, HTTPException

from app.content.templates import DEFAULT_TEMPLATE_ID, shared_prompt, template_prompt
from app.providers.image.adapter import load_image_prompt
from app.providers.llm.adapter import load_copy_to_story_prompt, load_improve_image_prompt, load_theme_ideas_prompt, load_theme_prompt


router = APIRouter()

# 旧接口保留给已存在的页面和书签；内容统一由 templates/ 清单里的提示词文件提供。
_LEGACY_COPY_TEMPLATE_IDS = {
    "default": DEFAULT_TEMPLATE_ID,
    "copy-xianxia": "xianxia",
    "copy-reality-breakout": "reality_breakout",
    "copy-reality-stop-loss": "reality_stop_loss",
    "copy-reality-burnout-support": "reality_burnout_support",
    "copy-fantasy-wuxia": "fantasy_wuxia",
    "copy-fantasy-zombie": "fantasy_zombie",
    "copy-fantasy-otherworld": "fantasy_otherworld",
    "copy-fantasy-cyberpunk": "fantasy_cyberpunk",
    "copy-fantasy-weird-rules": "fantasy_weird_rules",
}


def _legacy_copy_prompt(route_key: str) -> dict[str, str]:
    return {"prompt": template_prompt(_LEGACY_COPY_TEMPLATE_IDS[route_key], "copy")}


@router.get("/api/prompt/default")
def default_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("default")


@router.get("/api/prompt/copy-xianxia")
def copy_xianxia_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-xianxia")


@router.get("/api/prompt/copy-reality-breakout")
def copy_reality_breakout_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-reality-breakout")


@router.get("/api/prompt/copy-reality-stop-loss")
def copy_reality_stop_loss_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-reality-stop-loss")


@router.get("/api/prompt/copy-reality-burnout-support")
def copy_reality_burnout_support_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-reality-burnout-support")


@router.get("/api/prompt/copy-fantasy-wuxia")
def copy_fantasy_wuxia_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-fantasy-wuxia")


@router.get("/api/prompt/copy-fantasy-zombie")
def copy_fantasy_zombie_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-fantasy-zombie")


@router.get("/api/prompt/copy-fantasy-otherworld")
def copy_fantasy_otherworld_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-fantasy-otherworld")


@router.get("/api/prompt/copy-fantasy-cyberpunk")
def copy_fantasy_cyberpunk_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-fantasy-cyberpunk")


@router.get("/api/prompt/copy-fantasy-weird-rules")
def copy_fantasy_weird_rules_prompt() -> dict[str, str]:
    return _legacy_copy_prompt("copy-fantasy-weird-rules")


@router.get("/api/prompt/image")
def image_prompt() -> dict[str, str]:
    return {"prompt": load_image_prompt()}


@router.get("/api/prompt/improve-image")
def improve_image_prompt() -> dict[str, str]:
    return {"prompt": load_improve_image_prompt()}


@router.get("/api/prompt/copy-to-story")
def copy_to_story_prompt() -> dict[str, str]:
    return {"prompt": load_copy_to_story_prompt()}


@router.get("/api/prompt/theme")
def theme_prompt() -> dict[str, str]:
    return {"prompt": load_theme_prompt()}


@router.get("/api/prompt/theme-ideas")
def theme_ideas_prompt() -> dict[str, str]:
    return {"prompt": load_theme_ideas_prompt()}


@router.get("/api/prompt/shared/{kind}")
def shared_prompt_route(kind: str) -> dict[str, str]:
    try:
        return {"prompt": shared_prompt(kind)}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
