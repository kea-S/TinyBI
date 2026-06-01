FROM python:3.13-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

RUN npm install -g promptfoo@0.121.12

COPY pyproject.toml requirements.txt ./
RUN uv pip install --system -r requirements.txt

COPY . .

RUN mkdir -p data/app_data

ENV PROMPTFOO_PYTHON=/usr/local/bin/python3
ENV PYTHONPATH=/app

CMD ["promptfoo"]
