FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY instructions ./instructions
COPY src ./src
RUN pip install --no-cache-dir . && useradd -r -u 10001 app && mkdir /data && chown app /data
USER app
VOLUME ["/data"]
EXPOSE 8080
CMD ["python", "-m", "entry_strategy.api"]
