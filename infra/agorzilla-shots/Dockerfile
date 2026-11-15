# Agorzilla's evening pictures (shots.mjs): a headless Chromium that opens agorzilla.com like a visitor.
FROM node:22-bookworm-slim
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npm init -y >/dev/null && npm install --omit=dev playwright@1.63.0 && npx playwright install --with-deps --only-shell chromium && rm -rf /root/.npm /var/lib/apt/lists/*
# /work: the YouTube film jobs (film.mjs), shared with alerts/yt.py, which runs as uid 10002
RUN mkdir -p /work/film && chown -R 10002 /work
COPY shots.mjs site-shots.mjs live-check.mjs film.mjs ./
CMD ["node", "shots.mjs"]
