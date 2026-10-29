"""创作模板接口。

页面启动时拉一次 ``GET /api/templates``，就能拿到所有品类的展示信息、
选题约束和已经解析好的提示词全文，不再需要为每个品类写一个接口。
"""

from fastapi import APIRouter, HTTPException

from app.content.templates import (
    TemplateError,
    get_template,
    resolve_template_id,
    template_prompt,
    templates_payload,
)


router = APIRouter()


@router.get("/api/templates")
def list_templates() -> dict:
    try:
        return templates_payload()
    except TemplateError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/templates/{template_id}")
def get_template_detail(template_id: str) -> dict:
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"模板不存在：{template_id}")
    return template.to_payload()


@router.get("/api/templates/{template_id}/prompt/{kind}")
def get_template_prompt(template_id: str, kind: str) -> dict[str, str]:
    try:
        return {
            "template_id": resolve_template_id(template_id),
            "kind": kind,
            "prompt": template_prompt(template_id, kind),
        }
    except TemplateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
