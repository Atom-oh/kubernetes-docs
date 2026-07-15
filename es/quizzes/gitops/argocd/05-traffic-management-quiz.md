# Cuestionario de gestión de tráfico de ArgoCD

Este cuestionario evalúa tu comprensión de la entrega progresiva y la gestión de tráfico con ArgoCD y Argo Rollouts.

1. ¿Qué es Argo Rollouts?
   - A) Una solución de registro para ArgoCD
   - B) Un Kubernetes controller para estrategias de entrega progresiva
   - C) Una herramienta de gestión de ramas de Git
   - D) Un panel de monitoreo de tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un Kubernetes controller para estrategias de entrega progresiva**

**Explicación:**
Argo Rollouts es un Kubernetes controller que proporciona capacidades avanzadas de Deployment, como Deployments canary, Deployments blue-green y entrega progresiva con análisis automatizado.

</details>

2. ¿Qué estrategia de Deployment desplaza gradualmente el tráfico de la versión anterior a la versión nueva?
   - A) Recrear
   - B) Actualización continua
   - C) Canary
   - D) Blue-Green

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Canary**

**Explicación:**
Los Deployments canary desplazan gradualmente el tráfico de la versión anterior a la nueva en incrementos (por ejemplo, 10 %, 25 %, 50 %, 100 %), lo que permite realizar pruebas y validaciones en cada paso.

</details>

3. En un Deployment Blue-Green con Argo Rollouts, ¿qué sucede durante la promoción?
   - A) El entorno azul se elimina
   - B) El tráfico se cambia del Service estable (azul) al Service de vista previa (verde)
   - C) Ambas versiones se ejecutan simultáneamente para siempre
   - D) Se crea un entorno nuevo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tráfico se cambia del Service estable (azul) al Service de vista previa (verde)**

**Explicación:**
En los Deployments Blue-Green, la promoción cambia el tráfico de la versión estable actual a la versión de vista previa al actualizar el selector del Service activo. El ReplicaSet anterior se reduce después de la promoción.

</details>

4. ¿Qué es un AnalysisTemplate en Argo Rollouts?
   - A) Una plantilla para crear aplicaciones nuevas
   - B) Una definición de métricas y criterios de éxito para el análisis canary automatizado
   - C) Una configuración de registro
   - D) Una plantilla de cuota de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una definición de métricas y criterios de éxito para el análisis canary automatizado**

**Explicación:**
Los AnalysisTemplates definen las métricas que se deben consultar (de Prometheus, Datadog, etc.) y los criterios de éxito o fallo. Durante un rollout, los AnalysisRuns ejecutan estas plantillas para determinar automáticamente si un Deployment debe continuar.

</details>

5. ¿Qué Ingress controller tiene integración nativa con Argo Rollouts para la división de tráfico?
   - A) Solo Traefik
   - B) Solo NGINX Ingress
   - C) Varios, incluidos NGINX, ALB, Istio y Traefik
   - D) Ninguno; se requiere configuración manual

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Varios, incluidos NGINX, ALB, Istio y Traefik**

**Explicación:**
Argo Rollouts tiene integraciones nativas de gestión de tráfico con varios Ingress controllers y service meshes, incluidos NGINX Ingress, AWS ALB, Istio, Linkerd, SMI y Traefik.

</details>

6. ¿Qué hace el paso `setWeight` en una estrategia Canary?
   - A) Establece el peso de CPU para los pods
   - B) Establece el porcentaje de tráfico que se enruta a la versión canary
   - C) Establece la importancia del Deployment
   - D) Establece el umbral de rollback

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establece el porcentaje de tráfico que se enruta a la versión canary**

**Explicación:**
El paso `setWeight` de una estrategia canary configura qué porcentaje del tráfico debe enrutarse a la versión canary (nueva). Por ejemplo, `setWeight: 20` enruta el 20 % del tráfico a la versión canary.

</details>

7. ¿Qué sucede cuando un AnalysisRun falla durante un Deployment canary?
   - A) El Deployment continúa sin importar qué ocurra
   - B) Se envía una alerta, pero no sucede nada más
   - C) El rollout se cancela y revierte automáticamente
   - D) El clúster se apaga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El rollout se cancela y revierte automáticamente**

**Explicación:**
Cuando un AnalysisRun falla (las métricas superan los umbrales de fallo), Argo Rollouts cancela automáticamente el rollout e inicia un rollback a la versión estable, lo que evita que Deployments defectuosos afecten a todo el tráfico.

</details>

8. ¿Cómo puedes pausar un Rollout en un paso específico para una verificación manual?
   - A) Usando el paso `pause` sin duración
   - B) Usando el paso `stop`
   - C) Usando el paso `wait` con duration: forever
   - D) No es posible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Usando el paso `pause` sin duración**

**Explicación:**
Agregar un paso `pause` sin duración crea una pausa indefinida que requiere promoción manual (mediante CLI o UI) para continuar. Esto es útil para controles de verificación manuales en el proceso de Deployment.

</details>

9. ¿Cómo divides el tráfico canary mediante Kong Ingress Controller?
   - A) Usa el campo `trafficRouting.kong` directamente
   - B) Manipula un HTTPRoute mediante el plugin de Gateway API (`trafficRouting.plugins`)
   - C) Kong no se puede integrar con Argo Rollouts
   - D) Enruta alrededor de él usando un Istio VirtualService

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Manipula un HTTPRoute mediante el plugin de Gateway API (`trafficRouting.plugins`)**

**Explicación:**
Kong no tiene integración nativa con Argo Rollouts; no existe el campo `trafficRouting.kong`. Solo es compatible mediante el plugin de Gateway API de argoproj-labs, que manipula un recurso HTTPRoute estándar. Otros controllers compatibles con Gateway API, como Traefik y kgateway, usan el mismo plugin.

</details>

10. ¿Qué recurso actualiza realmente el plugin de Gateway API de Argo Rollouts en cada paso de peso canary?
    - A) Las etiquetas `selector` del Service
    - B) La anotación `canary-weight` del Ingress
    - C) Los valores `backendRefs[].weight` del HTTPRoute
    - D) Las etiquetas de subconjunto del DestinationRule

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los valores `backendRefs[].weight` del HTTPRoute**

**Explicación:**
El plugin de Gateway API actualiza directamente los valores `backendRefs[].weight` del recurso HTTPRoute estándar de Gateway API en cada paso setWeight. Este es un mecanismo universal que se aplica de forma idéntica a cualquier controller que implemente Gateway API: Kong, Traefik, kgateway y otros.

</details>
