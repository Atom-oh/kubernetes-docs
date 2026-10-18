# GitOps

> **Última actualización**: October 12, 2026

## Tabla de contenido
- [¿Qué es GitOps?](#what-is-gitops)
- [Principios fundamentales](#core-principles)
- [Modelo push frente a pull](#push-vs-pull-model)
- [Descripción general de las herramientas GitOps](#gitops-tools-overview)
- [Guía para elegir una herramienta](#tool-selection-guide)
- [GitOps en Amazon EKS](#gitops-on-amazon-eks)
- [Primeros pasos](#getting-started)

## ¿Qué es GitOps?

GitOps es un marco operativo que aplica las prácticas recomendadas de DevOps para la automatización de la infraestructura (como el control de versiones, la colaboración, el cumplimiento y CI/CD) a la gestión de infraestructura. Weaveworks acuñó el término en 2017 y, desde entonces, se ha convertido en una metodología reconocida por CNCF para la implementación de aplicaciones nativas de la nube.

En esencia, GitOps usa repositorios Git como única fuente de verdad para la infraestructura declarativa y las configuraciones de las aplicaciones. Los cambios en el estado deseado se realizan mediante commits de Git, y los procesos automatizados garantizan que el estado real del sistema coincida con el estado declarado.

![Diagrama de arquitectura que muestra a un desarrollador enviando cambios a Git, que un agente GitOps observa y reconcilia en un clúster de Kubernetes, mientras el clúster informa su estado al agente.](../.gitbook/assets/en-gitops-readme-10.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-10.html)

### Historia y evolución

| Hito | Historial verificado del proyecto |
|---|---|
| Flux | Sandbox de CNCF en julio de 2019; incubación en marzo de 2021; graduación el 30 de noviembre de 2022 |
| Proyecto Argo | Incubación de CNCF en marzo de 2020; graduación el 6 de diciembre de 2022 |
| OpenGitOps | Publica principios con versiones; distingue los documentos publicados de la rama de trabajo main |

### Definición de CNCF OpenGitOps

El proyecto OpenGitOps define GitOps mediante cuatro principios:

1. **Declarativo**: Un sistema gestionado mediante GitOps debe expresar declarativamente su estado deseado
2. **Con versiones e inmutable**: El estado deseado se almacena de una manera que impone la inmutabilidad y el control de versiones, y conserva un historial completo de versiones
3. **Recuperado automáticamente**: Los agentes de software recuperan automáticamente las declaraciones del estado deseado desde el origen
4. **Reconciliado continuamente**: Los agentes de software observan continuamente el estado real del sistema e intentan aplicar el estado deseado

## Principios fundamentales

El historial de Git registra la configuración deseada. Una reversión de Git no restaura las migraciones de bases de datos, los datos eliminados ni el estado externo. La sincronización automatizada, prune y selfHeal de Argo CD son ajustes independientes; GitOps describe un bucle de control que intenta realizar la reconciliación.

### Configuración declarativa

Todo se define como código: infraestructura, aplicaciones, políticas y configuraciones. Esto permite:

- **Reproducibilidad**: La configuración con versiones, junto con los artefactos, secretos y datos disponibles, permite recrear el sistema
- **Auditabilidad**: Se conserva el historial de configuración; los registros de auditoría del entorno de ejecución y de la API aún deben recopilarse
- **Coherencia**: Bases compartidas con diferencias de entorno explícitas y revisadas

```yaml
# Example: Declarative application state
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
    version: v1.2.3
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: myregistry/web-app:v1.2.3
        ports:
        - containerPort: 8080
```

### Git como única fuente de verdad

Los repositorios Git almacenan el estado deseado de todo el sistema:

- **Configuraciones de aplicaciones**
- **Definiciones de infraestructura**
- **Políticas de seguridad**
- **Configuraciones específicas del entorno**

### Reconciliación automatizada

Los agentes GitOps continuamente:

1. Supervisan los cambios en el repositorio Git
2. Comparan el estado deseado con el estado real
3. Aplican cambios para que los sistemas cumplan con lo declarado
4. Informan del estado y las desviaciones

### Sistemas autorreparables

Los intentos de reconciliación dependen de la política de sync/self-heal, los permisos y el estado de salud. Por ejemplo, la sincronización automatizada y selfHeal de Argo CD requieren configuración; la instalación por sí sola no revierte todos los cambios manuales ni recupera los datos perdidos.

## Modelo push frente a pull

Compara la implementación tradicional push con GitOps basado en pull. Una canalización de `kubectl apply` que solo use CI no cumple por sí misma los principios de recuperación automática y reconciliación continua de OpenGitOps:

![Diagrama de flujo que contrasta CI/CD tradicional basado en push, donde una canalización aplica cambios directamente al clúster, con el modelo pull de GitOps, donde un agente supervisa Git y aplica los cambios por su cuenta.](../.gitbook/assets/en-gitops-readme-11.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-11.html)

### Modelo push

En el modelo push tradicional:
- La canalización de CI/CD tiene acceso directo al clúster
- Las credenciales se almacenan en el sistema de CI
- Los cambios se envían desde fuera del clúster

**Desventajas:**
- Requiere credenciales del clúster en el sistema de CI
- Es más difícil auditar quién realizó los cambios
- No detecta automáticamente las desviaciones

### Modelo pull (recomendado)

En el modelo pull de GitOps:
- El agente se ejecuta en el clúster de destino o en un clúster de gestión independiente
- El agente recupera los cambios desde Git
- Los agentes del clúster de gestión siguen necesitando acceso autorizado a la red/API de los destinos remotos

**Ventajas:**
- Puede reducir las credenciales del clúster de destino en CI; los agentes siguen teniendo derechos de acceso al origen y a la API
- Registro de auditoría completo en Git
- Detección y corrección automáticas de desviaciones
- Funciona detrás de firewalls

## Descripción general de las herramientas GitOps

### ArgoCD

[ArgoCD](argocd/README.md) es una herramienta declarativa de entrega continua para Kubernetes basada en GitOps.

**Características principales:**
- Interfaz web para la visualización
- Compatibilidad con varios clústeres
- Integración con SSO
- Funciones de reversión
- Supervisión del estado de salud
- ApplicationSet para la gestión de flotas

**Ideal para:** Equipos que quieren gestión visual, implementaciones en varios clústeres y funciones empresariales

### FluxCD

FluxCD es un conjunto de soluciones de entrega continua para Kubernetes, abierto y extensible.

**Características principales:**
- Ligero y modular
- Compatibilidad nativa con Helm y Kustomize
- Automatización de imágenes
- Compatibilidad con varios inquilinos
- Controladores de notificaciones

**Ideal para:** Equipos que prefieren soluciones ligeras, flujos de trabajo centrados en la CLI y automatización de imágenes

### Jenkins X / JayeX

Jenkins X / JayeX proporciona CI/CD para aplicaciones nativas de la nube en Kubernetes.

**Características principales:**
- Canalizaciones de CI/CD automatizadas
- Entornos de vista previa
- Promoción mediante GitOps
- Canalizaciones basadas en Tekton

**Evaluar para:** Flujos de trabajo integrados de CI/CD y entornos de vista previa; JayeX/Jenkins X / JayeX no es simplemente Jenkins con GitOps habilitado

### Matriz comparativa

| Requisito | Argo CD | Flux |
|---|---|---|
| Interfaz de usuario predeterminada | Interfaz web y CLI integradas | Controladores principales/CLI; interfaces de usuario opcionales del ecosistema |
| Comportamiento de Helm | helm template; Argo CD administra el ciclo de vida de los recursos | Helm Controller administra el ciclo de vida de las versiones de Helm |
| Actualizaciones de imágenes | Argo CD Image Updater independiente | Controladores Image Reflector/Automation opcionales |
| Compatibilidad con varios inquilinos | AppProjects, RBAC, restricciones de destino/origen | RBAC de Kubernetes, suplantación de ServiceAccount, restricciones entre espacios de nombres |
| Orígenes OCI | Orígenes OCI/Helm generales; validar capas y tipos de medios | Orígenes OCIRepository/Helm; validar la configuración de verificación/capas |
| Capacidad | Medir la cantidad de aplicaciones/clústeres y la carga de reconciliación | Medir los controladores, orígenes y la carga de reconciliación instalados |

## Guía para elegir una herramienta

### Elige ArgoCD cuando:

- Necesites un panel visual para las operaciones
- Se requiera administrar varios clústeres
- El SSO/RBAC empresarial sea importante
- El equipo prefiera flujos de trabajo basados en la interfaz de usuario
- Necesites ApplicationSet para la gestión de flotas

### Elige FluxCD cuando:

- Prefieras una arquitectura ligera y modular
- La automatización de imágenes sea un requisito prioritario
- Se prefiera un flujo de trabajo centrado en la CLI
- La limitación de recursos sea motivo de preocupación
- Necesites una integración estrecha con Helm Controller

### Marco de decisión

El diagrama ilustra preguntas para elegir, no capacidades exclusivas. Compara las funciones actuales, los límites de autorización y el costo operativo con la tabla y una prueba representativa.

![Árbol de decisión que orienta la elección entre ArgoCD, FluxCD o cualquiera de las dos herramientas en función de la necesidad de una interfaz web, el alcance de varios clústeres, los requisitos de RBAC, la prioridad de la automatización de imágenes y la prioridad de una huella ligera.](../.gitbook/assets/en-gitops-readme-12.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-12.html)

## GitOps en Amazon EKS

### Consideraciones específicas de EKS

Al implementar GitOps en Amazon EKS:

#### Integración con IAM

Una anotación de ServiceAccount por sí sola no establece acceso a IAM. Configura el proveedor OIDC/la política de confianza/la compatibilidad del SDK de IRSA o una asociación de EKS Pod Identity. Los permisos de la API de AWS y la autenticación/RBAC de la API de Kubernetes de destino son independientes.

Usa IAM Roles for Service Accounts (IRSA) para acceder de forma segura a la API de AWS:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitops-controller
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/GitOpsRole
```

#### Arquitectura multicuenta

![Diagrama de arquitectura que muestra ArgoCD en una cuenta de gestión leyendo desde Git y reconciliando clústeres EKS en cuentas independientes de desarrollo, pruebas y producción mediante conexiones entre cuentas.](../.gitbook/assets/en-gitops-readme-13.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-13.html)

#### Integración con servicios de AWS

GitOps puede administrar recursos de AWS mediante:

- **AWS Controllers for Kubernetes (ACK)**: CRD nativos de K8s para servicios de AWS
- **Crossplane**: Aprovisionamiento de recursos en varias nubes
- **Terraform Controller**: Gestión del estado de Terraform mediante GitOps

### Arquitectura recomendada

```
├── infrastructure/
│   ├── base/                    # Shared infrastructure
│   │   ├── vpc/
│   │   ├── eks/
│   │   └── iam/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── production/
├── applications/
│   ├── base/                    # Application base configs
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── production/
└── platform/
    ├── argocd/                  # GitOps tooling
    ├── monitoring/              # Observability stack
    └── security/                # Security policies
```

## Primeros pasos

### Inicio rápido con ArgoCD

Usa una versión compatible de Kubernetes, un espacio de nombres dedicado vacío y permisos de clúster para CRD/RBAC. Este ejemplo de instalación sin alta disponibilidad fija Argo CD en la versión 3.5.4; revisa la [guía de instalación](argocd/01-installation.md) completa antes de usarlo en producción. Debes cambiar las credenciales iniciales de administrador y eliminar el Secret de arranque después de usarlo.

1. **Instala ArgoCD:**
   ```bash
   kubectl create namespace argocd
   kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml
   ```

2. **Accede a la interfaz de usuario:**
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   ```

3. **Obtén la contraseña inicial:**
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   ```

Para obtener instrucciones detalladas sobre la configuración de ArgoCD, consulta la [documentación de ArgoCD](argocd/README.md).

### Inicio rápido con FluxCD

Prepara `GITHUB_ORG`/`GITOPS_REPOSITORY`, la autenticación de GitHub documentada y los permisos de Kubernetes. Bootstrap escribe en Git e instala los controladores del clúster. Añade `--personal` solo si se trata de un propietario personal y selecciona explícitamente los controladores opcionales de automatización de imágenes cuando sean necesarios.

1. **Instala Flux CLI:**
   ```bash
   curl --fail --location https://fluxcd.io/install.sh -o install-flux.sh
   # Review the script and select a supported version before running it.
   sudo bash install-flux.sh
   ```

2. **Inicia Flux:**
   ```bash
   flux bootstrap github \
     --owner="$GITHUB_ORG" \
     --repository="$GITOPS_REPOSITORY" \
     --path=clusters/my-cluster
   ```

Para obtener instrucciones detalladas sobre la configuración de FluxCD, consulta la documentación de FluxCD.

## Navegación de la sección

| Tema | Descripción |
|-------|-------------|
| [ArgoCD](argocd/README.md) | Guía completa de ArgoCD con instalación, aplicaciones, estrategias de sincronización y más |
| [FluxCD](02-fluxcd.md) | Configuración de FluxCD, controladores de origen y automatización de imágenes |

## Lecturas adicionales

- [Grupo de trabajo GitOps de CNCF](https://github.com/cncf/tag-app-delivery/tree/main/gitops-wg)
- [Proyecto OpenGitOps](https://opengitops.dev/)
- [Principios de GitOps](https://www.gitops.tech/)

## Cuestionario

Para poner a prueba lo que has aprendido, prueba los siguientes cuestionarios:
- [Cuestionario de ArgoCD](../quizzes/gitops/01-argocd-quiz.md)
- [Cuestionario de FluxCD](../quizzes/gitops/02-fluxcd-quiz.md)
- [Cuestionario comparativo de GitOps](../quizzes/gitops/03-gitops-comparison-quiz.md)

### Fuentes de consulta

- [Principios de OpenGitOps](https://github.com/open-gitops/documents/blob/v1.0.0/PRINCIPLES.md)
- [Madurez del proyecto Argo](https://www.cncf.io/projects/argo/)
- [Madurez del proyecto Flux](https://www.cncf.io/projects/flux/)
- [Orígenes OCI de Argo CD](https://argo-cd.readthedocs.io/en/stable/user-guide/oci/)
- [Sincronización automatizada de Argo CD](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Compatibilidad de Flux con varios inquilinos](https://fluxcd.io/flux/installation/configuration/multitenancy/)
- [Ecosistema de Flux](https://fluxcd.io/ecosystem/)
- [Proyecto JayeX](https://jayex.io/v3/about/)
