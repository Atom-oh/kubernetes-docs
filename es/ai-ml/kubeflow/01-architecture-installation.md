# Parte 1: Arquitectura e instalación de Kubeflow en EKS

> **Base de revisión**: Community Distribution 26.03.1; Dashboard 2.0.0; KFP 2.16.1
> **Última revisión**: September 12, 2026
> **Validación**: El overlay de Profile se renderizó localmente con kubectl 1.36.2 / Kustomize 5.8.1. No se ejecutó ninguna instalación de EKS ni flujo de identidad de AWS.

## Preparación del entorno

Selecciona una versión de la distribución antes de elegir los comandos. Registra la versión de EKS/Kubernetes, la arquitectura de los nodos, el CNI, las clases de almacenamiento, el proveedor de identidad y los componentes requeridos. `Kubernetes 1.34+` no garantiza compatibilidad sin límites.

La versión 26.03.1 informa cobertura de CI para Kubernetes 1.36 y uso de Kind 0.32+. Esto no certifica todas las combinaciones de complementos de EKS. Su README advierte que algunas imágenes podrían no ser compatibles con ARM64. El renderizado requiere kubectl con Kustomize o la versión independiente de Kustomize especificada por la distribución; para aplicar recursos también se requiere un clúster de destino, permisos y dependencias listas.

## ¿Qué es Kubeflow?

Kubeflow está compuesto por componentes de ML que se publican de forma independiente. Community Distribution reúne sus revisiones y servicios compartidos. Algunas cargas de trabajo usan CRD; otras operaciones usan API de aplicaciones, bases de datos y almacenamiento de objetos. El dashboard es un punto de entrada a la interfaz de usuario, no el planificador ni un despachador universal.

### Graduación de CNCF: 17 de agosto de 2026

El [anuncio de CNCF](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/) registra la graduación, una auditoría de seguridad independiente y una gobernanza formal. Esto respalda una evaluación de la madurez del proyecto. No sustituye el modelado de amenazas, las pruebas de aislamiento entre tenants ni una evaluación de cumplimiento específica de la implementación.

## Modelo de versiones y base actual

La distribución usa `YY.MM.patch`, prevé aproximadamente dos versiones base por año y describe el soporte de la comunidad como de mejor esfuerzo durante unos seis meses. Esto no es un SLA de soporte de un proveedor.

La [versión 26.03.1](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1), publicada el 15 de junio de 2026, y su [inventario etiquetado](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md) proporcionan esta base:

| Componente | Revisión incluida |
| --- | --- |
| Dashboard / Profile Controller / gestión de acceso | 2.0.0 |
| Pipelines | 2.16.1 |
| Notebooks v1 | 1.11.0 |
| Trainer v2 / Training Operator heredado | 2.2.0 / 1.9.2 |
| Katib | 0.19.0 |
| KServe / aplicación web Models | 0.18.0 / 0.18.0 |
| Hub / Spark Operator | 0.3.9 / 2.5.0 |
| Istio / Knative | 1.30.1 / 1.22.0 |
| cert-manager / Dex / oauth2-proxy | 1.20.2 / 2.45.1 / 7.15.2 |

La versión describe Workspaces (Notebooks v2) como beta; esto no reemplaza la fila estable de Notebooks v1. Training Operator heredado y Trainer v2 coexisten con API distintas. Comprueba las CRD instaladas y las definiciones de tiempo de ejecución antes de escribir trabajos de entrenamiento.

## Arquitectura de componentes

![Arquitectura de Kubeflow que separa el acceso autenticado a la interfaz de usuario, las API de aplicaciones y el almacenamiento, y la reconciliación de Kubernetes mediante Profile y los controladores de cargas de trabajo.](../../.gitbook/assets/en-ai-ml-kubeflow-01-architecture-installation-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-01-architecture-installation-0.html)

