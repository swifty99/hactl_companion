ARG BASE_IMAGE=ghcr.io/home-assistant/amd64-base:latest
FROM ${BASE_IMAGE}
RUN command -v python3 > /dev/null 2>&1 || apk add --no-cache python3 py3-pip
COPY pyproject.toml /app/
COPY src/ /app/src/
RUN pip3 install --no-cache-dir --break-system-packages /app
COPY run.sh /
RUN chmod a+x /run.sh
CMD ["/run.sh"]
