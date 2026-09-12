# Frameworks de Inferencia para el Serving de LLM

> **Revisado**: September 12, 2026
> **Alcance**: Lanzamientos oficiales, APIs, charts y comprobaciones locales; sin ejecución de modelos GPU/Neuron.

Seleccione por separado motores de inferencia, capas de ejecución distribuida, controladores Kubernetes y gateways de proveedores. “Compatible con OpenAI” no implica endpoints, campos, streaming, llamadas a herramientas o autenticación idénticos.

## Panorama de Frameworks de Inferencia

![Los roles diferenciados de los motores de inferencia, serving distribuido, operaciones Kubernetes y gateways de proveedores.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-0.html)

| Componente | Línea base inspeccionada | Comprobaciones de selección |
| --- | --- | --- |
| NIM LLM/VLM | Documentación 2.0.12; oferta 3.0 independiente | Modelo, perfil, hardware, acuerdo de soporte y backend |
| Dynamo | 1.4.2 | Serving agregado/desagregado, transferencia KV, planner y controller |
| AIBrix | 0.7.0 | Envoy Gateway, adapter/controller y autoscaling |
| SGLang | 0.5.19 | Modelo, backend de gramática, dispositivo y carga de trabajo medida |
| vLLM / Ray Serve | vLLM 0.29.0 / Ray 2.58.0 / KubeRay 1.7.0 | Combinaciones validadas individualmente de image/model/controller |
| TGI | 3.3.7; modo de mantenimiento | Mantenimiento de sistemas existentes y planificación de migración |
| Ollama | 0.34.0 | Acceso a API local, almacenamiento y preparación de modelos |
| LiteLLM | 1.100.1 | Adaptación de proveedor, autenticación, fallback e instrumentación de costes |
| Neuron | SDK 2.32.0; Helm 1.10.0 | Compatibilidad de plugin/compiler/driver específica de la instancia |

Evite una matriz universal de funcionalidades de sí/no. La planificación de Dynamo y la desagregación de vLLM/SGLang, el soporte de CPU y GGUF dependen del lanzamiento, backend y hardware. La carga de adapters y los alias de modelos no son límites de autenticación de tenants.

## NVIDIA NIM

Compruebe conjuntamente el contenedor, el perfil de modelo, la compatibilidad GPU y el acuerdo de soporte. NIM Operator 3.1.2 es independiente de los contenedores LLM/VLM 2.0.12. El lanzamiento 2.0.12 inspeccionado documenta vLLM 0.27.1; NIM no siempre usa TensorRT-LLM. No considere la oferta 3.0 basada en Dynamo como la misma ruta de despliegue que 2.0.

![Una ruta de entrada aprobada atiende solicitudes NIM, con caché de modelos preparada y recopilación de métricas independiente.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-1.html)

### Preparación del Deployment y Perfiles

Use la [guía de GPU](01-ai-ml-workloads.md) para los requisitos de AMI, driver/toolkit y device-plugin. Habilitar siempre la instalación del driver puede entrar en conflicto con una AMI de proveedor. Compruebe Karpenter NodePool/EC2NodeClass, los recursos de CPU/RAM/GPU realmente programables y los recuentos de dispositivos. Un Pod de ocho GPU no cabe en un nodo de una/cuatro GPU, y las Custom AMIs necesitan una configuración explícita de bootstrap de EKS.

Use NIM_MODEL_PROFILE con un ID/nombre de perfil admitido de la lista de perfiles del contenedor. No suponga que el antiguo NIM_MANIFEST_PROFILE o una cadena vllm-bf16-tp8 inventada son válidos. Registre juntos el digest de image, la revisión del modelo, el perfil, los drivers y la verificación real.

Las credenciales de image-pull de NGC y de descarga de modelos en runtime cumplen funciones diferentes. La ruta documentada de entorno NGC_API_KEY no satisface una política de credenciales solo de archivo. Use una ruta de modelo preparado aprobada o un adaptador de credenciales verificado; nunca incluya claves reales en argumentos de shell o código fuente. Un Service interno por sí solo no autentica solicitudes de inferencia.

Evite compartir un PVC EBS RWO entre réplicas en nodos diferentes. Elija almacenamiento/cachés locales por réplica o un sistema de archivos compartido adecuado, y pruebe errores de descarga, rendimiento de almacenamiento, probes de inicio y rollout. Los modelos no están incluidos universalmente en images, y las cachés no se sincronizan automáticamente con FSx/S3.

### Métricas y GenAI-Perf

