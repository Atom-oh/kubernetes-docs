# Parte 3: Despliegue de MLflow en EKS

> **Base de revisión**: MLflow 3.16.0 · chart comunitario 1.11.7; se comprobó el último parche 3.16.1 · 2026-10-12

## Configuración del entorno de laboratorio

Prepare una versión de Kubernetes de EKS compatible, kubectl compatible, Helm 3, una base de datos de metadatos y almacenamiento de artefactos. Un límite inferior como `kubectl >=1.34` no establece compatibilidad con todos los servidores de API. Consulte la política de desfase de versiones cliente/servidor para el clúster real.

Este capítulo se basa en un chart descargado, renderizado nativo de Helm y el código fuente del servidor MLflow 3.16.0. **No establece el aprovisionamiento exitoso de AWS, la conectividad de RDS, las cargas a S3 ni el despliegue de EKS.** Consulte la [Parte 1](01-tracking.md) para verificaciones locales de SQLite/API y la [Parte 2](02-model-registry.md) para verificaciones de Registry.

## Por qué ejecutar el servidor de Tracking de MLflow en EKS

Puede reutilizar patrones de despliegue de Kubernetes, observabilidad e IAM, al tiempo que asume la responsabilidad de los servidores, las bases de datos, los artefactos, el control de acceso, las copias de seguridad y las actualizaciones. Las aplicaciones MLflow de SageMaker y otros registros gestionados son alternativas; sus versiones compatibles, autenticación, características y costo no son necesariamente idénticos.

Compartir con un equipo no requiere automáticamente aprovisionar recursos nuevos e independientes de RDS y S3. Es posible realizar ejercicios pequeños con SQLite/PVC; elija la arquitectura de producción según los requisitos de concurrencia, durabilidad y recuperación.

## Arquitectura

| Capa | Responsabilidad y estado que se deben inspeccionar |
|---|---|
| Servidor HTTP | API de SDK, UI, proxy de artefactos; autenticación, autorización, política de host/CORS, workers |
| Base de datos de metadatos | metadatos de experimento/ejecución/métrica/modelo/registro; pools, migraciones, copias de seguridad |
| Almacén de artefactos | archivos de modelo/datos/gráficos; bucket/prefijo, IAM, cifrado, retención |
| Almacén de autenticación | base de datos de usuario/permisos, secretos de sesión/firma, caché para el mecanismo de autenticación seleccionado |
| Estado de características opcionales | colas, cachés y archivos temporales usados por trabajos habilitados, características de tracing/evaluación o gateway |

PostgreSQL más S3 no hace que todas las características sean sin estado. Por ejemplo, las bases de datos SQLite de autenticación básica locales al Pod pueden hacer que las réplicas tengan usuarios o permisos diferentes. Compruebe por separado las cachés de complementos OIDC y el almacenamiento de trabajos.

SQLite es una base de datos relacional y admite varios procesos con escrituras serializadas. No falla inmediatamente cuando se conecta un segundo usuario. Sin embargo, los archivos SQLite independientes locales al Pod no son una base de datos compartida; incluso los archivos compartidos tienen restricciones de escritor, bloqueo del sistema de archivos y recuperación. Relacione la selección de PostgreSQL para producción con esos requisitos.

![El acceso protegido conduce a servidores MLflow que usan bases de datos de metadatos/autenticación y artefactos de S3. Los permisos IAM de S3 y los permisos de inicio de sesión de PostgreSQL son independientes; el estado compartido se externaliza antes de escalar las réplicas.](../../.gitbook/assets/en-ai-ml-mlflow-03-eks-deployment-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-03-eks-deployment-0.html)

## Enfoques de instalación y fijaciones de versión

