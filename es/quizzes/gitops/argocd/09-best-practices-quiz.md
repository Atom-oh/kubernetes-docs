# Cuestionario de mejores prácticas de ArgoCD

Este cuestionario evalúa tu comprensión de las mejores prácticas y los patrones operativos de ArgoCD.

1. ¿Cuál es el enfoque recomendado para gestionar la propia configuración de ArgoCD?
   - A) Configuración manual a través de la UI
   - B) Gestionar ArgoCD con ArgoCD (patrón app-of-apps)
   - C) Usar kubectl apply directamente
   - D) La configuración nunca debe cambiar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar ArgoCD con ArgoCD (patrón app-of-apps)**

**Explicación:**
El patrón "app-of-apps" consiste en que ArgoCD gestione su propia configuración y otras Applications de ArgoCD. Esto garantiza que la configuración de ArgoCD esté controlada por versiones y siga los principios de GitOps.

</details>

2. ¿Cuál es la estructura de repositorio recomendada para GitOps?
   - A) Mezclar el código de la aplicación y los manifiestos en el mismo repositorio
   - B) Repositorios separados para el código de la aplicación y los manifiestos de deployment
   - C) Almacenar todo en un único archivo
   - D) Usar solo charts de Helm de repositorios públicos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Repositorios separados para el código de la aplicación y los manifiestos de deployment**

**Explicación:**
Separar el código de la aplicación de los manifiestos de deployment proporciona registros de auditoría más claros, permite que distintos equipos gestionen cada uno e impide que los cambios de deployment activen CI.

</details>

3. ¿Cómo debes gestionar las configuraciones específicas de cada entorno?
   - A) Crear Applications separadas para cada entorno
   - B) Usar overlays de Kustomize o archivos de values de Helm para cada entorno
   - C) Codificar los valores directamente en los manifiestos
   - D) Usar variables de entorno en los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar overlays de Kustomize o archivos de values de Helm para cada entorno**

**Explicación:**
Usar overlays de Kustomize o archivos de values de Helm te permite mantener una configuración base común mientras personalizas valores específicos (replicas, resources, domains) para cada entorno.

</details>

4. ¿Cuál es el enfoque recomendado para promover cambios entre entornos?
   - A) Commits directos a la rama de producción
   - B) Pull requests con revisión desde staging hasta producción
   - C) Sincronización manual en la UI
   - D) Promoción automática sin revisión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pull requests con revisión desde staging hasta producción**

**Explicación:**
Usar pull requests para la promoción garantiza que los cambios se revisen antes de llegar a producción, proporciona un registro de auditoría y permite realizar comprobaciones automatizadas (tests, validación de políticas) antes de fusionarlos.

</details>

5. ¿Cómo debes gestionar los Secrets en un flujo de trabajo de GitOps?
   - A) Hacer commit de Secrets en texto sin formato en Git
   - B) Usar Secrets cifrados (Sealed Secrets, SOPS) o administradores externos de Secrets
   - C) Crear Secrets manualmente en cada cluster
   - D) Almacenar Secrets en variables de entorno

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar Secrets cifrados (Sealed Secrets, SOPS) o administradores externos de Secrets**

**Explicación:**
Los Secrets nunca deben almacenarse en texto sin formato en Git. Usa herramientas de cifrado como Sealed Secrets o SOPS, o administradores externos de Secrets como HashiCorp Vault con External Secrets Operator.

</details>
