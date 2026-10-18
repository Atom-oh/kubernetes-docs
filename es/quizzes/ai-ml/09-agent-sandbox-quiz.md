# Cuestionario sobre Agent Sandbox en EKS

Este cuestionario comprueba la API de Agent Sandbox v1.0.6 (`v1beta1`) y el comportamiento de sus valores predeterminados en Amazon EKS. Capítulo relacionado: [Agent Sandbox en EKS](../../ai-ml/09-agent-sandbox.md).

## Preguntas de opción múltiple

### 1. ¿Qué proporciona Agent Sandbox por sí mismo para aislar código que no es de confianza?

- A. Un hipervisor microVM integrado para cada Sandbox
- B. Orquestación de Pods; el aislamiento lo proporciona `RuntimeClass` del Pod (por ejemplo, gVisor o Kata Containers)
- C. Un perfil seccomp que hace que `runc` sea seguro para cualquier código no confiable
- D. Ubicación automática en instancias EC2 dedicadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Orquestación de Pods; el aislamiento lo proporciona `RuntimeClass` del Pod (por ejemplo, gVisor o Kata Containers)**

**Explicación:**
El proyecto se describe como un orquestador de sandboxes. Su modelo de amenazas mitiga la salida del contenedor recomendando un entorno de ejecución seguro seleccionado mediante `runtimeClassName`, idealmente configurado en un `SandboxTemplate` para que los usuarios no puedan quitarlo. Con el `runc` predeterminado, el código del sandbox comparte el kernel del nodo.

</details>

### 2. Una plantilla omite `networkPolicy` y conserva `networkPolicyManagement: Managed`. ¿Qué afirmación sobre la política generada es correcta?

- A. Permite todo el tráfico de salida, incluido CoreDNS
- B. Solo permite la entrada desde Pods `sandbox-router` en `agent-sandbox-system` y el tráfico de salida a rangos IPv4 e IPv6 no privados; CoreDNS no está permitido
- C. Permite la entrada desde todos los Pods del mismo espacio de nombres
- D. Solo permite el tráfico de salida al CIDR de VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Solo permite la entrada desde Pods `sandbox-router` en `agent-sandbox-system` y el tráfico de salida a rangos IPv4 e IPv6 no privados; CoreDNS no está permitido**

**Explicación:**
La lista de excepciones predeterminada excluye `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` y `169.254.0.0/16` de `0.0.0.0/0`, y `fc00::/7` y `fe80::/10` de `::/0`. El bloqueo de CoreDNS es deliberado para impedir el descubrimiento de servicios internos, así que los nombres de host públicos no se resuelven hasta que cambies la política o el resolver del Pod.

</details>

### 3. En un clúster EKS IPv4, ¿a qué dirección todavía puede acceder un sandbox con la política administrada predeterminada si no se agrega una excepción?

- A. A IMDS en `169.254.169.254`
- B. Al EKS Pod Identity Agent en `169.254.170.23`
- C. A un Pod de un CIDR secundario `100.64.0.0/10` usado para redes personalizadas de VPC CNI
- D. A un Pod en `10.0.12.34`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. A un Pod de un CIDR secundario `100.64.0.0/10` usado para redes personalizadas de VPC CNI**

**Explicación:**
La lista predeterminada de excepciones solo cubre los rangos RFC1918 y de enlace local. `100.64.0.0/10` no es RFC1918, por lo que esas direcciones internas quedan dentro de la regla permitida `0.0.0.0/0`. IMDS y Pod Identity Agent están dentro de `169.254.0.0/16`, y `10.0.12.34` está dentro de `10.0.0.0/8`, así que las tres quedan bloqueadas. En clústeres IPv6 la situación es distinta: se ignoran las reglas IPv4, no se excluyen las direcciones unicast globales de VPC y no se filtra el tráfico IPv4 de salida mediante `ENABLE_V4_EGRESS`.

</details>

### 4. Un Pod de agente en el espacio de nombres `agent-orchestrator` usa el modo in-cluster del SDK para conectarse directamente a un Pod sandbox creado a partir de una plantilla con política administrada. ¿Qué sucede?

- A. Funciona porque el tráfico dentro del clúster nunca se filtra
- B. Se bloquea hasta que la política de la plantilla agrega una regla de entrada para ese espacio de nombres (con un CNI que aplique políticas)
- C. Solo funciona por IPv6
- D. El SDK recurre automáticamente a un Gateway público

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Se bloquea hasta que la política de la plantilla agrega una regla de entrada para ese espacio de nombres (con un CNI que aplique políticas)**

**Explicación:**
La regla de entrada predeterminada solo admite el router. Las conexiones directas mediante DNS de Service o IP del Pod omiten el router, así que necesitan una regla de entrada explícita. En EKS esto presupone que está habilitada la aplicación de políticas de red en VPC CNI; sin esa aplicación, la política no bloquea nada.

</details>

### 5. ¿Qué campos de `SandboxClaim` fuerzan un inicio en frío en lugar de adoptar un Sandbox en caliente?

- A. `warmPoolRef`
- B. `lifecycle.shutdownTime`
- C. `env` o `volumeClaimTemplates`
- D. `lifecycle.ttlSecondsAfterFinished`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. `env` o `volumeClaimTemplates`**

**Explicación:**
Las variables de entorno y los volúmenes deben existir antes de crear el Pod, mientras que el Pod en caliente ya existe. Una solicitud que establezca cualquiera de ellos se crea en frío a partir de la plantilla del pool. La plantilla también debe permitirlos: tanto `envVarsInjectionPolicy` como `volumeClaimTemplatesPolicy` tienen `Disallowed` como valor predeterminado.

