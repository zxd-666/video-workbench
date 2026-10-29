"""内容资源：创作模板（templates/*.json）。"""

from .templates import (
    DEFAULT_TEMPLATE_ID,
    RANDOM_TEMPLATE_VALUE,
    Template,
    TemplateError,
    get_template,
    list_templates,
    resolve_template_id,
    shared_prompt,
    template_defaults,
    template_ids,
    template_prompt,
    templates_payload,
    theme_instruction,
    theme_profile,
    validate_templates,
)

__all__ = [
    "DEFAULT_TEMPLATE_ID",
    "RANDOM_TEMPLATE_VALUE",
    "Template",
    "TemplateError",
    "get_template",
    "list_templates",
    "resolve_template_id",
    "shared_prompt",
    "template_defaults",
    "template_ids",
    "template_prompt",
    "templates_payload",
    "theme_instruction",
    "theme_profile",
    "validate_templates",
]
