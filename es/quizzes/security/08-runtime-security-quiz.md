# Cuestionario de seguridad en tiempo de ejecución

> **Última actualización**: September 13, 2026

Este cuestionario evalúa tu comprensión de Falco, Seccomp, AppArmor, seguridad basada en eBPF y seguridad en tiempo de ejecución de EKS.

## Preguntas del cuestionario

### 1. ¿Qué tecnología utiliza Falco para detectar amenazas en tiempo de ejecución?

- A. Análisis de paquetes de red
- B. Monitorización de llamadas al sistema (syscalls)
- C. Análisis de logs
- D. Escaneo de memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Monitorización de llamadas al sistema (syscalls)**

**Explicación:**
Falco habitualmente evalúa eventos de syscall de Linux frente a reglas; los plugins pueden proporcionar otras fuentes de eventos. En 0.44.1, los campos de contenedor proceden del plugin de contenedor. Verifica los requisitos de kernel/BTF de modern_ebpf y la recopilación de metadatos.

</details>

### 2. ¿Cuál es la función principal de Seccomp?

- A. Filtrado de tráfico de red
- B. Restringir las llamadas al sistema que puede realizar un proceso
- C. Cifrado del sistema de archivos
- D. Autenticación de usuarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Restringir las llamadas al sistema que puede realizar un proceso**

**Explicación:**
Seccomp filtra las llamadas al sistema. El rechazo puede devolver ERRNO, terminar o notificar según la acción del perfil; no siempre finaliza el proceso.

</details>

### 3. ¿Cuál es el perfil de Seccomp predeterminado recomendado en Kubernetes 1.27+?

- A. Unconfined
- B. RuntimeDefault
- C. Localhost
- D. Docker/default

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. RuntimeDefault**

**Explicación:**
RuntimeDefault es el perfil proporcionado por el runtime de contenedores. Configura seccompProfile explícitamente o verifica kubelet seccompDefault. Kubernetes 1.27+ por sí solo no lo aplica automáticamente a cada Pod.

</details>

### 4. ¿Cuál es la función del campo priority en las reglas de Falco?

- A. Determinar el orden de ejecución de las reglas
- B. Especificar el nivel de gravedad de las alertas
- C. Establecer la cuota de recursos
- D. Establecer el período de retención de logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Especificar el nivel de gravedad de las alertas**

**Explicación:**
priority es la gravedad del evento, no el orden de evaluación. Los niveles estándar son EMERGENCY, ALERT, CRITICAL, ERROR, WARNING, NOTICE, INFORMATIONAL y DEBUG. Una regla completa también necesita campos como desc, condition y output.

</details>

### 5. ¿Qué sucede en el modo complain de AppArmor?

- A. Bloquea todo acceso
- B. Registra infracciones ordinarias; una denegación explícita aún puede bloquear
- C. Desactiva el perfil
- D. Envía solo alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Registra infracciones ordinarias; una denegación explícita aún puede bloquear**

**Explicación:**
El modo complain normalmente registra las infracciones de políticas y las permite, pero las reglas deny explícitas aún pueden bloquear el acceso. No es un permiso incondicional para todo acceso. Verifica la compatibilidad del kernel y el perfil cargado.

</details>

### 6. ¿Cuál NO es una amenaza detectada por Amazon GuardDuty EKS Runtime Monitoring?

- A. Minería de criptomonedas
- B. Escalada de privilegios
- C. Problemas de calidad del código
- D. Intentos de escape de contenedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Problemas de calidad del código**

**Explicación:**
GuardDuty Runtime Monitoring detecta amenazas de seguridad, no defectos de calidad del código. La compatibilidad actual de EKS abarca EC2 y Auto Mode, pero excluye EKS Hybrid Nodes y EKS Fargate. Comprueba los requisitos de SO/kernel/agente y el estado de cobertura.

</details>

### 7. ¿Cuál es la función principal de Cilium Tetragon?

- A. Escaneo de imágenes de contenedores
- B. Observabilidad de seguridad basada en eBPF
- C. Gestión de políticas de red
- D. Gestión de secretos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Observabilidad de seguridad basada en eBPF**

**Explicación:**
Tetragon proporciona eventos de procesos, hooks de archivos/red y acciones compatibles. No requiere la instalación de Cilium CNI. Verifica la compatibilidad de hooks, el alcance del selector y los falsos positivos; prueba el comportamiento Post/monitor antes de la aplicación.

</details>

### 8. ¿Qué condición detecta la ejecución de un shell dentro de un contenedor en Falco?

- A. container and shell_procs
- B. spawned_process and container and shell_procs
- C. exec and shell
- D. process.name = bash

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. spawned_process and container and shell_procs**

**Explicación:**
Esta expresión depende de las macros cargadas spawned_process, container y shell_procs del conjunto de reglas. Un shell puede ser legítimo y no demuestra que haya habido una vulneración. La guía define macros independientes y nombres de reglas únicos.

</details>

### 9. ¿Cómo se configura un sistema de archivos raíz de solo lectura para un Pod?

- A. readOnlyRootFilesystem: true
- B. rootfs: readonly
- C. filesystem.readonly: true
- D. immutableRoot: true

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. readOnlyRootFilesystem: true**

**Explicación:**
readOnlyRootFilesystem pertenece al securityContext del contenedor. Los volúmenes escribibles o /tmp pueden proporcionarse por separado. No impide el uso malicioso de volúmenes escribibles, el acceso a la red ni a la memoria.

</details>

### 10. ¿Qué significa la estrategia "Defense in Depth" en la seguridad en tiempo de ejecución?

- A. Depender de una única capa de seguridad
- B. Aplicar múltiples capas de seguridad superpuestas
- C. Centrarse únicamente en la defensa
- D. Proteger solo los límites externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Aplicar múltiples capas de seguridad superpuestas**

**Explicación:**
Combina controles mientras verificas el alcance y los modos de fallo de cada capa. Las comprobaciones de imágenes/firmas, admisión/permisos, seccomp/AppArmor, detección en tiempo de ejecución, redes y recuperación se complementan entre sí; instalar más herramientas por sí solo no es una garantía.

</details>

<span id="_11-what-command-shows-traffic-blocked-by-policies-in-hubble"></span>

### 11. ¿Qué comando de Hubble filtra los flujos descartados?

- A. hubble observe --blocked
- B. hubble observe --verdict DROPPED
- C. hubble observe --denied
- D. hubble observe --policy-violation

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. hubble observe --verdict DROPPED**

**Explicación:**
--verdict DROPPED selecciona los flujos descartados. No todos los descartes son una denegación de NetworkPolicy; inspecciona los motivos de descarte y los veredictos de las políticas. La opción por sí sola no establece la causa específica de la política que implica la pregunta original.

</details>

### 12. ¿Cuál NO es una práctica recomendada de seguridad en tiempo de ejecución?

- A. Usar RuntimeDefault después de comprobar la compatibilidad de la carga de trabajo
- B. Verificar la recopilación de Falco en nodos compatibles
- C. Ejecutar contenedores como root
- D. Usar un sistema de archivos raíz de solo lectura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ejecutar contenedores como root**

**Explicación:**
Reduce los privilegios root innecesarios. RuntimeDefault y readOnlyRootFilesystem aún requieren compatibilidad con la carga de trabajo/el nodo. Los DaemonSets de Falco no pueden ejecutarse en todos los tipos de nodo, como Fargate. La habilitación de características y una cobertura de GuardDuty en buen estado son comprobaciones independientes.

</details>
