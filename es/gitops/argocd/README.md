# ArgoCD

> **Base de revisión**: Argo CD 3.5.2, Argo Rollouts 1.10.0; los manifiestos de Argo CD se actualizaron al parche 3.5.5 después de revisar las notas de versión (no se volvieron a ejecutar los ejemplos)
> **Última actualización**: 16 de octubre de 2026

## Tabla de contenido
- [¿Qué es ArgoCD?](#what-is-argocd)
- [Beneficios clave](#key-benefits)
- [Resumen de la arquitectura](#architecture-overview)
- [Conceptos principales](#core-concepts)
- [Navegación de las guías](#sub-guide-navigation)
- [Inicio rápido](#quick-start)
- [Compatibilidad de versiones](#version-compatibility)

## ¿Qué es ArgoCD? {#what-is-argocd}

ArgoCD es una herramienta declarativa de entrega continua basada en GitOps para Kubernetes. Automatiza el despliegue de aplicaciones en clústeres de Kubernetes al sincronizar el estado deseado definido en repositorios Git con el estado real del clúster.

Argo CD forma parte del proyecto Argo de la CNCF, que alcanzó el nivel Graduated. Su adopción, por sí sola, no demuestra que sea adecuado para un requisito concreto de seguridad o disponibilidad.

![Diagrama de arquitectura: el plano de control de ArgoCD obtiene manifiestos de Git, Helm y OCI mediante su Repo Server; el Application Controller reconcilia y sincroniza los manifiestos con los clústeres de Kubernetes administrados; los usuarios acceden al API Server desde la interfaz web, la CLI o la API gRPC.](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## Beneficios clave {#key-benefits}

### Nativo de GitOps

- **Git como única fuente de verdad**: todas las configuraciones de aplicaciones se almacenan en Git
- **Despliegues declarativos**: define el estado deseado y ArgoCD se encarga del resto
- **Pista de auditoría**: historial completo de los cambios mediante commits de Git
- **Reversión**: vuelve a desplegar revisiones de configuración conservadas; la recuperación de bases de datos y estado externo es independiente

### Administración de varios clústeres

- **Control centralizado**: administra cientos de clústeres desde una sola instancia de ArgoCD
- **ApplicationSet**: despliegues en varios clústeres basados en plantillas
- **Cluster Generator**: selección dinámica de clústeres según sus etiquetas

### Apto para entornos empresariales

- **RBAC**: control de acceso basado en roles con permisos detallados
- **Integración de SSO**: OIDC directo o conectores Dex compatibles con otros proveedores de identidad
- **Multitenencia**: aislamiento basado en proyectos
- **Alta disponibilidad**: despliegue de alta disponibilidad listo para producción

### Experiencia para desarrolladores

- **Interfaz web**: administración visual y supervisión de aplicaciones
- **CLI**: interfaz de línea de comandos completa
- **Notificaciones**: integraciones con Slack, Teams, correo electrónico y webhooks
- **Supervisión del estado**: comprobaciones de estado integradas y personalizadas

## Resumen de la arquitectura {#architecture-overview}

### Componentes principales

| Componente | Descripción | Réplicas (alta disponibilidad) |
|-----------|-------------|---------------|
| **API Server** | Gestiona las solicitudes a la API, la autenticación y RBAC | 2 o más |
| **Repository Server** | Clona repositorios, genera manifiestos y guarda resultados en caché | 2 o más |
| **Application Controller** | Supervisa las aplicaciones y reconcilia su estado | 2 o más (dividido en shards) |
| **Redis** | Capa de caché para Repo Server y el controlador | 3 (alta disponibilidad) |
| **Dex** | Agente de identidad opcional; no se consigue un escalado seguro agregando réplicas al almacenamiento en memoria incluido | 1 en el paquete estándar |
| **Notification Controller** | Envía notificaciones sobre eventos | 1 o más |
| **ApplicationSet Controller** | Administra los recursos ApplicationSet | 1 o más |

### Flujo de datos

![Diagrama de secuencia: un usuario crea una aplicación de ArgoCD mediante el API Server, que renderiza los manifiestos con Repo Server; después, el Application Controller compara repetidamente el estado deseado con el real en Kubernetes y aplica cambios cuando detecta desviaciones, dentro de un bucle de reconciliación.](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## Conceptos principales {#core-concepts}

### Application

El CRD Application es el recurso principal de ArgoCD. Define:
- **Origen**: de dónde obtener los manifiestos (repositorio Git, chart de Helm u OCI)
- **Destino**: dónde desplegarlos (clúster y espacio de nombres)
- **Política de sincronización**: cómo gestionar la sincronización

### Project

Los proyectos agrupan recursos de forma lógica y controlan el acceso:
- Restringen los repositorios que se pueden usar
- Limitan los clústeres y espacios de nombres de destino
- Definen los recursos permitidos y denegados

### ApplicationSet

ApplicationSet permite administrar varias aplicaciones desde una sola definición mediante generadores:
- **List Generator**: lista estática de valores
- **Cluster Generator**: selecciona clústeres registrados
- **Git Generator**: examina directorios y archivos del repositorio
- **Matrix/Merge**: combina varios generadores

### Sync

La sincronización hace que el estado del clúster coincida con el estado deseado:
- **Sincronización manual**: la inicia el usuario
- **Sincronización automática**: se inicia cuando cambia Git
- **Autorreparación**: corrige automáticamente las desviaciones
- **Poda**: elimina los recursos huérfanos

## Navegación de las guías {#sub-guide-navigation}

| Guía | Descripción |
|-------|-------------|
| [Instalación](01-installation.md) | Métodos de instalación, configuración de CLI, alta disponibilidad e integración con EKS |
| [Aplicaciones](02-applications.md) | CRD Application, tipos de origen, comprobaciones de estado, hooks y App of Apps |
| [Estrategias de sincronización](03-sync-strategies.md) | Políticas de sincronización, waves, ventanas, comparación de diferencias y configuración de reintentos |
| [ApplicationSets](04-applicationsets.md) | Todos los generadores, plantillas, sincronización progresiva y patrones para varios clústeres |
| [Gestión del tráfico](05-traffic-management.md) | Argo Rollouts, blue-green, canary, análisis e integración con ingress |
| [Proyectos y RBAC](06-projects-rbac.md) | AppProject, políticas RBAC, multiinquilinato y tokens JWT |
| [Seguridad](07-security.md) | Integración de SSO, gestión de secrets, TLS y registro de auditoría |
| [Notificaciones](08-notifications.md) | Servicios de notificación, desencadenadores, plantillas y suscripciones |
| [Prácticas recomendadas](09-best-practices.md) | Patrones de repositorio, ajuste de rendimiento, solución de problemas y consejos para EKS |
| [Análisis detallado de Rollouts Experiments](10-rollouts-experiment.md) | CRD Experiment, validación de ReplicaSet efímero y veredictos de AnalysisRun |

## Inicio rápido {#quick-start}

### 1. Instalar ArgoCD

Este ejemplo de evaluación es autoadministrado y no tiene alta disponibilidad. Prepara un clúster compatible, permisos para los CRD y RBAC, y un espacio de nombres dedicado y vacío. Para decidir sobre alta disponibilidad, autenticación y actualizaciones en producción, consulta la [guía de instalación](01-installation.md).

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml

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

### 4. Iniciar sesión mediante la CLI

Instala la CLI correspondiente al sistema operativo y la arquitectura, y verifica las sumas de comprobación de la versión como se indica en la [guía de instalación](01-installation.md). Mantén el reenvío de puertos en ejecución en otra terminal.

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. Desplegar la primera aplicación

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

## Compatibilidad de versiones {#version-compatibility}

La base de revisión es **Argo CD 3.5.2 / chart de Helm 10.8.4**; los manifiestos de ejemplo se actualizaron al parche 3.5.5 después de revisar las notas de versión (no se volvieron a ejecutar). El chart 10.8.4 todavía despliega Argo CD v3.5.2; la versión 3.5.5 aparece por primera vez en el chart 10.10.3. La versión de la aplicación y la del chart de instalación son distintas. Argo CD publica parches para las tres líneas menores más recientes; las anteriores están fuera de soporte (EOL).

### Combinaciones de Kubernetes probadas

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

Esta es la matriz de pruebas upstream registrada en el repositorio 3.5.5. Difiere de la restricción mínima `kubeVersion` de un chart, de los períodos de soporte de Kubernetes/EKS y de la política de versiones administradas de Argo CD. No hay una correspondencia uno a uno entre una versión menor de EKS y una versión menor de Argo CD.

### Versiones recientes

- 3.5.0: publicada el **4 de agosto de 2026**. Consulta la guía de migración para ver los cambios, incluido el renderizador Helm 4 del servidor.
- 3.5.1: publicada el 12 de agosto de 2026.
- 3.5.2: publicada el 27 de agosto de 2026.
- 3.5.3: publicada el 14 de septiembre de 2026. Correcciones de errores en comprobaciones de estado, estado de reintentos de sincronización e interfaz de usuario.
- 3.5.4: publicada el 6 de octubre de 2026. Es una **versión de parches de seguridad**: corrige cuatro problemas CRITICAL: ejecución de comandos en repo-server mediante una referencia remota de Kustomize y mediante `helmGlobals.configHome` de Kustomize; lectura de archivos por repo-server mediante una importación de Jsonnet; y elusión de restricciones de AppProject mediante los hooks PreDelete/PostDelete (CVE-2026-77459). Las mismas correcciones se retroportaron a v3.4.10/v3.3.15. Cambios de comportamiento: los builds de Kustomize ya no respetan `helmGlobals.configHome` y se rechazan los manifiestos OCI que superan 4 MiB; consulta las [notas de la versión](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4) antes de actualizar.
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1): primera versión candidata de la línea 3.6, publicada el 15 de septiembre de 2026. No es una versión base para producción.

### Actualización de octubre de 2026: comienza la planificación de Argo CD 4.0

Según la [publicación de la CNCF del 30 de septiembre](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/), la comunidad de Argo inició el proceso para definir la visión de Argo CD 4.0. ArgoCon North America 2026, un evento de jornada completa y dos sesiones simultáneas junto con KubeCon NA, comenzará con ponencias de los mantenedores sobre los avances recientes y las próximas versiones. Es una orientación inicial de la hoja de ruta; aún no hay compromisos sobre las funciones ni las fechas de 4.0.

### Argo Rollouts

Rollouts es un controlador independiente que se puede usar sin Argo CD. Esta revisión usa su documentación 1.10.0. Valida por separado los CRD y el controlador de Rollouts, los plugins de tráfico, Kubernetes y la integración de comprobaciones de estado de Argo CD; no deduzcas compatibilidad a partir de números de versión de productos distintos.

### Capacidad de Argo CD administrada por EKS

EKS Capability for Argo CD es un modelo operativo distinto de una instalación autoadministrada. Su configuración personalizada solo se aplica a las claves de argocd-cm **compatibles**, en el espacio de nombres configurado para la capacidad y con la etiqueta `app.kubernetes.io/part-of: argocd`. Las claves o flags no compatibles se ignoran; no supongas que están disponibles las bibliotecas Lua estándar ni plugins de ejecución arbitraria. Consulta la [guía de configuración administrada](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html).

## Próximos pasos

1. **[Guía de instalación](01-installation.md)**: configura ArgoCD para producción
2. **[Guía de aplicaciones](02-applications.md)**: aprende sobre el CRD Application
3. **[Guía de ApplicationSets](04-applicationsets.md)**: despliegues en varios clústeres

## Recursos

- [Documentación oficial de ArgoCD](https://argo-cd.readthedocs.io/)
- [Repositorio de ArgoCD en GitHub](https://github.com/argoproj/argo-cd)
- [Documentación de Argo Rollouts](https://argoproj.github.io/argo-rollouts/)
- [Página del proyecto Argo de la CNCF](https://www.cncf.io/projects/argo/)

## Cuestionario

Para comprobar lo aprendido, prueba el [cuestionario de instalación de ArgoCD](../../quizzes/gitops/argocd/01-installation-quiz.md).

### Fuentes de revisión versionadas

- [Versiones de Kubernetes probadas con Argo CD 3.5.5](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/tested-kubernetes-versions.md)
- [Política de soporte de versiones](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/developer-guide/release-process-and-cadence.md)
- [Versión 3.5.0](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [Versión 3.5.2](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [Versión 3.5.3](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [Versión 3.5.4](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.10.3 (primer chart con Argo CD 3.5.5)](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.10.3)
- [Comportamiento de los componentes en alta disponibilidad](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/high_availability.md)
