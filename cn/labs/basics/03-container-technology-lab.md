# 容器技术实验室指南

> **难度**: 初级
> **预计时间**: 45 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 编写 Dockerfile 并构建镜像
- 使用多阶段构建优化镜像
- 练习容器执行、调试和日志检查

## 前置要求
- [ ] Docker 已安装（使用 `docker --version` 验证）
- [ ] 已完成 [容器技术](../../basics/03-container-technology.md) 学习

---

## 练习 1：Dockerfile 编写和镜像构建

### 目标
将一个简单的 web 应用程序容器化。

### 步骤

**步骤 1.1：创建项目目录**
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

**步骤 1.2：编写 Dockerfile**
```bash
cat > Dockerfile << 'EOF'
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
```

**步骤 1.3：构建镜像**
```bash
docker build -t my-web:v1 .
docker images my-web
```

预期输出：
```
REPOSITORY   TAG   IMAGE ID       CREATED         SIZE
my-web       v1    abc123def456   5 seconds ago   ~40MB
```

<details>
<summary>需要提示吗？</summary>

- 在 `docker build -t name:tag .` 中，`.` 是构建上下文目录
- 基于 `alpine` 的镜像很小，这对于 Kubernetes 部署是有利的
- 使用 `docker build --no-cache` 在不使用缓存的情况下构建
</details>

### 验证
```bash
docker images my-web:v1 --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
```

---

## 练习 2：容器执行和调试

### 目标
运行容器并调试其内部。

### 步骤

**步骤 2.1：运行容器**
```bash
docker run -d --name my-web-container -p 8080:80 my-web:v1
docker ps
```

**步骤 2.2：验证容器访问**
```bash
curl http://localhost:8080
```

**步骤 2.3：连接到容器内部**
```bash
# Shell into the running container
docker exec -it my-web-container sh

# Run inside the container
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```

**步骤 2.4：检查日志**
```bash
docker logs my-web-container
docker logs --tail 5 my-web-container
```

<details>
<summary>需要提示吗？</summary>

- `docker exec -it` 中的 `-it` 代表交互式 + TTY 选项
- 使用 `docker inspect container-name` 查看详细信息
- 在 Kubernetes 中，这相当于 `kubectl exec -it pod-name -- sh`
</details>

### 验证
```bash
# Check HTTP response code
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080)
[ "$HTTP_CODE" = "200" ] && echo "Success! HTTP $HTTP_CODE" || echo "Failed: HTTP $HTTP_CODE"
```

---

## 练习 3：多阶段构建

### 目标
使用多阶段构建来优化镜像大小。

### 步骤

**步骤 3.1：创建 Go 应用程序**
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

**步骤 3.2：多阶段 Dockerfile**
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

**步骤 3.3：比较镜像大小**
```bash
docker images | grep -E "my-web|my-go-app|golang"
```

<details>
<summary>需要提示吗？</summary>

- 在多阶段构建中，使用 `FROM ... AS builder` 来命名构建阶段
- 使用 `COPY --from=builder` 仅从前一阶段复制构件
- 最终镜像不包括构建工具，大幅减小镜像大小
</details>

### 验证
```bash
echo "Go app image size:"
docker images my-go-app:v1 --format "{{.Size}}"
```

---

## 清理
```bash
docker stop my-web-container 2>/dev/null
docker rm my-web-container 2>/dev/null
docker rmi my-web:v1 my-go-app:v1 2>/dev/null
rm -rf /tmp/container-lab
```

## 后续步骤
- [容器技术测验](../../quizzes/basics/03-container-technology-quiz.md)
- [Pods 和工作负载实验室](../core/02-pods-and-workloads-lab.md)
