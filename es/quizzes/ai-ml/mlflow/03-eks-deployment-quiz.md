# Cuestionario sobre la implementación de MLflow en EKS

## Preguntas de opción múltiple

1. ¿Cuál es la principal disyuntiva al autoalojar MLflow en EKS?
   - A) Siempre tiene un costo menor que los servicios administrados
   - B) Reutilizar los patrones de Kubernetes a la vez que se operan los servidores, los almacenes y los controles de acceso
   - C) Los servicios administrados no pueden realizar seguimiento de experimentos
   - D) S3 y las bases de datos se crean automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Compara el trabajo operativo, las funciones, las versiones compatibles y la carga medida.
</details>

2. ¿Qué afirmación sobre la concurrencia de SQLite es correcta?
   - A) El segundo usuario siempre provoca un fallo inmediato
   - B) Se permiten varios procesos y las escrituras se serializan, aunque hay límites de concurrencia de escritura, de bloqueo y del archivo compartido
   - C) No es relacional
   - D) Los archivos locales de distintos Pods forman automáticamente una base de datos compartida

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Distingue las capacidades de SQLite de la topología de almacenamiento de varios Pods.
</details>

3. ¿Cuál es el valor predeterminado de metadatos del gráfico comunitario de Helm 1.11.7 revisado?
   - A) RDS PostgreSQL obligatorio
   - B) Objetos de S3
   - C) backendStore.defaultSqlitePath is :memory:
   - D) Un PVC duradero aprovisionado automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La configuración del gráfico difiere del nuevo valor predeterminado de la CLI oficial del proyecto, que usa un archivo SQLite.
</details>

4. ¿Una base de datos PostgreSQL externa para el seguimiento comparte automáticamente los demás datos de estado?
   - A) Sí, todas las bases de datos de autenticación y las cachés
   - B) Sí, toda la memoria de los procesos de trabajo
   - C) Sí, todos los secretos de sesión
   - D) No; verifica por separado las bases de datos de autenticación, los secretos, las colas y las cachés

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Antes de aumentar las réplicas, comprueba qué datos de estado deben compartir las funciones habilitadas.
</details>

5. ¿Cómo se deben gestionar las versiones del gráfico, de la imagen y del código fuente?
   - A) Siempre comparten el mismo número
   - B) Una etiqueta de código fuente garantiza que existe el paquete OCI
   - C) Verifica cada una y descarga e inspecciona el paquete real
   - D) Una etiqueta latest elimina la necesidad de revisar los resúmenes criptográficos de las imágenes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El código fuente revisado del gráfico y appVersion también diferían.
</details>

6. ¿El acceso de IAM a S3 de una ServiceAccount permite automáticamente iniciar sesión en PostgreSQL?
   - A) Siempre
   - B) No; configura por separado la red de la base de datos, TLS, los usuarios o credenciales y la autenticación de IAM para la base de datos
   - C) Solo si el nombre del bucket coincide
   - D) Coloca la contraseña de la base de datos en la imagen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Estas son capas independientes de autorización y autenticación.
</details>

7. ¿Qué requiere EKS Pod Identity?
   - A) Compatibilidad incondicional con todos los Pods de Fargate y Windows
   - B) Solo un nombre de ServiceAccount
   - C) Nodos de trabajo Linux en EC2, Agent, asociación, un SDK compatible y la configuración relacionada
   - D) Una clave de acceso root estática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Comprueba por separado la compatibilidad y la configuración de IRSA y Pod Identity.
</details>

8. ¿SecretKeyRef y allowed_hosts por sí solos bastan para proteger el sistema?
   - A) Evitan la exposición de variables de entorno e implementan toda la autorización de usuarios
   - B) No; revisa por separado la entrega de secretos y la autenticación y autorización de la aplicación
   - C) Realizan automáticamente copias de seguridad de las bases de datos
   - D) Se deben permitir todos los orígenes de CORS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Comprende cómo se inyectan los secretos en tiempo de ejecución y cuáles son los límites de la validación de hosts.
</details>

## Preguntas de respuesta corta

9. ¿Que /health devuelva 200 demuestra que RDS y S3 están en buen estado?

<details>
<summary>Mostrar respuesta</summary>

No. La implementación verificada devuelve OK, 200 para indicar que el proceso HTTP responde. Comprueba por separado el estado de la base de datos, S3, la autorización y las rutas reales de las cargas de trabajo.
</details>

10. ¿Qué debe tenerse en cuenta al evaluar el registro frecuente y Aurora Serverless v2?

<details>
<summary>Mostrar respuesta</summary>

Mide el procesamiento por lotes, las transacciones, el historial de métricas, el tamaño de las trazas y los grupos de conexiones entre réplicas y procesos de trabajo. Aurora tiene límites de capacidad, conexiones, E/S y transacciones; no se garantiza que absorba ráfagas sin límite ni que el costo sea mínimo.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/mlflow/03-eks-deployment.md)
