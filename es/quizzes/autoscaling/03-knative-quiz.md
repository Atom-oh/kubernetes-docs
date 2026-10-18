# Cuestionario de Knative

> **Última actualización**: 11 de septiembre de 2026

1. ¿Cómo funciona Scale-to-Zero en Knative Serving?
   - A) Elimina los Pods y vuelve a crear el Deployment ante nuevas solicitudes
   - B) Activator almacena temporalmente las solicitudes admitidas mientras la ruta de autoescalado activa réplicas listas
   - C) Apaga los nodos y hace que Karpenter aprovisione otros cuando recibe una solicitud
   - D) Pausa los contenedores y los reanuda cuando recibe una solicitud

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Activator almacena temporalmente las solicitudes admitidas mientras la ruta de autoescalado activa réplicas listas**

**Explicación:**
Con cero réplicas, la ruta de enrutamiento pasa por Activator, que almacena solicitudes dentro de sus límites de capacidad y tiempo de espera mientras se activa capacidad disponible para atenderlas. Los fallos, el agotamiento de los búferes o los tiempos de espera del cliente o de la solicitud aún pueden causar errores. Un valor positivo de min-scale evita el escalado normal a cero durante la inactividad, pero no elimina la inicialización de nuevas Revisions, los reinicios ni el arranque de réplicas adicionales.

</details>

---

2. ¿Qué distingue las integraciones KPA y HPA en Knative Serving?
   - A) KPA solo se basa en CPU y HPA solo en memoria
   - B) KPA escala según la concurrencia y admite Scale-to-Zero, mientras que HPA escala según CPU/memoria
   - C) KPA escala nodos y HPA escala Pods
   - D) KPA escala manualmente y HPA de forma automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KPA escala según la concurrencia y admite Scale-to-Zero, mientras que HPA escala según CPU/memoria**

**Explicación:**
Knative KPA admite concurrencia/RPS y la ruta a cero basada en Activator. La extensión opcional HPA de Knative admite CPU, memoria y métricas personalizadas de Pod compatibles, y no implementa esa ruta a cero. Esto no es una afirmación universal sobre HPA de Kubernetes: la versión upstream 1.37 de Kubernetes ofrece escalado a cero en fase beta para métricas de objeto y externas. En la implementación HPA 1.23, los objetivos de CPU son porcentajes de utilización con respecto a las solicitudes de CPU, los objetivos de memoria se expresan en MiB y las métricas personalizadas usan promedios por Pod.

</details>

---

3. ¿Qué función cumple un Trigger en el patrón Broker/Trigger de Knative Eventing?
   - A) Generar eventos como fuente
   - B) Filtrar los eventos del Broker y dirigirlos a servicios específicos
   - C) Almacenar eventos de forma persistente
   - D) Actuar como gateway que envía eventos a sistemas externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Filtrar los eventos del Broker y dirigirlos a servicios específicos**

**Explicación:**
Un Trigger define filtros y un suscriptor para un Broker; los controladores y el plano de datos del Broker implementan la entrega. Varios Triggers coincidentes pueden entregar copias del mismo evento, y el comportamiento de reintentos y almacenamiento depende de la implementación y la política. Un Trigger no es un almacén persistente de eventos ni un autoescalador genérico de consumidores.

</details>

---

4. ¿Qué ocurre al establecer `containerConcurrency: 1` en un Knative Service?
   - A) Solo se crea un Pod por contenedor
   - B) Queue Proxy reenvía como máximo una solicitud concurrente por Pod, con espera limitada y escalado asíncrono
   - C) Solo se permite una solicitud por segundo
   - D) Solo se mantiene una Revision

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Queue Proxy reenvía como máximo una solicitud concurrente por Pod, con espera limitada y escalado asíncrono**

**Explicación:**
Queue Proxy limita el número de solicitudes concurrentes que reenvía al contenedor receptor de cada Pod. Las solicitudes adicionales pueden esperar en colas limitadas, dirigirse a capacidad disponible o fallar. El autoescalado es asíncrono y está sujeto a límites y a la capacidad de los nodos. No equivale a una solicitud por segundo, a una sola solicitud global para todas las réplicas ni garantiza que cada solicitud adicional obtenga un Pod nuevo.

