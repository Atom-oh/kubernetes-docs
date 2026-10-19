# Comparación de herramientas GitOps

> **Última actualización**: 11 de septiembre de 2026

Esta guía compara herramientas GitOps, con especial atención a ArgoCD y FluxCD, dos de las opciones más populares del ecosistema de Kubernetes.

## Descripción general

GitOps es un marco operativo que aplica a la automatización de infraestructura las prácticas recomendadas de DevOps para el desarrollo de aplicaciones. Las dos herramientas GitOps líderes en el ecosistema CNCF son:

- **ArgoCD**: herramienta declarativa de entrega continua basada en GitOps para Kubernetes
- **FluxCD**: conjunto de soluciones de entrega continua y progresiva para Kubernetes

Ambos son proyectos graduados de CNCF, lo que indica madurez y amplia adopción.

## ArgoCD frente a FluxCD: comparación directa

### Filosofía y diseño

| Aspecto | ArgoCD | FluxCD |
|--------|--------|--------|
| **Arquitectura** | Servidores API y de repositorio separados, controlador de aplicaciones y componentes auxiliares | Conjunto modular de controladores |
| **Configuración** | CRD centrados en aplicaciones | CRD centrados en fuentes |
| **Interfaz de usuario** | Interfaz web completa incluida | Orientado a CLI, sin interfaz integrada |
| **Enfoque de aprendizaje** | Aplicaciones, AppProjects y flujos de trabajo en la interfaz | Relaciones entre los controladores Source, Kustomization y HelmRelease |
| **Modelo de despliegue** | GitOps basado en extracción (pull) | GitOps basado en extracción (pull) |

### Comparación de funciones

| Función | ArgoCD | FluxCD |
|---------|--------|--------|
| **Interfaz web** | Integrada y con numerosas funciones | No forma parte del núcleo; evalúa las interfaces del ecosistema con mantenimiento activo |
| **CLI** | CLI `argocd` | CLI `flux` |
| **Multitenencia** | Proyectos con RBAC | Aislamiento por espacio de nombres |
| **Varios clústeres** | Compatibilidad nativa | Compatibilidad nativa |
| **Compatibilidad con Helm** | helm template; Argo CD administra el ciclo de vida | Helm Controller administra las versiones de Helm |
| **Compatibilidad con Kustomize** | Compatibilidad completa | Compatibilidad completa mediante Kustomize Controller |
| **Compatibilidad con OCI** | Fuentes OCI generales y de Helm OCI; comprueba los requisitos de versión y tipo de medio | OCIRepository; comprueba la compatibilidad con capas y verificación |
| **Notificaciones** | Sistema de notificaciones integrado | Notification Controller |
| **RBAC** | RBAC completo | RBAC nativo de Kubernetes |
| **Integración de SSO** | OIDC directo o conectores de Dex compatibles | Autenticación de Kubernetes |
| **Comprobaciones de estado** | Estado integrado o personalizado de los recursos | Preparación específica de cada controlador, comprobaciones de estado y condiciones personalizadas |
| **Entrega progresiva** | Mediante Argo Rollouts | Mediante Flagger |
| **Automatización de imágenes** | Mediante Argo Image Updater | Image Reflector/Image Automation opcionales |
| **Vista previa de diferencias** | Diferencias visuales en la interfaz | Diferencias desde la CLI |
| **Sync Waves** | Compatibilidad nativa | Mediante dependencias |
| **Hooks** | Hooks de sincronización de Argo | Hooks de Helm; diseña por separado las dependencias de Kustomization y los Jobs |

### Comparación de arquitectura

#### Arquitectura de ArgoCD

![Arquitectura de ArgoCD: el servidor API conecta la interfaz web, el SSO de Dex y la caché de Redis; el servidor de repositorio obtiene los manifiestos de Git y el controlador de aplicaciones los aplica al clúster de Kubernetes de destino.](../.gitbook/assets/en-gitops-03-gitops-comparison-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-03-gitops-comparison-0.html)

#### Arquitectura de FluxCD

![Diagrama de arquitectura en el que Source Controller obtiene contenido de Git, Helm y fuentes OCI y activa Kustomize Controller y Helm Controller para aplicar recursos al clúster de Kubernetes; Notification Controller observa los tres, e Image Automation Controller escribe las etiquetas de imagen actualizadas de vuelta en Git.](../.gitbook/assets/en-gitops-03-gitops-comparison-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-03-gitops-comparison-1.html)

