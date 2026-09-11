# Container Technology Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 45 minutes
> **Last Updated**: September 11, 2026

## Learning Objectives
- Write a Dockerfile and build an image
- Optimize images using multi-stage builds
- Practice container execution, debugging, and log inspection

## Prerequisites
- [ ] Docker CLI, a supported local Docker Engine, Bash and curl
- [ ] Completed [Container Technology](../../basics/03-container-technology.md) learning

Use one Bash terminal and a disposable **local Linux-container Docker Engine**. Verify the chosen context before continuing; the helper below pins all commands to it. Check server availability/version, not only the client version. Use a maintained Engine at least28.0.0 for the documented loopback-publishing behavior; older releases have a same-L2 reachability caveat. Docker resources and ports are created only when you run the lab, not by this audit.

---

## Exercise 1: Dockerfile Writing and Image Building

### Goal
Containerize a simple web application.

### Steps

**Step 1.1: Create project directory**
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

SSI reads the documented NGINX `hostname` variable; it is not arbitrary environment-variable expansion.

**Step 1.2: Write Dockerfile**
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

**Step 1.3: Build image**
```bash
lab_docker build --build-arg "LAB_ID=${CONTAINER_LAB_ID:?}" \
  -t "${CONTAINER_LAB_WEB_IMAGE:?}" .
lab_docker image ls "$CONTAINER_LAB_WEB_IMAGE"
```

Inspect the actual image ID and reported size. The old `~40MB` line was an unverified illustration, not a benchmark or a required result. Size varies by base image, architecture and image store. No image sizes were measured in this audit.

<details>
<summary>Need a hint?</summary>

- In `docker build -t name:tag .`, the `.` is the build context directory
- Base-image size is only one tradeoff; consider libc/runtime compatibility and required tools.
- Use `docker build --no-cache` to build without cache
</details>

### Verification
```bash
lab_docker image ls "${CONTAINER_LAB_WEB_IMAGE:?}" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
```

---

## Exercise 2: Container Execution and Debugging

### Goal
Run a container and debug its internals.

### Steps

**Step 2.1: Run container**
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

**Step 2.2: Verify container access**
```bash
curl --disable --noproxy '*' --fail --show-error --silent \
  --retry 5 --retry-delay 1 --retry-connrefused --max-time 5 \
  "http://127.0.0.1:${CONTAINER_LAB_WEB_PORT:?Run Step 2.1}/"
```

**Step 2.3: Connect to container internals**
```bash
# This shell command applies to the NGINX image, which includes sh.
lab_docker exec -it "${CONTAINER_LAB_WEB_CID:?}" sh

# Run these inside that container, then return to the original Bash shell.
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```
**Step 2.4: Check logs**
```bash
lab_docker logs "${CONTAINER_LAB_WEB_CID:?}"
lab_docker logs --tail 5 "$CONTAINER_LAB_WEB_CID"
```

<details>
<summary>Need a hint?</summary>

- `-it` in `docker exec -it` stands for interactive + TTY options
- Use `docker inspect container-name` to view detailed information
- Kubernetes has the analogous `kubectl exec -it pod-name -c container-name -- sh`; RBAC and a shell in that image are required.
</details>

### Verification
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

**Step 3.2: Multi-stage Dockerfile**
This standard-library Go program is built with `CGO_ENABLED=0`, so the scratch runtime does not need the builder's libc. It contains no shell, package manager or CA bundle; applications needing those assets require a suitable runtime or explicit files. The two tagged stages contain the same Go artifact, so their comparison isolates removal of the build environment better than comparing unrelated NGINX and Go applications. BuildKit may not otherwise leave a tagged intermediate image.

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

Compare on the same platform/store. Reported image size is not necessarily compressed download size or unique disk consumption, because layers can be shared.

**Step 3.3: Compare image sizes**
```bash
# Same Go program/artifact; the build-stage image retains the compiler and base OS.
for image in "${CONTAINER_LAB_BUILD_IMAGE:?}" "${CONTAINER_LAB_GO_IMAGE:?}"; do
  lab_docker image ls "$image" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
done
```

<details>
<summary>Need a hint?</summary>

- In multi-stage builds, use `FROM ... AS build` to name the build stage
- Use `COPY --from=build` to copy only artifacts from the previous stage
- The final image doesn't include build tools, significantly reducing size
</details>

### Verification
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

## Cleanup
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


## References and validation scope

* [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
* [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/)
* [Docker run](https://docs.docker.com/reference/cli/docker/container/run/)
* [NGINX SSI](https://nginx.org/en/docs/http/ngx_http_ssi_module.html)
* [Official NGINX image tags](https://github.com/docker-library/official-images/blob/master/library/nginx)
* [Official Go image tags](https://github.com/docker-library/official-images/blob/master/library/golang)

The Go handler/static build and command syntax can be checked locally. This audit did not contact a Docker daemon, build/run images, publish ports or measure image-size savings; the lab steps are not recorded execution results.

## Next Steps
- [Container Technology Quiz](../../quizzes/basics/03-container-technology-quiz.md)
- [Pods and Workloads Lab](../core/02-pods-and-workloads-lab.md)
