# Stage 1: Install dependencies
FROM python:3.13-slim AS deps
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .


# Stage 2: Production image
FROM python:3.13-slim AS runtime

RUN groupadd -g 1000 nvs && \
    useradd -u 1000 -g nvs -s /bin/false -m nvs

WORKDIR /app

COPY --from=deps /install /usr/local
COPY src/ src/

RUN chown -R nvs:nvs /app

USER nvs

ENTRYPOINT ["nvs-sync"]
CMD ["--help"]