| Límite | Proporciona | Aún requiere configuración |
| --- | --- | --- |
| Proveedor de identidad, oauth2-proxy, gateway | Autenticación del navegador y reenvío de identidad de confianza | Clientes OIDC, TLS, encabezados de confianza, autenticación de máquina a máquina |
| Dashboard y aplicaciones web de componentes | Navegación e interfaces de aplicaciones | Autorización de cada API e identidad de servicio |
| Profile Controller y gestión de acceso (KFAM) | Propiedad del namespace, acceso de propietarios y colaboradores, RBAC generado y políticas de Istio | Cuotas, aislamiento de red, privilegios de cargas de trabajo, almacenamiento y permisos de AWS |
| Controladores de componentes | Reconciliación de recursos de Kubernetes compatibles | Admisión, planificación, dependencias y estado |
| API y persistencia de KFP | Operaciones de pipelines, ejecuciones y experimentos, metadatos y artefactos | Disponibilidad, autorización y copias de seguridad de la base de datos y del almacenamiento de objetos |

Un `Profile` con alcance de clúster tiene un propietario y gestiona un namespace; los colaboradores se administran mediante la gestión de acceso. Dashboard 2.0.0 crea su `ResourceQuota` solo cuando `spec.resourceQuotaSpec.hard` no está vacío. Omitir la cuota no genera un límite de recursos predeterminado; dejar vacío este campo elimina la cuota gestionada por este controlador.

El RBAC y `AuthorizationPolicy` de Istio generados por Profile no proporcionan un aislamiento completo entre tenants. La aplicación de NetworkPolicy, los permisos de Pod, el acceso al almacenamiento, AWS IAM y la autorización de aplicaciones siguen siendo aspectos independientes. La NetworkPolicy incluida en el overlay de Profile protege ese servicio del controlador y de gestión de acceso, no todos los namespaces de usuario.

Los conceptos de Pipeline, Run y Experiment de KFP no son universalmente CRD. El modo opcional de Kubernetes Native API añade las CRD `Pipeline` y `PipelineVersion`. KFP Experiment y Katib Experiment son recursos distintos.

### Ejemplo de Profile

Esto declara un propietario y una cuota explícita. No es un comando de instalación ni una política de aislamiento completa.

```yaml
apiVersion: kubeflow.org/v1
kind: Profile
metadata:
  name: team-a
spec:
  owner:
    kind: User
    name: owner@example.com
  resourceQuotaSpec:
    hard:
      requests.cpu: "8"
      requests.memory: 32Gi
      requests.nvidia.com/gpu: "2"
      persistentvolumeclaims: "10"
```

El controlador rechaza la apropiación de un namespace existente cuya propiedad no coincida. La referencia de propietario del namespace también hace que la eliminación sea importante: eliminar un Profile puede eliminar el namespace que posee y sus recursos. Durante la migración a Dashboard v2, sigue los pasos de eliminación específicos de la versión para los recursos de controladores antiguos; conserva la CRD Profile, los objetos Profile y los namespaces de usuario.

## Opciones de instalación en EKS

| Opción | Evidencia y limitaciones |
| --- | --- |
| Community Distribution 26.03.1 | Paquete comunitario revisado; configura la red, el almacenamiento, el ingreso y la identidad de EKS para esta versión |
| `awslabs/kubeflow-manifests` | Última versión publicada inspeccionada: `v1.7.0-aws-b1.0.3` (1 de septiembre de 2023). Su página de versión indica que las instalaciones nuevas fallan porque se eliminó una imagen OIDC antigua |
| Distribución con soporte de proveedor | Evalúa su propia matriz de versiones, soporte, integraciones y ruta de migración |

