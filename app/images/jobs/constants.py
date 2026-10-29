from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from app.core.image_status import IMAGE_JOB_QUEUED, IMAGE_JOB_RETRYING, IMAGE_JOB_RUNNING

ACTIVE_JOB_STATUSES = {IMAGE_JOB_QUEUED, IMAGE_JOB_RUNNING, IMAGE_JOB_RETRYING}

IMAGE_JOB_KIND = "image"

IMAGE_JOB_FILE_PREFIX = "img_"

# 并发生图直接打上游接口：100 路同时打过去基本等于自找 429/封号，
# 默认收敛到 8 路，需要更激进时可以显式把 job 的 concurrency 调大（上限仍是 100）。
DEFAULT_IMAGE_JOB_CONCURRENCY = 8

MAX_IMAGE_JOB_CONCURRENCY = 100

IMAGE_JOB_RETRY_LIMIT = 2

STALE_ACTIVE_JOB_GRACE_MS = 60_000

_runner = ThreadPoolExecutor(max_workers=4)

_lock = threading.RLock()

_cancelled: set[str] = set()

_active_job_ids: set[str] = set()

# 账号级错误（余额不足 / Key 无效）出现一次就整批停机，剩下的镜头不必再去撞同一堵墙。
# job_id -> {"message", "category", "code"}
_fatal: dict[str, dict[str, str]] = {}

