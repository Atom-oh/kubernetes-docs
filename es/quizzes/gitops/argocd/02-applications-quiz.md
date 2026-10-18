# Cuestionario de Applications de ArgoCD

Este cuestionario evalúa tu comprensión de las Applications de ArgoCD y su configuración.

1. ¿Cuál es el propósito principal de un recurso Application de ArgoCD?
   - A) Definir controles de acceso de usuarios
   - B) Especificar el estado deseado de una aplicación y su configuración de sincronización
   - C) Configurar notificaciones
   - D) Administrar secretos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Especificar el estado deseado de una aplicación y su configuración de sincronización**

**Explicación:**
Una Application de ArgoCD es un recurso personalizado de Kubernetes que define el origen (repositorio Git, ruta y revisión) y el destino (cluster y namespace) de una aplicación, junto con una política de sincronización. El controlador informa el estado de salud; las comprobaciones de salud personalizadas para recursos se configuran por separado en `argocd-cm`.

</details>

2. ¿Qué campo de una especificación de Application define dónde deben implementarse los manifiestos?
   - A) source
   - B) target
   - C) destination
   - D) cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) destination**

**Explicación:**
El campo `destination` especifica el cluster de destino (mediante la URL o el nombre del servidor) y el namespace donde deben implementarse los recursos de la aplicación.

</details>

3. ¿Qué especifica el campo `spec.source.path` en una Application?
   - A) La ruta a la instalación de ArgoCD
   - B) El directorio dentro del repositorio Git que contiene los manifiestos
   - C) La ruta del sistema de archivos local
   - D) La ruta del servidor de API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El directorio dentro del repositorio Git que contiene los manifiestos**

**Explicación:**
El campo `path` en `source` especifica el directorio dentro del repositorio Git que contiene los manifiestos de Kubernetes, el chart de Helm o la configuración de Kustomize.

</details>

4. ¿Qué opción de sincronización integrada hace que Argo CD cree automáticamente `destination.namespace`?
   - A) Crear primero el namespace manualmente
   - B) Usar syncPolicy.syncOptions con CreateNamespace=true
   - C) No es posible
   - D) Usar un hook de pre-sincronización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar syncPolicy.syncOptions con CreateNamespace=true**

**Explicación:**
Configurar `CreateNamespace=true` en `syncPolicy.syncOptions` indica a Argo CD que cree automáticamente el namespace de destino antes de sincronizar, siempre que lo autoricen AppProject y RBAC. No crea cada namespace distinto que aparezca en los manifiestos.

</details>

5. ¿Cuál es la diferencia entre `targetRevision: HEAD` y `targetRevision: main`?
   - A) No hay diferencia
   - B) HEAD siempre apunta a la rama predeterminada; main se especifica explícitamente
   - C) HEAD es más rápido
   - D) main admite webhooks; HEAD no

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) HEAD sigue la referencia remota HEAD; main nombra una rama específica**

**Explicación:**
`HEAD` es una referencia simbólica que apunta a la rama predeterminada del repositorio remoto, mientras que `main` especifica explícitamente esa rama. Un cambio en la rama predeterminada puede cambiar el destino de la implementación. Para que las versiones publicadas sean reproducibles, usa una política con commits o etiquetas verificados.

</details>

6. ¿Qué tipo de origen usarías para implementar un chart de Helm desde un repositorio de Helm (no Git)?
   - A) git
   - B) helm
   - C) directory
   - D) kustomize

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) helm**

**Explicación:**
Al implementar desde un repositorio de Helm, configuras `source.chart` y `source.repoURL` para que apunten al repositorio de Helm, y ArgoCD lo tratará como un origen de Helm en lugar de un origen de Git.

</details>

7. ¿Qué sucede cuando configuras `spec.source.helm.releaseName`?
   - A) Crea un nuevo repositorio de Helm
   - B) Anula el nombre de release predeterminado (que es el nombre de la Application)
   - C) Habilita los hooks de Helm
   - D) Establece la versión del chart

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Anula el nombre de release predeterminado (que es el nombre de la Application)**

**Explicación:**
De forma predeterminada, Argo CD usa el nombre de la Application como nombre de release de Helm. `releaseName` cambia el valor de plantilla `Release.Name`, pero Argo CD sigue administrando el ciclo de vida de los recursos y no mantiene un release de Helm normal. Si el seguimiento se basa en etiquetas, comprueba cómo interactúa este ajuste con los selectores del chart y las etiquetas de seguimiento.

</details>

8. ¿Cómo especificas valores de Helm en una Application de ArgoCD?
   - A) Solo mediante archivos de valores en el repositorio
   - B) Solo en línea dentro de la especificación de Application
   - C) Tanto mediante archivos de valores como mediante valores en línea
   - D) Los valores deben almacenarse en un ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Tanto mediante archivos de valores como mediante valores en línea**

**Explicación:**
Argo CD admite valores de Helm mediante `spec.source.helm.valueFiles` (archivos del repositorio) o `spec.source.helm.values` (YAML en línea), y permite combinarlos. La precedencia completa es `parameters` > `valuesObject` > `values` > `valueFiles` > valores predeterminados del chart. Conviene elegir una sola representación en línea en vez de duplicar valores en `valuesObject` y `values`.

</details>
