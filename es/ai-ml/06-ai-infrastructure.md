# Infraestructura de IA en EKS

> **Última actualización**: September12,2026
> **Líneas base**: GPU Operator26.7.0 / NVIDIA DRA0.5.0 / Argo Workflows4.1.3 / JupyterHub chart4.4.2 / Mountpoint CSI2.8.0

La infraestructura de IA combina notebooks, pipelines, runtimes distribuidos, dispositivos/nodos, almacenamiento/redes y autorización. Una lista de herramientas o un Helm release exitoso no establece la seguridad, disponibilidad ni ejecución de modelos de la plataforma.

## Capas y responsabilidades

![Capas que separan las responsabilidades de carga de trabajo, plataforma, cómputo y fundación de EKS.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-0.html)

Las cargas de trabajo son propietarias del código de modelo/datos/ejecución; las plataformas, de los workflows, runtimes y registros; el cómputo, de los dispositivos reales, los Pods y la capacidad de nodos. Las identidades de IAM, redes y almacenamiento abarcan estas capas. Un NodePool habilitado para Spot no garantiza ni capacidad ni recuperación/ahorros.

## Stack JARK

JARK combina JupyterHub, Argo Workflows, Ray y Karpenter. Es un patrón de integración, no un producto conectado automáticamente. Conecte explícitamente la autorización de notebooks, el envío de workflows, los trabajos de Ray, la programación de Kubernetes y el aprovisionamiento de nodos.

![JupyterHub/Argo/Ray crean cargas de trabajo de Kubernetes; el scheduler coloca Pods y Karpenter aprovisiona nodos.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-1.html)

### Autenticación de JupyterHub y perfiles de notebook

Chart4.4.2 declara appVersion5.5.2, distinta de la última Hub6.0.0 de PyPI inspeccionada. Las comprobaciones locales de API usaron Hub6.0.0/OAuthenticator17.4.0/KubeSpawner7.1.0; verifique las combinaciones de paquetes reales dentro de la imagen operativa del chart.

Cognito es una opción de proveedor OIDC. Haga coincidir las URL de callback, los endpoints de token/userInfo, los scopes y un claim de nombre de usuario estable, y configure una política de permiso explícita. MFA/federación corporativa debe configurarse en el proveedor; GenericOAuthenticator no las habilita automáticamente.

Esta configuración de Hub presupone un volumen Secret existente montado en /run/secrets/oidc. Mantenga los secretos reales fuera de ConfigMaps, código fuente y variables de entorno. Conecte este archivo Python a la ruta de configuración real de Hub y reemplace los URI/valores sub aprobados según su entorno.

```python
from pathlib import Path

c.JupyterHub.authenticator_class = "oauthenticator.generic.GenericOAuthenticator"
c.GenericOAuthenticator.client_id = "prepared-client-id"
c.GenericOAuthenticator.client_secret = Path("/run/secrets/oidc/client-secret").read_text().strip()
c.GenericOAuthenticator.oauth_callback_url = "https://jupyter.example.com/hub/oauth_callback"
c.GenericOAuthenticator.authorize_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize"
c.GenericOAuthenticator.token_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/token"
c.GenericOAuthenticator.userdata_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/userInfo"
c.GenericOAuthenticator.scope = ["openid", "profile", "email"]
c.GenericOAuthenticator.username_claim = "sub"
c.GenericOAuthenticator.allow_all = False
c.GenericOAuthenticator.allow_existing_users = False
c.GenericOAuthenticator.allowed_users = {"replace-with-approved-cognito-sub"}
```

El ejemplo establece allow_all=False, allowed_users explícitos y allow_existing_users=False. Las comprobaciones locales permitieron una identidad aprobada y rechazaron usuarios no aprobados/anteriores. No se ejecutó ningún inicio de sesión OAuth ni intercambio de tokens real.

