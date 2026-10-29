from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.content import templates as registry
from app.main import app
from app.workflow.auto_pipeline.constants import COPY_PRESET_THEME_PROFILES, COPY_PROMPT_PRESETS
from app.workflow.auto_pipeline.presets import (
    _copy_preset_theme_instruction,
    _copy_preset_theme_profile,
    _default_copy_prompt,
    _default_copy_to_story_prompt,
    _default_image_prompt,
    _resolve_copy_preset,
)


def test_all_template_manifests_are_valid():
    loaded = registry.validate_templates()
    assert loaded
    ids = [template.id for template in loaded]
    assert len(ids) == len(set(ids))
    assert registry.DEFAULT_TEMPLATE_ID in ids


def test_legacy_preset_names_are_preserved():
    assert set(COPY_PROMPT_PRESETS) == {template.id for template in registry.load_templates()}
    assert COPY_PRESET_THEME_PROFILES["reality_reverse"]["label"] == "现实反转压迫型"
    assert "general_oral" in COPY_PROMPT_PRESETS


def test_legacy_alias_resolves_to_default_template():
    assert _resolve_copy_preset("reality") == "reality_reverse"
    assert _resolve_copy_preset("") == registry.DEFAULT_TEMPLATE_ID
    assert _resolve_copy_preset("does_not_exist") == registry.DEFAULT_TEMPLATE_ID


def test_random_resolves_to_a_real_template():
    for _ in range(20):
        assert _resolve_copy_preset("random") in COPY_PROMPT_PRESETS


def test_default_copy_prompt_matches_template_file():
    expected = (registry.ROOT / "prompts" / "copy_general_oral.md").read_text(encoding="utf-8")
    assert _default_copy_prompt("general_oral") == expected
    assert _default_copy_prompt("reality_reverse") == (registry.ROOT / "prompts" / "copy_reality.md").read_text(encoding="utf-8")


def test_shared_default_prompts_are_genre_neutral():
    shared_copy = (registry.ROOT / "prompt.txt").read_text(encoding="utf-8")
    shared_theme_ideas = (registry.ROOT / "prompts" / "theme_ideas.md").read_text(encoding="utf-8")
    shared_theme_plan = (registry.ROOT / "prompts" / "theme_plan.md").read_text(encoding="utf-8")
    shared_story = (registry.ROOT / "prompts" / "story_shots.md").read_text(encoding="utf-8")
    shared_image = (registry.ROOT / "prompts" / "image_style.md").read_text(encoding="utf-8")
    for text in (shared_copy, shared_theme_ideas, shared_theme_plan, shared_story, shared_image):
        assert "人生副本" not in text
        assert "100种人生副本" not in text
        assert "光头" not in text


def test_life_copy_templates_keep_their_own_storyboard_prompt():
    life_copy = (registry.ROOT / "prompts" / "story_shots_life_copy.md").read_text(encoding="utf-8")
    assert "人生副本" in life_copy
    for template_id in ("reality_reverse", "fantasy_wuxia", "xianxia"):
        assert registry.template_prompt(template_id, "story_shots") == life_copy
    assert registry.template_prompt("general_oral", "story_shots") == (registry.ROOT / "prompts" / "story_shots.md").read_text(encoding="utf-8")


def test_life_copy_templates_keep_their_own_image_style():
    life_image = (registry.ROOT / "prompts" / "image_style_life_copy.md").read_text(encoding="utf-8")
    assert "光头" in life_image
    for template_id in ("reality_reverse", "reality_breakout", "fantasy_cyberpunk", "xianxia"):
        assert registry.template_prompt(template_id, "image_style") == life_image
    assert registry.template_prompt("general_oral", "image_style") == (registry.ROOT / "prompts" / "image_style.md").read_text(encoding="utf-8")


def test_storyboard_and_image_prompts_fall_back_to_shared_defaults():
    shared_story = (registry.ROOT / "prompts" / "copy_to_story.md").read_text(encoding="utf-8")
    shared_image = (registry.ROOT / "prompts" / "image_style.md").read_text(encoding="utf-8")
    assert _default_copy_to_story_prompt() == shared_story
    assert _default_copy_to_story_prompt("reality_reverse") == shared_story
    assert _default_image_prompt() == shared_image
    assert _default_image_prompt("product_planting") == shared_image
    assert _default_image_prompt("reality_reverse") != shared_image


def test_template_theme_instruction_includes_template_scope():
    instruction = _copy_preset_theme_instruction("knowledge_science")
    profile = _copy_preset_theme_profile("knowledge_science")
    assert profile["label"] in instruction
    assert profile["domain"] in instruction


def test_templates_payload_shape():
    payload = registry.templates_payload()
    assert payload["default_template"] == registry.DEFAULT_TEMPLATE_ID
    assert payload["random_value"] == "random"
    assert "通用" in payload["categories"]
    assert len(payload["templates"]) == len(registry.template_ids())
    first = payload["templates"][0]
    for key in ("id", "label", "category", "theme", "prompts", "defaults"):
        assert key in first
    assert first["theme"]["instruction"]
    assert first["prompts"]["copy"]


def test_templates_api_lists_general_templates():
    client = TestClient(app)
    response = client.get("/api/templates")
    assert response.status_code == 200
    data = response.json()
    ids = [item["id"] for item in data["templates"]]
    assert "general_oral" in ids
    assert "knowledge_science" in ids
    assert "product_planting" in ids
    assert data["shared"]["copy_to_story"]


def test_templates_api_single_template_and_404():
    client = TestClient(app)
    ok = client.get("/api/templates/general_oral")
    assert ok.status_code == 200
    assert ok.json()["id"] == "general_oral"
    missing = client.get("/api/templates/not_a_template")
    assert missing.status_code == 404


def test_legacy_prompt_endpoints_still_work():
    client = TestClient(app)
    for path, template_id in (
        ("/api/prompt/default", "general_oral"),
        ("/api/prompt/copy-xianxia", "xianxia"),
        ("/api/prompt/copy-reality-breakout", "reality_breakout"),
        ("/api/prompt/copy-fantasy-weird-rules", "fantasy_weird_rules"),
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["prompt"] == _default_copy_prompt(template_id)


def test_template_overrides_are_local_files():
    root = registry.ROOT.resolve()
    for template in registry.load_templates():
        for kind, relative in template.prompts.items():
            if not relative:
                continue
            path = (registry.ROOT / relative).resolve()
            assert path.is_file()
            assert str(path).startswith(str(root))


def test_manifest_files_match_ids():
    directory = registry.TEMPLATES_DIR
    for path in directory.glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["id"] == path.stem


@pytest.mark.parametrize("template_id", ["general_oral", "knowledge_science", "product_planting"])
def test_new_templates_have_required_defaults(template_id):
    defaults = registry.template_defaults(template_id)
    assert defaults["image_size"] == "9:16"
    assert defaults["storyboard_granularity"] in {"coarse", "balanced", "fine"}
    assert defaults["tts_preset"]