### Comunidad y ecosistema

| Métrica | ArgoCD | FluxCD |
|--------|--------|--------|
| **Estado en CNCF** | Graduado (diciembre de 2022) | Graduado (noviembre de 2022) |
| **Primera versión** | 2018 | 2016 (v1), 2020 (v2) |
| **Mantenimiento** | Comprueba la gobernanza y la cobertura de seguridad actuales | Comprueba la gobernanza y la cobertura de seguridad actuales |
| **Herramientas del ecosistema** | Argo Workflows, Rollouts, Events | Flagger, Weave GitOps |

## Cuándo elegir ArgoCD

ArgoCD es una buena opción si necesitas:

### Casos de uso

1. **Administración visual**: equipos que prefieren una interfaz gráfica para administrar despliegues
2. **Control centralizado**: organizaciones que quieren una vista unificada de varios clústeres
3. **RBAC completo**: requisitos complejos de control de acceso entre equipos
4. **Integración de SSO**: entornos empresariales que requieren autenticación OIDC/SAML
5. **Sync Waves y hooks**: orquestación compleja de despliegues que exige controlar el orden

### Ventajas

- **Interfaz web completa**: interfaz visual intuitiva para administrar despliegues
- **Centrada en aplicaciones**: se ajusta de forma natural a cómo los desarrolladores conciben los despliegues
- **Ecosistema maduro**: integración estrecha con Argo Workflows, Rollouts y Events
- **Funciones empresariales**: SSO, RBAC y registro de auditoría listos para usar
- **Depuración sencilla**: diferencias visuales y estado de sincronización en la interfaz

### Escenario de ejemplo

```
Scenario: Enterprise with 50+ microservices
- Multiple teams need self-service deployments
- Security team requires audit logs and RBAC
- Developers want visual feedback on sync status
- Need SSO integration with corporate identity provider

Recommendation: ArgoCD
- Projects per team with role-based access
- Application Sets for template-driven deployments
- Web UI for developer self-service
- Dex integration for SSO
```

## Cuándo elegir FluxCD

FluxCD es una buena opción si necesitas:

### Casos de uso

1. **Arquitectura modular**: elegir solo los controladores necesarios
2. **Flujos de trabajo centrados en la CLI**: flujos GitOps nativos sin depender de una interfaz
3. **Automatización de imágenes**: actualizar automáticamente en Git las imágenes de contenedor
4. **Artefactos OCI**: almacenar y desplegar desde registros OCI
5. **Elegir componentes**: seleccionar controladores y medir la carga de trabajo real que generan

### Ventajas

- **Diseño modular**: usar solo lo necesario
- **Automatización nativa de imágenes**: controladores opcionales para actualizar imágenes de contenedor
- **Compatibilidad con OCI**: compatibilidad de primera clase con artefactos OCI
- **Nativo de Kubernetes**: utiliza el RBAC estándar de Kubernetes
- **Control de recursos**: medir CPU y memoria en relación con los componentes instalados, las fuentes, los objetos y los intervalos de conciliación

### Escenario de ejemplo

```
Scenario: Platform team building internal developer platform
- Need automated image updates when CI builds new versions
- Want to store deployment artifacts in container registry
- Prefer CLI-driven GitOps workflows
- Multiple clusters with different configurations

Recommendation: FluxCD
- Image automation for continuous deployment
- OCI repositories for artifact storage
- Kustomize overlays for environment differences
- Multi-cluster management with fleet repo
```

## ¿Pueden trabajar juntos?

Sí, ArgoCD y FluxCD pueden combinarse en patrones complementarios. Asigna los recursos de manera que dos conciliadores no modifiquen ni eliminen los mismos objetos. Administrar un recurso personalizado junto con su operador es distinto de permitir que dos herramientas compitan por el mismo Deployment o la misma versión de Helm.

### Patrón 1: FluxCD para la infraestructura y ArgoCD para las aplicaciones

```
Git Repository
├── infrastructure/     # Managed by FluxCD
│   ├── cert-manager/
│   ├── ingress-controller/
│   └── monitoring/
└── applications/       # Managed by ArgoCD
    ├── app-a/
    ├── app-b/
    └── app-c/
```

- FluxCD administra la infraestructura del clúster (operadores y controladores)
- ArgoCD administra los despliegues de aplicaciones con una interfaz para los desarrolladores

