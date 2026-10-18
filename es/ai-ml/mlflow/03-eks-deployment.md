# Parte 3: Implementación de MLflow en EKS

> **Referencia de revisión**: MLflow 3.16.0 · community chart 1.11.7; última versión 3.17.1 comprobada · 2026-10-16

## Configuración del entorno de laboratorio

Prepare una versión de EKS Kubernetes compatible, una versión compatible de kubectl, Helm 3, una base de datos de metadatos y almacenamiento de artefactos. Un límite inferior como `kubectl >=1.34` no establece la compatibilidad con todos los servidores de API. Compruebe la política de desfase entre versiones del cliente y el servidor para el clúster real.

Este capítulo se basa en un chart descargado, la representación nativa de Helm y el código fuente del servidor de MLflow 3.16.0. **No demuestra que se hayan aprovisionado correctamente los recursos de AWS, que haya conectividad con RDS, que se hayan cargado archivos a S3 ni que se haya realizado la implementación en EKS.** Consulte la [Parte 1](01-tracking.md) para las comprobaciones locales de SQLite/API y la [Parte 2](02-model-registry.md) para las comprobaciones del Registry.

## Por qué ejecutar el servidor de Tracking de MLflow en EKS

Puede reutilizar patrones de implementación de Kubernetes, observabilidad e IAM, asumiendo la responsabilidad de los servidores, las bases de datos, los artefactos, el control de acceso, las copias de seguridad y las actualizaciones. SageMaker MLflow Apps y otros registros administrados son alternativas; sus versiones compatibles, autenticación, características y costos no son necesariamente idénticos.

Compartir con un equipo no requiere automáticamente aprovisionar nuevos recursos independientes de RDS y S3. Son posibles los ejercicios pequeños con SQLite/PVC; elija la arquitectura de producción según los requisitos de concurrencia, durabilidad y recuperación.

## Arquitectura

| Capa | Responsabilidad y estado que se debe inspeccionar |
|---|---|
| Servidor HTTP | API de SDK, UI, proxy de artefactos; autenticación, autorización, políticas de host/CORS, workers |
| Base de datos de metadatos | Metadatos de experimentos/ejecuciones/métricas/modelos/registro; pools, migraciones, copias de seguridad |
| Almacén de artefactos | Archivos de modelos/datos/gráficos; bucket/prefijo, IAM, cifrado, retención |
| Almacén de autenticación | Base de datos de usuarios/permisos, secretos de sesión/firma, caché del mecanismo de autenticación seleccionado |
| Estado opcional de características | Colas, cachés y archivos temporales utilizados por los trabajos habilitados, el tracing/evaluation o las características de gateway |

PostgreSQL más S3 no hace que todas las características sean sin estado. Por ejemplo, las bases de datos SQLite de basic-auth locales al Pod pueden dejar réplicas con distintos usuarios o permisos. Compruebe por separado las cachés de los plugins de OIDC y el almacenamiento de trabajos.

SQLite es una base de datos relacional y admite varios procesos con escrituras serializadas. No falla inmediatamente cuando se conecta un segundo usuario. Sin embargo, los archivos SQLite locales a distintos Pods no constituyen una base de datos compartida; incluso los archivos compartidos tienen limitaciones de escritura, bloqueo del sistema de archivos y recuperación. Relacione la selección de PostgreSQL para producción con esos requisitos.

![El acceso protegido permite que los servidores de MLflow utilicen bases de datos de metadatos/autenticación y artefactos de S3. Los permisos IAM de S3 y los permisos de inicio de sesión de PostgreSQL son independientes; el estado compartido se externaliza antes de escalar las réplicas.](../../.gitbook/assets/en-ai-ml-mlflow-03-eks-deployment-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-03-eks-deployment-0.html)

## Métodos de instalación y versiones fijadas

