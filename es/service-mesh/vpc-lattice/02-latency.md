# Análisis del impacto en la latencia

> **Alcance**: API de servicios/recursos de VPC Lattice y AWS Gateway API Controller; verifique la versión seleccionada y los CRD instalados.
> **Última actualización**: 13 de septiembre de 2026

## Qué abarca este documento

- Por qué migrar a Lattice introduce factores que aumentan y que reducen la latencia **al mismo tiempo**
- Por qué el resultado depende del entorno y no se puede predecir de antemano
- Qué medir y cómo hacerlo para obtener una respuesta: una matriz de mediciones de PoC

## Primero: este documento no proporciona cifras

El impacto en la latencia puede variar según la carga de trabajo. El procesamiento del proxy, las rutas de red, la reutilización de conexiones, la firma, la renovación de credenciales y la evaluación de políticas pueden cambiar el resultado. **Este capítulo no contiene mediciones de latencia de Lattice**, por lo que no afirma ni una magnitud ni una dirección garantizada.

Qué opción prevalece depende de factores como cuánta CPU de los nodos consumen actualmente los sidecars de Envoy, qué tan breves son las solicitudes (el peso relativo del costo fijo), si se usa keepalive, si está habilitada la autenticación IAM y qué proporción de llamadas cruza una AZ. Estos valores varían entre organizaciones.

Por tanto, la conclusión de este documento es **«hay que medirlo»** y su contenido explica **«qué medir para obtener una respuesta»**. A continuación, se organizan los factores por dirección y magnitud, y luego se presenta una matriz de medición que los aísla.

## Factores que aumentan la latencia

### 1. Se añade un recorrido por la red VPC

En AS-IS, el Envoy del emisor se conectaba **directamente a la IP del Pod receptor**. Si el Pod estaba en el mismo nodo, el tráfico nunca salía del par veth ni tocaba la NIC. En TO-BE, el destino es una dirección local de enlace de Lattice, y el tráfico **pasa por un endpoint de entrada de Lattice dentro de la VPC** antes de llegar al destino final.

La diferencia es mayor para la **comunicación Pod a Pod que antes ocurría en el mismo nodo**. Una ruta que en AS-IS terminaba dentro del kernel ahora sale del nodo, atraviesa Lattice y vuelve. Como referencia de base, la [prueba comparativa de red de Pods](../../networking/06-pod-network-benchmark.md) midió un RTT de 0.040 ms en el mismo nodo, 0.339 ms entre nodos de la misma AZ y 0.544 ms entre AZ. Si alguna ruta de llamada dependía de la proximidad dentro del mismo nodo, esa será la más afectada.

### 2. Sobrecarga de firma y verificación SigV4

Habilitar la autenticación IAM añade dos cálculos por solicitud.

- La firma del lado del emisor añade canonicalización y cálculo de firma. Lattice requiere `UNSIGNED-PAYLOAD`; no compare como trabajo de firma necesario de Lattice el hash genérico de la carga útil.
- La verificación del lado de Lattice y la evaluación de políticas habilitadas añaden trabajo. Mida la ruta completa en vez de suponer una duración por operación.

En realidad, el costo puede deberse menos a la criptografía en sí que a la **ruta de obtención de credenciales**. Con credenciales temporales, el proveedor configurado las almacena en caché y las renueva; IRSA usa STS, mientras que EKS Pod Identity usa el agente del nodo y EKS Auth. Una solicitud que espera la obtención o renovación puede incorporar esa latencia. Que afecte a p50, p99 o muestras más infrecuentes depende de la frecuencia de renovación y de la carga de trabajo; por ello, registre el comportamiento del proveedor/caché y la distribución de latencia alrededor de las renovaciones (consulte el [documento 03](./03-auth-flow.md)).

Si firma a través de un proxy de salida, añada el costo de otro salto de proxy.

### 3. Posible recorrido entre AZ

No dé por sentado que Lattice elige un destino en la misma AZ que el emisor. Si en AS-IS fijaba el tráfico dentro de una AZ mediante enrutamiento con conocimiento de zona o sugerencias de topología, debe confirmar por separado si esa optimización se conserva.

::: note Comportamiento de AZ documentado
AWS describe afinidad de AZ para la dirección de servicio/recurso que se devuelve al cliente, con alternativas si la AZ no está disponible. Los destinos de backend pueden abarcar AZ; la documentación del grupo de destino describe el enrutamiento por turnos. Esto no garantiza un backend en la misma AZ. Mida la ubicación real del destino en la PoC.

Por separado, **en la facturación no se cobra adicionalmente el tráfico entre AZ que pasa por Lattice**. Está incluido en el cargo por procesamiento de datos. Por tanto, durante esta migración el cruce entre AZ es **un factor de latencia, pero no un factor de facturación adicional**.
:::

### 4. Cambio en el patrón del protocolo de enlace TLS

En AS-IS, la conexión mTLS entre los Envoy era **una conexión de larga duración**. El costo del protocolo de enlace se pagaba una vez y muchas solicitudes usaban esa conexión.

