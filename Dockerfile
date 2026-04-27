FROM ghcr.io/home-assistant/amd64-base:latest
RUN apk add --no-cache python3 py3-pip
COPY pyproject.toml /app/
COPY src/ /app/src/
RUN pip3 install --no-cache-dir --break-system-packages /app
COPY run.sh /
RUN chmod a+x /run.sh
CMD ["/run.sh"]
