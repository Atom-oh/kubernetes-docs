# Guía de laboratorio de tecnología de contenedores

> **Dificultad**: Principiante
> **Tiempo estimado**: 45 minutos
> **Última actualización**: February 11, 2026

## Objetivos de aprendizaje
- Escribir un Dockerfile y construir una imagen
- Optimizar imágenes usando builds multi-stage
- Practicar la ejecución de contenedores, la depuración y la inspección de logs

## Prerrequisitos
- [ ] Docker instalado (verificar con `docker --version`)
- [ ] Haber completado el aprendizaje de [Tecnología de contenedores](../../basics/03-container-technology.md)

---

## Ejercicio 1: Escritura de Dockerfile y construcción de imágenes

### Objetivo
Contenerizar una aplicación web sencilla.

### Pasos

**Paso 1.1: Crear el directorio del proyecto**
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

**Paso 1.2: Escribir Dockerfile**
```bash
cat > Dockerfile << 'EOF'
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
```

**Paso 1.3: Construir la imagen**
```bash
docker build -t my-web:v1 .
docker images my-web
```

Salida esperada:
```
REPOSITORY   TAG   IMAGE ID       CREATED         SIZE
my-web       v1    abc123def456   5 seconds ago   ~40MB
```

<details>
<summary>¿Necesitas una pista?</summary>

- En `docker build -t name:tag .`, el `.` es el directorio de contexto de build
- Las imágenes basadas en `alpine` son pequeñas, lo cual es ventajoso para el deployment en K8s
- Usa `docker build --no-cache` para construir sin caché
</details>

### Verificación
```bash
docker images my-web:v1 --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
```

---

## Ejercicio 2: Ejecución y depuración de contenedores

### Objetivo
Ejecutar un contenedor y depurar su interior.

### Pasos

**Paso 2.1: Ejecutar el contenedor**
```bash
docker run -d --name my-web-container -p 8080:80 my-web:v1
docker ps
```

**Paso 2.2: Verificar el acceso al contenedor**
```bash
curl http://localhost:8080
```

**Paso 2.3: Conectarse al interior del contenedor**
```bash
# Shell into the running container
docker exec -it my-web-container sh

# Run inside the container
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```

**Paso 2.4: Comprobar logs**
```bash
docker logs my-web-container
docker logs --tail 5 my-web-container
```

<details>
<summary>¿Necesitas una pista?</summary>

- `-it` en `docker exec -it` representa las opciones interactivo + TTY
- Usa `docker inspect container-name` para ver información detallada
- En K8s, esto equivale a `kubectl exec -it pod-name -- sh`
</details>

### Verificación
```bash
# Check HTTP response code
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080)
[ "$HTTP_CODE" = "200" ] && echo "Success! HTTP $HTTP_CODE" || echo "Failed: HTTP $HTTP_CODE"
```

---

## Ejercicio 3: Build multi-stage

### Objetivo
Usar builds multi-stage para optimizar el tamaño de la imagen.

### Pasos

**Paso 3.1: Crear una aplicación Go**
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

**Paso 3.2: Dockerfile multi-stage**
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

**Paso 3.3: Comparar tamaños de imágenes**
```bash
docker images | grep -E "my-web|my-go-app|golang"
```

<details>
<summary>¿Necesitas una pista?</summary>

- En los builds multi-stage, usa `FROM ... AS builder` para nombrar la etapa de build
- Usa `COPY --from=builder` para copiar solo artefactos desde la etapa anterior
- La imagen final no incluye herramientas de build, lo que reduce significativamente el tamaño
</details>

### Verificación
```bash
echo "Go app image size:"
docker images my-go-app:v1 --format "{{.Size}}"
```

---

## Limpieza
```bash
docker stop my-web-container 2>/dev/null
docker rm my-web-container 2>/dev/null
docker rmi my-web:v1 my-go-app:v1 2>/dev/null
rm -rf /tmp/container-lab
```

## Próximos pasos
- [Cuestionario de tecnología de contenedores](../../quizzes/basics/03-container-technology-quiz.md)
- [Laboratorio de Pods y Workloads](../core/02-pods-and-workloads-lab.md)
