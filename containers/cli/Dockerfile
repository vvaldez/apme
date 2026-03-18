# CLI: presentation layer; calls Primary over gRPC for scan, runs fix/format locally.
# Mount project at /workspace; set APME_PRIMARY_ADDRESS to primary service.
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

ENV APME_PRIMARY_ADDRESS=primary:50051
WORKDIR /workspace

ENTRYPOINT ["apme-scan"]
CMD ["scan", "."]
