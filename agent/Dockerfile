# Build context: the repository root, so app-assets/ can be copied into the package (S12.1).
FROM ghcr.io/astral-sh/uv:0.13.0 AS uv

FROM python:3.14-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.14 \
    PYTHONUNBUFFERED=1

WORKDIR /build/agent
COPY agent/pyproject.toml agent/uv.lock agent/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app-assets /build/app-assets
COPY agent/hatch_build.py ./
COPY agent/src ./src
RUN uv sync --frozen --no-dev --no-editable \
    && useradd --system --uid 10001 blueprint

ENV PATH=/build/agent/.venv/bin:$PATH
USER blueprint
EXPOSE 8000
CMD ["python", "-m", "blueprint"]