La documentación NIM 2.0.12 inspeccionada expone `/v1/metrics`, transmitiendo las métricas nativas del backend vLLM. Inspeccione los nombres, unidades y labels reales en lugar de copiar nombres nim_* inventados o `/metrics`. Un ConfigMap de Grafana necesita el datasource/sidecar correspondiente y scraping de Prometheus. No muestre segundos sin cambios en un panel de milisegundos.

Defina SLO específicos para la carga de trabajo para TTFT, ITL, latencia end-to-end, throughput exitoso y encolamiento. Con intervalos uniformes de tokens, la aproximación es `TTFT + (output tokens - 1) × ITL`, más overhead independiente de red/postprocesamiento. Objetivos como 500ms o GPU80% no son estándares universales de salud.

GenAI-Perf 0.0.16 usa el subcomando profile y las opciones synthetic-input-tokens-mean/output-tokens-mean. El siguiente comando cargaría un endpoint interno preparado y no se ejecutó en esta auditoría. Prepare primero perf_analyzer, tokenizer y otras dependencias de distribución.

```bash
genai-perf profile   --endpoint-type chat   --service-kind openai   --url http://127.0.0.1:8000   --model approved-model-alias   --concurrency 2   --synthetic-input-tokens-mean 128   --output-tokens-mean 64   --num-prompts 20   --profile-export-file profile_export.json
```

No suponga que analyze es solo postprocesamiento JSON: los ajustes de sweep pueden realizar profiling adicional. Conserve solicitudes sin procesar, errores, tokenizer, warmup, concurrencia y revisiones de modelo/backend. La utilización de GPU necesita recopilación de métricas reales.

## NVIDIA Dynamo

La ruta Kubernetes oficial 1.4.2 usa la plataforma Dynamo, DynamoGraphDeployment (DGD) y DynamoGraphDeploymentRequest (DGDR). No está implementada por las images dynamo-router/dynamo-worker anteriormente inventadas, KV_CACHE_HOST y YAML de router arbitrario. Un DGDR solicita profiling y creación de DGD; no es una inspección de solo lectura.

![El frontend de Dynamo, workers configurados y transferencia KV, con controller/planner administrando el Deployment y la capacidad.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-2.html)

### Estructura DGD Real

Esta **configuración comprobada contra el esquema** adapta el ejemplo agregado v1beta1 oficial 1.4.2 para un modelo público y ajustes de ejecución acotados. Requiere la plataforma/controller, namespace, GPU, acceso al modelo y red. Fije los digests de modelo/image y verifique el hardware real antes del despliegue; no se ejecutó ningún modelo en esta auditoría.

```yaml
apiVersion: nvidia.com/v1beta1
kind: DynamoGraphDeployment
metadata:
  name: vllm-agg
  namespace: dynamo-system
spec:
  components:
  - name: Frontend
    podTemplate:
      spec:
        containers:
        - image: nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.4.2
          name: main
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: '1'
              memory: 2Gi
    replicas: 1
    type: frontend
  - name: VllmDecodeWorker
    podTemplate:
      spec:
        containers:
        - args:
          - --model
          - Qwen/Qwen3-0.6B
          - --max-model-len
          - '2048'
          - --max-num-seqs
          - '8'
          command:
          - python3
          - -m
          - dynamo.vllm
          image: nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.4.2
          name: main
          resources:
            limits:
              nvidia.com/gpu: '1'
              cpu: '4'
              memory: 12Gi
            requests:
              ephemeral-storage: 2Gi
              cpu: '2'
              memory: 4Gi
          workingDir: /workspace/examples/backends/vllm
    replicas: 1
    type: worker
```

La desagregación requiere roles de prefill/decode compatibles, conectores/formatos KV, revisiones de modelo y red. Las mezclas arbitrarias de backends o GPU no son interoperables automáticamente. El routing consciente de KV equilibra localidad y carga; una fórmula fija0.7/0.3 no es una implementación universal. Redis no es el almacén obligatorio de tensores KV para todos los despliegues Dynamo.

El operator de todo el clúster del chart de plataforma inspeccionado administra CRDs mediante un contenedor init crd-apply. upgradeCRD=false selecciona la gestión externa; no elimina el requisito de CRD. Compruebe planner, discovery, NATS/etcd, Grove/KAI y otros ajustes específicos del lanzamiento. El renderizado del chart no verifica la aplicación de CRD, autorización ni discovery en vivo.

## AIBrix

La versión0.7.0 usa Envoy Gateway, un plugin de gateway, controller-manager y servicios de metadatos. KubeRay es opcional para capacidades basadas en Ray. El anterior servidor aibrix-registry independiente y la API /v1/lora/register no son la ruta de instalación 0.7.0 inspeccionada.

