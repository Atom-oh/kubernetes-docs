# Mejores prácticas de IA/ML en EKS

> **Última actualización**: 12 de septiembre de 2026
> **Líneas base**: inference-perf0.6.1 / SOCI0.15.0 / Karpenter1.14.1 / External Secrets2.10.0

Evalúe las mejoras según la latencia, la tasa de éxito, el rendimiento, el costo y la recuperación para la misma carga de trabajo. Una GPU, un snapshotter o una función de uso compartido no garantiza una mejora de velocidad ni un porcentaje de ahorro determinados.

![Evaluación del rendimiento, la optimización del inicio, los dispositivos, las redes y el almacenamiento, la observabilidad, los costos y la seguridad mediante mediciones y comprobaciones de recuperación.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-0.html)

## Evaluación del rendimiento de inferencia de LLM

![Ventanas de medición diferenciadas para la primera salida, los intervalos entre tokens, la latencia de extremo a extremo y el rendimiento/goodput agregado.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-1.html)

| Métrica | Definición y salvedades |
| --- | --- |
| TTFT | Tiempo desde el envío hasta la recepción de la primera **salida no vacía**; el primer frame HTTP/SSE no necesariamente contiene un token |
| ITL | Intervalos entre tokens/trozos; un fragmento de red puede contener varios tokens |
| TPOT | Promedio definido por la herramienta después del primer token; no está definido si se generan cero o un solo token |
| E2E | Tiempo desde la solicitud hasta su finalización; registre los límites de cola, red y posprocesamiento |
| Rendimiento de solicitudes | Solicitudes completadas correctamente / ventana de medición especificada |
| Rendimiento de tokens | Suma de los tokens de salida en la ventana / tiempo, no un promedio no ponderado del TPS de las solicitudes |
| Goodput | Tasa de solicitudes que cumplen los criterios de éxito y latencia de los SLO |

Con marcas de tiempo reales de los tokens, el ITL medio es (hora del último token - hora del primero)/(tokens-1). Las respuestas que no se transmiten en streaming no permiten medir el TTFT/ITL real. Especifique el tokenizador, las salidas vacías/de un solo token, los errores y las exclusiones del calentamiento. 500 ms/50 ms no son SLO universales.

### inference-perf y GenAI-Perf

inference-perf es una herramienta de pruebas comparativas de Kubernetes SIGs/wg-serving. El paquete de PyPI inspeccionado es la versión 0.6.1, mientras que el pyproject de su etiqueta Git todavía indica 0.5.0; se documenta esta discrepancia de metadatos. La CLI real usa --config_file u opciones estructuradas como --server.type, no la interfaz anterior de benchmark --endpoint --prompt-length.

Esta configuración de **simulación interna** no llama a ningún servidor de modelos. La CLI real 0.6.1 completó tres solicitudes con un trabajador. La cantidad de tokens simulada es cero y TTFT/TPOT son nulos, por lo que estos no son resultados de rendimiento de modelos.

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

Antes de cambiar a un endpoint real, verifique los tipos de servidor/API, los alias del modelo, el streaming, el tokenizador y la autenticación. El archivo de configuración puede contener encabezados secretos y la configuración combinada queda registrada en los logs; por ello, valide la entrega y el enmascaramiento de credenciales. Conserve los archivos de salida, las solicitudes/respuestas sin procesar y los errores, respetando la privacidad de los conjuntos de datos y los permisos de uso.

La tasa constante/Poisson mide las llegadas por segundo; la carga concurrente controla la concurrencia. Los mismos valores numéricos no son equivalentes. Pruebe una línea base de una sola solicitud, aumentos graduales de carga acotados, ráfagas y distribuciones realistas. Una curva de saturación por sí sola no demuestra un cuello de botella de CPU/GPU/memoria; inspeccione el perfil, las colas, las redes y la capacidad del cliente.

