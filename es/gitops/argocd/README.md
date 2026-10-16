# ArgoCD

> **Referencia de revisión**: Argo CD 3.5.2, Argo Rollouts 1.10.0; los pines de los manifiestos de Argo CD se actualizaron al parche 3.5.4 tras revisar las notas de la versión (los ejemplos no se volvieron a ejecutar)
> **Última actualización**: October 12, 2026

## Tabla de contenidos
- [¿Qué es ArgoCD?](#what-is-argocd)
- [Beneficios clave](#key-benefits)
- [Descripción general de la arquitectura](#architecture-overview)
- [Conceptos principales](#core-concepts)
- [Navegación por las subguías](#sub-guide-navigation)
- [Inicio rápido](#quick-start)
- [Compatibilidad de versiones](#version-compatibility)

## ¿Qué es ArgoCD?

ArgoCD es una herramienta declarativa de entrega continua GitOps para Kubernetes. Automatiza el despliegue de aplicaciones en clústeres de Kubernetes al sincronizar el estado deseado definido en repositorios Git con el estado real del clúster.

Argo CD forma parte del proyecto Argo graduado de la CNCF. La adopción por sí sola no determina la idoneidad para un requisito de seguridad o disponibilidad concreto.

![Diagrama de arquitectura que muestra el plano de control de ArgoCD obteniendo manifiestos de fuentes Git, Helm y OCI a través de su Repo Server, mientras el Application Controller los reconcilia y sincroniza en clústeres de Kubernetes administrados, y los usuarios acceden al API Server mediante la interfaz web, CLI o la API gRPC.](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## Beneficios clave

### GitOps nativo

- **Git como única fuente de verdad**: Todas las configuraciones de aplicaciones se almacenan en Git
- **Despliegues declarativos**: Define el estado deseado; ArgoCD se ocupa del resto
- **Registro de auditoría**: Historial completo de todos los cambios mediante commits de Git
- **Rollback**: Vuelve a desplegar revisiones de configuración conservadas; la recuperación de la base de datos o del estado externo se gestiona por separado

### Gestión de múltiples clústeres

- **Control centralizado**: Gestiona cientos de clústeres desde una única instancia de ArgoCD
- **ApplicationSet**: Despliegues en múltiples clústeres basados en plantillas
- **Cluster Generator**: Selección dinámica de clústeres basada en etiquetas

### Preparado para empresas

- **RBAC**: Control de acceso detallado basado en roles
- **Integración de SSO**: OIDC directo o conectores Dex compatibles para otros proveedores de identidad
- **Multi-tenancy**: Aislamiento basado en proyectos
- **Alta disponibilidad**: Despliegue HA preparado para producción

### Experiencia de desarrollador

- **Interfaz web**: Gestión visual y monitoreo de aplicaciones
- **CLI**: Interfaz de línea de comandos con todas las funciones
- **Notificaciones**: Integraciones con Slack, Teams, correo electrónico y webhooks
- **Monitoreo de estado**: Comprobaciones de estado integradas y personalizadas

## Descripción general de la arquitectura

### Componentes principales

| Componente | Descripción | Réplicas (HA) |
|-----------|-------------|---------------|
| **API Server** | Gestiona todas las solicitudes de API, la autenticación y RBAC | 2+ |
| **Repository Server** | Clona repositorios, genera manifiestos y almacena resultados en caché | 2+ |
| **Application Controller** | Monitorea aplicaciones y reconcilia el estado | 2+ (fragmentado) |
| **Redis** | Capa de caché para el servidor de repositorios y el controlador | 3 (HA) |
| **Dex** | Broker de identidad opcional; el almacenamiento en memoria incluido no se puede escalar de forma segura agregando réplicas | 1 en el paquete estándar |
| **Notification Controller** | Envía notificaciones de eventos | 1+ |
| **ApplicationSet Controller** | Gestiona recursos ApplicationSet | 1+ |

### Flujo de datos

![Diagrama de secuencia que muestra a un usuario creando una aplicación de ArgoCD a través del API Server, que renderiza manifiestos mediante el Repo Server, tras lo cual el Application Controller compara repetidamente el estado deseado y el real con Kubernetes y aplica cambios ante desviaciones en un ciclo de reconciliación.](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## Conceptos principales

### Application

El CRD Application es el recurso principal de ArgoCD. Define:
- **Fuente**: De dónde obtener los manifiestos (repositorio Git, chart de Helm, OCI)
- **Destino**: Dónde desplegar (clúster y namespace)
- **Política de sincronización**: Cómo gestionar la sincronización

### Project

Los proyectos proporcionan agrupación lógica y control de acceso:
- Restringen los repositorios que se pueden utilizar
- Limitan los clústeres y namespaces de destino
- Definen los recursos permitidos o denegados

### ApplicationSet

ApplicationSet permite gestionar múltiples aplicaciones desde una única definición mediante generadores:
- **List Generator**: Lista estática de valores
- **Cluster Generator**: Selecciona los clústeres registrados como destino
- **Git Generator**: Explora directorios y archivos del repositorio
- **Matrix/Merge**: Combina múltiples generadores

### Sync

La sincronización hace que el estado del clúster coincida con el estado deseado:
- **Sincronización manual**: La inicia el usuario
- **Sincronización automática**: Automática al cambiar Git
- **Autocorrección**: Corrige automáticamente las desviaciones
- **Prune**: Elimina recursos huérfanos

## Navegación por las subguías

| Guía | Descripción |
|-------|-------------|
| [Instalación](01-installation.md) | Métodos de instalación, configuración de CLI, configuración HA, integración con EKS |
| [Aplicaciones](02-applications.md) | CRD Application, tipos de fuente, comprobaciones de estado, hooks, App of Apps |
| [Estrategias de sincronización](03-sync-strategies.md) | Políticas de sincronización, oleadas, ventanas, diferencias, configuración de reintentos |
| [ApplicationSets](04-applicationsets.md) | Todos los generadores, plantillas, sincronización progresiva, patrones para múltiples clústeres |
| [Gestión del tráfico](05-traffic-management.md) | Argo Rollouts, blue-green, canary, análisis, integración de ingress |
| [Proyectos y RBAC](06-projects-rbac.md) | AppProject, políticas RBAC, multi-tenancy, tokens JWT |
| [Seguridad](07-security.md) | Integración de SSO, gestión de secretos, TLS, registros de auditoría |
| [Notificaciones](08-notifications.md) | Servicios de notificación, triggers, plantillas, suscripciones |
| [Prácticas recomendadas](09-best-practices.md) | Patrones de repositorio, ajuste del rendimiento, resolución de problemas, consejos para EKS |
| [Análisis detallado de experimentos de Rollouts](10-rollouts-experiment.md) | CRD Experiment, validación efímera de ReplicaSet, veredictos de AnalysisRun |

## Inicio rápido

### 1. Instalar ArgoCD

Este es un ejemplo de evaluación autogestionado sin HA. Prepare un clúster compatible, permisos de CRD/RBAC y un namespace dedicado vacío; use la [guía de instalación](01-installation.md) para tomar decisiones de producción sobre HA, autenticación y actualizaciones.

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

### 2. Acceder a la interfaz

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

### 4. Iniciar sesión mediante CLI

Instale el CLI correspondiente a su SO/arquitectura y verifique las sumas de comprobación de la versión tal como se muestra en la [guía de instalación](01-installation.md). Mantenga el reenvío de puertos ejecutándose en otra terminal.

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. Desplegar su primera aplicación

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

La referencia revisada es **Argo CD 3.5.2 / chart de Helm 10.8.4**; los ejemplos de manifiestos se actualizaron al parche 3.5.4 tras revisar las notas de la versión (no se volvieron a ejecutar). El chart 10.8.4 sigue desplegando Argo CD v3.5.2; la versión 3.5.4 se publica por primera vez en el chart 10.9.7. Las versiones de la aplicación y del chart de instalación son diferentes. Argo CD aplica parches a las tres líneas menores más recientes; las líneas anteriores están al final de su vida útil.

### Combinaciones de Kubernetes probadas

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

Esta es la matriz de pruebas upstream registrada en el repositorio 3.5.4. Difiere de la restricción kubeVersion mínima de un chart, de las ventanas de soporte de Kubernetes/EKS y de la política de versiones administradas de Argo CD. No existe una asignación uno a uno entre versiones menores de EKS y versiones menores de Argo CD.

### Versiones recientes

- 3.5.0: publicada el **2026-08-04**. Consulte la guía de migración para los cambios, incluido el renderizador Helm 4 del servidor.
- 3.5.1: publicada el 2026-08-12.
- 3.5.2: publicada el 2026-08-27.
- 3.5.3: publicada el 2026-09-14. Correcciones de errores (comprobaciones de estado, estado de reintento de sincronización, interfaz).
- 3.5.4: publicada el 2026-10-06. Una **versión de parche de seguridad**: corrige cuatro problemas CRÍTICOS —ejecución de comandos en el repo-server mediante una referencia remota de Kustomize y mediante un directorio principal de configuración de Helm de Kustomize, lectura de archivos del repo-server mediante una importación de Jsonnet y restricciones de AppProject omitidas por hooks PreDelete/PostDelete (CVE-2026-77459)—, y las mismas correcciones se retroportaron en v3.4.10/v3.3.15. Cambios de comportamiento: las compilaciones de Kustomize ya no respetan `helmGlobals.configHome`, y se rechazan los manifiestos OCI de más de 4 MiB; revise las [notas de la versión](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4) antes de actualizar.
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1): primera versión candidata de la línea 3.6, publicada el 2026-09-15. No es una referencia para producción.

### Actualización de octubre de 2026: comienza la definición de visión para Argo CD 4.0

Según la [publicación de CNCF del 30 de septiembre](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/), la comunidad de Argo ha iniciado el proceso de definición de visión para Argo CD 4.0, y ArgoCon North America 2026 (un evento de día completo con dos pistas, organizado conjuntamente con KubeCon NA) comenzará con ponencias de los maintainers que cubrirán desarrollos recientes y próximas versiones. Esta es una orientación temprana de la hoja de ruta; las funciones y el calendario de 4.0 aún no están comprometidos.

### Argo Rollouts

Rollouts es un controlador independiente y puede utilizarse sin Argo CD. Esta revisión utiliza su documentación 1.10.0. Valide los CRD/controlador de Rollouts, los plugins de tráfico, Kubernetes y la integración de comprobaciones de estado de Argo CD, en lugar de asignar números de versión de productos no relacionados.

### Capacidad de Argo CD administrado de EKS

EKS Capability for Argo CD es un modelo operativo distinto de una instalación autogestionada. Su configuración personalizada se aplica únicamente a las claves de argocd-cm **compatibles**, en el namespace configurado para la capacidad y con la etiqueta `app.kubernetes.io/part-of: argocd`. Las claves y flags no compatibles se ignoran; no asuma que las bibliotecas Lua estándar o los plugins de ejecución arbitrarios están disponibles. Consulte la [guía de configuración administrada](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html).

## Próximos pasos

1. **[Guía de instalación](01-installation.md)**: Configure ArgoCD para producción
2. **[Guía de aplicaciones](02-applications.md)**: Aprenda sobre el CRD Application
3. **[Guía de ApplicationSets](04-applicationsets.md)**: Despliegues en múltiples clústeres

## Recursos

- [Documentación oficial de ArgoCD](https://argo-cd.readthedocs.io/)
- [Repositorio de GitHub de ArgoCD](https://github.com/argoproj/argo-cd)
- [Documentación de Argo Rollouts](https://argoproj.github.io/argo-rollouts/)
- [Página del proyecto ArgoCD de CNCF](https://www.cncf.io/projects/argo/)

## Cuestionario

Para poner a prueba lo que ha aprendido, pruebe el [cuestionario de instalación de ArgoCD](../../quizzes/gitops/argocd/01-installation-quiz.md).

### Fuentes de revisión versionadas

- [Versiones de Kubernetes probadas con Argo CD 3.5.4](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/tested-kubernetes-versions.md)
- [Política de soporte de versiones](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/developer-guide/release-process-and-cadence.md)
- [Versión 3.5.0](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [Versión 3.5.2](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [Versión 3.5.3](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [Versión 3.5.4](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.9.7 (primer chart con Argo CD 3.5.4)](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.9.7)
- [Comportamiento de los componentes HA](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/high_availability.md)