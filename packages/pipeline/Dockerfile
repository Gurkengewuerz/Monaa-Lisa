# Stage 1: Dependencies (cached)
FROM python:3.13-slim AS deps

RUN apt-get update && apt-get install -y \
    git \
    iputils-ping \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: App
FROM deps AS app

COPY . .

# Create data directories – downloaded files live here at runtime
RUN mkdir -p /app/data/models /app/.cache

RUN useradd -m -s /bin/bash vscode \
    && chown -R vscode:vscode /app

USER vscode

CMD ["python", "src/main.py"]