Use las opciones verificadas de [perfil, endpoint, servicio y token de GenAI-Perf 0.0.16](04-inference-frameworks.md), no combinaciones inventadas de --backend vllm. Las métricas de GPU requieren recopilación por separado; compruebe los límites de CPU/red del generador de carga. Los Jobs de pruebas de rendimiento necesitan imágenes y claves de configuración verificadas, PVC, plazos y una semántica de reintentos que tenga en cuenta la carga duplicada.

## Optimización del inicio de contenedores

![Mida por separado la colocación del Pod, la descarga/descompresión de imágenes, el inicio del contenedor, la carga del modelo y la preparación.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-2.html)

Mida por separado la transferencia de imágenes, la descompresión, la descarga/carga del modelo y la preparación. Se eliminaron las tablas sin fuentes que afirmaban “siempre 5–15 minutos” y “ahorros del 80–95 %”. 45 GB/1 Gbps ≈ 360 segundos es solo un cálculo idealizado de transferencia, que no incluye el tamaño comprimido ni la sobrecarga de protocolo, disco y concurrencia; no es un tiempo de descarga medido.

Los artefactos de modelos externos pueden reducir los cambios/descargas de imágenes, pero añaden costos de descarga y gestión de caché. Las imágenes preparadas pueden ser adecuadas en algunos entornos. La inicialización debe propagar los errores y verificar la revisión, las sumas de comprobación y la finalización. Se eliminó el anterior comando de sincronización de S3 seguido de un echo exitoso, que podía ocultar errores de descarga.

Las compilaciones de varias etapas deben tener versiones compatibles del intérprete/ABI de Python y de las bibliotecas de CUDA/runtime, incluidos los ejecutables y las bibliotecas compartidas. No dé por sentado que python3.11 de Ubuntu 22.04 y pip3 usan el mismo intérprete ni copie solo site-packages. Use paquetes/wheels compatibles con la distribución y pruebe las importaciones y los puntos de entrada dentro de la imagen. Prefiera sistemas de archivos raíz de solo lectura con montajes explícitos y escribibles para caché/tmp/modelos.

### SOCI 0.15

SOCI permite la carga diferida de imágenes, pero sus ventajas pueden reducirse si el inicio lee de inmediato todos los pesos/bibliotecas. Tener un índice no configura CRI para que use el snapshotter de SOCI. Verifique la integración de containerd/CRI, los digests de la imagen/índice y la compatibilidad del registro. Se eliminó el DaemonSet privilegiado no verificado que exponía sockets de containerd del host.

En la versión 0.15, create/push reciben referencias de imagen posicionales, no --ref. La guía de inicio actual usa convert para crear imágenes con SOCI habilitado. El modo independiente procesa diseños OCI locales sin containerd ni sudo.

```bash
soci convert --standalone --format oci-dir input-oci-layout output-soci-layout
```

Las entradas deben ser diseños OCI, no archivos tar ordinarios de docker-save. La conversión puede fallar si todas las capas son menores que min-layer-size. En esta auditoría se convirtió una capa sintética con min-layer-size=0 explícito y se verificaron ocho digests de blobs. No se ejecutó ningún benchmark de inicio de contenedores. Al publicar, conserve juntos la imagen y el índice convertidos.

### Inicio de Bottlerocket

En 1.64, `bootstrap-containers.<name>.user-data` contiene **datos codificados en base64**, que el contenedor de arranque consume como archivo. El texto de shell sin formato en la configuración no se ejecuta automáticamente. La imagen de origen debe existir y usar correctamente los almacenes y espacios de nombres de imágenes del host. Una etiqueta estática images-prefetched=true no demuestra que la operación haya tenido éxito.

mode=once pasa a ser off después de la ejecución. Si falla essential=true, se detiene el arranque; false permite que falle, así que ajuste la configuración a las necesidades de preparación. allowed-unsafe-sysctls no es un conmutador de contenedores privilegiados. Incluya el efecto de la precarga en el tiempo de preparación del nodo en las mediciones.

## Selección de GPU, Neuron y almacenamiento

