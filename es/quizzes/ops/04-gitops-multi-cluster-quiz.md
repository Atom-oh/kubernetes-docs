# Cuestionario de GitOps Multi-Cluster

> **Documento relacionado**: [GitOps Multi-Cluster](../../ops/04-gitops-multi-cluster.md)

## Preguntas de opción múltiple

### 1. ¿Qué es el modelo hub-spoke en GitOps multi-cluster?

- A) Un patrón de topología de red
- B) Un cluster central de gestión que controla varios clusters de workloads
- C) Una estrategia de replicación de datos
- D) Un algoritmo de balanceo de carga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un cluster central de gestión que controla varios clusters de workloads**

**Explicación:**
En el modelo hub-spoke, un cluster central "hub" ejecuta ArgoCD y gestiona deployments hacia varios clusters de workloads "spoke". Esto centraliza las operaciones de GitOps mientras mantiene los workloads aislados entre clusters.

</details>

### 2. ¿Cómo logra ArgoCD High Availability (HA)?

- A) Ejecutando una sola réplica con reinicio automático
- B) Ejecutando varias réplicas de cada componente con leader election
- C) Usando replicación de base de datos externa
- D) Desplegando en varias regiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ejecutando varias réplicas de cada componente con leader election**

**Explicación:**
ArgoCD HA despliega varias réplicas de los componentes application-controller, repo-server y server. El application-controller usa leader election para garantizar que solo una instancia procese cada application mientras las demás permanecen en espera.

</details>

### 3. ¿Qué es un ApplicationSet en ArgoCD?

- A) Un grupo de Applications creadas manualmente
- B) Una plantilla que genera Applications dinámicamente según generadores
- C) Una copia de seguridad de configuraciones de Application
- D) Una colección de charts de Helm

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una plantilla que genera Applications dinámicamente según generadores**

**Explicación:**
ApplicationSet es un controller que usa generadores (List, Cluster, Git, Matrix, etc.) para crear y gestionar automáticamente varias ArgoCD Applications desde una sola plantilla. Esto habilita deployments escalables multi-cluster y multi-entorno.

</details>

### 4. ¿Qué generador de ApplicationSet crea Applications basadas en secrets de clusters registrados?

- A) Generador List
- B) Generador Git
- C) Generador Cluster
- D) Generador Matrix

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Generador Cluster**

**Explicación:**
El generador Cluster itera sobre todos los clusters registrados en ArgoCD (almacenados como secrets) y genera una Application para cada uno. Esto permite el deployment automático en nuevos clusters sin modificar el ApplicationSet.

</details>

### 5. ¿Cómo se puede integrar IAM Identity Center (SSO) con ArgoCD?

- A) Conexión directa a la base de datos
- B) Autenticación SAML u OIDC con RBAC basado en grupos
- C) Autenticación con clave SSH
- D) Gestión de claves de API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Autenticación SAML u OIDC con RBAC basado en grupos**

**Explicación:**
ArgoCD admite SAML y OIDC para la integración con SSO. Los grupos de IAM Identity Center pueden asignarse a roles RBAC de ArgoCD, lo que permite una gestión de acceso centralizada donde los permisos se controlan mediante tu proveedor de identidad.

</details>

### 6. ¿Cuál es el propósito de External Secrets Operator en GitOps?

- A) Cifrar repositorios git
- B) Sincronizar secrets desde proveedores externos (AWS Secrets Manager) hacia Kubernetes
- C) Rotar certificados TLS
- D) Gestionar claves SSH para acceso a git

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sincronizar secrets desde proveedores externos (AWS Secrets Manager) hacia Kubernetes**

**Explicación:**
External Secrets Operator crea automáticamente Kubernetes secrets desde sistemas externos de gestión de secrets como AWS Secrets Manager, HashiCorp Vault o Azure Key Vault. Esto mantiene los datos sensibles fuera de git mientras conserva los workflows de GitOps.

</details>

### 7. En la configuración de proyectos de ArgoCD, ¿qué restringe `sourceRepos`?

- A) Clusters de destino para deployment
- B) Repositorios git permitidos para applications
- C) Selección de namespace
- D) Cuotas de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Repositorios git permitidos para applications**

**Explicación:**
El campo `sourceRepos` en ArgoCD Projects especifica qué repositorios git pueden usarse como fuentes para Applications en ese proyecto. Esto proporciona límites de seguridad al evitar el acceso no autorizado a repositorios.

</details>

### 8. ¿Cuál es el beneficio de usar el generador Matrix en ApplicationSets?

- A) Realiza cálculos matemáticos
- B) Combina varios generadores para crear el producto cartesiano de parámetros
- C) Cifra los manifests de application
- D) Valida la sintaxis YAML

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Combina varios generadores para crear el producto cartesiano de parámetros**

**Explicación:**
El generador Matrix combina dos o más generadores y crea Applications para cada combinación de sus salidas. Por ejemplo, combinar un generador Cluster con un generador List despliega varios services en varios clusters.

</details>

### 9. Al gestionar NodePools mediante GitOps, ¿cuál es una consideración clave?

- A) Los NodePools no se pueden gestionar mediante GitOps
- B) Los cambios deben ser graduales para evitar interrumpir workloads en ejecución
- C) Los NodePools deben estar en el mismo namespace que ArgoCD
- D) Solo se pueden gestionar instancias Spot

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los cambios deben ser graduales para evitar interrumpir workloads en ejecución**

**Explicación:**
Los cambios de NodePool mediante GitOps deben gestionarse cuidadosamente porque las modificaciones pueden activar reemplazos de nodes. Usar estrategias como Progressive Sync o Applications separadas para la gestión de nodes ayuda a evitar interrupciones.

</details>

### 10. ¿Cuál es la forma recomendada de añadir un cluster remoto a ArgoCD?

- A) Editar directamente el ConfigMap de ArgoCD
- B) Usar `argocd cluster add` o crear un Secret de cluster con credenciales
- C) Instalar ArgoCD en cada cluster
- D) Usar kubectl port-forward

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar `argocd cluster add` o crear un Secret de cluster con credenciales**

**Explicación:**
Los clusters remotos se añaden usando el comando CLI `argocd cluster add` o creando un Secret con la URL del servidor API del cluster y las credenciales. ArgoCD usa estas credenciales para desplegar y sincronizar applications en clusters remotos.

</details>
