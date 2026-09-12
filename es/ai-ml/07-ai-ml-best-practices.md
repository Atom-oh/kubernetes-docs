# Mejores prácticas de IA/ML en EKS

> **Última actualización**: September12,2026
> **Líneas base**: inference-perf0.6.1 / SOCI0.15.0 / Karpenter1.14.1 / External Secrets2.10.0

Evalúe las mejoras usando latencia, tasa de éxito, throughput (rendimiento), costo y recuperación para la misma carga de trabajo. Una GPU, un snapshotter o una función de compartición no garantizan un porcentaje fijo de aceleración ni de ahorro.

![Benchmarking, optimización del arranque, dispositivos, redes/almacenamiento, observabilidad, costo y seguridad evaluados con mediciones y comprobaciones de recuperación.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-0.html)

## Benchmarking de inferencia de LLM

![Ventanas de medición distintas para la primera salida, los intervalos entre tokens, la latencia end-to-end y el throughput/goodput agregado.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-1.html)

| Métrica | Definición y advertencias |
| --- | --- |
| TTFT | Desde el envío hasta recibir la primera **salida no vacía**; el primer frame HTTP/SSE no necesita contener un token |
| ITL | Intervalos entre tokens/chunks; un chunk de red puede contener varios tokens |
| TPOT | Promedio definido por la herramienta después del primer token; indefinido para uno o menos tokens de salida |
| E2E | Tiempo desde la solicitud hasta la finalización; registre los límites de cola, red y postprocesamiento |
| Throughput de solicitudes | Solicitudes completadas con éxito / ventana de medición especificada |
| Throughput de tokens | Suma de tokens de salida en la ventana / tiempo, no una media sin ponderar de las TPS por solicitud |
| Goodput | Tasa de solicitudes que cumplen los criterios de éxito y de SLO de latencia |

Con timestamps reales de tokens, el ITL medio es(tiempo del último token-tiempo del primero)/(tokens-1). Las respuestas sin streaming no pueden medir TTFT/ITL reales. Especifique el tokenizador, las salidas vacías o de un solo token, los fallos y las exclusiones de warmup.500ms/50ms no son SLO universales.

### inference-perf y GenAI-Perf

inference-perf es una herramienta de benchmark de Kubernetes SIGs/wg-serving. El paquete de PyPI inspeccionado es0.6.1, mientras que el pyproject de su tag de Git todavía indica0.5.0; esta discrepancia de metadatos queda registrada. La CLI real usa --config_file u opciones estructuradas como --server.type, no la antigua interfaz benchmark --endpoint --prompt-length.

Esta configuración **mock interna** no llama a ningún servidor de modelos. La CLI real0.6.1 completó tres solicitudes con un worker. Los recuentos de tokens del mock son cero y TTFT/TPOT son null, por lo que estos no son resultados de rendimiento de modelo.

```yaml
api:
  type: chat
  streaming: false
data:
  type: mock
load:
  type: concurrent
  stages:
    - concurrency_level: 1
      num_requests: 3
  num_workers: 1
  worker_max_concurrency: 1
  base_seed: 17
server:
  type: mock
  base_url: http://127.0.0.1:8000
report:
  request_lifecycle:
    summary: true
    per_stage: true
    per_request: true
storage:
  local_storage:
    path: ./benchmark-fixture-results
```

```bash
inference-perf --config_file benchmark-fixture.yaml
```

Antes de cambiar a un endpoint real, verifique los tipos de servidor/API, los alias de modelo, el streaming, el tokenizador y la autenticación. La configuración puede contener headers secretos y la configuración fusionada se registra en logs, así que valide la entrega y el enmascaramiento de credenciales. Conserve los archivos de salida, las solicitudes/respuestas en bruto y los fallos, respetando la privacidad del dataset y los permisos de uso.

Una tasa constante/Poisson mide las llegadas por segundo; la carga concurrente controla la concurrencia. Ajustes numéricos iguales no son equivalentes. Pruebe una línea base de una sola solicitud, rampas de carga acotadas, ráfagas y distribuciones realistas. Una curva de saturación por sí sola no demuestra un cuello de botella de CPU/GPU/memoria; inspeccione el profiling, las colas, la red y la capacidad del cliente.

