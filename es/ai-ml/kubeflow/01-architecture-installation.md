# Parte 1: Arquitectura e instalación de Kubeflow en EKS

> **Referencia de revisión**: Community Distribution 26.03.1; Dashboard 2.0.0; KFP 2.16.1
> **Última revisión**: September 12, 2026
> **Validación**: El overlay de Profile se renderizó localmente con kubectl 1.36.2 / Kustomize 5.8.1. No se ejecutó ninguna instalación de EKS ni flujo de identidad de AWS.

## Preparación del entorno

Seleccione una versión de la distribución antes de seleccionar comandos. Registre la versión de EKS/Kubernetes, la arquitectura de los nodos, CNI, las clases de almacenamiento, el proveedor de identidad y los componentes requeridos. `Kubernetes 1.34+` no es una garantía de compatibilidad sin límites.

La versión 26.03.1 informa cobertura de CI de Kubernetes 1.36 y uso de Kind 0.32+. Esto no certifica todas las combinaciones de complementos de EKS. Su README advierte que algunas imágenes pueden no contar con compatibilidad con ARM64. El renderizado requiere kubectl con Kustomize o el Kustomize independiente especificado por la distribución; aplicar recursos también requiere un clúster de destino, permisos y dependencias listas.

## ¿Qué es Kubeflow?

Kubeflow incluye componentes de ML publicados de forma independiente. Community Distribution reúne sus revisiones y servicios compartidos. Algunas cargas de trabajo utilizan CRD; otras operaciones utilizan API de aplicaciones, bases de datos y almacenamiento de objetos. El dashboard es un punto de entrada de UI, no el planificador ni un distribuidor universal.

### Graduación de CNCF — 17 de agosto de 2026

El [anuncio de CNCF](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/) registra la graduación, una auditoría de seguridad independiente y una gobernanza formal. Esto respalda una evaluación de la madurez del proyecto. No sustituye el modelado de amenazas, las pruebas de aislamiento de tenants ni una evaluación de cumplimiento específica para la implementación.

## Modelo de versiones y referencia actual

La distribución utiliza `YY.MM.patch`, planea aproximadamente dos versiones base al año y describe el soporte de la comunidad como de mejor esfuerzo durante unos seis meses. Esto no es un SLA de soporte de un proveedor.

La [versión 26.03.1](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1), publicada el 15 de junio de 2026, y su [inventario etiquetado](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md) proporcionan esta referencia:

| Componente | Revisión incluida |
| --- | --- |
| Dashboard / Profile Controller / gestión de acceso | 2.0.0 |
| Pipelines | 2.16.1 |
| Notebooks v1 | 1.11.0 |
| Trainer v2 / legacy Training Operator | 2.2.0 / 1.9.2 |
| Katib | 0.19.0 |
| KServe / Models Web Application | 0.18.0 / 0.18.0 |
| Hub / Spark Operator | 0.3.9 / 2.5.0 |
| Istio / Knative | 1.30.1 / 1.22.0 |
| cert-manager / Dex / oauth2-proxy | 1.20.2 / 2.45.1 / 7.15.2 |

La versión describe Workspaces (Notebooks v2) como beta; esto no reemplaza la fila estable de Notebooks v1. Legacy Training Operator y Trainer v2 coexisten con API diferentes. Compruebe los CRD instalados y las definiciones de tiempo de ejecución antes de escribir trabajos de entrenamiento.

## Arquitectura de componentes

![Arquitectura de Kubeflow que separa el acceso a UI autenticada, las API de aplicaciones y el almacenamiento, y la reconciliación de Kubernetes mediante Profile y controladores de cargas de trabajo.](../../.gitbook/assets/en-ai-ml-kubeflow-01-architecture-installation-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-01-architecture-installation-0.html)

