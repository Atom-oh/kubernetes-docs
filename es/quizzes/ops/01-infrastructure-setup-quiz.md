# Cuestionario de configuración de infraestructura

> **Documento relacionado**: [Configuración de infraestructura](../../ops/01-infrastructure-setup.md)

## Preguntas de opción múltiple

### 1. ¿Qué tres capas operativas usa esta guía?

- A) Red → Clúster → Plataforma
- B) Fundamentos → Carga de trabajo → Base de datos
- C) VPC → Pod → Contenedor
- D) Todos los recursos en un mismo estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Red → Clúster → Plataforma**

00-shared es un proceso de arranque independiente. La capa de red administra la VPC, la capa de clúster administra EKS y la capa de plataforma administra CoreDNS, Pod Identity y el acceso de los equipos. Separar los estados no impide que los fallos de VPC o DNS afecten a las demás capas.

</details>

### 2. ¿Qué ajuste habilita el bloqueo nativo del backend de S3 en Terraform 1.10 o posterior?

- A) use_lockfile = true
- B) Crear siempre una tabla de DynamoDB
- C) Habilitar solo el versionado del bucket
- D) Usar la misma clave para todas las capas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) use_lockfile = true**

El bloqueo nativo usa escrituras condicionales de S3. El bloqueo de DynamoDB sigue siendo pertinente para configuraciones existentes y transiciones, pero no es necesario para el bloqueo nativo de S3. Cambiar solo el mecanismo de bloqueo no traslada la ubicación donde se almacena el estado.

</details>

### 3. ¿Qué afirmación sobre la seguridad de terraform_remote_state es correcta?

- A) Los lectores solo pueden acceder a las salidas
- B) El acceso al backend puede exponer toda la instantánea del estado, por lo que hay que considerar los límites de confianza
- C) sensitive=true revoca el acceso de lectura de IAM
- D) El estado nunca contiene valores sensibles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El acceso al backend puede exponer toda la instantánea del estado, por lo que hay que considerar los límites de confianza**

La expresión expone las salidas raíz, pero el estado subyacente contiene más información. Considera publicar por separado solo los valores necesarios cuando se crucen límites de confianza.

</details>

### 4. ¿Qué afirmación sobre un clúster regional estándar de EKS y los grupos integrados de Auto Mode es correcta?

- A) Basta con una sola zona de disponibilidad para las subredes del plano de control
- B) El nombre blue fija los nodos de trabajo en la zona AZ-a
- C) Las subredes de EKS deben abarcar al menos dos zonas de disponibilidad distintas; las restricciones de ubicación de los nodos de trabajo son independientes
- D) Una etiqueta de subred Cluster=blue fija la ubicación de los nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Las subredes de EKS deben abarcar al menos dos zonas de disponibilidad distintas; las restricciones de ubicación de los nodos de trabajo son independientes**

Los grupos integrados pueden usar varias zonas de disponibilidad configuradas. Las celdas de nodos de trabajo de una sola zona requieren diseñar la ubicación mediante NodePool/NodeClass y disponer de capacidad de recuperación en otras celdas.

</details>

### 5. ¿Qué sucede si se añade gpu como nombre de grupo integrado en compute_config.node_pools?

- A) Se crea un grupo GPU integrado oficial
- B) gpu no es un nombre de grupo integrado; configura un NodePool personalizado adecuado
- C) Los nodos existentes se convierten inmediatamente en GPU
- D) Todos los clústeres se vuelven exclusivos para GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) gpu no es un nombre de grupo integrado; configura un NodePool personalizado adecuado**

Los nombres integrados son general-purpose y system. La entrada es una lista de nombres, no un mapa arbitrario que defina grupos GPU. Los NodePool personalizados corresponden al lado de GitOps de esta guía.

</details>

### 6. ¿Cuál es el propósito y el requisito correctos de EKS Pod Identity?

- A) Corrige automáticamente las descargas de imágenes de Pod desde ECR
- B) Siempre requiere un proveedor OIDC
- C) Proporciona credenciales de rol para llamadas compatibles del SDK, con asociación, relación de confianza y compatibilidad de nodo
- D) La asociación instala ServiceAccount y ESO

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Proporciona credenciales de rol para llamadas compatibles del SDK, con asociación, relación de confianza y compatibilidad de nodo**

Auto Mode incluye la funcionalidad del agente; los nodos normales de EKS pueden necesitar el agente por separado. Configura el namespace y el SA correspondientes, y distingue los permisos de kubelet para descargar imágenes de los permisos de la aplicación para llamadas al SDK.

</details>

### 7. ¿Cómo se debe separar el estado por entorno y color de clúster?

- A) TF_DATA_DIR por sí solo separa una clave de S3 compartida
- B) Seleccionar valores distintos de bucket/clave del backend y directorios de inicialización correspondientes
- C) Cambiar la variable de entorno traslada el estado de producción a desarrollo
- D) Deshabilitar el versionado de S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Seleccionar valores distintos de bucket/clave del backend y directorios de inicialización correspondientes**

La configuración del backend determina la ubicación real del estado. TF_DATA_DIR separa los metadatos de inicialización, los módulos y las cachés de proveedores; no sustituye la clave de estado. Separa también el estado local de arranque por cuenta y entorno.

</details>

### 8. ¿Cómo gestiona este ejemplo de Auto Mode CoreDNS y las StorageClasses?

- A) Ambos se crean siempre sin configuración
- B) Auto Mode puro usa DNS local al nodo; los clústeres mixtos necesitan un Deployment de CoreDNS; las StorageClasses se crean por separado
- C) Siempre se instalan agentes duplicados de EBS CSI y Pod Identity
- D) Se fija la versión de CoreDNS a la palabra latest

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Auto Mode puro usa DNS local al nodo; los clústeres mixtos necesitan un Deployment de CoreDNS; las StorageClasses se crean por separado**

Auto Mode puro usa CoreDNS como servicio de sistema del nodo. Los clústeres mixtos conservan el Deployment; consulta la compatibilidad de Kubernetes y de la región y fija la versión de ese complemento. Las StorageClasses de Auto Mode usan ebs.csi.eks.amazonaws.com.

</details>

### 9. ¿Una entrada de acceso de administrador completa por sí sola el acceso con kubectl?

- A) También concede IAM DescribeCluster y acceso de red
- B) No: autentícate como ese principal y prepara los permisos de IAM y la conectividad a la API privada
- C) El solicitante de Terraform siempre se convierte automáticamente en administrador
- D) La misma entrada debe volver a crearse en la capa de plataforma

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No: autentícate como ese principal y prepara los permisos de IAM y la conectividad a la API privada**

Este ejemplo deshabilita la administración automática del creador. Las políticas de acceso de EKS rigen los permisos de Kubernetes, por separado de IAM. Una sola capa debe ser responsable de la entrada de acceso de cada principal.

</details>

### 10. ¿Qué gestión de fallos es correcta para una prueba de humo?

- A) Ocultar los errores al crear Pods con || true
- B) Eliminar siempre un namespace preexistente de la prueba de humo
- C) Devolver un estado distinto de cero si falla y limpiar solo el namespace temporal verificado
- D) Considerar saludable cualquier Pod en fase Running

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Devolver un estado distinto de cero si falla y limpiar solo el namespace temporal verificado**

La prueba abarca la programación de cargas de trabajo y el DNS del clúster, no el tráfico externo del balanceador ni todas las dependencias de la aplicación. Los recuentos READY de contenedores y las condiciones Ready de los Pods también son distintos.

</details>
