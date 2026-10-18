# Cuestionario de gestión de tráfico de ArgoCD

Este cuestionario evalúa tu comprensión de la entrega progresiva y la gestión de tráfico con ArgoCD y Argo Rollouts.

1. ¿Qué es Argo Rollouts?
   - A) Una solución de gestión de registros para ArgoCD
   - B) Un controlador de Kubernetes para estrategias de entrega progresiva
   - C) Una herramienta de gestión de ramas de Git
   - D) Un panel de monitoreo de tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un controlador de Kubernetes para estrategias de entrega progresiva**

**Explicación:**
Argo Rollouts es un controlador de Kubernetes que proporciona capacidades avanzadas de despliegue, como despliegues canary, Blue-Green y entrega progresiva con análisis automatizado.

</details>

2. ¿Qué estrategia valida una versión nueva mediante pasos explícitos de ponderación del tráfico y controles de análisis?
   - A) Recrear
   - B) Actualización continua
   - C) Canary
   - D) Blue-Green

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Canary**

**Explicación:**
Canary desplaza gradualmente el tráfico hacia la versión nueva mediante pasos de ponderación explícitos y controles de análisis, que permiten validar el cambio en cada etapa.

</details>

3. En un Deployment Blue-Green con Argo Rollouts, ¿qué sucede durante la promoción?
   - A) El entorno azul se elimina
   - B) El selector del Service activo cambia para apuntar al nuevo ReplicaSet
   - C) Ambas versiones se ejecutan simultáneamente para siempre
   - D) Se crea un entorno nuevo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El selector del Service activo cambia para apuntar al nuevo ReplicaSet**

**Explicación:**
En los despliegues Blue-Green, la promoción cambia el selector del Service activo para que apunte al nuevo ReplicaSet. El ReplicaSet anterior se reduce después de que terminen el análisis y los retardos configurados; la propagación por el plano de datos no es instantánea.

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

5. ¿Qué proveedores tienen integraciones nativas de gestión del tráfico en Argo Rollouts?
   - A) Solo Traefik
   - B) Solo NGINX Ingress
   - C) Varios, incluidos NGINX, ALB, Istio y Traefik
   - D) Ninguno; se requiere configuración manual

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Varios, incluidos NGINX, ALB, Istio y Traefik**

**Explicación:**
Argo Rollouts incluye integraciones nativas con varios controladores Ingress y mallas de servicio, como AWS ALB, Istio, Traefik y APISIX. Que se mantenga la compatibilidad con las API ingress-nginx/SMI no significa que esos proyectos sigan mantenidos; tampoco existe un campo nativo específico para Linkerd.

</details>

6. Con un enrutador de tráfico y maxTrafficWeight=100 predeterminado, ¿qué configura setWeight?
   - A) Establece el peso de CPU para los pods
   - B) Establece el porcentaje de tráfico que se enruta a la versión canary
   - C) Establece la importancia del Deployment
   - D) Establece el umbral de rollback

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establece el porcentaje de tráfico que se enruta a la versión canary**

**Explicación:**
El paso `setWeight` de una estrategia canary solicita un peso relativo del tráfico. Por ejemplo, setWeight:20 solicita una proporción de 20/100. El porcentaje observado puede variar según las muestras, las conexiones y las cookies. Sin un enrutador, el controlador aproxima esa proporción mediante la cantidad de Pods.

</details>

7. ¿Qué sucede cuando un AnalysisRun falla durante un Deployment canary?
   - A) El Deployment continúa sin importar qué ocurra
   - B) Se envía una alerta, pero no sucede nada más
   - C) El rollout se aborta y el tráfico vuelve a la versión estable
   - D) El clúster se apaga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El rollout se aborta y el tráfico vuelve a la versión estable**

**Explicación:**
Cuando falla un AnalysisRun (las métricas superan los umbrales de fallo), Argo Rollouts aborta el rollout y devuelve el tráfico a la versión estable. No revierte los cambios de Git ni los de la base de datos. failureLimit distingue las mediciones fallidas de un AnalysisRun fallido; Inconclusive pausa el rollout para investigar.

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
Kong no tiene integración nativa con Argo Rollouts; no existe el campo `trafficRouting.kong`. Este capítulo usa el plugin de Gateway API de argoproj-labs, que modifica un recurso HTTPRoute estándar. Otros controladores compatibles con Gateway API, como Traefik y kgateway, usan el mismo plugin.

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
El plugin de Gateway API actualiza directamente los valores `backendRefs[].weight` del recurso HTTPRoute estándar en cada paso setWeight. Este mecanismo puede funcionar con controladores compatibles; comprueba que las CRD estén instaladas, que se admitan las funciones de Route necesarias y que el plano de datos haya convergido realmente.

</details>