### ModelAdapter y PodAutoscaler

Los campos reales de ModelAdapter incluyen baseModel, podSelector y artifactURL. Omitir replicas carga el adapter en todos los Pods coincidentes;1 selecciona un Pod; se rechazan otros valores. Sustituya el bucket/revisión de ejemplo y el modelo base por valores aprobados. Verifique por separado los permisos de descarga del controller, la compatibilidad runtime, la capacidad/ciclo de vida del adapter y la autorización del tenant.

```yaml
apiVersion: model.aibrix.ai/v1alpha1
kind: ModelAdapter
metadata:
  name: support-lora
  namespace: ai-inference
spec:
  baseModel: approved-base-model
  podSelector:
    matchLabels:
      model.aibrix.ai/name: approved-base-model
  artifactURL: s3://REPLACE_WITH_APPROVED_BUCKET/adapters/support/REVISION/
  replicas: 1
```

PodAutoscaler0.7.0 usa metricsSources y estrategias HPA/KPA/APA, no un ConfigMap de autoscaler arbitrario. Este ejemplo de CPU requiere metrics-server, solicitudes de CPU de la carga de trabajo y el controller. No valida el escalado basado en la cola GPU. Evite propietarios de scaler en competencia para el mismo objetivo.

```yaml
apiVersion: autoscaling.aibrix.ai/v1alpha1
kind: PodAutoscaler
metadata:
  name: model-cpu
  namespace: ai-inference
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: prepared-model-server
  minReplicas: 1
  maxReplicas: 3
  scalingStrategy: HPA
  metricsSources:
  - metricSourceType: resource
    targetMetric: cpu
    targetValue: '70'
```

## Integración de Ray Serve

Use las APIs auditadas de [Ray Serve](ray/04-ray-serve.md) y [KubeRay](ray/02-kuberay-operator.md). La reconciliación de KubeRay, el autoscaling de workers Ray y el autoscaling de réplicas Serve tienen funciones distintas. No use RayCluster como objetivo normal de escalado HPA de Deployment ni adivine los nombres y selectores de Service generados de cluster/Serve.

El código y las dependencias deben llegar a los workers de ejecución, no solo al head. user_config no cambia automáticamente los argumentos del constructor; implemente la ruta de reconfigure adecuada. Una API compatible necesita el template de chat real, streaming, cancelación, razones de finalización, uso y errores. Concatenar cadenas de roles e ignorar stream=true es insuficiente. Se eliminaron los ejemplos antiguos de Ray2.9/operator1.1 y trust_remote_code=True incondicional.

## SGLang

La RadixAttention de la versión0.5.19 reutiliza KV para prefijos comunes; las subcadenas centrales arbitrarias superpuestas no son prefijos en caché intercambiables. El modelo, formato KV y políticas de acceso deben coincidir. Los backends de gramática actuales incluyen XGrammar predeterminado y las alternativas Outlines/Llguidance. “Siempre10x más rápido por FSM comprimido” no es una conclusión general.

![Las APIs/runtime de SGLang, el caché KV de prefijos comunes y el backend de gramática seleccionado.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-3.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-3.html)

### Ejemplo de Solicitud Estructurada

Este cliente asume un gateway aprobado que admite la forma de solicitud json_schema de SGLang. Comprueba la finalización normal y la forma de salida. La validación usa un fixture HTTP local con respuestas sintéticas y casos de error; no mide la precisión del modelo. La validez JSON no establece la corrección factual ni la autorización de herramientas.

```python
from pathlib import Path
import json
from urllib.request import Request, urlopen

# Existing private gateway and a scoped credential mounted as a file.
base_url = "https://inference.example.internal/v1"
credential = Path("/run/secrets/inference/token").read_text().strip()
payload = {
    "model": "approved-model-alias",
    "messages": [{"role": "user", "content": "Return the city Seoul and country Korea."}],
    "temperature": 0,
    "max_tokens": 128,
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "location",
            "schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}, "country": {"type": "string"}},
                "required": ["city", "country"],
                "additionalProperties": False,
            },
        },
    },
}
request = Request(
    base_url + "/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + credential},
    method="POST",
)
with urlopen(request, timeout=30) as response:
    result = json.load(response)
choice = result["choices"][0]
if choice["finish_reason"] != "stop":
    raise RuntimeError("Generation did not complete normally")
location = json.loads(choice["message"]["content"])
if set(location) != {"city", "country"} or not all(isinstance(v, str) for v in location.values()):
    raise ValueError("Unexpected output shape")
print(location)
```

