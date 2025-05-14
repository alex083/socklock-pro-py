# Stage 1 — Сборка 3proxy
FROM alpine:3.18 AS builder
RUN apk add --no-cache build-base git \
 && git clone --branch 0.9.5 --depth 1 https://github.com/z3APA3A/3proxy.git /3proxy \
 && cd /3proxy \
 && make -f Makefile.Linux

# Stage 2 — Финальный минимальный образ
FROM python:3.11-alpine
RUN apk add --no-cache curl jq bash sqlite

# Копируем только бинарник 3proxy
COPY --from=builder /3proxy/bin/3proxy /usr/local/3proxy/bin/3proxy

WORKDIR /app

COPY ./scripts/ /app/scripts/
COPY ./configs/ /configs/
COPY entrypoint.py /app/entrypoint.py

RUN pip install --no-cache-dir requests

RUN chmod +x /app/scripts/*.py /app/entrypoint.py

ENTRYPOINT ["python", "/app/entrypoint.py"]
