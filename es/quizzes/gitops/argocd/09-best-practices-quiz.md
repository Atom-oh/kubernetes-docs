# Cuestionario de mejores prácticas de ArgoCD

Este cuestionario evalúa tu comprensión de las mejores prácticas y los patrones operativos de ArgoCD.

1. ¿Qué patrón usa un repositorio raíz administrado por un administrador para declarar varias Applications secundarias?
   - A) Configuración manual a través de la UI
   - B) App of Apps
   - C) Usar kubectl apply directamente
   - D) La configuración nunca debe cambiar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) App of Apps**

**Explicación:**
App of Apps usa una Application raíz para administrar Applications secundarias. No es sinónimo de que Argo CD se administre a sí mismo ni es obligatorio en todas las instalaciones. Considérelo una capacidad administrativa, restrinja las escrituras al repositorio y conserve una ruta independiente de arranque/recuperación.

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
Separar el código de la aplicación de los manifiestos de despliegue proporciona registros de auditoría más claros, permite que distintos equipos administren cada uno y puede evitar reconstruir el código de la aplicación para cambios que solo afectan al despliegue. Aun así, hay que diseñar explícitamente los activadores de CI, los filtros de rutas y los límites de los repositorios.

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
