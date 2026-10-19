# Guía de laboratorio de habilidades avanzadas de Linux

> **Dificultad**: Principiante
> **Tiempo estimado**: 40 minutos
> **Última actualización**: 11 de septiembre de 2026

## Objetivos de aprendizaje
- Practicar el análisis de datos JSON con jq
- Escribir scripts de shell sencillos
- Procesar la salida de kubectl mediante pipelines

## Requisitos previos
- [ ] Bash y herramientas de texto estándar de Linux (awk, grep, sed, coreutils)
- [ ] jq y curl instalados (`sudo apt-get install jq curl` o `sudo dnf install jq curl`)
- [ ] Haber completado el material de aprendizaje [Habilidades de operaciones en Linux](../../basics/02-linux-advanced.md)

Usa la misma terminal de Bash para todos los pasos. Los archivos se crearán en un directorio temporal privado. La PodList reducida es un conjunto de datos de prueba para analizar JSON, no un manifiesto que debas aplicar; no se necesita un clúster de Kubernetes. Que el campo phase indique Running no significa por sí solo que un Pod esté Ready.

---

## Ejercicio 1: Análisis de JSON con jq

### Objetivo
Procesar datos JSON similares a la salida de kubectl para Kubernetes mediante jq.

### Pasos

**Paso 1.1: Crear el JSON de ejemplo**
```bash
LINUX_ADVANCED_LAB_DIR=$(mktemp -d /tmp/k8s-docs-linux-advanced.XXXXXX)
: "${LINUX_ADVANCED_LAB_DIR:?mktemp failed}"
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json" << 'EOF'
{
  "apiVersion": "v1",
  "kind": "PodList",
  "items": [
    {
      "metadata": {"name": "nginx-7d4f8b", "namespace": "default", "labels": {"app": "nginx"}},
      "status": {"phase": "Running", "podIP": "10.244.0.5"}
    },
    {
      "metadata": {"name": "redis-abc123", "namespace": "cache", "labels": {"app": "redis"}},
      "status": {"phase": "Running", "podIP": "10.244.1.3"}
    },
    {
      "metadata": {"name": "api-server-xyz", "namespace": "default", "labels": {"app": "api"}},
      "status": {"phase": "Pending", "podIP": null}
    }
  ]
}
EOF
```

**Paso 1.2: Consultas básicas con jq**
```bash
# Extract only Pod names
jq '.items[].metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Filter only Pods in Running state
jq '.items[] | select(.status.phase == "Running") | .metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Output in table format
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

Salida esperada:
```
nginx-7d4f8b    default    Running
redis-abc123    cache      Running
api-server-xyz  default    Pending
```

**Paso 1.3: Pipelines avanzados de jq**
```bash
# Count Pods by namespace
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Filter based on labels
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

<details>
<summary>¿Necesitas una pista?</summary>

- `jq -r` quita las comillas de las cadenas
- `select(condition)` filtra solo los elementos que cumplen la condición
- `@tsv` genera una salida separada por tabuladores
- En un clúster K8s real, úsalo así: `kubectl get pods -A -o json | jq '...'`
</details>

### Verificación
```bash
# Verify that the number of Running Pods is 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json")
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## Ejercicio 2: Escritura de scripts de shell

### Objetivo
Escribir scripts de shell sencillos que sean útiles para las operaciones de K8s.

### Pasos

**Paso 2.1: Script de comprobación de estado**
El script exige intencionadamente una respuesta HTTP 200. Valida el tiempo de espera y considera fallida una transferencia de curl que falle, incluso si se recibió una cabecera 200. Envía solicitudes directas, sin configuraciones de curlrc ni de proxy. La aplicación debe proporcionar realmente el endpoint; no supongas que el script lo crea. En Kubernetes, prefiere una sonda nativa httpGet cuando sea posible. Su regla de éxito 200–399 difiere de la de este script; una sonda exec también necesita Bash/curl en la imagen y un tiempo de espera de sonda que permita completar el presupuesto del script.

```bash
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh" << 'SCRIPT'
#!/bin/bash
set -u

