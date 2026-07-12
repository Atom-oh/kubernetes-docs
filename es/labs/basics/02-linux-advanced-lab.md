# Guía de laboratorio de habilidades avanzadas de Linux

> **Dificultad**: Principiante
> **Tiempo estimado**: 40 minutos
> **Última actualización**: February 11, 2026

## Objetivos de aprendizaje
- Practicar el análisis de datos JSON usando jq
- Escribir scripts de shell sencillos
- Procesar la salida de kubectl con pipelines

## Requisitos previos
- [ ] Acceso a una terminal Linux
- [ ] jq instalado (`sudo apt-get install jq` o `sudo yum install jq`)
- [ ] Haber completado el aprendizaje de [Habilidades de operaciones en Linux](../../basics/02-linux-advanced.md)

---

## Ejercicio 1: Análisis de JSON con jq

### Objetivo
Procesar datos JSON similares a la salida de Kubernetes kubectl usando jq.

### Pasos

**Paso 1.1: Crear JSON de ejemplo**
```bash
cat > /tmp/pods.json << 'EOF'
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

**Paso 1.2: Consultas básicas de jq**
```bash
# Extract only Pod names
jq '.items[].metadata.name' /tmp/pods.json

# Filter only Pods in Running state
jq '.items[] | select(.status.phase == "Running") | .metadata.name' /tmp/pods.json

# Output in table format
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' /tmp/pods.json
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
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' /tmp/pods.json

# Filter based on labels
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' /tmp/pods.json
```

<details>
<summary>¿Necesitas una pista?</summary>

- `jq -r` elimina las comillas de las cadenas
- `select(condition)` filtra solo los elementos que coinciden con la condición
- `@tsv` genera salida en formato separado por tabulaciones
- En K8s real, úsalo así: `kubectl get pods -o json | jq '...'`
</details>

### Verificación
```bash
# Verify that the number of Running Pods is 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' /tmp/pods.json)
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## Ejercicio 2: Escritura de scripts de shell

### Objetivo
Escribir scripts de shell sencillos útiles para operaciones de K8s.

### Pasos

**Paso 2.1: Script de Health Check**
```bash
cat > /tmp/health-check.sh << 'SCRIPT'
#!/bin/bash
# Health check script that can be used in K8s liveness probes

ENDPOINT="${1:-http://localhost:8080/health}"
TIMEOUT="${2:-5}"

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$ENDPOINT" 2>/dev/null)

if [ "$response" = "200" ]; then
    echo "OK: Health check passed (HTTP $response)"
    exit 0
else
    echo "FAIL: Health check failed (HTTP $response)"
    exit 1
fi
SCRIPT

chmod +x /tmp/health-check.sh
cat /tmp/health-check.sh
```

**Paso 2.2: Script de análisis de logs**
```bash
cat > /tmp/log-analyzer.sh << 'SCRIPT'
#!/bin/bash
# Script to analyze error patterns in log files

LOG_FILE="${1:-/tmp/sample.log}"

# Generate sample logs
if [ ! -f "$LOG_FILE" ]; then
    for i in $(seq 1 100); do
        level=$((RANDOM % 4))
        case $level in
            0) echo "$(date -Iseconds) INFO  Request processed successfully" ;;
            1) echo "$(date -Iseconds) WARN  High memory usage detected" ;;
            2) echo "$(date -Iseconds) ERROR Connection timeout to database" ;;
            3) echo "$(date -Iseconds) INFO  Health check passed" ;;
        esac
    done > "$LOG_FILE"
fi

echo "=== Log Analysis Results ==="
echo "Total lines: $(wc -l < "$LOG_FILE")"
echo ""
echo "Statistics by level:"
grep -oP '(INFO|WARN|ERROR)' "$LOG_FILE" | sort | uniq -c | sort -rn
echo ""
echo "Recent errors (last 5):"
grep "ERROR" "$LOG_FILE" | tail -5
SCRIPT

chmod +x /tmp/log-analyzer.sh
bash /tmp/log-analyzer.sh
```

<details>
<summary>¿Necesitas una pista?</summary>

- `$((RANDOM % N))` genera un número aleatorio de 0 a N-1
- `grep -oP` extrae solo la parte coincidente usando regex de Perl
- `sort | uniq -c | sort -rn` es el patrón básico para contar frecuencias
</details>

### Verificación
```bash
# Verify scripts are executable
[ -x /tmp/health-check.sh ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x /tmp/log-analyzer.sh ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## Ejercicio 3: Pipeline de procesamiento de texto

### Objetivo
Procesar datos combinando grep, awk y sed.

### Pasos

**Paso 3.1: Búsqueda de patrones con grep**
```bash
# Extract ERROR lines from sample log
grep "ERROR" /tmp/sample.log | head -5

# Extract errors by time period (using regex)
grep -P "T\d{2}:" /tmp/sample.log | grep ERROR | head -5
```

**Paso 3.2: Extracción de campos con awk**
```bash
# Extract only time and level from log
awk '{print $1, $2}' /tmp/sample.log | head -10

# Filter only ERROR level and count
awk '$2 == "ERROR" {count++} END {print "Error count:", count}' /tmp/sample.log
```

**Paso 3.3: Transformación de texto con sed**
```bash
# Convert log levels to different text
sed 's/INFO/info/g; s/WARN/warning/g; s/ERROR/error/g' /tmp/sample.log | head -5

# Change K8s YAML values (ConfigMap update simulation)
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**Paso 3.4: Combinación de pipelines**
```bash
# Frequency analysis by error message
grep "ERROR" /tmp/sample.log | awk '{$1=$2=""; print $0}' | sort | uniq -c | sort -rn
```

### Verificación
```bash
echo "Exercise complete! Feel free to experiment with pipeline combinations."
```

---

## Limpieza
```bash
rm -f /tmp/pods.json /tmp/health-check.sh /tmp/log-analyzer.sh /tmp/sample.log
```

## Siguientes pasos
- [Cuestionario de habilidades avanzadas de Linux](../../quizzes/basics/02-linux-advanced-quiz.md)
- [Laboratorio de tecnología de contenedores](./03-container-technology-lab.md)
