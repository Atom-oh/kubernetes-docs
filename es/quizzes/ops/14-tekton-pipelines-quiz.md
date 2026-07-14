# Cuestionario sobre Tekton Pipelines

1. ¿Qué ventaja tiene Tekton sobre Jenkins o GitHub Actions en entornos Kubernetes?
   - A) Tekton proporciona más plugins
   - B) Las pipelines basadas en CRD se gestionan como recursos de Kubernetes, lo que habilita GitOps, RBAC y namespace isolation
   - C) Tekton proporciona mayor velocidad de ejecución
   - D) Tekton es gratuito mientras que otras herramientas son de pago

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las pipelines basadas en CRD se gestionan como recursos de Kubernetes, lo que habilita GitOps, RBAC y namespace isolation**

**Explicación:**
Tekton define Tasks, Pipelines y PipelineRuns como Kubernetes CRDs. Esto permite la gestión declarativa de pipelines en Git (GitOps), el control de acceso mediante Kubernetes RBAC, el aislamiento a nivel de namespace y la gestión mediante kubectl. Cada Step se ejecuta en un contenedor separado para lograr un aislamiento sólido.

</details>

---

2. ¿Cómo compartes datos entre Tasks en una Tekton Pipeline?
   - A) Pasarlos mediante variables de entorno
   - B) Compartir sistemas de archivos mediante Workspaces (PVC) y pasar datos pequeños mediante Results
   - C) Almacenarlos en ConfigMaps
   - D) Comunicación de red directa entre Tasks

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Compartir sistemas de archivos mediante Workspaces (PVC) y pasar datos pequeños mediante Results**

**Explicación:**
Workspaces permite compartir sistemas de archivos basados en PVC entre Tasks, ideal para patrones como clonar código fuente y luego compilar. Results pasa datos pequeños en forma de cadena (image tags, commit SHAs, etc.) entre Tasks, referenciados como `$(tasks.task-name.results.result-name)`.

</details>

---

3. ¿Qué hace el EventListener de Tekton Triggers?
   - A) Generar eventos y enviarlos a sistemas externos
   - B) Recibir solicitudes webhook y crear automáticamente PipelineRuns mediante TriggerBinding/TriggerTemplate
   - C) Monitorizar los resultados de ejecución de la pipeline
   - D) Sondear periódicamente repositorios Git

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Recibir solicitudes webhook y crear automáticamente PipelineRuns mediante TriggerBinding/TriggerTemplate**

**Explicación:**
El EventListener es un endpoint HTTP que recibe solicitudes webhook (GitHub Push, eventos PR, etc.). Interceptors valida/filtra la solicitud, TriggerBinding extrae parámetros del payload y TriggerTemplate crea un PipelineRun con esos parámetros.

</details>

---

4. ¿Qué característica de seguridad de la cadena de suministro proporciona Tekton Chains?
   - A) Escanear imágenes de contenedor en busca de vulnerabilidades
   - B) Firmar automáticamente los artefactos (imágenes) de TaskRun/PipelineRun y generar SLSA Provenance
   - C) Cifrar el tráfico de red
   - D) Generar automáticamente políticas RBAC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Firmar automáticamente los artefactos (imágenes) de TaskRun/PipelineRun y generar SLSA Provenance**

**Explicación:**
Tekton Chains firma automáticamente imágenes OCI con Cosign/Sigstore después de que se completa TaskRun y genera SLSA Provenance (metadatos de build, información de origen, pasos de build, etc.). Esto fortalece la seguridad de la cadena de suministro de software y permite verificar el origen y la integridad de las imágenes.

</details>

---

5. ¿Cuál es el propósito de las Tasks `finally` en una Tekton Pipeline?
   - A) Ejecutarse como la primera Task de la pipeline
   - B) Tareas de limpieza que siempre se ejecutan al final, independientemente del éxito o fallo de la pipeline
   - C) Tasks ejecutadas condicionalmente
   - D) Tasks que se ejecutan en paralelo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tareas de limpieza que siempre se ejecutan al final, independientemente del éxito o fallo de la pipeline**

**Explicación:**
Las Tasks `finally` se ejecutan después de que se completan todas las demás Tasks de la pipeline, independientemente de si tuvieron éxito o fallaron. Como se ejecutan incluso cuando falla el build, son ideales para limpiar recursos temporales, enviar notificaciones e informar resultados de pruebas. Es similar a un patrón try-catch-finally.

</details>

---

6. ¿Por qué separar CI/CD en una arquitectura de integración ArgoCD + Tekton?
   - A) Porque Tekton no admite CD
   - B) Separar las responsabilidades de CI (build/test) y CD (deploy) mejora la seguridad, la auditoría y el rollback
   - C) Porque ArgoCD no admite CI
   - D) Porque las herramientas tienen licencias diferentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Separar las responsabilidades de CI (build/test) y CD (deploy) mejora la seguridad, la auditoría y el rollback**

**Explicación:**
Tekton gestiona CI (source clone, test, build, image push) mientras que ArgoCD gestiona CD (deployment declarativo basado en Git). CI confirma el image tag en Git, y ArgoCD detecta este cambio para desplegar. Esto permite separar permisos de deployment, tener registros de auditoría basados en Git y realizar rollback declarativo.

</details>

---

7. ¿Cuál es un caso de uso del CEL Interceptor en Tekton?
   - A) Verificar firmas de GitHub
   - B) Filtrar y transformar payloads webhook mediante expresiones CEL (ramas específicas, rutas de archivos, etc.)
   - C) Verificar tokens de GitLab
   - D) Procesar eventos de Bitbucket

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Filtrar y transformar payloads webhook mediante expresiones CEL (ramas específicas, rutas de archivos, etc.)**

**Explicación:**
El CEL (Common Expression Language) Interceptor realiza filtrado y transformación sobre payloads webhook mediante expresiones CEL. Por ejemplo, `body.ref == 'refs/heads/main'` filtra solo los pushes a la rama main, o `body.commits.exists(c, c.modified.exists(f, f.startsWith('src/')))` activa la ejecución solo ante cambios en rutas específicas.

</details>

---

8. ¿Cuál es una estrategia de limpieza adecuada para Tekton PipelineRuns?
   - A) Conservar todos los PipelineRuns permanentemente
   - B) Configurar eliminación automática basada en TTL con distintos períodos de retención para éxitos/fallos a fin de gestionar recursos
   - C) Eliminarlos solo manualmente
   - D) Los PipelineRuns se eliminan automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar eliminación automática basada en TTL con distintos períodos de retención para éxitos/fallos a fin de gestionar recursos**

**Explicación:**
PipelineRuns y TaskRuns permanecen en etcd después de la ejecución, consumiendo almacenamiento. Usa la configuración de limpieza de Tekton (`keep`, `keep-since`) o scripts de limpieza basados en CronJob para eliminar automáticamente registros de ejecución antiguos. Las ejecuciones fallidas suelen conservarse durante más tiempo con fines de depuración.

</details>