Las APIs DSL de función/system/user/assistant/gen de SGLang permanecen en este lanzamiento. Declarar una función no ejecuta la inferencia: conecte un RuntimeEndpoint/backend preparado y ejecútelo. Verifique la compatibilidad de Torch, FlashInfer y hardware durante la instalación. Esta auditoría no instaló el SDK GPU completo ni conectó el DSL a un modelo.

## Hugging Face TGI

El repositorio oficial declara **modo de mantenimiento**; el último lanzamiento inspeccionado es3.3.7(December19,2025). Acepta correcciones menores, documentación y mantenimiento, y orienta la adopción de nuevos motores hacia vLLM/SGLang y otros. Ya no es una recomendación predeterminada genérica para un proyecto nuevo. Valide la compatibilidad de modelo, template, streaming, métricas y SLO al migrar despliegues existentes.

Añadir --quantize=awq no produce automáticamente pesos AWQ a partir de un modelo ordinario. Use un modelo admitido preparado en ese formato. Los tags flotantes, las credenciales de modelo gated ausentes y los plazos cortos de liveness perjudican la reproducibilidad y el inicio correcto.

## Ollama

En0.34.0, descargar un modelo y servirlo son operaciones independientes. Un hook postStart con sleep10 no garantiza la preparación. Prepare previamente los modelos aprobados o use un procedimiento de preparación independiente con health checks, reintentos acotados y manejo de errores. Registre los tags mutables del modelo y los permisos de almacenamiento.

La API local de Ollama no proporciona autenticación de usuario; establezca autorización y controles de rutas delante antes de exponerla. Un servidor vinculado solo al localhost del Pod no puede alcanzarse mediante su Service. OLLAMA_HOST cambia el ámbito de escucha, no la autenticación. Delimite por separado los endpoints de gestión de modelos e inferencia.

Un Modelfile define el modelo base, el prompt de sistema y los ajustes de generación; no entrena un modelo ni crea una image Kubernetes. Verifique el soporte CPU/GPU por tamaño de modelo, dispositivo y backend en lugar de suponer multitenancy a gran escala.

## LiteLLM

Use la configuración Router auditada1.100.1 en la [guía de IA agéntica](03-agentic-ai-platform.md). Un gateway de proveedor es una capa distinta de un motor de inferencia. Llamar a un alias gpt-4-equivalent no establece calidad equivalente. El fallback debe satisfacer primero las políticas de proveedor permitido y salida de datos.

Conecte el archivo de configuración real al comando proxy y configure las credenciales de cliente, DB/Redis y callbacks según sea necesario. Una clave ficticia o ClusterIP no es autenticación; drop_params=true puede eliminar condiciones significativas de la solicitud. Distinga solicitudes, éxito, fallo, reintentos y costes de caché.

## AWS Neuron e Inferentia2

Distinga chips, NeuronCores y RAM/HBM del host. Cada chip Inferentia2 tiene dos cores NeuronCore-v2 y32GiB de HBM.

| Instancia | Chips | NeuronCores-v2 | HBM del dispositivo (GiB) | RAM del host (GiB) | vCPU |
| --- | --- | --- | --- | --- | --- |
| inf2.xlarge | 1 | 2 | 32 | 16 | 4 |
| inf2.8xlarge | 1 | 2 | 32 | 128 | 32 |
| inf2.24xlarge | 6 | 12 | 192 | 384 | 96 |
| inf2.48xlarge | 12 | 24 | 384 | 768 | 192 |

### Asignación de Dispositivos y Rutas de Plugin

aws.amazon.com/neuron asigna **dispositivos completos**; aws.amazon.com/neuroncore asigna **cores**. El anterior ejemplo inf2.xlarge solicitaba neuron:2, ocho CPU y24Gi RAM en un nodo con un dispositivo, cuatro vCPU y16Gi RAM; no puede programarse. NEURON_RT_VISIBLE_CORES selecciona el ámbito runtime y no crea dispositivos no asignados. Compruebe la precedencia con NUM_CORES y la política de core lógico frente al lanzamiento elegido.

El Helm1.10.0 oficial inspeccionado incluye opciones de device-plugin, scheduler y node-problem-detector. Inspeccione los DaemonSets renderizados, hostPaths, RBAC y el comportamiento de recuperación antes de la instalación. Este comando solo genera salida local.

```bash
helm template neuron-audit oci://public.ecr.aws/neuron/neuron-helm-chart   --version 1.10.0 --namespace kube-system --include-crds > neuron-rendered.yaml
```