Parámetros × bytes es solo el límite inferior de los pesos. Incluya la caché KV considerando la arquitectura, las activaciones, el espacio de trabajo, los búferes de comunicación, la fragmentación y las restricciones de particionamiento. Los pesos FP16 de 13B ≈ 26 GB no caben en 24 GB; 70B en FP16 ≈ 140 GB superan los 96 GB combinados de cuatro GPU de 24 GB. Más CPU de host no amplía la VRAM de GPU sin cambios.

Distinga p4d.24xlarge, con 8 GPU de 40 GB cada una, de p4de, con 8 GPU A100 de 80 GB cada una. G5g usa Arm/T4G; verifique la arquitectura de la imagen/kernel. Consulte la [tabla auditada de Inf2](04-inference-frameworks.md) para inf2.48xlarge: 192 vCPU/768 GiB de RAM de host, 12 chips/24 NeuronCores/384 GiB de HBM. Un nombre de familia como P5 no determina la cantidad de GPU en todos los tamaños. Vuelva a comprobar las generaciones, regiones, cuotas y precios disponibles al elegir.

LoRA reduce el estado de los adaptadores entrenables, pero mantiene los pesos/activaciones base y es distinto de QLoRA. No use una función que dé por sentado que la mayoría de los modelos LoRA caben en 24 GB. Mida la memoria máxima, la latencia, el rendimiento y los reinicios.

No seleccione el almacenamiento únicamente por un umbral de conjunto de datos de 10 TB. Compare los patrones de acceso, la concurrencia, los metadatos, la latencia, la semántica, la durabilidad y el costo. La documentación general actual de gp3 indica una línea base de 3000 IOPS/125 MiB/s y un máximo de 80000 IOPS/2000 MiB/s, sujetos a restricciones de tamaño/IOPS/instancia; Outposts es distinto. Los límites históricos de 16000 IOPS/1 GB/s no están vigentes universalmente.

Use la [guía de infraestructura](06-ai-infrastructure.md) para el rendimiento Elastic de EFS, las asociaciones de FSx/CSI/S3 y los límites POSIX de Mountpoint. S3 no tiene rendimiento infinito ni latencia fija; EFS no es siempre más lento que FSx. El almacenamiento de instancia/tmpfs es efímero. La caché KV de GPU normalmente reside en la memoria de la GPU, no automáticamente en SSD/tmpfs.

### Verificación de la caché del modelo

La presencia de config.json no demuestra que haya finalizado la descarga de los pesos. Verifique **todos los archivos** con un manifiesto de publicación/revisión confiable antes de exponer almacenamiento inmutable de solo lectura. Evite las condiciones de carrera entre descargadores simultáneos y los archivos escritos parcialmente.

Este validador local no descarga ni elimina archivos. Las pruebas abarcan archivos completos, revisiones incorrectas, pesos parciales/ausentes, ataques de traversal de rutas y enlaces simbólicos externos. La confianza en el manifiesto y la inmutabilidad posterior a la verificación siguen siendo requisitos independientes.

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

Los puntos de control necesitan el estado del optimizador/RNG/cursor de datos y de los shards, como en el [ejemplo de entrenamiento/recuperación](05-model-training.md). No elimine copias válidas anteriores hasta que la transferencia, las sumas de comprobación y los manifiestos de finalización se hayan completado correctamente. Se eliminó el antiguo bucle ls/xargs rm -rf, que confundía el contenido de directorios con las rutas de los puntos de control e intentaba eliminar archivos a través de un montaje de solo lectura. Retrasar 30 minutos la primera sincronización u omitir el vaciado durante la terminación aumenta el riesgo de perder trabajo.

## Redes y programación

EFA mejora la comunicación para las cargas de trabajo adecuadas; no es obligatorio para todas las ejecuciones de DDP. Verifique las interfaces, la colocación en la misma AZ, driver/libfabric/aws-ofi-nccl, los recursos del Pod, los grupos de seguridad y el transporte real. RAID0/las etiquetas de subred no lo habilitan. Evite NCCL_TIMEOUT no verificado y los ajustes Ring/Simple/IB_DISABLE copiados sin criterio. torchrun --nnodes cuenta nodos, no el WORLD_SIZE total de procesos.