ENDPOINT="${1:-http://127.0.0.1:8080/health}"
TIMEOUT="${2:-5}"
if (( $# > 2 )) || ! [[ "$TIMEOUT" =~ ^[1-9][0-9]?$ ]] || (( TIMEOUT > 60 )); then
    printf 'Usage: health-check.sh [http(s) URL] [timeout integer 1..60]\n' >&2
    exit 2
fi
case "$ENDPOINT" in
    http://*|https://*) ;;
    *) printf 'Only HTTP(S) endpoints are supported\n' >&2; exit 2 ;;
esac

# Ignore curlrc and proxies for this direct health-endpoint check.
if ! response=$(curl --disable --noproxy '*' --silent --show-error \
    --output /dev/null --write-out '%{http_code}' \
    --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" -- "$ENDPOINT"); then
    printf 'FAIL: transport error or timeout\n' >&2
    exit 1
fi
if [[ "$response" == "200" ]]; then
    printf 'OK: health endpoint returned HTTP 200\n'
    exit 0
fi
printf 'FAIL: health endpoint returned HTTP %s\n' "$response" >&2
exit 1
SCRIPT
chmod +x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh"
```

**Paso 2.2: Script de análisis de logs**
Crea explícitamente el siguiente archivo de prueba sintético de seis líneas. El analizador lee un archivo regular proporcionado y nunca inventa datos si la ruta es incorrecta. Supone una instantánea estática con la marca de tiempo y el nivel en los campos 1 y 2. El registro INFO que contiene la palabra ERROR no debe contarse como error.

```bash
# Explicit synthetic fixture, not a copy of production logs.
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" << 'LOG'
2026-01-01T10:00:00Z INFO Application started
2026-01-01T10:00:01Z WARN Cache warming
2026-01-01T10:00:02Z ERROR Database connection timeout
2026-01-01T10:00:03Z INFO The word ERROR appears in this message
2026-01-01T10:00:04Z ERROR Upstream request timeout
2026-01-01T10:00:05Z INFO Health check passed
LOG

cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" << 'SCRIPT'
#!/bin/bash
set -euo pipefail

if (( $# != 1 )) || [[ ! -f "$1" || ! -r "$1" ]]; then
    printf 'Usage: log-analyzer.sh readable-regular-log-file\n' >&2
    exit 2
fi
LOG_FILE="$1"

# Assumes a static snapshot: first field UTC timestamp, second field log level.
printf 'Total lines: %s\n' "$(wc -l < "$LOG_FILE")"
printf 'Counts by level:\n'
awk '$2 ~ /^(INFO|WARN|ERROR)$/ {count[$2]++}
     END {for (level in count) print count[level], level}' "$LOG_FILE" | sort -rn
printf 'Recent ERROR records (last 5):\n'
awk '$2 == "ERROR"' "$LOG_FILE" | tail -5
SCRIPT
chmod +x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh"
bash "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

<details>
<summary>¿Necesitas una pista?</summary>

- `awk` puede comparar exactamente el campo de nivel; una palabra que aparezca en otra parte del mensaje es distinta.
- `grep -E` usa expresiones regulares extendidas; estos ejemplos no necesitan compatibilidad con expresiones regulares de Perl.
- El archivo de prueba tiene 6 registros: INFO 3, WARN 1 y ERROR 2. Son recuentos sintéticos, no registros observados de un servicio.
</details>

### Verificación
```bash
# Verify scripts are executable
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh" ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## Ejercicio 3: Pipeline de procesamiento de texto

### Objetivo
Procesar datos combinando grep, awk y sed.

### Pasos

**Paso 3.1: Búsqueda de patrones con grep**
```bash
# Match the level field, not the word ERROR inside a message.
grep -E '^[^[:space:]]+[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Sample UTC window: 10:00:02 through 10:00:04 on the fixture date.
grep -E '^2026-01-01T10:00:0[2-4]Z[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**Paso 3.2: Extracción de campos con awk**
```bash
# Extract only time and level from log
awk '{print $1, $2}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -10

# Filter only ERROR level and count
awk '$2 == "ERROR" {count++} END {print "Error count:", count+0}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**Paso 3.3: Transformación de texto con sed**
```bash
# Convert log levels to different text
sed -E 's/^([^[:space:]]+[[:space:]]+)INFO([[:space:]]|$)/\1info\2/; s/^([^[:space:]]+[[:space:]]+)WARN([[:space:]]|$)/\1warning\2/; s/^([^[:space:]]+[[:space:]]+)ERROR([[:space:]]|$)/\1error\2/' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Text-only Deployment replica-field example; not a ConfigMap or API update
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**Paso 3.4: Combinación de comandos en un pipeline**
```bash
awk '$2 == "ERROR" {sub(/^[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+/, ""); print}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | sort | uniq -c | sort -rn
```

### Verificación
```bash
echo "Exercise complete! Feel free to experiment with pipeline combinations."
```

---

## Limpieza
```bash
if [[ -n ${LINUX_ADVANCED_LAB_DIR:-} ]]; then
  rm -f -- "$LINUX_ADVANCED_LAB_DIR/pods.json" \
    "$LINUX_ADVANCED_LAB_DIR/health-check.sh" \
    "$LINUX_ADVANCED_LAB_DIR/log-analyzer.sh" \
    "$LINUX_ADVANCED_LAB_DIR/sample.log"
  if rmdir -- "$LINUX_ADVANCED_LAB_DIR"; then
    unset LINUX_ADVANCED_LAB_DIR
  fi
fi
```

## Referencias y alcance de la validación

* [Manual de jq](https://jqlang.org/manual/)
* [Manual de curl](https://curl.se/docs/manpage.html)
* [Sondas de Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

La validación usa archivos locales sintéticos de JSON y logs, además de códigos de estado y de salida simulados de curl. No se accede a ningún endpoint de estado en vivo, a logs de producción ni a la API de Kubernetes.

## Siguientes pasos
- [Cuestionario de habilidades avanzadas de Linux](../../quizzes/basics/02-linux-advanced-quiz.md)
- [Laboratorio de tecnología de contenedores](./03-container-technology-lab.md)
