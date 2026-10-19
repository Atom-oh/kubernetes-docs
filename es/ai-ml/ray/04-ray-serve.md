# Parte 4: Ray Serve

> **Versión base de revisión**: Ray 2.58.0 · KubeRay 1.7.1 · 2026-10-16

## Entorno y alcance de la validación

Se comprobó un pequeño ejemplo de respuesta en CPU con Python 3.12 y `ray[serve]==2.58.0`. En este entorno, el módulo HAProxy importaba Jinja2 aunque la instalación del extra no lo había incluido; añadir explícitamente `Jinja2==3.1.6` solucionó la importación. Es posible que otros entornos ya lo incluyan a través de otra dependencia.

El extra `ray[llm]` añade dependencias de inferencia de gran tamaño, como vLLM. No se instaló aquí y no se ejecutaron pesos de modelos, GPU ni cargas de trabajo en EKS. La validación siguiente abarca la configuración de Serve, las respuestas HTTP y las llamadas a DeploymentHandle.

## Deployments, aplicaciones y rutas de solicitudes

Un **Deployment** de Serve administra réplicas de actores; es distinto de un Deployment de Kubernetes. Pueden caber varios actores de réplica en un Ray Pod, por lo que las cantidades de réplicas y de Pods no son intercambiables.

Una **aplicación** contiene uno o más deployments y un deployment de entrada. Los DeploymentHandles pueden conectar el preprocesamiento y la inferencia sin hacer que cada llamada interna atraviese HTTP ni crear un Service de Kubernetes por deployment.

El Controller administra el estado de control de Serve y los ciclos de vida de los actores. Los proxies reciben tráfico HTTP/gRPC y lo reenvían a los deployments. La ubicación predeterminada del proxy en la versión 2.58.0 es **`EveryNode` en los nodos que alojan réplicas**. Se pueden seleccionar explícitamente `HeadOnly` y `Disabled`. La afirmación de una página de arquitectura anterior de que el valor predeterminado es solo el nodo principal no debe prevalecer sobre el contrato actual de la API.

Distingue las colas de llamadas en los proxies/handles de las solicitudes en curso asignadas a las réplicas. Revisa en la aplicación los controladores síncronos/asíncronos, el trabajo bloqueante, los tiempos de espera y el comportamiento de cancelación.

## Pequeño ejemplo local de HTTP/Handle

Esto valida las API de respuesta, no la inferencia de modelos. La comprobación real utilizó un puerto disponible de loopback privado y confirmó HTTP 200 y `double(4) == 8`.

```python
import requests
import ray
from ray import serve

try:
    ray.init(address="local", num_cpus=2, include_dashboard=False,
             object_store_memory=80 * 1024 * 1024)
    serve.start(proxy_location="HeadOnly",
                http_options={"host": "127.0.0.1", "port": 18080})

    @serve.deployment(num_replicas=1,
                      ray_actor_options={"num_cpus": 1},
                      max_ongoing_requests=2, max_queued_requests=4)
    class Echo:
        async def __call__(self, request):
            return {"echo": request.query_params.get("value", "")}
        def double(self, value):
            return value * 2

    handle = serve.run(Echo.bind(), name="echo", route_prefix="/echo")
    response = requests.get("http://127.0.0.1:18080/echo",
                            params={"value": "fixture"}, timeout=15)
    assert response.status_code == 200
    assert response.json() == {"echo": "fixture"}
    assert handle.double.remote(4).result(timeout_s=15) == 8
finally:
    serve.shutdown()
    ray.shutdown()
```

Ejecútalo en un proceso independiente para el ejercicio, con el puerto 18080 disponible. Los recursos lógicos de Ray y el tamaño del almacén de objetos no son límites de memoria/CPU del sistema operativo para todo el proceso. `serve.shutdown()` detiene la instancia de Serve conectada; no utilices la limpieza de este ejemplo en un clúster de producción compartido.

## Réplicas, escalado automático y control de presión

Distingue estos valores predeterminados verificados en la versión 2.58.0:

| Configuración | Valor o significado |
|---|---|
| Deployment predeterminado | una réplica, escalado automático sin configurar |
| `num_replicas="auto"` | aplica mínimo 1, máximo 100, objetivo de solicitudes en curso 2 |
| `AutoscalingConfig()` directo | mínimo 1, **máximo 1**; omitir el máximo limita la expansión |
| `max_ongoing_requests` | solicitudes enviadas a una réplica que aún no han recibido respuesta; valor predeterminado 5 |
| `max_queued_requests` | límite de cola en **cada llamador** (proxy/handle); valor predeterminado -1, ilimitado |
| Retraso de escalado | aumento predeterminado de 30 segundos/reducción de 600 segundos; no es la latencia real hasta que el servicio está listo |

El objetivo del escalado automático observa la carga de solicitudes; es distinto del máximo de solicitudes en curso y de un límite global de cola. Superar los límites de la cola puede generar BackPressureError para los handles o devolver HTTP 503 de forma predeterminada. La configuración del control de presión puede personalizar la respuesta HTTP.

Ajusta conjuntamente el mínimo/máximo, las ventanas de medición y los retrasos, los arranques en frío, la carga de modelos, el procesamiento por lotes (batching) y el tiempo real de procesamiento. Escalar a cero con `min_replicas=0` no elimina la latencia de reinicio. La cantidad deseada de réplicas no garantiza que todas estén listas.

## Capas de control en EKS