| Método | Qué se verificó |
|---|---|
| Community chart | se descargó y representó `community-charts/mlflow` 1.11.7; appVersion 3.16.0, imagen predeterminada `burakince/mlflow` |
| Chart del repositorio de MLflow | `v3.16.0/charts` contiene el chart 0.1.1 con appVersion 3.15.2; la etiqueta de origen, la versión del chart y la versión de la imagen son distintas |
| Manifiestos directos | una opción cuando la entrega de credenciales en archivos, las redes, la autenticación o las políticas de migración requieren control directo |

El código fuente en el repositorio upstream no demuestra que se haya publicado un paquete OCI con una versión idéntica. La descarga del chart OCI oficial 0.1.1 devolvió `not found` durante la revisión, por lo que no se presenta aquí como un comando de instalación verificado.

Estos comandos inspeccionan los valores predeterminados del chart mediante su descubrimiento, descarga y representación. Prepare los valores de producción por separado con las comprobaciones siguientes.

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update community-charts
helm show chart community-charts/mlflow --version 1.11.7
helm pull community-charts/mlflow --version 1.11.7 --untar --untardir ./vendor
helm show values community-charts/mlflow --version 1.11.7 > values.reference.yaml
helm template mlflow ./vendor/mlflow --namespace mlflow -f values.reference.yaml > rendered.yaml
```

Inspeccione la imagen/digest, ServiceAccount, entrega de credenciales, argumentos CLI, probes, Service e Ingress representados antes de aplicarlos. El chart utiliza por defecto una imagen comunitaria, no la imagen upstream de MLflow; verifique también sus drivers de bases de datos, AWS SDK y plugins de autenticación.

### Valores predeterminados importantes del chart 1.11.7

- Los valores predeterminados incluyen `replicaCount: 1`, `auth.enabled: false` e `ingress.enabled: false`.
- `backendStore.defaultSqlitePath: ":memory:"` configura metadatos en memoria. **Esto difiere del nuevo valor predeterminado del CLI upstream, que usa un archivo SQLite.** Una instalación predeterminada del chart no es un servicio de producción duradero.
- PostgreSQL externo utiliza `backendStore.postgres.*`; las referencias a credenciales utilizan `backendStore.existingDatabaseSecret.*`.
- Compruebe `artifactRoot.s3.*` junto con `artifactRoot.proxiedArtifactStorage: true`. La representación nativa produjo `--artifacts-destination=s3://...` y `--serve-artifacts`.
- La configuración de la base de datos de basic-auth se encuentra por separado en `auth.postgres.*`. Cambiar la base de datos de Tracking no comparte automáticamente el estado de autenticación.
- `backendStore.databaseMigration: true` agrega una ruta de init-container del Pod. Planifique las copias de seguridad, una fase de migración coordinada y las comprobaciones de compatibilidad antes de permitir que varias réplicas migren al mismo tiempo.

Completar los nombres sin valores reales ni Secrets no termina la configuración de producción. Algunas referencias a bases de datos/autenticación de este chart se entregan mediante **variables de entorno del contenedor**. SecretKeyRef evita los valores en texto sin formato en Git, pero no elimina la exposición en el entorno del proceso. Si la política prohíbe los valores de secretos en los entornos, prepare archivos de credenciales proporcionados desde Secrets Manager/SSM o un almacén equivalente, y una implementación que utilice esos archivos. No incluya claves estáticas de AWS en los valores de Helm ni en las imágenes.

## IAM y autenticación de bases de datos

Limite los permisos de S3 al bucket/prefijo previsto. Según las operaciones reales, compruebe los permisos de `GetObject`, `PutObject`, listado, cargas multiparte y KMS. El modo proxy utiliza los permisos de AWS del servidor; el modo de artefactos directos utiliza los permisos del cliente. Los URI de experimentos existentes no se reescriben simplemente al cambiar las opciones del servidor.

EKS Pod Identity requiere el Agent, una asociación y un SDK compatible, y está destinado a workers Linux EC2. No está disponible universalmente para Pods de Fargate ni de Windows. IRSA sigue siendo otra opción dentro de sus configuraciones compatibles. Especificar un nombre de ServiceAccount o una anotación no completa la configuración de confianza de IAM, la asociación ni la del SDK.

