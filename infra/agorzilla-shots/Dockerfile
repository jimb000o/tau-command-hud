# Agorzilla's evening pictures (shots.mjs): a headless Chromium that opens agorzilla.com like a visitor.
FROM node:22-bookworm-slim
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npm init -y >/dev/null && npm install --omit=dev playwright@1.63.0 && npx playwright install --with-deps --only-shell chromium && rm -rf /root/.npm /var/lib/apt/lists/*
COPY shots.mjs ./
CMD ["node", "shots.mjs"]
