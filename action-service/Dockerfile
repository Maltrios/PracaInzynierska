# Budowanie binarki Go
FROM golang:1.24 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o action-service .

# Finalny obraz
FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/action-service .
COPY .env .env
EXPOSE 8081
CMD ["./action-service"]
