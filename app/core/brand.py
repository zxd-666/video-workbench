"""产品名与通用文案集中在这里。

「人生副本」只是其中一个创作模板，产品本身是通用短视频创作工作台。
改品牌时只改这个文件，不要在各处硬编码产品名。
"""

APP_NAME = "短视频创作工作台"

APP_NAME_SHORT = "短视频工作台"

APP_TAGLINE = "从选题到成片，一条流水线跑完"

DEFAULT_PROJECT_TOPIC = "新项目"

DEFAULT_STORY_TITLE = "短视频样片"

DEFAULT_JIANYING_DRAFT_NAME = "短视频剪映草稿"

DEFAULT_TTS_PREVIEW_TEXT = "这是配音效果预览，可以调整语气和速度。"


def app_title() -> str:
    """FastAPI / 页面标题统一入口。"""
    return APP_NAME
