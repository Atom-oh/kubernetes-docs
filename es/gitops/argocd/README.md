# ArgoCD

> **Línea base revisada**: Argo CD 3.5.2, Argo Rollouts 1.10.0; los pines de manifiestos de Argo CD se actualizaron al parche 3.5.4 después de revisar las notas de la versión (los ejemplos no se volvieron a ejecutar)
> **Última actualización**: October 12, 2026

## Tabla de contenidos
- [¿Qué es ArgoCD?](#what-is-argocd)
- [Beneficios clave](#key-benefits)
- [Resumen de la arquitectura](#architecture-overview)
- [Conceptos principales](#core-concepts)
- [Navegación de subguías](#sub-guide-navigation)
- [Inicio rápido](#quick-start)
- [Compatibilidad de versiones](#version-compatibility)

## ¿Qué es ArgoCD?

ArgoCD es una herramienta declarativa de entrega continua GitOps para Kubernetes. Automatiza el Deployment de aplicaciones en clústeres de Kubernetes sincronizando el estado deseado definido en repositorios Git con el estado real del clúster.

Argo CD forma parte del proyecto Argo graduado de la CNCF. La adopción por sí sola no establece la idoneidad para un requisito concreto de seguridad o disponibilidad.

![Diagrama de arquitectura que muestra el plano de control de ArgoCD obteniendo manifiestos de fuentes Git, Helm y OCI a través de su Repo Server, con Application Controller reconciliándolos y sincronizándolos en clusters de Kubernetes administrados, mientras los usuarios llegan a API Server mediante la web UI, CLI o la API gRPC.](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## Beneficios clave

### GitOps nativo

- **Git como única fuente de verdad**: Todas las configuraciones de aplicaciones se almacenan en Git
- **Deployments declarativos**: Defina el estado deseado; ArgoCD se encarga del resto
- **Registro de auditoría**: Historial completo de todos los cambios mediante commits de Git
- **Reversión**: Vuelva a desplegar revisiones de configuración conservadas; la recuperación de la base de datos o del estado externo se realiza por separado

### Gestión de múltiples clústeres

- **Control centralizado**: Gestione cientos de clústeres desde una única instancia de ArgoCD
- **ApplicationSet**: Deployments de múltiples clústeres basados en plantillas
- **Generador de clústeres**: Selección dinámica de clústeres basada en etiquetas

### Preparado para empresas

- **RBAC**: Control de acceso detallado basado en roles
- **Integración de SSO**: OIDC directo o conectores Dex compatibles para otros proveedores de identidad
- **Multi-tenancy**: Aislamiento basado en proyectos
- **Alta disponibilidad**: Deployment HA preparado para producción

### Experiencia de desarrollador

- **Web UI**: Gestión y monitorización visual de aplicaciones
- **CLI**: Interfaz de línea de comandos con todas las funciones
- **Notificaciones**: Integraciones con Slack, Teams, correo electrónico y webhook
- **Monitorización de estado**: Comprobaciones de estado integradas y personalizadas

## Resumen de la arquitectura

### Componentes principales

| Componente | Descripción | Réplicas (HA) |
|-----------|-------------|---------------|
| **API Server** | Gestiona todas las solicitudes de API, la autenticación y RBAC | 2+ |
| **Repository Server** | Clona repositorios, genera manifiestos y almacena resultados en caché | 2+ |
| **Application Controller** | Monitoriza aplicaciones y reconcilia el estado | 2+ (fragmentado) |
| **Redis** | Capa de caché para el servidor de repositorios y el controlador | 3 (HA) |
| **Dex** | Agente de identidad opcional; el almacenamiento en memoria incluido no se escala de forma segura al añadir réplicas | 1 en el paquete estándar |
| **Notification Controller** | Envía notificaciones sobre eventos | 1+ |
| **ApplicationSet Controller** | Gestiona recursos ApplicationSet | 1+ |

### Flujo de datos

![Diagrama de secuencia que muestra a un usuario creando una aplicación ArgoCD mediante API Server, que renderiza manifiestos a través de Repo Server, seguido de Application Controller comparando repetidamente el estado deseado y real con Kubernetes y aplicando cambios ante desviaciones en un ciclo de reconciliación.](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## Conceptos principales

### Application

El CRD Application es el recurso principal de ArgoCD. Define:
- **Origen**: Dónde obtener los manifiestos (repositorio Git, chart Helm, OCI)
- **Destino**: Dónde realizar el Deployment (clúster y namespace)
- **Política de sincronización**: Cómo gestionar la sincronización

### Project

Los proyectos proporcionan agrupación lógica y control de acceso:
- Restringen qué repositorios se pueden utilizar
- Limitan los clústeres y namespaces de destino
- Definen los recursos permitidos/denegados

### ApplicationSet

ApplicationSet permite gestionar múltiples aplicaciones desde una única definición mediante generadores:
- **Generador de lista**: Lista estática de valores
- **Generador de clústeres**: Selecciona clústeres registrados como destino
- **Generador Git**: Explora directorios/archivos del repositorio
- **Matriz/Fusión**: Combina varios generadores

### Sync

La sincronización hace que el estado del clúster coincida con el estado deseado:
- **Sincronización manual**: Iniciada por el usuario
- **Sincronización automática**: Automática ante cambios en Git
- **Autorreparación**: Corrige la desviación automáticamente
- **Prune**: Elimina recursos huérfanos

## Navegación de subguías

| Guía | Descripción |
|-------|-------------|
| [Instalación](01-installation.md) | Métodos de instalación, configuración de CLI, configuración HA, integración con EKS |
| [Aplicaciones](02-applications.md) | CRD Application, tipos de origen, comprobaciones de estado, hooks, App of Apps |
| [Estrategias de sincronización](03-sync-strategies.md) | Políticas de sincronización, oleadas, ventanas, comparación de diferencias, configuración de reintentos |
| [ApplicationSets](04-applicationsets.md) | Todos los generadores, plantillas, sincronización progresiva, patrones de múltiples clústeres |
| [Gestión del tráfico](05-traffic-management.md) | Argo Rollouts, blue-green, canary, análisis, integración de ingress |
| [Proyectos y RBAC](06-projects-rbac.md) | AppProject, políticas RBAC, multi-tenancy, tokens JWT |
| [Seguridad](07-security.md) | Integración de SSO, gestión de secrets, TLS, registro de auditoría |
| [Notificaciones](08-notifications.md) | Servicios de notificación, desencadenadores, plantillas, suscripciones |
| [Prácticas recomendadas](09-best-practices.md) | Patrones de repositorio, ajuste de rendimiento, solución de problemas, consejos para EKS |
| [Análisis detallado de experimentos de Rollouts](10-rollouts-experiment.md) | CRD Experiment, validación efímera de ReplicaSet, veredictos de AnalysisRun |

## Inicio rápido

### 1. Instalar ArgoCD

Este es un ejemplo de evaluación autogestionado sin HA. Prepare un clúster compatible, permisos de CRD/RBAC y un namespace dedicado vacío; utilice la [guía de instalación](01-installation.md) para tomar decisiones de producción sobre HA, autenticación y actualización.

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

### 2. Acceder a la UI

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

Instale la CLI que corresponda con el SO/la arquitectura y verifique las sumas de comprobación de la versión como se indica en la [guía de instalación](01-installation.md). Mantenga el reenvío de puertos en ejecución en otra terminal.

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. Realizar el Deployment de su primera aplicación

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

La línea base revisada es **Argo CD 3.5.2 / Helm chart 10.8.4**; los ejemplos de manifiestos se actualizaron al parche 3.5.4 después de revisar las notas de la versión (no se volvieron a ejecutar). El chart 10.8.4 aún realiza el Deployment de Argo CD v3.5.2; la versión 3.5.4 se incluye por primera vez en el chart 10.9.7. Las versiones de la aplicación y del chart de instalación son diferentes. Argo CD aplica parches a las tres líneas minor más recientes; las líneas anteriores están EOL.

### Combinaciones de Kubernetes probadas

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

Esta es la matriz de pruebas upstream registrada en el repositorio 3.5.4. Difiere de la restricción mínima `kubeVersion` de un chart, las ventanas de soporte de Kubernetes/EKS y la política de versiones administradas de Argo CD. No existe una correspondencia uno a uno entre una versión minor de EKS y una versión minor de Argo CD.

### Versiones recientes

- 3.5.0: publicada el **2026-08-04**. Consulte la guía de migración para los cambios, incluido el renderizador Helm 4 del servidor.
- 3.5.1: publicada el 2026-08-12.
- 3.5.2: publicada el 2026-08-27.
- 3.5.3: publicada el 2026-09-14. Correcciones de errores (comprobaciones de estado, estado de reintento de sincronización, UI).
- 3.5.4: publicada el 2026-10-06. Correcciones de seguridad, incluidas cuatro calificadas como CRITICAL en el manejo de hooks de repo-server y AppProject. Las notas de la versión enumeran dos cambios potencialmente incompatibles: las compilaciones de Kustomize que renderizan charts Helm ya no respetan `helmGlobals.configHome`, y se rechazan los manifiestos OCI de más de 4 MiB. Consulte las versiones oficiales para conocer las líneas compatibles actuales.

### Argo Rollouts

Rollouts es un controlador independiente y puede utilizarse sin Argo CD. Esta revisión usa su documentación 1.10.0. Valide los CRD/controlador de Rollouts, los plugins de tráfico, Kubernetes y la integración de comprobaciones de estado de Argo CD en lugar de asignar números de versión de productos no relacionados.

### Capacidad de Argo CD administrada por EKS

EKS Capability for Argo CD es un modelo operativo distinto de una instalación autogestionada. Su configuración personalizada se aplica solo a claves **compatibles** de argocd-cm, en el namespace configurado para la capacidad y con la etiqueta `app.kubernetes.io/part-of: argocd`. Las claves/flags no compatibles se ignoran; no suponga que las bibliotecas Lua estándar o los plugins de ejecución arbitraria estén disponibles. Consulte la [guía de configuración administrada](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html).

## Próximos pasos

1. **[Guía de instalación](01-installation.md)**: Configure ArgoCD para producción
2. **[Guía de aplicaciones](02-applications.md)**: Aprenda sobre el CRD Application
3. **[Guía de ApplicationSets](04-applicationsets.md)**: Deployments de múltiples clústeres

## Recursos

- [Documentación oficial de ArgoCD](https://argo-cd.readthedocs.io/)
- [Repositorio de GitHub de ArgoCD](https://github.com/argoproj/argo-cd)
- [Documentación de Argo Rollouts](https://argoproj.github.io/argo-rollouts/)
- [Página del proyecto ArgoCD de CNCF](https://www.cncf.io/projects/argo/)

## Cuestionario

Para comprobar lo que ha aprendido, pruebe el [cuestionario de instalación de ArgoCD](../../quizzes/gitops/argocd/01-installation-quiz.md).

### Fuentes de revisión versionadas

- [Versiones de Kubernetes probadas con Argo CD 3.5.4](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/tested-kubernetes-versions.md)
- [Política de soporte de versiones](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/developer-guide/release-process-and-cadence.md)
- [Versión 3.5.0](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [Versión 3.5.2](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [Versión 3.5.3](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [Versión 3.5.4](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.9.7 (primer chart con Argo CD 3.5.4)](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.9.7)
- [Comportamiento de componentes HA](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/high_availability.md)