Use el placementGroupSelector real de Karpenter 1.14.1. Una etiqueta aws:ec2:placement-group no es la API de colocación, y aws: no es un espacio de nombres para etiquetas de usuario. Este **ejemplo de esquema** requiere identificadores aprobados de AMI/subred/SG/rol y un grupo de ubicación (placement group) existente. El ejemplo especifica amiFamily AL2023, por lo que la sustitución debe ser una AMI de EKS AL2023 validada, no una AMI de otro sistema operativo. No completa la configuración de EFA networkInterfaces.

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

### Presupuestos de interrupción y Spot

Este presupuesto se aplica de lunes a viernes, de **09:00 a 17:00 UTC**. El antiguo 0 9-17 * * 1-5 iniciaba una ventana de ocho horas cada hora hasta las 17:00, prolongando la protección hasta la 01:00 del día siguiente. Los presupuestos simultáneos aplican la restricción más estricta y no se ajustan automáticamente a las zonas horarias locales.

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

budgets.nodes=0 limita las interrupciones voluntarias, no las interrupciones de Spot, los fallos de nodos ni la expiración forzosa. Los requisitos exclusivos de Spot son obligatorios, no una preferencia con capacidad bajo demanda como alternativa. ScheduleAnyway para la distribución de topología es una configuración flexible; verifique las réplicas, la capacidad y la distribución entre AZ reales.

terminationGracePeriodSeconds=120 no garantiza que EC2 conceda 120 segundos. Pruebe la preparación/drenaje del gateway, la propagación de endpoints, SIGTERM, los streams activos, los reintentos y los duplicados durante una terminación real. No invente una API /drain de vLLM. Las cachés de inferencia, las sesiones y los grupos TP conllevan costos de estado/reinicio.

## Observabilidad y costos

Use las [métricas actuales de vLLM](02-vllm-deployment.md) y las [reglas de DCGM](06-ai-infrastructure.md). La ocupación de KV es vllm:kv_cache_usage_perc, no el antiguo gpu_cache_usage_perc. Observe las colas/la expulsión y el comportamiento del backend en vez de suponer que la caché completa rechaza las solicitudes de inmediato. Calcule las tasas de aciertos de prefijos a partir de los contadores actuales de aciertos/consultas y contemple el caso de denominador cero.

DCGM FB_USED/FREE son gauges en MiB; XID_ERRORS es el último código. Evite FB_TOTAL, que no existe, o increase() aplicado a gauges. La temperatura por sí sola no demuestra limitación térmica; compare los clocks, la potencia, los motivos de limitación y la carga de trabajo. Haga coincidir las etiquetas de Prometheus y la agregación de histogramas, y use sintaxis válida de subconsulta para avg_over_time aplicado a expresiones.

VPA Off proporciona recomendaciones de CPU/memoria, no selección automática de instancias GPU. Se eliminó el anterior script de ajuste de tamaño, que inspeccionaba solo la primera serie y comparaba proporciones de 0–1 con 50/90. Inspeccione los picos, las colas, los SLO y la recuperación tras la eliminación en todas las cargas de trabajo.

Registre los ahorros con los precios reales por región, sistema operativo y modalidad de compra, además de la utilización, el tiempo de inactividad o fallos, el almacenamiento, la transferencia y la operación. Spot/Savings Plans/RI difieren en descuentos y garantías de capacidad. Evite tablas con porcentajes fijos del 60–90 % o sumar porcentajes de ahorro de optimizaciones. Tome las decisiones de compra de compromisos por separado, basándose en líneas base medidas y variabilidad.

## Acceso a modelos y gestión de secretos

S3 ListBucket y GetObject usan ARN de bucket/objeto y claves de condición compatibles, respectivamente. Los buckets de uso general pueden usar condiciones basadas en etiquetas de bucket, como aws:ResourceTag/Environment, una vez que se habilite explícitamente ABAC. ABAC está deshabilitado de forma predeterminada: verifique el estado del bucket, los permisos confiables para administrar etiquetas, las políticas de identidad/bucket y la correspondencia entre acciones y recursos, en vez de copiar solo la condición de etiqueta. Habilitarlo no crea el Allow necesario ni anula otras políticas Deny. Verifique el namespace/nombre del ServiceAccount vinculado a la relación de confianza, las cadenas de credenciales del SDK y la identidad real de la solicitud. vLLM no descarga automáticamente todos los URI de modelos de S3.