Use las [opciones auditadas de profile/endpoint/service/token](04-inference-frameworks.md) de GenAI-Perf0.0.16, no combinaciones inventadas de --backend vllm. Las métricas de GPU requieren una recolección aparte; verifique los límites de CPU/red del generador de carga. Los Jobs de benchmark necesitan imágenes verificadas, claves de configuración, PVCs, deadlines y una semántica de reintentos que tenga en cuenta la carga duplicada.

## Optimización del arranque de contenedores

![Mida por separado la ubicación del Pod, la descarga/desempaquetado de imagen, el arranque del contenedor, la carga del modelo y la readiness.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-2.html)

Mida por separado la transferencia de imagen, el desempaquetado, la descarga/carga del modelo y la readiness (disponibilidad). Se eliminaron las tablas sin fuente de“siempre5–15minutos” y“80–95%de ahorro”.45GB/1Gbps≈360segundos es solo aritmética de transferencia idealizada, que excluye el tamaño comprimido, el protocolo, el disco y la sobrecarga de concurrencia: no es un tiempo de pull medido.

Los artefactos de modelo externos pueden reducir los cambios y pulls de imagen, pero añaden costos de descarga y de gestión de caché. Las imágenes preparadas pueden ser apropiadas en algunos entornos. La inicialización debe propagar los fallos y verificar la revisión, los checksums y la finalización. El antiguo sync de S3 seguido de un echo exitoso podía ocultar un fallo de descarga y fue eliminado.

Las builds multietapa deben alinear el intérprete/ABI de Python y las bibliotecas de CUDA/runtime, incluidos los ejecutables y las bibliotecas compartidas. No suponga que python3.11 y pip3 de Ubuntu22.04 usan el mismo intérprete ni copie solo site-packages. Use paquetes/wheels de distribución soportados y pruebe los imports y entrypoints dentro de la imagen. Prefiera sistemas de archivos raíz de solo lectura con montajes de caché/tmp/modelo escribibles explícitos.

### SOCI0.15

SOCI admite la carga diferida de imágenes, pero los beneficios pueden reducirse cuando el arranque lee de inmediato todos los pesos y bibliotecas. Tener un índice no configura CRI para usar el snapshotter de SOCI. Verifique la integración con containerd/CRI, los digests de imagen/índice y la compatibilidad del registro. Se eliminó el DaemonSet privilegiado no verificado que exponía sockets de containerd del host.

En la versión0.15, create/push toman referencias de imagen posicionales, no --ref. La guía de inicio actual usa convert para crear imágenes habilitadas para SOCI. El modo standalone procesa layouts OCI locales sin containerd ni sudo.

```bash
soci convert --standalone --format oci-dir input-oci-layout output-soci-layout
```

Las entradas deben ser layouts OCI, no tarballs ordinarios de docker-save. La conversión puede fallar si cada capa es más pequeña que min-layer-size. Esta auditoría convirtió una capa sintética con min-layer-size=0 explícito y verificó ocho digests de blobs. No se ejecutó ningún benchmark de arranque de contenedores. Conserve juntos la imagen convertida y el índice al publicarlos.

### Bootstrap de Bottlerocket

En1.64, `bootstrap-containers.<name>.user-data` son **datos base64**, consumidos como archivo por el bootstrap container. El texto de shell en claro dentro de los settings no se ejecuta automáticamente. La imagen de origen debe ser real y usar correctamente los almacenes/namespaces de imágenes del host. Una etiqueta estática images-prefetched=true no es evidencia de éxito.

mode=once pasa a off después de la ejecución. El fallo con essential=true detiene el arranque; false permite el fallo, así que alinee el ajuste con las necesidades de readiness. allowed-unsafe-sysctls no es un interruptor de contenedor privilegiado. Incluya en las mediciones el efecto del prefetch sobre el tiempo de preparación del nodo.

## Selección de GPU, Neuron y almacenamiento

Parámetros×bytes es solo el límite inferior de los pesos. Incluya la KV cache según la arquitectura, las activaciones, el workspace, los buffers de comunicación, la fragmentación y las restricciones de sharding.Los pesos FP16 de13B≈26GB no caben en24GB;70B FP16≈140GB supera el total de cuatro GPUs de24GB. Más CPUs de host no amplían la VRAM de GPU si esta no cambia.