Distinga las garantías de CPU/RAM del notebook de los límites y haga coincidir las imágenes de GPU reales, etiquetas, tolerations y drivers. No suponga que las etiquetas jupyter/*:gpu antiguas proporcionan CUDA. Los PVC deben compartir el namespace del Pod consumidor; un Pod de jupyterhub no puede hacer referencia a un PVC de ml-platform únicamente por nombre. Revise los puntos de acceso por usuario, UID/GID, cuotas y permisos de escritura de modelos compartidos. EFS storage_capacity no es un límite de capacidad física.

### Flujo de datos de Argo Workflows

El workflow anterior hacía referencia a templates, artefactos y scripts inexistentes. Este **pequeño fixture de flujo de datos** tiene seis etapas. Pasa parámetros mediante variables de entorno y JSON en lugar de inyectar valores en el código fuente Python. Selecciona entre dos coeficientes; no es un entrenamiento real de clasificación de imágenes, pipeline de cluster Ray ni pipeline de registro externo.

Se validaron localmente el lint offline de Argo4.1.3 y los seis cuerpos de scripts Python. Prepare prepared-workflow-runner con el mínimo privilegio y configure por separado los digests de imágenes, cuotas y almacenamiento de artefactos antes de las operaciones.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: toy-dataflow-
  namespace: argo
spec:
  entrypoint: pipeline
  serviceAccountName: prepared-workflow-runner
  parallelism: 1
  activeDeadlineSeconds: 600
  arguments:
    parameters:
    - name: data
      value: '[[1,2],[2,4],[3,6],[4,8]]'
  templates:
  - name: pipeline
    dag:
      tasks:
      - name: validate
        template: validate
        arguments:
          parameters:
          - name: data
            value: '{{workflow.parameters.data}}'
      - name: prepare
        template: prepare
        arguments:
          parameters:
          - name: data
            value: '{{tasks.validate.outputs.result}}'
        dependencies:
        - validate
      - name: tune
        template: tune
        arguments:
          parameters:
          - name: data
            value: '{{tasks.prepare.outputs.result}}'
        dependencies:
        - prepare
      - name: train
        template: train
        arguments:
          parameters:
          - name: scale
            value: '{{tasks.tune.outputs.result}}'
        dependencies:
        - tune
      - name: evaluate
        template: evaluate
        arguments:
          parameters:
          - name: model
            value: '{{tasks.train.outputs.result}}'
          - name: data
            value: '{{tasks.prepare.outputs.result}}'
        dependencies:
        - train
      - name: register
        template: register
        arguments:
          parameters:
          - name: model
            value: '{{tasks.train.outputs.result}}'
        dependencies:
        - evaluate
        when: '{{tasks.evaluate.outputs.result}} == 0'
  - name: validate
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        rows = json.loads(os.environ["DATA"])

        assert rows and all(len(row) == 2 for row in rows)

        assert all(isinstance(v, (int, float)) for row in rows for v in row)

        print(json.dumps(rows))

        '
  - name: prepare
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        rows = json.loads(os.environ["DATA"])

        print(json.dumps({"train": rows[:2], "test": rows[2:]}))

        '
  - name: tune
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        data = json.loads(os.environ["DATA"])

        candidates = [1.0, 2.0]

        loss = lambda scale: sum((scale*x-y)**2 for x,y in data["train"]) / len(data["train"])

        print(min(candidates, key=loss))

        '
  - name: train
    inputs:
      parameters:
      - name: scale
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: SCALE
        value: '{{inputs.parameters.scale}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        print(json.dumps({"scale": float(os.environ["SCALE"]), "fixture": True}))

        '
  - name: evaluate
    inputs:
      parameters:
      - name: model
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: MODEL
        value: '{{inputs.parameters.model}}'
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        model = json.loads(os.environ["MODEL"])

        held_out = json.loads(os.environ["DATA"])["test"]

        print(sum((model["scale"]*x-y)**2 for x,y in held_out) / len(held_out))

        '
  - name: register
    inputs:
      parameters:
      - name: model
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: MODEL
        value: '{{inputs.parameters.model}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        model = json.loads(os.environ["MODEL"])

        print(json.dumps({"candidate": model, "note": "fixture output only; no registry write"}))

        '
```

El MSE0 del fixture procede de cuatro muestras sintéticas, no de una medición real de calidad del modelo. Los workflows de producción necesitan separación de entrenamiento/prueba, revisiones de datos/modelos, reglas de fallo/reintento/idempotencia y transferencias de artefactos reales. artifactRepositoryRef no instala boto3 ni concede permisos de descarga a la aplicación.

### Ray y Karpenter

Use las rutas auditadas de Ray2.58/KubeRay1.7 en la [guía de Ray](ray/README.md). GCS significa Global Control Service; la programación interactúa con raylets. El head puede ejecutar trabajo si anuncia CPU. Evite combinaciones no verificadas de Ray/Python entre workers de CPU/GPU/Neuron; las imágenes Neuron también necesitan Ray y frameworks compatibles.

El autoscaling de Ray expresa la demanda de Pods de workers, el scheduler de Kubernetes coloca Pods y Karpenter proporciona capacidad de nodos compatible. Los workers de Ray no invocan directamente las API de Karpenter. Haga coincidir las etiquetas de producto de memoria/GPU con nodos reales; no seleccione A100 p4d de40GB con una etiqueta de80GB.

No duplique drivers en las AMI NVIDIA AL2023 ni sobrescriba toda la configuración de containerd. Los límites de Karpenter no son límites absolutos de admisión/costo, y la consolidación no usa directamente un umbral de utilización DCGM20%. Inspeccione requests, viabilidad de programación, precios y restricciones de interrupción.

## API de DRA y límites de soporte

DRA representa atributos de dispositivos, requests y asignación mediante DeviceClass, ResourceSlice y ResourceClaim/Template. Los drivers publican slices; los componentes de scheduler/driver asignan y preparan claims. Los ResourceSlices escritos manualmente no crean GPU reales. La madurez de la API de Kubernetes y la madurez de las características del driver NVIDIA son independientes.

![Recursos extendidos de device-plugin frente a las rutas DRA de DeviceClass/ResourceSlice/ResourceClaim; el uso compartido/la topología dependen del driver, hardware y feature gates.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-2.html)

### Ejemplo de claim actual

El schema resource.k8s.io/v1 de Kubernetes1.36.2 inspeccionado usa requests.exactly. Los prerrequisitos del driver NVIDIA0.5 distinguen la asignación de GPU(1.34.2+) de ComputeDomains(1.32+). Verifique las API y versiones de patch/plataforma realmente servidas por EKS. “Todas las características DRA en1.31+” es inexacto.

Este **ejemplo de schema** define un claim de GPU y un Pod de comando de inventario. Prepare por separado el namespace ml-workloads, DeviceClass gpu.nvidia.com, driver/CDI, nodos y permisos. No se ejecutó ninguna GPU en esta auditoría.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  namespace: ml-workloads
  name: single-gpu
spec:
  spec:
    devices:
      requests:
      - name: gpu
        exactly:
          deviceClassName: gpu.nvidia.com
          count: 1
---
apiVersion: v1
kind: Pod
metadata:
  name: gpu-inventory-demo
  namespace: ml-workloads
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  containers:
  - name: inspect
    image: ubuntu:24.04
    command:
    - nvidia-smi
    - -L
    resources:
      claims:
      - name: gpu
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
  resourceClaims:
  - name: gpu
    resourceClaimTemplateName: single-gpu
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

CEL debe usar los atributos tipados/estructura de dominio publicados reales. El anterior device.topology.node==device.topology.node no expresa ni la colocación en el mismo nodo ni coincide con la API. matchAttribute necesita un atributo calificado real. Un claim de GPU normal para un único Pod no asigna automáticamente72GPU a través de un rack NVL72.

### NVIDIA0.5 y GPU Operator26.7

El README de0.5 aún describe la asignación de GPU como experimental/deshabilitada por defecto, en conflicto con la documentación de instalación/chart y Operator26.7. El chart independiente real establece por defecto resources.gpus.enabled=true pero **rechaza el renderizado** sin una aceptación explícita para evitar colisiones con device-plugin. No describa la instalación predeterminada como si deshabilitara silenciosamente las GPU y tuviera éxito.

La ruta administrada de Operator26.7 usa el singleton GPUCluster llamado gpu-cluster, mutuamente excluyente con ClusterPolicy. Su ruta de driver preinstalado establece clusterPolicy.deployCR=false, gpuCluster.deployCR=true y driver.enabled=false. GPUCluster no reemplaza toda la preparación de driver/toolkit; proporcione los prerrequisitos de driver/CDI. No instale una release DRA independiente duplicada. El renderizado local simuló una API DeviceClass servida; no habilitó una característica de cluster real.

Distinga el soporte de GPU completa/MIG existente y ComputeDomain de DynamicMIG alpha, MPS y TimeSlicingSettings. El código de feature gates0.5 inspeccionado declara esos tres como false/Alpha. Algunas etiquetas GA de la documentación también difieren de las etiquetas Beta del código; registre conjuntamente la matriz de soporte, el código y la configuración de la release exacta. GPU Operator25.3 por sí solo no establece soporte para todo.

Los device plugins también admiten rutas de MIG existente, time-slicing y MPS experimental; el uso compartido de GPU no es exclusivo de DRA.3g.20gb nombra un perfil de instancia, no tres instancias de20GB. La asignación MIG/exclusiva no aísla automáticamente el host, driver, privilegios ni todos los canales laterales; MPS/time-slicing no son límites de seguridad.

### NVLink multinodo y ComputeDomains

GB200 es Grace Blackwell, no Grace Hopper. ComputeDomains coordinan recursos MNNVL/IMEX entre Pods/nodos. Distinga racks, instancias EC2, nodos Kubernetes y Pods, y verifique el soporte real de clique/fabric/dispositivo/driver. Los campos nvswitchEnabled/graceHopperMode o scheduling gates inventados no configuran la topología. Un scheduling gate sin un controller que lo elimine deja el Pod esperando.

## Plataformas de agentes y MCP

Use las API actuales de Kagent/LangGraph/Langfuse/Milvus en la [guía de IA agéntica](03-agentic-ai-platform.md). GitLab es una plataforma opcional de fuente/CI; los runners privilegiados y el ingress público no son requisitos de referencia. Separe la identidad de trabajo, redes, secretos y permisos de creación de imágenes, y verifique la entrega de credenciales del proveedor.

MCP define operaciones de protocolo como el listado/llamada de herramientas; no es un controller de descubrimiento automático estándar de Kubernetes ni una distribución de gateway. La imagen anterior ghcr.io/anthropics/mcp-gateway:latest y la etiqueta/configuración mcp.anthropic.com/tool eran implementaciones no verificadas y se eliminaron. Seleccione una release real de server/gateway y valide el transporte, autenticación, autorización, timeouts y schemas de entrada de herramientas. Una variable de entorno de URL no implementa esas operaciones.

Solicitar recursos de GPU para Milvus no habilita la indexación por GPU. Haga coincidir dimensiones de embedding/revisiones de modelo, parámetros de índice, ciclo de vida de eliminación/actualización y filtros de tenant. No use un Deployment de Langfuse2.x como instalación de plataforma4.x actual; compruebe dependencias de backend, credenciales de archivos, API de instrumentación y retención de datos sensibles.

## Almacenamiento y redes

Verifique IAM/UID/GID del access point de EFS, permisos de directorio y consumo de PVC en el mismo namespace. La opción de montaje IAM no configura por sí misma las credenciales de identidad de controller/montaje.

Use parámetros de CSI FSx y unidades de capacidad compatibles. No copie configuraciones s3ImportPath/s3ExportPath inventadas para PERSISTENT_2 ni una capacidad10Ti inválida. Distinga los filesystems existentes/estáticos y los recién aprovisionados, DRA y la compatibilidad de backups en la [guía de almacenamiento](01-ai-ml-workloads.md).

Mountpoint CSI2.8.0 admite **PV estáticos** para buckets S3 existentes. Se eliminó el ejemplo de bucket dinámico solo con StorageClass/PVC. Mountpoint no es totalmente POSIX; compruebe el comportamiento de rename, escritura aleatoria, locking y checkpoints. La tabla de soporte2.8 elimina AL2/Ubuntu22.04 y dirige las instalaciones a add-ons de EKS o charts oficiales en lugar de branches de repositorio.

No multiplique el recuento de interfaces por el ancho de banda de instancia ya agregado. Las cifras anteriores de p4d“4×400Gbps” y trn1n“16×1600Gbps” eran incorrectas. Use la [guía de redes de entrenamiento](05-model-training.md) para la colocación en la misma AZ, interfaces reales, driver/libfabric/NCCL, asignación de dispositivo/Pod y security groups. Las etiquetas RAID0 y efa-enabled no habilitan EFA.

Las subnets son una parte del aislamiento. Configure los requisitos de ingress/egress de carga de trabajo y autorreferencia de EFA mediante recursos SG/IAM reales. El YAML con aspecto de Terraform almacenado en un ConfigMap no aplica reglas de red. Evite el acceso predeterminado desde todo un CIDR de VPC.

## Observabilidad y alertas de GPU

DCGM Exporter4.6.0-4.8.3 define XID_ERRORS como el último gauge de código de error. increase(XID_ERRORS) no es un recuento de errores y puede interpretar erróneamente un cambio de código31→13 como un reinicio. Observe el código actual o habilite por separado el contador XID_ERRORS_TOTAL. No todos los XID indican un fallo de hardware.

FB_USED/FB_FREE son gauges de MiB; la relación siguiente va de0 a1. VRAM reservada alta no es necesariamente OOM: inspeccione juntos los fallos de asignación, comportamiento de carga de trabajo, caché de modelo y memoria disponible. Los umbrales fijos de85C/20% no son estándares universales de fallo/reclamación. Compruebe los tipos/unidades reales de métricas antes de aplicar rate() al rendimiento PCIe o a los gauges de ancho de banda NVLink.

Estas reglas presuponen un cluster por Prometheus. Para clusters combinados, incluya etiquetas de cluster en agregación/joins. Inspeccione las etiquetas reales de nodo/UUID/MIG y la normalización de etiquetas de recursos de kube-state-metrics.

```yaml
groups:
- name: gpu-observations
  rules:
  - record: gpu:framebuffer_used_ratio
    expr: DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)
  - alert: GPUReportedXIDCode
    expr: DCGM_FI_DEV_XID_ERRORS > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Inspect the reported XID code and workload context"
  - record: namespace:pending_gpu_requesting_pods:count
    expr: |
      count by (namespace) (
        max by (namespace, pod) (kube_pod_status_phase{phase="Pending"} == 1)
        and on (namespace, pod)
        max by (namespace, pod) (kube_pod_container_resource_requests{resource="nvidia_com_gpu"} > 0)
      )
```

La regla de pendientes cuenta los Pods en espera que solicitan GPU; no demuestra que la escasez de GPU haya causado la espera. Varios containers que solicitan GPU cuentan una vez por Pod. Inspeccione eventos, PVC, affinity, taints, cuotas, claims e image pulls. No suponga que exista una etiqueta de nodo en cada alerta.

Configure la selección de reglas de Prometheus real y el scraping correcto de Service/puerto para DCGM, Ray y Karpenter. El aprovisionamiento de archivos de Grafana difiere de un wrapper de dashboard HTTP; una etiqueta por sí sola no conecta datasources. La salida de monitor Neuron y los endpoints de exporter necesitan preparación independiente.

## Alcance de la verificación

Se revisaron todo el texto original de la guía/quiz y58bloques de código únicos. Las comprobaciones cubren schemas DRA/Pod, Helm oficial, políticas de permiso de OAuthenticator, lint offline/cuerpos de scripts de Argo y fixtures de Prometheus. No se ejecutó ningún OAuth/cluster/asignación de GPU/DRA, modelo, montaje S3 ni server MCP real; no se crearon recursos cloud ni llamadas de pago.

## Referencias

- [Instalación DRA de GPU Operator26.7](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/dra-intro-install.html)
- [Código fuente de NVIDIA DRA0.5](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/tree/v0.5.0)
- [Prerrequisitos de DRA0.5](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [Feature gates de DRA0.5](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/pkg/featuregates/featuregates.go)
- [OAuthenticator17.4](https://github.com/jupyterhub/oauthenticator/tree/17.4.0)
- [Chart JupyterHub4.4.2](https://github.com/jupyterhub/zero-to-jupyterhub-k8s/releases/tag/4.4.2)
- [Argo Workflows4.1.3](https://github.com/argoproj/argo-workflows/tree/v4.1.3)
- [Mountpoint CSI2.8.0](https://github.com/awslabs/mountpoint-s3-csi-driver/tree/v2.8.0)
- [Definiciones de contadores de DCGM Exporter](https://github.com/NVIDIA/dcgm-exporter/blob/4.6.0-4.8.3/etc/default-counters.csv)
- [Especificación de herramientas MCP](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

## Cuestionario

[Cuestionario de infraestructura de IA](../quizzes/ai-ml/06-ai-infrastructure-quiz.md)