El CRD de ESO 2.10.0 inspeccionado **sirve v1**; v1beta1 tiene served=false. Este ejemplo hace referencia a un SecretStore aprobado que ya existe en el mismo namespace. Prepare por separado las claves remotas, los permisos, la rotación y el ciclo de vida del recurso de destino.

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

Monte los Secrets de Kubernetes como volúmenes y haga que las aplicaciones vuelvan a leer los archivos cuando sea necesario. Los montajes subPath no reciben actualizaciones automáticas; las variables de entorno o los valores que solo se leen durante el inicio no se recargan automáticamente. La actualización de ESO no es, por sí sola, la emisión/rotación de credenciales del proveedor. Verifique por separado la rotación del proveedor, el acceso al Secret y la recarga de la aplicación.

Los registros de la API de Secrets Manager de CloudTrail no capturan todas las lecturas que hace una aplicación de un archivo Secret local. No afirme que kubectl describe suele mostrar valores de SecretKeyRef, pero tenga en cuenta que la entrega mediante variables de entorno sigue exponiendo superficies de procesos/depuración y difiere de una política de credenciales en archivo. Nunca imprima secretos reales en ejemplos/logs.

NetworkPolicy requiere que CNI aplique las políticas. Verifique la semántica AND/OR de los selectores, las etiquetas predeterminadas de nombre de namespace y DNS por TCP/UDP. Se eliminaron la apertura de comprobaciones de estado a 10.0.0.0/8 y la regla de que “internet 443 significa solo S3”. Con modelos preparados, restrinja el egreso en tiempo de ejecución a las rutas necesarias y distinga las API de inferencia/gestión en el gateway.

Los registros de auditoría deben capturar la identidad del usuario/carga de trabajo, la revisión del modelo, la acción, el resultado y el ID de solicitud, enmascarando los prompts/secretos según corresponda. Analizar los registros CRI de containerd como si fueran Docker o conservar solo las líneas que contienen request puede hacer que se pierdan eventos de auditoría. Verifique los recopiladores, analizadores, IAM, búferes, retención y errores de entrega reales, no solo un ConfigMap.

## Alcance de la verificación

Se revisó toda la prosa original de la guía y el cuestionario, así como los 87 bloques de código únicos. La validación incluye tres solicitudes de simulación nativas de inference-perf, conversión OCI local de SOCI, seis casos de caché, tres esquemas de Karpenter/ESO y cálculos de cron. No se ejecutaron pruebas de rendimiento con GPU ni modelos reales, mediciones del inicio de contenedores, instalaciones de SOCI en el host, recursos en la nube ni proveedores de secretos.

## Referencias

- [inference-perf 0.6.1](https://github.com/kubernetes-sigs/inference-perf/tree/v0.6.1)
- [CLI de SOCI 0.15](https://github.com/awslabs/soci-snapshotter/blob/v0.15.0/docs/cli-usage.md)
- [Configuración de contenedores de arranque de Bottlerocket 1.64](https://bottlerocket.dev/en/os/1.64.x/api/settings/bootstrap-containers/)
- [CRD de Karpenter 1.14.1](https://github.com/aws/karpenter-provider-aws/tree/v1.14.1/pkg/apis/crds)
- [Interrupciones de Karpenter](https://karpenter.sh/docs/concepts/disruption/)
- [CRD ExternalSecret de ESO 2.10](https://github.com/external-secrets/external-secrets/blob/helm-chart-2.10.0/config/crds/bases/external-secrets.io_externalsecrets.yaml)
- [Actualizaciones de Secret de Kubernetes](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Habilitación de ABAC para buckets de uso general de S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/buckets-tagging-enable-abac.html)
- [Rendimiento de EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)

## Cuestionario

[Cuestionario sobre mejores prácticas de IA/ML](../quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
