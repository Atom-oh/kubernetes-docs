# Cuestionario de prácticas recomendadas y seguridad: parte 5

Spark 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4.

## 1. ¿Qué versiones de Hadoop/S3A coinciden con la distribución de Spark 4.2 revisada?

<details>
<summary>Mostrar respuesta</summary>

Tanto el cliente de Hadoop como `hadoop-aws` usan la versión 3.5.0, junto con el paquete de AWS SDK v2 2.35.4 y las dependencias de runtime resueltas. Vuelve a comprobar las versiones incluidas si usas otra imagen o EMR.

</details>

## 2. ¿Qué proveedor de IRSA es compatible con esta combinación de SDK v2?

<details>
<summary>Mostrar respuesta</summary>

`software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider`. En esta combinación, la clase antigua `com.amazonaws.auth.WebIdentityTokenCredentialsProvider` no se asigna automáticamente.

</details>

## 3. ¿Qué cambia al usar Pod Identity?

<details>
<summary>Mostrar respuesta</summary>

Usa `ContainerCredentialsProvider`, asociaciones de cuentas de servicio, confianza para `pods.eks.amazonaws.com` y permisos para el agente y los nodos. Las anotaciones de IRSA y la configuración de OIDC no reemplazan esta ruta.

</details>

## 4. ¿La cadena predeterminada de S3A usa IRSA automáticamente?

<details>
<summary>Mostrar respuesta</summary>

La cadena revisada de Hadoop 3.5.0 incluye el envoltorio de credenciales de contenedor o instancia, pero no el proveedor de identidad web. Especifica el proveedor requerido y verifica la identidad efectiva y el acceso al prefijo.

</details>

## 5. ¿Por qué separar las cuentas de servicio del driver, los executors y History Server?

<details>
<summary>Mostrar respuesta</summary>

Para separar los permisos de administración de Kubernetes del driver de los permisos de acceso a los datos en S3 de cada proceso. History Server puede iniciarse con un rol de solo lectura si se deshabilita su proceso de limpieza.

</details>

## 6. ¿Un Role con alcance de espacio de nombres restringe al driver a sus propios executors?

<details>
<summary>Mostrar respuesta</summary>

No. Concede permisos de recursos y verbos en todo el espacio de nombres, sin condiciones de propiedad basadas en las etiquetas de los pods. Combina controles de admisión y límites de confianza para restringir la creación de pods, otras cuentas de servicio y el acceso al host.

</details>

## 7. ¿ClusterRole siempre significa permisos para todo el clúster?

<details>
<summary>Mostrar respuesta</summary>

No. Un RoleBinding que referencia un ClusterRole puede limitar los permisos de recursos de espacio de nombres al espacio de nombres de la asociación. Inspecciona tanto las reglas como el tipo y alcance de la asociación.

</details>

## 8. ¿`spark.authenticate=true` proporciona inicio de sesión en Spark UI?

<details>
<summary>Mostrar respuesta</summary>

No. Autentica las conexiones internas. Los Secrets de aplicaciones que genera Kubernetes pueden propagarse por los entornos de los executors, por lo que importan los permisos de lectura de pods. La autenticación y autorización de la interfaz, y TLS, son aspectos independientes.

</details>

## 9. ¿Qué problema tiene una NetworkPolicy que se basa únicamente en la etiqueta del rol?

<details>
<summary>Mostrar respuesta</summary>

También coinciden los executors de otros trabajos del espacio de nombres. El ejemplo comparte un ID de ejecución único entre las etiquetas y políticas del driver y los executors. Las etiquetas no son autenticación; considera que quienes crean pods pueden falsificarlas.

</details>

## 10. ¿Aplicar esta NetworkPolicy bloquea todas las demás rutas?

<details>
<summary>Mostrar respuesta</summary>

Las políticas son aditivas y requieren que el CNI las aplique. Este ejemplo limita solo el ingreso. Revisa por separado el egreso, el comportamiento de los nodos y `hostNetwork`, otras políticas que permiten tráfico, DNS, la API, los endpoints de AWS y los plugins adicionales.

</details>

## 11. ¿Por qué combinar puertos fijos con `spark.port.maxRetries=0`?

<details>
<summary>Mostrar respuesta</summary>

Una colisión hace que el inicio falle en lugar de cambiar silenciosamente a un puerto fuera de la política. Configura los puertos y la seguridad por separado para los endpoints adicionales.

</details>

## 12. ¿PrometheusServlet y el endpoint agregado de executors son idénticos?

<details>
<summary>Mostrar respuesta</summary>

No. `/metrics/prometheus/` sirve el registro Dropwizard del driver; `/metrics/executors/prometheus/` sirve los agregados de executors recopilados por el driver. Los executors no tienen cada uno su propia Spark UI; compara las series, etiquetas y unidades reales.

</details>

## 13. ¿Qué es correcto sobre un agente Java de JMX y las métricas del chart del operador?

<details>
<summary>Mostrar respuesta</summary>

El agente se ejecuta dentro de la JVM, no como otro proceso. Las métricas predeterminadas del chart del operador describen al propio operador; el chart no instala automáticamente un agente en cada JVM de Spark.

</details>

## 14. ¿Crear un PodMonitor basta para recopilar métricas?

<details>
<summary>Mostrar respuesta</summary>

Los selectores de etiquetas y espacios de nombres de Prometheus, el RBAC de descubrimiento, los puertos y rutas de los pods, y NetworkPolicy deben coincidir. Verifica que los destinos aparezcan como UP y las series reales; los trabajos breves pueden terminar entre scrapes.

</details>

## 15. ¿Conservar el objeto del pod del driver también conserva su interfaz después de que termine el trabajo?

<details>
<summary>Mostrar respuesta</summary>

La interfaz activa deja de funcionar cuando se detiene su JVM. History Server reconstruye la información desde registros de eventos guardados por separado, no desde stdout/stderr ni desde checkpoints.

</details>

## 16. ¿Basta con montar un archivo de configuración para cargar la configuración de History Server?

<details>
<summary>Mostrar respuesta</summary>

No. El ejemplo usa explícitamente `spark-class org.apache.spark.deploy.history.HistoryServer --properties-file` y se ejecuta en primer plano. Verifica la ruta, el directorio de registros y la identidad de S3.

</details>

## 17. ¿History Server restaura todos los detalles de todos los trabajos anteriores?

<details>
<summary>Mostrar respuesta</summary>

Los registros de eventos deben conservarse y poder leerse. Los eventos faltantes, dañados, sin vaciar, eliminados o compactados limitan la reconstrucción. Los registros de eventos no son checkpoints de recuperación de datos ni copias de seguridad de resultados.

</details>

## 18. ¿Un operador, el modo clúster e IRSA son las únicas opciones de producción?

<details>
<summary>Mostrar respuesta</summary>

No. Elige entre el envío directo validado, un operador o EMR; el modo cliente o clúster adecuado; e IRSA o Pod Identity según los requisitos. Prueba los permisos, la exactitud de los datos, la recuperación, la red, los recursos y los costos en el entorno real.

</details>

[Guía](../../../data-on-eks/spark/05-best-practices.md)

[README](../../../data-on-eks/spark/README.md)
