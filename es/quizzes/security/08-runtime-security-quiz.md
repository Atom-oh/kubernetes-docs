# Cuestionario de seguridad en Runtime

Este cuestionario evalúa tu comprensión de Falco, Seccomp, AppArmor, la seguridad basada en eBPF y la seguridad en Runtime de EKS.

## Preguntas del cuestionario

### 1. ¿Qué tecnología utiliza Falco para detectar amenazas en Runtime?

A. Análisis de paquetes de red
B. Monitoreo de llamadas al sistema (syscall)
C. Análisis de logs
D. Escaneo de memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Monitoreo de llamadas al sistema (syscall)**

**Explicación:**
Falco utiliza eBPF o módulos del kernel para monitorear llamadas al sistema a nivel del kernel. Detecta actividades como la ejecución de procesos, el acceso a archivos y las conexiones de red en tiempo real.

</details>

### 2. ¿Cuál es la función principal de Seccomp?

A. Filtrado de tráfico de red
B. Restringir las llamadas al sistema que puede realizar un proceso
C. Cifrado del sistema de archivos
D. Autenticación de usuarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Restringir las llamadas al sistema que puede realizar un proceso**

**Explicación:**
Seccomp (Secure Computing Mode) restringe las llamadas al sistema que puede realizar un proceso mediante un enfoque de lista permitida. El proceso finaliza si intenta ejecutar una syscall no autorizada.

</details>

### 3. ¿Cuál es el perfil de Seccomp predeterminado recomendado en Kubernetes 1.27+?

A. Unconfined
B. RuntimeDefault
C. Localhost
D. Docker/default

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. RuntimeDefault**

**Explicación:**
RuntimeDefault es el perfil de Seccomp predeterminado proporcionado por el runtime de contenedores (containerd, CRI-O):
```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault
```

Proporciona un nivel de seguridad adecuado para la mayoría de las cargas de trabajo.

</details>

### 4. ¿Cuál es el rol del campo priority en las reglas de Falco?

A. Determinar el orden de ejecución de las reglas
B. Especificar el nivel de severidad de las alertas
C. Establecer la cuota de recursos
D. Establecer el período de retención de logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Especificar el nivel de severidad de las alertas**

**Explicación:**
La priority en las reglas de Falco especifica la severidad de los eventos detectados:
- EMERGENCY, ALERT, CRITICAL, ERROR
- WARNING, NOTICE, INFORMATIONAL, DEBUG

```yaml
- rule: Shell in Container
  priority: WARNING
```

</details>

### 5. ¿Qué ocurre en el modo complain de AppArmor?

A. Bloquea todo acceso
B. Solo registra las violaciones de políticas
C. Deshabilita el perfil
D. Envía solo alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Solo registra las violaciones de políticas**

**Explicación:**
Modos de AppArmor:
- **enforce**: Bloquea y registra ante una violación de política
- **complain**: Solo registra ante una violación de política (para depuración)
- **unconfined**: No se aplica ningún perfil

El modo complain es útil para probar perfiles nuevos.

</details>

### 6. ¿Cuál NO es una amenaza detectada por Amazon GuardDuty EKS Runtime Monitoring?

A. Minería de criptomonedas
B. Escalamiento de privilegios
C. Problemas de calidad del código
D. Intentos de escape de contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Problemas de calidad del código**

**Explicación:**
Tipos de detección de GuardDuty EKS Runtime Monitoring:
- PrivilegeEscalation
- Execution (código malicioso)
- CryptoCurrency (minería)
- CredentialAccess
- DefenseEvasion

La calidad del código es un problema de calidad de desarrollo, no una amenaza de seguridad.

</details>

### 7. ¿Cuál es la función principal de Cilium Tetragon?

A. Escaneo de imágenes de contenedor
B. Observabilidad de seguridad basada en eBPF
C. Gestión de Network Policy
D. Gestión de Secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Observabilidad de seguridad basada en eBPF**

**Explicación:**
Tetragon es la herramienta de observabilidad de seguridad basada en eBPF de Cilium:
- Monitoreo de ejecución de procesos
- Seguimiento de actividad de red
- Monitoreo de acceso a archivos
- Respuesta en tiempo real basada en políticas (por ejemplo, finalización de procesos)

</details>

### 8. ¿Qué condición detecta la ejecución de shell dentro de un contenedor en Falco?

A. container and shell_procs
B. spawned_process and container and shell_procs
C. exec and shell
D. process.name = bash

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. spawned_process and container and shell_procs**

**Explicación:**
Ejemplo de regla de Falco:
```yaml
- rule: Shell in Container
  condition: >
    spawned_process and
    container and
    shell_procs
  output: "Shell spawned in container"
  priority: WARNING
```

`spawned_process` significa creación de un proceso nuevo, `container` significa entorno de contenedor, y `shell_procs` significa procesos de shell (bash, sh, etc.).

</details>

### 9. ¿Cómo configuras un sistema de archivos raíz de solo lectura para un Pod?

A. readOnlyRootFilesystem: true
B. rootfs: readonly
C. filesystem.readonly: true
D. immutableRoot: true

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. readOnlyRootFilesystem: true**

**Explicación:**
```yaml
securityContext:
  readOnlyRootFilesystem: true
```

Esta configuración hace que el sistema de archivos raíz del contenedor sea de solo lectura, lo que impide que el código malicioso modifique archivos. Monta volúmenes emptyDir para las rutas que necesitan acceso de escritura.

</details>

### 10. ¿Qué significa la estrategia "Defense in Depth" en seguridad en Runtime?

A. Depender de una sola capa de seguridad
B. Aplicar múltiples capas de seguridad superpuestas
C. Centrarse solo en la defensa
D. Proteger solo los límites externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Aplicar múltiples capas de seguridad superpuestas**

**Explicación:**
Defense in Depth usa múltiples capas de seguridad:
1. Tiempo de construcción: escaneo de imágenes, análisis de vulnerabilidades
2. Tiempo de despliegue: Admission Control, PSS/PSA
3. Runtime: Falco, Seccomp, AppArmor

Si se vulnera una capa, las demás capas proporcionan protección.

</details>

### 11. ¿Qué comando muestra el tráfico bloqueado por políticas en Hubble?

A. hubble observe --blocked
B. hubble observe --verdict DROPPED
C. hubble observe --denied
D. hubble observe --policy-violation

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. hubble observe --verdict DROPPED**

**Explicación:**
```bash
hubble observe --verdict DROPPED
```

`--verdict DROPPED` filtra el tráfico denegado por las políticas de red. Puedes monitorear y analizar violaciones de políticas en tiempo real.

</details>

### 12. ¿Cuál NO es una buena práctica de seguridad en Runtime?

A. Aplicar RuntimeDefault Seccomp a todas las cargas de trabajo
B. Desplegar Falco como DaemonSet en todos los nodos
C. Ejecutar contenedores como root
D. Usar un sistema de archivos raíz de solo lectura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ejecutar contenedores como root**

**Explicación:**
Buenas prácticas de seguridad en Runtime:
- Aplicar RuntimeDefault Seccomp
- Desplegar Falco
- Sistema de archivos raíz de solo lectura
- **Ejecutar como usuario no root** (runAsNonRoot: true)
- Eliminar capacidades innecesarias
- Habilitar el monitoreo de Runtime de GuardDuty

Ejecutar como root es peligroso porque un escape del contenedor otorga privilegios elevados en el host.

</details>
