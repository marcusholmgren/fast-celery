FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock* /app/

RUN pip install uv
RUN uv pip install --system --no-cache --upgrade pip
RUN uv pip install --system --no-cache -r pyproject.toml

COPY . /app