En TO-BE, cambian el lugar y la frecuencia con que se establecen las conexiones. Establecer una conexión nueva requiere trabajo adicional; el protocolo de enlace TLS se aplica cuando se usa TLS. En la prueba HTTP de Pods citada, deshabilitar keepalive aumentó p50 de 0.461 → 1.079 ms en la misma AZ y de 0.704 → 1.517 ms entre AZ. Esas mediciones demuestran el efecto de reutilizar conexiones en esa configuración, no un costo aislado de TLS/Lattice ni que la reutilización importe más que un salto de proxy.

Por eso, durante la migración debe auditar la configuración del cliente HTTP de sus aplicaciones (tamaño del pool de conexiones, keepalive y tiempo de espera inactiva). No es una característica de Lattice; es una configuración del cliente que sale a la luz cuando desaparece el proxy que antes administraba las conexiones.

## Factores que reducen la latencia

### 1. Los recorridos por el proxy pasan de dos a uno

En AS-IS, cada solicitud pasa **dos veces** por un proxy: una vez por el Envoy del emisor (decisión de enrutamiento, inicio de mTLS y métricas) y otra por el Envoy del receptor (terminación de mTLS, autorización y métricas). Cada recorrido es un ciclo completo de recepción, procesamiento y envío en espacio de usuario.

Esto elimina los dos **recorridos de sidecar administrados por el cliente** de la ruta ilustrada. La implementación interna de Lattice, los proxies de firma y los cambios en las rutas de red impiden considerar garantizada una reducción de la latencia de extremo a extremo.

### 2. Desaparece la contención de CPU de los sidecars Envoy

En la práctica, este es el factor que más se suele subestimar.

Hay un sidecar Envoy por Pod y cada uno consume CPU del nodo. Cuando un nodo sufre presión de CPU, el proceso Envoy espera a que se le asigne tiempo de ejecución; esa espera se añade directamente a la latencia de solicitud. La característica de este fenómeno es que **apenas aparece en el promedio, pero se nota en la cola de la distribución**. La mayoría de las solicitudes se programan de inmediato; algunas esperan de varios milisegundos a decenas de milisegundos.

Eliminar el sidecar elimina la propia contención. Por tanto, **en clústeres con alta densidad de Pods y recursos de CPU limitados, p99 puede mejorar**. Al mismo tiempo, queda más CPU y memoria disponibles por nodo, lo que permite aumentar la densidad de Pods.

### 3. Cambia la convergencia de configuración

AWS administra el plano de datos de Lattice, pero la reconciliación del controlador, el registro de endpoints, las comprobaciones de estado y la propagación de políticas siguen llevando tiempo. AWS documenta que las actualizaciones de políticas de autenticación pueden tardar unos minutos. Mida la convergencia y el comportamiento del despliegue en vez de suponer que desaparece el retraso de propagación.

## Resumen de factores: signo y dónde se manifiestan

| Factor | Efecto | Métrica en que aparece | Condiciones que lo amplifican |
|---|---|---|---|
| Recorrido adicional por la red VPC | Aumenta | Tanto p50 como p99 | Gran proporción de tráfico en el mismo nodo/la misma AZ |
| Firma/verificación SigV4 | Aumenta | Un poco en p50, **p99** (renovación de credenciales) | Autenticación IAM habilitada, solicitudes breves |
| Recorrido entre AZ | Aumenta | p50, p99 | Dependía de enrutamiento con conocimiento de AZ |
| Cambio en el patrón de protocolo de enlace TLS | Aumenta | p50, p99 | Sin keepalive ni ajuste del pool de conexiones |
| Eliminación del sidecar | Posible mejora | p50, p99 | Depende del trabajo eliminado, la ruta de firma y la topología de red |
| Eliminación de la contención de CPU de Envoy | **Mejora** | **p99** | Existe presión de CPU en los nodos |
| Convergencia de configuración | Hay que medirla | Disponibilidad/latencia durante los cambios | Controlador, estado del destino y propagación de políticas |

El punto clave de esta tabla es que **p50 y p99 tienen composiciones de factores distintas**. Es probable que los factores que aumentan la latencia (la ruta añadida) dominen p50; los factores que la mejoran (la eliminación de la contención de CPU) pueden dominar p99. **Mirar solo el promedio oculta esta estructura.**

## Matriz de medición de PoC

Para observar estos factores por separado, separe las mediciones según estos ejes.

### Ejes de medición

| Eje o resultado | Valores | Propósito y límite |
|---|---|---|
| **Percentil** | p50, p99 | Describe la latencia central y de cola; atribuir causas requiere controles adicionales |
| **Ubicación de AZ** | Misma AZ / entre AZ | Comparar las rutas configuradas y registrar la ubicación del emisor y del destino seleccionado |
| **Autenticación IAM** | activada/desactivada en una prueba aislada aprobada | Efecto combinado de firma, credenciales y evaluación de políticas |

La ubicación de AZ y el modo de autenticación son ejes de configuración; p50/p99 son dos resultados de cada ejecución, no ensayos independientes. Use ejecuciones emparejadas repetidas, aleatorice el orden cuando sea práctico e informe también de errores/rendimiento además de latencia.