</details>

### 6. Quieres usar Kata Containers en EKS sin instancias bare metal. ¿Qué enfoque coincide con las capacidades documentadas?

- A. EKS Auto Mode con un runtime containerd personalizado
- B. Fargate, porque cada Pod ya se ejecuta en una máquina virtual y allí se aplica la NetworkPolicy administrada
- C. Karpenter v1.13.0+ con `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled` en una familia compatible como M8i, C8i o R8i, más un RuntimeClass asociado a esos nodos
- D. Cualquier instancia Graviton, porque todas exponen virtualización anidada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Karpenter v1.13.0+ con `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled` en una familia compatible como M8i, C8i o R8i, más un RuntimeClass asociado a esos nodos**

**Explicación:**
EC2 admite virtualización anidada en familias Intel específicas (M7i/C7i/R7i, M8i/C8i/R8i y otras). Karpenter filtra tipos de instancia para elegir los que informan `nested-virtualization`. Auto Mode administra la AMI y el runtime de contenedores, así que no se puede agregar Kata allí. VPC CNI no puede aplicar políticas de red a Pods de Fargate. Asocia RuntimeClass mediante `scheduling` para que los Pods solo se programen en nodos preparados.

</details>

### 7. ¿Qué ocurre con un Sandbox cuando `operatingMode` cambia de `Running` a `Suspended`?

- A. Se eliminan el objeto Sandbox, el Pod y los PVC
- B. Se elimina el Pod; el objeto Sandbox y sus PVC permanecen, y la condición `Suspended` pasa de `PodTerminating` a `PodTerminated`
- C. El Pod se congela en memoria en el mismo nodo
- D. Solo se elimina el Service headless

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Se elimina el Pod; el objeto Sandbox y sus PVC permanecen, y la condición `Suspended` pasa de `PodTerminating` a `PodTerminated`**

**Explicación:**
La suspensión se basa en PVC: se detiene el cómputo y se conserva el almacenamiento. `Ready` pasa a False con el motivo `SandboxSuspended`. En EKS, los volúmenes EBS pertenecen a una zona, por lo que el Pod reanudado debe programarse en la zona de disponibilidad del volumen.

</details>

### 8. Antes de actualizar a v1.0.6 un clúster que ejecuta Agent Sandbox v0.4.x, ¿qué debes hacer?

- A. Nada; `kubectl apply` de v1.0.6 convierte automáticamente los objetos
- B. Actualizar a v0.5.2 o posterior, migrar los objetos almacenados a `v1beta1` y confirmar que `status.storedVersions` de cada CRD solo enumere `v1beta1`
- C. Eliminar todos los CRD y volver a crearlos
- D. Volver a habilitar el webhook de conversión en v1.0.6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Actualizar a v0.5.2 o posterior, migrar los objetos almacenados a `v1beta1` y confirmar que `status.storedVersions` de cada CRD solo enumere `v1beta1`**

**Explicación:**
v1.0.0 eliminó `v1alpha1` y el webhook de conversión, y no se admiten actualizaciones directas desde versiones anteriores a v0.5.0. Si `v1alpha1` sigue en `storedVersions`, el servidor de API rechaza la actualización. Eliminar los CRD borraría en cascada todos los Sandbox, claims, plantillas y pools.

</details>

### 9. Necesitas acceso desde el navegador a los sandboxes a través de `sandbox-router`. ¿Qué diseño coincide con las directrices de EKS del capítulo?

- A. Un `Service` de tipo `LoadBalancer` con un NLB orientado a Internet que usa el autorizador `AllowAll` predeterminado del router
- B. CloudFront → origen VPC de CloudFront → ALB interno → `sandbox-router-svc`, con autorización v2 mediante tokens de alcance limitado y límites de frecuencia en la capa ALB o Envoy
- C. Una IP pública en cada Pod sandbox
- D. Reenvío de puertos desde el portátil de cada usuario en producción

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. CloudFront → origen VPC de CloudFront → ALB interno → `sandbox-router-svc`, con autorización v2 mediante tokens de alcance limitado y límites de frecuencia en la capa ALB o Envoy**

**Explicación:**
Solo CloudFront es público; el ALB es interno y su Security Group admite únicamente el Security Group del origen VPC de CloudFront o una lista de prefijos administrada. El autorizador predeterminado del router es `AllowAll` y no aplica límites de conexiones en conexiones actualizadas como WebSockets, así que la autorización y los límites deben configurarse antes de exponerlo.

</details>

### 10. ¿Qué cambia v1.0.6 para un Sandbox con un nombre de 70 caracteres y `spec.service: true`?

- A. Nada; sigue funcionando como antes
- B. Una regla CEL lo rechaza durante la admisión y un objeto existente falla en cada actualización hasta que se quite `spec.service` o se vuelva a crear el Sandbox con un nombre de 63 caracteres o menos
- C. El controlador trunca automáticamente el nombre del Service
- D. El Sandbox se convierte a `v1alpha1`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Una regla CEL lo rechaza durante la admisión y un objeto existente falla en cada actualización hasta que se quite `spec.service` o se vuelva a crear el Sandbox con un nombre de 63 caracteres o menos**

**Explicación:**
El Service headless usa el nombre del Sandbox, y el nombre de un Service es una etiqueta DNS-1035 de un máximo de 63 caracteres, así que esos Sandbox nunca llegaron a `Ready`. v1.0.6 informa del fallo durante la admisión. La regla cubre todo el objeto y no excluye los objetos existentes, así que también fallan las actualizaciones de estado.

</details>
