# ArgoCD

> **Base de revisión**: Argo CD 3.5.2, Argo Rollouts 1.10.0; los manifiestos de Argo CD se actualizaron para fijar la versión de parche 3.5.5 tras revisar las notas de la versión (no se volvieron a ejecutar los ejemplos)
> **Última actualización**: 19 de octubre de 2026

## Tabla de contenidos
- [¿Qué es ArgoCD?](#what-is-argocd)
- [Ventajas principales](#key-benefits)
- [Descripción general de la arquitectura](#architecture-overview)
- [Conceptos básicos](#core-concepts)
- [Navegación por las guías](#sub-guide-navigation)
- [Inicio rápido](#quick-start)
- [Compatibilidad de versiones](#version-compatibility)

## ¿Qué es ArgoCD?

ArgoCD es una herramienta declarativa de entrega continua basada en GitOps para Kubernetes. Automatiza el despliegue de aplicaciones en clústeres de Kubernetes al sincronizar el estado deseado definido en repositorios Git con el estado real del clúster.

Argo CD forma parte del proyecto Argo de la CNCF, que se graduó. La adopción por sí sola no demuestra que sea adecuada para un requisito de seguridad o disponibilidad particular.

![Diagrama de arquitectura que muestra el plano de control de ArgoCD obteniendo manifiestos de Git, Helm y fuentes OCI a través de su Repo Server, mientras el Application Controller reconcilia y sincroniza esos manifiestos en clústeres de Kubernetes administrados, y los usuarios acceden al API Server a través de la interfaz web, la CLI o la API gRPC.](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## Ventajas principales

### Nativo de GitOps

- **Git como única fuente de verdad**: todas las configuraciones de las aplicaciones se almacenan en Git
- **Despliegues declarativos**: define el estado deseado y ArgoCD se encarga del resto
- **Registro de auditoría**: historial completo de todos los cambios mediante confirmaciones de Git
- **Reversión**: vuelve a desplegar revisiones de configuración conservadas; la recuperación de bases de datos y estados externos es independiente

### Administración de varios clústeres

- **Control centralizado**: administra cientos de clústeres desde una sola instancia de ArgoCD
- **ApplicationSet**: despliegues en varios clústeres basados en plantillas
- **Generador de clústeres**: selección dinámica de clústeres según sus etiquetas

### Preparado para empresas

- **RBAC**: control de acceso basado en roles con permisos detallados
- **Integración con SSO**: OIDC directo o conectores Dex compatibles con otros proveedores de identidad
- **Multiinquilinato**: aislamiento basado en proyectos
- **Alta disponibilidad**: despliegue de alta disponibilidad listo para producción

### Experiencia de desarrollo

- **Interfaz web**: administración y supervisión visuales de aplicaciones
- **CLI**: interfaz de línea de comandos con todas las funciones
- **Notificaciones**: integraciones con Slack, Teams, correo electrónico y webhooks
- **Supervisión del estado**: comprobaciones de estado integradas y personalizadas

## Descripción general de la arquitectura

### Componentes principales

| Componente | Descripción | Réplicas (HA) |
|-----------|-------------|---------------|
| **API Server** | Gestiona todas las solicitudes a la API, la autenticación y RBAC | 2+ |
| **Repository Server** | Clona repositorios, genera manifiestos y almacena en caché los resultados | 2+ |
| **Application Controller** | Supervisa las aplicaciones y reconcilia el estado | 2+ (fragmentado) |
| **Redis** | Capa de caché para el servidor de repositorios y el controlador | 3 (HA) |
| **Dex** | Agente de identidad opcional; no es seguro escalar el almacenamiento en memoria incluido agregando réplicas | 1 en el paquete estándar |
| **Notification Controller** | Envía notificaciones cuando se producen eventos | 1+ |
| **ApplicationSet Controller** | Administra recursos ApplicationSet | 1+ |

### Flujo de datos

![Diagrama de secuencia que muestra a un usuario creando una aplicación ArgoCD a través del API Server, que representa manifiestos mediante el Repo Server; después, el Application Controller compara repetidamente el estado deseado y el real con Kubernetes y aplica cambios cuando detecta divergencias, como parte de un ciclo de reconciliación.](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## Conceptos básicos

### Application

El CRD Application es el recurso principal de ArgoCD. Define:
- **Origen**: de dónde obtener los manifiestos (repositorio Git, chart de Helm, OCI)
- **Destino**: dónde realizar el despliegue (clúster y espacio de nombres)
- **Política de sincronización**: cómo gestionar la sincronización

### Project

Los proyectos proporcionan agrupación lógica y control de acceso:
- Restringen los repositorios que se pueden usar
- Limitan los clústeres y espacios de nombres de destino
- Definen los recursos permitidos o denegados

### ApplicationSet

ApplicationSet permite administrar varias aplicaciones desde una sola definición mediante generadores:
- **Generador de listas**: lista estática de valores
- **Generador de clústeres**: selecciona clústeres registrados
- **Generador de Git**: explora directorios y archivos de repositorios
- **Matriz/fusión**: combina varios generadores

### Sincronización

La sincronización hace que el estado del clúster coincida con el estado deseado:
- **Sincronización manual**: iniciada por el usuario
- **Sincronización automática**: automática cuando hay cambios en Git
- **Autorreparación**: corrige automáticamente las divergencias
- **Poda**: elimina los recursos huérfanos

## Navegación por las guías

| Guía | Descripción |
|-------|-------------|
| [Instalación](01-installation.md) | Métodos de instalación, configuración de la CLI, configuración de HA e integración con EKS |
| [Aplicaciones](02-applications.md) | CRD Application, tipos de origen, comprobaciones de estado, hooks y App of Apps |
| [Estrategias de sincronización](03-sync-strategies.md) | Políticas de sincronización, waves, ventanas, comparación de diferencias y configuración de reintentos |
| [ApplicationSets](04-applicationsets.md) | Todos los generadores, plantillas, sincronización progresiva y patrones para varios clústeres |
| [Administración del tráfico](05-traffic-management.md) | Argo Rollouts, blue-green, canary, análisis e integración con ingress |
| [Proyectos y RBAC](06-projects-rbac.md) | AppProject, políticas RBAC, multiinquilinato y tokens JWT |
| [Seguridad](07-security.md) | Integración con SSO, administración de secretos, TLS y registro de auditoría |
| [Notificaciones](08-notifications.md) | Servicios de notificación, activadores, plantillas y suscripciones |
| [Prácticas recomendadas](09-best-practices.md) | Patrones de repositorio, optimización del rendimiento, resolución de problemas y consejos para EKS |
| [Análisis detallado de los experimentos de Rollouts](10-rollouts-experiment.md) | CRD Experiment, validación de ReplicaSet efímeros y veredictos de AnalysisRun |

## Inicio rápido

### 1. Instalar ArgoCD

Este es un ejemplo de evaluación autoadministrado, sin alta disponibilidad. Prepara un clúster compatible, permisos para CRD/RBAC y un espacio de nombres dedicado y vacío; consulta la [guía de instalación](01-installation.md) para tomar decisiones de producción sobre HA, autenticación y actualizaciones.

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

### 2. Acceder a la interfaz de usuario

```bash
# Port forward to access locally
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### 3. Obtener la contraseña inicial

```bash
# Retrieve the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

### 4. Iniciar sesión mediante la CLI

Instala la CLI correspondiente al sistema operativo y la arquitectura, y verifica las sumas de comprobación de la versión como se indica en la [guía de instalación](01-installation.md). Mantén activo el reenvío de puertos en otra terminal.

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. Desplegar tu primera aplicación

```bash
# Create application via CLI
argocd app create guestbook \
  --repo https://github.com/argoproj/argocd-example-apps.git \
  --path guestbook \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default

# Sync the application
argocd app sync guestbook
```

O de forma declarativa:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## Compatibilidad de versiones

La base de revisión es **Argo CD 3.5.2 / Helm chart 10.8.4**; los ejemplos de manifiestos se actualizaron para usar el parche 3.5.5 tras revisar las notas de la versión (no se volvieron a ejecutar). Chart 10.8.4 sigue desplegando Argo CD v3.5.2; la versión 3.5.5 aparece por primera vez en chart 10.10.3. Las versiones de la aplicación y del chart de instalación son distintas. Argo CD aplica parches a las tres líneas de versiones menores más recientes; las líneas anteriores están fuera de servicio (EOL).

### Combinaciones de Kubernetes probadas

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

Esta es la matriz de pruebas upstream registrada en el repositorio 3.5.5. Difiere de la restricción de versión mínima de Kubernetes de un chart, de los períodos de compatibilidad de Kubernetes/EKS y de la política de versiones de Argo CD administrado. No existe una correspondencia biunívoca entre las versiones menores de EKS y las de Argo CD.

### Versiones recientes

- 3.5.0: publicada el **4 de agosto de 2026**. Consulta la guía de migración para conocer los cambios, incluido el renderizador Helm 4 del servidor.
- 3.5.1: publicada el 12 de agosto de 2026.
- 3.5.2: publicada el 27 de agosto de 2026.
- 3.5.3: publicada el 14 de septiembre de 2026. Correcciones de errores (comprobaciones de estado, estado de reintentos de sincronización e interfaz de usuario).
- 3.5.4: publicada el 6 de octubre de 2026. Una **versión de parche de seguridad**: corrige cuatro problemas CRÍTICOS, concretamente la ejecución de comandos en repo-server mediante una referencia remota de Kustomize y mediante un directorio de configuración Helm de Kustomize, la lectura de archivos de repo-server mediante una importación de Jsonnet y la elusión de las restricciones de AppProject mediante hooks PreDelete/PostDelete (CVE-2026-77459). Las mismas correcciones se retrointegraron en v3.4.10/v3.3.15. Cambios de comportamiento: las compilaciones de Kustomize ya no respetan `helmGlobals.configHome` y se rechazan los manifiestos OCI de más de 4 MiB; revisa las [notas de la versión](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4) antes de actualizar.
- 3.5.5: publicada el 12 de octubre de 2026. Una versión de parche con correcciones de errores (manifiestos obsoletos y una fuga de goroutines en repo-server después de un fallo de CMP, comportamiento de la caché OCI y más); v3.4.11/v3.3.16 se publicaron el mismo día. Consulta las [notas de la versión](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5).
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1): primera versión candidata de la línea 3.6, publicada el 15 de septiembre de 2026. No es una base para producción.
- [3.6.0-rc3](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3): versión candidata más reciente de la línea 3.6, publicada el 15 de octubre de 2026. Tampoco es una base para producción.

### Actualización de octubre de 2026: comienza la planificación de Argo CD 4.0

Según la [publicación de la CNCF del 30 de septiembre](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/), la comunidad de Argo ha comenzado el proceso de planificación de Argo CD 4.0, y ArgoCon North America 2026 (un evento de jornada completa y dos sesiones simultáneas, celebrado junto con KubeCon NA) comenzará con ponencias principales de los mantenedores sobre novedades recientes y próximas versiones. Esta es una orientación inicial de la hoja de ruta; todavía no se han confirmado las funciones ni los plazos de la versión 4.0.

### Argo Rollouts

Rollouts es un controlador independiente que puede usarse sin Argo CD. Esta revisión utiliza la documentación de la versión 1.10.0. Valida la integración entre los CRD y el controlador de Rollouts, los complementos de tráfico, Kubernetes y las comprobaciones de estado de Argo CD, en lugar de relacionar números de versión de productos que no guardan relación.

### Capacidad de Argo CD administrado en EKS

EKS Capability for Argo CD ofrece un modelo operativo distinto al de una instalación autoadministrada. Su configuración personalizada solo se aplica a las claves de argocd-cm **compatibles**, en el espacio de nombres configurado para la capacidad y con la etiqueta `app.kubernetes.io/part-of: argocd`. Las claves y los indicadores no compatibles se ignoran; no des por sentado que están disponibles las bibliotecas Lua estándar ni los complementos de ejecución arbitrarios. Consulta la [guía de configuración administrada](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html).

## Próximos pasos

1. **[Guía de instalación](01-installation.md)**: configura ArgoCD para producción
2. **[Guía de aplicaciones](02-applications.md)**: aprende sobre el CRD Application
3. **[Guía de ApplicationSets](04-applicationsets.md)**: despliegues en varios clústeres

## Recursos

- [Documentación oficial de ArgoCD](https://argo-cd.readthedocs.io/)
- [Repositorio de ArgoCD en GitHub](https://github.com/argoproj/argo-cd)
- [Documentación de Argo Rollouts](https://argoproj.github.io/argo-rollouts/)
- [Página del proyecto ArgoCD en la CNCF](https://www.cncf.io/projects/argo/)

## Cuestionario

Para comprobar lo que has aprendido, prueba el [cuestionario de instalación de ArgoCD](../../quizzes/gitops/argocd/01-installation-quiz.md).

### Fuentes de revisión por versión

- [Versiones de Kubernetes probadas con Argo CD 3.5.5](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/tested-kubernetes-versions.md)
- [Política de soporte de versiones](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/developer-guide/release-process-and-cadence.md)
- [Versión 3.5.0](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [Versión 3.5.2](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [Versión 3.5.3](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [Versión 3.5.4](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.10.3 (primer chart con Argo CD 3.5.5)](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.10.3)
- [Comportamiento de los componentes de HA](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/high_availability.md)
