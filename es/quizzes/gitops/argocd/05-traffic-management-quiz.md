# Cuestionario sobre gestión de tráfico con ArgoCD

Este cuestionario evalúa tu comprensión de la entrega progresiva y la gestión de tráfico con ArgoCD y Argo Rollouts.

1. ¿Qué es Argo Rollouts?
   - A) Una solución de registro para ArgoCD
   - B) Un controlador de Kubernetes para estrategias de entrega progresiva
   - C) Una herramienta de gestión de ramas de Git
   - D) Un panel de monitoreo de tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un controlador de Kubernetes para estrategias de entrega progresiva**

**Explicación:**
Argo Rollouts es un controlador de Kubernetes que proporciona capacidades avanzadas de despliegue, como despliegues Canary, despliegues Blue-Green y entrega progresiva con análisis automatizado.

</details>

2. ¿Qué estrategia de despliegue desplaza gradualmente el tráfico de la versión anterior a la nueva versión?
   - A) Recreate
   - B) Rolling Update
   - C) Canary
   - D) Blue-Green

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Canary**

**Explicación:**
Los despliegues Canary desplazan gradualmente el tráfico de la versión anterior a la nueva versión en incrementos (p. ej., 10 %, 25 %, 50 %, 100 %), lo que permite realizar pruebas y validaciones en cada paso.

</details>

3. En un despliegue Blue-Green con Argo Rollouts, ¿qué sucede durante la promoción?
   - A) El entorno azul se elimina
   - B) El tráfico cambia del Service estable (azul) al Service de vista previa (verde)
   - C) Ambas versiones se ejecutan simultáneamente para siempre
   - D) Se crea un entorno nuevo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tráfico cambia del Service estable (azul) al Service de vista previa (verde)**

**Explicación:**
En los despliegues Blue-Green, la promoción cambia el tráfico de la versión estable actual a la versión de vista previa mediante la actualización del selector del Service activo. El ReplicaSet anterior se reduce después de la promoción.

</details>

4. ¿Qué es un AnalysisTemplate en Argo Rollouts?
   - A) Una plantilla para crear aplicaciones nuevas
   - B) Una definición de métricas y criterios de éxito para el análisis Canary automatizado
   - C) Una configuración de registro
   - D) Una plantilla de cuota de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una definición de métricas y criterios de éxito para el análisis Canary automatizado**

**Explicación:**
Los AnalysisTemplates definen las métricas que se consultarán (de Prometheus, Datadog, etc.) y los criterios de éxito/error. Durante un rollout, los AnalysisRuns ejecutan estas plantillas para determinar automáticamente si un despliegue debe continuar.

</details>

5. ¿Qué controlador Ingress tiene integración nativa con Argo Rollouts para la división de tráfico?
   - A) Solo Traefik
   - B) Solo NGINX Ingress
   - C) Varios, incluidos NGINX, ALB, Istio y Traefik
   - D) Ninguno; se requiere configuración manual

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Varios, incluidos NGINX, ALB, Istio y Traefik**

**Explicación:**
Argo Rollouts cuenta con integraciones nativas de gestión de tráfico con varios controladores Ingress y mallas de servicios, incluidos NGINX Ingress, AWS ALB, Istio, Linkerd, SMI y Traefik.

</details>

6. ¿Qué hace el paso `setWeight` en una estrategia Canary?
   - A) Establece el peso de CPU para los Pods
   - B) Establece el porcentaje de tráfico que se enruta a la versión Canary
   - C) Establece la importancia del despliegue
   - D) Establece el umbral de reversión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establece el porcentaje de tráfico que se enruta a la versión Canary**

**Explicación:**
El paso `setWeight` en una estrategia Canary configura qué porcentaje de tráfico debe enrutarse a la versión Canary (nueva). Por ejemplo, `setWeight: 20` enruta el 20 % del tráfico al Canary.

</details>

7. ¿Qué sucede cuando un AnalysisRun falla durante un despliegue Canary?
   - A) El despliegue continúa de todos modos
   - B) Se envía una alerta, pero no sucede nada más
   - C) El rollout se cancela y se revierte automáticamente
   - D) El clúster se apaga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El rollout se cancela y se revierte automáticamente**

**Explicación:**
Cuando un AnalysisRun falla (las métricas superan los umbrales de error), Argo Rollouts cancela automáticamente el rollout e inicia una reversión a la versión estable, evitando que los despliegues defectuosos afecten a todo el tráfico.

</details>

8. ¿Cómo puedes pausar un Rollout en un paso específico para realizar una verificación manual?
   - A) Usando el paso `pause` sin duración
   - B) Usando el paso `stop`
   - C) Usando el paso `wait` con duration: forever
   - D) No es posible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Usando el paso `pause` sin duración**

**Explicación:**
Agregar un paso `pause` sin duración crea una pausa indefinida que requiere una promoción manual (mediante CLI o UI) para continuar. Esto es útil para las puertas de verificación manual en el proceso de despliegue.

</details>
