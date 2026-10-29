from __future__ import annotations

from app.image_adapter import ImageConfig, ImageError
from app.image_status import IMAGE_JOB_FAILED, IMAGE_JOB_QUEUED
from app.images.jobs import runner
from app.jobs.store import read_job, save_job


def _prepare(tmp_path, monkeypatch, *, shot_count: int = 10, concurrency: int = 4) -> dict:
    monkeypatch.setattr("app.core.paths.PROJECTS_DIR", tmp_path)
    job = {
        "job_id": "img_balance_dead",
        "project_id": "p_balance",
        "kind": "image",
        "status": "queued",
        "concurrency": concurrency,
        "items": [
            {"shot_index": index, "status": IMAGE_JOB_QUEUED, "attempt": 0}
            for index in range(shot_count)
        ],
    }
    save_job(job)
    return job


def test_account_level_error_stops_remaining_shots(tmp_path, monkeypatch):
    """余额不足出现一次后，整批立刻收尾，而不是把剩下 100 张也去撞一遍。"""
    _prepare(tmp_path, monkeypatch, shot_count=10, concurrency=4)
    monkeypatch.setattr(
        "app.images.jobs.state._apply_failure",
        lambda project_id, shot_index, exc: ("生图接口余额/额度不足", "balance", "http_402"),
    )
    monkeypatch.setattr(
        runner,
        "_apply_failure",
        lambda project_id, shot_index, exc: ("生图接口余额/额度不足", "balance", "http_402"),
    )

    calls: list[int] = []

    def fake_generate(story, index, cfg, fixed_prompt):
        calls.append(index)
        raise ImageError(
            "生图接口余额/额度不足",
            category="balance",
            code="http_402",
            status_code=402,
        )

    monkeypatch.setattr(runner, "generate_one_story_image", fake_generate)

    runner._run_job(
        "img_balance_dead",
        "p_balance",
        {"shots": [{} for _ in range(10)]},
        ImageConfig(api_key="k", base_url="http://example.test/v1", model="m"),
        None,
    )

    job = read_job("p_balance", "img_balance_dead")

    assert job["status"] == IMAGE_JOB_FAILED
    assert all(item["status"] == IMAGE_JOB_FAILED for item in job["items"])
    # 并发 4：最多只会真的去打 4 次（同一个 Key 已被判死，重试也没用）
    assert len(calls) <= 4
    assert len(calls) < 10
    skipped = [item for item in job["items"] if item.get("error_code") == "skipped_after_account_error"]
    assert skipped, "剩下的镜头应该被标记为账号级错误跳过"


def test_generic_error_does_not_stop_the_batch(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch, shot_count=6, concurrency=2)
    monkeypatch.setattr(
        "app.images.jobs.state._apply_failure",
        lambda project_id, shot_index, exc: ("boom", "request", "http_500"),
    )
    monkeypatch.setattr(
        runner,
        "_apply_failure",
        lambda project_id, shot_index, exc: ("boom", "request", "http_500"),
    )

    calls: list[int] = []

    def fake_generate(story, index, cfg, fixed_prompt):
        calls.append(index)
        raise ImageError("boom", category="request", code="http_500", status_code=500)

    monkeypatch.setattr(runner, "generate_one_story_image", fake_generate)

    runner._run_job(
        "img_balance_dead",
        "p_balance",
        {"shots": [{} for _ in range(6)]},
        ImageConfig(api_key="k", base_url="http://example.test/v1", model="m"),
        None,
    )

    job = read_job("p_balance", "img_balance_dead")

    # 普通错误仍然每个镜头都试满（1 + 重试 2 次），不会被当成账号级错误
    assert len(calls) == 6 * 3
    assert job["status"] == IMAGE_JOB_FAILED
