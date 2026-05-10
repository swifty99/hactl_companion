ARG BASE_IMAGE=python:3.12-alpine
FROM ${BASE_IMAGE}
COPY pyproject.toml /app/
COPY src/ /app/src/
RUN pip install --no-cache-dir --break-system-packages /app
COPY run.sh /
RUN chmod a+x /run.sh
CMD ["python3", "-m", "companion"]
