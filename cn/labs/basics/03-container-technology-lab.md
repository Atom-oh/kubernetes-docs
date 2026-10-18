# 容器技术实验指南

> **难度**：初级
> **预计时间**：45 分钟
> **最后更新**：October 16, 2026

## 学习目标
- 编写 Dockerfile 并构建镜像
- 使用多阶段构建优化镜像
- 练习容器运行、调试和日志检查

## 先决条件
- [ ] Docker CLI、受支持的本地 Docker Engine、Bash 和 curl
- [ ] 已完成[容器技术](../../basics/03-container-technology.md)学习

使用一个 Bash 终端和一个可随时丢弃的**本地 Linux 容器 Docker Engine**。继续之前，请确认已选定的 context；下方的辅助函数会将所有命令固定到该 context。检查服务器是否可用及其版本，而不只是客户端版本。对于文档所述的回环地址端口发布行为，请使用至少 28.0.0 版本且仍受维护的 Engine；较早版本存在同一 L2 网络可达性的注意事项。只有在运行本实验时才会创建 Docker 资源和端口，本次审计不会创建它们。

---

## 练习 1：编写 Dockerfile 并构建镜像

### 目标
将一个简单的 Web 应用容器化。

### 步骤

**步骤 1.1：创建项目目录**
```bash
CONTAINER_LAB_START_DIR=$PWD
unset CONTAINER_LAB_WEB_PORT CONTAINER_LAB_GO_PORT CONTAINER_LAB_WEB_CID CONTAINER_LAB_GO_CID
CONTAINER_LAB_DIR=$(mktemp -d /tmp/k8s-docs-container.XXXXXX)
: "${CONTAINER_LAB_DIR:?mktemp failed}"
CONTAINER_LAB_ID=$(basename "$CONTAINER_LAB_DIR")
CONTAINER_LAB_CONTEXT=$(docker context show)
lab_docker() { docker --context "${CONTAINER_LAB_CONTEXT:?}" "$@"; }
lab_docker context inspect "$CONTAINER_LAB_CONTEXT" --format '{{json .Endpoints.docker.Host}}'
lab_docker version

CONTAINER_LAB_WEB_IMAGE="k8s-docs-lab/web:$CONTAINER_LAB_ID"
CONTAINER_LAB_GO_IMAGE="k8s-docs-lab/go:$CONTAINER_LAB_ID"
CONTAINER_LAB_BUILD_IMAGE="k8s-docs-lab/go-build:$CONTAINER_LAB_ID"
cd "$CONTAINER_LAB_DIR"

cat > index.html << 'EOF'
<!DOCTYPE html>
<html><body>
<h1>Hello from Container!</h1>
<p>Hostname: <!--# echo var="hostname" --></p>
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

SSI 会读取 NGINX 文档中定义的 `hostname` 变量；它不会任意展开环境变量。

**步骤 1.2：编写 Dockerfile**
```bash
cat > Dockerfile << 'EOF'
FROM nginx:1.30.6-alpine
ARG LAB_ID
LABEL io.kubernetes-docs.lab=$LAB_ID
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
```

**步骤 1.3：构建镜像**
```bash
lab_docker build --build-arg "LAB_ID=${CONTAINER_LAB_ID:?}" \
  -t "${CONTAINER_LAB_WEB_IMAGE:?}" .
