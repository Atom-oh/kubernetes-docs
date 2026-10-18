# Parte 7: Cuestionario de monitoreo

Repasa los nombres reales de las métricas, el alcance del scraping y cómo tratar los datos ausentes, el lag y el comportamiento de KEDA con autenticación.

## 1. ¿Cómo se ejecuta el enfoque JMX de este capítulo y es la única opción de métricas de Strimzi?

<details>
<summary>Mostrar respuesta</summary>

JMX Exporter se ejecuta como agente Java en la misma JVM. Strimzi también admite `strimziMetricsReporter`. Al cambiar entre opciones, revisa los nombres, la configuración y los paneles.

</details>

## 2. ¿En qué se diferencian las reglas de asignación de MBeans de JMX del reetiquetado de PodMonitor?

<details>
<summary>Mostrar respuesta</summary>

Las reglas JMX del ConfigMap asignan MBeans a nombres de métricas y etiquetas. El reetiquetado de PodMonitor es una etapa de descubrimiento independiente que aporta contexto del destino, como el espacio de nombres, `kafka_cluster` y el rol.

</details>

## 3. ¿Un valor de UnderReplicatedPartitions superior a cero significa que ya se han perdido datos?

<details>
<summary>Mostrar respuesta</summary>

No. En estado estable, el valor saludable es cero, pero los fallos, el retraso o las operaciones planificadas pueden elevarlo. Comprueba cuánto dura, si hay particiones por debajo del mínimo de ISR o particiones sin conexión, y cuál es la causa.

</details>

## 4. ¿Se puede diagnosticar de inmediato una condición de split-brain si la suma de controladores activos es dos?

<details>
<summary>Mostrar respuesta</summary>

No. Primero comprueba el alcance del clúster, los destinos duplicados, las muestras obsoletas y el momento del scraping. En estado estable, la suma de los controladores de un clúster debe ser uno.

</details>

## 5. ¿Qué métricas deberías correlacionar con un valor bajo de BrokerRequestHandlerAvgIdlePercent?

<details>
<summary>Mostrar respuesta</summary>

Pon ese valor en correlación con CPU, GC, E/S, latencia y colas de solicitudes, y caudal de tráfico. Indica que los procesadores de solicitudes están ocupados, pero no permite atribuirlo solo a la CPU ni justifica automáticamente añadir hilos o brokers.

</details>

## 6. ¿El mapeo JMX del broker calcula por sí solo el lag del grupo de consumidores?

<details>
<summary>Mostrar respuesta</summary>

No. Se necesitan los offsets confirmados del grupo y los offsets al final de cada partición. Este capítulo usa Strimzi Kafka Exporter; KEDA consulta las API de Kafka de forma independiente.

</details>

## 7. Indica la métrica de lag y la etiqueta de grupo del Kafka Exporter elegido, y explica el estado del proyecto anterior.

<details>
<summary>Mostrar respuesta</summary>

`kafka_consumergroup_lag` y `consumergroup`. El proyecto anterior seglo/kafka-lag-exporter está archivado; no confundas su convención `kafka_consumergroup_group_lag`/`group` con la de este exportador.

</details>

## 8. ¿PodMonitor es siempre más fiable que ServiceMonitor?

<details>
<summary>Mostrar respuesta</summary>

No. ServiceMonitor funciona si el Service y sus selectores son correctos. Este capítulo elige el descubrimiento directo de pods; comprueba los selectores de etiquetas y espacios de nombres de Prometheus, RBAC, conectividad de red y que no se duplique el scraping.

</details>

## 9. Explica cómo funciona `for: 5m` y qué ocurre cuando faltan datos en una PrometheusRule.

<details>
<summary>Mostrar respuesta</summary>

La condición debe estar presente y seguir siendo verdadera durante cinco minutos antes de que se active la alerta. No es un intervalo de scraping ni un promedio. Si falta una familia de métricas, una comparación con una suma puede no devolver resultados; incluye comprobaciones de ausencia y de cobertura del scraping.

</details>

## 10. ¿El escalador Kafka de KEDA necesita un exportador de lag de Prometheus?

