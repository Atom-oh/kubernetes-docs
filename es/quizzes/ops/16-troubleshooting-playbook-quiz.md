# Cuestionario del manual de solución de problemas

> **Documento relacionado**: [Manual de solución de problemas de Kubernetes/EKS](../../ops/16-troubleshooting-playbook.md)

## Preguntas de opción múltiple

### 1. El evento FailedScheduling informa de un fallo de CPU, uno de memoria, seis de afinidad y ocho de taints. ¿Qué interpretación es correcta?

- A) Los recuentos de motivos pueden superponerse; compara el estado de cada nodo
- B) Exactamente el mismo nodo debe tener insuficiencia de CPU y de memoria
- C) Los quince nodos carecen de CPU
- D) El scheduler no evaluó ningún nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Los recuentos de motivos pueden superponerse; compara el estado de cada nodo**

El scheduler puede agrupar varios motivos por nodo. Los recuentos por sí solos no dividen los nodos en conjuntos mutuamente excluyentes ni identifican un nodo concreto. Comprueba nodeName y PodScheduled para distinguir un problema de scheduling de esperas durante la inicialización de la imagen o de CNI.

</details>

### 2. Falla con 401 Unauthorized la descarga de una imagen de ECR en un worker EC2 estándar. ¿Qué se debe comprobar primero?

- A) Los límites de frecuencia de Docker Hub
- B) El mecanismo de credenciales de imagen que usa kubelet y los permisos de ECR del rol del nodo
- C) La ruta de liveness del contenedor
- D) El nombre del bucket de S3 de la aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El mecanismo de credenciales de imagen que usa kubelet y los permisos de ECR del rol del nodo**

No confundas IRSA de la aplicación con la identidad usada para descargar imágenes. Fargate usa el rol de ejecución del Pod. crictl pull no reutiliza automáticamente los proveedores de credenciales del kubelet ni imagePullSecrets, así que no constituye una prueba de autenticación equivalente.

</details>

### 3. Un contenedor termina con el motivo OOMKilled y el código de salida 137. ¿Cuál es el siguiente paso adecuado?

- A) Una ejecución prolongada demuestra que hay una fuga de memoria
- B) Revisar los límites del contenedor, la presión del nodo, la serie temporal de memoria y los eventos del kernel
- C) Duplicar siempre el límite de inmediato
- D) Ignorarlo porque es una salida SIGTERM normal

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Revisar los límites del contenedor, la presión del nodo, la serie temporal de memoria y los eventos del kernel**

El código 137 suele representar SIGKILL (128+9); OOMKilled aporta indicios de falta de memoria (OOM). Esto por sí solo no demuestra que haya una fuga ni que el fallo se deba exclusivamente al límite del contenedor. Un código 137 con otro motivo requiere una investigación aparte. Según la aplicación, la gestión de SIGTERM también puede producir códigos de salida distintos de 143.

</details>

### 4. Aparece una IP en la columna ENDPOINTS de un EndpointSlice. ¿Qué se puede concluir?

- A) Todos los Pods están Ready
- B) Las solicitudes al Service deben funcionar
- C) La dirección existe; revisa por separado ready, serving y terminating
- D) Todas las NetworkPolicies permiten el tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La dirección existe; revisa por separado ready, serving y terminating**

Un Pod que no está listo puede aparecer con ready=false. El recuento READY de los contenedores también difiere de la condición Ready del Pod. Si faltan direcciones, comprueba los selectores, los espacios de nombres y la gestión de los endpoints; los Services sin selector pueden requerir EndpointSlices administrados manualmente.

</details>

### 5. ¿Qué taint automático corresponde a DiskPressure=True?

- A) node.kubernetes.io/unreachable
- B) node.kubernetes.io/not-ready
- C) node.kubernetes.io/disk-pressure
- D) node.kubernetes.io/memory-pressure

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) node.kubernetes.io/disk-pressure**

