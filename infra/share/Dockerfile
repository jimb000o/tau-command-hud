# Built from infra/ (see docker-compose.yml) so it can take the recap's fonts.
FROM python:3.13-slim
RUN useradd --system --uid 10003 share
WORKDIR /app
COPY share/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alerts/fonts ./fonts
COPY share/cards.py share/share.py ./
USER share
EXPOSE 8070
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8070/s/', timeout=4)"
CMD ["python", "share.py"]
