# Guía del laboratorio de conceptos básicos de Linux

> **Dificultad**: Principiante
> **Tiempo estimado**: 45 minutos
> **Última actualización**: 16 de octubre de 2026

## Objetivos de aprendizaje
- Practicar comandos de gestión de procesos en Linux
- Observar directamente el efecto de aislamiento de los namespaces de Linux
- Comprender los límites de recursos mediante cgroups
- Practicar la gestión de permisos y propiedad de archivos

## Requisitos previos
- [ ] Una VM Linux con una distribución mantenida, Bash, systemd y cgroup v2 para el ejercicio 3
- [ ] Herramientas: coreutils, procps/procps-ng, util-linux, iproute2/iproute y Python 3
- [ ] Privilegios de sudo
- [ ] Haber completado el curso de [Conceptos básicos de Linux](../../basics/01-linux-basics.md)

Ejecuta los bloques en orden y en la misma terminal de Bash para que las variables del laboratorio sigan disponibles. Usa una VM aislada para los ejercicios de namespaces/cgroups con sudo. A un contenedor o entorno restringido pueden faltarle las capacidades necesarias, incluso con sudo. Los resultados que aparecen a continuación son ilustrativos; los ejercicios con privilegios no se ejecutaron durante esta auditoría.

---

## Ejercicio 1: Gestión de procesos

### Objetivo
Practicar el listado de procesos, la ejecución en segundo plano y el envío de señales.

### Pasos

**Paso 1.1: Comprobar los procesos que se están ejecutando actualmente**
```bash
# Snapshot of processes visible in the current PID namespace
ps aux | head -20

# View process relationships in tree format
ps auxf | head -30
```

**Paso 1.2: Ejecutar un proceso en segundo plano**
```bash
sleep 300 &
LINUX_LAB_SLEEP_PID=$!
printf 'Lab child PID: %s\n' "$LINUX_LAB_SLEEP_PID"
jobs -l
```

**Paso 1.3: Enviar una señal a un proceso**
```bash
# Run in the same Bash session as Step 1.2.
: "${LINUX_LAB_SLEEP_PID:?Run Step 1.2 first}"
if jobs -pr | grep -Fxq -- "$LINUX_LAB_SLEEP_PID"; then
  kill -TERM "$LINUX_LAB_SLEEP_PID"
fi
if wait "$LINUX_LAB_SLEEP_PID"; then
  LINUX_LAB_EXIT_STATUS=0
else
  LINUX_LAB_EXIT_STATUS=$?
fi
printf 'Lab child exit status: %s\n' "$LINUX_LAB_EXIT_STATUS"
unset LINUX_LAB_SLEEP_PID
```

<details>
<summary>¿Necesitas una pista?</summary>

- Usa `kill -l` para ver la lista de señales disponibles
- `kill -9 PID` termina el proceso por la fuerza con SIGKILL
- Guarda el PID capturado con `$!`; los patrones de nombres pueden coincidir con otros trabajos no relacionados.
</details>

### Verificación
```bash
printf 'Recorded lab child exit status: %s\n' "${LINUX_LAB_EXIT_STATUS:?Complete Step 1.3}"
jobs -l
```

---

## Ejercicio 2: Aislamiento de namespaces de Linux

### Objetivo
Crear namespaces para observar el aislamiento de procesos y de red.

### Pasos