La [advertencia de la versión de AWS](https://github.com/awslabs/kubeflow-manifests/releases/tag/v1.7.0-aws-b1.0.3) significa que la antigua guía de manifiestos/Terraform no es una receta de instalación verificada para 26.03.1. La actividad del repositorio, por sí sola, no cambia la compatibilidad de esa versión.

Los overlays históricos de AWS describen integraciones con Cognito, RDS y S3. Pueden reducir la operación de los servicios autogestionados de identidad, bases de datos y almacenamiento de objetos, pero no son valores predeterminados intercambiables: la asignación de emisor y claims, la compatibilidad de bases de datos, la red, IAM, los costos y la migración siguen siendo importantes. Valida los overlays antiguos antes de combinarlos con una versión nueva.

### Renderiza antes de aplicar

Estos comandos obtienen la versión revisada y renderizan únicamente su overlay del controlador de Profile. Crean archivos locales sin conectarse a Kubernetes:

```bash
git clone --depth 1 --branch 26.03.1 \
  https://github.com/kubeflow/community-distribution.git kubeflow-26.03.1
cd kubeflow-26.03.1
kubectl kustomize \
  applications/dashboard/upstream/profile-controller/overlays/kubeflow \
  > profile-controller.rendered.yaml
```

El overlay revisado produjo 14 recursos, incluida la CRD Profile, RBAC, Service y `profiles-deployment` en `kubeflow`. Sus contenedores usan imágenes de Profile Controller y de gestión de acceso de Dashboard 2.0.0. Este overlay no crea el namespace `kubeflow` y requiere sus dependencias de Istio y de políticas de red.

Para la instalación, sigue el orden de componentes individuales de la versión fijada. Inspecciona los recursos renderizados, establece las CRD requeridas, espera a que los controladores y webhooks estén listos y luego aplica los recursos personalizados. Diagnostica los errores de admisión o de propiedad de campos en vez de forzar repetidamente los conflictos. Un renderizado correcto no demuestra ni la admisión de la API ni el funcionamiento de una implementación en EKS.

## Patrones de acceso de IAM: IRSA, KFPv2 y Pod Identity

La [guía actual de KFP sobre almacenamiento de objetos](https://www.kubeflow.org/docs/components/pipelines/operator-guides/configure-object-store/) documenta S3 con IRSA y `credentials.fromEnv: true` en el launcher. La nota “solo KFPv1” sobre IRSA de la antigua distribución de AWS no es una limitación universal del KFPv2 actual.

En KFP 2.16.1, `fromEnv` delega la apertura del bucket en Go Cloud. Su versión fijada de `gocloud.dev`, la 0.40.0, usa de forma predeterminada la cadena de credenciales de AWS SDK v2, salvo que se especifique una anulación del SDK. Esto va más allá de leer variables de entorno con claves de acceso estáticas.

Configura el ServiceAccount de ejecución del pipeline y cada componente que acceda a artefactos, incluido el servidor de API cuando así lo requiera su configuración de almacenamiento de objetos. Comprueba la compatibilidad real de los contenedores con el SDK/proveedor, los prefijos del bucket y los permisos de KMS. IRSA requiere una relación de confianza de rol coincidente y credenciales proyectadas, no solo una anotación. Pod Identity también requiere un entorno de EKS compatible, el agente, una asociación y compatibilidad con el SDK; esta revisión no ejecutó esa integración.

El complemento Profile `AwsIamForServiceAccount` de Dashboard no activa Pod Identity: anota `default-editor` y puede actualizar la política de confianza de un rol de IAM. Ten en cuenta los permisos del controlador y los cambios de confianza. El ejemplo anterior no habilita ese complemento. Usa identidad de carga de trabajo con acceso de alcance limitado en lugar de copiar a una implementación nueva una solución alternativa histórica basada en un usuario de IAM y claves estáticas.

## ¿Por qué ejecutarlo en EKS en vez de usar una alternativa gestionada?

EKS es adecuado para equipos con capacidad operativa de Kubernetes que necesitan herramientas compartidas, entornos de ejecución de entrenamiento personalizados o comportamientos específicos de planificación y serving. El equipo es responsable de los controladores, las CRD, los límites entre tenants, la recuperación, la capacidad y las actualizaciones.

SageMaker AI puede reducir la operación de infraestructura, pero no elimina las responsabilidades relacionadas con las aplicaciones, los datos, IAM ni la calidad de los modelos. Compara los servicios y modos de implementación que realmente necesitas.

## Fuentes y validación

La revisión inspeccionó los manifiestos etiquetados de la distribución, el código de Profile de Dashboard 2.0.0 y el código de almacenamiento de objetos de KFP 2.16.1. El overlay de Profile se renderizó localmente y el ejemplo se comprobó con el esquema de su CRD. Esto no demuestra la autenticación integral, el aislamiento ni el acceso a artefactos.

- [Controlador Profile de Dashboard](https://github.com/kubeflow/dashboard/blob/v2.0.0/components/profile-controller/controllers/profile_controller.go)
- [Complemento Profile de AWS de Dashboard](https://github.com/kubeflow/dashboard/blob/v2.0.0/components/profile-controller/controllers/plugin_iam.go)
- [Implementación de almacenamiento de objetos de KFP](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/objectstore/object_store.go)

## Pasos siguientes

Continúa con [Parte 2: Pipelines](02-pipelines.md).

[Volver a la página principal](README.md)

## Cuestionario

Prueba el [cuestionario del tema](../../quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md).