| Límite | Proporciona | Aún requiere configuración |
| --- | --- | --- |
| Proveedor de identidad, oauth2-proxy, gateway | Autenticación del navegador y reenvío de identidad de confianza | Clientes OIDC, TLS, encabezados de confianza, autenticación de máquina a máquina |
| Dashboard y aplicaciones web de componentes | Navegación e interfaces de aplicación | La autorización y la identidad de Service de cada API |
| Profile Controller y gestión de acceso (KFAM) | Propiedad de Namespace, acceso de propietario/colaborador, RBAC e Istio policies generadas | Cuotas, aislamiento de red, privilegios de cargas de trabajo, almacenamiento y permisos de AWS |
| Controladores de componentes | Reconciliación de recursos de Kubernetes compatibles | Admisión, programación, dependencias y estado |
| API y persistencia de KFP | Operaciones de pipeline/ejecución/experimento, metadatos y artefactos | Disponibilidad de base de datos/almacenamiento de objetos, autorización y copia de seguridad |

Un `Profile` con alcance de clúster tiene un propietario y administra un Namespace; los colaboradores se gestionan mediante la gestión de acceso. Dashboard 2.0.0 crea su `ResourceQuota` únicamente cuando `spec.resourceQuotaSpec.hard` no está vacío. Omitir la cuota no genera un límite de recursos predeterminado; vaciar este campo elimina la cuota gestionada por este controlador.

El RBAC generado por Profile y la `AuthorizationPolicy` de Istio no proporcionan aislamiento completo entre tenants. La aplicación de NetworkPolicy, los permisos de Pod, el acceso al almacenamiento, AWS IAM y la autorización de aplicaciones siguen siendo independientes. La NetworkPolicy incluida con el overlay de Profile protege ese servicio de controlador/gestión de acceso, no todos los Namespace de usuarios.

Los conceptos Pipeline, Run y Experiment de KFP no son CRD universales. El modo opcional de API Kubernetes Native añade los CRD `Pipeline` y `PipelineVersion`. KFP Experiment y Katib Experiment son recursos diferentes.

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

El controlador rechaza la toma de control de un Namespace existente con propiedad no coincidente. Su referencia de propietario del Namespace también hace que la eliminación sea significativa: eliminar un Profile puede eliminar el Namespace que posee y sus recursos. Durante la migración a Dashboard v2, siga los pasos de eliminación específicos de la versión para los recursos del controlador antiguo; conserve el CRD de Profile, los objetos Profile y los Namespace de usuarios.

## Rutas de instalación en EKS

| Ruta | Evidencia y limitaciones |
| --- | --- |
| Community Distribution 26.03.1 | Paquete de comunidad revisado; configure las redes de EKS, el almacenamiento, ingress y la identidad para esta versión |
| `awslabs/kubeflow-manifests` | Última versión publicada inspeccionada: `v1.7.0-aws-b1.0.3` (1 de septiembre de 2023). Su página de versiones indica que las nuevas instalaciones fallan porque se eliminó una imagen OIDC antigua |
| Distribución con soporte de proveedor | Evalúe su propia matriz de versiones, soporte, integraciones y ruta de migración |