SDK2.32.0 documenta dos rutas independientes: **plugin NxD Inference0.5.x con vLLM0.16 para Inf2/Trn1/Trn2**, y el **nuevo beta vLLM Neuron0.24.0.1.1.0 solo para Trn2/Trn3**. La guía detallada de NxD aún muestra0.5.0/SDK2.29 mientras que el resumen muestra0.5.3; verifique el tag de plugin elegido, DLC y las dependencias exactas. Instalar el beta más reciente en Inf2 o añadir pip install a un DLC2.18 antiguo no constituye validación de compatibilidad.

La compilación Neuron requiere implementaciones de modelos admitidas, buckets de forma/batch/secuencia, TP, compiler/SDK, hardware y artefactos de caché. Llamar a torch_neuronx.trace en un modelo Transformers genérico con un diccionario tp_degree sin usar no implementa serving de LM causal distribuido. Los archivos de salida del compiler y los directorios tokenizer son artefactos diferentes. No se ejecutó ningún compiler ni instancia Neuron en esta auditoría.

## Rendimiento, Coste y Operaciones

Se eliminaron la tabla de clasificación A100 sin fuentes y las afirmaciones fijas de ahorro del40–70%. Compare el mismo modelo/revisión/precisión, distribución de tokens de entrada/salida, concurrencia, tasa de éxito, SLO, warmup y precios fechados. Un millón de solicitudes/día durante30días son30millones de solicitudes: unos hipotéticos48,000 dólares mensuales son1.60 dólares por1,000 solicitudes. La cifra anterior de0.80 era aritméticamente incorrecta; esta ilustración no corresponde a los precios actuales de AWS.

Pruebe mediante regresión las cargas útiles, templates, streaming, uso y comportamiento de fallos reales al cambiar de motor. Distinga los grupos de modelos fragmentados de las réplicas independientes, y compruebe si la preparación ordenada de StatefulSet bloquea workers que se esperan mutuamente. StatefulSet por sí solo no configura TP/PP, rendezvous ni NCCL.

Compare cachés locales, EBS, EFS y FSx usando el tamaño de modelo, la concurrencia de reinicio/descarga, autorización y coste. EFS no es universalmente más lento que FSx, y los límites históricos de gp3 no son garantías actuales. Consulte los [ejemplos de GPU/almacenamiento](01-ai-ml-workloads.md).

Antes de las operaciones, pruebe autenticación, TLS, rutas de gestión, probes, ubicación, cuotas, un único propietario de scaler, unidades de métricas, revisiones de modelo fijadas, ciclo de vida de caché, rollout/rollback y recuperación ante interrupciones en el entorno real.

## Alcance de la Verificación

Las comprobaciones cubren charts/CRDs oficiales, código fuente real de SDK/CLI, fixtures locales de solicitud/error HTTP, Markdown e imágenes. No se realizaron ejecución de modelos GPU/Neuron, mediciones de throughput/coste, despliegue cloud ni descarga de modelos. El éxito de esquema/chart no establece admisión, autorización, compatibilidad de modelos ni preparación para producción.

## Referencias

- [Notas de lanzamiento de NIM 2.0](https://docs.nvidia.com/nim/large-language-models/2.0.12/about-nim-llm/release-notes.html)
- [Configuración de NIM](https://docs.nvidia.com/nim/large-language-models/2.0.12/reference/environment-variables.html)
- [Observabilidad de NIM](https://docs.nvidia.com/nim/large-language-models/2.0.12/reference/logging-and-observability.html)
- [Dynamo 1.4.2](https://github.com/ai-dynamo/dynamo/tree/v1.4.2)
- [AIBrix 0.7.0](https://github.com/aibrix/aibrix/tree/v0.7.0)
- [Salida estructurada de SGLang 0.5.19](https://github.com/sgl-project/sglang/blob/v0.5.19/docs/docs/advanced_features/structured_outputs.mdx)
- [Aviso de mantenimiento de TGI](https://github.com/huggingface/text-generation-inference)
- [Ollama 0.34.0](https://github.com/ollama/ollama/tree/v0.34.0)
- [GenAI-Perf 0.0.16](https://pypi.org/project/genai-perf/0.0.16/)
- [Rutas de inferencia de Neuron SDK 2.32.0](https://github.com/aws-neuron/aws-neuron-sdk/blob/v2.32.0/libraries/vllm-neuron/neuron-inference-overview.rst)
- [Arquitectura de Inf2](https://awsdocs-neuron.readthedocs-hosted.com/en/latest/about-neuron/arch/neuron-hardware/inf2-arch.html)
- [Componentes Kubernetes de Neuron](https://github.com/aws-neuron/neuron-helm-charts)

## Cuestionario

[Cuestionario de Frameworks de Inferencia](../quizzes/ai-ml/04-inference-frameworks-quiz.md)
