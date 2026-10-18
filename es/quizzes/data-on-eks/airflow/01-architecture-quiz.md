# Cuestionario sobre la arquitectura de Airflow

Airflow 3.3.1 / chart de Helm 1.22.0 · septiembre de 2026.

## 1. ¿Qué descripción del análisis de DAG en Airflow 2 es correcta?

- A) Todos los archivos se analizaban únicamente en el mismo ciclo del scheduler
- B) Los DAG solo se leían desde Redis
- C) Ya existían subprocesos para procesar archivos y la opción de ejecutar el análisis de DAG de forma independiente
- D) Las tareas se ejecutaban sin analizarse

<details>
<summary>Mostrar respuesta</summary>

**C**

El scheduler podía iniciar un administrador con subprocesos por archivo o usar el procesamiento independiente. La planificación de DAG serializados y la alta disponibilidad con varios schedulers también existían antes de Airflow 3.

</details>

## 2. ¿Qué hace el procesador de DAG de Airflow 3?

- A) Ejecuta todos los operadores
- B) Solo emite tokens JWT para usuarios de la interfaz
- C) Sustituye al broker de Celery
- D) Analiza y serializa los DAG de los bundles, y actualiza los metadatos relacionados

<details>
<summary>Mostrar respuesta</summary>

**D**

Es un rol independiente obligatorio en Airflow 3. Los workers también necesitan el código y las dependencias de ejecución; colocar el código de DAG solo en el procesador no basta.

</details>

## 3. ¿Qué permite separar el procesador de DAG?

- A) Implementar y ajustar de forma más independiente el análisis y la planificación
- B) Eliminar toda latencia de planificación
- C) Eliminar los cuellos de botella de la base de datos
- D) Garantizar alta disponibilidad al aumentar el número de réplicas

<details>
<summary>Mostrar respuesta</summary>

**A**

La demora al analizar DAG nuevos, los recursos y la carga de la base de datos compartidos, y una concurrencia excesiva todavía pueden afectar a la planificación. La separación no reemplaza la validación operativa.

</details>

## 4. ¿Quién llama a la API durante una ejecución normal y supervisada de Python Task SDK?

- A) El código de la tarea del usuario ejecuta directamente consultas SQL de metadatos
- B) El supervisor del worker llama a Execution API usando un token JWT de tarea
- C) Redis transporta todo el acceso al estado
- D) Kubernetes almacena XCom

<details>
<summary>Mostrar respuesta</summary>

**B**

El ejecutor de tareas y el supervisor se comunican mediante un socket. Importan el direccionamiento, la autenticación y la red entre el worker y la API; inspecciona por separado elementos internos del executor, como los backends de resultados de Celery.

</details>

## 5. ¿Qué afirmación sobre el triggerer es correcta?

- A) Ejecuta todos los operadores completos
- B) Es obligatorio en cualquier implementación mínima
- C) Ejecuta los triggers de las tareas diferidas; después, los workers reanudan las tareas
- D) Todas las tareas asíncronas liberan espacios de worker

<details>
<summary>Mostrar respuesta</summary>

**C**

Se puede omitir en una implementación que no use tareas diferidas. Las tareas diferidas liberan espacios de worker y, normalmente, espacios de pool; el comportamiento del pool se puede configurar.

</details>

## 6. ¿Qué afirmación sobre las bases de datos de metadatos y los brokers de Celery es correcta?

- A) PostgreSQL y Redis son obligatorios en todas las implementaciones
- B) SQLite es la recomendación habitual para producción
- C) MariaDB y MySQL tienen la misma compatibilidad
- D) PostgreSQL/MySQL son compatibles y Celery tiene alternativas a Redis para el broker

<details>
<summary>Mostrar respuesta</summary>

**D**

Esta serie usa PostgreSQL como ejemplo. SQLite se usa para desarrollo y pruebas, MariaDB no es compatible y KubernetesExecutor no necesita necesariamente un broker de Celery.

</details>

## 7. ¿Qué clases híbridas fijas dejaron de ser compatibles en Airflow 3.0?

- A) LocalKubernetesExecutor y CeleryKubernetesExecutor
- B) LocalExecutor y CeleryExecutor
- C) KubernetesExecutor y todos los brokers
- D) Procesador de DAG y triggerer

<details>
<summary>Mostrar respuesta</summary>

**A**

Las clases híbridas fijas de dos vías son distintas de la configuración de executors concurrentes. Configura explícitamente los executors compatibles y selecciónalos por tarea.

</details>

## 8. ¿Cómo funcionan los executors concurrentes y los valores predeterminados de los DAG?

- A) Se introdujeron solo en la versión 3.3; también funcionan los executors no instalados
- B) Son compatibles desde la versión 2.10.0; usa `executor` en `default_args` del DAG y sobrescríbelo en las tareas
- C) Solo se permite uno en cualquier momento
- D) Todas las opciones usan únicamente nombres de colas de Redis

<details>
<summary>Mostrar respuesta</summary>

**B**

El primer executor configurado es el predeterminado. Las tareas seleccionan un nombre o alias configurado, y `default_args` del DAG puede proporcionar valores predeterminados para las tareas.

</details>

## 9. ¿Qué relación hay entre los bundles de DAG y git-sync?

- A) Airflow 3 eliminó git-sync
- B) Todos los S3DagBundle pasan a tener versiones al habilitar el versionado de S3
- C) git-sync sigue siendo compatible; el versionado depende del bundle
- D) Los workers nunca necesitan el código de DAG

<details>
<summary>Mostrar respuesta</summary>

**C**

GitDagBundle admite versionado; los bundles Local/S3/GCS revisados no. Verifica la distribución y la versión del código que se usa en los reintentos.

</details>

[Guía](../../../data-on-eks/airflow/01-architecture.md)
