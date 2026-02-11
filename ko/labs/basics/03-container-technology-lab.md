# 컨테이너 기술 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 45분
> **마지막 업데이트**: 2025년 2월

## 학습 목표
- Dockerfile을 작성하고 이미지를 빌드합니다
- 멀티스테이지 빌드를 활용하여 이미지를 최적화합니다
- 컨테이너 실행, 디버깅, 로그 확인을 실습합니다

## 사전 요구 사항
- [ ] Docker 설치 (`docker --version`으로 확인)
- [ ] [컨테이너 기술](../../basics/03-container-technology.md) 학습 완료

---

## 실습 1: Dockerfile 작성과 이미지 빌드

### 목표
간단한 웹 애플리케이션을 컨테이너화합니다.

### 단계

**Step 1.1: 프로젝트 디렉토리 생성**
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

**Step 1.2: Dockerfile 작성**
```bash
cat > Dockerfile << 'EOF'
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
```

**Step 1.3: 이미지 빌드**
```bash
docker build -t my-web:v1 .
docker images my-web
```

예상 결과:
```
REPOSITORY   TAG   IMAGE ID       CREATED         SIZE
my-web       v1    abc123def456   5 seconds ago   ~40MB
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `docker build -t 이름:태그 .`에서 `.`은 빌드 컨텍스트 디렉토리입니다
- `alpine` 기반 이미지는 크기가 작아서 K8s 배포에 유리합니다
- `docker build --no-cache`로 캐시 없이 빌드할 수 있습니다
</details>

### 검증
```bash
docker images my-web:v1 --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
```

---

## 실습 2: 컨테이너 실행과 디버깅

### 목표
컨테이너를 실행하고 내부를 디버깅합니다.

### 단계

**Step 2.1: 컨테이너 실행**
```bash
docker run -d --name my-web-container -p 8080:80 my-web:v1
docker ps
```

**Step 2.2: 컨테이너 접근 확인**
```bash
curl http://localhost:8080
```

**Step 2.3: 컨테이너 내부 접속**
```bash
# 실행 중인 컨테이너에 shell 접속
docker exec -it my-web-container sh

# 컨테이너 내부에서 실행
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```

**Step 2.4: 로그 확인**
```bash
docker logs my-web-container
docker logs --tail 5 my-web-container
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `docker exec -it`의 `-it`는 interactive + TTY 옵션입니다
- `docker inspect 컨테이너명`으로 상세 정보를 확인할 수 있습니다
- K8s에서는 `kubectl exec -it pod명 -- sh`와 동일합니다
</details>

### 검증
```bash
# HTTP 응답 코드 확인
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080)
[ "$HTTP_CODE" = "200" ] && echo "성공! HTTP $HTTP_CODE" || echo "실패: HTTP $HTTP_CODE"
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

**Step 3.2: 멀티스테이지 Dockerfile**
```bash
cat > Dockerfile.multi << 'EOF'
# Stage 1: 빌드
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY main.go .
RUN go build -o server main.go

# Stage 2: 실행 (최소 이미지)
FROM alpine:3.19
COPY --from=builder /app/server /server
EXPOSE 8080
CMD ["/server"]
EOF

docker build -f Dockerfile.multi -t my-go-app:v1 .
```

**Step 3.3: 이미지 크기 비교**
```bash
docker images | grep -E "my-web|my-go-app|golang"
```

<details>
<summary>힌트가 필요하신가요?</summary>

- 멀티스테이지 빌드에서 `FROM ... AS builder`로 빌드 스테이지에 이름을 부여합니다
- `COPY --from=builder`로 이전 스테이지의 산출물만 복사합니다
- 최종 이미지에는 빌드 도구가 포함되지 않아 크기가 대폭 줄어듭니다
</details>

### 검증
```bash
echo "Go 앱 이미지 크기:"
docker images my-go-app:v1 --format "{{.Size}}"
```

---

## 정리
```bash
docker stop my-web-container 2>/dev/null
docker rm my-web-container 2>/dev/null
docker rmi my-web:v1 my-go-app:v1 2>/dev/null
rm -rf /tmp/container-lab
```

## 다음 단계
- [컨테이너 기술 퀴즈](../../quizzes/basics/03-container-technology-quiz.md)
- [파드와 워크로드 실습](../core/02-pods-and-workloads-lab.md)
