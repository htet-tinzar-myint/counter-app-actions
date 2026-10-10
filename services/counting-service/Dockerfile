# counting-service: 呼ばれるたびにカウントを1増やしてJSONで返すサービス
# ビルド済みの静的バイナリ（Go, linux/amd64）をそのまま載せる
FROM gcr.io/distroless/static-debian12:nonroot

COPY --chmod=755 bin/counting-service /app/counting-service

# Cloud Run は環境変数 PORT（既定 8080）を渡す。バイナリは PORT を読んで待ち受ける
ENV PORT=9003
EXPOSE 9003

USER nonroot:nonroot
ENTRYPOINT ["/app/counting-service"]