Distinga p4d.24xlarge con8×40GB de p4de con8×80GB A100. G5g usa Arm/T4G; verifique la arquitectura de imagen/kernel. Consulte la [tabla auditada de Inf2](04-inference-frameworks.md) para inf2.48xlarge con192vCPUs/768GiB de RAM de host,12chips/24NeuronCores/384GiB de HBM. Un nombre de familia como P5 no fija los recuentos de GPU en todos los tamaños. Vuelva a comprobar las generaciones disponibles, las regiones, las cuotas y los precios al elegir.

LoRA reduce el estado entrenable del adaptador, pero conserva los pesos base y las activaciones, y difiere de QLoRA. No use una función que asuma que la mayoría de los modelos LoRA caben en24GB. Mida la memoria máxima, la latencia, el throughput y los reinicios.

No seleccione el almacenamiento únicamente por un umbral de dataset de10TB. Compare los patrones de acceso, la concurrencia, los metadatos, la latencia, la semántica, la durabilidad y el costo. La documentación general actual de gp3 indica una línea base de3000IOPS/125MiB/s y un máximo de80000IOPS/2000MiB/s, sujeto a restricciones de tamaño/IOPS/instancia; Outposts difiere. Los límites históricos de16000IOPS/1GB/s no son universalmente vigentes.

Use la [guía de infraestructura](06-ai-infrastructure.md) para el throughput Elastic de EFS, las asociaciones FSx/CSI/S3 y los límites POSIX de Mountpoint. S3 no tiene throughput infinito ni latencia fija; EFS no es universalmente más lento que FSx. El instance store y tmpfs son efímeros. La KV cache de GPU normalmente reside en memoria de GPU, no automáticamente en SSD/tmpfs.

### Verificación de la caché de modelos

Un archivo config.json no demuestra que los pesos terminaron de descargarse. Verifique **todos los archivos** contra un manifiesto/revisión de release de confianza antes de exponer almacenamiento inmutable de solo lectura. Evite carreras entre descargadores concurrentes y archivos escritos parcialmente.

Este validador local no realiza descargas ni eliminaciones. Las pruebas cubren archivos completos, revisiones incorrectas, pesos parciales o ausentes, traversal y symlinks externos. La confianza en el manifiesto y la inmutabilidad posterior a la verificación siguen siendo requisitos aparte.

```python
from pathlib import Path
import hashlib
import re


def verify_model_cache(root, manifest, expected_revision):
    """Verify files against a separately trusted release manifest; no downloads/deletion."""
    root = Path(root).resolve(strict=True)
    if manifest.get("revision") != expected_revision:
        raise ValueError("Model revision mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Empty or invalid release manifest")
    for relative, expected_hash in files.items():
        name = Path(relative)
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise ValueError("Unsafe manifest path")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("Invalid SHA256")
        target = (root / name).resolve(strict=True)
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("File escapes the cache or is not a regular file")
        digest = hashlib.sha256()
        with target.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected_hash:
            raise ValueError("Incomplete or corrupt model file: " + relative)
    return root
```

Los checkpoints necesitan el estado del optimizador/RNG/cursor de datos y de los shards, como en el [ejemplo de entrenamiento/recuperación](05-model-training.md). No elimine copias válidas previas antes de que la transferencia, los checksums y los manifiestos de finalización tengan éxito. El antiguo bucle ls/xargs rm -rf confundía el contenido de directorios con rutas de checkpoint e intentaba eliminar a través de un montaje de solo lectura; fue eliminado. Retrasar el primer sync30minutos u omitir el flush en la terminación aumenta la exposición a pérdida de trabajo.

## Redes y planificación

EFA mejora la comunicación para cargas de trabajo adecuadas; no es obligatorio para toda ejecución de DDP. Verifique las interfaces, la ubicación en la misma AZ, el driver/libfabric/aws-ofi-nccl, los recursos del Pod, los security groups y el transporte real. Las etiquetas de RAID0/subred no lo habilitan. Evite un NCCL_TIMEOUT no verificado y ajustes de Ring/Simple/IB_DISABLE copiados a ciegas. torchrun --nnodes cuenta nodos, no el WORLD_SIZE total de procesos.

