# Cuestionario sobre Spark Operator

Base: Kubeflow 2.5.2 y Apache operator 1.0.0 / chart 1.8.0.

## 1. ¿Qué relación hay entre los dos operadores de Spark?

- A) Es el mismo chart con otro nombre
- B) Uno reemplazó al otro cuando terminó el soporte de Kubeflow
- C) Son proyectos distintos, con API y modelos de ciclo de vida diferentes
- D) Son totalmente compatibles si solo se cambia apiVersion

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Kubeflow usa sparkoperator.k8s.io/v1beta2; este capítulo usa spark.apache.org/v1. También hay que revisar la migración de campos, estados y comportamiento de reintentos.

</details>

## 2. ¿Qué chart acompaña al Apache operator 1.0.0 revisado?

- A) Necesariamente 1.0.0
- B) 2.5.2, como Kubeflow
- C) 4.2.0, como Spark
- D) 1.8.0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Las versiones del chart y de la aplicación son independientes. Comprueba los metadatos de versiones/publicaciones y los recursos renderizados.

</details>

## 3. ¿Qué se necesita para Comet o Gluten?

- A) Plugins, imágenes, classpaths y configuración compatibles
- B) Solo instalar Apache operator
- C) Comportamiento idéntico en todas las arquitecturas y versiones de Spark
- D) Kubeflow nunca puede ejecutar estas cargas de trabajo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Los ejemplos oficiales tienen requisitos previos adicionales. Elegir un operador no garantiza por sí solo la aceleración ni la compatibilidad de los plugins.

</details>

## 4. ¿Qué afirmación sobre spark-submit simple es correcta?

- A) Siempre envía el trabajo y se desconecta
- B) Puede esperar y mostrar registros; la reconciliación del CR del operador es independiente
- C) No puede crear Pods executor
- D) Su configuración no se puede versionar en Git

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El envío Native ofrece acceso al estado, los registros y la interfaz de usuario. Un operador agrega gestión del ciclo de vida de CR, controladores programados y reintentos de aplicaciones.

</details>

## 5. ¿Cuál es el valor predeterminado de webhook.enable en Kubeflow 2.5.2?

- A) false
- B) Cambia automáticamente según la versión de Spark
- C) true
- D) true solo en el espacio de nombres de instalación predeterminado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El ejemplo explicita el valor predeterminado. Si se deshabilita, revisa las funciones que dependen de esa ruta de admisión.

</details>

## 6. ¿En qué se diferencian los charts revisados con respecto a la admisión?

- A) Ambos instalan el mismo mutador de Pods
- B) Los webhooks colocan Pods en los nodos
- C) Los webhooks asignan tareas de Spark
- D) Apache no instala un webhook equivalente al webhook mutador de Pods de Kubeflow

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

El diagrama ilustra Kubeflow. La programación de Kubernetes y la asignación de tareas a ejecutores de Spark siguen siendo responsabilidades independientes.

</details>

## 7. ¿Qué se necesita para los trabajos en spark-jobs?

- A) Alinear el espacio de nombres observado, el espacio de nombres del trabajo y RBAC
- B) Enviar todos los trabajos solo al espacio de nombres de instalación
- C) Un ClusterRole hace irrelevante el ámbito de observación
- D) Observar default incluye automáticamente todos los espacios de nombres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Los espacios de nombres de instalación y de las cargas de trabajo pueden ser distintos. El ámbito de observación predeterminado no incluye automáticamente un espacio de nombres nuevo para trabajos.

</details>

## 8. ¿Dónde se declaran los volúmenes personalizados de Kubeflow?

- A) Solo en spec.driver.volumes
- B) En spec.volumes, con driver/executor.volumeMounts
- C) Solo en spec.executor.volumes
- D) En status.volumes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El CRD revisado no tiene campos driver.volumes ni executor.volumes. Declara las definiciones de volúmenes compartidos en spec.volumes y móntalos donde se necesiten.

</details>

## 9. ¿Qué tienen de especial los volúmenes spark-local-dir-?

- A) Crean automáticamente discos NVMe físicos
- B) Convierten todos los volúmenes a S3
- C) Se traducen a la configuración nativa de volúmenes locales de Spark
- D) El webhook debe ser la única ruta de implementación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El mutador genérico de volúmenes omite estos volúmenes de directorios locales; la configuración del envío se ocupa de ellos. emptyDir no selecciona por sí solo almacenamiento físico.

</details>

## 10. ¿Qué campos serviceAccount son válidos en Kubeflow 2.5.2?

- A) Solo driver.serviceAccount
- B) Solo executor.serviceAccount
- C) Ambos deben contener ARN de IAM de AWS
- D) Tanto driver.serviceAccount como executor.serviceAccount

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Ambos campos indican cuentas de servicio de Kubernetes. RBAC de API y permisos de datos de AWS se configuran por separado.

