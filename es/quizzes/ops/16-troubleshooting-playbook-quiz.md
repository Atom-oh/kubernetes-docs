# Cuestionario del manual de solución de problemas

> **Documento relacionado**: [Manual de solución de problemas de Kubernetes/EKS](../../ops/16-troubleshooting-playbook.md)

## Preguntas de opción múltiple

### 1. Un Pod `Pending` muestra el siguiente evento `FailedScheduling`. ¿Qué interpretación del mensaje es correcta?

```
0/15 nodes are available: 1 Insufficient cpu, 1 Insufficient memory,
6 node(s) didn't match Pod's node affinity/selector, 8 node(s) had untolerated taint(s).
```

- A) Los 15 nodos no tienen suficiente CPU y memoria
- B) Solo un nodo es elegible para este Pod, y a ese nodo le faltan CPU y memoria
- C) El scheduler está dañado y no pudo evaluar ningún nodo
- D) El scheduling falló porque 8 nodos tienen demasiados Pods (`Too many pods`)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo un nodo es elegible para este Pod, y a ese nodo le faltan CPU y memoria**

**Explicación:**
El scheduler agrega el motivo de rechazo por nodo. 8 nodos fueron rechazados por taints sin una toleration correspondiente, 6 por una discrepancia de etiqueta de nodeSelector/affinity, y al único nodo restante le faltaban CPU y memoria. En otras palabras, exactamente un nodo satisface las restricciones de scheduling y está lleno; por tanto, debes ampliar la toleration/las etiquetas o añadir nodos que las satisfagan (con Karpenter, la clave de etiqueta debe aparecer en los requisitos de NodePool).

</details>

### 2. Un Pod que usa una imagen privada de ECR está en `ImagePullBackOff`, y los eventos de `describe` muestran `Failed to pull image "...dkr.ecr...": ... 401 Unauthorized`. ¿Qué deberías sospechar primero?

- A) Un error tipográfico en un tag de imagen
- B) Al rol IAM del nodo le falta permiso para extraer de ECR (`AmazonEC2ContainerRegistryPullOnly` o `ReadOnly`)
- C) El límite de tasa de Docker Hub (`toomanyrequests`)
- D) Una subred privada sin endpoints NAT/VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Al rol IAM del nodo le falta permiso para extraer de ECR (`AmazonEC2ContainerRegistryPullOnly` o `ReadOnly`)**

**Explicación:**
Lo que sigue a `Failed to pull image` es el diagnóstico. `401 Unauthorized` / `no basic auth credentials` significa que la autenticación del registry falló; para ECR, el kubelet se autentica con el rol IAM del nodo, así que comprueba el permiso de extracción de ECR de ese rol. Un error tipográfico en un tag aparece como `not found` / `manifest unknown`, un problema de ruta de red como `dial tcp ... i/o timeout`, y el límite de Docker Hub como `toomanyrequests`.

</details>

### 3. El `lastState.terminated` de un Pod en `CrashLoopBackOff` muestra `Reason: OOMKilled`, `Exit Code: 137`. ¿Qué afirmación es correcta?

- A) La app detectó un error por sí misma y salió con el código 1
- B) El kernel envió SIGKILL porque se superó el límite de memoria; aumenta el límite o corrige la fuga de memoria
- C) Recibió SIGTERM y se cerró correctamente, por lo que no se requiere ninguna acción
- D) La arquitectura de la imagen (arm64/amd64) no coincide con la del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El kernel envió SIGKILL porque se superó el límite de memoria; aumenta el límite o corrige la fuga de memoria**

**Explicación:**
El código de salida 137 es SIGKILL (128+9). Con Reason `OOMKilled`, el OOM killer del kernel terminó el contenedor por superar su límite de memoria; el mismo 137 con Reason `Error` es un SIGKILL por otro motivo, como un fallo de liveness en el que el contenedor no salió dentro de `terminationGracePeriodSeconds`. Una salida correcta por SIGTERM es 143, y una discrepancia de arquitectura aparece como 126 bajo un entrypoint de shell (`cannot execute binary file: Exec format error`) o como Reason `StartError` cuando la imagen ejecuta el binario directamente. Lee los logs justo antes del crash con `kubectl logs <pod> -c <container> --previous`.

</details>

### 4. Todos los Pods están `1/1 Running`, pero las solicitudes nunca llegan al Service. La columna ENDPOINTS de `kubectl get endpointslices -l kubernetes.io/service-name=<svc>` está vacía. ¿Cuál es la causa más probable?

- A) Los Pods de CoreDNS están caídos, por lo que falla la resolución de nombres
- B) El `selector` del Service no coincide con las etiquetas del Pod
- C) `targetPort` difiere del puerto en el que escucha el contenedor
- D) Una NetworkPolicy bloquea el ingreso

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El `selector` del Service no coincide con las etiquetas del Pod**