</details>

---

5. ¿En qué caso conviene usar KEDA y Knative juntos?
   - A) Las dos herramientas son incompatibles; usa solo una
   - B) Usa Knative Serving para cargas HTTP y KEDA para cargas asíncronas basadas en colas o streams
   - C) Deja que KEDA y KPA escalen por separado el mismo Deployment generado por Knative
   - D) Cada Knative Service instala KEDA automáticamente y lo usa como autoescalador predeterminado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa Knative Serving para cargas HTTP y KEDA para cargas asíncronas basadas en colas o streams**

**Explicación:**
Usa Knative Serving para los servicios HTTP adecuados y KEDA para workers en segundo plano administrados por separado. Configura la retención de la cola, las confirmaciones, las métricas de activación y la idempotencia de los workers. No permitas que KEDA y KPA controlen por separado el mismo Deployment generado. SinkBinding configura productores de eventos; no activa un consumidor HTTP arbitrario escalado a cero.

</details>

---

6. ¿Cómo se implementan despliegues canary con división del tráfico en Knative?
   - A) Ajustando las réplicas del Deployment
   - B) Especificando porcentajes de tráfico por Revision en `spec.traffic` del Knative Service
   - C) Creando manualmente un Istio VirtualService
   - D) Ajustando HPA minReplicas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Especificando porcentajes de tráfico por Revision en `spec.traffic` del Knative Service**

**Explicación:**
`spec.traffic` contiene destinos explícitos mediante `revisionName` o `latestRevision: true`, junto con los porcentajes. `@latest` es una abreviatura de la CLI de kn; no es un valor de `revisionName` ni una etiqueta de la API que signifique «latest». Las Revisions referenciadas deben existir y estar listas; la reconciliación de rutas no es un cambio global instantáneo y las solicitudes existentes pueden seguir atendiendo con la Revision anterior.

</details>

---

7. ¿Para qué sirve un Dead Letter Sink en Knative?
   - A) Archivar Knative Services eliminados
   - B) Intentar entregar el evento a un destino alternativo configurado cuando falla la entrega al suscriptor
   - C) Limpiar Revisions vencidas
   - D) Almacenar registros de depuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Intentar entregar el evento a un destino alternativo configurado cuando falla la entrega al suscriptor**

**Explicación:**
Un DLS configurado es el destino alternativo cuando la política de entrega ya no puede entregar el evento al suscriptor. El propio DLS también puede fallar; la retención del evento y su almacenamiento correcto dependen del transporte y del controlador. Envía el acuse de recibo solo después de completar el almacenamiento o procesamiento previsto y, cuando sea necesario, deduplica mediante source e id del CloudEvent.

</details>

---

8. ¿Qué combinación puede reducir la latencia de arranque en frío y mantener una política explícita de capacidad disponible?
   - A) Reducir indefinidamente el tamaño de la imagen del contenedor
   - B) Mantener instancias mínimas con la anotación `minScale` y usar imágenes ligeras con frameworks de inicio rápido
   - C) Deshabilitar Scale-to-Zero por completo
   - D) Mantener siempre los nodos en su capacidad máxima

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mantener instancias mínimas con la anotación `minScale` y usar imágenes ligeras con frameworks de inicio rápido**

**Explicación:**
Un valor positivo de `autoscaling.knative.dev/min-scale` mantiene capacidad base durante los periodos normales de inactividad, mientras que `initial-scale` se aplica al crear una Revision por primera vez. El tamaño de la imagen, la disponibilidad de nodos, la caché de imágenes, el tiempo de arranque y la preparación para recibir tráfico afectan la latencia. Las nuevas Revisions, los reinicios y el escalado por encima de la capacidad base aún pueden provocar arranques en frío; mide tráfico representativo en lugar de prometer que desaparecerán.

</details>
