
FROM python:3.10-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apk --no-cache add git
RUN apk add --no-cache linux-headers && \
    apk --no-cache add gcc musl-dev && \
    apk --no-cache add postgresql-dev && \
    apk --no-cache add postgresql-libs && \
    apk --no-cache add libc-dev && \
    apk --no-cache add libffi-dev && \
    apk --no-cache add git && \
    apk --no-cache add cmake && \
    apk --no-cache add poppler-utils && \
    apk --no-cache add python-poppler && \
    apk update

WORKDIR /app
COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
RUN uv sync --locked

COPY . .
CMD ["uv", "run", "run_bot.py"]