**Explicación:**
Un EndpointSlice enumera las IP de los **Pods Ready** coincidentes con el selector del Service. Si todos los Pods están Ready y el slice sigue vacío, el selector y las etiquetas del Pod difieren (en los charts de Helm, que `selectorLabels` y `podLabels` se separen es una causa común). Un `targetPort` incorrecto muestra IP más `connection refused`, un bloqueo de NetworkPolicy muestra IP más timeouts, y una interrupción de CoreDNS muestra fallos de `NXDOMAIN`/resolución. En Kubernetes 1.33+, `kubectl get endpoints` imprime una advertencia de deprecación, así que revisa EndpointSlices en su lugar.

</details>

### 5. Las condiciones de un nodo muestran `DiskPressure=True (KubeletHasDiskPressure)`. ¿Qué taint añade automáticamente el controlador de nodos (kube-controller-manager) al nodo?

- A) `node.kubernetes.io/unreachable`
- B) `node.kubernetes.io/not-ready`
- C) `node.kubernetes.io/disk-pressure`
- D) `node.kubernetes.io/memory-pressure`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `node.kubernetes.io/disk-pressure`**

**Explicación:**
Cada condición de nodo tiene un taint automático correspondiente: `DiskPressure` → `node.kubernetes.io/disk-pressure`, `MemoryPressure` → `node.kubernetes.io/memory-pressure`, `PIDPressure` → `node.kubernetes.io/pid-pressure`, `Ready=False` → `node.kubernetes.io/not-ready`, y `Ready=Unknown` (el kubelet dejó de publicar el estado, reason `NodeStatusUnknown`) → `node.kubernetes.io/unreachable`. Por eso un nodo puede estar `Ready` mientras los Pods nuevos lo evitan con `node(s) had untolerated taint(s)`. DiskPressure suele deberse a que la caché de imágenes y los logs de contenedores llenan el volumen raíz, y los Pods son `Evicted` con `The node was low on resource: ephemeral-storage`.

</details>

### 6. Un PVC está `Pending` y `describe pvc` solo muestra `WaitForFirstConsumer: waiting for first consumer to be created before binding`. Aún no se ha desplegado ningún Pod que use este PVC. ¿Cuál es la conclusión correcta?

- A) El nombre de StorageClass está mal escrito; compruébalo con `kubectl get sc`
- B) Al controlador CSI de EBS le falta permiso IAM
- C) Esto es normal: `volumeBindingMode: WaitForFirstConsumer` aplaza la creación del volumen hasta que se programe un Pod
- D) El PV está en otra AZ, lo que causa un `volume node affinity conflict`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Esto es normal: `volumeBindingMode: WaitForFirstConsumer` aplaza la creación del volumen hasta que se programe un Pod**

**Explicación:**
La StorageClass `gp2` que EKS crea de forma predeterminada usa el modo de binding `WaitForFirstConsumer`. Una StorageClass `gp3` que creas para el driver CSI de EBS solo lo hace si estableces explícitamente `volumeBindingMode: WaitForFirstConsumer`; el valor predeterminado de la API es `Immediate`; y la clase `gp3` del clúster de verificación sí lo hace, como muestra la salida de `kubectl get storageclass` en el manual. La espera es intencional: el volumen de EBS se crea en la AZ donde termina programándose el Pod, por lo que un PVC que permanece `Pending` mientras ningún Pod lo utiliza no es un problema. Un error tipográfico de StorageClass aparece como `storageclass.storage.k8s.io "<name>" not found`, un permiso IAM faltante como `ProvisioningFailed` + `UnauthorizedOperation`/`AccessDenied`, y una discrepancia de AZ como `volume node affinity conflict` en el evento `FailedScheduling` del Pod.

</details>

### 7. Las llamadas a la API de AWS desde un Pod son `AccessDenied`, y el principal denegado es el rol IAM del nodo en lugar del rol de la cuenta de servicio. `kubectl get sa` muestra la anotación `eks.amazonaws.com/role-arn`, pero el entorno del Pod no tiene `AWS_ROLE_ARN`/`AWS_WEB_IDENTITY_TOKEN_FILE`. ¿Cuál es la causa y solución?

- A) La política de permisos del rol IAM es insuficiente → añade acciones a la política
- B) La anotación se añadió **después** de crear el Pod, por lo que el webhook nunca inyectó credenciales → `kubectl rollout restart`
- C) No hay un proveedor OIDC → vuelve a crear el clúster
- D) El agente EKS Pod Identity está caído → reinicia el agente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La anotación se añadió después de crear el Pod, por lo que el webhook nunca inyectó credenciales → `kubectl rollout restart`**

