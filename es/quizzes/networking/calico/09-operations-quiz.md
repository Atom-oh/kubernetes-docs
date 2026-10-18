# Cuestionario de operaciones

> **Documento relacionado**: [Operaciones](../../../networking/calico/09-operations.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. ¿Qué afirmación describe correctamente quién debe encargarse de la instalación de Calico?
   - A) Instalar juntos el manifiesto y los operadores de Helm para tener redundancia
   - B) Elegir un único responsable —Operator/Helm o manifiestos directos— que se ajuste a la plataforma
   - C) Habilitar BPF es obligatorio en todas las instalaciones
   - D) Un manifiesto nuevo del Operator incluye automáticamente todos los CRD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Elegir un único responsable —Operator/Helm o manifiestos directos— que se ajuste a la plataforma**

**Explicación:**
El chart de Helm instala Tigera Operator. Usa un solo responsable, fija la versión, administra los CRD correspondientes y elige el perfil de red real. El ejemplo usa Calico CNI completo en Linux autogestionado; EKS VPC CNI con solo políticas es una configuración distinta.

</details>

2. ¿Qué inspecciona `calicoctl node status`?
   - A) Todos los nodos del contexto de kubeconfig
   - B) El estado BGP del nodo local, con el acceso necesario a ese nodo
   - C) La disponibilidad HTTP de todas las aplicaciones
   - D) Todas las fugas de asignaciones de IPAM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El estado BGP del nodo local, con el acceso necesario a ese nodo**

**Explicación:**
Es un diagnóstico BGP local, no una comprobación de disponibilidad de todo el clúster. Los perfiles que tienen BGP deshabilitado no necesitan obtener un resultado de BGP correcto. Selecciona el nodo afectado e inspecciona su socket BIRD real cuando corresponda.

</details>

3. ¿Qué información proporciona `calicoctl ipam show --show-blocks`?
   - A) El uso de bloques de Calico IPAM; la afinidad de nodo se inspecciona por separado
   - B) La liberación segura y automática de los bloques vacíos
   - C) Todas las asignaciones de ENI de VPC CNI
   - D) Una copia de seguridad transaccional del datastore

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El uso de bloques de Calico IPAM; la afinidad de nodo se inspecciona por separado**

**Explicación:**
El comando informa del uso de bloques y pools de IP. Usa BlockAffinity para consultar la relación entre bloques y nodos. Se aplica a Calico IPAM; para VPC CNI o host-local, inspecciona el asignador que realmente se esté usando.

</details>

4. ¿Qué tipo tiene `felix_int_dataplane_apply_time_seconds` en la versión revisada?
   - A) Counter de paquetes denegados
   - B) Histogram con series `_bucket` obligatorias
   - C) Summary con cuantiles, `_sum` y `_count`
   - D) Gauge de bloques de IP asignados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Summary con cuantiles, `_sum` y `_count`**

**Explicación:**
Es un Summary del tiempo incremental de aplicación del datapath. Un cuantíl local no equivale al p99 de todo el clúster. Usa las tasas de `_sum` y `_count` para calcular una media mientras haya observaciones; no inventes buckets de histogramas.

</details>

5. ¿Qué afirmación sobre los puertos de métricas de Typha es correcta?
   - A) El binario usa el puerto 9091 de forma predeterminada; la guía configura explícitamente las métricas de Typha del Operator en el 9093
   - B) Todas las instalaciones de Typha usan automáticamente el puerto 9093
   - C) Typha siempre comparte el puerto 9094 de kube-controllers
   - D) Basta con crear un Service para habilitar las métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El binario usa el puerto 9091 de forma predeterminada; la guía configura explícitamente las métricas de Typha del Operator en el 9093**

**Explicación:**
Las métricas de Typha están deshabilitadas de forma predeterminada. `typhaMetricsPort` del Operator habilita y configura la exposición de métricas y su Service. Un ServiceMonitor debe seleccionar el puerto correspondiente del Service y, a su vez, Prometheus debe seleccionarlo.

</details>

6. ¿Qué debes comprobar cuando un Pod no tiene una dirección IP?
   - A) Liberar inmediatamente una dirección y reiniciar todos los agentes de Calico
   - B) La programación y los eventos, el nodo seleccionado y el asignador CNI/IPAM real
   - C) Solo los registros DNS
   - D) Si todas las sesiones BGP tienen el mismo ASN

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La programación y los eventos, el nodo seleccionado y el asignador CNI/IPAM real**

**Explicación:**
Es posible que un Pod en estado Pending todavía no se haya programado. Si falla la asignación, inspecciona la evidencia de kubelet/CNI y del asignador, además de los pools elegibles y las restricciones de capacidad y afinidad. Los registros del proceso Felix no son la fuente de todos los errores de asignación de Pods.

</details>