Un nodo puede seguir Ready mientras la presión impide programar Pods nuevos. Revisa los inodos, además del espacio libre y la distribución de los sistemas de archivos. Ready=Unknown se relaciona con unreachable; Ready=False, con not-ready.

</details>

### 6. Un PVC usa una StorageClass con WaitForFirstConsumer y todavía no existe ningún Pod consumidor. ¿Cuál es la interpretación correcta?

- A) Tiene que ser un error de IAM de CSI
- B) Una StorageClass llamada gp3 tiene que estar mal configurada
- C) Puede ser normal: la vinculación o el aprovisionamiento esperan las restricciones de scheduling del consumidor
- D) Hay que eliminar el PV de inmediato

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Puede ser normal: la vinculación o el aprovisionamiento esperan las restricciones de scheduling del consumidor**

El comportamiento depende de volumeBindingMode, no del nombre de la StorageClass. El valor predeterminado de la API es Immediate, así que comprueba el valor real. Si el consumidor también está Pending, revisa FailedScheduling y las restricciones de topología. Eliminar el PVC no es la acción de diagnóstico predeterminada.

</details>

### 7. Se añadió una anotación IRSA a una cuenta de servicio después de crear el Pod; el Pod existente no tiene campos inyectados. ¿Qué se debe hacer?

- A) Volver a crear el clúster
- B) Comprobar serviceAccountName y la configuración del webhook; después, volver a crear los Pods teniendo en cuenta el impacto
- C) Conceder AdministratorAccess al rol del nodo
- D) Esperar a que cambie el entorno existente, independientemente de la cuenta de servicio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comprobar serviceAccountName y la configuración del webhook; después, volver a crear los Pods teniendo en cuenta el impacto**

La inyección ocurre al crear el Pod; los Pods existentes no se modifican automáticamente. Después de recrearlos, verifica la inyección y la identidad que realmente realiza las llamadas. Otro proveedor de credenciales del SDK puede tener prioridad, y no se puede recurrir al rol del nodo si el acceso a IMDS está bloqueado.

</details>

### 8. Karpenter informa de que todos los tipos de instancia disponibles superan los límites de nodepool. ¿Qué significa?

- A) Solo puede ocurrir cuando el uso actual alcanza exactamente el límite
- B) Cualquier instancia candidata superaría la capacidad restante de NodePool
- C) No existe ningún tipo de instancia EC2 en la Región
- D) Al Pod le falta una toleration

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cualquier instancia candidata superaría la capacidad restante de NodePool**

Con un uso actual de CPU de 7, un límite de 8 y una instancia candidata más pequeña de 2 CPU, el error puede aparecer antes de alcanzar el límite. Revisa también los otros límites de recursos, la sobrecarga de DaemonSet y los requisitos. Un evento Nominated no demuestra que el nodo o el Pod estén listos.

</details>

### 9. En modo de IP secundaria, WARM_IP_TARGET=3, MINIMUM_IP_TARGET=6 y hay una IP en uso. ¿Cuál es la interpretación correcta?

- A) Debe haber cuatro IP en total
- B) Para satisfacer ambos objetivos pueden hacer falta seis IP en total y cinco libres
- C) MINIMUM_IP_TARGET significa que debe haber al menos seis IP libres
- D) Demasiados Pods demuestran que se agotaron las subredes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para satisfacer ambos objetivos pueden hacer falta seis IP en total y cinco libres**

Los objetivos warm indican cuántas direcciones libres se deben mantener; el mínimo establece el piso total entre las direcciones en uso y las libres. La reconciliación de IPAM, los límites de ENI y la granularidad de asignación de prefijos afectan a los recuentos reales. Los objetivos positivos de IP tienen prioridad sobre WARM_ENI_TARGET. El modo de prefijos requiere instancias compatibles y bloques /28 contiguos; diagnostica max-pods por separado del agotamiento real de IP.

</details>
