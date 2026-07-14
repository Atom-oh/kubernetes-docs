# Cuestionario sobre automatización GitOps

> **Documento relacionado**: [Automatización GitOps](../../ops/05-gitops-automation.md)

## Preguntas de opción múltiple

### 1. ¿Qué es Atlantis en el contexto de la automatización de Terraform?

- A) Un proveedor de cloud
- B) Una herramienta de automatización de pull requests para Terraform
- C) Un registro de módulos de Terraform
- D) Un servicio de cifrado de archivos de estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una herramienta de automatización de pull requests para Terraform**

**Explicación:**
Atlantis es una aplicación autoalojada que escucha pull requests de Terraform y ejecuta `terraform plan` y `apply` automáticamente. Proporciona la salida del plan como comentarios en el PR y aplica flujos de trabajo de aprobación antes de aplicar cambios.

</details>

### 2. ¿Cuál es una ventaja clave de Terraform Cloud frente a Terraform autoalojado?

- A) Uso ilimitado gratuito
- B) Estado gestionado, ejecuciones y características de colaboración
- C) Mayor velocidad de ejecución
- D) Compatibilidad con más proveedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Estado gestionado, ejecuciones y características de colaboración**

**Explicación:**
Terraform Cloud proporciona almacenamiento de estado remoto gestionado, ejecución de runs, colaboración en equipo, aplicación de políticas (Sentinel) y un registro privado de módulos. Estas características gestionadas reducen la carga operativa en comparación con configuraciones autoalojadas.

</details>

### 3. ¿En qué se diferencia FluxCD de ArgoCD en su arquitectura?

- A) FluxCD no tiene UI
- B) FluxCD usa una arquitectura distribuida basada en pull, sin servidor central
- C) FluxCD solo admite Helm
- D) FluxCD requiere una base de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) FluxCD usa una arquitectura distribuida basada en pull, sin servidor central**

**Explicación:**
FluxCD ejecuta controladores directamente en cada cluster que hacen pull desde git, mientras que ArgoCD usa un modelo de servidor centralizado. El enfoque de FluxCD es más ligero y escala de forma natural en escenarios multi-cluster sin un hub central.

</details>

### 4. ¿Qué hace Flux Image Automation Controller?

- A) Construye imágenes de contenedor
- B) Escanea registros y actualiza git con nuevos tags de imagen
- C) Despliega imágenes en Kubernetes
- D) Gestiona secretos de pull de imágenes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Escanea registros y actualiza git con nuevos tags de imagen**

**Explicación:**
Image Automation Controller observa registros de contenedores en busca de nuevos tags de imagen y luego confirma automáticamente actualizaciones en repositorios git. Esto permite despliegues totalmente automatizados cuando se publican nuevas imágenes, manteniendo los principios de GitOps.

</details>

### 5. En un flujo de trabajo de Atlantis, ¿qué ocurre cuando un PR se aprueba y se fusiona?

- A) Terraform plan se ejecuta automáticamente
- B) Atlantis ejecuta terraform apply sobre el código fusionado
- C) El PR se cierra sin acción
- D) Se crea una nueva rama

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Atlantis ejecuta terraform apply sobre el código fusionado**

**Explicación:**
Cuando se configura con auto-apply o después de una aprobación explícita, Atlantis ejecuta `terraform apply` después de fusionar el PR. Esto garantiza que los cambios de infraestructura se apliquen solo después de una revisión y aprobación de código, manteniendo el control de cambios.

</details>

### 6. ¿Cuál es un beneficio clave de AIOps en los flujos de trabajo GitOps?

- A) Eliminar la necesidad de git
- B) Detección automatizada de anomalías y recomendaciones de respuesta
- C) Builds de contenedores más rápidos
- D) Costos de almacenamiento reducidos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Detección automatizada de anomalías y recomendaciones de respuesta**

**Explicación:**
AIOps aplica machine learning para detectar anomalías en métricas y logs, correlacionar eventos y recomendar o automatizar respuestas. En GitOps, esto puede incluir la generación automática de PRs para cambios de escalado o ajustes de peso del tráfico.

</details>

### 7. ¿Cómo puede AIOps automatizar cambios de peso del tráfico en despliegues blue/green?

- A) Modificando directamente la configuración del load balancer
- B) Detectando anomalías y creando PRs para actualizar configuraciones de peso en git
- C) Reiniciando pods fallidos
- D) Cambiando registros DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Detectando anomalías y creando PRs para actualizar configuraciones de peso en git**

**Explicación:**
AIOps puede monitorizar métricas, detectar problemas en el despliegue green (tasas de error, latencia) y crear automáticamente un PR para devolver los pesos de tráfico a blue. Esto mantiene los principios de GitOps y, al mismo tiempo, permite una respuesta automatizada a incidentes.

</details>

### 8. ¿Cuál es el propósito del recurso GitRepository de Flux?

- A) Crear repositorios git
- B) Definir una fuente git que Flux monitoriza en busca de cambios
- C) Hacer backup de recursos de Kubernetes en git
- D) Gestionar credenciales de git

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir una fuente git que Flux monitoriza en busca de cambios**

**Explicación:**
GitRepository es un recurso personalizado de Flux que especifica una URL de repositorio git, una rama y un intervalo de sondeo. Los controladores de Flux observan estas fuentes y activan la reconciliación cuando se detectan cambios.

</details>

### 9. Al comparar FluxCD y ArgoCD, ¿qué afirmación es correcta?

- A) ArgoCD tiene mejor multi-tenancy mediante su modelo Project
- B) FluxCD tiene una UI integrada más completa
- C) ArgoCD usa GitOps mientras que FluxCD no
- D) FluxCD requiere bases de datos externas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) ArgoCD tiene mejor multi-tenancy mediante su modelo Project**

**Explicación:**
El recurso Project de ArgoCD proporciona multi-tenancy robusta con control de acceso granular sobre repositorios, clusters y namespaces. FluxCD logra multi-tenancy mediante aislamiento por namespace, pero con un control menos granular.

</details>

### 10. En Terraform Cloud, ¿qué es una política Sentinel?

- A) Una estrategia de backup
- B) Un framework de policy-as-code para gobernanza y cumplimiento
- C) Un método de cifrado de estado
- D) Un sistema de versionado de módulos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un framework de policy-as-code para gobernanza y cumplimiento**

**Explicación:**
Sentinel es el framework de policy-as-code de HashiCorp que aplica reglas antes de que Terraform aplique cambios. Las políticas pueden exigir etiquetas, restringir tipos de instancia, requerir cifrado o aplicar cualquier requisito personalizado de cumplimiento.

</details>