1. Serve ajusta los objetivos de réplicas de los deployments en función de la carga de solicitudes y las políticas.
2. Ray coloca los actores/bundles; el escalado automático de Ray, si está habilitado, y KubeRay pueden ajustar la capacidad de los Pods de trabajo.
3. Kubernetes coloca los Pods y un aprovisionador como Karpenter proporciona capacidad de nodos cuando es necesario.

**Un actor pendiente no se convierte automáticamente en un Pod Pending o un nodo EC2.** Los Ray Pods existentes pueden disponer de capacidad libre, o los límites de los grupos, la ubicación y las cuotas pueden impedir el avance. Inspecciona la demanda y la disponibilidad en cada capa.

![Las solicitudes HTTP/Handle llegan a los proxies de Serve y a las réplicas de los deployments. Los objetivos de los actores, la capacidad de los Ray Pods y el aprovisionamiento de nodos de Kubernetes son capas separadas, sin una correspondencia uno a uno entre actor/Pod/nodo.](../../.gitbook/assets/en-ai-ml-ray-04-ray-serve-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-04-ray-serve-0.html)

## Inferencia con GPU y Ray Serve LLM

Las réplicas de GPU ordinarias usan la configuración de recursos de Ray, como `ray_actor_options`. Alinea los dispositivos, los controladores, los límites de los Pods y la precedencia de los recursos estructurados de Ray/rayStartParams. Como se explica en la [Parte 2](02-kuberay-operator.md), los límites de los Pods no siempre son el único valor configurado.

Las API como `LLMConfig` y `build_openai_app` proporcionan una capa de configuración de LLM independiente. La documentación y el paquete de la versión 2.58.0 muestran **los backends vLLM y SGLang**. Entre las dependencias verificadas de `ray[llm]` se incluyen `vllm[audio]==0.26.0` y paquetes NIXL; esto no implica que también estén instaladas todas las dependencias de SGLang.

Distingue `model_loading_config`, `deployment_config`, `engine_kwargs` y `server_cls`. Comprueba los campos específicos del motor y las combinaciones admitidas en lugar de asumir que todas las opciones de la CLI `vllm serve` se transfieren sin cambios. Los backends pueden diferir en los nombres de las opciones de paralelismo de tensores y en la ubicación de los workers. Algunas API están en fase beta, y las rutas antiguas de LLMServer/LLMRouter incluyen avisos de obsolescencia.

Valida por separado el acceso al modelo, la revisión, las descargas de pesos, la compatibilidad entre el motor/CUDA/controlador, la caché KV y los recursos de paralelismo de tensores y de canalización. El formato de solicitud compatible con OpenAI no garantiza la autenticación, la seguridad ni una cobertura idéntica de funciones. La comprobación de CPU con Echo no demuestra el rendimiento ni la compatibilidad de LLM.

## RayService y actualizaciones operativas

RayService es una opción para la administración declarativa del ciclo de vida de aplicaciones de Serve y RayClusters en EKS, no un requisito universal para cada deployment de producción. Distingue los cambios en la configuración de las aplicaciones de los cambios en el clúster, y `NewCluster` de las estrategias de actualización incremental basadas en Gateway.

La función incremental habilitada de la versión 1.7 de KubeRay sigue requiriendo las API/implementación de Gateway, capacidad disponible, condiciones de disponibilidad y drenaje. Prueba el streaming y las solicitudes de larga duración con los límites de apagado. No describas todas las actualizaciones como si garantizaran la pérdida cero de solicitudes.

La configuración de inicio del clúster, como las opciones HTTP, tiene límites para las actualizaciones dinámicas. Los cambios en los deployments pueden consistir en una reconfiguración ligera o en el reemplazo de actores. Las réplicas reiniciadas/reemplazadas incurren en los costos de inicialización del modelo y recuperación del estado.

## Control de acceso y límites

Restringe por separado los puntos de entrada de API/dashboard/cliente, el acceso a los artefactos de modelos y el acceso de los usuarios de la aplicación. Los tokens del clúster Ray y ClusterIP no implementan automáticamente la autenticación/autorización para todos los endpoints de Serve. Revisa las entradas, respuestas, prompts y registros sensibles, y configura límites para las colas, los tiempos de espera y los recursos.

Estas comprobaciones cubren la configuración/decoradores nativos y una pequeña aplicación HTTP/Handle de un solo nodo. No se realizaron pruebas de carga de escalado automático, ejecución con GPU/LLM, conmutación por error multinodo ni despliegues de RayService.

## Fuentes principales

- [Serve 2.58.0](https://docs.ray.io/en/releases-2.58.0/serve/index.html)
- [Escalado automático](https://docs.ray.io/en/releases-2.58.0/serve/autoscaling-guide.html)
- [Serve LLM](https://docs.ray.io/en/releases-2.58.0/serve/llm/index.html)
- [API de Serve y valores predeterminados del proxy](https://github.com/ray-project/ray/blob/ray-2.58.0/python/ray/serve/api.py)
- [Configuración de Serve](https://github.com/ray-project/ray/blob/ray-2.58.0/python/ray/serve/config.py)
- [Configuración de réplicas/colas](https://github.com/ray-project/ray/blob/ray-2.58.0/python/ray/serve/_private/config.py)
- [KubeRay 1.7](https://github.com/ray-project/kuberay/releases/tag/v1.7.1)

[Página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/ray/04-ray-serve-quiz.md)