### Plantilla de tabla de medición

| Configuración | p50 misma AZ | p99 misma AZ | p50 entre AZ | p99 entre AZ |
|---|---|---|---|---|
| AS-IS: App Mesh (línea base) | | | | |
| TO-BE: Lattice, autenticación IAM **desactivada** | | | | |
| TO-BE: Lattice, autenticación IAM **activada** | | | | |

La diferencia entre autenticación activada y desactivada es el **efecto combinado de la firma, la gestión de credenciales y la evaluación de políticas habilitadas en esas condiciones**. La diferencia entre App Mesh y Lattice incluye los cambios de proxy, enrutamiento, TLS y otras configuraciones. Ninguna de las diferencias identifica un componente causal aislado sin controles adicionales.

### Condiciones que debe registrar además

Anotar solo las cifras hace imposible interpretarlas después. Registre también lo siguiente.

| Elemento | Motivo |
|---|---|
| **Uso de keepalive y ajustes del pool de conexiones** | Como se muestra, esto puede importar más que un salto de proxy. Si cambia entre celdas, estas no son comparables |
| **Tamaños de solicitudes/respuestas** | Cambian el peso relativo del costo fijo. La sobrecarga parece grande en solicitudes breves |
| **Nivel de carga (RPS) y concurrencia** | El comportamiento puede cambiar cerca de las cuotas |
| **Tipo de instancia de nodo y utilización de CPU del nodo durante la ejecución** | Base para interpretar el efecto de la contención de CPU. En las ejecuciones AS-IS, registre **por separado el uso de CPU del contenedor Envoy** |
| **Solicitudes/límites de recursos del sidecar en AS-IS** | Permite determinar si se producía limitación de CPU |
| **Herramienta y ajustes de medición** | `fortio`, `wrk2`, `k6`, etc. El cálculo de percentiles varía según la herramienta |
| **Marca temporal, región y AZ** | Reproducibilidad |

### Aspectos del diseño de medición que suelen pasarse por alto

**Primero, registre por separado las condiciones en frío y en caliente.** La primera solicitud puede incluir la obtención de credenciales y el establecimiento de conexiones si las credenciales o conexiones aún no están en caché. El proveedor determina la ruta de obtención, y la configuración TLS se aplica solo a conexiones TLS; ni una llamada directa a STS ni un protocolo de enlace TLS ocurren en cada primera solicitud. Mida el estado estable después del calentamiento y registre por separado la latencia de la primera solicitud, junto con el estado del proveedor, la caché y el transporte. Evalúe ambos casos para cargas de trabajo con arranques en frío frecuentes, como Lambda o servicios que escalan horizontalmente a menudo.

**Segundo, recopile suficientes muestras para que p99 sea significativo.** Con pocas solicitudes, p99 es ruido. Use valores recopilados después de decenas de miles de solicitudes bajo carga estable.

**Tercero, tenga en cuenta la profundidad de la cadena de llamadas.** Las mediciones de un solo salto sirven para aislar factores, pero la latencia real para el usuario es la suma de toda la cadena. La sobrecarga se acumula en cada salto Lattice adicional, así que **elija la ruta real de llamadas más profunda y mida también de extremo a extremo**. Esta perspectiva se relaciona directamente con la facturación (consulte el [documento 06](./06-constraints.md)).

**Cuarto, la posibilidad de observar directamente el salto de Lattice es limitada.** Lattice no crea spans de traza, por lo que tendrá que correlacionar las mediciones del cliente con los registros de acceso de Lattice. Asegúrese de incluir la **habilitación de los registros de acceso** en el plan de medición.

## Conclusión

- Este capítulo proporciona un diseño de medición, no mediciones de latencia de Lattice ni una mejora garantizada.
- p50 puede empeorar mientras que p99 puede mejorar. Evaluar un solo promedio oculta esta estructura.
- keepalive y los ajustes del pool de conexiones pueden importar más que el cambio del salto de proxy. Auditar la configuración del cliente es obligatorio durante la migración.
- Compare las configuraciones de AZ/autenticación con ejecuciones emparejadas repetidas; informe p50/p99, fallos y rendimiento de cada ejecución.

Siguiente: [Flujo detallado de autenticación IAM](./03-auth-flow.md) explica en qué consiste realmente la sobrecarga SigV4 y la dependencia de credenciales asociada.

## Referencias

- [Prueba comparativa de red de Pods](../../networking/06-pod-network-benchmark.md): RTT medidos en el mismo nodo, la misma AZ y entre AZ, y efecto de keepalive
- [Precios de Amazon VPC Lattice](https://aws.amazon.com/vpc/lattice/pricing/): el tráfico entre AZ está incluido en el procesamiento de datos
- [Registros de acceso de Amazon VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [Supervisión de Amazon VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-overview.html)

La prueba comparativa de Pods enlazada es una línea base de carga de trabajo distinta. Sus cifras HTTP con keepalive no son mediciones de protocolos de enlace TLS ni de Lattice.