lab_docker image ls "$CONTAINER_LAB_WEB_IMAGE"
```

检查实际镜像 ID 和报告的大小。之前的 `~40MB` 数值未经验证，仅作示例，并非基准或必需结果。大小会因基础镜像、架构和镜像存储而异。本次审计没有测量任何镜像大小。

<details>
<summary>需要提示吗？</summary>

- 在 `docker build -t name:tag .` 中，`.` 是构建上下文目录
- 基础镜像大小只是需要权衡的一项因素；还要考虑 libc/运行时兼容性以及所需工具。
- 使用 `docker build --no-cache` 可在不使用缓存的情况下构建
</details>

### 验证
```bash
lab_docker image ls "${CONTAINER_LAB_WEB_IMAGE:?}" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
```

---

## 练习 2：运行和调试容器

### 目标
运行容器并调试其内部情况。

### 步骤

**步骤 2.1：运行容器**
```bash
if lab_docker run -d --pull=never \
  --name "web-${CONTAINER_LAB_ID:?}" --hostname container-lab-web \
  --label "io.kubernetes-docs.lab=$CONTAINER_LAB_ID" \
  --cidfile "${CONTAINER_LAB_DIR:?}/web.cid" \
  -p 127.0.0.1::80 "${CONTAINER_LAB_WEB_IMAGE:?}"; then
  CONTAINER_LAB_WEB_CID=$(cat "$CONTAINER_LAB_DIR/web.cid")
  CONTAINER_LAB_WEB_MAPPING=$(lab_docker port "$CONTAINER_LAB_WEB_CID" 80/tcp)
  CONTAINER_LAB_WEB_PORT=${CONTAINER_LAB_WEB_MAPPING##*:}
  : "${CONTAINER_LAB_WEB_PORT:?No port mapping found}"
  lab_docker ps --filter "id=$CONTAINER_LAB_WEB_CID"
else
  printf 'Container startup failed; inspect the created lab resource before continuing\n' >&2
fi
```

**步骤 2.2：验证容器访问**
```bash
curl --disable --noproxy '*' --fail --show-error --silent \
  --retry 5 --retry-delay 1 --retry-connrefused --max-time 5 \
  "http://127.0.0.1:${CONTAINER_LAB_WEB_PORT:?Run Step 2.1}/"
```

**步骤 2.3：连接到容器内部**
```bash
# This shell command applies to the NGINX image, which includes sh.
lab_docker exec -it "${CONTAINER_LAB_WEB_CID:?}" sh

# Run these inside that container, then return to the original Bash shell.
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```
**步骤 2.4：检查日志**
```bash
lab_docker logs "${CONTAINER_LAB_WEB_CID:?}"
lab_docker logs --tail 5 "$CONTAINER_LAB_WEB_CID"
```

<details>
<summary>需要提示吗？</summary>

- `docker exec -it` 中的 `-it` 表示交互式 + TTY 选项
- 使用 `docker inspect container-name` 查看详细信息
- Kubernetes 中有相应的命令 `kubectl exec -it pod-name -c container-name -- sh`；这需要 RBAC 权限，且镜像中包含 shell。
</details>

### 验证
```bash
if HTTP_CODE=$(curl --disable --noproxy '*' --silent --show-error \
  --output /dev/null --write-out '%{http_code}' --max-time 5 \
  "http://127.0.0.1:${CONTAINER_LAB_WEB_PORT:?}/"); then
  [ "$HTTP_CODE" = "200" ] && printf 'HTTP 200 confirmed\n' || printf 'Unexpected HTTP %s\n' "$HTTP_CODE"
else
  printf 'HTTP transfer failed; a printed status alone is not success\n' >&2
fi
```

---

## 练习 3：多阶段构建

### 目标
使用多阶段构建优化镜像大小。

### 步骤

**步骤 3.1：创建 Go 应用**
```bash
cat > main.go << 'EOF'
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

func newHandler(hostname string) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		fmt.Fprintf(w, "Hello from %s!\n", hostname)
	})
	return mux
}

