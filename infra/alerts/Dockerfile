FROM python:3.13-slim
RUN useradd --system --uid 10002 alerts && mkdir /state /public && chown alerts /state /public
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fonts ./fonts
COPY alerts.py recap.py ./
USER alerts
CMD ["python", "alerts.py"]
