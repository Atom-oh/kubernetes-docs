# Container Technology Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 45 minutes
> **Last Updated**: February 2025

## Learning Objectives
- Write a Dockerfile and build an image
- Optimize images using multi-stage builds
- Practice container execution, debugging, and log inspection

## Prerequisites
- [ ] Docker installed (verify with `docker --version`)
- [ ] Completed [Container Technology](../../basics/03-container-technology.md) learning

---

## Exercise 1: Dockerfile Writing and Image Building

### Goal
Containerize a simple web application.

### Steps

**Step 1.1: Create project directory**
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

**Step 1.2: Write Dockerfile**
```bash
cat > Dockerfile << 'EOF'
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
```

**Step 1.3: Build image**
```bash
docker build -t my-web:v1 .
docker images my-web
```

Expected output:
```
REPOSITORY   TAG   IMAGE ID       CREATED         SIZE
my-web       v1    abc123def456   5 seconds ago   ~40MB
```

<details>
<summary>Need a hint?</summary>

- In `docker build -t name:tag .`, the `.` is the build context directory
- `alpine`-based images are small, which is advantageous for K8s deployment
- Use `docker build --no-cache` to build without cache
</details>

### Verification
```bash
docker images my-web:v1 --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
```

---

## Exercise 2: Container Execution and Debugging

### Goal
Run a container and debug its internals.

### Steps

**Step 2.1: Run container**
```bash
docker run -d --name my-web-container -p 8080:80 my-web:v1
docker ps
```

**Step 2.2: Verify container access**
```bash
curl http://localhost:8080
```

**Step 2.3: Connect to container internals**
```bash
# Shell into the running container
docker exec -it my-web-container sh

# Run inside the container
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```

**Step 2.4: Check logs**
```bash
docker logs my-web-container
docker logs --tail 5 my-web-container
```

<details>
<summary>Need a hint?</summary>

- `-it` in `docker exec -it` stands for interactive + TTY options
- Use `docker inspect container-name` to view detailed information
- In K8s, this is equivalent to `kubectl exec -it pod-name -- sh`
</details>

### Verification
```bash
# Check HTTP response code
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080)
[ "$HTTP_CODE" = "200" ] && echo "Success! HTTP $HTTP_CODE" || echo "Failed: HTTP $HTTP_CODE"
```

---

## Exercise 3: Multi-stage Build

### Goal
Use multi-stage builds to optimize image size.

### Steps

**Step 3.1: Create Go application**
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

**Step 3.2: Multi-stage Dockerfile**
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

**Step 3.3: Compare image sizes**
```bash
docker images | grep -E "my-web|my-go-app|golang"
```

<details>
<summary>Need a hint?</summary>

- In multi-stage builds, use `FROM ... AS builder` to name the build stage
- Use `COPY --from=builder` to copy only artifacts from the previous stage
- The final image doesn't include build tools, significantly reducing size
</details>

### Verification
```bash
echo "Go app image size:"
docker images my-go-app:v1 --format "{{.Size}}"
```

---

## Cleanup
```bash
docker stop my-web-container 2>/dev/null
docker rm my-web-container 2>/dev/null
docker rmi my-web:v1 my-go-app:v1 2>/dev/null
rm -rf /tmp/container-lab
```

## Next Steps
- [Container Technology Quiz](../../quizzes/basics/03-container-technology-quiz.md)
- [Pods and Workloads Lab](../core/02-pods-and-workloads-lab.md)
