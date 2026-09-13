# 컨테이너 기술 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 45분
> **마지막 업데이트**: 2026년 9월 11일

## 학습 목표
- Dockerfile을 작성하고 이미지를 빌드합니다
- 멀티스테이지 빌드를 활용하여 이미지를 최적화합니다
- 컨테이너 실행, 디버깅, 로그 확인을 실습합니다

## 사전 요구 사항
- [ ] Docker CLI·지원되는 로컬 Docker Engine·Bash·curl
- [ ] [컨테이너 기술](../../basics/03-container-technology.md) 학습 완료

같은 Bash 터미널과 폐기 가능한 **로컬 Linux 컨테이너용 Docker Engine**을 사용합니다. 진행 전에 context를 확인하세요. 아래 함수는 모든 명령의 context를 고정합니다. 클라이언트 버전만 보지 말고 서버 연결·버전도 확인합니다. 문서의 loopback 게시 동작에는 유지보수 중인 최소28.0.0 Engine을 사용하세요. 이전 버전에는 같은 L2 구간의 접근 예외가 있습니다. Docker 리소스·포트는 사용자가 실습을 실행할 때만 생성하며 이번 감사에서는 만들지 않았습니다.

---

## 실습 1: Dockerfile 작성과 이미지 빌드

### 목표
간단한 웹 애플리케이션을 컨테이너화합니다.

### 단계

**Step 1.1: 프로젝트 디렉토리 생성**
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

SSI는 NGINX의 문서화된 `hostname` 변수를 읽으며 임의의 환경 변수 확장이 아닙니다.

**Step 1.2: Dockerfile 작성**
```bash
cat > Dockerfile << 'EOF'
FROM nginx:1.30.4-alpine
ARG LAB_ID
LABEL io.kubernetes-docs.lab=$LAB_ID
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
```

**Step 1.3: 이미지 빌드**
```bash
lab_docker build --build-arg "LAB_ID=${CONTAINER_LAB_ID:?}" \
  -t "${CONTAINER_LAB_WEB_IMAGE:?}" .
lab_docker image ls "$CONTAINER_LAB_WEB_IMAGE"
```

실제 이미지 ID와 표시 크기를 확인합니다. 기존 `~40MB` 줄은 검증되지 않은 예시이며 벤치마크나 필수 결과가 아닙니다. 기반 이미지·아키텍처·이미지 저장 방식에 따라 달라집니다. 이번 감사에서 이미지 크기를 측정하지 않았습니다.

<details>
<summary>힌트가 필요하신가요?</summary>

- `docker build -t 이름:태그 .`에서 `.`은 빌드 컨텍스트 디렉토리입니다
- 크기뿐 아니라 libc·런타임 호환성과 필요한 도구도 고려합니다.
- `docker build --no-cache`로 캐시 없이 빌드할 수 있습니다
</details>

### 검증
```bash
lab_docker image ls "${CONTAINER_LAB_WEB_IMAGE:?}" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
```

---

## 실습 2: 컨테이너 실행과 디버깅

### 목표
컨테이너를 실행하고 내부를 디버깅합니다.

### 단계

**Step 2.1: 컨테이너 실행**
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

**Step 2.2: 컨테이너 접근 확인**
```bash
curl --disable --noproxy '*' --fail --show-error --silent \
  --retry 5 --retry-delay 1 --retry-connrefused --max-time 5 \
  "http://127.0.0.1:${CONTAINER_LAB_WEB_PORT:?Run Step 2.1}/"
```

**Step 2.3: 컨테이너 내부 접속**
```bash
# This shell command applies to the NGINX image, which includes sh.
lab_docker exec -it "${CONTAINER_LAB_WEB_CID:?}" sh

# Run these inside that container, then return to the original Bash shell.
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```
**Step 2.4: 로그 확인**
```bash
lab_docker logs "${CONTAINER_LAB_WEB_CID:?}"
lab_docker logs --tail 5 "$CONTAINER_LAB_WEB_CID"
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `docker exec -it`의 `-it`는 interactive + TTY 옵션입니다
- `docker inspect 컨테이너명`으로 상세 정보를 확인할 수 있습니다
- Kubernetes의 유사한 명령은 `kubectl exec -it pod명 -c 컨테이너명 -- sh`이며 RBAC와 해당 이미지의 shell이 필요합니다.
</details>

### 검증
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

## 실습 3: 멀티스테이지 빌드

### 목표
멀티스테이지 빌드를 사용하여 이미지 크기를 최적화합니다.

### 단계

**Step 3.1: Go 애플리케이션 생성**
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

**Step 3.2: 멀티스테이지 Dockerfile**
표준 라이브러리 Go 프로그램을 `CGO_ENABLED=0`으로 빌드하므로 scratch 런타임에 빌더의 libc가 필요하지 않습니다. shell·패키지 관리자·CA bundle이 없으며 필요한 앱에는 적절한 런타임이나 파일이 필요합니다. 두 태그의 단계는 같은 Go 산출물을 포함하므로 서로 다른 NGINX·Go 앱을 비교하는 대신 빌드 환경 제외 효과를 비교할 수 있습니다. BuildKit은 별도로 태그하지 않은 중간 이미지를 남기지 않을 수 있습니다.

```bash
cat > Dockerfile.multi << 'EOF'
FROM golang:1.27.1 AS build
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

같은 플랫폼·이미지 저장소 방식에서 비교하세요. 표시 크기는 압축 다운로드 크기나 고유 디스크 사용량과 같지 않을 수 있으며 레이어는 공유될 수 있습니다.

**Step 3.3: 이미지 크기 비교**
```bash
# Same Go program/artifact; the build-stage image retains the compiler and base OS.
for image in "${CONTAINER_LAB_BUILD_IMAGE:?}" "${CONTAINER_LAB_GO_IMAGE:?}"; do
  lab_docker image ls "$image" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
done
```

<details>
<summary>힌트가 필요하신가요?</summary>

- 멀티스테이지 빌드에서 `FROM ... AS build`로 빌드 스테이지에 이름을 부여합니다
- `COPY --from=build`로 이전 스테이지의 산출물만 복사합니다
- 최종 이미지에는 빌드 도구가 포함되지 않아 크기가 대폭 줄어듭니다
</details>

### 검증
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

## 정리
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


## 참고 자료와 검증 범위

* [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
* [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/)
* [Docker run](https://docs.docker.com/reference/cli/docker/container/run/)
* [NGINX SSI](https://nginx.org/en/docs/http/ngx_http_ssi_module.html)
* [Official NGINX image tags](https://github.com/docker-library/official-images/blob/master/library/nginx)
* [Official Go image tags](https://github.com/docker-library/official-images/blob/master/library/golang)

Go 핸들러·정적 빌드와 명령 구문을 로컬 검사합니다. 이번 감사에서는 Docker daemon 접속·이미지 빌드/실행·포트 게시·이미지 절감량 측정을 하지 않았으며 실습 단계는 실행 기록이 아닙니다.

## 다음 단계
- [컨테이너 기술 퀴즈](../../quizzes/basics/03-container-technology-quiz.md)
- [파드와 워크로드 실습](../core/02-pods-and-workloads-lab.md)
