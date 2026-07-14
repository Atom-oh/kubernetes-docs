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
Una Application de ArgoCD es un recurso personalizado de Kubernetes que define el origen (repositorio Git, ruta, revisión) y el destino (cluster, namespace) de una aplicación, junto con las políticas de sincronización y las comprobaciones de estado.

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

4. ¿Cómo puedes implementar una aplicación en un namespace específico que aún no existe?
   - A) Crear primero el namespace manualmente
   - B) Usar syncPolicy.syncOptions con CreateNamespace=true
   - C) No es posible
   - D) Usar un hook de pre-sincronización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar syncPolicy.syncOptions con CreateNamespace=true**

**Explicación:**
Configurar `CreateNamespace=true` en `syncPolicy.syncOptions` indica a ArgoCD que cree automáticamente el namespace de destino si no existe antes de sincronizar los recursos de la aplicación.

</details>

5. ¿Cuál es la diferencia entre `targetRevision: HEAD` y `targetRevision: main`?
   - A) No hay diferencia
   - B) HEAD siempre apunta a la rama predeterminada; main se especifica explícitamente
   - C) HEAD es más rápido
   - D) main admite webhooks; HEAD no

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) HEAD siempre apunta a la rama predeterminada; main se especifica explícitamente**

**Explicación:**
`HEAD` es una referencia simbólica que apunta a la rama predeterminada del repositorio, mientras que `main` especifica explícitamente la rama principal. Usar `HEAD` es más flexible si cambia la rama predeterminada.

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
De forma predeterminada, ArgoCD usa el nombre de la Application como nombre de release de Helm. Configurar `releaseName` explícitamente te permite usar un nombre diferente para el release de Helm.

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
ArgoCD admite especificar valores de Helm mediante `spec.source.helm.valueFiles` (que hace referencia a archivos en el repositorio) y/o `spec.source.helm.values` (YAML en línea). Ambos pueden usarse juntos y los valores en línea tienen prioridad.

</details>
