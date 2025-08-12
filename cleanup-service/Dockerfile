FROM golang:1.24 AS builder
WORKDIR /app
COPY .. .
RUN go mod download
RUN go build -o cleanup-service .

FROM debian:bookworm-slim
WORKDIR /app
ENV HOME=/app

RUN apt-get update && apt-get install -y cron postgresql-client bash && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/cleanup-service .
RUN chmod +x /app/cleanup-service
COPY .env /app/.env
COPY cleanup-cron /etc/cron.d/cleanup-cron

RUN chmod 0644 /etc/cron.d/cleanup-cron

RUN touch /var/log/cleanup.log

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV STORAGE_DIRECTORY=/app/storage
ENV DBConnectionString postgres://user:password@db:5432/db_users?sslmode=disable


CMD ["/app/entrypoint.sh"]
