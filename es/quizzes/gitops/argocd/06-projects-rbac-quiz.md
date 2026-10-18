# Cuestionario sobre proyectos y RBAC de ArgoCD

Este cuestionario evalúa tu comprensión de los proyectos de ArgoCD y el control de acceso basado en roles.

1. ¿Cuál es el propósito principal de un proyecto de ArgoCD (AppProject)?
   - A) Agrupar repositorios Git relacionados
   - B) Proporcionar una agrupación lógica de aplicaciones con restricciones de acceso
   - C) Administrar namespaces de Kubernetes
   - D) Configurar pipelines de CI/CD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar una agrupación lógica de aplicaciones con restricciones de acceso**

**Explicación:**
Los AppProjects agrupan lógicamente las Applications y restringen las fuentes, los destinos y los recursos permitidos. Limitan el alcance de los despliegues de Argo CD; Kubernetes RBAC, Pod Security Admission, el aislamiento de red y las cuotas siguen siendo controles independientes.

</details>

2. ¿Qué controla el campo `sourceRepos` en un AppProject?
   - A) Las ramas Git que se pueden usar
   - B) Los repositorios fuente permitidos (Git/Helm/OCI)
   - C) Los repositorios de imágenes de contenedor
   - D) Las versiones de Helm charts

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los repositorios fuente permitidos (Git/Helm/OCI)**

**Explicación:**
El campo `sourceRepos` restringe qué repositorios Git, Helm y OCI pueden usar como fuentes las Applications; no selecciona ramas de Git ni registros de imágenes de contenedor. Usar `*` permite cualquier repositorio, mientras que las URL específicas limitan las fuentes permitidas a esos repositorios.

</details>

3. ¿Cómo se restringe a qué clusters y namespaces puede desplegar un AppProject?
   - A) Mediante el campo `destinations`
   - B) Mediante el campo `clusters`
   - C) Mediante el campo `namespaces`
   - D) Mediante Kubernetes NetworkPolicies

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Mediante el campo `destinations`**

**Explicación:**
El campo `destinations` define las combinaciones permitidas de clúster y namespace. Cada entrada compara un servidor o nombre de clúster registrado con un namespace. Este ámbito del destino de despliegue es distinto de `sourceNamespaces`, que controla dónde se ubican los recursos Application.

</details>

4. ¿Cuál es el propósito de `clusterResourceWhitelist` en un AppProject?
   - A) Permitir que se administren recursos específicos con ámbito de cluster
   - B) Incluir direcciones IP en una lista de permitidos
   - C) Permitir usuarios específicos
   - D) Habilitar características específicas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Permitir que se administren recursos específicos con ámbito de cluster**

**Explicación:**
Un proyecto personalizado nuevo sin una lista de permitidos no puede administrar recursos con ámbito de clúster. El proyecto predeterminado, que inicialmente es permisivo, constituye una excepción porque permite explícitamente todos los tipos. `clusterResourceWhitelist` permite que las Applications del proyecto administren tipos específicos, como Namespaces o ClusterRoles.

</details>

5. ¿Cómo se define un rol dentro de un proyecto de ArgoCD?
   - A) Mediante Kubernetes RBAC
   - B) Mediante el campo `roles` en la especificación de AppProject
   - C) Mediante un CRD Role independiente
   - D) No se pueden definir roles en los proyectos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante el campo `roles` en la especificación de AppProject**

**Explicación:**
Los roles del proyecto se definen en `spec.roles` de un AppProject. Cada rol tiene nombre, descripción, políticas (las acciones permitidas) y metadatos para emitir tokens o asociaciones de grupos. Los JWT firmados se emiten mediante la CLI o la API; declarar los metadatos por sí solo no emite ningún token.

</details>
