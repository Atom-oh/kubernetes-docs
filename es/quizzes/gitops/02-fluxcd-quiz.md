# Cuestionario de FluxCD

Este cuestionario evalúa tu comprensión de FluxCD y sus componentes.

1. ¿Qué estado de CNCF tiene FluxCD?
   - A) Sandbox
   - B) Incubating
   - C) Graduated
   - D) Archived

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Graduated**

**Explicación:**
FluxCD se graduó de CNCF en noviembre de 2022, lo que indica que ha alcanzado la madurez y se adopta ampliamente en entornos de producción.

</details>

2. ¿Qué controller de FluxCD es responsable de obtener artefactos de repositorios Git?
   - A) Kustomize Controller
   - B) Helm Controller
   - C) Source Controller
   - D) Notification Controller

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Source Controller**

**Explicación:**
El Source Controller es responsable de obtener artefactos de fuentes externas, incluidos repositorios Git (GitRepository), repositorios Helm (HelmRepository), registros OCI (OCIRepository) y buckets S3 (Bucket).

</details>

3. ¿Qué CRD utiliza FluxCD para desplegar configuraciones de Kustomize?
   - A) Application
   - B) Kustomization
   - C) KustomizeConfig
   - D) Deployment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Kustomization**

**Explicación:**
El CRD Kustomization se utiliza para definir cómo se deben aplicar las superposiciones de Kustomize al clúster. Hace referencia a una fuente (GitRepository) y especifica la ruta a la configuración de Kustomize.

</details>

4. ¿Cómo gestiona FluxCD los despliegues de Helm chart?
   - A) Mediante el CRD Application
   - B) Mediante el CRD HelmRelease
   - C) Mediante helm CLI directamente
   - D) Helm no es compatible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante el CRD HelmRelease**

**Explicación:**
El CRD HelmRelease se utiliza para gestionar declarativamente los releases de Helm chart. Especifica la fuente del chart, la versión, los values y las políticas de actualización/rollback.

</details>

5. ¿Cuál es el propósito de ImageUpdateAutomation de FluxCD?
   - A) Analizar imágenes en busca de vulnerabilidades
   - B) Actualizar automáticamente los tags de imagen en Git cuando se detectan nuevas versiones
   - C) Crear imágenes de contenedor
   - D) Gestionar image pull secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Actualizar automáticamente los tags de imagen en Git cuando se detectan nuevas versiones**

**Explicación:**
ImageUpdateAutomation trabaja con ImageRepository e ImagePolicy para detectar nuevos tags de imágenes de contenedor y hacer commit automáticamente de las actualizaciones en el repositorio Git, lo que permite despliegues automatizados.

</details>

6. ¿Qué comando se utiliza para inicializar FluxCD en un clúster?
   - A) flux install
   - B) flux bootstrap
   - C) flux init
   - D) flux setup

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) flux bootstrap**

**Explicación:**
El comando `flux bootstrap` instala los componentes de FluxCD y configura el repositorio Git para gestionar el clúster. Es compatible con varios proveedores Git, como GitHub, GitLab y servidores Git genéricos.

</details>

7. ¿Cómo admite FluxCD la multi-tenancy?
   - A) Mediante Projects como ArgoCD
   - B) Mediante aislamiento de namespace y Kubernetes RBAC
   - C) La multi-tenancy no es compatible
   - D) Mediante un tenant de administración central

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante aislamiento de namespace y Kubernetes RBAC**

**Explicación:**
FluxCD admite multi-tenancy mediante el aislamiento de namespace, donde cada tenant tiene su propio namespace con recursos de Flux, combinado con Kubernetes RBAC nativo para el control de acceso.

</details>

8. ¿Cuál es el propósito de Notification Controller en FluxCD?
   - A) Enviar mensajes SMS
   - B) Gestionar eventos y enviar alertas a servicios externos
   - C) Gestionar únicamente webhooks de Git
   - D) Supervisar logs de Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar eventos y enviar alertas a servicios externos**

**Explicación:**
El Notification Controller gestiona tanto las notificaciones salientes (Alerts a Slack, Teams, etc.) como los webhooks entrantes (Receivers) que activan la reconciliación cuando ocurren eventos externos.

</details>
