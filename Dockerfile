FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN git clone https://github.com/typst/typst.git /tmp/typst \
    && cd /tmp/typst \
    && cargo build --release \
    && cp target/release/typst /usr/local/bin/ \
    && rm -rf /tmp/typst

RUN echo "Typst build complete"

WORKDIR /app

COPY . .

RUN ls -la static/ || echo "Static directory not found"

RUN uv sync --locked

EXPOSE 8000

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

VOLUME /app/data

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]