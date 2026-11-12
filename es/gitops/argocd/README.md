# ArgoCD

> **Base de revisión**: Argo CD 3.5.2, Argo Rollouts 1.10.0; los manifiestos de Argo CD se actualizaron para fijar la versión de parche 3.5.5 tras revisar las notas de la versión (no se volvieron a ejecutar los ejemplos)
> **Última actualización**: 26 de octubre de 2026

## Tabla de contenido
- [¿Qué es ArgoCD?](#what-is-argocd)
- [Ventajas principales](#key-benefits)
- [Descripción general de la arquitectura](#architecture-overview)
- [Conceptos básicos](#core-concepts)
- [Navegación por las guías](#sub-guide-navigation)
- [Inicio rápido](#quick-start)
- [Compatibilidad entre versiones](#version-compatibility)

## ¿Qué es ArgoCD?

ArgoCD es una herramienta declarativa de entrega continua basada en GitOps para Kubernetes. Automatiza la implementación de aplicaciones en clústeres de Kubernetes mediante la sincronización del estado deseado definido en repositorios Git con el estado real del clúster.

Argo CD forma parte del proyecto Argo de la CNCF, que alcanzó el nivel Graduated. La adopción por sí sola no demuestra que sea adecuado para un requisito de seguridad o disponibilidad determinado.

![Diagrama de arquitectura que muestra cómo el plano de control de ArgoCD obtiene manifiestos de fuentes Git, Helm y OCI a través de su Repo Server, mientras el Application Controller los reconcilia y sincroniza con los clústeres de Kubernetes administrados; los usuarios acceden al API Server mediante la interfaz web, la CLI o la API gRPC.](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## Ventajas principales

### Nativo de GitOps

- **Git como única fuente de verdad**: todas las configuraciones de aplicaciones se almacenan en Git
- **Implementaciones declarativas**: se define el estado deseado y ArgoCD se encarga del resto
- **Registro de auditoría**: historial completo de todos los cambios mediante los commits de Git
- **Reversión**: volver a implementar revisiones de configuración conservadas; la recuperación de bases de datos y estados externos es independiente

### Administración de varios clústeres

- **Control centralizado**: administrar cientos de clústeres desde una sola instancia de ArgoCD
- **ApplicationSet**: implementaciones de varios clústeres basadas en plantillas
- **Generador de clústeres**: selección dinámica de clústeres según sus etiquetas

### Preparado para empresas

- **RBAC**: control de acceso detallado basado en roles
- **Integración con SSO**: OIDC directo o conectores de Dex compatibles con otros proveedores de identidad
- **Multitenencia**: aislamiento basado en proyectos
- **Alta disponibilidad**: implementación de alta disponibilidad preparada para producción

### Experiencia del desarrollador

- **Interfaz web**: administración y supervisión visual de aplicaciones
- **CLI**: interfaz de línea de comandos con todas las funciones
- **Notificaciones**: integraciones con Slack, Teams, correo electrónico y webhook
- **Supervisión del estado**: comprobaciones de estado integradas y personalizadas

## Descripción general de la arquitectura

### Componentes principales

| Componente | Descripción | Réplicas (HA) |
|-----------|-------------|---------------|
| **API Server** | Gestiona todas las solicitudes a la API, la autenticación y RBAC | 2+ |
| **Repository Server** | Clona repositorios, genera manifiestos y almacena en caché los resultados | 2+ |
| **Application Controller** | Supervisa aplicaciones y reconcilia el estado | 2+ (fragmentado) |
| **Redis** | Capa de almacenamiento en caché para el servidor de repositorios y el controlador | 3 (HA) |
| **Dex** | Agente de identidad opcional; el almacenamiento en memoria incluido no se escala de forma segura al añadir réplicas | 1 en el paquete estándar |
| **Notification Controller** | Envía notificaciones sobre eventos | 1+ |
| **ApplicationSet Controller** | Administra los recursos ApplicationSet | 1+ |

### Flujo de datos

![Diagrama de secuencia que muestra a un usuario creando una aplicación de ArgoCD mediante el API Server, que genera manifiestos a través del Repo Server; a continuación, el Application Controller compara repetidamente el estado deseado y el real con Kubernetes y aplica cambios cuando detecta divergencias, dentro de un bucle de reconciliación.](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## Conceptos básicos

### Application

El CRD Application es el recurso principal de ArgoCD. Define:
- **Origen**: de dónde obtener los manifiestos (repositorio Git, chart de Helm, OCI)
- **Destino**: dónde implementar (clúster y espacio de nombres)
- **Política de sincronización**: cómo gestionar la sincronización

### Project

Los proyectos ofrecen agrupación lógica y control de acceso:
- Restringir los repositorios que se pueden usar
- Limitar los clústeres y espacios de nombres de destino
- Definir los recursos permitidos o denegados

### ApplicationSet

ApplicationSet permite administrar varias aplicaciones a partir de una sola definición mediante generadores:
- **Generador de listas**: lista estática de valores
- **Generador de clústeres**: seleccionar clústeres registrados como destino
- **Generador de Git**: examinar directorios y archivos del repositorio
- **Matrix/Merge**: combinar varios generadores

### Sincronización

La sincronización hace que el estado del clúster coincida con el estado deseado:
- **Sincronización manual**: iniciada por el usuario
- **Sincronización automática**: automática cuando hay cambios en Git
- **Autorreparación**: corregir divergencias automáticamente
- **Poda**: eliminar recursos huérfanos

## Navegación por las guías

| Guía | Descripción |
|-------|-------------|
| [Instalación](01-installation.md) | Métodos de instalación, configuración de la CLI, configuración de alta disponibilidad e integración con EKS |
| [Aplicaciones](02-applications.md) | CRD Application, tipos de origen, comprobaciones de estado, hooks y App of Apps |
| [Estrategias de sincronización](03-sync-strategies.md) | Políticas de sincronización, waves, ventanas, comparación de diferencias y configuración de reintentos |
| [ApplicationSets](04-applicationsets.md) | Todos los generadores, plantillas, sincronización progresiva y patrones de varios clústeres |
| [Administración del tráfico](05-traffic-management.md) | Argo Rollouts, blue-green, canary, análisis e integración con ingress |
| [Proyectos y RBAC](06-projects-rbac.md) | AppProject, políticas RBAC, multitenencia y tokens JWT |
| [Seguridad](07-security.md) | Integración con SSO, administración de secretos, TLS y registro de auditoría |
| [Notificaciones](08-notifications.md) | Servicios de notificaciones, activadores, plantillas y suscripciones |
| [Prácticas recomendadas](09-best-practices.md) | Patrones de repositorios, optimización del rendimiento, solución de problemas y consejos para EKS |
| [Análisis detallado de experimentos de Rollouts](10-rollouts-experiment.md) | CRD Experiment, validación de ReplicaSet efímeros y veredictos de AnalysisRun |

## Inicio rápido

### 1. Instalar ArgoCD

Este es un ejemplo de evaluación autoadministrado sin alta disponibilidad. Prepare un clúster compatible, los permisos para CRD/RBAC y un espacio de nombres dedicado vacío; consulte la [guía de instalación](01-installation.md) para tomar decisiones sobre alta disponibilidad, autenticación y actualizaciones en producción.

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

Instale la CLI correspondiente al sistema operativo y la arquitectura, y verifique las sumas de comprobación de la versión como se indica en la [guía de instalación](01-installation.md). Mantenga activo el reenvío de puertos en otra terminal.

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. Implementar la primera aplicación

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

## Compatibilidad entre versiones

La base de revisión es **Argo CD 3.5.2 / chart de Helm 10.8.4**; los ejemplos de manifiestos se actualizaron para usar la versión de parche 3.5.5 tras revisar las notas de la versión (no se volvieron a ejecutar). El chart 10.8.4 sigue implementando Argo CD v3.5.2; la versión 3.5.5 se incluye por primera vez en el chart 10.10.3. Las versiones de la aplicación y del chart de instalación son distintas. Argo CD publica parches para las tres líneas menores más recientes; las líneas anteriores están fuera de soporte.

### Combinaciones de Kubernetes probadas

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

Esta es la matriz de pruebas upstream registrada en el repositorio 3.5.5. Difiere de la restricción kubeVersion mínima de un chart, de los periodos de soporte de Kubernetes/EKS y de la política de versiones de Argo CD administrado. No existe una correspondencia biunívoca entre las versiones menores de EKS y las versiones menores de Argo CD.

### Versiones recientes

- 3.5.0: publicada el **4 de agosto de 2026**. Consulte las instrucciones de migración para conocer cambios como el renderizador Helm 4 del servidor.
- 3.5.1: publicada el 12 de agosto de 2026.
- 3.5.2: publicada el 27 de agosto de 2026.
- 3.5.3: publicada el 14 de septiembre de 2026. Correcciones de errores (comprobaciones de estado, estado de reintento de sincronización e interfaz de usuario).
- 3.5.4: publicada el 6 de octubre de 2026. Una **versión con parches de seguridad**: corrige cuatro problemas CRÍTICOS: ejecución de comandos en repo-server mediante una referencia remota de Kustomize y mediante el directorio de configuración de Helm de Kustomize, lectura de archivos de repo-server mediante una importación de Jsonnet y elusión de las restricciones de AppProject mediante hooks PreDelete/PostDelete (CVE-2026-77459). Las mismas correcciones se retroportaron a v3.4.10/v3.3.15. Cambios de comportamiento: las compilaciones de Kustomize ya no respetan `helmGlobals.configHome` y se rechazan los manifiestos OCI de más de 4 MiB; revise las [notas de la versión](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4) antes de actualizar.
- 3.5.5: publicada el 12 de octubre de 2026. Una versión de parche con correcciones de errores (manifiestos obsoletos y una fuga de goroutines en repo-server tras un fallo de CMP, comportamiento de la caché OCI, entre otras); v3.4.11/v3.3.16 se publicaron el mismo día. Consulte las [notas de la versión](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5).
- 3.5.6: publicada el 20 de octubre de 2026. Una versión de parche con correcciones de errores; v3.4.12 (21 de octubre de 2026) y v3.3.17 (20 de octubre de 2026) se publicaron en el mismo periodo. Consulte las [notas de la versión](https://github.com/argoproj/argo-cd/releases/tag/v3.5.6).
- 3.3.18: publicada el 22 de octubre de 2026. Incluye una **corrección de seguridad** para la línea 3.3 que deja de confiar en los certificados de CA de eMudhra comprometidos (el compromiso de la CA intermedia, divulgado el 20 de octubre de 2026, se corrigió en todo el ecosistema). Consulte las [notas de la versión](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18).
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1): primera versión candidata de la línea 3.6, publicada el 15 de septiembre de 2026. No es una versión de referencia para producción.
- [3.6.0-rc3](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3): versión candidata de la línea 3.6, publicada el 15 de octubre de 2026. Tampoco es una versión de referencia para producción.
- [3.6.0-rc4](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4): versión candidata más reciente de la línea 3.6, publicada el 22 de octubre de 2026. Tampoco es una versión de referencia para producción.

### Actualización de octubre de 2026: comienza la definición de la visión de Argo CD 4.0

Según la [publicación de la CNCF del 30 de septiembre](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/), la comunidad Argo ha comenzado el proceso de definición de la visión para Argo CD 4.0, y ArgoCon North America 2026 (un evento de jornada completa con dos sesiones paralelas, celebrado junto con KubeCon NA) comenzará con ponencias principales de los responsables del proyecto sobre los avances recientes y las próximas versiones. Esta es una etapa inicial de orientación de la hoja de ruta; todavía no se han definido las funciones ni las fechas de la versión 4.0.

### Argo Rollouts

Rollouts es un controlador independiente que puede utilizarse sin Argo CD. Esta revisión utiliza su documentación 1.10.0. Valide los CRD y el controlador de Rollouts, los plugins de tráfico, Kubernetes y la integración de comprobaciones de estado de Argo CD, en lugar de asociar números de versión de productos que no guardan relación entre sí.

### Capacidad de Argo CD administrada de EKS

EKS Capability for Argo CD tiene un modelo operativo distinto al de una instalación autoadministrada. Su configuración personalizada solo se aplica a las claves de argocd-cm **compatibles**, en el espacio de nombres configurado para la capacidad y con la etiqueta `app.kubernetes.io/part-of: argocd`. Las claves y marcas no compatibles se ignoran; no suponga que están disponibles las bibliotecas Lua estándar ni los plugins de ejecución arbitrarios. Consulte la [guía de configuración administrada](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html).

En las pruebas de octubre de 2026, incluso el clúster local tuvo que registrarse con un Secret de clúster que usara su ARN de EKS, y la entrada de acceso creada automáticamente no pudo sincronizarse hasta que se asociaron tanto `AmazonEKSEditPolicy` como `AmazonEKSAdminViewPolicy`. El sondeo predeterminado de Git tardó entre 342 y 697 segundos desde el commit hasta que el estado pasó a Synced; un webhook de GitHub redujo el tiempo a unos 7 segundos. El inicio de sesión solo está disponible mediante IAM Identity Center; Notifications, CMP y `argocd admin` no están disponibles, y AWS elige la versión. Para consultar los permisos, las distribuciones de varios clústeres, la preparación para las versiones y la comparación con la modalidad autoadministrada, consulte [Capacidades de EKS](../../eks/13-eks-capabilities.md).

## Próximos pasos

1. **[Guía de instalación](01-installation.md)**: configurar ArgoCD para producción
2. **[Guía de aplicaciones](02-applications.md)**: aprender sobre el CRD Application
3. **[Guía de ApplicationSets](04-applicationsets.md)**: implementaciones en varios clústeres

## Recursos

- [Documentación oficial de ArgoCD](https://argo-cd.readthedocs.io/)
- [Repositorio de ArgoCD en GitHub](https://github.com/argoproj/argo-cd)
- [Documentación de Argo Rollouts](https://argoproj.github.io/argo-rollouts/)
- [Página del proyecto ArgoCD de la CNCF](https://www.cncf.io/projects/argo/)

## Cuestionario

Para comprobar lo que ha aprendido, pruebe el [cuestionario de instalación de ArgoCD](../../quizzes/gitops/argocd/01-installation-quiz.md).

### Fuentes de revisión por versión

- [Versiones de Kubernetes probadas con Argo CD 3.5.5](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/tested-kubernetes-versions.md)
- [Política de soporte de versiones](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/developer-guide/release-process-and-cadence.md)
- [Versión 3.5.0](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [Versión 3.5.2](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [Versión 3.5.3](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [Versión 3.5.4](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.10.3 (primer chart con Argo CD 3.5.5)](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.10.3)
- [Comportamiento de los componentes en alta disponibilidad](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/high_availability.md)
