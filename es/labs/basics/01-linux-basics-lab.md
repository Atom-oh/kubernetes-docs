# Guía de laboratorio de conceptos básicos de Linux

> **Dificultad**: Principiante
> **Tiempo estimado**: 45 minutos
> **Última actualización**: February 11, 2026

## Objetivos de aprendizaje
- Practicar comandos de gestión de procesos en Linux
- Observar directamente el efecto de aislamiento de los namespaces de Linux
- Entender los límites de recursos mediante cgroups
- Practicar la gestión de permisos y propiedad de archivos

## Prerrequisitos
- [ ] Acceso a una terminal Linux (se recomienda Ubuntu 20.04+)
- [ ] Privilegios sudo
- [ ] Haber completado el aprendizaje [Conceptos básicos de Linux](../../basics/01-linux-basics.md)

---

## Ejercicio 1: Gestión de procesos

### Objetivo
Practicar el listado de procesos, la ejecución en segundo plano y el envío de señales.

### Pasos

**Paso 1.1: Comprobar los procesos que se están ejecutando actualmente**
```bash
# Processes in the current terminal
ps aux | head -20

# View process relationships in tree format
ps auxf | head -30
```

**Paso 1.2: Ejecutar un proceso en segundo plano**
```bash
# Run a sleep process in the background
sleep 300 &
echo "PID: $!"

# Check background jobs
jobs -l
```

**Paso 1.3: Enviar una señal a un proceso**
```bash
# Get the process ID
SLEEP_PID=$(pgrep -f "sleep 300")
echo "Sleep PID: $SLEEP_PID"

# Request termination with SIGTERM
kill $SLEEP_PID

# Verify the process has terminated
ps aux | grep "sleep 300" | grep -v grep
```

<details>
<summary>¿Necesitas una pista?</summary>

- Usa `kill -l` para ver una lista de las señales disponibles
- `kill -9 PID` termina forzosamente con SIGKILL
- `pkill -f "pattern"` permite la terminación basada en el nombre
</details>

### Verificación
```bash
# The sleep process should not exist
pgrep -f "sleep 300" && echo "Still running" || echo "Termination complete"
```

---

## Ejercicio 2: Aislamiento de namespaces de Linux

### Objetivo
Crear namespaces para observar el aislamiento de procesos y de red.

### Pasos

**Paso 2.1: Verificar el aislamiento del PID namespace**
```bash
# Run bash in a new PID namespace
sudo unshare --pid --fork --mount-proc bash -c '
echo "PID list inside the new namespace:"
ps aux
echo "Current process PID: $$"
'
```

Salida esperada:
```
PID list inside the new namespace:
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0   ...   ...  ...      S    ...    0:00 bash -c ...
root         2  0.0  0.0   ...   ...  ...      R    ...    0:00 ps aux
Current process PID: 1
```

**Paso 2.2: Aislamiento del network namespace**
```bash
# Create a network namespace
sudo ip netns add test-ns

# List namespaces
sudo ip netns list

# Check network inside the isolated namespace
sudo ip netns exec test-ns ip addr

# Cleanup
sudo ip netns delete test-ns
```

<details>
<summary>¿Necesitas una pista?</summary>

- Las interfaces de red del host no son visibles dentro del network namespace
- Solo existe la interfaz `lo` (loopback), y está DOWN de forma predeterminada
- Este es el principio detrás del aislamiento de red de los contenedores
</details>

### Verificación
```bash
# Verify the namespace has been deleted
sudo ip netns list | grep test-ns && echo "Still exists" || echo "Deletion complete"
```

---

## Ejercicio 3: Límites de recursos de cgroup

### Objetivo
Usar cgroups para limitar el uso de memoria de los procesos.

### Pasos

**Paso 3.1: Comprobar la información de cgroup**
```bash
# Check cgroup v2 mount
mount | grep cgroup

# Check cgroup of current process
cat /proc/self/cgroup

# Check cgroup controllers
cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null || echo "Using cgroup v1"
```

**Paso 3.2: Comprobar el uso de memoria**
```bash
# System memory information
free -h

# Memory usage of specific processes
ps aux --sort=-%mem | head -10
```

**Paso 3.3: Conexión con los límites de recursos de Kubernetes**
```bash
# This is how resources.limits works in K8s
# Let's look at a Pod manifest example
cat << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: memory-demo
spec:
  containers:
  - name: memory-demo
    image: nginx
    resources:
      requests:
        memory: "64Mi"
      limits:
        memory: "128Mi"
EOF
```

<details>
<summary>¿Necesitas una pista?</summary>

- K8s `resources.limits.memory` se traduce en límites de memoria de cgroup para el contenedor
- Superar el límite da como resultado el estado OOMKilled
- Puedes comprobar los límites de recursos con `kubectl describe pod`
</details>

---

## Ejercicio 4: Gestión de permisos de archivos

### Objetivo
Practicar la gestión de permisos y propiedad de archivos.

### Pasos

**Paso 4.1: Crear un archivo y comprobar los permisos**
```bash
# Create a test file
mkdir -p /tmp/linux-lab
echo "Hello Linux" > /tmp/linux-lab/test.txt

# Check current permissions
ls -la /tmp/linux-lab/test.txt
```

**Paso 4.2: Cambiar permisos**
```bash
# Add execute permission
chmod +x /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt

# Set with numeric mode (read/write - read - none)
chmod 640 /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt

# Set the same permissions as K8s Secret volume defaults
chmod 0644 /tmp/linux-lab/test.txt
```

**Paso 4.3: Cambiar la propiedad**
```bash
# Check current user and group
id

# Change group (if executable)
sudo chown $USER:root /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt
```

### Verificación
```bash
# Verify permissions are -rw-r--r--
stat -c "%a %U %G" /tmp/linux-lab/test.txt
```

---

## Limpieza
```bash
# Delete test files
rm -rf /tmp/linux-lab

# Clean up remaining processes
pkill -f "sleep 300" 2>/dev/null
```

## Solución de problemas

<details>
<summary>El comando unshare no se encuentra</summary>

Instala el paquete `util-linux`:
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo yum install util-linux       # CentOS/RHEL
```
</details>

<details>
<summary>El comando ip netns no funciona</summary>

Se requiere el paquete `iproute2`:
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo yum install iproute          # CentOS/RHEL
```
</details>

## Próximos pasos
- [Cuestionario de conceptos básicos de Linux](../../quizzes/basics/01-linux-basics-quiz.md)
- [Laboratorio de habilidades avanzadas de Linux](./02-linux-advanced-lab.md)
