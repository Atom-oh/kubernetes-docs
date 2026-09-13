# Cuestionario sobre el Deployment de MLflow en EKS

## Preguntas de opción múltiple

1. ¿Cuál es la principal compensación del autoalojamiento en EKS?
   - A) Siempre tiene un costo menor que los servicios administrados
   - B) Reutilizar patrones de Kubernetes mientras se operan servidores, almacenes y controles de acceso
   - C) Los servicios administrados no pueden realizar seguimiento de experimentos
   - D) S3 y las bases de datos se crean automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Compare el trabajo operativo, las características, las versiones compatibles y la carga medida.
</details>

2. ¿Qué afirmación sobre la concurrencia de SQLite es correcta?
   - A) El segundo usuario siempre lo rompe de inmediato
   - B) Son posibles varios procesos y escrituras serializadas, con límites de escritor/bloqueo/archivo compartido
   - C) No es relacional
   - D) Los archivos locales del Pod separados forman automáticamente una DB compartida

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Distinga las capacidades de SQLite de la topología de almacenamiento de varios Pods.
</details>

3. ¿Cuál es el valor predeterminado de metadata del chart comunitario 1.11.7 revisado?
   - A) RDS PostgreSQL obligatorio
   - B) Objetos de S3
   - C) backendStore.defaultSqlitePath is :memory:
   - D) Un PVC duradero aprovisionado automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La anulación del chart difiere del nuevo valor predeterminado de archivo SQLite del CLI upstream.
</details>

4. ¿Una base de datos PostgreSQL de tracking externa comparte automáticamente todos los demás estados?
   - A) Sí, toda DB de autenticación y caché
   - B) Sí, toda la memoria de los workers
   - C) Sí, cada secreto de sesión
   - D) No; inspeccione las DB de autenticación, los secretos, las colas y las cachés independientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Compruebe el estado compartido de las características habilitadas antes de aumentar las réplicas.
</details>

5. ¿Cómo se deben manejar las versiones de chart, imagen y código fuente?
   - A) Siempre comparten un solo número
   - B) Una etiqueta de código fuente garantiza que existe el paquete OCI
   - C) Verifique cada una y descargue/renderice el paquete real
   - D) Una etiqueta latest elimina la necesidad de revisar los digests de imagen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El código fuente del chart upstream revisado y appVersion también diferían.
</details>

6. ¿El acceso IAM de ServiceAccount a S3 permite automáticamente el inicio de sesión en PostgreSQL?
   - A) Siempre
   - B) No; configure por separado la red de DB, TLS, los usuarios/credenciales o la autenticación IAM de DB
   - C) Solo si el nombre del bucket coincide
   - D) Coloque la contraseña de DB en la imagen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Estas son capas independientes de autorización y autenticación.
</details>

7. ¿Qué requiere EKS Pod Identity?
   - A) Compatibilidad incondicional con todos los Pods de Fargate y Windows
   - B) Solo un nombre de ServiceAccount
   - C) workers EC2 de Linux, Agent, asociación, SDK compatible y configuración relacionada
   - D) Una clave de acceso root estática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Compruebe por separado la compatibilidad y configuración de IRSA y Pod Identity.
</details>

8. ¿SecretKeyRef y allowed_hosts por sí solos completan la seguridad?
   - A) Eliminan la exposición del entorno e implementan toda la autorización de usuarios
   - B) No; revise por separado la entrega de secretos y la autenticación/autorización de la aplicación
   - C) Realizan automáticamente copias de seguridad de las bases de datos
   - D) Se deben permitir todos los orígenes de CORS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Comprenda la inyección de secretos en tiempo de ejecución y los límites de validación de hosts.
</details>

## Preguntas de respuesta corta

9. ¿Que /health devuelva 200 prueba que RDS y S3 están en buen estado?

<details>
<summary>Mostrar respuesta</summary>

No. La implementación verificada devuelve OK, 200 para la capacidad de respuesta del proceso HTTP. Compruebe por separado la base de datos continua, S3, la autorización y las rutas de carga de trabajo reales.
</details>

10. ¿Qué importa al evaluar el logging frecuente y Aurora Serverless v2?

<details>
<summary>Mostrar respuesta</summary>

Mida el batching, las transacciones, el historial de métricas, las cargas útiles de traces y los pools entre réplicas/workers. Aurora tiene límites de capacidad, conexiones, I/O y transacciones; no se garantiza una absorción de ráfagas ilimitada ni un costo mínimo.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/mlflow/03-eks-deployment.md)
