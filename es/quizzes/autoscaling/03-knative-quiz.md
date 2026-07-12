# Cuestionario de Knative

1. ¿Cómo funciona Scale-to-Zero en Knative Serving?
   - A) Elimina Pods y vuelve a crear el Deployment ante nuevas solicitudes
   - B) Activator almacena temporalmente el tráfico mientras Autoscaler escala las réplicas de 0 a 1
   - C) Apaga Nodes y hace que Karpenter aprovisione nuevos Nodes bajo solicitud
   - D) Pausa los contenedores y los reanuda bajo solicitud

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Activator almacena temporalmente el tráfico mientras Autoscaler escala las réplicas de 0 a 1**

**Explicación:**
Cuando las réplicas están en 0, las solicitudes entrantes son almacenadas temporalmente por Activator. Activator solicita un escalado hacia arriba a Autoscaler y, una vez que los Pods están listos, las solicitudes almacenadas se reenvían. Este proceso es el "cold start" (arranque en frío), que se puede evitar configurando `minScale` para mantener instancias mínimas.

</details>

---

2. ¿Cuál es la diferencia clave entre KPA (Knative Pod Autoscaler) y HPA?
   - A) KPA se basa solo en CPU, HPA se basa solo en memoria
   - B) KPA escala en función de la concurrencia y admite Scale-to-Zero, mientras que HPA escala en función de CPU/memoria
   - C) KPA escala nodes, HPA escala Pods
   - D) KPA es escalado manual, HPA es escalado automático

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KPA escala en función de la concurrencia y admite Scale-to-Zero, mientras que HPA escala en función de CPU/memoria**

**Explicación:**
KPA escala en función de solicitudes concurrentes o RPS medidos por Queue Proxy y admite Scale-to-Zero de forma nativa. HPA escala en función de métricas de CPU/memoria, pero requiere al menos 1 réplica en todo momento.

</details>

---

3. ¿Cuál es el rol de un Trigger en el patrón Broker/Trigger de Knative Eventing?
   - A) Una fuente que genera eventos
   - B) Filtra eventos del Broker y los enruta a servicios específicos
   - C) Almacenamiento persistente para eventos
   - D) Una gateway que envía eventos a sistemas externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Filtra eventos del Broker y los enruta a servicios específicos**

**Explicación:**
Los Triggers se registran con un Broker y filtran CloudEvents en función de atributos (tipo, fuente, etc.). Solo los eventos coincidentes se entregan al Subscriber especificado (Knative Service, Kubernetes Service, etc.). Se pueden registrar múltiples Triggers en un solo Broker para enrutar eventos a diferentes servicios.

</details>

---

4. ¿Qué ocurre cuando configuras `containerConcurrency: 1` en un Knative Service?
   - A) Solo se crea 1 Pod por contenedor
   - B) Cada contenedor procesa una solicitud a la vez; las solicitudes adicionales se enrutan a nuevos Pods
   - C) Solo se permite una solicitud por segundo
   - D) Solo se mantiene una Revision

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cada contenedor procesa una solicitud a la vez; las solicitudes adicionales se enrutan a nuevos Pods**

**Explicación:**
`containerConcurrency: 1` configura Queue Proxy en cada Pod para reenviar solo una solicitud concurrente al contenedor. Cuando llegan solicitudes adicionales, Autoscaler crea nuevos Pods. Esto es útil para tareas intensivas en CPU o aplicaciones que no son thread-safe.

</details>

---

5. ¿Cuál es un escenario adecuado para usar KEDA y Knative juntos?
   - A) Las dos herramientas son incompatibles; usa solo una
   - B) Usa Knative Serving para workloads HTTP y KEDA para workloads asíncronos basados en colas/streams
   - C) Usa KEDA para Scale-to-Zero y Knative para enrutamiento de eventos
   - D) Knative usa KEDA internamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa Knative Serving para workloads HTTP y KEDA para workloads asíncronos basados en colas/streams**

**Explicación:**
Knative Serving está optimizado para workloads serverless basados en solicitudes HTTP, con Scale-to-Zero y escalado basado en concurrencia. KEDA destaca al escalar en función de métricas de colas de SQS, Kafka, Redis, etc. Usar ambos juntos permite escalar workloads síncronos y asíncronos de forma óptima.

</details>

---

6. ¿Cómo implementas despliegues Canary usando división de tráfico en Knative?
   - A) Ajusta las réplicas del Deployment
   - B) Especifica porcentajes de tráfico por Revision en spec.traffic del Knative Service
   - C) Crea manualmente un Istio VirtualService
   - D) Ajusta HPA minReplicas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Especifica porcentajes de tráfico por Revision en spec.traffic del Knative Service**

**Explicación:**
El campo `spec.traffic` en un Knative Service permite especificar porcentajes de tráfico por Revision. Por ejemplo, asigna el 90% a la Revision existente y el 10% a la nueva Revision para un despliegue Canary. Usa `@latest` para hacer referencia a la Revision más reciente o especifica directamente los nombres de Revision.

</details>

---

7. ¿Cuál es el propósito de un Dead Letter Sink en Knative?
   - A) Archivar Knative Services eliminados
   - B) Enviar eventos fallidos a un destino separado para evitar la pérdida de eventos
   - C) Limpiar Revisions expiradas
   - D) Almacenar logs de debug

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enviar eventos fallidos a un destino separado para evitar la pérdida de eventos**

**Explicación:**
Un Dead Letter Sink reenvía eventos a un destino designado (otro Knative Service, Kubernetes Service, etc.) cuando la entrega falla después de los reintentos. Esto evita la pérdida de eventos y permite analizar o reprocesar eventos fallidos.

</details>

---

8. ¿Cuál es la forma más efectiva de minimizar los cold starts en Knative Serving?
   - A) Reducir infinitamente el tamaño de la imagen del contenedor
   - B) Mantener instancias mínimas con la anotación `minScale` y usar imágenes ligeras con frameworks de inicio rápido
   - C) Deshabilitar Scale-to-Zero por completo
   - D) Mantener siempre los Nodes en el conteo máximo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mantener instancias mínimas con la anotación `minScale` y usar imágenes ligeras con frameworks de inicio rápido**

**Explicación:**
Configurar `autoscaling.knative.dev/min-scale` en 1 o más evita los cold starts. Combinar esto con imágenes base ligeras (distroless, alpine), frameworks de inicio rápido como GraalVM Native Image y configuraciones de `initialScale` minimiza la latencia de cold start.

</details>
