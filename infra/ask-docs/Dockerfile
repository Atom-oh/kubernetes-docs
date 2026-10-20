# Docs Q&A server for the demo EKS cluster (arm64 nodes). Build context: this directory.
#   docker build --platform linux/arm64 -t <ecr>/ask-docs/server:<tag> .
FROM public.ecr.aws/docker/library/python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOST=0.0.0.0 PORT=8080
RUN pip install --no-cache-dir boto3==1.40.* && useradd --uid 10001 --no-create-home app
WORKDIR /srv
COPY lambda/ask/app.py lambda/ask/server.py ./
USER 10001
EXPOSE 8080
CMD ["python3", "server.py"]
