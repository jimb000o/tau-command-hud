FROM python:3.13-slim
# git: devpulse.py reads the history of IDNI's public repositories
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd --system --uid 10002 alerts && mkdir /state /public && chown alerts /state /public
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fonts ./fonts
COPY alerts.py explain.py findings.py gazette.py recap.py bot.py donations.py devpulse.py ./
USER alerts
CMD ["python", "alerts.py"]
