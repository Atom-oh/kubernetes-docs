# Cuestionario avanzado de infraestructura

> **Documento relacionado**: [Infraestructura avanzada](../../ops/02-infrastructure-advanced.md)

## Preguntas de opción múltiple

### 1. ¿Qué significa una proporción de pesos 5:5 en un NLB?

- A) Crear cinco nodos en cada clúster
- B) Configurar una distribución relativa equitativa de los flujos nuevos
- C) Mover todas las conexiones existentes en cinco segundos
- D) Es inválido porque el total no es 100

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar una distribución relativa equitativa de los flujos nuevos**

Los pesos de NLB son enteros relativos de 0 a 999. Los bytes y las solicitudes observados pueden diferir según el tamaño del flujo, la persistencia y la ventana de observación.

</details>

### 2. ¿Qué hay que tener en cuenta al reducir a cero el peso de un grupo de NLB?

- A) Las conexiones existentes deben mantenerse hasta que se cierren de forma natural
- B) La guía actual indica que las conexiones existentes también se cierran al cabo de poco tiempo, por lo que hay que probar la reconexión
- C) El retraso de cancelación del registro garantiza todos los tiempos de transición
- D) Una respuesta correcta de la API significa que todo el tráfico ya se trasladó

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La guía actual indica que las conexiones existentes también se cierran al cabo de poco tiempo, por lo que hay que probar la reconexión**

Distingue los cambios normales de peso de las transiciones a cero. La aceptación de la configuración y la convergencia del plano de datos son cosas distintas; inspecciona los flujos nuevos y activos, los errores y la latencia.

</details>

### 3. Si los nombres DNS de blue y green apuntan al mismo NLB compartido, ¿qué pueden hacer los pesos de DNS?

- A) Seleccionar sus grupos de destino de forma independiente
- B) Fijar las solicitudes a una zona de disponibilidad usando solo el nombre de host
- C) Seleccionar el mismo balanceador; no eligen grupos de destino específicos de un clúster
- D) Seleccionar automáticamente la misma réplica de base de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Seleccionar el mismo balanceador; no eligen grupos de destino específicos de un clúster**

La selección basada en DNS requiere endpoints reales de balanceadores distintos que conduzcan a los clústeres previstos. Los pesos del listener y los pesos de los registros DNS operan en capas diferentes.

</details>

### 4. ¿Cómo se colocan las cargas de trabajo en nodos de Auto Mode en una zona de disponibilidad elegida?

- A) Pod nodeSelector crea nodos por sí solo
- B) Colocar subnet_ids en el NodePool
- C) Alinear la selección del Pod, los requisitos del NodePool, la selección de subredes del NodeClass y las tolerancias
- D) Ponerle al clúster el nombre blue

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Alinear la selección del Pod, los requisitos del NodePool, la selección de subredes del NodeClass y las tolerancias**

NodeSelector/affinity selecciona los nodos elegibles; también deben coincidir las restricciones de aprovisionamiento y las taints/tolerations. Distingue la colocación de los nodos de trabajo del plano de control administrado regional.

</details>

### 5. ¿Qué modelo de propiedad de TGB usa este ejemplo de un grupo de destino administrado externamente?

- A) El Auto Mode integrado siempre tiene un comportamiento de eliminación idéntico
- B) Un LBC instalado por separado con elbv2.k8s.aws/v1beta1, distinto del Auto Mode integrado
- C) Solo un ARN, sin requisitos previos de Service ni targetPort
- D) Direcciones IP permanentes de Pods registradas mediante Terraform

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un LBC instalado por separado con elbv2.k8s.aws/v1beta1, distinto del Auto Mode integrado**

Auto Mode integrado usa eks.amazonaws.com/v1 y documenta el comportamiento de eliminación de grupos de destino. Esta receta usa un controlador independiente para el registro dinámico y las reglas de red.

</details>

### 6. ¿Qué garantiza por sí solo un StatefulSet único de PostgreSQL con un PVC cuya política es Retain?

- A) Replicación entre clústeres
- B) Conmutación por error de la base de datos entre zonas de disponibilidad sin tiempo de inactividad
- C) Que todas las conexiones permanezcan abiertas
- D) Por sí solo, no garantiza alta disponibilidad, copias de seguridad ni recuperación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Por sí solo, no garantiza alta disponibilidad, copias de seguridad ni recuperación**

Retain es una política de retención de recursos. La replicación, las copias de seguridad, la propiedad del escritor y los procedimientos de recuperación son aspectos independientes. Los pesos de NLB no trasladan volúmenes de EBS entre zonas de disponibilidad.

</details>

### 7. ¿Por qué separar los temas de SNS para las entradas de alarmas y las notificaciones de decisiones?

- A) Evitar que las notificaciones vuelvan a recibirse como entrada y provoquen ejecuciones o errores adicionales
- B) Permitir publicaciones sin permisos de IAM
- C) Reintentar Lambda para siempre
- D) Eliminar el TTL de DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Evitar que las notificaciones vuelvan a recibirse como entrada y provoquen ejecuciones o errores adicionales**

Este controlador acepta el formato de evento de SNS. Los eventos de CloudWatch invocados directamente por Lambda tienen otro formato, así que no conectes ambas rutas de invocación. Un fallo de notificación no debe volver a ejecutar una mutación del listener que ya se completó correctamente.

</details>

### 8. ¿Qué hace el valor predeterminado automatic_failover=false?

- A) Trasladar inmediatamente todo el tráfico a Green
- B) Proponer cambios sin conceder el permiso ModifyListener
- C) Omitir las comprobaciones de estado
- D) Modificar todos los listeners disponibles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proponer cambios sin conceder el permiso ModifyListener**

Habilita el modo automático solo después de probar la capacidad, los SLO, la reconexión y la coordinación del escritor. Reserved concurrency=1 no serializa las escrituras externas de Terraform ni las manuales.

</details>

### 9. ¿Qué debe hacer un script de transición manual?

- A) Evaluar cadenas sin validar del usuario como expresiones aritméticas de Bash
- B) Suponer siempre un estado inicial 100/0
- C) Validar los pesos y el estado de los destinos, y luego mostrar y aprobar el plan completo
- D) Repetir un bucle temporizado con STEP=0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Validar los pesos y el estado de los destinos, y luego mostrar y aprobar el plan completo**

Valida primero los límites numéricos y usa las variables y el backend previstos. Comprueba los SLO reales y la compatibilidad de los datos entre etapas. Que la API o la aplicación terminen correctamente no demuestra por sí solo que la transición haya finalizado.

</details>

### 10. ¿Qué afirmación sobre el peso y el TTL de Route 53 es correcta?

- A) Los pesos son enteros de 0 a 255; el TTL por sí solo no garantiza el tiempo de recuperación
- B) Los pesos siempre van de 0 a 999
- C) Un TTL de 60 segundos equivale a un SLA de recuperación de 60 segundos
- D) Si todos los destinos tienen un estado no saludable, DNS debe indicar que no hay respuesta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Los pesos son enteros de 0 a 255; el TTL por sí solo no garantiza el tiempo de recuperación**

Los registros de alias heredan el TTL del destino. Ten en cuenta el estado de salud, las cachés de los resolutores, la duración de las conexiones y el comportamiento alternativo. Unos pesos de cero en todos los registros no son un método fiable para detener el tráfico.

</details>