| Ruta | Lo que se verificó |
|---|---|
| Chart comunitario | se descargó/renderizó `community-charts/mlflow` 1.11.7; appVersion 3.16.0, imagen predeterminada `burakince/mlflow` |
| Chart del repositorio de MLflow | `v3.16.0/charts` contiene el chart 0.1.1 con appVersion 3.15.2; la etiqueta de fuente, la versión del chart y la versión de imagen difieren |
| Manifiestos directos | una opción cuando las políticas de entrega de credenciales basadas en archivos, redes, autenticación o migración necesitan control directo |

El código fuente en el repositorio upstream no prueba que se publique un paquete OCI con una versión idéntica. La extracción del chart OCI oficial 0.1.1 devolvió `not found` durante la revisión, por lo que no se presenta aquí como un comando de instalación verificado.

Estos comandos inspeccionan los valores predeterminados del chart mediante descubrimiento, descarga y renderizado. Prepare los valores de producción por separado mediante las verificaciones siguientes.

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update community-charts
helm show chart community-charts/mlflow --version 1.11.7
helm pull community-charts/mlflow --version 1.11.7 --untar --untardir ./vendor
helm show values community-charts/mlflow --version 1.11.7 > values.reference.yaml
helm template mlflow ./vendor/mlflow --namespace mlflow -f values.reference.yaml > rendered.yaml
```

Inspeccione la imagen/digest renderizada, ServiceAccount, entrega de credenciales, argumentos de CLI, probes, Service e Ingress antes de aplicar. El chart usa de forma predeterminada una imagen comunitaria en lugar de la imagen upstream de MLflow; verifique también sus controladores de base de datos, SDK de AWS y complementos de autenticación.

### Valores predeterminados importantes del chart 1.11.7

- Los valores predeterminados incluyen `replicaCount: 1`, `auth.enabled: false` e `ingress.enabled: false`.
- `backendStore.defaultSqlitePath: ":memory:"` configura metadatos en memoria. **Esto difiere del nuevo valor predeterminado de archivo SQLite de la CLI upstream.** Una instalación predeterminada del chart no es un servicio de producción durable.
- PostgreSQL externo usa `backendStore.postgres.*`; las referencias de credenciales usan `backendStore.existingDatabaseSecret.*`.
- Compruebe `artifactRoot.s3.*` junto con `artifactRoot.proxiedArtifactStorage: true`. El renderizado nativo produjo `--artifacts-destination=s3://...` y `--serve-artifacts`.
- Los ajustes de la base de datos de autenticación básica están separados en `auth.postgres.*`. Cambiar la base de datos de Tracking no comparte automáticamente el estado de autenticación.
- `backendStore.databaseMigration: true` agrega una ruta de init-container de Pod. Planifique las copias de seguridad, una fase de migración coordinada y verificaciones de compatibilidad antes de permitir que varias réplicas migren de forma simultánea.

Completar nombres sin valores reales y Secrets no finaliza la configuración de producción. Algunas referencias de base de datos/autenticación en este chart se entregan mediante **variables de entorno del contenedor**. SecretKeyRef evita valores de texto sin formato en Git, pero no elimina la exposición al entorno del proceso. Cuando la política prohíbe valores secretos en entornos, prepare archivos de credenciales proporcionados desde Secrets Manager/SSM o un almacén equivalente, y un despliegue que consuma esos archivos. No coloque claves estáticas de AWS en los valores de Helm ni en las imágenes.

## IAM y autenticación de base de datos

Limite los permisos de S3 al bucket/prefijo previsto. Según las operaciones reales, compruebe los permisos de `GetObject`, `PutObject`, listado, multipart y KMS. El modo proxy usa permisos de AWS del servidor; el modo de artefactos directos usa permisos del cliente. Los URI de experimentos existentes no se reescriben simplemente al cambiar las flags del servidor.

EKS Pod Identity requiere el Agent, una asociación y un SDK compatible, y se dirige a workers Linux EC2. No está disponible de forma universal para Pods de Fargate o Windows. IRSA sigue siendo otra opción dentro de sus configuraciones compatibles. Especificar un nombre de ServiceAccount o una anotación no completa la confianza de IAM, la asociación ni la configuración del SDK.

