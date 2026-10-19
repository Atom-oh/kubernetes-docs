# Guía de laboratorio de tecnología de contenedores

> **Dificultad**: Principiante
> **Tiempo estimado**: 45 minutos
> **Última actualización**: 16 de octubre de 2026

## Objetivos de aprendizaje
- Escribir un Dockerfile y crear una imagen
- Optimizar imágenes mediante compilaciones multietapa
- Practicar la ejecución de contenedores, la depuración y la inspección de registros

## Requisitos previos
- [ ] Docker CLI, Docker Engine local compatible, Bash y curl
- [ ] Haber completado el módulo de aprendizaje sobre [tecnología de contenedores](../../basics/03-container-technology.md)

Usa una sola terminal Bash y un **Docker Engine local y desechable para contenedores Linux**. Antes de continuar, verifica el contexto elegido; la función auxiliar de abajo fija todos los comandos a ese contexto. Comprueba que el servidor esté disponible y su versión; no basta con revisar la versión del cliente. Para el comportamiento documentado de publicación en loopback, usa una versión mantenida de Engine igual o posterior a 28.0.0; las versiones anteriores tienen una salvedad de alcance que permite el acceso desde la misma capa 2. Los recursos y puertos de Docker solo se crean cuando ejecutas el laboratorio; esta auditoría no los crea.

---

## Ejercicio 1: escribir un Dockerfile y crear una imagen

### Objetivo
Empaqueta una aplicación web sencilla en un contenedor.

### Pasos

**Paso 1.1: crear el directorio del proyecto**
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

SSI lee la variable `hostname` documentada por NGINX; no expande variables de entorno arbitrarias.

**Paso 1.2: escribir el Dockerfile**
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

**Paso 1.3: crear la imagen**
```bash
lab_docker build --build-arg "LAB_ID=${CONTAINER_LAB_ID:?}" \
  -t "${CONTAINER_LAB_WEB_IMAGE:?}" .
lab_docker image ls "$CONTAINER_LAB_WEB_IMAGE"
```

Inspecciona el ID real de la imagen y el tamaño que informa Docker. La antigua cifra `~40MB` era un ejemplo sin verificar, no una medición de referencia ni un resultado obligatorio. El tamaño varía según la imagen base, la arquitectura y el almacén de imágenes. En esta auditoría no se midió el tamaño de ninguna imagen.

<details>
<summary>¿Necesitas una pista?</summary>

- En `docker build -t name:tag .`, `.` indica el directorio del contexto de compilación
- El tamaño de la imagen base es solo un factor; ten en cuenta la compatibilidad con libc y el entorno de ejecución, además de las herramientas necesarias.
- Usa `docker build --no-cache` para crear la imagen sin usar la caché
</details>

### Verificación
```bash
lab_docker image ls "${CONTAINER_LAB_WEB_IMAGE:?}" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
```

---

## Ejercicio 2: ejecutar y depurar contenedores

### Objetivo
Ejecuta un contenedor y examina su funcionamiento interno.

### Pasos

**Paso 2.1: ejecutar el contenedor**
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

**Paso 2.2: verificar el acceso al contenedor**
```bash
curl --disable --noproxy '*' --fail --show-error --silent \
  --retry 5 --retry-delay 1 --retry-connrefused --max-time 5 \
  "http://127.0.0.1:${CONTAINER_LAB_WEB_PORT:?Run Step 2.1}/"
```

**Paso 2.3: acceder al interior del contenedor**
```bash
# This shell command applies to the NGINX image, which includes sh.
lab_docker exec -it "${CONTAINER_LAB_WEB_CID:?}" sh

# Run these inside that container, then return to the original Bash shell.
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```
**Paso 2.4: revisar los registros**
```bash
lab_docker logs "${CONTAINER_LAB_WEB_CID:?}"
lab_docker logs --tail 5 "$CONTAINER_LAB_WEB_CID"
```

<details>
<summary>¿Necesitas una pista?</summary>

- En `docker exec -it`, `-i` mantiene la entrada interactiva y `-t` asigna un seudoterminal (TTY)
- Usa `docker inspect container-name` para consultar información detallada
- En Kubernetes, el comando equivalente es `kubectl exec -it pod-name -c container-name -- sh`; se requieren permisos RBAC y que la imagen incluya un shell.
</details>

### Verificación
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

## Ejercicio 3: compilación multietapa

### Objetivo
Usa compilaciones multietapa para optimizar el tamaño de la imagen.

### Pasos

**Paso 3.1: crear la aplicación en Go**
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

**Paso 3.2: Dockerfile multietapa**
Este programa de Go, que usa la biblioteca estándar, se compila con `CGO_ENABLED=0`; por eso, el entorno de ejecución `scratch` no necesita la libc del compilador. `scratch` no incluye shell, gestor de paquetes ni conjunto de certificados de autoridades de certificación (CA); las aplicaciones que necesiten esos recursos requieren un entorno adecuado o que se copien los archivos explícitamente. Las dos etapas etiquetadas contienen el mismo artefacto de Go, así que compararlas permite aislar mejor la eliminación del entorno de compilación que comparar aplicaciones distintas de NGINX y Go. De lo contrario, BuildKit quizá no conserve una etiqueta para la imagen intermedia.

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

Compara las imágenes en la misma plataforma y el mismo almacén. El tamaño informado no equivale necesariamente al tamaño comprimido de descarga ni al espacio de disco exclusivo, porque las capas pueden compartirse.

**Paso 3.3: comparar el tamaño de las imágenes**
```bash
# Same Go program/artifact; the build-stage image retains the compiler and base OS.
for image in "${CONTAINER_LAB_BUILD_IMAGE:?}" "${CONTAINER_LAB_GO_IMAGE:?}"; do
  lab_docker image ls "$image" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
done
```

<details>
<summary>¿Necesitas una pista?</summary>

- En una compilación multietapa, usa `FROM ... AS build` para asignar un nombre a la etapa de compilación
- Usa `COPY --from=build` para copiar solo los artefactos de la etapa anterior
- La imagen final no incluye las herramientas de compilación, lo que reduce considerablemente su tamaño
</details>

### Verificación
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

## Limpieza
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


## Referencias y alcance de la validación

* [Compilaciones multietapa de Docker](https://docs.docker.com/build/building/multi-stage/)
* [Publicación de puertos de Docker](https://docs.docker.com/engine/network/port-publishing/)
* [Comando docker run](https://docs.docker.com/reference/cli/docker/container/run/)
* [SSI de NGINX](https://nginx.org/en/docs/http/ngx_http_ssi_module.html)
* [Etiquetas oficiales de la imagen de NGINX](https://github.com/docker-library/official-images/blob/master/library/nginx)
* [Etiquetas oficiales de la imagen de Go](https://github.com/docker-library/official-images/blob/master/library/golang)

El controlador de Go, la compilación estática y la sintaxis de los comandos se pueden comprobar localmente. Esta auditoría no se conectó a un daemon de Docker, no creó ni ejecutó imágenes, no publicó puertos ni midió el ahorro de tamaño; los pasos del laboratorio no son resultados de una ejecución registrada.

## Próximos pasos
- [Cuestionario de tecnología de contenedores](../../quizzes/basics/03-container-technology-quiz.md)
- [Laboratorio de pods y cargas de trabajo](../core/02-pods-and-workloads-lab.md)
