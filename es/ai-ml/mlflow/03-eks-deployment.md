# Parte 3: Despliegue de MLflow en EKS

> **Base de revisión**: MLflow 3.16.0 · chart comunitario 1.11.7 · 2026-09-12

## Configuración del entorno de laboratorio

Prepare una versión de Kubernetes compatible en EKS, un kubectl compatible, Helm 3, una base de datos de metadatos y almacenamiento de artefactos. Un límite inferior como `kubectl >=1.34` no garantiza la compatibilidad con todos los API server. Consulte la política de desfase de versiones (version skew) entre cliente y servidor para el clúster real.

Este capítulo se basa en un chart descargado, en el renderizado nativo de Helm y en el código fuente del servidor de MLflow 3.16.0. **No acredita un aprovisionamiento correcto en AWS, conectividad con RDS, cargas a S3 ni un despliegue en EKS.** Consulte la [Parte 1](01-tracking.md) para las comprobaciones locales de SQLite/API y la [Parte 2](02-model-registry.md) para las comprobaciones del Registry.

## Por qué ejecutar el Tracking Server de MLflow en EKS

Puede reutilizar los patrones de despliegue, observabilidad e IAM de Kubernetes, asumiendo a cambio la responsabilidad sobre servidores, bases de datos, artefactos, control de acceso, copias de seguridad y actualizaciones. SageMaker MLflow Apps y otros Registry administrados son alternativas; sus versiones compatibles, autenticación, funcionalidades y coste no son necesariamente idénticos.

Compartir el entorno con un equipo no obliga automáticamente a aprovisionar nuevos recursos separados de RDS y S3. Es posible realizar ejercicios pequeños con SQLite/PVC; elija la arquitectura de producción a partir de los requisitos de concurrencia, durabilidad y recuperación.

## Arquitectura

| Capa | Responsabilidad y estado que se debe inspeccionar |
|---|---|
| Servidor HTTP | API del SDK, UI, proxy de artefactos; autenticación, autorización, política de host/CORS, workers |
| Base de datos de metadatos | metadatos de experimentos/ejecuciones/métricas/modelos/registry; pools, migraciones, copias de seguridad |
| Almacén de artefactos | archivos de modelos/datos/gráficos; bucket/prefijo, IAM, cifrado, retención |
| Almacén de autenticación | base de datos de usuarios/permisos, secretos de sesión/firma, caché del mecanismo de autenticación elegido |
| Estado de funcionalidades opcionales | colas, cachés y archivos temporales usados por los jobs habilitados, por el tracing/evaluación o por las funcionalidades de gateway |

PostgreSQL junto con S3 no convierte todas las funcionalidades en stateless. Por ejemplo, las bases de datos SQLite locales al Pod para basic-auth pueden dejar réplicas con usuarios o permisos distintos. Revise por separado las cachés del plugin OIDC y el almacenamiento de los jobs.

SQLite es una base de datos relacional y admite varios procesos con escrituras serializadas. No falla de inmediato cuando se conecta un segundo usuario. Sin embargo, archivos SQLite separados y locales al Pod no constituyen una base de datos compartida; incluso los archivos compartidos tienen restricciones de escritor, de bloqueo del sistema de archivos y de recuperación. Relacione la elección de PostgreSQL en producción con esos requisitos.

![El acceso protegido conduce a servidores MLflow que usan bases de datos de metadatos/autenticación y artefactos en S3. Los permisos IAM de S3 y los permisos de inicio de sesión de PostgreSQL son independientes; el estado compartido se externaliza antes de escalar réplicas.](../../.gitbook/assets/en-ai-ml-mlflow-03-eks-deployment-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-03-eks-deployment-0.html)

## Enfoques de instalación y fijación de versiones

| Vía | Qué se verificó |
|---|---|
| Chart comunitario | se descargó/renderizó `community-charts/mlflow` 1.11.7; appVersion 3.16.0, imagen por defecto `burakince/mlflow` |
| Chart del repositorio de MLflow | `v3.16.0/charts` contiene el chart 0.1.1 con appVersion 3.15.2; el tag del código fuente, la versión del chart y la versión de la imagen difieren |
| Manifiestos directos | una opción cuando se necesita control directo sobre la entrega de credenciales basada en archivos, la red, la autenticación o las políticas de migración |

Que el código exista en el repositorio upstream no demuestra que se publique un paquete OCI con la misma versión. La descarga del chart OCI oficial 0.1.1 devolvió `not found` durante la revisión, por lo que aquí no se presenta como un comando de instalación verificado.

Estos comandos inspeccionan los valores por defecto del chart mediante descubrimiento, descarga y renderizado. Prepare los values de producción por separado usando las comprobaciones siguientes.

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update community-charts
helm show chart community-charts/mlflow --version 1.11.7
helm pull community-charts/mlflow --version 1.11.7 --untar --untardir ./vendor
helm show values community-charts/mlflow --version 1.11.7 > values.reference.yaml
helm template mlflow ./vendor/mlflow --namespace mlflow -f values.reference.yaml > rendered.yaml
```

Inspeccione la imagen/digest renderizados, el ServiceAccount, la entrega de credenciales, los argumentos de CLI, las probes, el Service y el Ingress antes de aplicar. El chart usa por defecto una imagen comunitaria en lugar de la imagen upstream de MLflow; verifique también sus drivers de base de datos, el AWS SDK y los plugins de autenticación.

### Valores por defecto importantes del chart 1.11.7

- Los valores por defecto incluyen `replicaCount: 1`, `auth.enabled: false` e `ingress.enabled: false`.
- `backendStore.defaultSqlitePath: ":memory:"` configura los metadatos en memoria. **Esto difiere del nuevo valor por defecto de archivo SQLite de la CLI upstream.** Una instalación del chart con los valores por defecto no es un servicio de producción duradero.
- PostgreSQL externo se configura con `backendStore.postgres.*`; las referencias a credenciales usan `backendStore.existingDatabaseSecret.*`.
- Revise `artifactRoot.s3.*` junto con `artifactRoot.proxiedArtifactStorage: true`. El renderizado nativo produjo `--artifacts-destination=s3://...` y `--serve-artifacts`.
- La configuración de la base de datos de basic-auth es independiente y se encuentra en `auth.postgres.*`. Cambiar la base de datos de tracking no comparte automáticamente el estado de autenticación.
- `backendStore.databaseMigration: true` añade una ruta de init-container en el Pod. Planifique copias de seguridad, una única fase de migración coordinada y comprobaciones de compatibilidad antes de permitir que varias réplicas migren de forma concurrente.