Use el placementGroupSelector real de Karpenter1.14.1. Una etiqueta aws:ec2:placement-group no es la API de placement, y aws: no es un namespace de etiquetas de usuario. Este **ejemplo de esquema** requiere identificadores aprobados de AMI/subred/SG/rol y un placement group existente. El ejemplo especifica amiFamily AL2023, por lo que el reemplazo debe ser una AMI de EKS AL2023 validada, no una AMI de otro sistema operativo. No completa la configuración de networkInterfaces para EFA.

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: prepared-gpu-class
spec:
  role: REPLACE_WITH_APPROVED_NODE_ROLE
  amiSelectorTerms:
  - id: ami-0123456789abcdef0
  subnetSelectorTerms:
  - id: subnet-0123456789abcdef0
  securityGroupSelectorTerms:
  - id: sg-0123456789abcdef0
  placementGroupSelector:
    name: prepared-training-placement-group
  amiFamily: AL2023
```

### Presupuestos de disrupción y Spot

Este presupuesto se aplica de lunes a viernes de **09:00–17:00UTC**. El antiguo0 9-17 * * 1-5 iniciaba una ventana de ocho horas cada hora hasta las17:00, extendiendo la protección hasta la01:00del día siguiente. Los presupuestos concurrentes aplican la restricción más estricta y no siguen automáticamente las zonas horarias locales.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-gpu-pool
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: prepared-gpu-class
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: '0'
      schedule: 0 9 * * 1-5
      duration: 8h
    - nodes: 30%
```

budgets.nodes=0 limita la disrupción voluntaria, no las interrupciones de Spot, los fallos de nodo ni la expiración forzada. Los requirements exclusivos de Spot son obligatorios, no una preferencia con fallback a on-demand. La distribución de topología con ScheduleAnyway es soft (flexible); verifique las réplicas reales, la capacidad y la distribución por AZ.

terminationGracePeriodSeconds=120 no garantiza que EC2 conceda120segundos. Pruebe la readiness/drenaje del gateway, la propagación de endpoints, SIGTERM, los streams activos, los reintentos y los duplicados mediante una terminación real. No invente una API /drain de vLLM. Las cachés de inferencia, las sesiones y los grupos TP conllevan estado y costos de reinicio.

## Observabilidad y costo

Use las [métricas actuales de vLLM](02-vllm-deployment.md) y las [reglas de DCGM](06-ai-infrastructure.md). La ocupación de KV es vllm:kv_cache_usage_perc, no el antiguo gpu_cache_usage_perc. Observe las colas/preempción y el comportamiento del backend en lugar de suponer que una caché llena rechaza solicitudes de inmediato. Derive las tasas de acierto de prefijo de los contadores actuales de hits/consultas, manejando el denominador cero.

FB_USED/FREE de DCGM son gauges en MiB; XID_ERRORS es el último código. Evite un FB_TOTAL inexistente o increase() sobre gauges. La temperatura por sí sola no demuestra throttling térmico; compare los clocks, la potencia, las razones de throttle y la carga de trabajo. Haga coincidir las etiquetas de Prometheus y la agregación de histogramas, y use una sintaxis de subquery válida para avg_over_time sobre expresiones.

VPA en modo Off proporciona recomendaciones de CPU/memoria, no una selección automática de instancias de GPU. El antiguo script de rightsizing inspeccionaba solo la primera serie y comparaba proporciones0–1con50/90; fue eliminado. Inspeccione los picos, las colas, los SLO y la recuperación después de eliminarlo en todas las cargas de trabajo.

Registre los ahorros usando la región/SO/condiciones de compra reales, la utilización, el tiempo inactivo o de fallo, el almacenamiento, la transferencia y las operaciones. Spot/Savings Plans/RI difieren en descuentos y garantías de capacidad. Evite tablas fijas de60–90% o sumar porcentajes de ahorro por optimización. Tome las decisiones de compra con compromiso por separado, usando líneas base medidas y su variabilidad.

## Acceso a modelos y gestión de secretos

