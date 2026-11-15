FROM python:3.13-slim
# git: devpulse.py reads the history of IDNI's public repositories; ffmpeg: the pirates' clip (trick_clip.py)
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates ffmpeg && rm -rf /var/lib/apt/lists/*
RUN useradd --system --uid 10002 alerts && mkdir -p /state /public /work/film && chown alerts /state /public /work /work/film
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fonts ./fonts
# every module of the service: a list by name missed firsts.py and follow.py (31 October to 2 November 2026 the
# container died on its first import, and the channel went quiet without a word); the tests ride along, they are small
COPY *.py ./
# the YouTube channel's views that can be filmed and its five answer videos (yt.py)
COPY yt_scenes.json ./
COPY yt_briefs ./yt_briefs
USER alerts
CMD ["python", "alerts.py"]
