# Cuestionario: implementación de MLflow en EKS

Este cuestionario evalúa tu comprensión de la arquitectura del tracking server de MLflow en EKS: el backend store, el artifact store, los patrones de acceso IAM y las consideraciones operativas para ejecutar el tracking server como un servicio compartido por el equipo.

## Preguntas de opción múltiple

1. ¿Cuál es la principal contrapartida de alojar por cuenta propia el tracking server de MLflow en EKS en lugar de usar una alternativa administrada como la capacidad de tracking compatible con MLflow de SageMaker?
   - A) El alojamiento propio siempre es más económico, independientemente del tamaño del equipo
   - B) Un equipo que ya usa EKS reutiliza sus patrones existentes de implementación, observabilidad e IAM, pero asume la operación del tracking server, el backend store y el artifact store
   - C) Las alternativas administradas no pueden registrar métricas ni parámetros
   - D) No hay ninguna contrapartida; las dos opciones son funcionalmente idénticas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un equipo que ya usa EKS reutiliza sus patrones existentes de implementación, observabilidad e IAM, pero asume la operación del tracking server, el backend store y el artifact store**

**Explicación:**
El alojamiento propio permite que un equipo reutilice los mismos patrones de implementación de Kubernetes, observabilidad e IAM (IRSA/Pod Identity) que ya utiliza para otras cargas de trabajo, a cambio de operar directamente el tracking server, su base de datos backend y su artifact store, en lugar de delegar esa tarea a una alternativa administrada.
</details>

2. ¿Por qué el backend store SQLite predeterminado de MLflow no es adecuado para un tracking server compartido por un equipo?
   - A) SQLite no puede almacenar valores de métricas de punto flotante
   - B) SQLite no admite el nivel de escrituras simultáneas que necesita un tracking server compartido
   - C) SQLite requiere un node group de EKS independiente
   - D) Los artifacts de SQLite expiran después de 30 días

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) SQLite no admite el nivel de escrituras simultáneas que necesita un tracking server compartido**

**Explicación:**
SQLite funciona bien para una sola persona que experimenta, pero deja de ser adecuado cuando más de un proceso necesita escribir simultáneamente: no admite la escala de escritores simultáneos que requiere un tracking server compartido por un equipo. Por eso una base de datos real, como RDS PostgreSQL o Aurora Serverless v2, lo reemplaza en producción.
</details>

3. ¿Qué tipo de datos contiene el backend store, en contraste con el artifact store?
   - A) El backend store contiene objetos binarios grandes, como modelos serializados; el artifact store contiene metadatos estructurados
   - B) El backend store contiene metadatos estructurados (experimentos, ejecuciones, parámetros, métricas, modelos registrados, versiones, alias); el artifact store contiene objetos binarios grandes (modelos, gráficos, conjuntos de datos)
   - C) Ambos stores contienen copias idénticas de todos los datos para redundancia
   - D) El backend store solo contiene nombres de usuario y contraseñas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El backend store contiene metadatos estructurados (experimentos, ejecuciones, parámetros, métricas, modelos registrados, versiones, alias); el artifact store contiene objetos binarios grandes (modelos, gráficos, conjuntos de datos)**

**Explicación:**
El backend store es una base de datos relacional que contiene todo lo que se puede consultar con SQL: experimentos, ejecuciones, parámetros, métricas, modelos registrados, versiones y alias. El artifact store (S3 en AWS) contiene los objetos binarios grandes que el backend store no almacena, como modelos registrados, gráficos y conjuntos de datos.
</details>

4. En AWS, ¿qué dos servicios son las opciones estándar para el backend store de MLflow en producción?
   - A) DynamoDB y EFS
   - B) Amazon RDS for PostgreSQL y Aurora Serverless v2
   - C) ElastiCache y S3
   - D) Redshift y Glacier

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Amazon RDS for PostgreSQL y Aurora Serverless v2**

**Explicación:**
Ambos son bases de datos relacionales reales que admiten escritores simultáneos. Vale la pena considerar Aurora Serverless v2 específicamente porque puede escalar con una carga de tracking irregular, en lugar de requerir que la base de datos se dimensione para la carga máxima durante todo el año.
</details>

5. ¿Cuál es el chart Helm de la comunidad mencionado para implementar MLflow en Kubernetes y cómo se agrega su repositorio?
   - A) `bitnami/mlflow`, agregado mediante `helm repo add bitnami https://charts.bitnami.com/bitnami`
   - B) `community-charts/mlflow`, agregado mediante `helm repo add community-charts https://community-charts.github.io/helm-charts`
   - C) No existe un chart de comunidad mantenido para MLflow
   - D) `mlflow/mlflow-operator`, instalado únicamente mediante `kubectl apply -f`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `community-charts/mlflow`, agregado mediante `helm repo add community-charts https://community-charts.github.io/helm-charts`**

**Explicación:**
`community-charts/helm-charts` mantiene un chart de MLflow que admite configuraciones de base de datos backend y object storage, y ofrece una alternativa práctica a escribir a mano tus propios manifiestos de Deployment/Service/Ingress.
</details>