**Explicación:**
IRSA funciona haciendo que pod-identity-webhook inyecte las variables de entorno `AWS_ROLE_ARN` y `AWS_WEB_IDENTITY_TOKEN_FILE` (además del volumen de token) **en el momento de creación del Pod**. Si no hay rastro de la inyección, el Pod se creó antes de que existiera la anotación o el nombre de SA es distinto, y el SDK recurre al rol del nodo porque no encuentra credenciales. Volver a crear los Pods lo corrige. Una política de permisos insuficiente (A) tiene otro aspecto: el entorno está bien, pero se deniega una API específica; y Pod Identity (D) se reconoce por la variable de entorno `AWS_CONTAINER_CREDENTIALS_FULL_URI`.

</details>

### 8. Un Pod está `Pending`, no aparece ningún NodeClaim nuevo, y un evento de Karpenter indica `all available instance types exceed limits for nodepool "graviton"`. ¿Cuál es la causa?

- A) La clave de etiqueta nodeSelector del Pod no está en los requisitos de NodePool
- B) No hay una toleration para el taint de NodePool
- C) Ya se alcanzaron los `spec.limits` (cpu/memory) de NodePool
- D) EC2 no tiene capacidad en esa AZ (`InsufficientInstanceCapacity`)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ya se alcanzaron los `spec.limits` (cpu/memory) de NodePool**

**Explicación:**
Karpenter recorre cada NodePool para un Pod y registra como evento por qué se rechazó cada uno. `exceed limits` significa que cualquier instancia que pudiera añadir llevaría el NodePool más allá de sus `spec.limits`; `kubectl get nodepool -o custom-columns=...spec.limits.cpu,...status.resources.cpu` muestra que el límite y el uso son iguales. Una clave de etiqueta faltante aparece como `label "<key>" does not have known values`, una toleration faltante como `did not tolerate <key>=<value>:NoSchedule`, y la falta de capacidad de EC2 como `InsufficientInstanceCapacity` en los logs del controlador de Karpenter.

</details>

### 9. Los Pods de un nodo de EKS se quedan bloqueados en `ContainerCreating` con el evento `FailedCreatePodSandBox ... plugin type="aws-cni" ... failed to assign an IP address to container`. El `AvailableIpAddressCount` de la subred está en un solo dígito, y `aws-node` se ejecuta con los valores predeterminados de VPC CNI (`WARM_ENI_TARGET=1`, `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` sin establecer). ¿Qué afirmación es correcta?

- A) El valor predeterminado `WARM_ENI_TARGET=1` mantiene conectada a cada nodo una ENI de reserva completa con sus IP, por lo que la subred se agota mucho antes de lo que sugiere el número de Pods; establecer `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` reduce ese pool caliente porque tienen prioridad sobre la regla de ENI caliente
- B) Establecer `WARM_ENI_TARGET=0` es suficiente, porque `WARM_IP_TARGET` se ignora mientras `WARM_ENI_TARGET` esté establecido
- C) `ENABLE_PREFIX_DELEGATION=true` añade IP al conectar más ENI, por lo que funciona en cualquier familia de instancias
- D) `FailedCreatePodSandBox` significa que el scheduler no pudo encontrar un nodo, por lo que es el mismo fallo que `Too many pods`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El valor predeterminado `WARM_ENI_TARGET=1` mantiene conectada a cada nodo una ENI de reserva completa con sus IP, por lo que la subred se agota mucho antes de lo que sugiere el número de Pods; establecer `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` reduce ese pool caliente porque tienen prioridad sobre la regla de ENI caliente**

**Explicación:**
Con el valor predeterminado `WARM_ENI_TARGET=1` por sí solo, ipamd mantiene una ENI de reserva completa conectada a cada nodo (15 IP por ENI en un m5.xlarge), por lo que en una subred pequeña las IP preasignadas se agotan mucho antes que los Pods. Una vez que se establecen `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`, anulan la regla de ENI caliente: el clúster de verificación del manual usa `WARM_IP_TARGET=3`, `MINIMUM_IP_TARGET=6`, por lo que un nodo mantiene solo 3 IP de reserva además de las que usan sus Pods y nunca menos de 6 IP asignadas en total (`MINIMUM_IP_TARGET` limita el total, en uso más reserva, no el número de reserva). B invierte la prioridad. La delegación de prefijo (C) asigna prefijos /28 a los slots de ENI existentes en lugar de añadir ENI, y requiere instancias basadas en Nitro además de recalcular el máximo de Pods. D confunde dos síntomas: `FailedCreatePodSandBox` ocurre después del scheduling, cuando el kubelet solicita al CNI una IP en un nodo al que no le queda ninguna; `Too many pods` ocurre cuando el scheduler rechaza el nodo porque ya se alcanzó `allocatable.pods`; ambos comparten la causa raíz (no hay IP para entregar), pero ocurren en etapas distintas.

</details>