<details>
<summary>Mostrar respuesta</summary>

No. Consulta directamente las API de Kafka y necesita su propia conectividad con los brokers, TLS, autenticación y acceso al Secret. Es una vía distinta de la que usa el exportador de los paneles.

</details>

## 11. ¿Un lag igual a cero demuestra que el procesamiento de negocio ha terminado?

<details>
<summary>Mostrar respuesta</summary>

No. Normalmente mide el offset siguiente al final del log menos el siguiente offset confirmado. Las confirmaciones anticipadas o las condiciones de los datos y de su recopilación pueden hacer que difiera de la finalización del procesamiento de negocio. La compactación del log y las transacciones también pueden hacer que difiera del recuento físico de registros.

</details>

## 12. ¿Cómo se deben consultar bytesin_total e idle_percent?

<details>
<summary>Mostrar respuesta</summary>

Aplica `rate(...[5m])` al contador bytesin_total para obtener el throughput por segundo. idle_percent ya es una métrica gauge de proporción; consúltala directamente, sin volver a aplicarle rate.

</details>

## 13. Explica `lagThreshold=50` con `minReplicaCount=1`.

<details>
<summary>Mostrar respuesta</summary>

El objetivo es un lag total efectivo de 50 por réplica; aproximadamente ceil(total lag/50), sujeto a los ajustes y límites del HPA y del escalador. No crea varios consumidores por partición. Con min=1, revisa el comportamiento de reducción de escala del HPA, no la activación ni el periodo de espera del escalado desde cero.

</details>

## 14. ¿Qué revelan los cambios de ISR y el throughput de los temas, y cuáles son sus límites?

<details>
<summary>Mostrar respuesta</summary>

Las tasas de los contadores de reducción y ampliación de ISR muestran cambios que se pueden correlacionar con la salud de la replicación. El throughput agregado de un tema no permite identificar una partición con mucha carga; añade observaciones por partición y cliente.

</details>

## 15. Escribe el parche que añade metricsConfig y Kafka Exporter de este capítulo al recurso Kafka existente.

<details>
<summary>Mostrar respuesta</summary>

```yaml
spec:
  kafka:
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
  kafkaExporter:
    topicRegex: ^orders$
    groupRegex: ^order-processor$
    showAllOffsets: true
    template:
      pod:
        metadata:
          labels:
            docs.example.com/kafka-monitor: lag
```

Crea primero metrics-config.yaml y después ejecuta `kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml`. No es un manifiesto completo para crear un recurso Kafka; conserva la autenticación y los listeners existentes.

</details>

## 16. Escribe el ScaledObject que usa TLS/SCRAM y un TriggerAuthentication en el mismo espacio de nombres.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-consumer-scaler
  namespace: kafka
spec:
  scaleTargetRef:
    name: order-consumer
  minReplicaCount: 1
  maxReplicaCount: 10
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9093
      version: 4.3.1
      consumerGroup: order-processor
      topic: orders
      tls: enable
      sasl: scram_sha512
      lagThreshold: '50'
      allowIdleConsumers: 'false'
      offsetResetPolicy: earliest
    authenticationRef:
      name: kafka-lag-auth
```

Requiere el archivo keda-auth.yaml del capítulo y el Deployment kafka/order-consumer existente. La aplicación debe consumir como order-processor. El máximo de 10 se ajusta a las 12 particiones de la Parte 2; adáptalo a otras topologías.

</details>

## 17. ¿Cómo se deben separar el alcance del clúster, `for` y el tratamiento de datos ausentes en una alerta de subreplicación?

<details>
<summary>Mostrar respuesta</summary>

Limita la métrica a namespace="kafka" y kafka_cluster="my-cluster", calcula la suma por clúster y aplica `for: 5m` a la condición >0. Añade reglas independientes para la cobertura del scraping de los nodos y la ausencia de la métrica del controlador. Para el lag, supervisa también los fallos del exportador, la ausencia de los grupos esperados y los offsets confirmados negativos.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/kafka/07-monitoring.md) | [Cuestionario anterior](./06-msk-integration-quiz.md) | [Cuestionario siguiente](./08-best-practices-quiz.md)
