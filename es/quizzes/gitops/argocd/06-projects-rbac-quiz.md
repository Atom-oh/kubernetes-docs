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
Los AppProjects proporcionan una agrupación lógica de Applications con restricciones sobre qué fuentes, destinos y recursos están permitidos. Habilitan la multi-tenencia al limitar lo que cada equipo puede desplegar.

</details>

2. ¿Qué controla el campo `sourceRepos` en un AppProject?
   - A) Las ramas Git que se pueden usar
   - B) Los repositorios Git desde los que las Applications pueden obtener manifiestos
   - C) Los repositorios de imágenes de contenedor
   - D) Las versiones de Helm charts

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los repositorios Git desde los que las Applications pueden obtener manifiestos**

**Explicación:**
El campo `sourceRepos` restringe qué repositorios Git pueden usar como fuentes las Applications de este proyecto. Usar `*` permite cualquier repositorio, mientras que las URL específicas limitan el acceso únicamente a esos repositorios.

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
El campo `destinations` define las combinaciones permitidas de cluster y namespace. Cada entrada especifica un `server` (URL del cluster o `*`) y un `namespace` (namespace específico o `*`) a los que pueden dirigirse las Applications.

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
De forma predeterminada, los proyectos no pueden administrar recursos con ámbito de cluster. `clusterResourceWhitelist` permite que las Applications del proyecto administren tipos específicos (como Namespaces o ClusterRoles).

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
Los roles de proyecto se definen en el campo `spec.roles` de un AppProject. Cada rol tiene un nombre, una descripción, políticas (qué acciones están permitidas) y tokens JWT opcionales o asociaciones de grupos.

</details>