### Patrón 2: automatización de imágenes con FluxCD y despliegues con ArgoCD

```
1. CI builds new image → pushes to registry
2. FluxCD Image Automation detects new tag
3. FluxCD commits updated manifest to Git
4. ArgoCD syncs the change to cluster
```

### Patrón 3: herramientas distintas para clústeres diferentes

- Clústeres de producción: ArgoCD (para la interfaz y los requisitos de auditoría)
- Clústeres de desarrollo: FluxCD (para iterar con rapidez)

## Consideraciones para la migración

Estas son correspondencias de diseño, no cambios automáticos de nombre de CRD. Compara el inventario de recursos, las versiones de Helm, los hooks, la poda y los finalizadores, los secretos y los permisos. En un entorno de pruebas, comprueba cómo detener el conciliador anterior y transferir la propiedad sin provocar eliminaciones. El uso de plantillas de Argo CD no adopta automáticamente el historial de versiones de Helm de Flux.

### De FluxCD a ArgoCD

1. Exporta las Kustomizations de FluxCD como Applications de ArgoCD
2. Asigna las fuentes de FluxCD a repositorios de ArgoCD
3. Convierte los HelmReleases en Helm Applications de ArgoCD
4. Configura RBAC y SSO en ArgoCD

### De ArgoCD a FluxCD

1. Convierte las Applications de ArgoCD en Kustomizations/HelmReleases
2. Configura Source Controller con repositorios de Git y Helm
3. Configura Notification Controller para las alertas
4. Implementa Image Automation si es necesario

## Otras herramientas GitOps

Aunque ArgoCD y FluxCD dominan el panorama GitOps, existen otras herramientas:

### Jenkins X

- Se centra en automatizar los pipelines de CI/CD
- Incluye entornos de vista previa
- Utiliza pipelines basados en Tekton
- Ideal para: equipos que quieren integrar CI/CD y GitOps

### Rancher Fleet

- Diseñado para administrar miles de clústeres
- GitOps a escala
- Integrado con Rancher
- Ideal para: despliegues distribuidos en el borde a gran escala

### Weave GitOps

- Proyecto de interfaz de código abierto basado en Flux; verifica por separado la disponibilidad de soporte comercial
- Añade una interfaz y funciones empresariales a Flux
- Evalúa las versiones actuales, la compatibilidad con Flux y quién proporciona el soporte

## Matriz de decisión

| Requisito | Opción más adecuada |
|-------------|-------------|
| Se necesita una interfaz web | ArgoCD |
| Flujos de trabajo centrados en la CLI | FluxCD |
| Automatización de imágenes | Controladores opcionales de Flux o Argo CD Image Updater |
| RBAC complejo | ArgoCD |
| Integración de SSO | ArgoCD |
| Límites de recursos | Evalúa el mismo tipo de carga de trabajo real |
| Artefactos OCI | Ambos; compara las necesidades de formato, verificación y autenticación |
| Sync Waves/hooks | ArgoCD |
| Diferencias visuales | ArgoCD |
| Despliegue modular | FluxCD |
| Auditoría empresarial | ArgoCD |
| Administración de muchos clústeres a escala | Ambos |

## Conclusión

ArgoCD y FluxCD son excelentes opciones para implementar GitOps. La decisión suele depender de lo siguiente:

- **Elige ArgoCD** si valoras una interfaz completa, funciones empresariales y una administración centrada en aplicaciones
- **Elige FluxCD** si prefieres la modularidad, los flujos de trabajo con CLI y la automatización de imágenes integrada

Muchas organizaciones utilizan ambas herramientas para fines diferentes y aprovechan las ventajas de cada una donde más se necesitan.

## Cuestionario

Para comprobar lo aprendido, prueba el [cuestionario de comparación de herramientas GitOps](../quizzes/gitops/03-gitops-comparison-quiz.md).

## Referencias

- [Argo CD y OCI](https://argo-cd.readthedocs.io/en/stable/user-guide/oci/)
- [Ciclo de vida de Helm en Argo CD](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)
- [Ciclo de vida de HelmRelease en Flux](https://fluxcd.io/flux/components/helm/helmreleases/)
- [Multitenencia en Flux](https://fluxcd.io/flux/installation/configuration/multitenancy/)
- [Ecosistema de Flux](https://fluxcd.io/ecosystem/)