Un rol de IAM para S3 no autoriza automáticamente el inicio de sesión de PostgreSQL. Verifique el acceso de red a la base de datos, la validación de TLS, usuarios/credenciales o la autenticación de base de datos IAM configurada por separado. Revise la configuración de IMDS y SDK para impedir un respaldo no intencionado hacia las credenciales del rol de nodo.

## Acceso al servidor y verificaciones de estado

ClusterIP, los ALB privados y TLS proporcionan controles de red o transporte; no sustituyen los permisos de MLflow por usuario. Use la arquitectura de Ingress protegida de la organización en lugar de asumir exposición directa a un ALB público.

Configure `allowed_hosts` y los orígenes CORS de MLflow 3.16.0 para los llamadores reales. En este chart comunitario, configure los argumentos de CLI correspondientes mediante `extraArgs.allowedHosts` y `extraArgs.corsAllowedOrigins`. Las restricciones de Host/CORS no sustituyen el inicio de sesión ni la autorización.

La autenticación básica cambió a autorización de denegación predeterminada en 3.16.0. La versión 3.16.1 eliminó la contraseña predeterminada del administrador incluida, por lo que no dependa de las credenciales predeterminadas. Configure explícitamente una contraseña de administrador aprobada y los ajustes de autenticación antes del inicio. La combinación de este capítulo de chart y MLflow 3.16.0 no se volvió a validar con 3.16.1.

El endpoint de estado verificado es **`/health`**, implementado como un retorno de `"OK", 200`. Comprueba la capacidad de respuesta del proceso HTTP, no la conectividad continua de RDS/S3 ni la autorización de usuarios. Esta versión exime los endpoints de estado de la validación de host. Compruebe las rutas reales del servicio al usar `static-prefix`, reescrituras de Ingress o complementos.

## Notas operativas

Antes de escalar réplicas, comparta o externalice las bases de datos de metadatos/autenticación, los secretos de sesión y las colas/cachés habilitadas; pruebe la conmutación por error. Después aplique distribución de topología, PDB, readiness y límites de recursos. Dos Pods por sí solos no garantizan alta disponibilidad.

Una llamada de API no siempre equivale a una escritura de SQL. Mida conjuntamente el registro por lotes, las transacciones, las cargas de tracing, el historial de métricas y los pools de conexiones por worker. Los pools entre réplicas/workers se acumulan; la configuración de un pool no describe la demanda total de conexiones de base de datos.

Aurora Serverless v2 funciona dentro de rangos de capacidad y restricciones de conexiones, E/S y transacciones configurados. No absorbe ráfagas ilimitadas ni garantiza menor costo. Compárelo con RDS/Aurora aprovisionado frente a la carga medida y los requisitos de recuperación.

Realice copias de seguridad de las bases de datos de metadatos/autenticación y de los artefactos en conjunto, y pruebe la restauración. Revise herramientas de eliminación permanente como `mlflow gc` frente a la política de retención en lugar de agregarlas como limpieza rutinaria. Los cambios de alias de modelo y el redespliegue de serving también son operaciones independientes.

## Fuentes principales

- [Lanzamiento del parche MLflow 3.16.1](https://github.com/mlflow/mlflow/releases/tag/v3.16.1)
- [Base de revisión de MLflow 3.16.0](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Arquitectura del servidor de Tracking](https://mlflow.org/docs/3.16.0/self-hosting/architecture/tracking-server/)
- [Chart comunitario](https://github.com/community-charts/helm-charts/tree/main/charts/mlflow)
- [Chart del repositorio de MLflow](https://github.com/mlflow/mlflow/tree/v3.16.0/charts)
- [Implementación de estado del servidor](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/server/__init__.py)
- [Restricciones de EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Casos de uso y concurrencia de SQLite](https://www.sqlite.org/whentouse.html)
- [Configuración de capacidad de Aurora Serverless v2](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

[Página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