</details>

## 11. ¿Cómo debe configurarse una ejecución diaria de ScheduledSparkApplication a las 02:00 UTC?

- A) Usar schedule: "0 2 * * *" y timeZone: UTC
- B) Depender siempre de la hora local del controlador
- C) timeZone no es compatible
- D) Configurar solo la TZ del Pod executor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

La versión 2.5.2 admite timeZone y usa Local de forma predeterminada. Una zona horaria explícita para la programación evita depender del entorno del controlador.

</details>

## 12. ¿Qué impide concurrencyPolicy: Forbid?

- A) Escrituras duplicadas en todos los sistemas
- B) La superposición entre una ejecución anterior de un recurso programado y su siguiente ejecución programada
- C) Todos los reintentos de aplicaciones
- D) Todos los envíos manuales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Otros planificadores, las ejecuciones manuales y los reintentos aún pueden provocar efectos secundarios duplicados. Diseña salidas idempotentes o transaccionales.

</details>

## 13. ¿Qué hace suspend: true?

- A) Necesariamente termina el trabajo secundario activo
- B) Revierte los datos ya escritos
- C) Detiene las futuras activaciones programadas
- D) Elimina la implementación del operador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Inspecciona o termina las ejecuciones actuales por separado. Suspender no revierte datos ni es una copia de seguridad.

</details>

## 14. ¿Qué garantiza cambiar únicamente sparkVersion a 4.2.0?

- A) La actualización automática del entorno de ejecución del controlador
- B) La compatibilidad con todos los plugins de Spark
- C) La actualización automática de Kubernetes
- D) No garantiza que se actualice el spark-submit del controlador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

El laboratorio de Kubeflow coincide con el entorno de envío del controlador, 4.0.4. Prueba por separado otras combinaciones de herramientas de envío y cargas de trabajo.

</details>

## 15. ¿Qué estados de los Pods observa el operador?

- A) Tanto los del driver como los del executor
- B) Solo los del driver
- C) Solo los del executor
- D) Ningún estado de Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

El controlador también actualiza el estado de los ejecutores y realiza la limpieza. El driver de Spark solicita los ejecutores y asigna las tareas de Spark.

</details>

## 16. ¿Qué es importante al usar reintentos OnFailure?

- A) Las escrituras exactamente una vez se realizan automáticamente
- B) Las reejecuciones de la aplicación pueden repetir efectos secundarios de salida
- C) Siempre se reinicia únicamente el mismo contenedor
- D) Todas las transacciones externas fallidas se revierten

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los intentos de envío/aplicación son distintos de los reinicios de contenedores. Valida también la semántica de los datos, junto con los recuentos e intervalos de reintentos.

</details>

## 17. ¿En qué se diferencian IRSA y EKS Pod Identity?

- A) Ambos solo necesitan la misma anotación
- B) Un Role de Kubernetes otorga acceso a S3
- C) IRSA usa OIDC/anotaciones de rol; Pod Identity usa asociaciones y su Agent
- D) Una URI S3 completa la autenticación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Configura permisos de AWS, confianza o asociación y proveedores de credenciales compatibles. Verifica la identidad efectiva y el acceso en los Pods reales.

</details>

## 18. ¿Qué expone el endpoint Prometheus predeterminado del chart en el puerto 8080?

- A) Recopilación automática de JMX de todas las JVM de Spark
- B) Todos los registros de Spark History Server
- C) Resultados de validación de datos S3
- D) Métricas del operador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

JMX de la carga de trabajo requiere su propio JAR de exporter de la aplicación, configuración y ajustes de scraping.

</details>

## 19. ¿Cómo deben gestionarse los CRD durante las actualizaciones de Helm?

- A) Revisar la migración de CRD y la opción explícita hook.upgradeCrd
- B) helm upgrade normal siempre los reemplaza
- C) Eliminar siempre los CRD existentes antes
- D) No pueden afectar los recursos de la aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Las actualizaciones normales no reemplazan automáticamente los CRD de crds/. Eliminar un CRD afecta a sus recursos personalizados y no es un paso habitual de actualización.

</details>

## 20. ¿Qué demuestran una renderización correcta de Helm y las comprobaciones de CRD?

- A) Prueban que la conectividad activa del webhook funciona
- B) La forma de los recursos y las rutas de configuración; que la carga de trabajo activa funcione es otra cuestión
- C) Prueban el acceso a S3 y la corrección de los datos
- D) La compatibilidad con todas las versiones de Spark

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Inspecciona también los Pods reales, el estado, las salidas, el comportamiento de reintentos y los permisos. COMPLETED por sí solo no demuestra que los datos externos sean correctos.

</details>

[Texto / Guía](../../../data-on-eks/spark/02-spark-operator.md)