**Paso 2.1: Verificar el aislamiento del namespace de PID**
```bash
# Run bash in a new PID namespace
sudo unshare --mount --pid --fork --mount-proc bash -c '
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

**Paso 2.2: Aislamiento del namespace de red**
```bash
LINUX_LAB_NETNS="k8s-docs-netns-${UID}-$$"
(
  # Install cleanup only after creating this namespace successfully.
  sudo ip netns add "$LINUX_LAB_NETNS" || exit 1
  trap 'sudo ip netns delete "$LINUX_LAB_NETNS"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  sudo ip netns exec "$LINUX_LAB_NETNS" ip addr
)
```

<details>
<summary>¿Necesitas una pista?</summary>

- Las interfaces de red del host no son visibles dentro del namespace de red
- Solo existe la interfaz `lo` (loopback), y está DOWN de forma predeterminada
- Este es el principio en el que se basa el aislamiento de red de los contenedores
</details>

### Verificación
```bash
if LINUX_LAB_NS_LIST=$(sudo ip netns list); then
  if printf '%s\n' "$LINUX_LAB_NS_LIST" | awk '{print $1}' | grep -Fxq -- "$LINUX_LAB_NETNS"; then
    printf 'Named handle still exists: %s\n' "$LINUX_LAB_NETNS"
  else
    printf 'Named handle is not listed: %s\n' "$LINUX_LAB_NETNS"
  fi
else
  printf 'Could not verify namespace handles\n' >&2
fi
```

---

Eliminar el identificador del namespace de red no termina los procesos ni destruye un namespace que un proceso o descriptor de archivo aún mantiene. Este ejemplo espera a que finalice el comando `ip addr` antes de limpiar.

## Ejercicio 3: Límites de recursos de cgroup

### Objetivo
Usar cgroups para limitar el uso de memoria de los procesos.

### Pasos

**Paso 3.1: Comprobar la información de cgroup**
```bash
# cgroup2fs identifies a cgroup v2 mount.
stat -fc '%T' /sys/fs/cgroup
cat /proc/self/cgroup
if [ -r /sys/fs/cgroup/cgroup.controllers ]; then
  cat /sys/fs/cgroup/cgroup.controllers
else
  printf 'Controllers are not readable here; inspect the mount and permissions\n'
fi
```

**Paso 3.2: Comprobar el uso de memoria**
```bash
# System memory information
free -h

# Memory usage of specific processes
ps aux --sort=-%mem | head -10
```

**Paso 3.3: Aplicar un límite a un servicio transitorio**

En una VM con systemd y el controlador de memoria disponible en cgroup v2, esto crea un servicio con nombre automático y un límite máximo de memoria de 128 MiB, sin permitir swap. El proceso toca 16 MiB sin provocar deliberadamente un OOM; después, `--wait --collect` espera a que termine y descarga la unidad transitoria. Los límites de los cgroups antecesores pueden ser más restrictivos.

```bash
sudo systemd-run --wait --collect --pipe \
  --property=MemoryMax=128M --property=MemorySwapMax=0 \
  python3 -c '
from pathlib import Path
entry = next(line for line in Path("/proc/self/cgroup").read_text().splitlines()
             if line.startswith("0::"))
group = Path("/sys/fs/cgroup") / entry.split(":", 2)[2].lstrip("/")
print("Configured memory.max:", (group / "memory.max").read_text().strip())
data = bytearray(16 * 1024 * 1024)
for offset in range(0, len(data), 4096):
    data[offset] = 1
print("Touched allocation bytes:", len(data))
'
```

El valor configurado de `memory.max` debería ser 134217728 bytes para 128 M; la asignación es de 16777216 bytes. Son expectativas de configuración y cálculo, no resultados medidos en esta auditoría. El siguiente manifiesto solo se imprime; no crea un Pod de Kubernetes.

**Paso 3.4: Relación con los límites de recursos de Kubernetes**
```bash
# Linux container memory-limit example; this block only prints YAML
# Let's look at a Pod manifest example
cat << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: memory-demo
spec:
  containers:
  - name: memory-demo
    image: nginx:1.30.6
    resources:
      requests:
        memory: "64Mi"
      limits:
        memory: "128Mi"
