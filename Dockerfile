FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg / ffprobe: 视频合成、字幕烧录、音频处理
# fonts-noto-cjk: 中文字幕渲染（项目 ASS 默认字体是 Microsoft YaHei，容器里做别名映射）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        fontconfig \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 把 "Microsoft YaHei" 映射到 Noto Sans CJK SC，保证中文字幕不出方块
RUN printf '%s\n' \
    '<?xml version="1.0"?>' \
    '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">' \
    '<fontconfig>' \
    '  <alias binding="same">' \
    '    <family>Microsoft YaHei</family>' \
    '    <prefer><family>Noto Sans CJK SC</family></prefer>' \
    '  </alias>' \
    '  <alias binding="same">' \
    '    <family>微软雅黑</family>' \
    '    <prefer><family>Noto Sans CJK SC</family></prefer>' \
    '  </alias>' \
    '</fontconfig>' \
    > /etc/fonts/conf.d/99-msyh-alias.conf \
    && fc-cache -f

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/workspace

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/api/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
