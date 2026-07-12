# Container Technology ラボガイド

> **難易度**: 初級
> **目安時間**: 45分
> **最終更新**: February 11, 2026

## 学習目標
- Dockerfile を書いてイメージをビルドする
- マルチステージビルドを使用してイメージを最適化する
- コンテナの実行、デバッグ、ログ確認を練習する

## 前提条件
- [ ] Docker がインストール済み（`docker --version` で確認）
- [ ] [Container Technology](../../basics/03-container-technology.md) の学習を完了済み

---

## 演習 1: Dockerfile の作成とイメージのビルド

### 目標
シンプルな Web アプリケーションをコンテナ化します。

### 手順

**ステップ 1.1: プロジェクトディレクトリの作成**
```bash
mkdir -p /tmp/container-lab && cd /tmp/container-lab

cat > index.html << 'EOF'
<!DOCTYPE html>
<html><body>
<h1>Hello from Container!</h1>
<p>Hostname: <!--#echo var="HOSTNAME" --></p>
</body></html>
EOF

cat > nginx.conf << 'EOF'
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        ssi on;
    }
}
EOF
```

**ステップ 1.2: Dockerfile の作成**
```bash
cat > Dockerfile << 'EOF'
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
```

**ステップ 1.3: イメージのビルド**
```bash
docker build -t my-web:v1 .
docker images my-web
```

期待される出力:
```
REPOSITORY   TAG   IMAGE ID       CREATED         SIZE
my-web       v1    abc123def456   5 seconds ago   ~40MB
```

<details>
<summary>ヒントが必要ですか?</summary>

- `docker build -t name:tag .` では、`.` がビルドコンテキストのディレクトリです
- `alpine` ベースのイメージは小さく、K8s Deployment に有利です
- `docker build --no-cache` を使うと、キャッシュなしでビルドできます
</details>

### 検証
```bash
docker images my-web:v1 --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
```

---

## 演習 2: コンテナの実行とデバッグ

### 目標
コンテナを実行し、その内部をデバッグします。

### 手順

**ステップ 2.1: コンテナの実行**
```bash
docker run -d --name my-web-container -p 8080:80 my-web:v1
docker ps
```

**ステップ 2.2: コンテナアクセスの確認**
```bash
curl http://localhost:8080
```

**ステップ 2.3: コンテナ内部への接続**
```bash
# Shell into the running container
docker exec -it my-web-container sh

# Run inside the container
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```

**ステップ 2.4: ログの確認**
```bash
docker logs my-web-container
docker logs --tail 5 my-web-container
```

<details>
<summary>ヒントが必要ですか?</summary>

- `docker exec -it` の `-it` は interactive + TTY オプションを意味します
- `docker inspect container-name` を使用すると、詳細情報を表示できます
- K8s では、これは `kubectl exec -it pod-name -- sh` に相当します
</details>

### 検証
```bash
# Check HTTP response code
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080)
[ "$HTTP_CODE" = "200" ] && echo "Success! HTTP $HTTP_CODE" || echo "Failed: HTTP $HTTP_CODE"
```

---

## 演習 3: マルチステージビルド

### 目標
マルチステージビルドを使用してイメージサイズを最適化します。

### 手順

**ステップ 3.1: Go アプリケーションの作成**
```bash
cat > main.go << 'EOF'
package main
import (
    "fmt"
    "net/http"
    "os"
)
func main() {
    hostname, _ := os.Hostname()
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "Hello from %s!\n", hostname)
    })
    fmt.Println("Server starting on :8080")
    http.ListenAndServe(":8080", nil)
}
EOF
```

**ステップ 3.2: マルチステージ Dockerfile**
```bash
cat > Dockerfile.multi << 'EOF'
# Stage 1: Build
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY main.go .
RUN go build -o server main.go

# Stage 2: Run (minimal image)
FROM alpine:3.19
COPY --from=builder /app/server /server
EXPOSE 8080
CMD ["/server"]
EOF

docker build -f Dockerfile.multi -t my-go-app:v1 .
```

**ステップ 3.3: イメージサイズの比較**
```bash
docker images | grep -E "my-web|my-go-app|golang"
```

<details>
<summary>ヒントが必要ですか?</summary>

- マルチステージビルドでは、`FROM ... AS builder` を使用してビルドステージに名前を付けます
- `COPY --from=builder` を使用して、前のステージから成果物だけをコピーします
- 最終イメージにはビルドツールが含まれないため、サイズを大幅に削減できます
</details>

### 検証
```bash
echo "Go app image size:"
docker images my-go-app:v1 --format "{{.Size}}"
```

---

## クリーンアップ
```bash
docker stop my-web-container 2>/dev/null
docker rm my-web-container 2>/dev/null
docker rmi my-web:v1 my-go-app:v1 2>/dev/null
rm -rf /tmp/container-lab
```

## 次のステップ
- [Container Technology Quiz](../../quizzes/basics/03-container-technology-quiz.md)
- [Pods and Workloads Lab](../core/02-pods-and-workloads-lab.md)
