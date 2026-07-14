# Cuestionario de multi-cluster de Linkerd

Este cuestionario evalúa tu comprensión de las características de multi-cluster de Linkerd.

## Preguntas del cuestionario

### 1. ¿Cuál es el concepto central de la arquitectura multi-cluster de Linkerd?

A. Federación de mesh
B. Reflejo de Service
C. Fusión de clusters
D. Balanceador de carga global

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Reflejo de Service**

**Explicación:**
Linkerd utiliza una arquitectura de reflejo de Service. Los Services exportados desde clusters remotos aparecen como Services espejo en el cluster local, accesibles como Services locales.

</details>

### 2. ¿Qué se debe compartir para la comunicación mTLS entre dos clusters?

A. Identity Issuer
B. Trust Anchor
C. Certificados de workload
D. Kubernetes Secret

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Trust Anchor**

**Explicación:**
Para que dos clusters confíen mutuamente entre sí, deben compartir el mismo Trust Anchor (Root CA). Cada cluster puede tener Identity Issuers independientes, pero deben estar firmados por el mismo Trust Anchor.

</details>

### 3. ¿Qué label se utiliza para exportar un Service a otros clusters?

A. linkerd.io/exported: "true"
B. mirror.linkerd.io/exported: "true"
C. multicluster.linkerd.io/export: "enabled"
D. linkerd.io/multicluster: "export"

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. mirror.linkerd.io/exported: "true"**

**Explicación:**
Agregar el label `mirror.linkerd.io/exported: "true"` a un Service hace que otros clusters vinculados lo reflejen.

</details>

### 4. ¿Cuál es el formato de nomenclatura para los Services espejo?

A. `<service>.<cluster>`
B. `<service>-<cluster>`
C. `<cluster>-<service>`
D. `<service>@<cluster>`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `<service>-<cluster>`**

**Explicación:**
Los Services espejo se crean con el formato `<original-service-name>-<original-cluster-name>`. Ejemplo: el Service web del cluster west se refleja como web-west en el cluster east.

</details>

### 5. ¿Cuál es el propósito del comando `linkerd multicluster link`?

A. Conexión de red entre dos clusters
B. Registrar localmente las credenciales del cluster remoto
C. Configurar el enrutamiento del tráfico de Service a Service
D. Intercambio de certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Registrar localmente las credenciales del cluster remoto**

**Explicación:**
`linkerd multicluster link --cluster-name <name>` genera las credenciales del cluster actual (dirección del gateway, token de Service Account, etc.) para registrarlas en otro cluster.

</details>

### 6. ¿Qué comando comprueba el estado de los gateways multi-cluster?

A. `linkerd multicluster status`
B. `linkerd multicluster gateways`
C. `linkerd multicluster check`
D. `kubectl get gateway`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `linkerd multicluster gateways`**

**Explicación:**
`linkerd multicluster gateways` muestra el estado de los gateways de los clusters vinculados. Muestra ALIVE, NUM_SVC (número de Services espejo) y LATENCY.

</details>

### 7. ¿Cuál es la configuración recomendada para los gateways en multi-cluster de EKS?

A. Service ClusterIP
B. Service NodePort
C. NLB (Network Load Balancer)
D. ALB (Application Load Balancer)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. NLB (Network Load Balancer)**

**Explicación:**
Se recomienda NLB para los gateways multi-cluster en EKS. Está optimizado para el tráfico TCP/TLS y se configura con la anotación `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"`.

</details>

### 8. ¿Qué Services de backend se usan al dividir el tráfico entre clusters locales y remotos con TrafficSplit?

A. Service local y gateway remoto
B. Service local y Service espejo
C. Solo Service local
D. Referencia directa al Service remoto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Service local y Service espejo**

**Explicación:**
Los backends de TrafficSplit especifican el Service local (p. ej., web) y el Service espejo (p. ej., web-west). El tráfico hacia el Service espejo se enruta automáticamente al gateway del cluster remoto.

</details>

### 9. ¿Cuál NO es una función del mirror controller en entornos multi-cluster?

A. Observar Services remotos
B. Crear/actualizar Services espejo
C. Emitir certificados
D. Sincronizar endpoints

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Emitir certificados**

**Explicación:**
El service mirror controller observa los Services exportados en clusters remotos, crea/actualiza Services espejo localmente y sincroniza endpoints. La emisión de certificados es función del Identity Controller.

</details>

### 10. ¿Qué servicio de AWS se utiliza para la conectividad privada entre dos clusters de EKS?

A. Solo Direct Connect
B. VPC Peering o Transit Gateway
C. Solo Route 53
D. CloudFront

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. VPC Peering o Transit Gateway**

**Explicación:**
Para la conectividad privada entre clusters de EKS, usa VPC Peering (conexión directa entre dos VPC) o Transit Gateway (modelo hub-and-spoke). Configura el gateway con un NLB interno.

</details>

### 11. ¿Cómo permites el acceso solo a Services remotos específicos en un entorno multi-cluster?

A. NetworkPolicy
B. ServerAuthorization con SPIFFE ID
C. AWS Security Group
D. Kubernetes RBAC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. ServerAuthorization con SPIFFE ID**

**Explicación:**
Controla el acceso especificando SPIFFE IDs concretos del cluster remoto en meshTLS.identities de ServerAuthorization. Ejemplo: `spiffe://root.linkerd.cluster.local/ns/production/sa/api-gateway`

</details>

### 12. ¿Qué NO verifica el comando `linkerd multicluster check`?

A. Estado del recurso Link
B. Conectividad del gateway
C. Lógica de negocio de la aplicación
D. Estado del service mirror controller

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Lógica de negocio de la aplicación**

**Explicación:**
`linkerd multicluster check` verifica el estado de la infraestructura multi-cluster, incluidos los recursos Link, los gateways, el service mirror controller y los certificados. No verifica la lógica de la aplicación.

</details>
