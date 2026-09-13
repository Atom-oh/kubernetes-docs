FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 lab \
    && useradd --uid 10001 --gid 10001 --no-create-home lab
COPY api.py db_config.py main.py messaging.py storage.py telemetry.py ./
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["python", "main.py"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]
