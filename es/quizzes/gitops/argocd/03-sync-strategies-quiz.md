# Cuestionario de estrategias de sincronización de ArgoCD

Este cuestionario evalúa tu comprensión de las estrategias y opciones de sincronización de ArgoCD.

1. ¿Cuál es la diferencia entre un "Sync" y un "Refresh" en ArgoCD?
   - A) Son la misma operación
   - B) Refresh compara el estado actual con Git; Sync aplica cambios para que coincidan
   - C) Sync es manual, Refresh es automático
   - D) Refresh elimina recursos, Sync los crea

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Refresh compara el estado actual con Git; Sync aplica cambios para que coincidan**

**Explicación:**
Una operación Refresh obtiene los manifiestos más recientes de Git y los compara con el estado live, actualizando el estado de la Application. Una operación Sync realmente aplica cambios al cluster para alinear el estado live con el estado deseado en Git.

</details>

2. ¿Qué hace habilitar la política de sincronización `automated`?
   - A) Elimina automáticamente la aplicación
   - B) Habilita la sincronización automática cuando el estado deseado difiere del estado live
   - C) Habilita la reversión automática
   - D) Crea copias de seguridad automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Habilita la sincronización automática cuando el estado deseado difiere del estado live**

**Explicación:**
Cuando `syncPolicy.automated` está habilitado, ArgoCD sincronizará automáticamente la aplicación siempre que detecte que el estado live se ha desviado del estado deseado definido en Git.

</details>

3. ¿Cuál es el propósito de la opción `prune` en la sincronización automática?
   - A) Limpiar ramas antiguas de Git
   - B) Eliminar automáticamente recursos que ya no están definidos en Git
   - C) Eliminar deployments fallidos
   - D) Eliminar la propia aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Eliminar automáticamente recursos que ya no están definidos en Git**

**Explicación:**
Cuando se establece `prune: true` en la sincronización automática, ArgoCD eliminará automáticamente los recursos de Kubernetes que existen en el cluster, pero que ya no están definidos en el repositorio Git.

</details>

4. ¿Qué hace `selfHeal: true` en una política de sincronización?
   - A) Corrige automáticamente errores de sintaxis de YAML
   - B) Sincroniza automáticamente cuando el estado live se desvía del estado deseado debido a cambios manuales
   - C) Reinicia Pods no saludables
   - D) Repara repositorios Git dañados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sincroniza automáticamente cuando el estado live se desvía del estado deseado debido a cambios manuales**

**Explicación:**
La autorreparación garantiza que, si alguien realiza un cambio manual en un recurso del cluster (fuera de Git), ArgoCD lo revertirá automáticamente para que coincida con el estado deseado en Git.

</details>

5. ¿Qué opción de sincronización usarías para reemplazar recursos en lugar de aplicar patches?
   - A) Force=true
   - B) Replace=true
   - C) Recreate=true
   - D) Update=true

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Replace=true**

**Explicación:**
La opción de sincronización `Replace=true` indica a ArgoCD que use `kubectl replace` en lugar de `kubectl apply`, lo que reemplaza completamente el recurso en vez de aplicarle un patch. Esto es útil al trabajar con campos inmutables.

</details>
