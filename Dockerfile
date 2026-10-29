# Run Darkroom on any host (Fly.io, Render, a VPS...) so your phone needs nothing but a browser.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY darkroom ./darkroom
RUN pip install --no-cache-dir .
ENV DARKROOM_DATA=/data PORT=8765
VOLUME /data
EXPOSE 8765
# DARKROOM_TOKEN protects the app (required: it is reachable from the internet)
CMD ["sh", "-c", "darkroom serve --host 0.0.0.0 --port ${PORT} --data ${DARKROOM_DATA}"]
