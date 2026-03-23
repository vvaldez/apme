# Primary daemon: gRPC orchestrator for scan/fix pipelines.
FROM localhost/apme-base:latest

ENV APME_PRIMARY_LISTEN=0.0.0.0:50051
ENV APME_COLLECTION_CACHE=/sessions
EXPOSE 50051

CMD ["apme-primary"]