Rellenar nombres sin valores reales ni Secrets no completa la configuración de producción. Algunas referencias de base de datos/autenticación de este chart se entregan a través de **variables de entorno del contenedor**. SecretKeyRef evita valores en texto plano en Git, pero no elimina la exposición en el entorno del proceso. Cuando la política prohíba valores secretos en el entorno, prepare archivos de credenciales suministrados desde Secrets Manager/SSM o un almacén equivalente, y un despliegue que consuma esos archivos. No incluya claves estáticas de AWS en los values de Helm ni en las imágenes.

## IAM y autenticación de base de datos

Limite los permisos de S3 al bucket/prefijo previsto. Según las operaciones reales, revise los permisos de `GetObject`, `PutObject`, listado, multipart y KMS. El modo proxy usa los permisos AWS del servidor; el modo de artefactos directo usa los permisos del cliente. Los URI de experimentos existentes no se reescriben solo por cambiar los flags del servidor.

EKS Pod Identity requiere el Agent, la asociación y un SDK compatible, y está dirigido a workers EC2 con Linux. No está disponible de forma universal para Pods de Fargate o de Windows. IRSA sigue siendo otra opción dentro de sus configuraciones compatibles. Especificar el nombre de un ServiceAccount o una anotación no completa la confianza IAM, la asociación ni la configuración del SDK.

Un rol de IAM para S3 no autoriza automáticamente el inicio de sesión en PostgreSQL. Verifique el acceso de red a la base de datos, la validación de TLS, los usuarios/credenciales o la autenticación IAM de base de datos configurada por separado. Revise la configuración de IMDS y del SDK para evitar un uso involuntario de las credenciales del rol del nodo como alternativa (fallback).

## Acceso al servidor y comprobaciones de salud

ClusterIP, los ALB privados y TLS proporcionan controles de red o de transporte; no sustituyen los permisos de MLflow por usuario. Utilice la arquitectura de ingress protegido de la organización en lugar de asumir una exposición pública directa mediante ALB.

Configure `allowed_hosts` y los orígenes CORS de MLflow 3.16.0 para los llamantes reales. En este chart comunitario, los argumentos de CLI correspondientes se pueden establecer mediante `extraArgs.allowedHosts` y `extraArgs.corsAllowedOrigins`. Las restricciones de host/CORS no sustituyen el inicio de sesión ni la autorización. En la versión 3.16.0, basic-auth pasó a una autorización fail-closed por defecto, así que valide la compatibilidad de los plugins de autenticación existentes y de los endpoints.

El endpoint de salud verificado es **`/health`**, implementado como un retorno de `"OK", 200`. Comprueba la capacidad de respuesta del proceso HTTP, no la conectividad continua con RDS/S3 ni la autorización del usuario. Esta versión exime a los endpoints de salud de la validación de host. Compruebe las rutas reales del servicio cuando use `static-prefix`, reescrituras de ingress o plugins.

## Notas operativas

Antes de escalar réplicas, comparta o externalice las bases de datos de metadatos/autenticación, los secretos de sesión y las colas/cachés habilitadas; pruebe el failover. Después aplique topology spread, PDB, readiness y límites de recursos. Dos Pods por sí solos no garantizan alta disponibilidad.

Una llamada a la API no siempre equivale a una escritura SQL. Mida en conjunto el logging por lotes, las transacciones, las cargas de trazas, el historial de métricas y los pools de conexiones por worker. Los pools de las distintas réplicas/workers se suman; la configuración de un pool no describe la demanda total de conexiones a la base de datos.

Aurora Serverless v2 opera dentro de los rangos de capacidad configurados y de las restricciones de conexiones, E/S y transacciones. No absorbe picos ilimitados ni garantiza un coste menor. Compárelo con RDS/Aurora provisionado frente a la carga medida y los requisitos de recuperación.

Realice copias de seguridad de las bases de datos de metadatos/autenticación y de los artefactos en conjunto, y pruebe la restauración. Evalúe las herramientas de borrado permanente, como `mlflow gc`, frente a la política de retención, en lugar de añadirlas como limpieza rutinaria. Los cambios de alias de modelos y el redespliegue del serving son también operaciones independientes.

## Fuentes principales

- [MLflow 3.16.0 release](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Arquitectura del tracking server](https://mlflow.org/docs/3.16.0/self-hosting/architecture/tracking-server/)
- [Chart comunitario](https://github.com/community-charts/helm-charts/tree/main/charts/mlflow)
- [Chart del repositorio de MLflow](https://github.com/mlflow/mlflow/tree/v3.16.0/charts)
- [Implementación de la salud del servidor](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/server/__init__.py)
- [Restricciones de EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Casos de uso y concurrencia de SQLite](https://www.sqlite.org/whentouse.html)
- [Configuración de capacidad de Aurora Serverless v2](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

[Página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
