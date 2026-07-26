FROM python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    TMAS_BINARY=/usr/local/bin/tmas

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       tini \
       curl \
       jq \
       tar \
       unzip \
    && rm -rf /var/lib/apt/lists/*

# Pinned TMAS installer script and CLI version.
RUN curl -fsSL \
      "https://raw.githubusercontent.com/trendmicro/tmas-scan-action/72036f533d2b9b5f7a4a4cab0029df4f1ab6ea26/tmas-scripts/setup_tmas.sh" \
      -o /tmp/setup_tmas.sh \
    && chmod +x /tmp/setup_tmas.sh \
    && /tmp/setup_tmas.sh \
       --install \
       --install-dir /usr/local/bin \
       --version 2.284.0 \
    && tmas --version \
    && rm -f /tmp/setup_tmas.sh

WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.lock.txt ./

RUN test -s requirements.lock.txt \
    && grep -q '^fastapi==' requirements.lock.txt \
    && grep -q '^uvicorn==' requirements.lock.txt \
    && grep -q '^visionone_filesecurity==' requirements.lock.txt \
    && echo "Dependency lock verified: $(wc -l < requirements.lock.txt) packages"

RUN python -m venv "${VIRTUAL_ENV}" \
    && "${VIRTUAL_ENV}/bin/python" -m pip install \
       --no-cache-dir \
       --disable-pip-version-check \
       -r requirements.lock.txt \
    && "${VIRTUAL_ENV}/bin/python" -m pip check \
    && "${VIRTUAL_ENV}/bin/python" -c \
       "import fastapi, uvicorn, httpx, boto3, amaas; print('Python runtime dependencies verified')"

COPY app ./app

RUN addgroup --system --gid 10001 appgroup \
    && adduser --system --uid 10001 --ingroup appgroup appuser \
    && mkdir -p \
       /data/clean \
       /data/quarantine \
    && chown -R appuser:appgroup /app /data

USER 10001:10001

EXPOSE 8080

HEALTHCHECK \
  --interval=30s \
  --timeout=5s \
  --start-period=15s \
  --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3).read()"]

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
