# Cuestionario de configuración de infraestructura

> **Documento relacionado**: [Configuración de infraestructura](../../ops/01-infrastructure-setup.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el propósito principal de la arquitectura Terraform de 3 capas?

- A) Reducir la cantidad de archivos de Terraform
- B) Separar la infraestructura por ciclo de vida y radio de impacto
- C) Habilitar tiempos de despliegue más rápidos
- D) Eliminar la necesidad de gestionar el estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Separar la infraestructura por ciclo de vida y radio de impacto**

**Explicación:**
La arquitectura de 3 capas separa la infraestructura en capas Foundation (VPC, IAM), Platform (cluster de EKS) y Workload (aplicaciones). Cada capa tiene distintas frecuencias de cambio y radios de impacto, lo que permite cambios de infraestructura más seguros y manejables.

</details>

### 2. En la configuración del backend S3 de Terraform, ¿cuál es el propósito de la tabla de DynamoDB?

- A) Almacenar archivos de estado de Terraform
- B) Proporcionar bloqueo de estado y consistencia
- C) Hacer copias de seguridad de las configuraciones de Terraform
- D) Registrar operaciones de Terraform

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar bloqueo de estado y consistencia**

**Explicación:**
La tabla de DynamoDB habilita el bloqueo de estado para evitar modificaciones concurrentes al mismo archivo de estado. Esto evita condiciones de carrera cuando varios usuarios o pipelines de CI/CD intentan modificar la infraestructura simultáneamente.

</details>

### 3. ¿Qué te permite hacer el data source `terraform_remote_state`?

- A) Almacenar archivos de estado en una ubicación remota
- B) Referenciar outputs de otro estado de Terraform
- C) Migrar el estado entre backends
- D) Cifrar archivos de estado automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Referenciar outputs de otro estado de Terraform**

**Explicación:**
El data source `terraform_remote_state` permite que una configuración de Terraform lea valores de output desde otro archivo de estado. Esto habilita referencias entre capas, como que la capa Platform lea el ID de VPC desde la capa Foundation.

</details>

### 4. ¿Qué tamaño de bloque CIDR de VPC se recomienda para clusters de EKS en producción?

- A) /24 (256 direcciones)
- B) /20 (4,096 direcciones)
- C) /16 (65,536 direcciones)
- D) /8 (16 millones de direcciones)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) /16 (65,536 direcciones)**

**Explicación:**
Un bloque CIDR /16 proporciona 65,536 direcciones IP, lo cual se recomienda para clusters de EKS en producción. Esto permite la asignación de IPs de pod (especialmente con VPC CNI), crecimiento futuro y despliegues multi-AZ sin preocupaciones por agotamiento de IPs.

</details>

### 5. ¿Cuál es la característica clave de EKS Auto Mode en comparación con Managed Node Groups?

- A) Auto Mode requiere aprovisionamiento manual de nodos
- B) Auto Mode gestiona automáticamente el ciclo de vida y el escalado de los nodos
- C) Auto Mode solo admite instancias Spot
- D) Auto Mode elimina la necesidad de pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Auto Mode gestiona automáticamente el ciclo de vida y el escalado de los nodos**

**Explicación:**
EKS Auto Mode gestiona automáticamente el aprovisionamiento, escalado y ciclo de vida de los nodos según las demandas de la workload. A diferencia de Managed Node Groups, los operadores no necesitan configurar Auto Scaling Groups ni gestionar manualmente las actualizaciones de nodos.

</details>

### 6. ¿En qué se diferencia Pod Identity de IRSA (IAM Roles for Service Accounts)?

- A) Pod Identity no admite roles de IAM
- B) Pod Identity usa credenciales gestionadas por EKS sin configurar un proveedor OIDC
- C) Pod Identity requiere rotación manual de tokens
- D) Pod Identity solo funciona con Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod Identity usa credenciales gestionadas por EKS sin configurar un proveedor OIDC**

**Explicación:**
Pod Identity simplifica la integración con IAM al eliminar la necesidad de configurar un proveedor OIDC. AWS gestiona la inyección de credenciales mediante el Pod Identity Agent, lo que facilita la configuración y el mantenimiento en comparación con IRSA.

</details>

### 7. En la arquitectura de 3 capas, ¿qué capa contiene el recurso de cluster de EKS?

- A) Capa Foundation
- B) Capa Platform
- C) Capa Workload
- D) Capa Network

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Capa Platform**

**Explicación:**
La capa Platform contiene el cluster de EKS, los node groups y los add-ons del cluster. Depende de la capa Foundation (VPC, subnets) y proporciona la plataforma para la capa Workload (aplicaciones, services).

</details>

### 8. ¿Qué debe habilitarse en los buckets de S3 que almacenan el estado de Terraform?

- A) Acceso público
- B) Versionado y cifrado
- C) Alojamiento de sitio web estático
- D) Solo replicación entre regiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Versionado y cifrado**

**Explicación:**
Los archivos de estado de Terraform contienen información sensible y deben protegerse con versionado (para recuperarse de corrupción o cambios accidentales) y cifrado (para proteger secretos en reposo). El acceso público siempre debe bloquearse.

</details>

### 9. Al usar workspaces de Terraform para la gestión de múltiples entornos, ¿cuál es una limitación clave?

- A) Los workspaces no pueden usar variables
- B) Todos los entornos comparten la misma configuración de backend
- C) Los workspaces no admiten módulos
- D) Solo se permiten dos workspaces

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Todos los entornos comparten la misma configuración de backend**

**Explicación:**
Los workspaces de Terraform comparten la misma configuración de backend y el mismo código, lo que puede provocar cambios accidentales en producción al trabajar en desarrollo. Muchos equipos prefieren directorios o repositorios separados por entorno para lograr un aislamiento más fuerte.

</details>

### 10. ¿Cuál es el enfoque recomendado para gestionar las versiones de proveedores de Terraform?

- A) Usar siempre la versión más reciente sin restricciones
- B) Usar restricciones de versión exactas en el bloque required_providers
- C) Dejar que Terraform actualice automáticamente los proveedores
- D) Evitar especificar versiones de proveedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar restricciones de versión exactas en el bloque required_providers**

**Explicación:**
Especificar restricciones de versión exactas o pesimistas (por ejemplo, `~> 5.0`) en el bloque `required_providers` garantiza despliegues reproducibles y evita cambios incompatibles inesperados por actualizaciones de proveedores. Esto es especialmente importante en entornos de producción.

</details>
