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

### 2. ¿Cuál es una ventaja clave de HCP Terraform frente a Terraform autoalojado?

- A) Uso ilimitado gratuito
- B) Estado gestionado, ejecuciones y características de colaboración
- C) Mayor velocidad de ejecución
- D) Compatibilidad con más proveedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Estado gestionado, ejecuciones y características de colaboración**

**Explicación:**
HCP Terraform proporciona almacenamiento remoto gestionado del estado, ejecución de runs, colaboración en equipo, aplicación de políticas (Sentinel) y un registro privado de módulos. Estas funciones gestionadas reducen la carga operativa frente a una instalación autoalojada.

</details>

### 3. ¿En qué se diferencia FluxCD de ArgoCD en su arquitectura?

- A) FluxCD no tiene UI
- B) Ambos usan reconciliación, con distintas API, controladores y opciones de interfaz
- C) FluxCD solo admite Helm
- D) FluxCD requiere una base de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ambos usan reconciliación, con distintas API, controladores y opciones de interfaz**

**Explicación:**
Flux usa las API específicas de sus controladores, como GitRepository y Kustomization. Argo CD también tiene varios componentes y admite distintas topologías de despliegue. El uso de recursos y el comportamiento multiclúster dependen de la configuración, no de una clasificación arquitectónica universal.

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
image-reflector-controller examina los registros y evalúa ImagePolicies. El componente independiente image-automation-controller aplica esas selecciones a los archivos marcados y las confirma en Git. Esto permite automatizar por completo los despliegues cuando se publican imágenes nuevas, sin dejar de seguir los principios de GitOps.

</details>

### 5. ¿Cuál es la secuencia habitual de aplicación y fusión en Atlantis?

- A) La fusión de cualquier PR siempre aplica automáticamente Terraform
- B) Revisar el plan del PR, cumplir los requisitos, aplicar explícitamente el plan guardado y luego fusionar
- C) Fusionar primero e ignorar el plan guardado
- D) Un plan satisfactorio ya constituye una aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Revisar el plan del PR, cumplir los requisitos, aplicar explícitamente el plan guardado y luego fusionar**

**Explicación:** Atlantis aplica los cambios desde el flujo de trabajo del PR; fusionarlo no desencadena una aplicación por sí sola. La fusión automática opcional ocurre después de que las aplicaciones terminan correctamente. Revisa y vuelve a generar el plan si cambian los commits, y no permitas que un PR anule los requisitos impuestos por el servidor.

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
AIOps puede monitorizar métricas, detectar problemas en el despliegue green (tasas de error o latencia) y crear automáticamente un PR para cambiar los pesos del tráfico y volver a blue. La propuesta aún requiere comprobaciones de calidad de datos, aprobación autorizada y un ejecutor con permisos limitados que vuelva a verificar el estado actual, la capacidad y la salud del destino. Una anomalía o la mera apertura de un PR no autoriza a cambiar el tráfico.

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

### 9. ¿Qué afirmación sobre la multitenencia es correcta?

- A) Argo CD siempre es más seguro porque tiene AppProjects
- B) Un namespace de Flux por sí solo completa el aislamiento de tenants
- C) Ambos requieren configurar deliberadamente las fuentes, identidades, RBAC y límites de recursos
- D) La automatización de imágenes también analiza vulnerabilidades

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ambos requieren configurar deliberadamente las fuentes, identidades, RBAC y límites de recursos**

**Explicación:** AppProjects y las identidades de tenant de Flux limitan distintas partes de la reconciliación. Ninguno proporciona automáticamente todos los límites de red, autorización de Kubernetes o aislamiento de código no confiable. Evita que dos controladores administren los mismos campos de un recurso.

</details>

### 10. En HCP Terraform, ¿qué es una política Sentinel?

- A) Una estrategia de backup
- B) Un framework de policy-as-code para gobernanza y cumplimiento
- C) Un método de cifrado de estado
- D) Un sistema de versionado de módulos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un framework de policy-as-code para gobernanza y cumplimiento**

**Explicación:**
Sentinel es el marco de policy-as-code de HashiCorp que aplica reglas antes de que Terraform realice cambios. Las políticas pueden comprobar etiquetas, tipos de instancia, cifrado u otros requisitos modelados. Su efecto real depende del alcance del conjunto de políticas, su nivel de aplicación y cómo maneje valores ausentes o desconocidos; un ejemplo no cubre automáticamente todos los recursos.

</details>