ListBucket y GetObject de S3 usan ARNs de bucket y de objeto respectivamente, junto con claves de condición soportadas. Los buckets de propósito general pueden usar condiciones de etiqueta de bucket como aws:ResourceTag/Environment una vez que ABAC se habilita explícitamente. ABAC está deshabilitado por defecto: verifique el estado del bucket, los permisos de administración de etiquetas de confianza, las políticas de identidad/bucket y el emparejamiento de acción/recurso en lugar de copiar solo la condición de etiqueta. Habilitarlo no crea el Allow necesario ni anula otras políticas Deny. Verifique el namespace/nombre de la ServiceAccount vinculada a la trust policy, las cadenas de credenciales del SDK y la identidad real de la solicitud. vLLM no descarga automáticamente cualquier URI de modelo en S3.

El CRD de ESO2.10.0 inspeccionado **sirve v1**, con v1beta1 en served=false. Este ejemplo referencia un SecretStore ya aprobado en el mismo namespace. Prepare las claves remotas, los permisos, la rotación y el ciclo de vida del target por separado.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: model-download-token
  namespace: ai-ml
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: approved-secrets-manager
    kind: SecretStore
  target:
    name: model-download-credential
    creationPolicy: Owner
  data:
  - secretKey: token
    remoteRef:
      key: approved/model-download
      property: token
```

Monte los Secrets de Kubernetes como volúmenes y haga que las aplicaciones vuelvan a leer los archivos cuando sea necesario. Los montajes con subPath no reciben actualizaciones automáticas; las variables de entorno o los valores leídos solo en el arranque no se recargan automáticamente. El refresh de ESO no es en sí la emisión/rotación de credenciales upstream. Verifique la rotación del proveedor, el acceso al Secret y la recarga en la aplicación por separado.

Los registros de la API de Secrets Manager en CloudTrail no capturan cada lectura de la aplicación de un archivo de Secret local. No afirme que kubectl describe imprime en general los valores de SecretKeyRef, pero la entrega por entorno sigue exponiendo superficies de proceso/depuración y difiere de una política de credenciales en archivo. Nunca imprima secretos reales en ejemplos ni logs.

NetworkPolicy requiere aplicación por parte del CNI. Verifique la semántica AND/OR de los selectores, las etiquetas de nombre de namespace por defecto y el DNS tanto en TCP como en UDP. Se eliminaron la apertura de health-check a10.0.0.0/8 y la regla de que“internet443significa solo S3”. Con modelos preparados, restrinja el egress en runtime a las rutas necesarias y distinga las APIs de inferencia y de administración en el gateway.

Los logs de auditoría deberían capturar la identidad de usuario/carga de trabajo, la revisión del modelo, la acción, el resultado y el ID de solicitud, enmascarando prompts y secretos según corresponda. Parsear los logs CRI de containerd como si fueran de Docker o retener solo las líneas que contienen request puede perder eventos de auditoría. Verifique los collectors, parsers, IAM, buffers, retención y fallos de entrega reales, no solo un ConfigMap.

## Alcance de la verificación

Se revisaron toda la prosa de las guías/cuestionarios y87bloques de código únicos. La validación incluye tres solicitudes mock nativas de inference-perf, la conversión OCI local de SOCI, seis casos de caché, tres esquemas de Karpenter/ESO y aritmética de cron. No se ejecutó ningún benchmark de GPU/modelo real, medición de arranque de contenedores, instalación de SOCI en el host, recurso en la nube ni proveedor de secretos.

## Referencias

- [inference-perf0.6.1](https://github.com/kubernetes-sigs/inference-perf/tree/v0.6.1)
- [CLI de SOCI0.15](https://github.com/awslabs/soci-snapshotter/blob/v0.15.0/docs/cli-usage.md)
- [Ajustes de bootstrap de Bottlerocket1.64](https://bottlerocket.dev/en/os/1.64.x/api/settings/bootstrap-containers/)
- [CRDs de Karpenter1.14.1](https://github.com/aws/karpenter-provider-aws/tree/v1.14.1/pkg/apis/crds)
- [Disrupción en Karpenter](https://karpenter.sh/docs/concepts/disruption/)
- [CRD ExternalSecret de ESO2.10](https://github.com/external-secrets/external-secrets/blob/helm-chart-2.10.0/config/crds/bases/external-secrets.io_externalsecrets.yaml)
- [Actualizaciones de Secret en Kubernetes](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Habilitación de ABAC en buckets de propósito general de S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/buckets-tagging-enable-abac.html)
- [Rendimiento de EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)

## Cuestionario

[Cuestionario de mejores prácticas de IA/ML](../quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