6. ¿Qué mecanismo de EKS se presenta como la opción predeterminada más moderna para asociar un rol IAM al ServiceAccount del tracking server en una nueva implementación?
   - A) Claves de acceso IAM estáticas almacenadas en un ConfigMap
   - B) EKS Pod Identity, manteniendo IRSA como una opción válida para los clusters que ya están estandarizados en ella
   - C) Instance profiles asociados directamente a las instancias EC2 de los nodos de trabajo
   - D) Una credencial compartida de la cuenta raíz de AWS incorporada en la imagen del contenedor

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) EKS Pod Identity, manteniendo IRSA como una opción válida para los clusters que ya están estandarizados en ella**

**Explicación:**
EKS Pod Identity es el mecanismo más reciente para asociar roles IAM a Pods y cada vez más se recomienda como la opción predeterminada para nuevas asociaciones de IAM a Pod en EKS en general. IRSA sigue siendo una opción válida, especialmente para equipos o clusters que ya están estandarizados en ella.
</details>

7. ¿Por qué un tracking server de MLflow respaldado por Postgres puede ejecutar de forma segura varias réplicas, mientras que el valor predeterminado respaldado por SQLite no puede escalarse en absoluto?
   - A) Las réplicas de Postgres sincronizan automáticamente el estado en memoria entre Pods
   - B) El tracking server no tiene estado cuando está respaldado por Postgres y S3, ya que todo el estado compartido vive fuera del Pod, mientras que SQLite no tolera escritores simultáneos
   - C) SQLite requiere más CPU que Postgres, por lo que escalarlo es un desperdicio
   - D) Kubernetes prohíbe ejecutar más de una réplica de cualquier Deployment que use una base de datos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El tracking server no tiene estado cuando está respaldado por Postgres y S3, ya que todo el estado compartido vive fuera del Pod, mientras que SQLite no tolera escritores simultáneos**

**Explicación:**
Como todo el estado persistente reside en el backend store y el artifact store en lugar de en el Pod, un tracking server respaldado por Postgres no tiene estado y es seguro escalarlo horizontalmente. La falta de compatibilidad de SQLite con escritores simultáneos hace que sea inseguro escalar en absoluto el valor predeterminado de un solo proceso.
</details>

8. ¿Qué se describe como el siguiente paso natural después de que un modelo tiene una versión o un alias registrados, y por qué está fuera del alcance de esta serie?
   - A) Volver a ejecutar el trabajo de entrenamiento; está fuera del alcance porque el entrenamiento ya se cubrió en la Parte 1
   - B) Cargar esa versión del modelo en un sistema de serving (KServe, un wrapper personalizado, SageMaker, etc.); está fuera del alcance porque la infraestructura de serving es un tema amplio en sí mismo
   - C) Eliminar la versión del modelo; está fuera del alcance porque MLflow no admite la eliminación
   - D) Migrar el backend store a DynamoDB; está fuera del alcance porque DynamoDB no es compatible

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Cargar esa versión del modelo en un sistema de serving (KServe, un wrapper personalizado, SageMaker, etc.); está fuera del alcance porque la infraestructura de serving es un tema amplio en sí mismo**

**Explicación:**
Una vez que un modelo tiene una versión o un alias registrados, muchos equipos pasan a cargarlo en un sistema de serving, como KServe, un wrapper personalizado de FastAPI/Flask o SageMaker. Esa capa de serving es un tema amplio por derecho propio y queda explícitamente fuera del alcance de esta serie de tres partes.
</details>

## Preguntas de respuesta corta

9. Nombra las tres piezas principales de la arquitectura que deben implementarse para que MLflow se ejecute como un servicio compartido por un equipo en EKS y explica brevemente qué almacena o hace cada una.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
- El MLflow Tracking Server: un contenedor sin estado que ejecuta `mlflow server` y expone la API REST y la interfaz de usuario.
- El backend store: una base de datos relacional (por ejemplo, RDS PostgreSQL o Aurora Serverless v2) que contiene metadatos estructurados: experimentos, ejecuciones, parámetros, métricas, modelos registrados, versiones y alias.
- El artifact store: object storage (S3 en AWS) que contiene objetos binarios grandes, como modelos registrados, gráficos y conjuntos de datos.

**Explicación:**
Ninguna de las tres es opcional una vez que más de una persona comparte el tracking server: este necesita algún lugar persistente donde escribir tanto sus metadatos estructurados como sus artifacts grandes, y ninguno debe residir en el propio Pod del tracking server.
</details>

10. Explica por qué las probes de readiness y liveness son importantes para un Deployment de tracking server y por qué este documento no especifica una ruta exacta para el endpoint de health check.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Las probes de readiness y liveness permiten que el Service dirija tráfico únicamente a Pods que realmente pueden atender solicitudes, y permiten que Kubernetes reinicie automáticamente un Pod que ha dejado de responder: una práctica estándar para cualquier servicio de Kubernetes de larga ejecución. Este documento no indica una ruta exacta de health check porque puede variar según la versión de MLflow, por lo que debe confirmarse con la versión específica que se va a implementar en lugar de darla por supuesta.

**Explicación:**
Realizar probes contra una ruta de endpoint inventada o que no coincida con la versión marcaría los Pods saludables como no listos o no detectaría un Pod realmente bloqueado, por lo que verificar la ruta real para tu versión de MLflow es el enfoque más seguro.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/mlflow/03-eks-deployment.md)