func main() {
	hostname, err := os.Hostname()
	if err != nil {
		log.Fatal(err)
	}
	server := &http.Server{
		Addr:              ":8080",
		Handler:           newHandler(hostname),
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Fatal(server.ListenAndServe())
}
EOF
```

**步骤 3.2：多阶段 Dockerfile**
这个使用 Go 标准库的程序通过 `CGO_ENABLED=0` 构建，因此 scratch 运行环境不需要构建器所用的 libc。它不包含 shell、软件包管理器或 CA 证书包；需要这些资源的应用必须使用合适的运行环境，或显式提供所需文件。两个带标签的阶段包含相同的 Go 构建产物，因此，与比较无关的 NGINX 和 Go 应用相比，这种比较更能单独体现移除构建环境的效果。否则，BuildKit 可能不会保留带标签的中间镜像。

```bash
cat > Dockerfile.multi << 'EOF'
FROM golang:1.27.2 AS build
ARG LAB_ID
LABEL io.kubernetes-docs.lab=$LAB_ID
WORKDIR /src
COPY main.go .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/server main.go
CMD ["/out/server"]

FROM scratch AS runtime
ARG LAB_ID
LABEL io.kubernetes-docs.lab=$LAB_ID
COPY --from=build /out/server /server
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/server"]
EOF

lab_docker build -f Dockerfile.multi --target build \
  --build-arg "LAB_ID=${CONTAINER_LAB_ID:?}" -t "${CONTAINER_LAB_BUILD_IMAGE:?}" .
lab_docker build -f Dockerfile.multi \
  --build-arg "LAB_ID=$CONTAINER_LAB_ID" -t "${CONTAINER_LAB_GO_IMAGE:?}" .
```

请在相同的平台/存储上进行比较。报告的镜像大小不一定等于压缩后的下载大小或磁盘上的独占占用，因为不同镜像可以共享层。

**步骤 3.3：比较镜像大小**
```bash
# Same Go program/artifact; the build-stage image retains the compiler and base OS.
for image in "${CONTAINER_LAB_BUILD_IMAGE:?}" "${CONTAINER_LAB_GO_IMAGE:?}"; do
  lab_docker image ls "$image" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
done
```

<details>
<summary>需要提示吗？</summary>

- 在多阶段构建中，使用 `FROM ... AS build` 为构建阶段命名
- 使用 `COPY --from=build` 仅复制前一阶段中的构建产物
- 最终镜像不包含构建工具，因此可以显著减小体积
</details>

### 验证
```bash
if lab_docker run -d --pull=never --read-only \
  --name "go-${CONTAINER_LAB_ID:?}" --hostname container-lab-go \
  --label "io.kubernetes-docs.lab=$CONTAINER_LAB_ID" \
  --cidfile "${CONTAINER_LAB_DIR:?}/go.cid" \
  -p 127.0.0.1::8080 "${CONTAINER_LAB_GO_IMAGE:?}"; then
  CONTAINER_LAB_GO_CID=$(cat "$CONTAINER_LAB_DIR/go.cid")
  CONTAINER_LAB_GO_MAPPING=$(lab_docker port "$CONTAINER_LAB_GO_CID" 8080/tcp)
  CONTAINER_LAB_GO_PORT=${CONTAINER_LAB_GO_MAPPING##*:}
  : "${CONTAINER_LAB_GO_PORT:?No port mapping found}"
  curl --disable --noproxy '*' --fail --show-error --silent \
    --retry 5 --retry-delay 1 --retry-connrefused --max-time 5 \
    "http://127.0.0.1:$CONTAINER_LAB_GO_PORT/"
  lab_docker logs "$CONTAINER_LAB_GO_CID"
fi
```

---

## 清理
```bash
# Resource IDs and labels must match this lab, even after a partial startup failure.
: "${CONTAINER_LAB_DIR:?}"
: "${CONTAINER_LAB_ID:?}"
for cid_file in "$CONTAINER_LAB_DIR/web.cid" "$CONTAINER_LAB_DIR/go.cid"; do
  [ -s "$cid_file" ] || continue
  cid=$(cat "$cid_file")
  owner=$(lab_docker container inspect --format '{{index .Config.Labels "io.kubernetes-docs.lab"}}' "$cid" 2>/dev/null) || continue
  if [ "$owner" = "$CONTAINER_LAB_ID" ]; then
    lab_docker container stop "$cid"
    lab_docker container rm "$cid"
  fi
done
for image in "${CONTAINER_LAB_WEB_IMAGE:?}" "${CONTAINER_LAB_GO_IMAGE:?}" "${CONTAINER_LAB_BUILD_IMAGE:?}"; do
  owner=$(lab_docker image inspect --format '{{index .Config.Labels "io.kubernetes-docs.lab"}}' "$image" 2>/dev/null) || continue
  if [ "$owner" = "$CONTAINER_LAB_ID" ]; then
    lab_docker image rm "$image"
  fi
done
cd "${CONTAINER_LAB_START_DIR:?}"
rm -f -- "$CONTAINER_LAB_DIR/index.html" "$CONTAINER_LAB_DIR/nginx.conf" \
  "$CONTAINER_LAB_DIR/Dockerfile" "$CONTAINER_LAB_DIR/main.go" \
  "$CONTAINER_LAB_DIR/Dockerfile.multi" "$CONTAINER_LAB_DIR/web.cid" "$CONTAINER_LAB_DIR/go.cid"
if rmdir -- "$CONTAINER_LAB_DIR"; then
  unset CONTAINER_LAB_DIR
fi
unset -f lab_docker
```


## 参考资料和验证范围

* [Docker 多阶段构建](https://docs.docker.com/build/building/multi-stage/)
* [Docker 端口发布](https://docs.docker.com/engine/network/port-publishing/)
* [Docker run](https://docs.docker.com/reference/cli/docker/container/run/)
* [NGINX SSI](https://nginx.org/en/docs/http/ngx_http_ssi_module.html)
* [NGINX 官方镜像标签](https://github.com/docker-library/official-images/blob/master/library/nginx)
* [Go 官方镜像标签](https://github.com/docker-library/official-images/blob/master/library/golang)

可以在本地检查 Go 处理程序/静态构建及命令语法。本次审计没有连接 Docker daemon、构建或运行镜像、发布端口，也没有测量镜像大小的减少情况；实验步骤并不代表已经记录的执行结果。

## 后续步骤
- [容器技术测验](../../quizzes/basics/03-container-technology-quiz.md)
- [Pods 和工作负载实验](../core/02-pods-and-workloads-lab.md)
