# Cuestionario sobre Backstage IDP

1. ¿Qué Entity Kind se usa para registrar un microservice en el Backstage Software Catalog?
   - A) Service
   - B) Component
   - C) Application
   - D) Workload

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Component**

**Explicación:**
En el Backstage Software Catalog, los microservices, websites y libraries se registran todos como Kind `Component`. El campo `spec.type` distingue entre service, website, library, etc.

</details>

---

2. ¿Cuál es el propósito principal de Backstage Software Templates (Golden Paths)?
   - A) Monitorizar el rendimiento de servicios existentes
   - B) Crear automáticamente nuevos servicios/infraestructura de forma estandarizada
   - C) Auditar la seguridad del cluster de Kubernetes
   - D) Monitorizar pipelines de CI/CD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear automáticamente nuevos servicios/infraestructura de forma estandarizada**

**Explicación:**
Software Templates (Golden Paths) permite a los desarrolladores introducir unos pocos parámetros en la UI de Backstage y generar automáticamente una estructura de proyecto estandarizada (Dockerfile, Helm chart, CI/CD, catalog-info.yaml, etc.), aplicando de forma natural las mejores prácticas de la organización.

</details>

---

3. ¿Qué anotación se requiere en catalog-info.yaml para mostrar el estado de los Pod de Kubernetes en Backstage?
   - A) kubernetes.io/pod-name
   - B) backstage.io/kubernetes-id
   - C) app.kubernetes.io/managed-by
   - D) backstage.io/k8s-cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) backstage.io/kubernetes-id**

**Explicación:**
La anotación `backstage.io/kubernetes-id` la usa el plugin de Kubernetes de Backstage para hacer coincidir entidades del catálogo con recursos de Kubernetes. Este valor debe coincidir con la etiqueta `backstage.io/kubernetes-id` en el Deployment de Kubernetes.

</details>

---

4. ¿Cuál es la configuración de PostgreSQL más adecuada para Backstage en un entorno de producción de EKS?
   - A) SQLite integrado
   - B) StatefulSet de PostgreSQL dentro del cluster
   - C) Amazon RDS PostgreSQL (gestionado externo)
   - D) DynamoDB

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon RDS PostgreSQL (gestionado externo)**

**Explicación:**
Los entornos de producción deben usar bases de datos gestionadas como Amazon RDS para copias de seguridad automáticas, alta disponibilidad (Multi-AZ) y monitorización. Configura `postgresql.enabled: false` en los valores de Helm y proporciona los detalles de conexión al RDS externo mediante Secrets.

</details>

---

5. ¿Qué herramienta de construcción de documentación usa Backstage TechDocs?
   - A) Docusaurus
   - B) GitBook
   - C) MkDocs
   - D) Sphinx

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) MkDocs**

**Explicación:**
Backstage TechDocs se basa en MkDocs. Genera documentación a partir del directorio `docs/` y el archivo `mkdocs.yml` del repositorio de un servicio, la publica en almacenamiento como S3 y la hace accesible directamente desde el catálogo.

</details>

---

6. Al adoptar Backstage de forma incremental, ¿con qué función deberías empezar?
   - A) Software Templates
   - B) Software Catalog
   - C) TechDocs
   - D) RBAC Permission Framework

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Software Catalog**

**Explicación:**
El Software Catalog es la base de Backstage y todas las demás funciones se construyen sobre él. Empieza registrando los servicios, las APIs y la información de equipos de tu organización, y luego añade Templates y TechDocs de forma incremental.

</details>

---

7. ¿Cómo puede un Backstage Software Template automatizar tanto la creación de repositorios de GitHub como la creación de Applications de ArgoCD?
   - A) Backstage llama directamente a la API de Kubernetes
   - B) Los pasos del template ejecutan secuencialmente las acciones publish:github y argocd:create-resources
   - C) Los webhooks de GitHub activan ArgoCD automáticamente
   - D) El Helm chart incluye todos los recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los pasos del template ejecutan secuencialmente las acciones publish:github y argocd:create-resources**

**Explicación:**
El Backstage Scaffolder ejecuta secuencialmente las acciones definidas en la sección `steps` del Template. `publish:github` crea el repositorio, y su salida (remoteUrl) se pasa como entrada a `argocd:create-resources` para crear automáticamente la ArgoCD Application. Finalmente, `catalog:register` la añade al catálogo.

</details>

---

8. ¿Cómo restringes a los equipos para que solo modifiquen sus propias entidades en el Backstage Permission Framework?
   - A) ClusterRole de RBAC de Kubernetes
   - B) Usar el campo conditions en la policy para coincidir con spec.owner
   - C) Permisos del repositorio de GitHub
   - D) Políticas de red de Ingress

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar el campo conditions en la policy para coincidir con spec.owner**

**Explicación:**
El campo `conditions` de la policy del Backstage Permission Framework puede hacer coincidir entidades donde `spec.owner` sea igual al nombre del equipo, concediendo permisos de actualización solo para sus propias entidades. Esto mantiene la autonomía del equipo mientras restringe la modificación de entidades de otros equipos a solo lectura.

</details>