La [advertencia de versión de AWS](https://github.com/awslabs/kubeflow-manifests/releases/tag/v1.7.0-aws-b1.0.3) significa que el antiguo tutorial de manifest/Terraform no es una receta de instalación verificada para 26.03.1. La actividad del repositorio por sí sola no cambia la compatibilidad de esa versión.

Los overlays históricos de AWS describen integraciones de Cognito, RDS y S3. Pueden reducir la operación de servicios de identidad, base de datos y almacenamiento de objetos autoalojados, pero no son valores predeterminados intercambiables: el mapeo de issuer/claim, la compatibilidad de base de datos, las redes, IAM, los costos y la migración siguen siendo importantes. Valide los overlays antiguos antes de combinarlos con una versión nueva.

### Renderizar antes de aplicar

Estos comandos obtienen la versión revisada y renderizan solo su overlay del controlador Profile. Crean archivos locales sin conectarse a Kubernetes:

```bash
git clone --depth 1 --branch 26.03.1 \
  https://github.com/kubeflow/community-distribution.git kubeflow-26.03.1
cd kubeflow-26.03.1
kubectl kustomize \
  applications/dashboard/upstream/profile-controller/overlays/kubeflow \
  > profile-controller.rendered.yaml
```

El overlay revisado produjo 14 recursos, incluidos el CRD de Profile, RBAC, Service y `profiles-deployment` en `kubeflow`. Sus contenedores usan imágenes de Dashboard 2.0.0 Profile Controller y gestión de acceso. Este overlay no crea el Namespace `kubeflow` y requiere sus dependencias de Istio/network-policy.

Para la instalación, siga el orden de componentes individuales de la versión fijada. Inspeccione los recursos renderizados, establezca los CRD requeridos, espere a los controladores/webhooks y luego aplique recursos personalizados. Diagnostique los errores de admisión o de propiedad de campos en vez de forzar conflictos repetidamente. Un renderizado correcto no demuestra ni la admisión de API ni una implementación funcional de EKS.

## Patrones de acceso de IAM: IRSA, KFPv2 y Pod Identity

La [guía actual de almacenamiento de objetos de KFP](https://www.kubeflow.org/docs/components/pipelines/operator-guides/configure-object-store/) documenta S3 con IRSA y `credentials.fromEnv: true` del launcher. La nota de IRSA “KFPv1 only” de la antigua distribución de AWS no es una limitación universal de KFPv2 actual.

En KFP 2.16.1, `fromEnv` delega al abridor de bucket de Go Cloud. Su `gocloud.dev` 0.40.0 fijado utiliza de forma predeterminada la cadena de credenciales de AWS SDK v2, salvo que se especifique una anulación de SDK. Esto es más amplio que leer variables de entorno de claves de acceso estáticas.

Configure el ServiceAccount de ejecución de pipelines y cada componente que acceda a artefactos, incluido el servidor API cuando lo requiera su configuración de almacenamiento de objetos. Compruebe la compatibilidad real con SDK/proveedor del contenedor, los prefijos de bucket y los permisos de KMS. IRSA necesita una confianza de rol coincidente y credenciales proyectadas, no solo una anotación. Pod Identity también necesita un entorno de EKS compatible, el agente, una asociación y compatibilidad con SDK; esta revisión no ejecutó esa integración.

El plugin Profile `AwsIamForServiceAccount` de Dashboard no es un interruptor de Pod Identity: anota `default-editor` y puede actualizar la política de confianza de un rol de IAM. Tenga en cuenta los permisos del controlador y los cambios de confianza. El ejemplo anterior no habilita ese plugin. Use identidad de carga de trabajo con acceso de alcance limitado en vez de copiar una solución histórica de usuario de IAM/clave estática en una implementación nueva.

## ¿Por qué ejecutar esto en EKS en lugar de una alternativa administrada?

EKS es adecuado para equipos con capacidad operativa de Kubernetes que necesitan herramientas compartidas, tiempos de ejecución de entrenamiento personalizados o un comportamiento específico de programación y serving. El equipo es responsable de los controladores, CRD, límites entre tenants, recuperación, capacidad y actualizaciones.

SageMaker AI puede reducir la operación de infraestructura, pero no elimina las responsabilidades relativas a la aplicación, los datos, IAM o la calidad del modelo. Compare los servicios y modos de implementación que realmente se necesitan.

## Fuentes y validación

La revisión inspeccionó manifests de distribución etiquetados, el código Profile de Dashboard 2.0.0 y el código de almacenamiento de objetos de KFP 2.16.1. El overlay de Profile se renderizó localmente y el ejemplo se comprobó con respecto a su esquema de CRD. Esto no demuestra la autenticación, el aislamiento ni el acceso a artefactos de extremo a extremo.

- [Controlador Profile de Dashboard](https://github.com/kubeflow/dashboard/blob/v2.0.0/components/profile-controller/controllers/profile_controller.go)
- [Plugin Profile de AWS para Dashboard](https://github.com/kubeflow/dashboard/blob/v2.0.0/components/profile-controller/controllers/plugin_iam.go)
- [Implementación de almacenamiento de objetos de KFP](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/objectstore/object_store.go)

## Próximos pasos

Continúe con [Parte 2: Pipelines](02-pipelines.md).

[Volver a la página principal](README.md)

## Cuestionario

Pruebe el [Cuestionario del tema](../../quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md).
