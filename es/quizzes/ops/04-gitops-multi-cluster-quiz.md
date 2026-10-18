# Cuestionario de GitOps multiclúster

> **Documento relacionado**: [GitOps multiclúster](../../ops/04-gitops-multi-cluster.md)

## Preguntas de opción múltiple

### 1. ¿Qué es el modelo hub-spoke en GitOps multiclúster?

- A) Un patrón de topología de red
- B) Un clúster central de gestión que controla varios clústeres de cargas de trabajo
- C) Una estrategia de replicación de datos
- D) Un algoritmo de balanceo de carga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un clúster central de gestión que controla varios clústeres de cargas de trabajo**

**Explicación:**
En el modelo hub-spoke, un clúster central, el «hub», ejecuta ArgoCD y gestiona los despliegues en varios clústeres de cargas de trabajo, los «spokes». Así se centralizan las operaciones de GitOps y se mantienen aisladas las cargas entre clústeres.

</details>

### 2. ¿Cómo consigue ArgoCD alta disponibilidad (HA)?

- A) Ejecutando una sola réplica con reinicio automático
- B) Combinando replicación específica de cada componente, fragmentación del controller y ubicación resiliente
- C) Usando replicación de una base de datos externa
- D) Desplegándose en varias regiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Combinando replicación específica de cada componente, fragmentación del controller y ubicación resiliente**

**Explicación:**
El Application Controller distribuye los clústeres de destino entre fragmentos; no mantiene todas las réplicas restantes en espera. ApplicationSet usa una elección de líder independiente y Server no conserva estado. La alta disponibilidad de Redis, la ubicación, la capacidad y los PDB atienden modos de fallo distintos; añadir réplicas por sí solo no garantiza la disponibilidad.

</details>

### 3. ¿Qué es un ApplicationSet en ArgoCD?

- A) Un grupo de Applications creadas manualmente
- B) Una plantilla que genera Applications dinámicamente a partir de generadores
- C) Una copia de seguridad de las configuraciones de Application
- D) Una colección de charts de Helm

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una plantilla que genera Applications dinámicamente a partir de generadores**

**Explicación:**
ApplicationSet es un controller que usa generadores (List, Cluster, Git, Matrix, entre otros) para crear y gestionar automáticamente varias Applications de ArgoCD a partir de una sola plantilla. Esto permite escalar los despliegues en varios clústeres y entornos.

</details>

### 4. ¿Qué generador de ApplicationSet crea Applications a partir de los secretos de clústeres registrados?

- A) El generador List
- B) El generador Git
- C) El generador Cluster
- D) El generador Matrix

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El generador Cluster**

**Explicación:**
El generador Cluster selecciona los clústeres registrados mediante el selector configurado y proporciona sus metadatos. Es posible que el clúster local predeterminado no tenga un Secret, por lo que el selector basado en etiquetas de Secret podría excluirlo. Solo se seleccionan los clústeres nuevos si coinciden sus datos de registro y etiquetas.

</details>

### 5. ¿Cómo se puede integrar IAM Identity Center (SSO) con ArgoCD?

- A) Mediante una conexión directa a la base de datos
- B) Mediante SAML a través de Dex, asignando a RBAC de Argo CD los atributos verificados de la aserción
- C) Mediante autenticación con claves SSH
- D) Mediante la gestión de claves de API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante SAML a través de Dex, asignando a RBAC de Argo CD los atributos verificados de la aserción**

**Explicación:**
Este capítulo sigue la integración documentada de Identity Center con SAML y Dex. Una URL de SAML no es un emisor de OIDC. Asignar grupos no garantiza que se incluya una declaración de grupos; la guía de origen señala la asignación del atributo de grupo como solución alternativa. El ejemplo mínimo asigna explícitamente identidades de correo electrónico verificadas.

</details>

### 6. ¿Cuál es el propósito de External Secrets Operator en GitOps?

- A) Cifrar repositorios de Git
- B) Sincronizar secretos de proveedores externos, como AWS Secrets Manager, con Kubernetes
- C) Rotar certificados TLS
- D) Gestionar claves SSH para acceder a Git

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sincronizar secretos de proveedores externos, como AWS Secrets Manager, con Kubernetes**

**Explicación:**
External Secrets Operator crea automáticamente secretos de Kubernetes a partir de sistemas externos de gestión de secretos, como AWS Secrets Manager, HashiCorp Vault o Azure Key Vault. Así se mantienen los datos confidenciales fuera de Git y se conservan los flujos de trabajo de GitOps.

</details>

### 7. En la configuración de un proyecto de ArgoCD, ¿qué restringe `sourceRepos`?

- A) Los clústeres de destino para los despliegues
- B) Los repositorios de Git permitidos como origen de las Applications
- C) La selección de espacios de nombres
- D) Las cuotas de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los repositorios de Git permitidos como origen de las Applications**

**Explicación:**
El campo `sourceRepos` de los proyectos de ArgoCD especifica qué repositorios de Git pueden servir como origen de las Applications de ese proyecto. Restringe la selección de origen, pero por sí solo no proporciona credenciales del repositorio, permisos RBAC en el destino ni un entorno aislado para código no confiable.

</details>

### 8. ¿Qué ventaja ofrece el generador Matrix de ApplicationSet?

- A) Realiza cálculos matemáticos
- B) Combina dos generadores secundarios para producir combinaciones compatibles de parámetros
- C) Cifra los manifiestos de las Applications
- D) Valida la sintaxis de YAML

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Combina dos generadores secundarios para producir combinaciones compatibles de parámetros**

**Explicación:**
El generador Matrix tiene exactamente dos generadores secundarios. Combina los parámetros que estos producen, sujeto a que las claves sean compatibles y a las restricciones de anidamiento admitidas. Por ejemplo, combinar un generador Cluster con uno List permite desplegar varios servicios en varios clústeres.

</details>

### 9. Al gestionar NodePools mediante GitOps, ¿qué aspecto es importante?

- A) No se pueden gestionar NodePools mediante GitOps
- B) Los cambios deben hacerse gradualmente para evitar interrumpir las cargas de trabajo en ejecución
- C) Los NodePools deben estar en el mismo espacio de nombres que ArgoCD
- D) Solo se pueden gestionar instancias Spot

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los cambios deben hacerse gradualmente para evitar interrumpir las cargas de trabajo en ejecución**

**Explicación:**
Gestiona con cuidado los cambios de NodePool mediante GitOps, porque pueden provocar el reemplazo de nodos. Revisa los cambios, la capacidad para reemplazos, los presupuestos de interrupción aplicables y el comportamiento de eliminación. Separar las Applications de infraestructura con sincronización manual puede limitar cambios accidentales; ninguna estrategia de sincronización garantiza reemplazos de nodos sin interrupciones.

</details>

### 10. ¿Cuál es la forma recomendada de añadir un clúster remoto a ArgoCD?

- A) Editar directamente el ConfigMap de ArgoCD
- B) Usar `argocd cluster add` o crear un Secret de clúster con credenciales
- C) Instalar ArgoCD en cada clúster
- D) Usar `kubectl port-forward`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar `argocd cluster add` o crear un Secret de clúster con credenciales**

**Explicación:**
Los clústeres remotos se añaden con el comando de CLI `argocd cluster add` o mediante un Secret que incluya la URL del servidor de API del clúster y las credenciales. La CLI puede modificar el RBAC del clúster de destino. La ruta declarativa de AWS requiere que ya existan la relación de confianza de roles, las EKS Access Entries/RBAC, la URL y la CA reales del endpoint y la conectividad de red; un Secret por sí solo no proporciona ninguno de esos requisitos previos.

</details>