7. ¿Qué debes incluir al solucionar problemas de BGP?
   - A) Solo una prueba de ping correcta
   - B) El estado de sesión del nodo afectado, direcciones de origen y par, ASN, TCP 179, autenticación/TTL y filtros
   - C) Cambiar al azar todos los ASN hasta que se abra una sesión
   - D) Leer el primer Pod de Calico del clúster, sin importar en qué nodo esté

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El estado de sesión del nodo afectado, direcciones de origen y par, ASN, TCP 179, autenticación/TTL y filtros**

**Explicación:**
Una conexión TCP no demuestra que BGP esté en estado Established ni que se acepten los prefijos. Comprueba las rutas esperadas y el socket BIRD IPv4/IPv6 correcto. Usa estas comprobaciones solo cuando el perfil de red elegido habilite BGP.

</details>

8. ¿Qué afirmación es correcta ante un aparente fallo de una política?
   - A) kube-proxy y la traducción de Service nunca pueden afectar la investigación
   - B) Las anotaciones de Pod enumeran todas las decisiones de políticas efectivas
   - C) Los registros Debug de Felix son automáticamente registros de denegación por paquete
   - D) Comprueba la identidad del endpoint, los selectores, la dirección, el nivel/orden, los flujos existentes y la ruta real de Service/datapath

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Comprueba la identidad del endpoint, los selectores, la dirección, el nivel/orden, los flujos existentes y la ruta real de Service/datapath**

**Explicación:**
Calico aplica la política, mientras que la traducción de Service, la selección de endpoints y los cambios de dirección de origen pueden afectar qué tráfico se evalúa. Inspecciona la ruta completa y prueba tanto los casos permitidos como los denegados, en vez de suponer que algún componente es irrelevante.

</details>

9. ¿Qué se requiere para actualizar Calico?
   - A) Modificar el DaemonSet administrado para quitar todos los agentes canary
   - B) Seguir el procedimiento de migración de CRD, Operator y datos almacenados correspondiente a la instalación y las versiones
   - C) Establecer siempre `Installation.spec.version` antes de empezar
   - D) Suponer que una reversión de Helm deshace todos los cambios en CRD y datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Seguir el procedimiento de migración de CRD, Operator y datos almacenados correspondiente a la instalación y las versiones**

**Explicación:**
Usa versiones de origen y destino compatibles, actualiza el responsable de instalación existente y administra los CRD antes de necesitar los campos nuevos. Prueba el despliegue y la recuperación. Un Operator antiguo o una exportación de YAML sin procesar no garantizan que se pueda volver a una versión anterior.

</details>

10. ¿Cómo debe introducirse una política de denegación predeterminada?
    - A) Validarla en un namespace seleccionado y permitir explícitamente las dependencias necesarias antes de ampliar el alcance
    - B) Aplicar de inmediato en todas partes una GlobalNetworkPolicy vacía para todos los endpoints
    - C) Inferir los endpoints del servidor de API a partir de una etiqueta de Pod inventada
    - D) Tomar un recuento de endpoints igual a cero como prueba de que la denegación funciona

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Validarla en un namespace seleccionado y permitir explícitamente las dependencias necesarias antes de ampliar el alcance**

**Explicación:**
Revisa explícitamente las rutas de DNS, API, identidad, monitorización y aplicaciones. Prueba casos positivos y negativos, conserva una vía de recuperación y contempla las políticas de endpoints de cargas de trabajo y de host.

</details>

11. ¿Qué descripción corresponde a la observabilidad de flujos actual en OSS?
    - A) `FlowLogsFileReporter` es un campo obligatorio de la API OSS
    - B) Cada registro de flujo corresponde exactamente a un paquete
    - C) Operator/Helm pueden desplegar Goldmane y Whisker; la guía actual de registros de flujo marca la función como vista previa técnica
    - D) Los registros de flujo y los registros de procesos de Felix son idénticos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Operator/Helm pueden desplegar Goldmane y Whisker; la guía actual de registros de flujo marca la función como vista previa técnica**

**Explicación:**
Goldmane proporciona datos de flujos agregados a Whisker. Está disponible en OSS con los requisitos previos de instalación documentados; los antiguos campos de registro a archivo/DNS no son un reemplazo válido. Protege los datos sensibles de flujos y ten en cuenta que la función sigue en vista previa.

</details>

12. ¿Cómo se puede configurar calicoctl para acceder al datastore de Kubernetes?
    - A) Establecer solo `CNI_PATH`
    - B) Usar `DATASTORE_TYPE=kubernetes` con acceso apropiado a kubeconfig, o un archivo de configuración explícito compatible
    - C) Se detecta automáticamente cualquier ruta arbitraria bajo `~/.config`
    - D) Un kubeconfig de Calico proporciona acceso al etcd administrado por EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar `DATASTORE_TYPE=kubernetes` con acceso apropiado a kubeconfig, o un archivo de configuración explícito compatible**

**Explicación:**
La guía muestra una configuración típica de entorno. También se admite una ruta explícita al archivo con `--config`. Selecciona el clúster previsto y configura RBAC; el acceso directo a etcdv3 corresponde a otra configuración de despliegue.

</details>