Un rol IAM para S3 no autoriza automáticamente el inicio de sesión en PostgreSQL. Verifique el acceso de red a la base de datos, la validación TLS, los usuarios/credenciales o la autenticación IAM de bases de datos configurada por separado. Revise IMDS y la configuración del SDK para evitar la alternativa no deseada de credenciales del rol del nodo.

## Acceso al servidor y comprobaciones de estado

ClusterIP, ALB privados y TLS proporcionan controles de red o de transporte; no reemplazan los permisos de MLflow por usuario. Utilice la arquitectura de ingreso protegida de la organización en lugar de dar por supuesto que se debe exponer directamente un ALB público.

Configure `allowed_hosts` y los orígenes CORS de MLflow 3.16.0 para los clientes reales. En este community chart, establezca los argumentos CLI correspondientes mediante `extraArgs.allowedHosts` y `extraArgs.corsAllowedOrigins`. Las restricciones de host/CORS no reemplazan el inicio de sesión ni la autorización.

La autorización de basic-auth cambió en 3.16.0 para denegar el acceso de forma predeterminada. La versión 3.16.1 eliminó la contraseña de administrador predeterminada incluida, así que no dependa de credenciales predeterminadas. Configure explícitamente una contraseña de administrador aprobada y los ajustes de autenticación antes del inicio. La combinación de chart y MLflow 3.16.0 de este capítulo no se volvió a validar en 3.16.1 ni en 3.17.x, y pasar a 3.17.0 o una versión posterior requiere una actualización del esquema del backend SQL.

El endpoint de estado verificado es **`/health`**, implementado como una respuesta `"OK", 200`. Comprueba que el proceso HTTP responde, no la conectividad continua con RDS/S3 ni la autorización de usuarios. Esta versión exime los endpoints de estado de la validación del host. Compruebe las rutas de servicio reales si utiliza `static-prefix`, reescrituras de ingress o plugins.

## Notas operativas

Antes de escalar las réplicas, comparta o externalice las bases de datos de metadatos/autenticación, los secretos de sesión y las colas/cachés habilitadas; pruebe la conmutación por error. Luego aplique la distribución de topología, PDBs, readiness y límites de recursos. Dos Pods por sí solos no garantizan alta disponibilidad.

Una llamada a la API no siempre equivale a una escritura SQL. Mida en conjunto el registro por lotes, las transacciones, las cargas de traces, el historial de métricas y los pools de conexiones por worker. Los pools de todas las réplicas/workers se acumulan; la configuración de un único pool no describe la demanda total de conexiones a la base de datos.

Aurora Serverless v2 opera dentro de rangos de capacidad configurados y está sujeto a límites de conexiones, E/S y transacciones. No absorbe ráfagas ilimitadas ni garantiza un menor costo. Compárelo con RDS/Aurora aprovisionado según la carga medida y los requisitos de recuperación.

Haga copias de seguridad de las bases de datos de metadatos/autenticación y de los artefactos conjuntamente, y pruebe la restauración. Revise las herramientas de eliminación permanente, como `mlflow gc`, con respecto a la política de retención en lugar de añadirlas como tareas de limpieza rutinarias. Los cambios de alias de modelos y la nueva implementación del servicio de inferencia también son operaciones independientes.

## Fuentes principales

- [Versión de mantenimiento de MLflow 3.16.1](https://github.com/mlflow/mlflow/releases/tag/v3.16.1)
- [Referencia de revisión de MLflow 3.16.0](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Arquitectura del servidor de Tracking](https://mlflow.org/docs/3.16.0/self-hosting/architecture/tracking-server/)
- [Community chart](https://github.com/community-charts/helm-charts/tree/main/charts/mlflow)
- [Chart del repositorio de MLflow](https://github.com/mlflow/mlflow/tree/v3.16.0/charts)
- [Implementación del estado del servidor](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/server/__init__.py)
- [Restricciones de EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Casos de uso y concurrencia de SQLite](https://www.sqlite.org/whentouse.html)
- [Configuración de capacidad de Aurora Serverless v2](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

[Página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