EOF
```

<details>
<summary>¿Necesitas una pista?</summary>

- En contenedores Linux, el entorno de ejecución/kubelet configura los límites de memoria de cgroup.
- La presión de memoria puede provocar recuperación de memoria, fallos de asignación o terminación por OOM, según la asignación y la política de OOM del grupo. Un contenedor terminado por OOM puede informar `OOMKilled`; no todos los fallos de asignación producen ese estado.
- `kubectl describe pod` muestra los límites solicitados y el estado de terminación registrado del contenedor, pero no demuestra todos los eventos de memoria del kernel.
</details>

---

## Ejercicio 4: Gestión de permisos de archivos

### Objetivo
Practicar la gestión de permisos y propiedad de archivos.

### Pasos

**Paso 4.1: Crear un archivo y comprobar los permisos**
```bash
LINUX_LAB_DIR=$(mktemp -d /tmp/k8s-docs-linux-basics.XXXXXX)
: "${LINUX_LAB_DIR:?mktemp failed}"
printf 'Hello Linux\n' > "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -ld "$LINUX_LAB_DIR"
ls -l "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

**Paso 4.2: Cambiar los permisos**
```bash
# Add execute permission
chmod +x "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -la "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"

# Set with numeric mode (read/write - read - none)
chmod 640 "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -la "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"

# Set the same permissions as K8s Secret volume defaults
chmod 0644 "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

Añadir el bit de ejecución no convierte texto arbitrario en un programa válido. El modo 0644 incluye permiso de lectura para el grupo y otros usuarios cuando está permitido atravesar el directorio; en este laboratorio, el directorio privado creado con mktemp restringe el acceso. Los volúmenes Secret de Kubernetes usan 0644 de forma predeterminada, pero los permisos reales del secreto deben corresponder al usuario/grupo que lo consume y al acceso necesario.

**Paso 4.3: Cambiar la propiedad**
```bash
id
# Demonstrate an owner change only on the private lab file, then restore it.
sudo chown "root:$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
stat -c '%a %U %G' "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
sudo chown "$(id -u):$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

### Verificación
```bash
# Expect mode644 and the restored user/group
stat -c "%a %U %G" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

---

## Limpieza
```bash
# Delete only the file created by this lab; keep an unexpected nonempty directory.
if [[ -n ${LINUX_LAB_DIR:-} ]]; then
  rm -f -- "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
  if rmdir -- "$LINUX_LAB_DIR"; then
    unset LINUX_LAB_DIR
  fi
fi

# Only an unfinished job created in this Bash session may be terminated.
if [[ -n ${LINUX_LAB_SLEEP_PID:-} ]]; then
  if jobs -pr | grep -Fxq -- "$LINUX_LAB_SLEEP_PID"; then
    kill -TERM "$LINUX_LAB_SLEEP_PID"
  fi
  wait "$LINUX_LAB_SLEEP_PID" 2>/dev/null || true
  unset LINUX_LAB_SLEEP_PID
fi
```

## Solución de problemas

<details>
<summary>No se encuentra el comando unshare</summary>

Instala el paquete `util-linux`:
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo dnf install util-linux       # Fedora/RHEL
```
</details>

<details>
<summary>El comando ip netns no funciona</summary>

Se necesita el paquete `iproute2`:
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo dnf install iproute          # Fedora/RHEL
```
</details>


## Referencias y alcance de la validación

* [systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html)
* [Control de recursos de memoria de systemd](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
* [Controlador de memoria de cgroup v2 del kernel](https://docs.kernel.org/admin-guide/cgroup-v2.html)
* [unshare](https://man7.org/linux/man-pages/man1/unshare.1.html)
* [ip netns](https://man7.org/linux/man-pages/man8/ip-netns.8.html)
* [Manual de GNU mktemp](https://man7.org/linux/man-pages/man1/mktemp.1.html)

Para la auditoría solo se ejecutaron comprobaciones de procesos/archivos aisladas y sin privilegios, además de comprobaciones de sintaxis. No se ejecutaron operaciones de creación de namespaces, cambio de propiedad ni cgroup/systemd.

## Siguientes pasos
- [Cuestionario de conceptos básicos de Linux](../../quizzes/basics/01-linux-basics-quiz.md)
- [Laboratorio de habilidades avanzadas de Linux](./02-linux-advanced-lab.md)
